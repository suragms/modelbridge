"""Tests for the liveness / readiness endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_healthy():
    """The liveness probe must report healthy without external dependencies."""
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"


def test_health_has_version():
    response = client.get("/health")
    assert "version" in response.json()


def test_root_returns_app_info():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "ModelBridge"


def test_readiness_returns_not_ready_without_dependencies():
    """Without reachable Postgres/Redis, readiness must report not_ready (503).

    The checks use short timeouts so a missing local dependency fails fast.
    """
    response = client.get("/ready")
    if response.status_code == 200:
        # Dependencies happened to be up (e.g. local dev services).
        assert response.json()["status"] == "ready"
    else:
        assert response.status_code == 503
        assert response.json()["status"] == "not_ready"
        assert "database" in response.json()["checks"]
        assert "redis" in response.json()["checks"]
