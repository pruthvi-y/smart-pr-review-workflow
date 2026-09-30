import argparse
import os
import sys

from .batch import BatchScanConfig, run_batch_reviews
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


def _run_single_workflow(owner: str, repo: str, pr_number: int) -> dict:
    """Run the workflow for a single PR and return final state."""
    graph = build_workflow()
    github_enabled = os.getenv("GITHUB_ENABLED", "false").lower() == "true"
    github_integration = os.getenv("GITHUB_INTEGRATION", "mcp").lower()

    initial_state = dict(MOCK_PR)
    if github_enabled:
        initial_state.update({
            "github_enabled": True,
            "github_integration": github_integration,
            "github_owner": owner,
            "github_repo": repo,
            "github_pr_number": pr_number,
        })

    config = {"configurable": {"thread_id": f"stage8-pr-review-{owner}-{repo}-{pr_number}"}}

    final_state = None
    for state in graph.stream(initial_state, config=config, stream_mode="values"):
        final_state = state

    return final_state or {}


def _run_single_pr_interactive() -> None:
    """Run single PR review with full output."""
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Smart PR Review Workflow: LangGraph + Bedrock + Local RAG + MCP"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Run in batch mode (review multiple PRs)",
    )
    parser.add_argument(
        "--owner",
        default=os.getenv("GITHUB_OWNER"),
        help="Repository owner (or use GITHUB_OWNER env var)",
    )
    parser.add_argument(
        "--repo",
        default=os.getenv("GITHUB_REPO"),
        help="Repository name (or use GITHUB_REPO env var)",
    )
    parser.add_argument(
        "--labels",
        help="Include PRs with these labels (comma-separated)",
    )
    parser.add_argument(
        "--exclude-labels",
        help="Exclude PRs with these labels (comma-separated)",
    )
    parser.add_argument(
        "--state",
        default="open",
        choices=["open", "closed", "all"],
        help="PR state filter (default: open)",
    )
    parser.add_argument(
        "--sort",
        default="created",
        choices=["created", "updated", "popularity"],
        help="Sort order (default: created)",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Maximum PRs to review (default: 10)",
    )
    parser.add_argument(
        "--no-exclude-draft",
        action="store_true",
        help="Include draft PRs (by default excluded)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output",
    )
    parser.add_argument(
        "--auto-label-reviewed",
        action="store_true",
        default=os.getenv("GITHUB_AUTO_LABEL_REVIEWED", "true").lower() == "true",
        help="Automatically add 'reviewed' label after posting a comment (env: GITHUB_AUTO_LABEL_REVIEWED)",
    )
    parser.add_argument(
        "--reviewed-label",
        default=os.getenv("GITHUB_REVIEWED_LABEL", "reviewed"),
        help="Label name to mark reviewed PRs (env: GITHUB_REVIEWED_LABEL, default: 'reviewed')",
    )
    parser.add_argument(
        "--show-full-review",
        action="store_true",
        help="Display complete review findings and recommendations (verbose batch mode)",
    )

    args = parser.parse_args()

    # Single PR mode (default)
    if not args.batch:
        print("[rag] Loading local knowledge index...")
        build_index()
        _run_single_pr_interactive()
        return

    # Batch mode
    if not args.owner or not args.repo:
        print("Error: --owner and --repo are required for batch mode")
        print("Or set GITHUB_OWNER and GITHUB_REPO environment variables")
        sys.exit(1)

    # Parse label filters
    labels = None
    if args.labels:
        labels = [l.strip() for l in args.labels.split(",")]

    exclude_labels = None
    if args.exclude_labels:
        exclude_labels = [l.strip() for l in args.exclude_labels.split(",")]

    # Build batch config
    config = BatchScanConfig(
        owner=args.owner,
        repo=args.repo,
        labels=labels,
        state=args.state,
        max_results=args.max_results,
        sort=args.sort,
        exclude_draft=not args.no_exclude_draft,
        exclude_labels=exclude_labels,
    )

    print("[rag] Loading local knowledge index...")
    build_index()

    # Run batch reviews
    results = run_batch_reviews(
        config=config,
        run_workflow=_run_single_workflow,
        use_mcp=os.getenv("GITHUB_INTEGRATION", "mcp").lower() == "mcp",
        verbose=not args.quiet,
        auto_label_reviewed=args.auto_label_reviewed,
        reviewed_label=args.reviewed_label,
        show_full_review=args.show_full_review,
    )

    if args.quiet:
        successes = sum(1 for r in results["results"] if r["status"] == "success")
        failures = len(results["results"]) - successes
        print(f"\n[summary] Reviewed {successes} PRs, {failures} errors\n")


if __name__ == "__main__":
    main()
