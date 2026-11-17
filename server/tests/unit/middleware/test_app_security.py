"""Verify protection through the actual app factory and registered routes.

Owner: Harsh · Task: S2-HAR-5 · Issue: #208 · Requirement: NFR-03
"""

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.core.config import Settings

from app.main import create_app
from app.middleware.security_headers import SECURITY_HEADERS


def test_app_auth_limit_is_shared_and_cannot_be_spoofed() -> None:
    """Invalid login attempts consume the same quota as register and refresh."""
    app = create_app()
    with TestClient(app) as client:
        for _ in range(10):
            response = client.post("/api/v1/auth/login", json={})
            assert response.status_code == 422
        for path in ("register", "refresh", "logout"):
            response = client.post(
                f"/api/v1/auth/{path}",
                json={},
                headers={"X-Forwarded-For": "203.0.113.123"},
            )
            assert response.status_code == 429
            assert int(response.headers["retry-after"]) > 0
            assert response.headers["x-request-id"]
            for header, value in SECURITY_HEADERS.items():
                assert response.headers[header] == value
        assert client.get("/api/v1/health").status_code == 200
        assert client.get("/api/v1/assessments/not-a-uuid").status_code == 422


def test_app_assessment_limit_is_shared_and_instances_are_isolated() -> None:
    """Switching assessment IDs does not reset quota, and app stores are isolated."""
    with TestClient(create_app()) as client:
        for index in range(60):
            assert client.get(f"/api/v1/assessments/fake-{index}").status_code == 422
        limited = client.post("/api/v1/assessments", json={})
        assert limited.status_code == 429
    with TestClient(create_app()) as fresh:
        assert fresh.post("/api/v1/assessments", json={}).status_code == 422


def test_app_headers_cover_normal_and_error_responses() -> None:
    """Check real health, validation, missing and unhandled error responses."""
    app = create_app()

    @app.get("/fixture-failure")
    def fail() -> None:
        raise RuntimeError("Fictional failure")

    # No lifespan needed for routes which do not access the database.
    with TestClient(app, raise_server_exceptions=False) as client:
        for path in ("/api/v1/health", "/missing", "/fixture-failure"):
            response = client.get(path)
            if path == "/fixture-failure":
                assert response.status_code == 500
            for header, value in SECURITY_HEADERS.items():
                assert response.headers[header] == value


def test_app_enables_hsts_for_https_staging(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTPS staging health responses carry the configured transport policy."""
    monkeypatch.setattr(
        main_module, "get_settings", lambda: Settings(app_env="staging")
    )
    client = TestClient(create_app(), base_url="https://staging.example.test")
    try:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.headers["strict-transport-security"] == "max-age=31536000"
    finally:
        client.close()
