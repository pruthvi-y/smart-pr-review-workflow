from __future__ import annotations

import os

from .client import MCPGitHubClient


def main() -> None:
    """List the tools exposed by the local MCP server and optionally call a read-only tool."""
    print("\n--- MCP Server Inspection ---\n")
    client = MCPGitHubClient()
    tools = client.list_tools()

    print("Discovered tools:")
    for tool in tools:
        print(f"- {tool['name']}: {tool['description']}")

    if os.getenv("GITHUB_ENABLED", "false").lower() != "true":
        print("\nGITHUB_ENABLED=false, so no live MCP tool call was made.")
        return

    owner = os.getenv("GITHUB_OWNER")
    repo = os.getenv("GITHUB_REPO")
    number = os.getenv("GITHUB_PR_NUMBER")
    if not owner or not repo or not number:
        raise RuntimeError("GITHUB_OWNER, GITHUB_REPO, and GITHUB_PR_NUMBER are required.")

    pr = client.get_pull_request(owner, repo, int(number))
    print(f"\nMCP read succeeded: {pr['html_url']}")


if __name__ == "__main__":
    main()
