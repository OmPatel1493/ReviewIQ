"""Data access for users.

The repository layer is the only place that talks to the DB for a given aggregate.
Services depend on this interface, not on SQLAlchemy directly — which keeps business
logic persistence-agnostic and easy to test.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.modules.auth.github import GitHubUser


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, user_id: uuid.UUID) -> User | None:
        return await self.db.get(User, user_id)

    async def get_by_github_id(self, github_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.github_id == github_id))
        return result.scalar_one_or_none()

    async def upsert_from_github(self, gh: GitHubUser, encrypted_token: str) -> User:
        """Create the user on first login, otherwise refresh their profile + token.

        Keying on GitHub's numeric id (not the login) means a username change doesn't
        create a duplicate account.
        """
        user = await self.get_by_github_id(gh.id)
        if user is None:
            user = User(github_id=gh.id, login=gh.login)
            self.db.add(user)

        user.login = gh.login
        user.name = gh.name
        user.email = gh.email
        user.avatar_url = gh.avatar_url
        user.github_access_token = encrypted_token

        await self.db.flush()  # assign PK / persist within the request's transaction
        return user
