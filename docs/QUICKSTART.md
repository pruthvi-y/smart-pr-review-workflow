# Quick Start Guide: Smart PR Review Workflow

Complete step-by-step guide to set up and run the Smart PR Review Workflow project.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Test Setup](#test-setup)
4. [Run Mock Mode](#run-mock-mode)
5. [Run Single PR Review](#run-single-pr-review)
6. [Run Batch Scanning](#run-batch-scanning)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

You need:

- **Python 3.12+** — Check with `python3 --version`
- **uv** — Package manager. Install with `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Git** — For version control
- **AWS Account** — With Bedrock access
- **GitHub Token** — For GitHub integration (optional, for testing)

### Check Prerequisites

```bash
python3 --version      # Should show 3.12.x or higher
uv --version          # Should show latest version
git --version         # Should be available
aws --version         # Optional, but good to have
```

---

## Initial Setup

### Step 1: Clone or Navigate to Project

```bash
# If you don't have the project yet
git clone https://github.com/your-org/stage8-build.git
cd stage8-build

# Or navigate to existing project
cd /Users/pruthviy/projects/stage8-build
```

### Step 2: Install Dependencies

```bash
uv sync
```

This installs all Python dependencies listed in `pyproject.toml`.

### Step 3: Prepare Environment Configuration

```bash
# Copy the example environment file
cp .env.example .env

# Open and edit .env
nano .env
# or
code .env
```

### Step 4: Configure `.env` File

Required settings:

```bash
# AWS Bedrock Configuration (Required)
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# GitHub Configuration (Required for GitHub mode)
GITHUB_ENABLED=false              # Start with false for testing
GITHUB_TOKEN=                     # Leave empty for now
GITHUB_OWNER=                     # Leave empty for now
GITHUB_REPO=                      # Leave empty for now
GITHUB_INTEGRATION=mcp            # Use MCP (default) or rest
GITHUB_POST_REVIEW_COMMENT=false  # Never auto-post, set true only after testing

# AWS Credentials (Set via command or ~/.aws/credentials)
# Option A: Via .env (not recommended for secrets)
# AWS_ACCESS_KEY_ID=your_key
# AWS_SECRET_ACCESS_KEY=your_secret

# Option B: Use AWS CLI configuration
# aws configure --profile default
```

### Step 5: Verify AWS Credentials

```bash
# Check AWS configuration
aws sts get-caller-identity --region us-east-1

# Should output something like:
# {
#     "UserId": "AIDAI...",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/username"
# }
```

If this fails, configure AWS:

```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Enter default region: us-east-1
# Enter default output format: json
```

### Step 6: Index Knowledge Base

```bash
uv run index-knowledge
```

Output should show:
```
[rag] Indexing knowledge base...
[rag] Indexed 150+ policy chunks into local Chroma vector store
```

This creates a local vector database from policy files in the `knowledge/` directory.

---

## Test Setup

### Step 1: Run Tests

```bash
uv run pytest
```

Should output:
```
======================== 17 passed in 0.60s ========================
```

All 17 tests should pass without AWS or GitHub credentials.

### Step 2: Inspect MCP Server

```bash
uv run inspect-mcp
```

Should list GitHub tools available through MCP:
```
Tool: get_pull_request
Tool: list_pull_request_files
Tool: create_pull_request_comment
```

### Step 3: Verify CLI Help

```bash
uv run run-pr-review --help
```

Should show all available options including batch mode flags.

---

## Run Mock Mode

Test without any GitHub or AWS calls (fully local).

### Step 1: Set Environment

```bash
# Already set in .env by default
export GITHUB_ENABLED=false
```

### Step 2: Run Workflow

```bash
uv run run-pr-review
```

### Expected Output

```
--- Running Smart PR Review Workflow: Stage 8 ---

[source] mock PR
[rag] Loading local knowledge index...
[rag] index_ready chunks=150
[classify] type=dependency, risk=high
[plan] route=security_review
       checks=[security, policy]
[rag] retrieved=5 chunks
      sources=security-policy.md, dependency-policy.md
[parallel check completed] security
[parallel check completed] policy
[review] draft generated
[evaluator] decision=approve_draft grounded=True complete=True actionable=True risk_consistent=True

--- Final Result ---

Change type : dependency
Initial risk: high
Route       : security_review
Checks      : security, policy
RAG chunks  : 5
Revisions   : 0
GitHub      : False
Integration : mock
Commented   : False

[Review draft text appears here...]
```

This demonstrates the full workflow without external dependencies.

---

## Run Single PR Review

Review one specific PR from GitHub.

### Prerequisites

- Valid AWS Bedrock credentials
- GitHub repository access
- GitHub token with `repo:read` permission

### Step 1: Create GitHub Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Name it: `smart-pr-review`
4. Select scopes: `repo` (full control)
5. Click "Generate token"
6. Copy the token (you won't see it again)

### Step 2: Update `.env`

```bash
GITHUB_ENABLED=true
GITHUB_OWNER=anthropics
GITHUB_REPO=claude-code
GITHUB_PR_NUMBER=123
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
GITHUB_POST_REVIEW_COMMENT=false
GITHUB_INTEGRATION=mcp
```

Replace values with your actual repository.

### Step 3: Verify MCP Can Connect

```bash
uv run inspect-mcp
```

Should successfully list GitHub tools (proves MCP connection works).

### Step 4: Run Dry-Run Review

```bash
uv run run-pr-review
```

This reads the PR and generates a review but doesn't post anything.

### Step 5: Review the Output

Check that:
- PR loaded successfully
- Classification looks correct
- Checks ran and found results
- Review draft is sensible

### Step 6: Post Review (Optional)

Only after verifying the output looks good:

```bash
# Update .env
GITHUB_POST_REVIEW_COMMENT=true
```

Then run again:

```bash
uv run run-pr-review
```

The review comment will be posted to the PR.

---

## Run Batch Scanning

Review multiple PRs automatically without specifying each PR number.

### Scenario A: Test Batch Mode (Mock)

No GitHub credentials needed:

```bash
uv run run-pr-review --batch --owner test --repo test --quiet
```

### Scenario B: Scan Real Repository (Dry-run)

```bash
# Make sure GITHUB_POST_REVIEW_COMMENT=false in .env

uv run run-pr-review --batch \
  --owner anthropics \
  --repo claude-code \
  --max-results 5
```

Replace `anthropics/claude-code` with your repository.

### Scenario C: Review Only Security PRs

```bash
uv run run-pr-review --batch \
  --owner anthropics \
  --repo claude-code \
  --labels "type:security" \
  --max-results 10
```

### Scenario D: Skip WIP/On-Hold PRs

```bash
uv run run-pr-review --batch \
  --owner anthropics \
  --repo claude-code \
  --exclude-labels "wip,on-hold,draft" \
  --max-results 20
```

### Scenario E: Review Recently Updated PRs

```bash
uv run run-pr-review --batch \
  --owner anthropics \
  --repo claude-code \
  --sort updated \
  --max-results 5
```

### Scenario F: Post Reviews to GitHub

After verifying output from dry-run:

```bash
# Update .env
GITHUB_POST_REVIEW_COMMENT=true

# Run batch
uv run run-pr-review --batch \
  --owner anthropics \
  --repo claude-code \
  --max-results 5
```

Each PR gets a comment with the review.

### Scenario G: Mark as Reviewed and Avoid Re-reviewing

After first batch run, you can mark PRs as reviewed and skip them next time:

```bash
# Only review PRs NOT labeled "reviewed"
uv run run-pr-review --batch \
  --owner anthropics \
  --repo claude-code \
  --exclude-labels "reviewed" \
  --max-results 20
```

Then, when posting reviews, manually add the "reviewed" label to each PR (or automate it).

### Scenario H: Quiet Mode for CI/Cron

Suppress progress output:

```bash
uv run run-pr-review --batch \
  --owner anthropics \
  --repo claude-code \
  --quiet
```

---

## Batch Scanning Reference

### All Available Options

```bash
uv run run-pr-review --batch [OPTIONS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--owner` | GitHub repository owner | `$GITHUB_OWNER` env var |
| `--repo` | GitHub repository name | `$GITHUB_REPO` env var |
| `--labels` | Include PRs with these labels (comma-separated) | None |
| `--exclude-labels` | Exclude PRs with these labels (comma-separated) | None |
| `--max-results` | Maximum number of PRs to review | 10 |
| `--state` | PR state: `open`, `closed`, or `all` | `open` |
| `--sort` | Sort by: `created`, `updated`, or `popularity` | `created` |
| `--no-exclude-draft` | Include draft PRs (default: excluded) | Exclude drafts |
| `--quiet` | Suppress progress output | Verbose |

### Common Batch Commands

```bash
# All open PRs (default)
uv run run-pr-review --batch --owner org --repo repo

# Recently updated PRs (good for in-flight reviews)
uv run run-pr-review --batch --owner org --repo repo --sort updated

# Security-related PRs
uv run run-pr-review --batch --owner org --repo repo --labels "type:security"

# Dependencies only
uv run run-pr-review --batch --owner org --repo repo --labels "type:dependency"

# Skip WIP/draft/hold
uv run run-pr-review --batch --owner org --repo repo \
  --exclude-labels "wip,draft,on-hold"

# All closed PRs (retrospective)
uv run run-pr-review --batch --owner org --repo repo --state closed

# Limited batch (good for testing)
uv run run-pr-review --batch --owner org --repo repo --max-results 3 --quiet

# Multiple filters
uv run run-pr-review --batch --owner org --repo repo \
  --labels "type:dependency" \
  --exclude-labels "wip,hold" \
  --sort updated \
  --max-results 10
```

---

## Troubleshooting

### Problem: Python Version Error

```
Error: Python 3.12+ required, found 3.11.x
```

**Solution:**
```bash
python3.12 --version
uv python install 3.12
uv sync
```

### Problem: AWS Credentials Not Found

```
Error: Unable to locate credentials
```

**Solution:**
```bash
aws configure
# Enter your AWS Access Key ID and Secret Access Key
# Then test:
aws sts get-caller-identity
```

### Problem: Bedrock Model Not Available

```
Error: Model anthropic.claude-3-sonnet-20240229-v1:0 not available in region
```

**Solution:**
- Check available models: https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html
- Update `BEDROCK_MODEL_ID` in `.env` with available model for your region
- Try changing `AWS_REGION`

### Problem: GitHub Token Invalid

```
Error: GitHub API error: HTTP 401 Unauthorized
```

**Solution:**
```bash
# Create new token
# 1. Go to https://github.com/settings/tokens
# 2. Generate new token (classic)
# 3. Select "repo" scope
# 4. Update GITHUB_TOKEN in .env
```

### Problem: GitHub API Rate Limit

```
Error: GitHub API error: HTTP 403 API rate limit exceeded
```

**Solution:**
- Reduce `--max-results` in batch mode
- Wait 1 hour for rate limit reset
- Use authenticated token (if not already)

### Problem: Knowledge Base Not Indexed

```
Error: Knowledge base not found
```

**Solution:**
```bash
uv run index-knowledge
# Should show: "[rag] Indexed X chunks into local Chroma vector store"
```

### Problem: MCP Server Won't Start

```
Error: Failed to start MCP server
```

**Solution:**
```bash
# Verify MCP tools are exposed
uv run inspect-mcp

# If fails, check Python dependencies
uv sync --all-groups

# Try running MCP server directly
uv run python -m smart_pr_review_workflow.mcp.server
```

### Problem: Tests Fail

```
ERROR: test_something.py FAILED
```

**Solution:**
```bash
# Re-sync dependencies
uv sync

# Run tests with verbose output
uv run pytest -v

# Run single test for debugging
uv run pytest tests/test_batch_scanning.py -v
```

### Problem: CLI Options Not Recognized

```
Error: unrecognized arguments: --batch
```

**Solution:**
```bash
# Verify you're using latest code
git pull
uv sync

# Check help
uv run run-pr-review --help
```

---

## Workflow Diagrams

### Mock Mode Flow

```
uv run run-pr-review
    ↓
Load Mock PR
    ↓
Classify (LLM)
    ↓
Select Checks
    ↓
Retrieve Policies (Local RAG)
    ↓
Run Checks in Parallel (LLM)
    ↓
Generate Review (LLM)
    ↓
Evaluate Review (LLM)
    ↓
Print Final Review
```

### Single PR Mode Flow

```
uv run run-pr-review --owner org --repo repo --pr 123
    ↓
Load PR from GitHub (MCP/REST)
    ↓
[Same as mock mode above]
    ↓
Post Review to GitHub (if enabled)
```

### Batch Mode Flow

```
uv run run-pr-review --batch --owner org --repo repo
    ↓
List PRs from GitHub (with filters)
    ↓
For Each PR:
    ├─→ Load PR details
    ├─→ [Same as mock mode]
    ├─→ Post Review (if enabled)
    └─→ Track results
    ↓
Print Batch Summary
```

---

## Next Steps

After completing this guide:

1. **Read** `docs/batch-scanning.md` for advanced batch options
2. **Read** `docs/architecture.md` for system design
3. **Read** `docs/mcp.md` for MCP integration details
4. **Check** `knowledge/` directory for policy documents
5. **Explore** `tests/` for example usage patterns

---

## Getting Help

### Check Logs

```bash
# Enable debug logging
DEBUG=true uv run run-pr-review
```

### Read Source Code

- `src/smart_pr_review_workflow/main.py` — CLI entry point
- `src/smart_pr_review_workflow/workflow.py` — Graph definition
- `src/smart_pr_review_workflow/nodes.py` — Node implementations
- `src/smart_pr_review_workflow/batch.py` — Batch scanning logic

### Run Tests

```bash
# Run all tests
uv run pytest

# Run specific test
uv run pytest tests/test_batch_scanning.py -v

# Run with coverage
uv run pytest --cov=src
```

### Check Configuration

```bash
# Verify .env is loaded
cat .env | grep -v '^#' | grep -v '^$'

# Check environment variables are set
env | grep GITHUB
env | grep AWS
env | grep BEDROCK
```

---

## Summary

| Mode | Command | When to Use |
|------|---------|------------|
| **Mock** | `uv run run-pr-review` | Testing without AWS/GitHub |
| **Single PR** | `uv run run-pr-review --owner org --repo repo --pr 123` | Review one specific PR |
| **Batch** | `uv run run-pr-review --batch --owner org --repo repo` | Automate reviews for multiple PRs |

Start with Mock mode to verify everything works locally, then move to GitHub integration.

Good luck! 🚀
