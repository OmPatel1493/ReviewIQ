"""Data access for review findings."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Finding


class FindingRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def bulk_insert(self, findings: Sequence[Finding]) -> None:
        if findings:
            self.db.add_all(list(findings))
            await self.db.flush()

    async def list_by_review(self, review_id: uuid.UUID) -> Sequence[Finding]:
        result = await self.db.execute(
            select(Finding)
            .where(Finding.review_id == review_id)
            .order_by(Finding.severity.desc(), Finding.file_path)
        )
        return result.scalars().all()
