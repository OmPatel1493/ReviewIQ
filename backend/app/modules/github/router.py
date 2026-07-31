"""Repository & pull-request endpoints (all require authentication)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import User
from app.modules.auth.dependencies import get_current_user
from app.modules.github.client import GitHubAPIError
from app.modules.github.service import (
    GitHubService,
    RepositoryAccessError,
    RepositoryNotFoundError,
)
from app.schemas.pull_request import ChangedFileOut, PullRequestOut
from app.schemas.repository import (
    ConnectRepositoryRequest,
    GitHubRepoOut,
    RepositoryOut,
)

router = APIRouter()


def get_github_service(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> GitHubService:
    """Build a per-request service bound to the authenticated user."""
    return GitHubService(db, user)


# GitHub upstream errors become 502 (we're a healthy gateway to an unhealthy upstream).
def _github_error(exc: GitHubAPIError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


@router.get("/github", response_model=list[GitHubRepoOut], summary="List connectable GitHub repos")
async def list_github_repositories(
    svc: GitHubService = Depends(get_github_service),
) -> list[GitHubRepoOut]:
    try:
        repos = await svc.list_remote_repositories()
    except GitHubAPIError as exc:
        raise _github_error(exc) from exc
    return [GitHubRepoOut.from_gh(r) for r in repos]


@router.get("", response_model=list[RepositoryOut], summary="List connected repositories")
async def list_connected_repositories(
    svc: GitHubService = Depends(get_github_service),
) -> list[RepositoryOut]:
    repos = await svc.list_connected_repositories()
    return [RepositoryOut.model_validate(r) for r in repos]


@router.post(
    "/connect",
    response_model=RepositoryOut,
    status_code=status.HTTP_201_CREATED,
    summary="Connect a repository",
)
async def connect_repository(
    body: ConnectRepositoryRequest,
    svc: GitHubService = Depends(get_github_service),
) -> RepositoryOut:
    try:
        repo = await svc.connect_repository(body.full_name)
    except GitHubAPIError as exc:
        raise _github_error(exc) from exc
    return RepositoryOut.model_validate(repo)


@router.get("/{repo_id}", response_model=RepositoryOut, summary="Get a connected repository")
async def get_repository(
    repo_id: uuid.UUID, svc: GitHubService = Depends(get_github_service)
) -> RepositoryOut:
    repo = await _resolve_repo(svc, repo_id)
    return RepositoryOut.model_validate(repo)


@router.get(
    "/{repo_id}/pulls",
    response_model=list[PullRequestOut],
    summary="Sync & list a repository's pull requests",
)
async def list_pull_requests(
    repo_id: uuid.UUID, svc: GitHubService = Depends(get_github_service)
) -> list[PullRequestOut]:
    try:
        pulls = await svc.sync_pull_requests(repo_id)
    except RepositoryNotFoundError:
        raise _not_found() from None
    except RepositoryAccessError:
        raise _forbidden() from None
    except GitHubAPIError as exc:
        raise _github_error(exc) from exc
    return [PullRequestOut.model_validate(p) for p in pulls]


@router.get(
    "/{repo_id}/pulls/{number}/files",
    response_model=list[ChangedFileOut],
    summary="Changed files (with diffs) for a pull request",
)
async def list_pull_request_files(
    repo_id: uuid.UUID, number: int, svc: GitHubService = Depends(get_github_service)
) -> list[ChangedFileOut]:
    try:
        files = await svc.get_pull_request_files(repo_id, number)
    except RepositoryNotFoundError:
        raise _not_found() from None
    except RepositoryAccessError:
        raise _forbidden() from None
    except GitHubAPIError as exc:
        raise _github_error(exc) from exc
    return [ChangedFileOut.model_validate(f) for f in files]


# --------------------------------------------------------------- helpers ----
async def _resolve_repo(svc: GitHubService, repo_id: uuid.UUID):
    try:
        return await svc.get_connected_repository(repo_id)
    except RepositoryNotFoundError:
        raise _not_found() from None
    except RepositoryAccessError:
        raise _forbidden() from None


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")


def _forbidden() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your repository")
