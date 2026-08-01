"""Celery application.

Redis is both the broker (queue that hands jobs to workers) and the result backend.
Run a worker with:

    uv run celery -A app.workers.celery_app worker --loglevel=info

Tasks are enqueued from the API (`task.delay(...)`) and executed here, off the request
path — so cloning + embedding a repo never blocks an HTTP request.
"""

from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "reviewiq",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # EAGER = run inline in the caller (no separate worker); used in tests/local.
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=True,
)

# Import task modules so their @celery_app.task functions register on this app.
from app.workers import tasks as _tasks  # noqa: E402,F401
