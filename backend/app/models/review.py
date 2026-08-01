"""Review — one AI analysis run over a pull request, with aggregate scores."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import ReviewStatus

if TYPE_CHECKING:
    from app.models.finding import Finding
    from app.models.pull_request import PullRequest


class Review(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "reviews"

    pull_request_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("pull_requests.id", ondelete="CASCADE"),
        index=True,
    )

    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, name="review_status"),
        default=ReviewStatus.PENDING,
        index=True,
    )

    # Executive summary written by the LLM.
    summary: Mapped[str | None] = mapped_column(Text)

    # Aggregate 0–100 scores (nullable until the review completes).
    quality_score: Mapped[int | None] = mapped_column(Integer)
    security_score: Mapped[int | None] = mapped_column(Integer)
    complexity_score: Mapped[int | None] = mapped_column(Integer)
    maintainability_score: Mapped[int | None] = mapped_column(Integer)
    performance_score: Mapped[int | None] = mapped_column(Integer)

    # Provenance: which model/provider produced this review (reproducibility).
    provider: Mapped[str | None] = mapped_column(String(32))
    model: Mapped[str | None] = mapped_column(String(128))

    # Free-form extras: token usage, raw rubric output, timings, etc.
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # --- relationships ---
    pull_request: Mapped[PullRequest] = relationship(back_populates="reviews")
    findings: Mapped[list[Finding]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Review {self.id} status={self.status}>"
