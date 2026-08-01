"""Repository API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import IndexStatus
from app.modules.github.schemas import GitHubRepo


class RepositoryOut(BaseModel):
    """A repository connected to ReviewIQ (from our DB)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    github_id: int
    full_name: str
    name: str
    owner_login: str
    private: bool
    default_branch: str
    language: str | None = None
    index_status: IndexStatus
    indexed_at: datetime | None = None
    created_at: datetime


class GitHubRepoOut(BaseModel):
    """A repository available on GitHub that the user could connect."""

    github_id: int
    full_name: str
    name: str
    owner_login: str
    private: bool
    language: str | None = None
    description: str | None = None
    stargazers_count: int
    html_url: str

    @classmethod
    def from_gh(cls, gh: GitHubRepo) -> GitHubRepoOut:
        return cls(
            github_id=gh.id,
            full_name=gh.full_name,
            name=gh.name,
            owner_login=gh.owner_login,
            private=gh.private,
            language=gh.language,
            description=gh.description,
            stargazers_count=gh.stargazers_count,
            html_url=gh.html_url,
        )


class ConnectRepositoryRequest(BaseModel):
    # Enforce the "owner/repo" shape at the edge.
    full_name: str = Field(
        pattern=r"^[^/\s]+/[^/\s]+$", examples=["octocat/Hello-World"]
    )
