"""Ask-AI endpoint (requires authentication)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import User
from app.modules.ai.llm import LLMError
from app.modules.ask.schemas import AskRequest, AskResponse, AskSource
from app.modules.ask.service import (
    AskService,
    RepositoryAccessError,
    RepositoryNotFoundError,
)
from app.modules.auth.dependencies import get_current_user

router = APIRouter()


def get_ask_service(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AskService:
    return AskService(db, user)


@router.post(
    "",
    response_model=AskResponse,
    summary="Ask a question about a repository (RAG-grounded)",
)
async def ask(
    body: AskRequest, svc: AskService = Depends(get_ask_service)
) -> AskResponse:
    try:
        answer, hits = await svc.ask(body.repository_id, body.question, body.top_k)
    except RepositoryNotFoundError:
        raise _not_found() from None
    except RepositoryAccessError:
        raise _forbidden() from None
    except LLMError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return AskResponse(
        question=body.question,
        answer=answer,
        sources=[AskSource.model_validate(h) for h in hits],
    )


# --------------------------------------------------------------- helpers ----
def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")


def _forbidden() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your repository")
