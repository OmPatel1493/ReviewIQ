"""Dashboard analytics schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import ReviewStatus


class ScoreAverages(BaseModel):
    """Mean 0–100 scores across the user's completed reviews (None if none yet)."""

    quality: float | None
    security: float | None
    complexity: float | None
    maintainability: float | None
    performance: float | None


class RecentReview(BaseModel):
    id: uuid.UUID
    repository: str
    pull_number: int
    status: ReviewStatus
    quality_score: int | None
    findings: int
    created_at: datetime


class AnalyticsOverview(BaseModel):
    repos_connected: int
    repos_indexed: int
    reviews_total: int
    reviews_completed: int
    findings_total: int
    # keyed by severity / category value → count (every enum value present, 0 if none)
    findings_by_severity: dict[str, int]
    findings_by_category: dict[str, int]
    score_averages: ScoreAverages
    recent_reviews: list[RecentReview]
