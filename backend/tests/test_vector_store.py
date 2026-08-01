"""Unit tests for QdrantVectorStore.search — no Qdrant server required.

A fake AsyncQdrantClient stands in for the real one so we can assert the search
maps payloads into `SearchHit`s and scopes the query to a single repository.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.modules.search.vector_store import REPO_KEY, QdrantVectorStore, SearchHit


class _FakeResponse:
    def __init__(self, points: list[SimpleNamespace]) -> None:
        self.points = points


class _FakeQdrant:
    """Records the last query and returns canned points."""

    def __init__(self, points: list[SimpleNamespace], *, exists: bool = True) -> None:
        self._points = points
        self._exists = exists
        self.last_query: dict = {}

    async def collection_exists(self, collection_name: str) -> bool:
        return self._exists

    async def query_points(self, **kwargs) -> _FakeResponse:
        self.last_query = kwargs
        return _FakeResponse(self._points)

    async def close(self) -> None:  # pragma: no cover - not exercised here
        pass


def _point(file_path: str, score: float) -> SimpleNamespace:
    return SimpleNamespace(
        payload={
            "file_path": file_path,
            "start_line": 3,
            "end_line": 12,
            "content": f"# {file_path}\n...",
        },
        score=score,
    )


async def test_search_maps_payload_into_hits() -> None:
    fake = _FakeQdrant([_point("auth/middleware.py", 0.91), _point("api/login.py", 0.72)])
    store = QdrantVectorStore(client=fake)

    hits = await store.search("repo-123", [0.1] * 384, limit=5)

    assert [type(h) for h in hits] == [SearchHit, SearchHit]
    assert hits[0] == SearchHit(
        file_path="auth/middleware.py",
        start_line=3,
        end_line=12,
        content="# auth/middleware.py\n...",
        score=0.91,
    )
    # limit is forwarded and the query is scoped to the given repo id.
    assert fake.last_query["limit"] == 5
    condition = fake.last_query["query_filter"].must[0]
    assert condition.key == REPO_KEY
    assert condition.match.value == "repo-123"


async def test_search_returns_empty_when_collection_absent() -> None:
    fake = _FakeQdrant([], exists=False)
    store = QdrantVectorStore(client=fake)

    hits = await store.search("repo-123", [0.1] * 384, limit=5)

    assert hits == []
    # Never issued a query against a non-existent collection.
    assert fake.last_query == {}
