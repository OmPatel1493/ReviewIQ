"""Analytics route auth-gating (DB stubbed; no Postgres needed)."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.db import get_db
from app.main import app


@pytest.fixture
def client_no_db() -> Iterator[TestClient]:
    async def _fake_db() -> AsyncGenerator[None, None]:
        yield None

    app.dependency_overrides[get_db] = _fake_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_analytics_overview_requires_auth(client_no_db: TestClient) -> None:
    resp = client_no_db.get("/api/v1/analytics/overview")
    assert resp.status_code == 401
