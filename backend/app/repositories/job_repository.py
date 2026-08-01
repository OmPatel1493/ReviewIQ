"""Data access + lifecycle transitions for background jobs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job
from app.models.enums import JobStatus, JobType


class JobRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        *,
        job_type: JobType,
        repository_id: uuid.UUID | None = None,
        pull_request_id: uuid.UUID | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Job:
        job = Job(
            type=job_type,
            status=JobStatus.QUEUED,
            repository_id=repository_id,
            pull_request_id=pull_request_id,
            payload=payload,
            progress=0,
        )
        self.db.add(job)
        await self.db.flush()
        return job

    async def get(self, job_id: uuid.UUID) -> Job | None:
        return await self.db.get(Job, job_id)

    async def mark_running(
        self, job_id: uuid.UUID, celery_task_id: str | None = None
    ) -> None:
        job = await self._require(job_id)
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(UTC)
        job.celery_task_id = celery_task_id
        await self.db.flush()

    async def set_progress(self, job_id: uuid.UUID, progress: int) -> None:
        job = await self._require(job_id)
        job.progress = max(0, min(100, progress))
        await self.db.flush()

    async def mark_succeeded(
        self, job_id: uuid.UUID, result: dict[str, Any] | None = None
    ) -> None:
        job = await self._require(job_id)
        job.status = JobStatus.SUCCEEDED
        job.progress = 100
        job.result = result
        job.finished_at = datetime.now(UTC)
        await self.db.flush()

    async def mark_failed(self, job_id: uuid.UUID, error: str) -> None:
        job = await self._require(job_id)
        job.status = JobStatus.FAILED
        job.error = error[:2000]
        job.finished_at = datetime.now(UTC)
        await self.db.flush()

    async def _require(self, job_id: uuid.UUID) -> Job:
        job = await self.db.get(Job, job_id)
        if job is None:
            raise ValueError(f"job {job_id} not found")
        return job
