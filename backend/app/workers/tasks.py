"""Celery task definitions."""

from __future__ import annotations

import asyncio
from typing import Any

from app.workers.celery_app import celery_app
from app.workers.runner import run_index_job, run_review_job


@celery_app.task(name="index_repository", bind=True)
def index_repository_task(self, job_id: str, repo_id: str) -> dict[str, Any]:  # noqa: ANN001
    """Clone + index a repository. Runs the async pipeline in a fresh event loop."""
    return asyncio.run(
        run_index_job(job_id=job_id, repo_id=repo_id, celery_task_id=self.request.id)
    )


@celery_app.task(name="review_pull_request", bind=True)
def review_pull_request_task(self, job_id: str, review_id: str) -> dict[str, Any]:  # noqa: ANN001
    """RAG + LLM review of a pull request. Runs the async pipeline in a fresh event loop."""
    return asyncio.run(
        run_review_job(
            job_id=job_id, review_id=review_id, celery_task_id=self.request.id
        )
    )
