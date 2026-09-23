from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


GITHUB_API_VERSION = "2026-03-10"


@dataclass(frozen=True)
class GitHubPullRequest:
    owner: str
    repo: str
    number: int
    title: str
    body: str
    html_url: str
    head_sha: str
    files: list[dict]


class GitHubClient:
    """Small GitHub REST client used to teach LangGraph tool integration."""

    def __init__(self) -> None:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise RuntimeError(
                "GITHUB_TOKEN is not set. Set it in .env when GITHUB_ENABLED=true."
            )

        self.token = token
        self.base_url = os.getenv("GITHUB_API_URL", "https://api.github.com").rstrip("/")
        self.max_files = int(os.getenv("GITHUB_MAX_FILES", "50"))

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict | list:
        url = f"{self.base_url}{path}"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
            "User-Agent": "smart-pr-review-workflow",
        }
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"GitHub API error: HTTP {exc.code} for {method} {path}: {detail}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(f"GitHub connection error for {method} {path}: {exc}") from exc

    def get_pull_request(self, owner: str, repo: str, number: int) -> dict:
        owner_q = quote(owner, safe="")
        repo_q = quote(repo, safe="")
        return self._request(
            "GET", f"/repos/{owner_q}/{repo_q}/pulls/{number}"
        )

    def list_pull_request_files(self, owner: str, repo: str, number: int) -> list[dict]:
        owner_q = quote(owner, safe="")
        repo_q = quote(repo, safe="")
        collected: list[dict] = []
        page = 1

        while len(collected) < self.max_files:
            remaining = self.max_files - len(collected)
            per_page = min(100, remaining)
            result = self._request(
                "GET",
                f"/repos/{owner_q}/{repo_q}/pulls/{number}/files?per_page={per_page}&page={page}",
            )
            if not isinstance(result, list):
                raise RuntimeError("Unexpected GitHub files response")
            collected.extend(result)
            if len(result) < per_page:
                break
            page += 1

        return collected[: self.max_files]

    def get_pull_request_bundle(self, owner: str, repo: str, number: int) -> GitHubPullRequest:
        pr = self.get_pull_request(owner, repo, number)
        files = self.list_pull_request_files(owner, repo, number)
        return GitHubPullRequest(
            owner=owner,
            repo=repo,
            number=number,
            title=pr.get("title", ""),
            body=pr.get("body") or "",
            html_url=pr.get("html_url", ""),
            head_sha=((pr.get("head") or {}).get("sha")) or "",
            files=files,
        )

    def create_pull_request_comment(self, owner: str, repo: str, number: int, body: str) -> dict:
        owner_q = quote(owner, safe="")
        repo_q = quote(repo, safe="")
        return self._request(
            "POST",
            f"/repos/{owner_q}/{repo_q}/issues/{number}/comments",
            {"body": body},
        )
