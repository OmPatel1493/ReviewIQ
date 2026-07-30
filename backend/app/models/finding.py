"""Finding — a single review comment: one issue at one place in the diff.

These are the "Comments" from the spec: each maps to a line/range in a changed file
and carries severity, category, the rationale (why), the impact, and a suggested fix.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import FindingCategory, Severity

if TYPE_CHECKING:
    from app.models.review import Review


class Finding(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "findings"

    review_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("reviews.id", ondelete="CASCADE"), index=True
    )

    file_path: Mapped[str] = mapped_column(String(1024), index=True)
    # Line range in the changed file. Nullable for file- or PR-level findings.
    line_start: Mapped[int | None] = mapped_column(Integer)
    line_end: Mapped[int | None] = mapped_column(Integer)

    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, name="severity"), index=True
    )
    category: Mapped[FindingCategory] = mapped_column(
        Enum(FindingCategory, name="finding_category"), index=True
    )

    title: Mapped[str] = mapped_column(String(512))
    rationale: Mapped[str] = mapped_column(Text)  # the "why"
    impact: Mapped[str | None] = mapped_column(Text)
    suggestion: Mapped[str | None] = mapped_column(Text)  # suggested fix / snippet

    # Model's self-reported confidence (0–1); useful for filtering/ranking.
    confidence: Mapped[float | None] = mapped_column(Float)

    # --- relationships ---
    review: Mapped[Review] = relationship(back_populates="findings")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Finding {self.severity}/{self.category} {self.file_path}:{self.line_start}>"
