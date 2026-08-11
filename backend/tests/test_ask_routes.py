"""Ask-AI route auth-gating (DB stubbed; no Postgres needed)."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.db import get_db
from app.main import app

_REPO_ID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture
def client_no_db() -> Iterator[TestClient]:
    async def _fake_db() -> AsyncGenerator[None, None]:
        yield None

    app.dependency_overrides[get_db] = _fake_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_ask_requires_auth(client_no_db: TestClient) -> None:
    resp = client_no_db.post(
        "/api/v1/ask",
        json={"repository_id": _REPO_ID, "question": "how does auth work?"},
    )
    assert resp.status_code == 401


def test_ask_validates_body(client_no_db: TestClient) -> None:
    # A blank question must never be accepted (401 or 422, never 2xx).
    resp = client_no_db.post(
        "/api/v1/ask", json={"repository_id": _REPO_ID, "question": ""}
    )
    assert resp.status_code in {401, 422}
