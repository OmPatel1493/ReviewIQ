"""Authenticated GitHub REST client.

One class owns every GitHub data call, so authentication, pagination, versioning,
and error/rate-limit handling live in a single place — and it's trivial to test by
injecting a fake `httpx.AsyncClient` (via `httpx.MockTransport`).

Auth uses the user's OAuth access token (decrypted just-in-time by the service).
"""

from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.modules.github.schemas import (
    GitHubCommit,
    GitHubFile,
    GitHubPull,
    GitHubRepo,
)

settings = get_settings()


class GitHubAPIError(Exception):
    """Any non-success response from GitHub (auth, rate limit, not found, 5xx)."""


class GitHubClient:
    def __init__(self, access_token: str, client: httpx.AsyncClient | None = None) -> None:
        self._token = access_token
        self._client = client  # injected in tests; otherwise a client per request
        self._base = settings.GITHUB_API_URL.rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def _get(
        self, path: str, params: dict[str, str | int] | None = None
    ) -> httpx.Response:
        url = f"{self._base}{path}"
        if self._client is not None:
            resp = await self._client.get(url, headers=self._headers(), params=params)
        else:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(url, headers=self._headers(), params=params)
        self._raise_for_status(resp, path)
        return resp

    @staticmethod
    def _raise_for_status(resp: httpx.Response, path: str) -> None:
        if resp.status_code == 401:
            raise GitHubAPIError("GitHub authentication failed (token invalid or expired).")
        if resp.status_code == 403 and resp.headers.get("x-ratelimit-remaining") == "0":
            raise GitHubAPIError("GitHub API rate limit exceeded — try again later.")
        if resp.status_code == 404:
            raise GitHubAPIError(f"GitHub resource not found: {path}")
        if resp.status_code >= 400:
            raise GitHubAPIError(f"GitHub API error {resp.status_code} for {path}")

    async def _paginate(
        self, path: str, params: dict[str, str | int] | None = None
    ) -> list[dict]:
        """Follow GitHub's `Link: rel="next"` pagination until exhausted."""
        results: list[dict] = []
        query: dict[str, str | int] = {"per_page": 100, **(params or {})}
        page = 1
        while True:
            query["page"] = page
            resp = await self._get(path, query)
            batch = resp.json()
            if not isinstance(batch, list) or not batch:
                break
            results.extend(batch)
            link = resp.headers.get("link", "")
            if 'rel="next"' not in link:
                break
            page += 1
        return results

    # --------------------------------------------------------------- repos --
    async def list_repositories(self) -> list[GitHubRepo]:
        raw = await self._paginate(
            "/user/repos",
            {"sort": "updated", "affiliation": "owner,collaborator,organization_member"},
        )
        return [GitHubRepo.model_validate(r) for r in raw]

    async def get_repository(self, owner: str, repo: str) -> GitHubRepo:
        resp = await self._get(f"/repos/{owner}/{repo}")
        return GitHubRepo.model_validate(resp.json())

    # --------------------------------------------------------------- pulls --
    async def list_pull_requests(
        self, owner: str, repo: str, state: str = "all"
    ) -> list[GitHubPull]:
        raw = await self._paginate(
            f"/repos/{owner}/{repo}/pulls",
            {"state": state, "sort": "updated", "direction": "desc"},
        )
        return [GitHubPull.model_validate(p) for p in raw]

    async def get_pull_request(self, owner: str, repo: str, number: int) -> GitHubPull:
        resp = await self._get(f"/repos/{owner}/{repo}/pulls/{number}")
        return GitHubPull.model_validate(resp.json())

    async def list_pull_request_files(
        self, owner: str, repo: str, number: int
    ) -> list[GitHubFile]:
        raw = await self._paginate(f"/repos/{owner}/{repo}/pulls/{number}/files")
        return [GitHubFile.model_validate(f) for f in raw]

    async def list_pull_request_commits(
        self, owner: str, repo: str, number: int
    ) -> list[GitHubCommit]:
        raw = await self._paginate(f"/repos/{owner}/{repo}/pulls/{number}/commits")
        return [GitHubCommit.model_validate(c) for c in raw]
