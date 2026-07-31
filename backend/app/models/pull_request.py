"""PullRequest — a GitHub PR we analyze."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import PRState

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.repository import Repository
    from app.models.review import Review


class PullRequest(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "pull_requests"
    __table_args__ = (
        # PR numbers are unique within a repository.
        UniqueConstraint("repository_id", "number"),
    )

    repository_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        index=True,
    )

    github_id: Mapped[int] = mapped_column(BigInteger)
    number: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(1024))
    body: Mapped[str | None] = mapped_column(Text)
    author_login: Mapped[str] = mapped_column(String(255))
    state: Mapped[PRState] = mapped_column(
        Enum(PRState, name="pr_state"), default=PRState.OPEN, index=True
    )

    # Git refs / SHAs describe exactly what diff to review.
    head_sha: Mapped[str] = mapped_column(String(64))
    base_sha: Mapped[str] = mapped_column(String(64))
    head_ref: Mapped[str] = mapped_column(String(255))
    base_ref: Mapped[str] = mapped_column(String(255))

    additions: Mapped[int] = mapped_column(Integer, default=0)
    deletions: Mapped[int] = mapped_column(Integer, default=0)
    changed_files: Mapped[int] = mapped_column(Integer, default=0)
    html_url: Mapped[str] = mapped_column(String(1024))

    # Timestamps reported by GitHub (distinct from our own audit timestamps).
    gh_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    gh_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # --- relationships ---
    repository: Mapped[Repository] = relationship(back_populates="pull_requests")
    reviews: Mapped[list[Review]] = relationship(
        back_populates="pull_request", cascade="all, delete-orphan"
    )
    jobs: Mapped[list[Job]] = relationship(back_populates="pull_request")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PullRequest #{self.number} {self.title!r}>"
