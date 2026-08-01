"""Semantic search use-case: turn a natural-language query into ranked code chunks.

Reuses the retrieval foundation built in Phase 4 — the same embedding model that
indexed the repo embeds the query, and the same Qdrant collection is queried, scoped
to the caller's repository. The review engine (Phase 6) will reuse this retrieval to
pull context for the LLM.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import User
from app.modules.ai.embeddings import EmbeddingProvider, get_embedding_provider
from app.modules.search.vector_store import QdrantVectorStore, SearchHit
from app.repositories.repository_repository import RepositoryRepository

settings = get_settings()


class RepositoryNotFoundError(Exception):
    """No such repository for this user."""


class RepositoryAccessError(Exception):
    """The repository exists but is owned by a different user."""


class SearchService:
    def __init__(
        self,
        db: AsyncSession,
        user: User,
        vector_store: QdrantVectorStore | None = None,
        embedder: EmbeddingProvider | None = None,
    ) -> None:
        self.db = db
        self.user = user
        self.repos = RepositoryRepository(db)
        # Injected collaborators default to the real ones (tests pass fakes).
        self.vs = vector_store or QdrantVectorStore()
        self.embedder = embedder or get_embedding_provider()

    async def search(
        self, repo_id: uuid.UUID, query: str, limit: int | None = None
    ) -> list[SearchHit]:
        """Embed the query with the same model used at index time and return the
        nearest chunks within the caller's repository."""
        repo = await self._owned_repository(repo_id)
        top_k = limit or settings.SEARCH_TOP_K
        # embed() is batch-oriented; a single query is a one-element batch.
        query_vector = self.embedder.embed([query])[0]
        return await self.vs.search(str(repo.id), query_vector, top_k)

    async def _owned_repository(self, repo_id: uuid.UUID):
        repo = await self.repos.get(repo_id)
        if repo is None:
            raise RepositoryNotFoundError
        if repo.owner_id != self.user.id:
            # Don't reveal existence to non-owners.
            raise RepositoryAccessError
        return repo

    async def aclose(self) -> None:
        await self.vs.aclose()
