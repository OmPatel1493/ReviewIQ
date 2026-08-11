"""Ask-AI use-case: answer a natural-language question grounded in a repo's code.

Deliberately thin — it reuses Phase 5's `SearchService` for ownership + retrieval and
Phase 6's `LLMProvider` for the answer. Runs synchronously (a single LLM call), unlike
the batch review.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import User
from app.modules.ai.llm import LLMProvider, get_llm_provider
from app.modules.ask.prompt import SYSTEM_PROMPT, build_user_prompt
from app.modules.search.service import (
    RepositoryAccessError,
    RepositoryNotFoundError,
    SearchService,
)
from app.modules.search.vector_store import SearchHit

settings = get_settings()

# Re-exported so the router catches ownership errors without importing the search module.
__all__ = ["AskService", "RepositoryAccessError", "RepositoryNotFoundError"]


class AskService:
    def __init__(
        self,
        db: AsyncSession,
        user: User,
        *,
        search: SearchService | None = None,
        llm: LLMProvider | None = None,
    ) -> None:
        # Reuse search for ownership check + embed + Qdrant retrieval.
        self.search = search or SearchService(db, user)
        self.llm = llm or get_llm_provider()

    async def ask(
        self, repo_id: uuid.UUID, question: str, top_k: int | None = None
    ) -> tuple[str, list[SearchHit]]:
        hits = await self.search.search(
            repo_id, question, top_k or settings.ASK_CONTEXT_TOP_K
        )
        answer = await self.llm.generate_text(SYSTEM_PROMPT, build_user_prompt(question, hits))
        return answer, hits

    async def aclose(self) -> None:
        await self.search.aclose()
