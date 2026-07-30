"""Enumerated types used across models.

We use `StrEnum` so values serialize as readable strings in JSON/logs, and map them
to native PostgreSQL `ENUM` types (SQLAlchemy does this automatically via `Enum(...)`).
Native enums give DB-level validation — an invalid status literally cannot be stored.
"""

from __future__ import annotations

from enum import StrEnum


class IndexStatus(StrEnum):
    """Where a repository is in the clone/embed/index pipeline."""

    PENDING = "pending"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"


class PRState(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingCategory(StrEnum):
    """The kinds of issues the review engine can raise."""

    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    COMPLEXITY = "complexity"
    DUPLICATION = "duplication"
    STYLE = "style"
    BEST_PRACTICE = "best_practice"
    EDGE_CASE = "edge_case"


class JobType(StrEnum):
    CLONE = "clone"
    INDEX = "index"
    REVIEW = "review"
    REPORT = "report"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
