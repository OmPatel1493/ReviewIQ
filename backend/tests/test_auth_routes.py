"""Auth route + GitHub client tests.

DB is stubbed out (the paths under test don't query it), and GitHub is simulated via
`httpx.MockTransport`, so these run fast and hermetically — no Postgres, no network.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Iterator

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.db import get_db
from app.main import app
from app.modules.auth.github import GitHubOAuth


@pytest.fixture
def client_no_db() -> Iterator[TestClient]:
    async def _fake_db() -> AsyncGenerator[None, None]:
        yield None

    app.dependency_overrides[get_db] = _fake_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_me_requires_auth(client_no_db: TestClient) -> None:
    resp = client_no_db.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.headers.get("WWW-Authenticate") == "Bearer"


def test_me_rejects_garbage_bearer(client_no_db: TestClient) -> None:
    resp = client_no_db.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-jwt"}
    )
    assert resp.status_code == 401


def test_login_returns_503_when_oauth_unconfigured(client_no_db: TestClient) -> None:
    # With no GITHUB_CLIENT_ID/SECRET in the test env, login is unavailable.
    resp = client_no_db.get("/api/v1/auth/github/login")
    assert resp.status_code == 503
    assert "GITHUB_CLIENT_ID" in resp.json()["detail"]


def test_logout_clears_cookie(client_no_db: TestClient) -> None:
    resp = client_no_db.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


async def test_github_client_exchanges_code_and_fetches_user() -> None:
    """Exercise the OAuth client against a simulated GitHub."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/login/oauth/access_token"):
            return httpx.Response(200, json={"access_token": "gho_abc", "token_type": "bearer"})
        if path == "/user":
            return httpx.Response(
                200,
                json={"id": 42, "login": "octocat", "name": "Octo", "email": None,
                      "avatar_url": "https://avatars/x"},
            )
        if path == "/user/emails":
            return httpx.Response(
                200, json=[{"email": "octo@example.com", "primary": True, "verified": True}]
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        gh = GitHubOAuth(client=http)

        token = await gh.exchange_code_for_token("code-123")
        assert token == "gho_abc"

        user = await gh.fetch_user(token)
        assert user.id == 42
        assert user.login == "octocat"
        # email was private on /user, so it must be resolved via /user/emails
        assert user.email == "octo@example.com"


def test_authorize_url_contains_state_and_redirect() -> None:
    gh = GitHubOAuth()
    url = gh.authorize_url("state-xyz")
    assert url.startswith("https://github.com/login/oauth/authorize?")
    assert "state=state-xyz" in url
    assert "redirect_uri=" in url
