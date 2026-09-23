# Contributing

## Local setup

```bash
uv sync
uv run pytest
```

Create `.env` from `.env.example` and keep secrets out of Git.

## Before opening a PR

```bash
uv run pytest
uv run inspect-mcp
```

For changes to the graph, update the related tests and learning notes when the workflow behavior changes.

## Dependency updates

Use `uv add` / `uv remove` and commit the resulting `uv.lock` when dependency versions are changed.
