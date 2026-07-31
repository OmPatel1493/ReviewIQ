"""Repository — a GitHub repo a user has connected to ReviewIQ."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import IndexStatus

if TYPE_CHECKING:
    from app.models.code_chunk import CodeChunk
    from app.models.job import Job
    from app.models.pull_request import PullRequest
    from app.models.user import User


class Repository(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "repositories"
    __table_args__ = (
        # A given owner connects a given GitHub repo at most once.
        UniqueConstraint("owner_id", "github_id"),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    github_id: Mapped[int] = mapped_column(BigInteger, index=True)
    full_name: Mapped[str] = mapped_column(String(512), index=True)  # "owner/repo"
    name: Mapped[str] = mapped_column(String(255))
    owner_login: Mapped[str] = mapped_column(String(255))
    private: Mapped[bool] = mapped_column(Boolean, default=False)
    default_branch: Mapped[str] = mapped_column(String(255), default="main")
    clone_url: Mapped[str] = mapped_column(String(1024))
    language: Mapped[str | None] = mapped_column(String(64))

    # Indexing lifecycle (drives the Phase 4 pipeline + UI badges).
    index_status: Mapped[IndexStatus] = mapped_column(
        Enum(IndexStatus, name="index_status"), default=IndexStatus.PENDING, index=True
    )
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # --- relationships ---
    owner: Mapped[User] = relationship(back_populates="repositories")
    pull_requests: Mapped[list[PullRequest]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    code_chunks: Mapped[list[CodeChunk]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    jobs: Mapped[list[Job]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Repository {self.full_name!r}>"
