from pathlib import Path

from smart_pr_review_workflow.state import PRState
from smart_pr_review_workflow.workflow import build_workflow


def test_stage7_graph_contains_github_nodes():
    graph = build_workflow()
    assert "load_pr" in graph.nodes
    assert "post_github_review" in graph.nodes


def test_stage7_state_has_github_fields():
    annotations = PRState.__annotations__
    assert "github_enabled" in annotations
    assert "github_pr_url" in annotations
    assert "github_comment_posted" in annotations
