"""Phase 0 smoke tests — prove the app boots and the contract holds."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_root_banner(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "ReviewIQ"
    assert body["health"].endswith("/health")


def test_health_ok(client: TestClient) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app"] == "ReviewIQ"
    assert body["environment"] == "local"


def test_readiness_lists_components(client: TestClient) -> None:
    resp = client.get("/api/v1/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    # "ok" when Postgres is reachable, "degraded" when it isn't — both are valid
    # responses; the probe must not 500 either way.
    assert body["status"] in {"ok", "degraded"}
    component_names = {c["name"] for c in body["components"]}
    assert {"postgres", "redis", "qdrant"} <= component_names


def test_openapi_schema_served(client: TestClient) -> None:
    """The interactive docs power a big part of the 'no loopholes' story."""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    assert resp.json()["info"]["title"] == "ReviewIQ"
