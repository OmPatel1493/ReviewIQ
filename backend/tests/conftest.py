"""Shared pytest fixtures.

`TestClient` wraps the ASGI app and drives it in-process (no real network),
so API tests are fast and hermetic. As the app grows we'll add fixtures here for
a throwaway database, a fake GitHub client, and a stub AI provider.
"""

from __future__ import annotations

import os

# Keep the suite hermetic: never inherit the developer's real .env OAuth credentials
# (local dev symlinks backend/.env -> the root .env). Environment variables take
# priority over the dotenv file in pydantic-settings, so forcing these empty *before*
# the app imports makes config-dependent tests deterministic regardless of .env.
os.environ["GITHUB_CLIENT_ID"] = ""
os.environ["GITHUB_CLIENT_SECRET"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)
