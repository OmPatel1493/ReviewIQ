"""GitHub route auth-gating tests (DB stubbed; no Postgres needed)."""

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


@pytest.mark.parametrize(
    ("method", "path", "json"),
    [
        ("get", "/api/v1/repos", None),
        ("get", "/api/v1/repos/github", None),
        ("post", "/api/v1/repos/connect", {"full_name": "octo/demo"}),
        ("get", "/api/v1/repos/00000000-0000-0000-0000-000000000000", None),
        ("get", "/api/v1/repos/00000000-0000-0000-0000-000000000000/pulls", None),
        ("post", "/api/v1/repos/00000000-0000-0000-0000-000000000000/index", None),
        ("get", "/api/v1/jobs/00000000-0000-0000-0000-000000000000", None),
    ],
)
def test_repo_endpoints_require_auth(
    client_no_db: TestClient, method: str, path: str, json: dict | None
) -> None:
    resp = client_no_db.request(method, path, json=json)
    assert resp.status_code == 401, f"{method} {path} should require auth"


def test_connect_validates_full_name_format(client_no_db: TestClient) -> None:
    # Even unauthenticated, a malformed body must never be accepted. Depending on
    # dependency/body resolution order FastAPI returns 401 or 422 — never 2xx.
    resp = client_no_db.post("/api/v1/repos/connect", json={"full_name": "not-a-repo"})
    assert resp.status_code in {401, 422}
