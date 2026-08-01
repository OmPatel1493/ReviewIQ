"""Health & readiness endpoints.

Two distinct probes, following the Kubernetes convention:

* **liveness** (`/health`)  — "is the process alive?" If this fails, restart me.
* **readiness** (`/health/ready`) — "are my dependencies reachable?" If this
  fails, stop routing traffic to me but don't necessarily restart.

Separating them prevents a transient DB blip from triggering a pod restart loop.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import redis.asyncio as aioredis
from fastapi import APIRouter
from qdrant_client import AsyncQdrantClient

from app.core.config import get_settings
from app.core.db import check_db
from app.schemas.common import ComponentStatus, HealthResponse, ReadinessResponse

router = APIRouter()
settings = get_settings()


async def _check_redis() -> bool:
    try:
        async with aioredis.from_url(settings.redis_url) as client:
            await client.ping()
        return True
    except Exception:
        return False


async def _check_qdrant() -> bool:
    client = AsyncQdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
    try:
        await client.get_collections()
        return True
    except Exception:
        return False
    finally:
        await client.close()


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
    # Ping all backing services concurrently.
    db_ok, redis_ok, qdrant_ok = await asyncio.gather(
        check_db(), _check_redis(), _check_qdrant()
    )
    components = [
        ComponentStatus(name="postgres", status="ok" if db_ok else "error"),
        ComponentStatus(name="redis", status="ok" if redis_ok else "error"),
        ComponentStatus(name="qdrant", status="ok" if qdrant_ok else "error"),
    ]
    # Degraded (not down) if any hard dependency is unreachable.
    overall = "ok" if all((db_ok, redis_ok, qdrant_ok)) else "degraded"
    return ReadinessResponse(status=overall, components=components)
