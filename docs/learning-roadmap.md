# Learning Roadmap

```text
Stage 1  StateGraph + State + Nodes
Stage 2  Conditional routing
Stage 3  Send + reducers + parallel work
Stage 4  RAG + evidence
Stage 5  Evaluator + revision loop
Stage 6  Deferred: human-in-the-loop + persistence
Stage 7  GitHub REST tool integration
Stage 8  MCP integration  <-- current
```

## Stage 8 takeaway

The main lesson is not "how to call GitHub with MCP".

It is learning where the integration boundary belongs:

```text
Bedrock  -> reasoning
LangGraph -> workflow
RAG      -> knowledge
MCP      -> capability boundary
GitHub   -> external system
```

## Suggested exercises

1. Run `uv run inspect-mcp` and observe tool discovery.
2. Run the normal workflow with `GITHUB_INTEGRATION=mcp`.
3. Switch to `GITHUB_INTEGRATION=rest` and compare the behavior.
4. Add a fourth MCP tool without changing the graph structure.
5. Change the MCP server from stdio to Streamable HTTP after the local flow is understood.
