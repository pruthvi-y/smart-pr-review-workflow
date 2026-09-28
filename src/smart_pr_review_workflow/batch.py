"""Batch scanning mode for reviewing multiple PRs from a repository."""

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from .tools.github import GitHubClient
from .mcp.client import MCPGitHubClient


@dataclass
class BatchScanConfig:
    """Configuration for batch PR scanning."""

    owner: str
    repo: str
    labels: list[str] | None = None  # Filter by labels (empty = any)
    state: str = "open"  # 'open', 'closed', or 'all'
    max_results: int = 10
    sort: str = "created"  # 'created', 'updated', 'popularity'
    direction: str = "desc"  # 'asc' or 'desc'
    exclude_draft: bool = True
    exclude_labels: list[str] | None = None  # PRs with any of these labels are skipped


@dataclass
class PRBatchItem:
    """A PR from the batch listing."""

    owner: str
    repo: str
    number: int
    title: str
    url: str
    created_at: str
    updated_at: str
    is_draft: bool


def _get_github_client(use_mcp: bool = True):
    """Get GitHub client (MCP or REST)."""
    return MCPGitHubClient() if use_mcp else GitHubClient()


def list_pull_requests(
    config: BatchScanConfig, use_mcp: bool = True
) -> list[PRBatchItem]:
    """
    List pull requests from a repository matching the given criteria.

    Args:
        config: BatchScanConfig with filtering options
        use_mcp: Whether to use MCP client (True) or REST client (False)

    Returns:
        List of PRBatchItem matching the criteria
    """
    client = _get_github_client(use_mcp)

    # Fetch PRs from GitHub
    labels_str = ",".join(config.labels) if config.labels else None
    response = client.list_pull_requests(
        owner=config.owner,
        repo=config.repo,
        state=config.state,
        per_page=config.max_results,
        labels=labels_str,
        sort=config.sort,
        direction=config.direction,
    )

    if not isinstance(response, list):
        raise RuntimeError(f"Unexpected GitHub PRs response: {response}")

    # Filter and transform results
    items: list[PRBatchItem] = []
    for pr_data in response:
        # Skip drafts if configured
        if config.exclude_draft and pr_data.get("draft", False):
            continue

        # Skip PRs with excluded labels
        if config.exclude_labels:
            pr_labels = [label["name"] for label in pr_data.get("labels", [])]
            if any(label in pr_labels for label in config.exclude_labels):
                continue

        items.append(
            PRBatchItem(
                owner=config.owner,
                repo=config.repo,
                number=pr_data["number"],
                title=pr_data.get("title", ""),
                url=pr_data.get("html_url", ""),
                created_at=pr_data.get("created_at", ""),
                updated_at=pr_data.get("updated_at", ""),
                is_draft=pr_data.get("draft", False),
            )
        )

    return items


def run_batch_reviews(
    config: BatchScanConfig,
    run_workflow: Callable[[str, str, int], dict],
    use_mcp: bool = True,
    verbose: bool = True,
) -> dict:
    """
    Run the review workflow on a batch of PRs.

    Args:
        config: BatchScanConfig with repository and filtering options
        run_workflow: Callable(owner, repo, number) -> final_state dict
        use_mcp: Whether to use MCP client (True) or REST client (False)
        verbose: Whether to print progress

    Returns:
        Dict with summary and per-PR results:
        {
            "total": int,
            "reviewed": int,
            "results": [
                {
                    "pr_number": int,
                    "pr_title": str,
                    "pr_url": str,
                    "status": "success" | "error",
                    "risk": str,
                    "summary": str,
                    "error": str (if status == "error")
                }
            ]
        }
    """
    if verbose:
        print(f"\n--- Batch PR Review: {config.owner}/{config.repo} ---\n")

    prs = list_pull_requests(config, use_mcp)
    if verbose:
        print(f"[scan] Found {len(prs)} qualifying PRs\n")

    results = []
    for i, pr in enumerate(prs, 1):
        if verbose:
            print(f"[{i}/{len(prs)}] PR #{pr.number}: {pr.title}")

        try:
            final_state = run_workflow(pr.owner, pr.repo, pr.number)

            classification = final_state.get("classification")
            review_draft = final_state.get("review_draft")
            risk = classification.risk if classification else "unknown"
            summary = review_draft.summary if review_draft else "No review generated"

            result = {
                "pr_number": pr.number,
                "pr_title": pr.title,
                "pr_url": pr.url,
                "status": "success",
                "risk": risk,
                "summary": summary,
                "github_commented": final_state.get("github_comment_posted", False),
            }

            if verbose:
                posted = " (comment posted)" if result["github_commented"] else ""
                print(f"        ✓ risk={risk}{posted}")

            results.append(result)

        except Exception as exc:
            result = {
                "pr_number": pr.number,
                "pr_title": pr.title,
                "pr_url": pr.url,
                "status": "error",
                "error": str(exc),
            }

            if verbose:
                print(f"        ✗ {str(exc)[:60]}...")

            results.append(result)

    if verbose:
        successes = sum(1 for r in results if r["status"] == "success")
        failures = len(results) - successes
        print(f"\n[summary] Reviewed {successes} PRs, {failures} errors\n")

    return {
        "total": len(prs),
        "reviewed": len(results),
        "results": results,
    }
