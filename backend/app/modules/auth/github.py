"""Thin GitHub OAuth client.

Isolates every HTTP call to GitHub behind one class so auth logic elsewhere stays
testable (inject a fake `httpx.AsyncClient` in tests) and so rate-limit/error handling
lives in one place. This is the OAuth *authorization-code* flow:

    authorize_url()          → send the user to GitHub to approve
    exchange_code_for_token  → swap the returned code for an access token (server-side)
    fetch_user               → call GitHub as the user to get their profile
"""

from __future__ import annotations

from urllib.parse import urlencode

import httpx
from pydantic import BaseModel

from app.core.config import get_settings

settings = get_settings()

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"


class GitHubOAuthError(Exception):
    """Raised when GitHub returns an error during the OAuth exchange."""


class GitHubUser(BaseModel):
    id: int
    login: str
    name: str | None = None
    email: str | None = None
    avatar_url: str | None = None


class GitHubOAuth:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        # An injected client (tests) is reused; otherwise we open one per call.
        self._client = client

    def authorize_url(self, state: str) -> str:
        params = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "redirect_uri": settings.GITHUB_OAUTH_CALLBACK_URL,
            "scope": " ".join(settings.github_oauth_scopes),
            "state": state,
            "allow_signup": "true",
        }
        return f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"

    async def _request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
        if self._client is not None:
            return await self._client.request(method, url, **kwargs)  # type: ignore[arg-type]
        async with httpx.AsyncClient(timeout=15.0) as client:
            return await client.request(method, url, **kwargs)  # type: ignore[arg-type]

    async def exchange_code_for_token(self, code: str) -> str:
        resp = await self._request(
            "POST",
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_OAUTH_CALLBACK_URL,
            },
        )
        if resp.status_code != 200:
            raise GitHubOAuthError(f"token exchange failed: HTTP {resp.status_code}")
        body = resp.json()
        token = body.get("access_token")
        if not token:
            # GitHub returns 200 with an "error" field on bad/expired codes.
            raise GitHubOAuthError(body.get("error_description") or "no access_token returned")
        return str(token)

    async def fetch_user(self, access_token: str) -> GitHubUser:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        }
        resp = await self._request("GET", f"{settings.GITHUB_API_URL}/user", headers=headers)
        if resp.status_code != 200:
            raise GitHubOAuthError(f"fetch user failed: HTTP {resp.status_code}")
        data = resp.json()

        # The /user endpoint hides the email when it's private; fall back to the
        # dedicated emails endpoint and pick the primary, verified one.
        if not data.get("email"):
            data["email"] = await self._primary_email(headers)

        return GitHubUser.model_validate(data)

    async def _primary_email(self, headers: dict[str, str]) -> str | None:
        try:
            resp = await self._request(
                "GET", f"{settings.GITHUB_API_URL}/user/emails", headers=headers
            )
            if resp.status_code != 200:
                return None
            for entry in resp.json():
                if entry.get("primary") and entry.get("verified"):
                    return str(entry["email"])
        except (httpx.HTTPError, ValueError):
            return None
        return None
