"""Review endpoints (all require authentication).

`POST /reviews` creates a pending review + a background job and returns 202 immediately;
the worker does the RAG+LLM analysis. `GET /reviews/{id}` returns the review + findings.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import PullRequest, Repository, Review, User
from app.models.enums import JobType
from app.modules.auth.dependencies import get_current_user
from app.modules.github.client import GitHubAPIError
from app.modules.review.schemas import (
    FindingOut,
    ReviewCreatedOut,
    ReviewOut,
    ReviewRequest,
)
from app.modules.review.service import (
    RepositoryAccessError,
    RepositoryNotFoundError,
    ReviewService,
)
from app.repositories.finding_repository import FindingRepository
from app.repositories.job_repository import JobRepository
from app.workers.tasks import review_pull_request_task

router = APIRouter()


def get_review_service(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ReviewService:
    return ReviewService(db, user)


@router.post(
    "",
    response_model=ReviewCreatedOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger an AI review of a pull request",
)
async def create_review(
    body: ReviewRequest,
    svc: ReviewService = Depends(get_review_service),
    db: AsyncSession = Depends(get_db),
) -> ReviewCreatedOut:
    try:
        review, repo = await svc.create_pending_review(body.repository_id, body.pull_number)
    except RepositoryNotFoundError:
        raise _not_found() from None
    except RepositoryAccessError:
        raise _forbidden() from None
    except GitHubAPIError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    job = await JobRepository(db).create(
        job_type=JobType.REVIEW,
        repository_id=repo.id,
        pull_request_id=review.pull_request_id,
        payload={"review_id": str(review.id)},
    )
    # Commit so the worker sees both rows before it starts (avoids a race).
    await db.commit()
    review_pull_request_task.delay(str(job.id), str(review.id))
    return ReviewCreatedOut(review_id=review.id, job_id=job.id)


@router.get(
    "/{review_id}",
    response_model=ReviewOut,
    summary="Get a review with its findings",
)
async def get_review(
    review_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewOut:
    review = await db.get(Review, review_id)
    if review is None:
        raise _not_found_review()
    # Ownership via pull_request → repository → owner. 404 (not 403) hides existence.
    pr = await db.get(PullRequest, review.pull_request_id)
    repo = await db.get(Repository, pr.repository_id) if pr is not None else None
    if repo is None or repo.owner_id != user.id:
        raise _not_found_review()

    findings = await FindingRepository(db).list_by_review(review_id)
    # Build explicitly so we never trigger a lazy load on review.findings in async.
    return ReviewOut(
        id=review.id,
        pull_request_id=review.pull_request_id,
        status=review.status,
        summary=review.summary,
        quality_score=review.quality_score,
        security_score=review.security_score,
        complexity_score=review.complexity_score,
        maintainability_score=review.maintainability_score,
        performance_score=review.performance_score,
        provider=review.provider,
        model=review.model,
        created_at=review.created_at,
        completed_at=review.completed_at,
        findings=[FindingOut.model_validate(f) for f in findings],
    )


# --------------------------------------------------------------- helpers ----
def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")


def _forbidden() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your repository")


def _not_found_review() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
