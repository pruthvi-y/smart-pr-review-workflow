# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **smart PR review workflow** — a learning project demonstrating LangGraph orchestration with Amazon Bedrock, local RAG, parallel parallel execution, GitHub integration via MCP (Model Context Protocol), and an evaluator/revision loop.

The workflow classifies PRs, retrieves relevant engineering policies, runs specialized checks (security, code quality, policy, operational), generates a review, evaluates it for quality, revises if needed, and optionally posts to GitHub.

This is **Stage 8** of the POC learning sequence. Stages 1-7 built up foundational patterns (state graphs, conditional routing, parallelism, RAG, evaluation, GitHub REST). Stage 8 adds MCP as the GitHub capability boundary, keeping the Stage 7 REST path as a compatibility mode for comparison.

## Key Architecture

```
LangGraph (orchestration, state, routing)
    ├── Bedrock (LLM: classify, analyze, generate, evaluate)
    ├── Local RAG (retrieve engineering policies)
    └── MCP Client (standardized tool boundary)
        └── MCP Server (stdio transport)
            └── GitHub REST API (read PRs, post comments)
```

### Central Concepts

- **State**: `PRState` (see `src/smart_pr_review_workflow/state.py`) is a TypedDict that flows through the graph. It holds PR metadata, classification, check results, review drafts, and evaluation decisions. Fields are `total=False` and use reducers (`Annotated[..., operator.add]`) for accumulated results.

- **Workflow**: Built with `StateGraph` and compiled. Nodes perform transformations; conditional edges route based on state. The `Send()` function (LangGraph 0.1.21+) maps `fan_out_checks` across multiple check types in parallel.

- **MCP vs REST**: Both paths coexist. Set `GITHUB_INTEGRATION=mcp` (default, Stage 8) or `rest` (Stage 7 compatibility). Only the GitHub capability boundary changes; business logic remains identical.

- **Evaluator loop**: `evaluate_review` → `revise_review` → `evaluate_review` until the review meets quality gates or `max_revision_attempts` is hit.

## Common Commands

All commands use `uv`:

```bash
# Install/sync dependencies
uv sync

# Run tests (includes structure, logic, and tool tests)
uv run pytest

# Inspect the MCP server: list tools, schemas, verify discovery
uv run inspect-mcp

# Prepare RAG: index knowledge base into local Chroma vector store
uv run index-knowledge

# Run mock workflow (no GitHub writes)
# Set GITHUB_ENABLED=false first
uv run run-pr-review

# Run against a real PR (dry-run or write)
# Set GITHUB_ENABLED=true, GITHUB_OWNER, GITHUB_REPO, GITHUB_PR_NUMBER, GITHUB_TOKEN
# Set GITHUB_INTEGRATION=mcp (default) or rest
# Set GITHUB_POST_REVIEW_COMMENT=false for dry-run, true to post
uv run inspect-mcp
uv run run-pr-review
```

## Project Structure

```
src/smart_pr_review_workflow/
├── state.py              # PRState TypedDict, data models (Pydantic)
├── workflow.py           # StateGraph builder + compilation
├── nodes.py              # 10 graph nodes (load_pr, classify_change, …, post_github_review)
├── model.py              # Bedrock client initialization
├── rag.py                # Local Chroma vector store, retrieval
├── main.py               # Entry point (CLI + environment setup)
├── index_knowledge.py    # Index knowledge/ into Chroma
├── tools/
│   └── github.py         # GitHubClient (Stage 7 REST path)
└── mcp/
    ├── server.py         # MCPServer: expose GitHub tools (stdio)
    ├── client.py         # MCPClient: call MCP server tools
    └── demo.py           # inspect-mcp: list and print tools

tests/
├── test_mcp_structure.py           # MCP server registration, tool discovery
├── test_github_guards.py           # Environment/credential guards
├── test_github_tool_structure.py   # GitHub tool schema, guards
├── test_rag_structure.py           # RAG initialization
├── test_stage5_logic.py            # Evaluator + revision loop
├── test_stage7_structure.py        # REST client shape
└── test_workflow_structure.py      # Graph edges, node existence

knowledge/
├── security-policy.md         # Dependency and security-sensitive change rules
├── code-quality.md            # PR quality, evidence standards
├── dependency-policy.md       # Dependency management
└── operational-policy.md      # (not yet detailed in current version)
```

## Key Dependencies

- **LangGraph** (1.2+): orchestration, StateGraph, Send, routing
- **Pydantic** (2.x): data models with validation
- **mcp** (2.x): MCP Python SDK v2 (MCPServer, Client, stdio transport)
- **langchain-aws** (1.2+): Bedrock integration
- **langchain-chroma** (0.2+): local vector store
- **python-dotenv**: environment variables from `.env`
- **pytest** (dev): test suite (no AWS/GitHub credentials required)

## Environment Setup

Copy `.env.example` to `.env` and set:

- **AWS credentials**: `AWS_REGION`, `AWS_PROFILE`, `BEDROCK_MODEL_ID` (required; placeholder is rejected)
- **GitHub** (optional): `GITHUB_ENABLED` (false by default), `GITHUB_OWNER`, `GITHUB_REPO`, `GITHUB_PR_NUMBER`, `GITHUB_TOKEN`
- **Integration mode**: `GITHUB_INTEGRATION=mcp` (Stage 8) or `rest` (Stage 7)
- **Safety**: `GITHUB_POST_REVIEW_COMMENT=false` until ready to post

## Important Patterns

### LangGraph + MCP Integration

The MCP client is initialized in `mcp/client.py` with a `StdioServerParameters` transport. The client `list_tools()` to discover capabilities, then `call_tool()` to invoke them. Nodes in the workflow use the client directly:

```python
# In a node
from mcp.client import MCPClient
client = MCPClient(...)
tools = await client.list_tools()
result = await client.call_tool("get_pull_request", {...})
```

### State Reducers

The `analysis_results` field uses `Annotated[list[PRCheckResult], operator.add]` so parallel checks accumulate rather than overwrite:

```python
analysis_results: Annotated[list[PRCheckResult], operator.add]
```

`Send()` spreads the check names across parallel tasks; each returns a dict with the check result; the reducer concatenates them.

### Evaluation & Revision

The `evaluate_review` node decides "approve_draft" or "revise". If "revise", `revise_review` regenerates, then loops back to `evaluate_review` with an incremented `revision_count`. After `max_revision_attempts`, the loop terminates and moves to `finalize_review` → `post_github_review`.

## Testing

All tests run without AWS or GitHub credentials:

```bash
uv run pytest                    # Run all
uv run pytest tests/test_rag_structure.py -v   # Single file, verbose
uv run pytest tests/test_stage5_logic.py::test_name   # Single test
```

Tests verify:
- MCP server registration and tool discovery
- GitHub tool schema and environment guards
- RAG initialization (local Chroma)
- Evaluator loop logic
- Workflow graph structure (edges, node existence)

When changing graph structure, check the relevant test; when workflow behavior changes, update tests and learning notes in `docs/`.

## GitHub Integration: MCP vs REST

**MCP (Stage 8, default):**
```
LangGraph → MCP client → MCP server (stdio) → GitHubClient → GitHub REST API
```

**REST (Stage 7, compatibility):**
```
LangGraph → GitHubClient → GitHub REST API
```

To compare, run once with each `GITHUB_INTEGRATION` setting. The graph logic is identical; only the capability boundary changes.

**Tool security:**
- The MCP subprocess is spawned with only the environment variables it needs (`GITHUB_TOKEN`, etc.)
- Protocol traffic uses stdout; logs go to stderr only
- GitHub commenting is opt-in via `GITHUB_POST_REVIEW_COMMENT`
- Default config is read-only (no writes without explicit opt-in)

## Policies

Refer to `knowledge/` for engineering standards:

- **security-policy.md**: Dependency updates require vulnerability review; security-sensitive changes need evidence; no secrets in PRs.
- **code-quality.md**: Changes must be focused, understandable, tested; review comments should cite code, not speculation.
- **dependency-policy.md**: Use `uv add`/`uv remove` and commit `uv.lock`.

## Learning Sequence

This is the **final stage** of the POC. Deliberately excluded: human approval, Slack notifications, streaming UI, production observability, multi-agent, deployment. Those are useful in production but not needed for the LangGraph + MCP learning goal.

Refer to:
- `README.md`: setup, run modes, MCP server tools
- `docs/architecture.md`: system diagram, responsibilities, Stage 7 vs 8
- `docs/mcp.md`: MCP design lessons (stdio, workflow vs capability boundary, official references)
- `docs/learning-roadmap.md`: (if present) further learning suggestions
