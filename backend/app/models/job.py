"""Job — a tracked unit of background work run by a Celery worker.

Every long-running task (clone, index, review, report) gets a row here so the API
and UI can show progress, surface errors, and keep an audit trail — independent of
Celery's own transient result store.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import JobStatus, JobType

if TYPE_CHECKING:
    from app.models.pull_request import PullRequest
    from app.models.repository import Repository


class Job(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "jobs"

    type: Mapped[JobType] = mapped_column(Enum(JobType, name="job_type"), index=True)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"), default=JobStatus.QUEUED, index=True
    )

    # Optional links to what the job operates on.
    repository_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        index=True,
    )
    pull_request_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("pull_requests.id", ondelete="CASCADE")
    )

    # Ties our row to the Celery task so we can correlate logs/retries.
    celery_task_id: Mapped[str | None] = mapped_column(String(255), index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0–100
    error: Mapped[str | None] = mapped_column(Text)

    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # inputs
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # outputs

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # --- relationships ---
    repository: Mapped[Repository | None] = relationship(back_populates="jobs")
    pull_request: Mapped[PullRequest | None] = relationship(back_populates="jobs")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Job {self.type} status={self.status} progress={self.progress}>"
