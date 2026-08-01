"""Typed models for the slices of the GitHub REST API we consume.

We validate GitHub's JSON into Pydantic models at the boundary so the rest of the
code works with typed objects (not raw dicts) and a schema change from GitHub fails
loudly here instead of silently deep in the app. We only model the fields we use.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GitHubOwner(BaseModel):
    model_config = ConfigDict(extra="ignore")
    login: str


class GitHubRepo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    name: str
    full_name: str  # "owner/repo"
    private: bool = False
    owner: GitHubOwner
    default_branch: str = "main"
    clone_url: str
    language: str | None = None
    html_url: str
    description: str | None = None
    stargazers_count: int = 0

    @property
    def owner_login(self) -> str:
        return self.owner.login


class GitHubRef(BaseModel):
    """A PR side (head/base): the branch name (`ref`) and commit (`sha`)."""

    model_config = ConfigDict(extra="ignore")
    ref: str
    sha: str


class GitHubPull(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    number: int
    title: str
    body: str | None = None
    state: str  # GitHub only reports "open" | "closed"
    user: GitHubOwner | None = None
    head: GitHubRef
    base: GitHubRef
    # These stats are present on the single-PR endpoint, absent on list endpoints.
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    html_url: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    merged_at: datetime | None = None

    @property
    def author_login(self) -> str:
        return self.user.login if self.user else "unknown"

    @property
    def effective_state(self) -> str:
        """GitHub lacks a 'merged' state; derive it from `merged_at`."""
        if self.merged_at is not None:
            return "merged"
        return self.state


class GitHubFile(BaseModel):
    """One changed file in a PR (from `.../pulls/{n}/files`)."""

    model_config = ConfigDict(extra="ignore")

    filename: str
    status: str  # added | modified | removed | renamed | ...
    additions: int = 0
    deletions: int = 0
    changes: int = 0
    patch: str | None = None  # unified diff; absent for binary/very large files
    previous_filename: str | None = None


class GitHubCommitAuthor(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str | None = None
    email: str | None = None
    date: datetime | None = None


class GitHubCommitDetail(BaseModel):
    model_config = ConfigDict(extra="ignore")
    message: str
    author: GitHubCommitAuthor | None = None


class GitHubCommit(BaseModel):
    model_config = ConfigDict(extra="ignore")
    sha: str
    commit: GitHubCommitDetail
    author: GitHubOwner | None = None
    html_url: str
