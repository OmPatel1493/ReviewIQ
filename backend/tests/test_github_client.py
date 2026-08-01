"""GitHubClient tests — GitHub simulated via httpx.MockTransport (no network)."""

from __future__ import annotations

import httpx
import pytest

from app.modules.github.client import GitHubAPIError, GitHubClient


def _repo(idx: int) -> dict:
    return {
        "id": idx,
        "name": f"repo{idx}",
        "full_name": f"octo/repo{idx}",
        "private": False,
        "owner": {"login": "octo"},
        "default_branch": "main",
        "clone_url": f"https://github.com/octo/repo{idx}.git",
        "language": "Python",
        "html_url": f"https://github.com/octo/repo{idx}",
    }


def _client(handler) -> GitHubClient:
    transport = httpx.MockTransport(handler)
    return GitHubClient(access_token="t", client=httpx.AsyncClient(transport=transport))


async def test_list_repositories_follows_pagination() -> None:
    """Two pages via the Link header should be transparently merged."""

    def handler(request: httpx.Request) -> httpx.Response:
        page = request.url.params.get("page")
        if page == "1":
            return httpx.Response(
                200,
                json=[_repo(1)],
                headers={"Link": '<https://api.github.com/user/repos?page=2>; rel="next"'},
            )
        return httpx.Response(200, json=[_repo(2)])  # page 2, no next link

    repos = await _client(handler).list_repositories()
    assert [r.full_name for r in repos] == ["octo/repo1", "octo/repo2"]
    assert repos[0].owner_login == "octo"


async def test_get_pull_request_derives_merged_state() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "id": 10, "number": 7, "title": "Feature", "body": None, "state": "closed",
            "user": {"login": "octo"},
            "head": {"ref": "feature", "sha": "a" * 40},
            "base": {"ref": "main", "sha": "b" * 40},
            "additions": 12, "deletions": 3, "changed_files": 2,
            "html_url": "https://github.com/octo/repo/pull/7",
            "merged_at": "2026-07-01T00:00:00Z",
        })

    pr = await _client(handler).get_pull_request("octo", "repo", 7)
    assert pr.effective_state == "merged"  # closed + merged_at → merged
    assert pr.author_login == "octo"
    assert pr.changed_files == 2


async def test_list_pull_request_files_parses_patch() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[
            {"filename": "app/main.py", "status": "modified", "additions": 4,
             "deletions": 1, "changes": 5, "patch": "@@ -1 +1 @@\n-old\n+new"},
            {"filename": "img.png", "status": "added", "additions": 0,
             "deletions": 0, "changes": 0},  # binary → no patch
        ])

    files = await _client(handler).list_pull_request_files("octo", "repo", 7)
    assert files[0].filename == "app/main.py"
    assert files[0].patch is not None and "new" in files[0].patch
    assert files[1].patch is None


async def test_api_errors_map_to_github_api_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    with pytest.raises(GitHubAPIError):
        await _client(handler).get_repository("octo", "nope")


async def test_rate_limit_is_surfaced() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, headers={"x-ratelimit-remaining": "0"}, json={})

    with pytest.raises(GitHubAPIError, match="rate limit"):
        await _client(handler).list_repositories()
