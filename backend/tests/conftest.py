"""Shared pytest fixtures.

`TestClient` wraps the ASGI app and drives it in-process (no real network),
so API tests are fast and hermetic. As the app grows we'll add fixtures here for
a throwaway database, a fake GitHub client, and a stub AI provider.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)
