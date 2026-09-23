from typing import Annotated, Literal
import operator

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


ChangeType = Literal[
    "dependency",
    "feature",
    "bugfix",
    "refactor",
    "configuration",
    "documentation",
    "other",
]
RiskLevel = Literal["low", "medium", "high"]
ReviewRoute = Literal[
    "security_review",
    "code_review",
    "configuration_review",
    "general_review",
]
CheckName = Literal["security", "code_quality", "policy", "operational"]
CheckStatus = Literal["pass", "review", "concern"]
EvaluationDecision = Literal["approve_draft", "revise"]


class PRClassification(BaseModel):
    change_type: ChangeType = Field(description="Primary type of change in the pull request")
    risk: RiskLevel = Field(description="Initial engineering risk assessment")
    reason: str = Field(description="Short explanation for the classification")


class PRCheckOutput(BaseModel):
    status: CheckStatus = Field(description="Overall result of this check")
    summary: str = Field(description="One or two sentence summary")
    findings: list[str] = Field(default_factory=list, description="Important findings")
    recommendation: str = Field(description="Most useful next step")


class PRCheckResult(TypedDict):
    check_name: CheckName
    status: CheckStatus
    summary: str
    findings: list[str]
    recommendation: str
    evidence: list[dict[str, str]]


class RetrievedContext(TypedDict):
    source: str
    content: str
    score: str


class PRFileChange(TypedDict, total=False):
    filename: str
    status: str
    additions: int
    deletions: int
    changes: int
    patch: str


class PRReviewDraft(BaseModel):
    overall_risk: RiskLevel = Field(description="Overall risk after considering all checks")
    summary: str = Field(description="Concise overall review summary")
    key_findings: list[str] = Field(default_factory=list, description="Important findings")
    recommendations: list[str] = Field(default_factory=list, description="Actionable recommendations")
    evidence_sources: list[str] = Field(default_factory=list, description="Policy/source names")


class PRReviewEvaluation(BaseModel):
    grounded_in_evidence: bool
    complete: bool
    actionable: bool
    risk_consistent: bool
    decision: EvaluationDecision
    feedback: list[str] = Field(default_factory=list)


class PRState(TypedDict, total=False):
    # Input / source information
    pr_title: str
    pr_description: str
    changed_files: list[str]
    file_changes: list[PRFileChange]
    github_enabled: bool
    github_owner: str
    github_repo: str
    github_pr_number: int
    github_pr_url: str
    github_head_sha: str
    github_integration: str

    # Graph state
    classification: PRClassification
    review_route: ReviewRoute
    checks_to_run: list[CheckName]
    retrieved_context: list[RetrievedContext]
    analysis_results: Annotated[list[PRCheckResult], operator.add]
    review_draft: PRReviewDraft
    evaluation: PRReviewEvaluation
    evaluation_passed: bool
    revision_count: int
    max_revision_attempts: int
    final_review: str

    # Tool/action state
    github_comment_posted: bool
    github_comment_url: str
