"""Data access + lifecycle transitions for reviews."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Review
from app.models.enums import ReviewStatus


class ReviewRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, *, pull_request_id: uuid.UUID) -> Review:
        review = Review(pull_request_id=pull_request_id, status=ReviewStatus.PENDING)
        self.db.add(review)
        await self.db.flush()
        return review

    async def get(self, review_id: uuid.UUID) -> Review | None:
        return await self.db.get(Review, review_id)

    async def list_by_pull_request(
        self, pull_request_id: uuid.UUID
    ) -> Sequence[Review]:
        result = await self.db.execute(
            select(Review)
            .where(Review.pull_request_id == pull_request_id)
            .order_by(Review.created_at.desc())
        )
        return result.scalars().all()

    async def mark_running(self, review_id: uuid.UUID) -> None:
        review = await self._require(review_id)
        review.status = ReviewStatus.RUNNING
        await self.db.flush()

    async def mark_completed(
        self,
        review_id: uuid.UUID,
        *,
        summary: str,
        quality_score: int,
        security_score: int,
        complexity_score: int,
        maintainability_score: int,
        performance_score: int,
        provider: str,
        model: str,
        meta: dict[str, Any] | None = None,
    ) -> None:
        review = await self._require(review_id)
        review.status = ReviewStatus.COMPLETED
        review.summary = summary
        review.quality_score = quality_score
        review.security_score = security_score
        review.complexity_score = complexity_score
        review.maintainability_score = maintainability_score
        review.performance_score = performance_score
        review.provider = provider
        review.model = model
        review.meta = meta
        review.completed_at = datetime.now(UTC)
        await self.db.flush()

    async def mark_failed(self, review_id: uuid.UUID) -> None:
        review = await self.db.get(Review, review_id)
        if review is not None:
            review.status = ReviewStatus.FAILED
            review.completed_at = datetime.now(UTC)
            await self.db.flush()

    async def _require(self, review_id: uuid.UUID) -> Review:
        review = await self.db.get(Review, review_id)
        if review is None:
            raise ValueError(f"review {review_id} not found")
        return review
