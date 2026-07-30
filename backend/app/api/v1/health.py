"""Health & readiness endpoints.

Two distinct probes, following the Kubernetes convention:

* **liveness** (`/health`)  — "is the process alive?" If this fails, restart me.
* **readiness** (`/health/ready`) — "are my dependencies reachable?" If this
  fails, stop routing traffic to me but don't necessarily restart.

Separating them prevents a transient DB blip from triggering a pod restart loop.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.db import check_db
from app.schemas.common import ComponentStatus, HealthResponse, ReadinessResponse

router = APIRouter()
settings = get_settings()


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.APP_NAME,
        environment=settings.ENVIRONMENT,
        version=settings.APP_VERSION,
        time=datetime.now(UTC),
    )


@router.get("/health/ready", response_model=ReadinessResponse, summary="Readiness probe")
async def readiness() -> ReadinessResponse:
    # Postgres is live as of Phase 1; Redis/Qdrant are wired in Phase 4.
    db_ok = await check_db()
    components = [
        ComponentStatus(
            name="postgres",
            status="ok" if db_ok else "error",
            detail=None if db_ok else "SELECT 1 failed",
        ),
        ComponentStatus(name="redis", status="skipped", detail="wired in Phase 4"),
        ComponentStatus(name="qdrant", status="skipped", detail="wired in Phase 4"),
    ]
    # Degraded (not down) if a hard dependency is unreachable.
    overall = "ok" if db_ok else "degraded"
    return ReadinessResponse(status=overall, components=components)
