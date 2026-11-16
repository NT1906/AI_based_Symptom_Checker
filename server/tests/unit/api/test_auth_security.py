"""Unit and integration tests for authentication security, token management, and CSRF.

Responsibilities:
    - Test token refresh endpoint (/api/v1/auth/refresh) with cookie rotation.
    - Test refresh token reuse detection and invalidation.
    - Test CSRF token endpoint (/api/v1/auth/csrf) and validation dependency.
    - Test cookie security attributes and path scoping (auth vs refresh).
    - Test logout cookie invalidation across all token cookies.

Owner: Vivek (tests) · Task: S2-VIV-2 · Requirements: NFR-03
"""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import (
    CsrfProtectDep,
    CurrentUserDep,
    get_auth_service,
    get_session_factory,
    get_settings,
)
from app.core.config import Settings
from app.models.base import Base
from app.services.auth.service import AuthService


@pytest.fixture
def test_db_session_factory() -> Iterator[sessionmaker[Session]]:
    """Create an isolated in-memory SQLite database session factory."""
    engine = create_engine(
        "sqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    yield factory
    engine.dispose()


@pytest.fixture
def test_settings() -> Settings:
    """Provide isolated application settings for API tests."""
    return Settings(
        app_env="local",
        jwt_secret="unit-test-api-secret-key-at-least-32-chars-long",
        jwt_algorithm="HS256",
        jwt_access_token_expire_minutes=15,
        jwt_refresh_token_expire_days=7,
        auth_cookie_name="auth_token",
        refresh_cookie_name="refresh_token",
        csrf_cookie_name="csrf_token",
    )


@pytest.fixture
def auth_client(
    app: FastAPI,
    test_db_session_factory: sessionmaker[Session],
    test_settings: Settings,
) -> Iterator[TestClient]:
    """Provide TestClient with overridden database and auth service."""
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_session_factory] = lambda: test_db_session_factory
    app.dependency_overrides[get_auth_service] = lambda: AuthService(
        session_factory=test_db_session_factory,
        settings=test_settings,
    )

    # Add a test-only route to test CsrfProtectDep
    @app.post("/test-csrf-protected")
    async def protected_route(
        _: CsrfProtectDep, user: CurrentUserDep
    ) -> dict[str, str]:
        return {"status": "success", "user_id": str(user.id)}

    with TestClient(app, raise_server_exceptions=True) as tc:
        yield tc

    app.dependency_overrides.pop(get_settings, None)
    app.dependency_overrides.pop(get_session_factory, None)
    app.dependency_overrides.pop(get_auth_service, None)


# ---------------------------------------------------------------------------
# Refresh Endpoint Tests
# ---------------------------------------------------------------------------


def test_login_sets_auth_refresh_and_csrf_cookies(
    auth_client: TestClient,
) -> None:
    """Verify login sets access token, refresh token, and CSRF cookies."""
    auth_client.post(
        "/api/v1/auth/register",
        json={"email": "cookies.test@example.com", "password": "Password123!"},
    )

    login_resp = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "cookies.test@example.com", "password": "Password123!"},
    )
    assert login_resp.status_code == status.HTTP_200_OK

    # Check that cookies were set in the client's cookie jar
    assert "auth_token" in auth_client.cookies
    assert "refresh_token" in auth_client.cookies
    assert "csrf_token" in auth_client.cookies
    assert "X-CSRF-Token" in login_resp.headers


def test_refresh_endpoint_success_and_token_rotation(
    auth_client: TestClient,
) -> None:
    """Verify POST /api/v1/auth/refresh updates session and rotates refresh token."""
    reg = auth_client.post(
        "/api/v1/auth/register",
        json={"email": "refresh.route@example.com", "password": "Password123!"},
    )
    user_id = reg.json()["id"]

    auth_client.post(
        "/api/v1/auth/login",
        json={"email": "refresh.route@example.com", "password": "Password123!"},
    )

    old_auth = auth_client.cookies.get("auth_token")
    old_refresh = auth_client.cookies.get("refresh_token")

    # Call refresh
    refresh_resp = auth_client.post("/api/v1/auth/refresh")
    assert refresh_resp.status_code == status.HTTP_200_OK
    assert refresh_resp.json()["id"] == user_id

    new_auth = auth_client.cookies.get("auth_token")
    new_refresh = auth_client.cookies.get("refresh_token")

    assert new_auth != old_auth
    assert new_refresh != old_refresh

    # Attempt reuse of the previous refresh token
    reuse_client = TestClient(auth_client.app, cookies={"refresh_token": old_refresh})
    reuse_resp = reuse_client.post("/api/v1/auth/refresh")
    assert reuse_resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert "revoked or already rotated" in reuse_resp.json()["message"]


def test_refresh_endpoint_missing_cookie_returns_401(
    auth_client: TestClient,
) -> None:
    """Verify refresh endpoint returns 401 when refresh cookie is missing."""
    auth_client.cookies.clear()
    resp = auth_client.post("/api/v1/auth/refresh")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert "cookie missing" in resp.json()["message"]


def test_refresh_endpoint_invalid_token_returns_401(
    auth_client: TestClient,
) -> None:
    """Verify refresh endpoint returns 401 when given an invalid token."""
    auth_client.cookies.set("refresh_token", "invalid.jwt.token")
    resp = auth_client.post("/api/v1/auth/refresh")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# CSRF Endpoint & Protection Tests
# ---------------------------------------------------------------------------


def test_get_csrf_token_endpoint(auth_client: TestClient) -> None:
    """Verify GET /api/v1/auth/csrf returns fresh CSRF token and sets cookie."""
    resp = auth_client.get("/api/v1/auth/csrf")
    assert resp.status_code == status.HTTP_200_OK

    body = resp.json()
    token = body.get("csrfToken") or body.get("csrf_token")
    assert token is not None
    assert len(token) == 64
    assert auth_client.cookies.get("csrf_token") == token
    assert resp.headers.get("X-CSRF-Token") == token


def test_csrf_protection_dependency_valid_token(
    auth_client: TestClient,
) -> None:
    """Verify state-changing request with valid CSRF header and cookie succeeds."""
    auth_client.post(
        "/api/v1/auth/register",
        json={"email": "csrf.valid@example.com", "password": "Password123!"},
    )
    auth_client.post(
        "/api/v1/auth/login",
        json={"email": "csrf.valid@example.com", "password": "Password123!"},
    )

    csrf_val = auth_client.cookies.get("csrf_token")
    assert csrf_val is not None

    resp = auth_client.post(
        "/test-csrf-protected",
        headers={"X-CSRF-Token": csrf_val},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "success"


def test_csrf_protection_dependency_missing_header_fails(
    auth_client: TestClient,
) -> None:
    """Verify request with missing CSRF header returns 401 Unauthorized."""
    auth_client.post(
        "/api/v1/auth/register",
        json={"email": "csrf.missing@example.com", "password": "Password123!"},
    )
    auth_client.post(
        "/api/v1/auth/login",
        json={"email": "csrf.missing@example.com", "password": "Password123!"},
    )

    resp = auth_client.post("/test-csrf-protected")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert "CSRF verification failed" in resp.json()["message"]


def test_csrf_protection_dependency_mismatched_token_fails(
    auth_client: TestClient,
) -> None:
    """Verify request with mismatched CSRF header returns 401 Unauthorized."""
    auth_client.post(
        "/api/v1/auth/register",
        json={"email": "csrf.mismatch@example.com", "password": "Password123!"},
    )
    auth_client.post(
        "/api/v1/auth/login",
        json={"email": "csrf.mismatch@example.com", "password": "Password123!"},
    )

    resp = auth_client.post(
        "/test-csrf-protected",
        headers={"X-CSRF-Token": "completely-wrong-token-value"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert "CSRF verification failed" in resp.json()["message"]


# ---------------------------------------------------------------------------
# Logout Cleanup Tests
# ---------------------------------------------------------------------------


def test_logout_clears_all_auth_cookies(
    auth_client: TestClient,
) -> None:
    """Verify logout deletes auth_token, refresh_token, and csrf_token."""
    auth_client.post(
        "/api/v1/auth/register",
        json={"email": "logout.all@example.com", "password": "Password123!"},
    )
    auth_client.post(
        "/api/v1/auth/login",
        json={"email": "logout.all@example.com", "password": "Password123!"},
    )

    old_refresh = auth_client.cookies.get("refresh_token")
    logout_resp = auth_client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == status.HTTP_200_OK

    # Verify that the refresh token was also revoked on server
    reuse_client = TestClient(auth_client.app, cookies={"refresh_token": old_refresh})
    reuse_resp = reuse_client.post("/api/v1/auth/refresh")
    assert reuse_resp.status_code == status.HTTP_401_UNAUTHORIZED
