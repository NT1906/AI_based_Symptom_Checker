"""Tests for the health endpoint."""
from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_status_and_version(monkeypatch) -> None:
    """Health endpoint returns the configured version."""
    monkeypatch.setenv("APP_VERSION", "test-version")
    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        client = TestClient(create_app())
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "version": "test-version"}
    finally:
        get_settings.cache_clear()
