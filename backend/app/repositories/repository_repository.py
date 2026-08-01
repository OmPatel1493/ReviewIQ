"""Data access for connected repositories."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Repository, User
from app.modules.github.schemas import GitHubRepo


class RepositoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, repo_id: uuid.UUID) -> Repository | None:
        return await self.db.get(Repository, repo_id)

    async def get_by_owner_and_github_id(
        self, owner_id: uuid.UUID, github_id: int
    ) -> Repository | None:
        result = await self.db.execute(
            select(Repository).where(
                Repository.owner_id == owner_id, Repository.github_id == github_id
            )
        )
        return result.scalar_one_or_none()

    async def list_by_owner(self, owner_id: uuid.UUID) -> Sequence[Repository]:
        result = await self.db.execute(
            select(Repository)
            .where(Repository.owner_id == owner_id)
            .order_by(Repository.created_at.desc())
        )
        return result.scalars().all()

    async def upsert_from_github(self, user: User, gh: GitHubRepo) -> Repository:
        """Create the connection on first connect, else refresh its metadata."""
        repo = await self.get_by_owner_and_github_id(user.id, gh.id)
        if repo is None:
            repo = Repository(owner_id=user.id, github_id=gh.id)
            self.db.add(repo)

        repo.full_name = gh.full_name
        repo.name = gh.name
        repo.owner_login = gh.owner_login
        repo.private = gh.private
        repo.default_branch = gh.default_branch
        repo.clone_url = gh.clone_url
        repo.language = gh.language

        await self.db.flush()
        return repo
