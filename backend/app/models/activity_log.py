"""ActivityLog — an append-only audit trail of noteworthy actions.

Powers the dashboard's recent-activity feed and gives us a security/audit record
(who connected a repo, when a review completed, etc.). Append-only by convention:
we insert, never update.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class ActivityLog(UUIDMixin, Base):
    __tablename__ = "activity_logs"

    # Nullable so we can log system events not tied to a specific user.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    action: Mapped[str] = mapped_column(String(128), index=True)  # "repo.connected"
    entity_type: Mapped[str | None] = mapped_column(String(64))  # "repository"
    entity_id: Mapped[str | None] = mapped_column(String(64))
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Only a creation timestamp — logs are immutable, so no `updated_at`.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # --- relationships ---
    user: Mapped[User | None] = relationship(back_populates="activity_logs")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ActivityLog {self.action} user={self.user_id}>"
