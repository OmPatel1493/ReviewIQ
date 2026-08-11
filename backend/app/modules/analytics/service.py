"""Analytics use-case: aggregate a user's reviews and findings for the dashboard.

Everything is scoped to repositories the user owns (Repository.owner_id), joined through
PullRequest → Review → Finding. Read-only; no writes.
"""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.models import Finding, PullRequest, Repository, Review, User
from app.models.enums import FindingCategory, IndexStatus, ReviewStatus, Severity
from app.modules.analytics.schemas import (
    AnalyticsOverview,
    RecentReview,
    ScoreAverages,
)


class AnalyticsService:
    def __init__(self, db: AsyncSession, user: User) -> None:
        self.db = db
        self.user = user

    async def overview(self) -> AnalyticsOverview:
        owner_id = self.user.id

        repos_connected = await self._count(
            select(func.count()).select_from(Repository).where(Repository.owner_id == owner_id)
        )
        repos_indexed = await self._count(
            select(func.count())
            .select_from(Repository)
            .where(
                Repository.owner_id == owner_id,
                Repository.index_status == IndexStatus.INDEXED,
            )
        )

        reviews_total = await self._count(self._owned_reviews(select(func.count())))
        reviews_completed = await self._count(
            self._owned_reviews(select(func.count())).where(
                Review.status == ReviewStatus.COMPLETED
            )
        )
        findings_total = await self._count(self._owned_findings(select(func.count())))

        findings_by_severity = await self._grouped(Finding.severity, Severity)
        findings_by_category = await self._grouped(Finding.category, FindingCategory)
        score_averages = await self._score_averages()
        recent_reviews = await self._recent_reviews()

        return AnalyticsOverview(
            repos_connected=repos_connected,
            repos_indexed=repos_indexed,
            reviews_total=reviews_total,
            reviews_completed=reviews_completed,
            findings_total=findings_total,
            findings_by_severity=findings_by_severity,
            findings_by_category=findings_by_category,
            score_averages=score_averages,
            recent_reviews=recent_reviews,
        )

    # --------------------------------------------------------------- helpers
    def _owned_reviews(self, stmt: Select) -> Select:
        """Attach the Review → PR → Repo(owner) joins to a select."""
        return (
            stmt.select_from(Review)
            .join(PullRequest, Review.pull_request_id == PullRequest.id)
            .join(Repository, PullRequest.repository_id == Repository.id)
            .where(Repository.owner_id == self.user.id)
        )

    def _owned_findings(self, stmt: Select) -> Select:
        return (
            stmt.select_from(Finding)
            .join(Review, Finding.review_id == Review.id)
            .join(PullRequest, Review.pull_request_id == PullRequest.id)
            .join(Repository, PullRequest.repository_id == Repository.id)
            .where(Repository.owner_id == self.user.id)
        )

    async def _count(self, stmt: Select) -> int:
        return int((await self.db.execute(stmt)).scalar() or 0)

    async def _grouped(
        self, column: InstrumentedAttribute, enum_cls: type[StrEnum]
    ) -> dict[str, int]:
        # Seed every enum value with 0 so the dashboard always renders all bars.
        counts = {member.value: 0 for member in enum_cls}
        rows = await self.db.execute(
            self._owned_findings(select(column, func.count())).group_by(column)
        )
        for value, count in rows.all():
            key = value.value if hasattr(value, "value") else str(value)
            counts[key] = int(count)
        return counts

    async def _score_averages(self) -> ScoreAverages:
        row = (
            await self.db.execute(
                self._owned_reviews(
                    select(
                        func.avg(Review.quality_score),
                        func.avg(Review.security_score),
                        func.avg(Review.complexity_score),
                        func.avg(Review.maintainability_score),
                        func.avg(Review.performance_score),
                    )
                ).where(Review.status == ReviewStatus.COMPLETED)
            )
        ).one()

        def _round(v: float | None) -> float | None:
            return None if v is None else round(float(v), 1)

        return ScoreAverages(
            quality=_round(row[0]),
            security=_round(row[1]),
            complexity=_round(row[2]),
            maintainability=_round(row[3]),
            performance=_round(row[4]),
        )

    async def _recent_reviews(self, limit: int = 5) -> list[RecentReview]:
        finding_count = (
            select(func.count())
            .select_from(Finding)
            .where(Finding.review_id == Review.id)
            .scalar_subquery()
        )
        rows = await self.db.execute(
            select(Review, PullRequest.number, Repository.full_name, finding_count.label("n"))
            .join(PullRequest, Review.pull_request_id == PullRequest.id)
            .join(Repository, PullRequest.repository_id == Repository.id)
            .where(Repository.owner_id == self.user.id)
            .order_by(Review.created_at.desc())
            .limit(limit)
        )
        return [
            RecentReview(
                id=review.id,
                repository=full_name,
                pull_number=number,
                status=review.status,
                quality_score=review.quality_score,
                findings=int(n),
                created_at=review.created_at,
            )
            for review, number, full_name, n in rows.all()
        ]
