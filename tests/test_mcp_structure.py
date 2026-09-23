import asyncio

from mcp import Client

from smart_pr_review_workflow.mcp.server import mcp
from smart_pr_review_workflow.nodes import _github_integration


def test_mcp_server_exposes_expected_tools():
    async def _list():
        async with Client(mcp) as client:
            result = await client.list_tools()
            return {tool.name for tool in result.tools}

    names = asyncio.run(_list())
    assert {
        "get_pull_request",
        "list_pull_request_files",
        "create_pull_request_comment",
    } <= names


def test_github_integration_defaults_to_mcp(monkeypatch):
    monkeypatch.delenv("GITHUB_INTEGRATION", raising=False)
    assert _github_integration() == "mcp"


def test_github_integration_rejects_unknown_mode(monkeypatch):
    monkeypatch.setenv("GITHUB_INTEGRATION", "unknown")
    try:
        _github_integration()
    except RuntimeError as exc:
        assert "mcp" in str(exc)
    else:
        raise AssertionError("Expected invalid integration mode to raise")
