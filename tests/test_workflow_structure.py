from smart_pr_review_workflow.state import PRState
from smart_pr_review_workflow.workflow import build_workflow


def test_graph_contains_stage5_nodes() -> None:
    graph = build_workflow()
    nodes = set(graph.nodes)
    assert {
        "classify_change",
        "select_checks",
        "retrieve_knowledge",
        "run_check",
        "generate_review",
        "evaluate_review",
        "revise_review",
        "finalize_review",
    }.issubset(nodes)


def test_state_has_revision_and_evaluation_fields() -> None:
    annotations = PRState.__annotations__
    assert "review_draft" in annotations
    assert "evaluation" in annotations
    assert "revision_count" in annotations
    assert "max_revision_attempts" in annotations
    assert "evaluation_passed" in annotations
