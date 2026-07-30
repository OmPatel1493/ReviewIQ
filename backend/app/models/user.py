"""User — a person authenticated via GitHub OAuth."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.activity_log import ActivityLog
    from app.models.repository import Repository


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    # GitHub's numeric user id — stable even if the login (username) changes.
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    login: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(320))
    avatar_url: Mapped[str | None] = mapped_column(Text)

    # The GitHub OAuth access token. Stored server-side ONLY, encrypted at rest
    # (encryption wired in Phase 2). The browser never receives this — it holds
    # our own JWT instead.
    github_access_token: Mapped[str | None] = mapped_column(Text)

    # --- relationships ---
    repositories: Mapped[list[Repository]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    activity_logs: Mapped[list[ActivityLog]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<User {self.login!r}>"
