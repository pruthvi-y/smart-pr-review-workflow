# MCP Learning Notes

## What MCP adds

MCP standardizes how an application discovers and invokes capabilities exposed by another process or service. The official Python SDK currently has v2 as its stable release line and supports stdio, Streamable HTTP, and SSE transports. For a local POC, stdio keeps the setup simple: the client launches the MCP server as a subprocess and communicates over stdin/stdout. citeturn205477search5turn205477search1

## What this project demonstrates

```text
LangGraph node
    |
    v
MCP client
    |
    | list_tools / call_tool
    v
MCP server
    |
    v
GitHubClient
    |
    v
GitHub REST API
```

The MCP server exposes three tools:

- `get_pull_request`
- `list_pull_request_files`
- `create_pull_request_comment`

The local server uses the current v2 API shape (`MCPServer`) rather than older v1 examples (`FastMCP`). The official SDK migration guide notes that `FastMCP` was renamed to `MCPServer` in v2.

## Why stdio first

Stdio avoids running another network service during local development. The official v2 client supports `Client(StdioServerParameters(...))` for this pattern. citeturn205477search0turn205477search1

Later, the same MCP interface can be moved to Streamable HTTP. The current SDK recommends Streamable HTTP for deployed clients.

## A key architectural lesson

MCP does **not** replace LangGraph.

```text
LangGraph = workflow/orchestration
MCP       = standardized capability/tool boundary
GitHub    = external system
```

Keep business workflow decisions in LangGraph. Keep external-system capabilities behind tools/MCP.

## Official references

- MCP Python SDK v2: https://py.sdk.modelcontextprotocol.io/
- MCP Python client: https://py.sdk.modelcontextprotocol.io/client/
- MCP client transports: https://py.sdk.modelcontextprotocol.io/v2/hi/client/transports/
- MCP v1-to-v2 migration: https://py.sdk.modelcontextprotocol.io/uk/migration/
