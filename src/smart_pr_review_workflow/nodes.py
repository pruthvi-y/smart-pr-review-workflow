import os

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Command, Send

from .model import get_llm
from .rag import retrieve_policy_context
from .state import (
    CheckName,
    PRCheckOutput,
    PRClassification,
    PRFileChange,
    PRReviewDraft,
    PRReviewEvaluation,
    PRState,
    RetrievedContext,
    ReviewRoute,
)
from .tools.github import GitHubClient
from .mcp.client import MCPGitHubClient


CHECK_DESCRIPTIONS: dict[CheckName, str] = {
    "security": (
        "Look for security-relevant concerns in the change. Do not invent vulnerabilities; "
        "only raise concerns supported by the supplied PR details and evidence."
    ),
    "code_quality": (
        "Look for maintainability, correctness, regression, testing, and code-quality concerns."
    ),
    "policy": (
        "Check whether the change appears to need additional engineering/security approval or evidence. "
        "Use the retrieved policy context as the source of truth."
    ),
    "operational": (
        "Look for deployment, configuration, compatibility, rollback, and operational concerns."
    ),
}


def _github_is_enabled() -> bool:
    return os.getenv("GITHUB_ENABLED", "false").lower() == "true"


def _github_integration() -> str:
    integration = os.getenv("GITHUB_INTEGRATION", "mcp").lower()
    if integration not in {"rest", "mcp"}:
        raise RuntimeError("GITHUB_INTEGRATION must be 'mcp' or 'rest'.")
    return integration


def _format_file_changes(file_changes: list[PRFileChange], max_chars: int = 12000) -> str:
    sections: list[str] = []
    current = 0
    for item in file_changes:
        section = (
            f"File: {item.get('filename', 'unknown')}\n"
            f"Status: {item.get('status', 'unknown')} | "
            f"+{item.get('additions', 0)} / -{item.get('deletions', 0)}\n"
            f"Patch:\n{item.get('patch', '[patch unavailable]')}"
        )
        if current + len(section) > max_chars:
            sections.append("[remaining file changes omitted for prompt size]")
            break
        sections.append(section)
        current += len(section)
    return "\n\n".join(sections)


def _get_github_client():
    return MCPGitHubClient() if _github_integration() == "mcp" else GitHubClient()


def load_pr(state: PRState) -> dict:
    """Use GitHub through MCP (default) or REST when enabled; otherwise keep mock mode."""
    if not _github_is_enabled():
        return {"github_enabled": False, "github_integration": "mock"}

    owner = os.getenv("GITHUB_OWNER")
    repo = os.getenv("GITHUB_REPO")
    number = os.getenv("GITHUB_PR_NUMBER")
    if not owner or not repo or not number:
        raise RuntimeError(
            "GITHUB_OWNER, GITHUB_REPO, and GITHUB_PR_NUMBER are required when GITHUB_ENABLED=true."
        )

    client = _get_github_client()
    if _github_integration() == "mcp":
        pr, files = client.get_pull_request_bundle(owner, repo, int(number))
    else:
        pr, files = client.get_pull_request(owner, repo, int(number)), client.list_pull_request_files(owner, repo, int(number))

    file_changes: list[PRFileChange] = [
        {
            "filename": item.get("filename", ""),
            "status": item.get("status", ""),
            "additions": int(item.get("additions", 0)),
            "deletions": int(item.get("deletions", 0)),
            "changes": int(item.get("changes", 0)),
            "patch": item.get("patch", ""),
        }
        for item in files
    ]

    return {
        "github_enabled": True,
        "github_integration": _github_integration(),
        "github_owner": owner,
        "github_repo": repo,
        "github_pr_number": int(number),
        "github_pr_url": pr.get("html_url", ""),
        "github_head_sha": pr.get("head_sha", ""),
        "pr_title": pr.get("title", ""),
        "pr_description": pr.get("body") or "",
        "changed_files": [item["filename"] for item in file_changes],
        "file_changes": file_changes,
    }


def classify_change(state: PRState) -> dict:
    """Use Bedrock to classify the PR and estimate initial risk."""
    classifier = get_llm().with_structured_output(PRClassification)
    changed_files = ", ".join(state.get("changed_files", []))
    diff_summary = _format_file_changes(state.get("file_changes", []), max_chars=8000)

    messages = [
        SystemMessage(
            content=(
                "You are a senior software engineer performing initial PR triage. "
                "Classify the change conservatively based only on the supplied PR details."
            )
        ),
        HumanMessage(
            content=(
                f"PR title: {state['pr_title']}\n"
                f"PR description: {state.get('pr_description', '')}\n"
                f"Changed files: {changed_files}\n\n"
                f"Diff summary:\n{diff_summary}"
            )
        ),
    ]

    result = classifier.invoke(messages)
    return {"classification": result}


def select_checks(state: PRState) -> dict:
    """Select which checks should run for this PR type."""
    change_type = state["classification"].change_type

    if change_type == "dependency":
        route: ReviewRoute = "security_review"
        checks = ["security", "policy", "code_quality"]
    elif change_type in {"feature", "bugfix", "refactor"}:
        route = "code_review"
        checks = ["code_quality", "security", "policy"]
    elif change_type == "configuration":
        route = "configuration_review"
        checks = ["operational", "security", "policy"]
    else:
        route = "general_review"
        checks = ["code_quality", "policy"]

    return {"review_route": route, "checks_to_run": checks}


def retrieve_knowledge(state: PRState) -> dict:
    """Retrieve project policies before parallel checks run."""
    classification = state["classification"]
    query = (
        f"PR title: {state['pr_title']}\n"
        f"PR description: {state.get('pr_description', '')}\n"
        f"Change type: {classification.change_type}\n"
        f"Risk: {classification.risk}\n"
        f"Changed files: {', '.join(state.get('changed_files', []))}"
    )

    results = retrieve_policy_context(query, k=4)
    context: list[RetrievedContext] = [
        {"source": item["source"], "content": item["content"], "score": item["score"]}
        for item in results
    ]
    return {"retrieved_context": context}


def fan_out_checks(state: PRState) -> list[Send]:
    """Create one parallel task for every selected check."""
    return [
        Send(
            "run_check",
            {
                "pr_title": state["pr_title"],
                "pr_description": state.get("pr_description", ""),
                "changed_files": state.get("changed_files", []),
                "file_changes": state.get("file_changes", []),
                "classification": state["classification"],
                "check_name": check_name,
                "retrieved_context": state.get("retrieved_context", []),
            },
        )
        for check_name in state.get("checks_to_run", [])
    ]


def run_check(task_state: dict) -> dict:
    """Run one reusable specialist check with retrieved policy context."""
    check_name: CheckName = task_state["check_name"]
    classification = task_state["classification"]
    changed_files = ", ".join(task_state.get("changed_files", []))
    context_text = "\n\n".join(
        f"Source: {item['source']}\n{item['content']}"
        for item in task_state.get("retrieved_context", [])
    )
    diff_summary = _format_file_changes(task_state.get("file_changes", []), max_chars=8000)

    reviewer = get_llm().with_structured_output(PRCheckOutput)
    messages = [
        SystemMessage(
            content=(
                "You are performing one focused pull-request review check. "
                f"Check type: {check_name}. {CHECK_DESCRIPTIONS[check_name]} "
                "Use the retrieved project policy only as supporting evidence. "
                "If the evidence does not support a claim, say so rather than inventing facts. "
                "Return concise findings and a practical recommendation."
            )
        ),
        HumanMessage(
            content=(
                f"PR title: {task_state['pr_title']}\n"
                f"PR description: {task_state.get('pr_description', '')}\n"
                f"Changed files: {changed_files}\n"
                f"Change type: {classification.change_type}\n"
                f"Initial risk: {classification.risk}\n"
                f"Classification reason: {classification.reason}\n\n"
                f"Diff summary:\n{diff_summary}\n\n"
                f"Retrieved policy context:\n{context_text}"
            )
        ),
    ]

    result = reviewer.invoke(messages)
    return {
        "analysis_results": [
            {
                "check_name": check_name,
                "status": result.status,
                "summary": result.summary,
                "findings": result.findings,
                "recommendation": result.recommendation,
                "evidence": task_state.get("retrieved_context", []),
            }
        ]
    }


def generate_review(state: PRState) -> dict:
    """Turn parallel findings into one structured review draft."""
    results_text = "\n\n".join(
        f"[{result['check_name'].upper()}]\n"
        f"Status: {result['status']}\n"
        f"Summary: {result['summary']}\n"
        f"Findings: {'; '.join(result.get('findings', []))}\n"
        f"Recommendation: {result['recommendation']}\n"
        f"Evidence: {', '.join(e['source'] for e in result.get('evidence', []))}"
        for result in state.get("analysis_results", [])
    )

    context_text = "\n\n".join(
        f"Source: {item['source']}\n{item['content']}"
        for item in state.get("retrieved_context", [])
    )

    writer = get_llm().with_structured_output(PRReviewDraft)
    messages = [
        SystemMessage(
            content=(
                "You consolidate multiple PR checks into one concise, evidence-grounded review draft. "
                "Use only the supplied PR details, findings, and evidence."
            )
        ),
        HumanMessage(
            content=(
                f"PR title: {state['pr_title']}\n"
                f"Classification: {state['classification'].model_dump()}\n\n"
                f"Check findings:\n{results_text}\n\n"
                f"Retrieved context:\n{context_text}"
            )
        ),
    ]
    draft = writer.invoke(messages)
    return {"review_draft": draft}


def evaluate_review(state: PRState) -> Command:
    """Evaluate the draft and either revise it or move to finalization."""
    draft = state["review_draft"]
    context_text = "\n\n".join(
        f"Source: {item['source']}\n{item['content']}"
        for item in state.get("retrieved_context", [])
    )

    evaluator = get_llm().with_structured_output(PRReviewEvaluation)
    messages = [
        SystemMessage(
            content=(
                "Evaluate a software PR review draft. Check whether it is grounded in supplied evidence, "
                "complete enough for a reviewer, actionable, and consistent with the initial risk. "
                "If any important criterion fails, choose revise and provide targeted feedback."
            )
        ),
        HumanMessage(
            content=(
                f"Classification: {state['classification'].model_dump()}\n"
                f"\nDraft:\n{draft.model_dump()}\n"
                f"\nEvidence:\n{context_text}"
            )
        ),
    ]

    evaluation = evaluator.invoke(messages)
    if os.getenv("DEMO_FORCE_FIRST_REVISION", "false").lower() == "true" and state.get("revision_count", 0) == 0:
        evaluation = evaluation.model_copy(
            update={
                "decision": "revise",
                "feedback": evaluation.feedback or [
                    "Demo mode: perform one revision pass so the graph loop is visible."
                ],
            }
        )

    max_attempts = state.get("max_revision_attempts", 2)
    revisions = state.get("revision_count", 0)
    should_revise = evaluation.decision == "revise" and revisions < max_attempts

    return Command(
        update={
            "evaluation": evaluation,
            "evaluation_passed": not should_revise,
        },
        goto="revise_review" if should_revise else "finalize_review",
    )


def revise_review(state: PRState) -> dict:
    """Use evaluator feedback to create a better review draft."""
    draft = state["review_draft"]
    evaluation = state["evaluation"]
    context_text = "\n\n".join(
        f"Source: {item['source']}\n{item['content']}"
        for item in state.get("retrieved_context", [])
    )

    reviser = get_llm().with_structured_output(PRReviewDraft)
    messages = [
        SystemMessage(
            content=(
                "You revise an engineering PR review using evaluator feedback. "
                "Keep strong existing content, fix the identified gaps, remain evidence-grounded, "
                "and avoid inventing facts."
            )
        ),
        HumanMessage(
            content=(
                f"Original PR classification: {state['classification'].model_dump()}\n"
                f"\nCurrent draft:\n{draft.model_dump()}\n"
                f"\nEvaluator feedback:\n{evaluation.feedback}\n"
                f"\nEvidence:\n{context_text}"
            )
        ),
    ]

    revised = reviser.invoke(messages)
    return {
        "review_draft": revised,
        "revision_count": state.get("revision_count", 0) + 1,
    }


def finalize_review(state: PRState) -> dict:
    """Convert the accepted/latest structured draft into readable output."""
    draft = state["review_draft"]
    lines = [
        "## Smart PR Review",
        f"Overall risk: {draft.overall_risk.upper()}",
        f"Summary: {draft.summary}",
        "",
        "### Key findings",
    ]
    for finding in draft.key_findings:
        lines.append(f"- {finding}")

    lines.extend(["", "### Recommendations"])
    for recommendation in draft.recommendations:
        lines.append(f"- {recommendation}")

    if draft.evidence_sources:
        lines.extend(["", f"Evidence sources: {', '.join(sorted(set(draft.evidence_sources)))}"])

    lines.extend(["", "_Generated by the Smart PR Review Workflow._"])
    return {"final_review": "\n".join(lines)}


def post_github_review(state: PRState) -> dict:
    """Post the final review through the configured GitHub integration when enabled."""
    if not state.get("github_enabled", False):
        return {"github_comment_posted": False}

    if os.getenv("GITHUB_POST_REVIEW_COMMENT", "false").lower() != "true":
        return {"github_comment_posted": False}

    owner = state["github_owner"]
    repo = state["github_repo"]
    number = state["github_pr_number"]
    result = _get_github_client().create_pull_request_comment(
        owner, repo, number, state["final_review"]
    )

    return {
        "github_comment_posted": True,
        "github_comment_url": result.get("html_url", ""),
    }
