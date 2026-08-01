"""Semantic code-search endpoint (requires authentication)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import User
from app.modules.auth.dependencies import get_current_user
from app.modules.search.schemas import (
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from app.modules.search.service import (
    RepositoryAccessError,
    RepositoryNotFoundError,
    SearchService,
)

router = APIRouter()


def get_search_service(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> SearchService:
    """Build a per-request service bound to the authenticated user."""
    return SearchService(db, user)


@router.post(
    "",
    response_model=SearchResponse,
    summary="Semantic code search within a repository",
)
async def search_code(
    body: SearchRequest, svc: SearchService = Depends(get_search_service)
) -> SearchResponse:
    try:
        hits = await svc.search(body.repository_id, body.query, body.limit)
    except RepositoryNotFoundError:
        raise _not_found() from None
    except RepositoryAccessError:
        raise _forbidden() from None
    return SearchResponse(
        repository_id=body.repository_id,
        query=body.query,
        results=[SearchResultItem.model_validate(h) for h in hits],
    )


# --------------------------------------------------------------- helpers ----
def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")


def _forbidden() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your repository")
