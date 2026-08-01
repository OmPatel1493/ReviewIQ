"""Job status endpoint — clients poll this after triggering async work."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import User
from app.modules.auth.dependencies import get_current_user
from app.repositories.job_repository import JobRepository
from app.repositories.repository_repository import RepositoryRepository
from app.schemas.job import JobOut

router = APIRouter()


@router.get("/{job_id}", response_model=JobOut, summary="Get a job's status")
async def get_job(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobOut:
    job = await JobRepository(db).get(job_id)
    # Ownership: a job is only visible to the owner of its repository. We return
    # 404 (not 403) so we don't reveal that someone else's job id exists.
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.repository_id is not None:
        repo = await RepositoryRepository(db).get(job.repository_id)
        if repo is None or repo.owner_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobOut.model_validate(job)
