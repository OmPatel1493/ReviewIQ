"""CodeChunk — metadata for one embedded slice of source code.

This is the "Embeddings" table. The actual float vectors live in **Qdrant** (a
purpose-built vector DB); PostgreSQL stores the *metadata* and the Qdrant point id
(`vector_id`) so we can join search hits back to rich relational data and manage the
index lifecycle. The `content_hash` lets us skip re-embedding chunks that didn't
change between indexing runs — the single biggest cost saver in the pipeline.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.repository import Repository


class CodeChunk(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "code_chunks"
    __table_args__ = (
        # One logical chunk per (repo, file, line-range).
        UniqueConstraint("repository_id", "file_path", "start_line", "end_line"),
    )

    repository_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        index=True,
    )

    file_path: Mapped[str] = mapped_column(String(1024), index=True)
    language: Mapped[str | None] = mapped_column(String(64))
    symbol: Mapped[str | None] = mapped_column(String(512))  # function/class name
    start_line: Mapped[int] = mapped_column(Integer)
    end_line: Mapped[int] = mapped_column(Integer)

    # SHA-256 of the chunk text — change detection to avoid re-embedding.
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    # The corresponding point id in Qdrant.
    vector_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True))
    token_count: Mapped[int | None] = mapped_column(Integer)

    # --- relationships ---
    repository: Mapped[Repository] = relationship(back_populates="code_chunks")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CodeChunk {self.file_path}:{self.start_line}-{self.end_line}>"
