"""Append-only writes to the activity log."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ActivityLog


class ActivityLogRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record(
        self,
        *,
        action: str,
        user_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> ActivityLog:
        entry = ActivityLog(
            action=action,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            meta=meta,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry
