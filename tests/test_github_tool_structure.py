from smart_pr_review_workflow.tools.github import GitHubClient


def test_github_client_exposes_core_operations():
    assert hasattr(GitHubClient, "get_pull_request")
    assert hasattr(GitHubClient, "list_pull_request_files")
    assert hasattr(GitHubClient, "create_pull_request_comment")
