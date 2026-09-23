import os

from .rag import build_index
from .workflow import build_workflow


MOCK_PR = {
    "pr_title": "Upgrade Jackson dependency from 2.15.x to 2.17.x",
    "pr_description": (
        "Upgrade the JSON dependency to address security findings and keep the "
        "payment service on a supported version."
    ),
    "changed_files": [
        "pom.xml",
        "src/main/java/com/example/payment/PaymentService.java",
    ],
    "file_changes": [
        {
            "filename": "pom.xml",
            "status": "modified",
            "additions": 1,
            "deletions": 1,
            "changes": 2,
            "patch": "@@ -20,7 +20,7 @@\n- <jackson.version>2.15.x</jackson.version>\n+ <jackson.version>2.17.x</jackson.version>",
        },
        {
            "filename": "src/main/java/com/example/payment/PaymentService.java",
            "status": "modified",
            "additions": 2,
            "deletions": 1,
            "changes": 3,
            "patch": "@@ -42,6 +42,7 @@\n paymentClient.send(request);\n+ logger.info(\"Payment request sent\");",
        },
    ],
    "github_enabled": False,
    "github_integration": "mock",
    "revision_count": 0,
    "max_revision_attempts": 2,
}


def main() -> None:
    graph = build_workflow()
    github_enabled = os.getenv("GITHUB_ENABLED", "false").lower() == "true"
    github_integration = os.getenv("GITHUB_INTEGRATION", "mcp").lower()

    print("\n--- Running Smart PR Review Workflow: Stage 8 ---\n")
    print(f"[source] {'GitHub PR' if github_enabled else 'mock PR'}")
    if github_enabled:
        print(f"[github] integration={github_integration}")

    print("[rag] Loading local knowledge index...")
    count = build_index()
    print(f"[rag] index_ready chunks={count}")

    initial_state = dict(MOCK_PR)
    config = {"configurable": {"thread_id": "stage8-pr-review-demo"}}

    final_state = None
    previous_count = 0
    seen_sources = False
    seen_draft = False
    seen_github = False
    last_revision_count = 0

    for state in graph.stream(initial_state, config=config, stream_mode="values"):
        final_state = state

        if state.get("github_enabled") and state.get("github_pr_url") and not seen_github:
            print(f"[github] loaded {state['github_pr_url']}")
            seen_github = True
        if "classification" in state and "review_route" not in state:
            classification = state["classification"]
            print(f"[classify] type={classification.change_type}, risk={classification.risk}")
        elif "checks_to_run" in state and "retrieved_context" not in state:
            print(f"[plan] route={state['review_route']}")
            print(f"       checks={state['checks_to_run']}")
        elif "retrieved_context" in state and not seen_sources:
            sources = [item["source"] for item in state["retrieved_context"]]
            print(f"[rag] retrieved={len(sources)} chunks")
            print(f"      sources={', '.join(sources)}")
            seen_sources = True
        elif len(state.get("analysis_results", [])) > previous_count:
            completed = state["analysis_results"][-1]["check_name"]
            print(f"[parallel check completed] {completed}")
        elif "review_draft" in state and not seen_draft:
            print("[review] draft generated")
            seen_draft = True
        elif "evaluation" in state:
            evaluation = state["evaluation"]
            print(
                f"[evaluator] decision={evaluation.decision} "
                f"grounded={evaluation.grounded_in_evidence} "
                f"complete={evaluation.complete} "
                f"actionable={evaluation.actionable} "
                f"risk_consistent={evaluation.risk_consistent}"
            )
        if state.get("revision_count", 0) > last_revision_count:
            print(f"[revision] pass={state['revision_count']}")
            last_revision_count = state["revision_count"]
        if state.get("github_comment_posted"):
            print(
                f"[github] review comment posted: {state.get('github_comment_url', '')}"
            )
        previous_count = len(state.get("analysis_results", []))

    if final_state is None:
        raise RuntimeError("Workflow produced no state")

    classification = final_state["classification"]
    print("\n--- Final Result ---\n")
    print(f"Change type : {classification.change_type}")
    print(f"Initial risk: {classification.risk}")
    print(f"Route       : {final_state['review_route']}")
    print(f"Checks      : {', '.join(final_state['checks_to_run'])}")
    print(f"RAG chunks  : {len(final_state.get('retrieved_context', []))}")
    print(f"Revisions   : {final_state.get('revision_count', 0)}")
    print(f"GitHub      : {final_state.get('github_enabled', False)}")
    print(f"Integration : {final_state.get('github_integration', 'mock')}")
    print(f"Commented   : {final_state.get('github_comment_posted', False)}")
    print("\n" + final_state["final_review"])


if __name__ == "__main__":
    main()
