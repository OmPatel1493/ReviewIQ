"""Pull-request API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import PRState


class PullRequestOut(BaseModel):
    """A pull request stored in ReviewIQ."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: int
    title: str
    author_login: str
    state: PRState
    additions: int
    deletions: int
    changed_files: int
    html_url: str
    head_sha: str
    base_sha: str
    gh_created_at: datetime | None = None
    created_at: datetime


class ChangedFileOut(BaseModel):
    """One changed file (with its diff) in a pull request."""

    model_config = ConfigDict(from_attributes=True)

    filename: str
    status: str
    additions: int
    deletions: int
    changes: int
    patch: str | None = None
