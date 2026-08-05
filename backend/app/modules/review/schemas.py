"""Review API schemas + the schema the LLM's JSON is validated against.

Two groups:
- `LLMFinding` / `LLMReviewResult` — validate/normalise the model's raw JSON. Lenient
  on case and out-of-range scores (LLMs drift), so one sloppy field doesn't sink a review.
- `ReviewRequest` / `ReviewOut` / `FindingOut` — the HTTP request/response boundary.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import FindingCategory, ReviewStatus, Severity

# --------------------------------------------------------------- LLM output --


def _clamp_score(v: int) -> int:
    return max(0, min(100, int(v)))


class LLMFinding(BaseModel):
    """One finding as emitted by the model (before it becomes a Finding row)."""

    file_path: str
    line_start: int | None = None
    line_end: int | None = None
    severity: Severity
    category: FindingCategory
    title: str
    rationale: str
    impact: str | None = None
    suggestion: str | None = None
    confidence: float | None = None

    @field_validator("severity", "category", mode="before")
    @classmethod
    def _normalise_enum(cls, v: object) -> object:
        # Models often return "High"/"SECURITY"; enum values are lowercase.
        return v.strip().lower() if isinstance(v, str) else v

    @field_validator("confidence")
    @classmethod
    def _clamp_confidence(cls, v: float | None) -> float | None:
        return None if v is None else max(0.0, min(1.0, v))


class LLMReviewResult(BaseModel):
    """The whole review payload the model returns."""

    summary: str = ""
    quality_score: int = 0
    security_score: int = 0
    complexity_score: int = 0
    maintainability_score: int = 0
    performance_score: int = 0
    findings: list[LLMFinding] = Field(default_factory=list)

    @field_validator(
        "quality_score",
        "security_score",
        "complexity_score",
        "maintainability_score",
        "performance_score",
        mode="before",
    )
    @classmethod
    def _clamp(cls, v: object) -> int:
        try:
            return _clamp_score(int(float(str(v))))
        except (TypeError, ValueError):
            return 0


# ------------------------------------------------------------ API boundary --


class ReviewRequest(BaseModel):
    repository_id: uuid.UUID
    pull_number: int = Field(ge=1, examples=[42])


class ReviewCreatedOut(BaseModel):
    """202 response: the review row (poll it) + the background job (poll its status)."""

    review_id: uuid.UUID
    job_id: uuid.UUID


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_path: str
    line_start: int | None
    line_end: int | None
    severity: Severity
    category: FindingCategory
    title: str
    rationale: str
    impact: str | None
    suggestion: str | None
    confidence: float | None


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pull_request_id: uuid.UUID
    status: ReviewStatus
    summary: str | None
    quality_score: int | None
    security_score: int | None
    complexity_score: int | None
    maintainability_score: int | None
    performance_score: int | None
    provider: str | None
    model: str | None
    created_at: datetime
    completed_at: datetime | None
    findings: list[FindingOut] = Field(default_factory=list)
