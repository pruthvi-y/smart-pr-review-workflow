from langgraph.graph import END, START, StateGraph

from .nodes import (
    classify_change,
    evaluate_review,
    fan_out_checks,
    finalize_review,
    generate_review,
    load_pr,
    post_github_review,
    retrieve_knowledge,
    revise_review,
    run_check,
    select_checks,
)
from .state import PRState


def build_workflow():
    """Build Stage 8: review a mock or real GitHub PR and optionally post via REST or MCP."""
    builder = StateGraph(PRState)

    builder.add_node("load_pr", load_pr)
    builder.add_node("classify_change", classify_change)
    builder.add_node("select_checks", select_checks)
    builder.add_node("retrieve_knowledge", retrieve_knowledge)
    builder.add_node("run_check", run_check)
    builder.add_node("generate_review", generate_review)
    builder.add_node("evaluate_review", evaluate_review)
    builder.add_node("revise_review", revise_review)
    builder.add_node("finalize_review", finalize_review)
    builder.add_node("post_github_review", post_github_review)

    builder.add_edge(START, "load_pr")
    builder.add_edge("load_pr", "classify_change")
    builder.add_edge("classify_change", "select_checks")
    builder.add_edge("select_checks", "retrieve_knowledge")
    builder.add_conditional_edges("retrieve_knowledge", fan_out_checks, ["run_check"])
    builder.add_edge("run_check", "generate_review")
    builder.add_edge("generate_review", "evaluate_review")
    builder.add_edge("revise_review", "evaluate_review")
    builder.add_edge("finalize_review", "post_github_review")
    builder.add_edge("post_github_review", END)

    return builder.compile()
