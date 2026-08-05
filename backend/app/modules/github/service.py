"""GitHub use-cases: connect repositories and sync their pull requests.

Orchestrates the GitHub client + repositories, enforces that a user can only touch
their own repos, and records activity. Reviews/indexing (later phases) build on the
rows this persists.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PullRequest, Repository, User
from app.modules.auth.security import decrypt_token
from app.modules.github.client import GitHubClient
from app.modules.github.schemas import GitHubFile, GitHubRepo
from app.repositories.activity_log_repository import ActivityLogRepository
from app.repositories.pull_request_repository import PullRequestRepository
from app.repositories.repository_repository import RepositoryRepository


class RepositoryNotFoundError(Exception):
    """No such repository for this user."""


class RepositoryAccessError(Exception):
    """The repository exists but is owned by a different user."""


class GitHubService:
    def __init__(
        self, db: AsyncSession, user: User, client: GitHubClient | None = None
    ) -> None:
        self.db = db
        self.user = user
        self.repos = RepositoryRepository(db)
        self.pulls = PullRequestRepository(db)
        self.activity = ActivityLogRepository(db)
        # Decrypt the user's GitHub token just-in-time to build a client. An
        # injected client (tests) bypasses this entirely.
        token = decrypt_token(user.github_access_token) if user.github_access_token else ""
        self.gh = client or GitHubClient(access_token=token)

    async def list_remote_repositories(self) -> list[GitHubRepo]:
        """Repos on GitHub the user could connect (not yet persisted)."""
        return await self.gh.list_repositories()

    async def list_connected_repositories(self) -> Sequence[Repository]:
        return await self.repos.list_by_owner(self.user.id)

    async def get_connected_repository(self, repo_id: uuid.UUID) -> Repository:
        repo = await self.repos.get(repo_id)
        if repo is None:
            raise RepositoryNotFoundError
        if repo.owner_id != self.user.id:
            # Don't reveal existence to non-owners.
            raise RepositoryAccessError
        return repo

    async def connect_repository(self, full_name: str) -> Repository:
        """Connect `owner/repo`: fetch it from GitHub and upsert the DB row."""
        owner, _, name = full_name.partition("/")
        gh_repo = await self.gh.get_repository(owner, name)
        repo = await self.repos.upsert_from_github(self.user, gh_repo)
        await self.activity.record(
            action="repo.connected",
            user_id=self.user.id,
            entity_type="repository",
            entity_id=str(repo.id),
            meta={"full_name": repo.full_name},
        )
        return repo

    async def sync_pull_requests(self, repo_id: uuid.UUID) -> Sequence[PullRequest]:
        """Pull the repo's PRs from GitHub and upsert them."""
        repo = await self.get_connected_repository(repo_id)
        owner, _, name = repo.full_name.partition("/")
        gh_pulls = await self.gh.list_pull_requests(owner, name, state="all")
        return [await self.pulls.upsert_from_github(repo.id, gp) for gp in gh_pulls]

    async def get_or_sync_pull_request(
        self, repo_id: uuid.UUID, number: int
    ) -> PullRequest:
        """Fetch a single PR from GitHub and upsert its row (used before a review)."""
        repo = await self.get_connected_repository(repo_id)
        owner, _, name = repo.full_name.partition("/")
        gh_pull = await self.gh.get_pull_request(owner, name, number)
        return await self.pulls.upsert_from_github(repo.id, gh_pull)

    async def get_pull_request_files(
        self, repo_id: uuid.UUID, number: int
    ) -> list[GitHubFile]:
        """The changed files + diffs for a PR (fetched live; not persisted)."""
        repo = await self.get_connected_repository(repo_id)
        owner, _, name = repo.full_name.partition("/")
        return await self.gh.list_pull_request_files(owner, name, number)
