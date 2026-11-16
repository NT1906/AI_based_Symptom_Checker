"""Unit tests for the authentication API endpoints (/api/v1/auth).

Responsibilities:
    - Verify registration endpoint (201 Created, 409 Conflict, 422).
    - Verify login endpoint (200 OK, HttpOnly cookie, 401 on invalid credentials).
    - Verify logout endpoint (200 OK, cleared cookie).
    - Verify current user /me endpoint (200 with session, 401 when missing/invalid).
    - Verify cookie security attributes (Secure flag in staging/production).
    - Ensure password hashes and tokens never leak in JSON bodies or logs.

Owner: Vivek (tests) · Task: S2-VIV-1 · Requirements: FR-01, NFR-03, NFR-08
"""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_auth_service, get_session_factory
from app.core.config import Settings, get_settings
from app.models.base import Base
from app.services.auth.security import create_access_token
from app.services.auth.service import AuthService


@pytest.fixture
def test_db_session_factory() -> Iterator[sessionmaker[Session]]:
    """Create an isolated in-memory SQLite database session factory for API tests."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    yield factory
    engine.dispose()


@pytest.fixture
def auth_client(
    app: FastAPI,
    test_db_session_factory: sessionmaker[Session],
    test_settings: Settings,
) -> Iterator[TestClient]:
    """Provide TestClient with overridden database session factory and auth service."""
    app.dependency_overrides[get_session_factory] = lambda: test_db_session_factory
    app.dependency_overrides[get_auth_service] = lambda: AuthService(
        session_factory=test_db_session_factory,
        settings=test_settings,
    )
    with TestClient(app, raise_server_exceptions=True) as tc:
        yield tc
    app.dependency_overrides.pop(get_session_factory, None)
    app.dependency_overrides.pop(get_auth_service, None)


# ---------------------------------------------------------------------------
# Registration Endpoint Tests
# ---------------------------------------------------------------------------


def test_register_endpoint_returns_201_and_safe_user_read(
    auth_client: TestClient,
) -> None:
    """Verify POST /api/v1/auth/register creates user and returns 201 without hash."""
    payload = {
        "email": "Jane.Doe@Example.com",
        "password": "Password1234!",
    }
    response = auth_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert "id" in data
    # Normalized to lowercase
    assert data["email"] == "jane.doe@example.com"
    assert "createdAt" in data

    # Security check: Password and password_hash must never appear in response
    assert "password" not in data
    assert "passwordHash" not in data
    assert "password_hash" not in data


def test_register_endpoint_duplicate_email_returns_409(
    auth_client: TestClient,
) -> None:
    """Verify duplicate email registration returns 409 Conflict with uniform error."""
    payload = {
        "email": "duplicate@example.com",
        "password": "Password1234!",
    }
    resp1 = auth_client.post("/api/v1/auth/register", json=payload)
    assert resp1.status_code == status.HTTP_201_CREATED

    resp2 = auth_client.post("/api/v1/auth/register", json=payload)
    assert resp2.status_code == status.HTTP_409_CONFLICT

    data = resp2.json()
    assert data["code"] == "CONFLICT"
    assert "already exists" in data["message"]
    assert "requestId" in data


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {"email": "not-an-email", "password": "Password123!"},
        {"email": "@example.com", "password": "Password123!"},
        {"email": "user@example.com", "password": "short"},  # < 8 characters
        {"email": "user@example.com", "password": "        "},  # whitespace only
        {"password": "Password123!"},  # missing email
        {"email": "user@example.com"},  # missing password
    ],
)
def test_register_endpoint_invalid_payload_returns_422(
    auth_client: TestClient,
    invalid_payload: dict[str, Any],
) -> None:
    """Verify malformed email or password validation returns 422."""
    response = auth_client.post("/api/v1/auth/register", json=invalid_payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert data["code"] == "VALIDATION_ERROR"


# ---------------------------------------------------------------------------
# Login Endpoint Tests
# ---------------------------------------------------------------------------


def test_login_endpoint_sets_httponly_cookie_and_returns_200(
    auth_client: TestClient,
) -> None:
    """Verify POST /api/v1/auth/login sets HttpOnly, SameSite=Lax cookie."""
    # Register first
    auth_client.post(
        "/api/v1/auth/register",
        json={"email": "login.test@example.com", "password": "MySecretPassword123!"},
    )

    # Login
    response = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "login.test@example.com", "password": "MySecretPassword123!"},
    )
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["email"] == "login.test@example.com"
    # Never return password or expose JWT directly in JSON body
    assert "token" not in data
    assert "password" not in data
    assert "passwordHash" not in data

    # Verify cookie configuration
    cookie_header = response.headers.get("set-cookie")
    assert cookie_header is not None
    assert "auth_token=" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "SameSite=lax" in cookie_header or "samesite=lax" in cookie_header.lower()


def test_login_endpoint_sets_secure_cookie_in_production(
    app: FastAPI,
    test_db_session_factory: sessionmaker[Session],
) -> None:
    """Verify Secure cookie flag is set when running in production mode."""
    prod_settings = Settings(
        app_env="production",
        jwt_secret="production-secret-at-least-32-chars-long",
    )
    app.dependency_overrides[get_settings] = lambda: prod_settings
    app.dependency_overrides[get_session_factory] = lambda: test_db_session_factory
    app.dependency_overrides[get_auth_service] = lambda: AuthService(
        session_factory=test_db_session_factory,
        settings=prod_settings,
    )

    with TestClient(app, raise_server_exceptions=True) as prod_client:
        prod_client.post(
            "/api/v1/auth/register",
            json={"email": "prod.user@example.com", "password": "ProdPassword123!"},
        )
        response = prod_client.post(
            "/api/v1/auth/login",
            json={"email": "prod.user@example.com", "password": "ProdPassword123!"},
        )
        assert response.status_code == status.HTTP_200_OK
        cookie_header = response.headers.get("set-cookie")
        assert cookie_header is not None
        assert "Secure" in cookie_header or "secure" in cookie_header.lower()


def test_login_endpoint_wrong_password_returns_401(
    auth_client: TestClient,
) -> None:
    """Verify incorrect password returns 401 Unauthorized with safe message."""
    auth_client.post(
        "/api/v1/auth/register",
        json={"email": "wrong.pwd@example.com", "password": "CorrectPassword123!"},
    )

    response = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "wrong.pwd@example.com", "password": "IncorrectPassword1!"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["code"] == "UNAUTHORIZED"
    assert "Invalid email or password" in data["message"]


def test_login_endpoint_unknown_email_returns_401(
    auth_client: TestClient,
) -> None:
    """Verify unregistered email returns 401 with identical safe message."""
    response = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "SomePassword123!"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["code"] == "UNAUTHORIZED"
    assert "Invalid email or password" in data["message"]


# ---------------------------------------------------------------------------
# Logout Endpoint Tests
# ---------------------------------------------------------------------------


def test_logout_endpoint_clears_cookie_and_returns_200(
    auth_client: TestClient,
) -> None:
    """Verify POST /api/v1/auth/logout deletes the auth cookie."""
    # Authenticate first
    auth_client.post(
        "/api/v1/auth/register",
        json={"email": "logout.user@example.com", "password": "Password123!"},
    )
    login_resp = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "logout.user@example.com", "password": "Password123!"},
    )
    assert login_resp.status_code == status.HTTP_200_OK

    # Logout
    logout_resp = auth_client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == status.HTTP_200_OK
    data = logout_resp.json()
    assert data["status"] == "ok"
    assert data["message"] == "Successfully logged out"

    # Verify cookie is invalidated (max-age=0 or empty value)
    cookie_header = logout_resp.headers.get("set-cookie")
    assert cookie_header is not None
    assert 'auth_token=""' in cookie_header or "Max-Age=0" in cookie_header


# ---------------------------------------------------------------------------
# Current User (/me) Endpoint Tests
# ---------------------------------------------------------------------------


def test_get_current_user_profile_authenticated(
    auth_client: TestClient,
) -> None:
    """Verify GET /api/v1/auth/me returns user when session cookie is present."""
    reg_resp = auth_client.post(
        "/api/v1/auth/register",
        json={"email": "profile.user@example.com", "password": "Password123!"},
    )
    user_id = reg_resp.json()["id"]

    # Log in to set cookie in TestClient session
    auth_client.post(
        "/api/v1/auth/login",
        json={"email": "profile.user@example.com", "password": "Password123!"},
    )

    # Fetch profile
    response = auth_client.get("/api/v1/auth/me")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == user_id
    assert data["email"] == "profile.user@example.com"


def test_get_current_user_profile_unauthenticated_returns_401(
    auth_client: TestClient,
) -> None:
    """Verify GET /api/v1/auth/me returns 401 when no session cookie is provided."""
    response = auth_client.get("/api/v1/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["code"] == "UNAUTHORIZED"
    assert "Authentication session cookie missing" in data["message"]


def test_get_current_user_profile_expired_token_returns_401(
    app: FastAPI,
    auth_client: TestClient,
    test_settings: Settings,
) -> None:
    """Verify GET /api/v1/auth/me returns 401 when token is expired."""
    reg_resp = auth_client.post(
        "/api/v1/auth/register",
        json={"email": "expired.user@example.com", "password": "Password123!"},
    )
    user_id = reg_resp.json()["id"]

    from datetime import timedelta
    from uuid import UUID

    # Generate an expired token
    expired_token = create_access_token(
        user_id=UUID(user_id),
        email="expired.user@example.com",
        settings=test_settings,
        expires_delta=timedelta(seconds=-30),
    )

    auth_client.cookies.set("auth_token", expired_token)
    response = auth_client.get("/api/v1/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["code"] == "UNAUTHORIZED"
    assert "expired" in data["message"].lower()


# ---------------------------------------------------------------------------
# Privacy and Logging Guard Tests
# ---------------------------------------------------------------------------


def test_sensitive_credentials_never_appear_in_logs(
    auth_client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify plaintext password and password hash never appear in logs."""
    sensitive_password = "SuperSecretPlainTextPassword999!"
    with caplog.at_level("DEBUG"):
        auth_client.post(
            "/api/v1/auth/register",
            json={"email": "nologs@example.com", "password": sensitive_password},
        )
        auth_client.post(
            "/api/v1/auth/login",
            json={"email": "nologs@example.com", "password": sensitive_password},
        )

    logs_text = caplog.text
    assert sensitive_password not in logs_text
    assert "$argon2id$" not in logs_text
