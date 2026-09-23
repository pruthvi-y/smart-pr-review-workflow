# Architecture

## Stage 8

```text
                    +----------------------+
                    |    Amazon Bedrock     |
                    |  chat + embeddings    |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    |      LangGraph        |
                    | state + orchestration |
                    +----+-------------+----+
                         |             |
                    RAG  |             | MCP client
                         |             |
                         v             v
                 +-------------+   +------------+
                 | Local vector|   | MCP server |
                 |    store    |   |  (stdio)   |
                 +-------------+   +------+-----+
                                         |
                                         v
                                    GitHub REST
```

### Responsibilities

- **LangGraph**: owns state, routing, parallel branches, evaluation, revision, and workflow sequencing.
- **Bedrock**: classification, specialist analysis, review generation, evaluation, and revision.
- **RAG**: supplies project-specific engineering policy and evidence.
- **MCP client**: connects the application to an MCP server using the MCP protocol.
- **MCP server**: exposes GitHub capabilities as standardized tools.
- **GitHub REST API**: remains the system that actually stores the pull request and comments.

## Stage 7 vs Stage 8

```text
Stage 7
LangGraph -> GitHubClient -> GitHub REST API

Stage 8
LangGraph -> MCP client -> MCP server -> GitHubClient -> GitHub REST API
```

The GitHub REST implementation is retained as a compatibility mode so the team can compare both integration styles.
