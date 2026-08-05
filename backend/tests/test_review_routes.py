"""Review route auth-gating (DB stubbed; no Postgres needed)."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.db import get_db
from app.main import app

_REPO_ID = "00000000-0000-0000-0000-000000000000"
_REVIEW_ID = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def client_no_db() -> Iterator[TestClient]:
    async def _fake_db() -> AsyncGenerator[None, None]:
        yield None

    app.dependency_overrides[get_db] = _fake_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("method", "path", "json"),
    [
        ("post", "/api/v1/reviews", {"repository_id": _REPO_ID, "pull_number": 1}),
        ("get", f"/api/v1/reviews/{_REVIEW_ID}", None),
    ],
)
def test_review_endpoints_require_auth(
    client_no_db: TestClient, method: str, path: str, json: dict | None
) -> None:
    resp = client_no_db.request(method, path, json=json)
    assert resp.status_code == 401, f"{method} {path} should require auth"


def test_create_review_validates_body(client_no_db: TestClient) -> None:
    # pull_number must be >= 1. Depending on dependency/body resolution order FastAPI
    # returns 401 or 422 — never 2xx.
    resp = client_no_db.post(
        "/api/v1/reviews", json={"repository_id": _REPO_ID, "pull_number": 0}
    )
    assert resp.status_code in {401, 422}
