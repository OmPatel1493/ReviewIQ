"""Data access for indexed code-chunk metadata."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CodeChunk


class CodeChunkRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def delete_by_repo(self, repository_id: uuid.UUID) -> None:
        await self.db.execute(
            delete(CodeChunk).where(CodeChunk.repository_id == repository_id)
        )

    async def bulk_insert(self, chunks: Sequence[CodeChunk]) -> None:
        if chunks:
            self.db.add_all(list(chunks))
            await self.db.flush()

    async def count_by_repo(self, repository_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(CodeChunk.id)).where(
                CodeChunk.repository_id == repository_id
            )
        )
        return result.scalar_one()
