from __future__ import annotations

import logging
import os

from ..tools.github import GitHubClient
from mcp.server.mcpserver import MCPServer

logger = logging.getLogger(__name__)

mcp = MCPServer(
    "smart-pr-review-github",
    instructions=(
        "Expose GitHub pull-request capabilities for the Smart PR Review Workflow. "
        "Tools are read-only except for the explicit pull-request comment operation."
    ),
)


def _github() -> GitHubClient:
    return GitHubClient()


@mcp.tool()
def get_pull_request(owner: str, repo: str, number: int) -> dict:
    """Get pull-request metadata from GitHub as structured MCP output."""
    result = _github().get_pull_request(owner, repo, number)

    return {
        "owner": owner,
        "repo": repo,
        "number": number,
        "title": result.get("title", ""),
        "body": result.get("body") or "",
        "html_url": result.get("html_url", ""),
        "head_sha": ((result.get("head") or {}).get("sha")) or "",
    }


@mcp.tool()
def list_pull_request_files(owner: str, repo: str, number: int) -> list[dict]:
    """List changed files for a pull request, including available patch text."""
    result = _github().list_pull_request_files(owner, repo, number)

    return [
        {
            "filename": item.get("filename", ""),
            "status": item.get("status", ""),
            "additions": item.get("additions", 0),
            "deletions": item.get("deletions", 0),
            "patch": item.get("patch") or "",
        }
        for item in result
    ]


@mcp.tool()
def create_pull_request_comment(
    owner: str,
    repo: str,
    number: int,
    body: str,
) -> dict:
    """Post a conversation comment on a GitHub pull request."""
    result = _github().create_pull_request_comment(owner, repo, number, body)

    return {
        "id": result.get("id"),
        "html_url": result.get("html_url", ""),
    }


def main() -> None:
    """Run the MCP server over stdio. Keep protocol output off stdout."""
    logging.basicConfig(level=os.getenv("MCP_LOG_LEVEL", "WARNING"))
    logger.info("Starting Smart PR Review GitHub MCP server")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
