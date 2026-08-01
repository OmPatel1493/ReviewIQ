"""Qdrant vector store wrapper.

All vector operations go through this class so the collection name, distance metric,
and payload shape live in one place. The float vectors live here in Qdrant (built for
approximate-nearest-neighbour search); PostgreSQL keeps the relational metadata and the
`vector_id` that links a row back to its point here.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from qdrant_client import AsyncQdrantClient, models

from app.core.config import get_settings

settings = get_settings()

# Qdrant payload key we filter on to scope search/deletes to a single repository.
REPO_KEY = "repository_id"


@dataclass(frozen=True)
class SearchHit:
    """One nearest-neighbour match, reconstructed from a point's payload so the
    caller never touches Qdrant types. `score` is cosine similarity (higher = closer)."""

    file_path: str
    start_line: int
    end_line: int
    content: str
    score: float


def make_point(
    point_id: uuid.UUID,
    vector: list[float],
    *,
    repo_id: str,
    file_path: str,
    start_line: int,
    end_line: int,
    content: str,
) -> models.PointStruct:
    """Build a Qdrant point. We store the chunk text in the payload so search can
    return snippets without a second round-trip to Postgres."""
    return models.PointStruct(
        id=str(point_id),
        vector=vector,
        payload={
            REPO_KEY: repo_id,
            "file_path": file_path,
            "start_line": start_line,
            "end_line": end_line,
            "content": content,
        },
    )


class QdrantVectorStore:
    def __init__(self, client: AsyncQdrantClient | None = None) -> None:
        self._owns_client = client is None
        self._client = client or AsyncQdrantClient(
            host=settings.QDRANT_HOST, port=settings.QDRANT_PORT
        )
        self.collection = settings.QDRANT_COLLECTION

    async def ensure_collection(self) -> None:
        """Create the collection on first use (idempotent)."""
        if not await self._client.collection_exists(self.collection):
            await self._client.create_collection(
                collection_name=self.collection,
                vectors_config=models.VectorParams(
                    size=settings.EMBEDDING_DIM, distance=models.Distance.COSINE
                ),
            )

    async def upsert(self, points: list[models.PointStruct]) -> None:
        if points:
            await self._client.upsert(collection_name=self.collection, points=points)

    async def search(
        self, repo_id: str, query_vector: list[float], limit: int
    ) -> list[SearchHit]:
        """Return the `limit` nearest chunks to `query_vector` within one repository.

        Scoped to `repo_id` via the same payload filter used for deletes, so users
        only ever see results from their own indexed code. Returns an empty list if
        nothing has been indexed yet (collection absent), rather than raising."""
        if not await self._client.collection_exists(self.collection):
            return []
        response = await self._client.query_points(
            collection_name=self.collection,
            query=query_vector,
            query_filter=self._repo_filter(repo_id),
            limit=limit,
            with_payload=True,
        )
        hits: list[SearchHit] = []
        for point in response.points:
            payload = point.payload or {}
            hits.append(
                SearchHit(
                    file_path=str(payload.get("file_path", "")),
                    start_line=int(payload.get("start_line", 0)),
                    end_line=int(payload.get("end_line", 0)),
                    content=str(payload.get("content", "")),
                    score=float(point.score),
                )
            )
        return hits

    async def delete_by_repo(self, repo_id: str) -> None:
        await self._client.delete(
            collection_name=self.collection,
            points_selector=models.FilterSelector(
                filter=self._repo_filter(repo_id)
            ),
        )

    async def count_by_repo(self, repo_id: str) -> int:
        result = await self._client.count(
            collection_name=self.collection, count_filter=self._repo_filter(repo_id)
        )
        return result.count

    @staticmethod
    def _repo_filter(repo_id: str) -> models.Filter:
        return models.Filter(
            must=[models.FieldCondition(key=REPO_KEY, match=models.MatchValue(value=repo_id))]
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.close()
