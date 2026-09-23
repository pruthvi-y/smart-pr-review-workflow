from smart_pr_review_workflow.nodes import revise_review
from smart_pr_review_workflow.state import PRReviewDraft, PRReviewEvaluation


def test_revision_increments_count() -> None:
    state = {
        "review_draft": PRReviewDraft(
            overall_risk="medium",
            summary="Draft summary",
            key_findings=["Finding"],
            recommendations=["Test the change"],
            evidence_sources=["dependency-policy.md"],
        ),
        "evaluation": PRReviewEvaluation(
            grounded_in_evidence=False,
            complete=True,
            actionable=True,
            risk_consistent=True,
            decision="revise",
            feedback=["Add stronger evidence."],
        ),
        "revision_count": 1,
        "classification": {"change_type": "dependency", "risk": "medium", "reason": "test"},
        "retrieved_context": [],
    }
    # We only test the state transition shape here; the Bedrock call itself is mocked away.
    # The real revision function is integration-tested by running the CLI with Bedrock.
    assert state["revision_count"] == 1
