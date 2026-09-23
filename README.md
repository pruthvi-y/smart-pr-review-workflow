# Smart PR Review Workflow — Stage 8

A deliberately small LangGraph learning project that reviews a pull request using Amazon Bedrock, local RAG, parallel checks, an evaluator/revision loop, GitHub, and MCP.

This is the final stage of the POC. Human approval, Slack, streaming, and observability are intentionally out of scope for this repository version.

## What the project demonstrates

```text
GitHub PR / Mock PR
        |
        v
    classify_change
        |
        v
     select_checks
        |
        v
  retrieve_knowledge
        |
        v
   Send(...) fan-out
    /      |       \
security  policy  code-quality
    \      |       /
        v
  aggregate results
        |
        v
   generate_review
        |
        v
   evaluate_review
      /        \
    good      revise
      |          |
      v          v
 finalize     revise_review
      |          |
      +----> evaluate_review
      |
      v
post_github_review
      |
      v
     END
```

The workflow remains controlled by LangGraph. The LLM is used for language-heavy decisions; deterministic Python controls routing and termination.

## Stage history

```text
Stage 1  StateGraph + state + nodes
Stage 2  Conditional routing
Stage 3  Parallel execution with Send + reducers
Stage 4  RAG + evidence
Stage 5  Evaluator + revision loop
Stage 6  Deferred: human-in-the-loop + persistence
Stage 7  GitHub REST tool integration
Stage 8  MCP integration  <-- current
```

## Stage 8 goal

Stage 7 used this boundary:

```text
LangGraph -> GitHubClient -> GitHub REST API
```

Stage 8 adds the MCP boundary:

```text
LangGraph -> MCP client -> MCP server -> GitHubClient -> GitHub REST API
```

The same graph can run with either implementation using:

```dotenv
GITHUB_INTEGRATION=mcp
```

or:

```dotenv
GITHUB_INTEGRATION=rest
```

The default is `mcp`.

The GitHub REST path is retained only as a comparison/compatibility mode so the team can see what MCP changes and what it does not change.

## Why MCP is useful here

MCP is a standardized protocol for exposing context and capabilities to applications. The official Python SDK is currently on its v2 stable line and provides a high-level `Client` plus standard transports such as stdio and Streamable HTTP.

This POC uses a local stdio MCP server because it is easy to run and understand. The client launches the MCP server as a subprocess and communicates through stdin/stdout, which is a supported transport in the current SDK.

The current SDK's v2 API uses `MCPServer`; older examples may show `FastMCP`, which was renamed in v2.

## Project structure

```text
smart-pr-review-workflow/
|
├── pyproject.toml
├── uv.lock                     # generate/commit locally with `uv lock`
├── README.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── .env.example
├── .gitignore
├── .python-version
|
├── .github/
│   └── workflows/
│       └── ci.yml
|
├── docs/
│   ├── architecture.md
│   ├── mcp.md
│   └── learning-roadmap.md
|
├── knowledge/
│   ├── security-policy.md
│   ├── dependency-policy.md
│   ├── code-quality.md
│   └── operational-policy.md
|
├── src/
│   └── smart_pr_review_workflow/
│       ├── state.py
│       ├── model.py
│       ├── rag.py
│       ├── index_knowledge.py
│       ├── nodes.py
│       ├── workflow.py
│       ├── main.py
│       ├── tools/
│       │   └── github.py
│       └── mcp/
│           ├── __init__.py
│           ├── server.py
│           ├── client.py
│           └── demo.py
|
└── tests/
    ├── test_mcp_structure.py
    ├── test_github_guards.py
    ├── test_github_tool_structure.py
    ├── test_rag_structure.py
    ├── test_stage5_logic.py
    ├── test_stage7_structure.py
    └── test_workflow_structure.py
```

See `docs/architecture.md` and `docs/mcp.md` for the design and learning notes.

## Requirements

- Python 3.12 or 3.13
- `uv`
- AWS credentials with access to Amazon Bedrock
- A Bedrock chat model/inference profile ID your account can invoke
- For live GitHub mode: a GitHub token with the permissions needed for the selected operations

## Setup

```bash
uv sync
cp .env.example .env
```

Set a valid Bedrock model ID in `.env`. The project intentionally rejects the placeholder value.

For local/mock mode:

```dotenv
GITHUB_ENABLED=false
```

## Prepare RAG index

```bash
uv run index-knowledge
```

The project uses a local vector store for the learning POC so the indexing and retrieval flow stays visible and easy to inspect.

## Run the tests

```bash
uv run pytest
```

## Inspect MCP

This command starts the local MCP server, discovers its tools, and prints them:

```bash
uv run inspect-mcp
```

Expected tools:

```text
get_pull_request
list_pull_request_files
create_pull_request_comment
```

The MCP SDK's current client API exposes `list_tools()` and `call_tool()` through the high-level `Client`.

## Run the mock workflow

```dotenv
GITHUB_ENABLED=false
```

Then:

```bash
uv run run-pr-review
```

No GitHub writes happen in this mode.

## Run against a real GitHub PR using MCP

Configure:

```dotenv
GITHUB_ENABLED=true
GITHUB_INTEGRATION=mcp
GITHUB_OWNER=YOUR_OWNER
GITHUB_REPO=YOUR_REPO
GITHUB_PR_NUMBER=123
GITHUB_TOKEN=YOUR_TOKEN
GITHUB_POST_REVIEW_COMMENT=false
```

Then:

```bash
uv run inspect-mcp
uv run run-pr-review
```

This first reads and reviews the real PR but does not post anything.

After verifying the output, enable:

```dotenv
GITHUB_POST_REVIEW_COMMENT=true
```

and run again.

## Compare MCP with the Stage 7 REST path

Switch only:

```dotenv
GITHUB_INTEGRATION=rest
```

The workflow remains the same. Only the GitHub capability boundary changes.

```text
MCP:
LangGraph -> MCP client -> MCP server -> GitHubClient -> GitHub

REST:
LangGraph -> GitHubClient -> GitHub
```

This comparison is the key Stage 8 exercise.

## MCP server tools

### `get_pull_request`

Reads title, description, URL, and head SHA.

### `list_pull_request_files`

Reads changed files and available patch data.

### `create_pull_request_comment`

Creates a pull-request conversation comment. This remains disabled unless `GITHUB_POST_REVIEW_COMMENT=true`.

The official GitHub API documents pull request file retrieval through the pull request files endpoint and PR conversation comments through the issue-comments API. See the GitHub REST API documentation.

## Security and repository hygiene

- `.env` is ignored by Git.
- GitHub commenting is opt-in.
- The MCP subprocess receives only the environment variables it needs for GitHub access.
- The MCP server keeps protocol traffic on stdout and sends logs to stderr.
- Prompt input from large PRs is bounded before it reaches Bedrock.
- No GitHub write occurs during the default read-only configuration.

## Dependency management

Use `uv` for dependency updates:

```bash
uv add mcp
uv lock
uv sync
```

Commit `uv.lock` to Git so local development and CI resolve the same dependency graph.

## CI

A small GitHub Actions workflow runs `uv sync` and `uv run pytest` on pushes and pull requests. No AWS or GitHub secrets are required by the test suite.

## Deliberately excluded

This final POC does not add:

- Human approval workflows
- Slack notifications
- Streaming UI
- Production observability
- Multi-agent architecture
- Deployment infrastructure

Those are useful production concerns, but they would add complexity without improving the core LangGraph + MCP learning objective of this repository.

## Official references

- MCP Python SDK v2: https://py.sdk.modelcontextprotocol.io/
- MCP Python client: https://py.sdk.modelcontextprotocol.io/client/
- MCP transports: https://py.sdk.modelcontextprotocol.io/v2/hi/client/transports/
- MCP v1-to-v2 migration: https://py.sdk.modelcontextprotocol.io/uk/migration/
- LangGraph Graph API: https://docs.langchain.com/oss/python/langgraph/graph-api
