import os

import pytest

from smart_pr_review_workflow.nodes import load_pr


def test_load_pr_requires_github_identifiers(monkeypatch):
    monkeypatch.setenv("GITHUB_ENABLED", "true")
    monkeypatch.delenv("GITHUB_OWNER", raising=False)
    monkeypatch.delenv("GITHUB_REPO", raising=False)
    monkeypatch.delenv("GITHUB_PR_NUMBER", raising=False)

    with pytest.raises(RuntimeError, match="GITHUB_OWNER"):
        load_pr({})
