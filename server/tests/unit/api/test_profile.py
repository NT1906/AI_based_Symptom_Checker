"""Unit and integration tests for Profile API endpoints (FR-02).

Responsibilities:
    - Test GET /api/v1/profile for unauthenticated, uninitialized,
      and initialized users.
    - Test PUT /api/v1/profile for creating, updating, and validating profile data.
    - Test PATCH /api/v1/profile for partial updates.
    - Test DELETE /api/v1/profile for resetting profile context.
    - Test input validation rejecting invalid clinical age bands and sexes.
    - Test user isolation ensuring users cannot see or modify each other's profiles.
    - Verify Cache-Control: no-store on all responses.

Owner: Vivek (tests) · Task: S2-VIV-3 · Requirements: FR-02, idea § 10
"""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import (
    get_auth_service,
    get_profile_service,
    get_session_factory,
    get_settings,
)
from app.core.config import Settings
from app.models.base import Base
from app.services.auth.service import AuthService
from app.services.profile.service import ProfileService


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
    factory = sessionmaker(bind=engine, expire_on_commit=False)
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
def profile_client(
    app: FastAPI,
    test_db_session_factory: sessionmaker[Session],
    test_settings: Settings,
) -> Iterator[TestClient]:
    """Provide TestClient with overridden database and profile/auth services."""
    auth_svc = AuthService(
        session_factory=test_db_session_factory,
        settings=test_settings,
    )
    profile_svc = ProfileService(session_factory=test_db_session_factory)

    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_session_factory] = lambda: test_db_session_factory
    app.dependency_overrides[get_auth_service] = lambda: auth_svc
    app.dependency_overrides[get_profile_service] = lambda: profile_svc

    with TestClient(app, raise_server_exceptions=True) as tc:
        yield tc

    app.dependency_overrides.clear()


def _register_and_login(
    client: TestClient, email: str = "patient@example.com"
) -> dict[str, str]:
    """Register and login a user, returning the cookies."""
    password = "StrongPassword123!"
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert reg_resp.status_code == status.HTTP_201_CREATED

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == status.HTTP_200_OK
    return dict(login_resp.cookies)


def test_get_profile_unauthenticated_fails_401(profile_client: TestClient) -> None:
    """Unauthenticated GET /api/v1/profile fails with HTTP 401."""
    resp = profile_client.get("/api/v1/profile")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    data = resp.json()
    assert "error" in data or "detail" in data or "code" in data


def test_get_profile_uninitialized_returns_empty_200(
    profile_client: TestClient,
) -> None:
    """Reading an uninitialized profile returns HTTP 200 with clean empty fields."""
    cookies = _register_and_login(profile_client, "new_user@example.com")
    resp = profile_client.get("/api/v1/profile", cookies=cookies)

    assert resp.status_code == status.HTTP_200_OK
    assert resp.headers.get("Cache-Control") == "no-store"
    data = resp.json()

    assert data.get("ageBand") is None
    assert data.get("biologicalSex") is None
    assert data.get("chronicConditions") == []
    assert data.get("profileId") is not None
    assert data.get("userId") is not None


def test_save_profile_happy_path(profile_client: TestClient) -> None:
    """PUT /api/v1/profile saves valid context and returns updated representation."""
    cookies = _register_and_login(profile_client, "saved_user@example.com")
    payload = {
        "ageBand": "young_adult",
        "biologicalSex": "female",
        "chronicConditions": ["Asthma", "Diabetes"],
    }
    resp = profile_client.put(
        "/api/v1/profile",
        json=payload,
        cookies=cookies,
    )

    assert resp.status_code == status.HTTP_200_OK
    assert resp.headers.get("Cache-Control") == "no-store"
    data = resp.json()

    assert data["ageBand"] == "young_adult"
    assert data["biologicalSex"] == "female"
    assert data["chronicConditions"] == ["Asthma", "Diabetes"]
    assert data["profileId"] == data["id"]

    # Verify subsequent GET returns identical data
    get_resp = profile_client.get("/api/v1/profile", cookies=cookies)
    assert get_resp.status_code == status.HTTP_200_OK
    assert get_resp.json()["chronicConditions"] == ["Asthma", "Diabetes"]


def test_save_profile_unauthenticated_fails_401(
    profile_client: TestClient,
) -> None:
    """Unauthenticated PUT /api/v1/profile fails with HTTP 401."""
    resp = profile_client.put(
        "/api/v1/profile",
        json={"ageBand": "adult"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_save_profile_invalid_age_band_fails_422(
    profile_client: TestClient,
) -> None:
    """Providing an invalid age band outside the clinical set fails with HTTP 422."""
    cookies = _register_and_login(profile_client, "invalid_age@example.com")
    resp = profile_client.put(
        "/api/v1/profile",
        json={"ageBand": "toddler"},
        cookies=cookies,
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_save_profile_invalid_biological_sex_fails_422(
    profile_client: TestClient,
) -> None:
    """Providing an invalid biological sex fails with HTTP 422."""
    cookies = _register_and_login(profile_client, "invalid_sex@example.com")
    resp = profile_client.put(
        "/api/v1/profile",
        json={"biologicalSex": "not_a_valid_sex"},
        cookies=cookies,
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_patch_profile_partial_update(profile_client: TestClient) -> None:
    """PATCH /api/v1/profile updates specified fields and preserves existing values."""
    cookies = _register_and_login(profile_client, "patch_user@example.com")

    # Initial full save
    profile_client.put(
        "/api/v1/profile",
        json={
            "ageBand": "adult",
            "biologicalSex": "male",
            "chronicConditions": ["Hypertension"],
        },
        cookies=cookies,
    )

    # Partial update: change only chronicConditions
    patch_resp = profile_client.patch(
        "/api/v1/profile",
        json={"chronicConditions": ["Hypertension", "Allergies"]},
        cookies=cookies,
    )
    assert patch_resp.status_code == status.HTTP_200_OK
    data = patch_resp.json()
    assert data["ageBand"] == "adult"
    assert data["biologicalSex"] == "male"
    assert data["chronicConditions"] == ["Hypertension", "Allergies"]


def test_delete_profile_returns_204_and_resets(
    profile_client: TestClient,
) -> None:
    """DELETE /api/v1/profile deletes record with 204; read back returns empty."""
    cookies = _register_and_login(profile_client, "delete_user@example.com")

    # Save initial profile
    profile_client.put(
        "/api/v1/profile",
        json={"ageBand": "senior"},
        cookies=cookies,
    )

    # Delete
    del_resp = profile_client.delete("/api/v1/profile", cookies=cookies)
    assert del_resp.status_code == status.HTTP_204_NO_CONTENT
    assert del_resp.headers.get("Cache-Control") == "no-store"

    # Subsequent GET returns empty profile
    get_resp = profile_client.get("/api/v1/profile", cookies=cookies)
    assert get_resp.status_code == status.HTTP_200_OK
    data = get_resp.json()
    assert data.get("ageBand") is None
    assert data.get("chronicConditions") == []


def test_delete_profile_unauthenticated_fails_401(
    profile_client: TestClient,
) -> None:
    """Unauthenticated DELETE /api/v1/profile fails with HTTP 401."""
    resp = profile_client.delete("/api/v1/profile")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_profile_user_isolation(profile_client: TestClient) -> None:
    """Users can only view and mutate their own profile."""
    # User A registers and logs in
    user_a_cookies = _register_and_login(profile_client, "user_a@example.com")
    profile_client.cookies.clear()
    user_b_cookies = _register_and_login(profile_client, "user_b@example.com")
    profile_client.cookies.clear()

    # User A saves profile
    profile_client.cookies.update(user_a_cookies)
    profile_client.put(
        "/api/v1/profile",
        json={
            "ageBand": "teen",
            "biologicalSex": "female",
            "chronicConditions": ["Asthma"],
        },
    )

    # User B reads profile -> sees only User B's uninitialized profile
    profile_client.cookies.clear()
    profile_client.cookies.update(user_b_cookies)
    user_b_profile = profile_client.get("/api/v1/profile").json()
    assert user_b_profile["ageBand"] is None
    assert user_b_profile["chronicConditions"] == []

    # User B saves their own profile
    profile_client.put(
        "/api/v1/profile",
        json={
            "ageBand": "senior",
            "biologicalSex": "male",
            "chronicConditions": ["Heart Disease"],
        },
    )

    # User A still sees their own profile unchanged
    profile_client.cookies.clear()
    profile_client.cookies.update(user_a_cookies)
    user_a_profile = profile_client.get("/api/v1/profile").json()
    assert user_a_profile["ageBand"] == "teen"
    assert user_a_profile["chronicConditions"] == ["Asthma"]
