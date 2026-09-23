from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any, Awaitable, Callable, TypeVar

from mcp import Client, StdioServerParameters


T = TypeVar("T")


def _server_parameters() -> StdioServerParameters:
    """Describe the local MCP server process and pass only required environment variables."""
    env = {
        "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN", ""),
        "GITHUB_API_URL": os.getenv(
            "GITHUB_API_URL",
            "https://api.github.com",
        ),
        "GITHUB_MAX_FILES": os.getenv(
            "GITHUB_MAX_FILES",
            "50",
        ),
        "MCP_LOG_LEVEL": os.getenv(
            "MCP_LOG_LEVEL",
            "WARNING",
        ),
    }

    return StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "smart_pr_review_workflow.mcp.server",
        ],
        env=env,
    )


async def _call_tool(
    client: Client,
    tool_name: str,
    arguments: dict[str, Any],
) -> Any:
    result = await client.call_tool(
        tool_name,
        arguments,
    )

    if result.is_error:
        raise RuntimeError(
            f"MCP tool '{tool_name}' returned an error"
        )

    # Preferred path: structured MCP output.
    if result.structured_content is not None:
        data = result.structured_content

        # MCP SDK may wrap inferred structured output
        # in a top-level "result" field.
        if (
            isinstance(data, dict)
            and set(data.keys()) == {"result"}
        ):
            return data["result"]

        return data

    # Fallback for text-based MCP responses.
    for block in result.content:
        text = getattr(block, "text", None)

        if text is not None:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text

    raise RuntimeError(
        f"MCP tool '{tool_name}' returned no usable content"
    )


class MCPGitHubClient:
    """Small synchronous facade over the official MCP v2 async client."""

    def _run(
        self,
        operation: Callable[[], Awaitable[T]],
    ) -> T:
        """Run one MCP operation from the synchronous LangGraph node layer."""
        return asyncio.run(operation())

    def list_tools(self) -> list[dict[str, str]]:
        async def _list() -> list[dict[str, str]]:
            async with Client(_server_parameters()) as client:
                result = await client.list_tools()

                return [
                    {
                        "name": tool.name,
                        "title": getattr(
                            tool,
                            "title",
                            "",
                        )
                        or "",
                        "description": getattr(
                            tool,
                            "description",
                            "",
                        )
                        or "",
                    }
                    for tool in result.tools
                ]

        return self._run(_list)

    def get_pull_request_bundle(
        self,
        owner: str,
        repo: str,
        number: int,
    ) -> tuple[
        dict[str, Any],
        list[dict[str, Any]],
    ]:
        """Discover MCP tools and use one MCP session for PR metadata + changed files."""

        async def _bundle() -> tuple[
            dict[str, Any],
            list[dict[str, Any]],
        ]:
            async with Client(_server_parameters()) as client:
                tools = await client.list_tools()

                names = {
                    tool.name
                    for tool in tools.tools
                }

                required = {
                    "get_pull_request",
                    "list_pull_request_files",
                }

                missing = required - names

                if missing:
                    raise RuntimeError(
                        "MCP server is missing required tools: "
                        + ", ".join(sorted(missing))
                    )

                pr = await _call_tool(
                    client,
                    "get_pull_request",
                    {
                        "owner": owner,
                        "repo": repo,
                        "number": number,
                    },
                )

                files = await _call_tool(
                    client,
                    "list_pull_request_files",
                    {
                        "owner": owner,
                        "repo": repo,
                        "number": number,
                    },
                )

                return pr, files

        return self._run(_bundle)

    def create_pull_request_comment(
        self,
        owner: str,
        repo: str,
        number: int,
        body: str,
    ) -> dict[str, Any]:
        async def _comment() -> dict[str, Any]:
            async with Client(_server_parameters()) as client:
                result = await _call_tool(
                    client,
                    "create_pull_request_comment",
                    {
                        "owner": owner,
                        "repo": repo,
                        "number": number,
                        "body": body,
                    },
                )

                return result

        return self._run(_comment)