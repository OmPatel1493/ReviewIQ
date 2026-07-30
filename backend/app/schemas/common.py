"""Shared response schemas used across the API.

Pydantic models here define the *contract* between the backend and any client.
Because FastAPI derives the OpenAPI docs from these, keeping them tidy gives us
accurate, self-documenting API docs for free.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Liveness payload — 'is the process up and serving?'"""

    status: str = Field(examples=["ok"])
    app: str = Field(examples=["ReviewIQ"])
    environment: str = Field(examples=["local"])
    version: str = Field(examples=["0.1.0"])
    time: datetime


class ComponentStatus(BaseModel):
    """Health of a single downstream dependency."""

    name: str
    status: str  # "ok" | "error" | "skipped"
    detail: str | None = None


class ReadinessResponse(BaseModel):
    """Readiness payload — 'can we serve traffic (deps reachable)?'

    In Phase 0 the dependency checks are placeholders; from Phase 1/4 we wire in
    real Postgres / Redis / Qdrant pings so orchestrators can gate traffic.
    """

    status: str  # "ok" | "degraded"
    components: list[ComponentStatus]
