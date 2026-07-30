"""Auth use-cases: turn a GitHub OAuth round-trip into a ReviewIQ user + JWT.

This is the orchestration layer. It knows *what* login means (validate state →
exchange code → fetch profile → upsert user → mint our token) but delegates the
*how* to the GitHub client, the repository, and the security helpers.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import User
from app.modules.auth.github import GitHubOAuth
from app.modules.auth.security import (
    create_access_token,
    create_state_token,
    encrypt_token,
    verify_state_token,
)
from app.repositories.user_repository import UserRepository

settings = get_settings()


class OAuthNotConfiguredError(Exception):
    """GitHub client id/secret are missing from the environment."""


class InvalidOAuthStateError(Exception):
    """The `state` returned by GitHub is missing, forged, or expired."""


class AuthService:
    def __init__(self, db: AsyncSession, oauth: GitHubOAuth | None = None) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.oauth = oauth or GitHubOAuth()

    def build_login_url(self) -> str:
        if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
            raise OAuthNotConfiguredError
        return self.oauth.authorize_url(create_state_token())

    async def complete_login(self, code: str, state: str) -> tuple[User, str]:
        if not verify_state_token(state):
            raise InvalidOAuthStateError

        access_token = await self.oauth.exchange_code_for_token(code)
        gh_user = await self.oauth.fetch_user(access_token)

        user = await self.users.upsert_from_github(gh_user, encrypt_token(access_token))
        jwt_token = create_access_token(subject=str(user.id), extra={"login": user.login})
        return user, jwt_token
