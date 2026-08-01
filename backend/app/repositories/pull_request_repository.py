"""Data access for pull requests."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PullRequest
from app.models.enums import PRState
from app.modules.github.schemas import GitHubPull


class PullRequestRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_repo_and_number(
        self, repository_id: uuid.UUID, number: int
    ) -> PullRequest | None:
        result = await self.db.execute(
            select(PullRequest).where(
                PullRequest.repository_id == repository_id,
                PullRequest.number == number,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_repo(self, repository_id: uuid.UUID) -> Sequence[PullRequest]:
        result = await self.db.execute(
            select(PullRequest)
            .where(PullRequest.repository_id == repository_id)
            .order_by(PullRequest.number.desc())
        )
        return result.scalars().all()

    async def upsert_from_github(
        self, repository_id: uuid.UUID, gh: GitHubPull
    ) -> PullRequest:
        pr = await self.get_by_repo_and_number(repository_id, gh.number)
        if pr is None:
            pr = PullRequest(repository_id=repository_id, number=gh.number)
            self.db.add(pr)

        pr.github_id = gh.id
        pr.title = gh.title
        pr.body = gh.body
        pr.author_login = gh.author_login
        pr.state = PRState(gh.effective_state)
        pr.head_sha = gh.head.sha
        pr.base_sha = gh.base.sha
        pr.head_ref = gh.head.ref
        pr.base_ref = gh.base.ref
        pr.additions = gh.additions
        pr.deletions = gh.deletions
        pr.changed_files = gh.changed_files
        pr.html_url = gh.html_url
        pr.gh_created_at = gh.created_at
        pr.gh_updated_at = gh.updated_at

        await self.db.flush()
        return pr
