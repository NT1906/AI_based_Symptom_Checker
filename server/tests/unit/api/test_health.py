"""Unit tests for the health check endpoint.

Responsibilities:
    - Verify GET /api/v1/health returns status ok and deployed version.
    - Test dependency overrides and dynamic version reporting.

Owner: Vivek (tests) · Task: S0-VIV-1 · Requirements: NFR-08
"""

from app.core.config import Settings, get_settings
from fastapi import FastAPI, status
from fastapi.testclient import TestClient


def test_health_returns_status_and_version(client: TestClient) -> None:
    """Verify that GET /api/v1/health returns HTTP 200 with status ok and version.

    Args:
        client: Synchronous HTTP test client.
    """
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "test-sha-12345"


def test_health_reflects_custom_version(app: FastAPI, client: TestClient) -> None:
    """Verify that custom version configured in settings is returned by the endpoint.

    Args:
        app: Test FastAPI application instance.
        client: Synchronous HTTP test client.
    """
    custom_settings = Settings(
        app_env="production",
        app_version="v0.1.0-release",
    )
    app.dependency_overrides[get_settings] = lambda: custom_settings

    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": "ok",
        "version": "v0.1.0-release",
    }


def test_health_rejects_invalid_methods(client: TestClient) -> None:
    """Verify non-GET requests to /api/v1/health are rejected with 405.

    Args:
        client: Synchronous HTTP test client.
    """
    post_response = client.post("/api/v1/health")
    assert post_response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    put_response = client.put("/api/v1/health")
    assert put_response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
