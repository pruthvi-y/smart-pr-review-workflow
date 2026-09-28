# Batch PR Scanning

Automated batch scanning allows you to review multiple PRs from a repository without specifying each PR number individually. The batch mode lists qualifying PRs and runs the review workflow for each one.

## Quick Start

### Review all open PRs from a repo

```bash
export GITHUB_ENABLED=true
export GITHUB_TOKEN=<your-token>
export AWS_REGION=us-east-1
export BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

uv run run-pr-review --batch --owner myorg --repo my-repo
```

This lists the 10 most recently created open PRs and reviews each one.

### Post reviews to GitHub

```bash
export GITHUB_POST_REVIEW_COMMENT=true
uv run run-pr-review --batch --owner myorg --repo my-repo
```

Each PR gets a comment with the generated review.

## CLI Options

### Core Arguments

- `--batch` — Enable batch mode (default: single PR mode)
- `--owner <org>` — Repository owner (or use `GITHUB_OWNER` env var)
- `--repo <name>` — Repository name (or use `GITHUB_REPO` env var)

### Filtering

- `--labels <label1,label2>` — Only review PRs with these labels
- `--exclude-labels <label1,label2>` — Skip PRs with these labels
- `--state {open|closed|all}` — PR state filter (default: `open`)

### Sorting & Pagination

- `--sort {created|updated|popularity}` — Sort order (default: `created`)
- `--max-results <n>` — Maximum PRs to review (default: 10)
- `--no-exclude-draft` — Include draft PRs (by default excluded)

### Output

- `--quiet` — Suppress progress output (useful for CI)

## Examples

### Review recent security-related PRs

```bash
uv run run-pr-review --batch \
  --owner myorg \
  --repo backend \
  --labels "type:security" \
  --max-results 20
```

### Review all PRs, skip WIP

```bash
uv run run-pr-review --batch \
  --owner myorg \
  --repo frontend \
  --exclude-labels "wip,hold" \
  --max-results 50
```

### Recently updated PRs (for reviews in flight)

```bash
uv run run-pr-review --batch \
  --owner myorg \
  --repo api \
  --sort updated \
  --state open \
  --max-results 5
```

### All closed PRs (retrospective review)

```bash
uv run run-pr-review --batch \
  --owner myorg \
  --repo infrastructure \
  --state closed \
  --max-results 100
```

### Scheduled batch job (CI/cron)

```bash
uv run run-pr-review --batch \
  --owner myorg \
  --repo services \
  --labels "type:dependency" \
  --quiet
```

## Output Format

Progress output shows each PR as it's reviewed:

```
--- Batch PR Review: myorg/repo ---

[scan] Found 5 qualifying PRs

[1/5] PR #123: Upgrade Jackson dependency
        ✓ risk=high (comment posted)
[2/5] PR #124: Fix race condition
        ✓ risk=medium
[3/5] PR #125: Add observability
        ✓ risk=low
[4/5] PR #126: Refactor auth
        ✗ GitHub API rate limit exceeded...
[5/5] PR #127: Update dependencies
        ✓ risk=medium (comment posted)

[summary] Reviewed 4 PRs, 1 errors
```

With `--quiet`, only summary is printed.

## Integration with GitHub Actions

Create a workflow file (`.github/workflows/batch-review.yml`):

```yaml
name: Batch PR Review

on:
  workflow_dispatch:
    inputs:
      labels:
        description: 'Comma-separated labels filter (optional)'
        required: false
  schedule:
    - cron: '0 9 * * MON'  # Every Monday at 9 AM

jobs:
  batch-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: prefix-dev/setup-uv@v0
      - run: uv sync

      - name: Run batch PR review
        env:
          GITHUB_ENABLED: 'true'
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_OWNER: ${{ github.repository_owner }}
          GITHUB_REPO: ${{ github.event.repository.name }}
          AWS_REGION: us-east-1
          BEDROCK_MODEL_ID: anthropic.claude-3-sonnet-20240229-v1:0
          GITHUB_POST_REVIEW_COMMENT: 'true'
        run: |
          uv run run-pr-review --batch \
            --labels "${{ github.event.inputs.labels }}" \
            --max-results 20 \
            --sort updated
```

Trigger manually or on schedule to run automated reviews across your repo.

## Cron Job Setup (Local)

To run batch reviews periodically on your machine:

```bash
# Every weekday at 10 AM
0 10 * * MON-FRI /usr/local/bin/batch-pr-review.sh
```

Create `/usr/local/bin/batch-pr-review.sh`:

```bash
#!/bin/bash
set -e

cd /path/to/stage8-build
export $(cat .env | xargs)

uv run run-pr-review --batch \
  --owner myorg \
  --repo myrepo \
  --labels "type:dependency" \
  --max-results 10
```

## Comparison with Single PR Mode

| Mode | Use Case | Command |
|------|----------|---------|
| **Single** | Review one PR at a time | `uv run run-pr-review --owner org --repo repo --pr 123` |
| **Batch** | Automate reviews across multiple PRs | `uv run run-pr-review --batch --owner org --repo repo --max-results 20` |
| **Mock** | Test without GitHub | `uv run run-pr-review` (no args) |

## Environment Variables

Batch mode respects the same environment variables as single PR mode:

- `GITHUB_ENABLED` — Enable GitHub integration
- `GITHUB_TOKEN` — GitHub API token
- `GITHUB_OWNER` / `GITHUB_REPO` — Repository (can also use `--owner` / `--repo` flags)
- `GITHUB_INTEGRATION` — `mcp` (default) or `rest`
- `GITHUB_POST_REVIEW_COMMENT` — Post reviews as PR comments
- `AWS_REGION` — AWS region for Bedrock
- `BEDROCK_MODEL_ID` — Bedrock model ID

## Error Handling

If a PR review fails:

- The batch continues with remaining PRs
- A summary of errors is printed at the end
- Individual errors (e.g., API rate limits, network timeouts) are logged

Example:

```
[4/10] PR #200: Add metrics endpoint
        ✗ GitHub API error: HTTP 403 for GET /repos/org/repo: API rate limit exceeded
```

To handle rate limits, reduce `--max-results` or add a delay between batch runs.

## Filtering Strategies

### Review only dependency updates

```bash
uv run run-pr-review --batch \
  --owner myorg \
  --repo api \
  --labels "type:dependency" \
  --state open
```

### Security reviews

```bash
uv run run-pr-review --batch \
  --owner myorg \
  --repo services \
  --labels "type:security" \
  --max-results 50
```

### Exclude known noise

```bash
uv run run-pr-review --batch \
  --owner myorg \
  --repo web \
  --exclude-labels "documentation,chore,wip,on-hold" \
  --max-results 30
```

### Review recently updated (in-flight) PRs

```bash
uv run run-pr-review --batch \
  --owner myorg \
  --repo backend \
  --sort updated \
  --max-results 10
```

## Performance Considerations

- Each PR review takes time proportional to its diff size and complexity
- Parallel execution: Batch mode runs PRs sequentially (one at a time)
- RAG indexing is cached: The knowledge base is indexed once at startup, reused for all PRs
- Recommendation: Start with `--max-results 5` and increase as needed

For very large batches (100+ PRs), consider:
- Running in CI/cron during off-hours
- Filtering by labels to reduce scope
- Splitting into multiple smaller batches with different label filters
