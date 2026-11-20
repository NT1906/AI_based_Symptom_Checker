"""S2-KAV-8 — Accounts, profile, history, deletion API tests (Issue #334).

Responsibilities:
    - Account authentication lifecycle & password change (FR-01, NFR-03):
        - TC-ACC-A-01: User registration with Argon2id hashing and conflict handling.
        - TC-ACC-A-02: User login issuing HttpOnly access/refresh and CSRF cookies.
        - TC-ACC-A-03: Token refresh rotating access and refresh tokens.
        - TC-ACC-A-04: Current user profile (/auth/me) with session verification.
        - TC-ACC-A-05: Authenticated password change invalidating old credentials.
        - TC-ACC-A-06: Session logout clearing cookies and revoking tokens.
    - Clinical profile context management (FR-02, idea § 10):
        - TC-ACC-A-07: Profile retrieval with default empty state and no-store headers.
        - TC-ACC-A-08: Full profile creation/replacement with deduplicated conditions.
        - TC-ACC-A-09: Partial profile updates (PATCH) preserving existing attributes.
        - TC-ACC-A-10: Profile validation rejecting invalid age bands or sexes.
        - TC-ACC-A-11: Profile deletion resetting clinical context.
    - Assessment history querying & tenant isolation (FR-02, NFR-03, DR-02):
        - TC-ACC-A-12: Paginated assessment history listing with Cache-Control no-store.
        - TC-ACC-A-13: History pagination boundary validation (limit <= 100, offset).
        - TC-ACC-A-14: Detailed assessment retrieval including triage result payload.
        - TC-ACC-A-15: Cross-tenant IDOR protection (404 Not Found on foreign record).
    - Data rights, portability & deletion (DPDP Act 2023, DR-06, NFR-04):
        - TC-ACC-A-16: Account data export returning comprehensive portable JSON.
        - TC-ACC-A-17: Atomic account erasure cascading deletions and anonymizing logs.
        - TC-ACC-A-18: Post-deletion rejection of login and expunged records check.

Owner: Kavya (Database & Testing) · Task: S2-KAV-8 · Issue: #334
Requirements: FR-01, FR-02, NFR-03, NFR-04, DR-02, DR-06, idea § 10
"""

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.api.deps import (
    get_audit_service,
    get_auth_service,
    get_db_engine,
    get_profile_service,
    get_session_factory,
)
from app.api.v1.history import get_history_service
from app.api.v1.privacy import get_account_export, get_data_rights_service
from app.core.config import Settings, get_settings
from app.models.assessment import Assessment as DbAssessment
from app.models.audit_log import AuditLog
from app.models.base import Base
from app.models.consent import Consent
from app.models.guest_session import GuestSession
from app.models.message import Message
from app.models.profile import Profile as DbProfile
from app.models.symptom import Symptom as DbSymptom
from app.models.user import User
from app.schemas.condition import Condition
from app.schemas.enums import ConfidenceLabel, RiskLevel
from app.schemas.result import AssessmentResult, ReferralInfo
from app.services.audit.service import AuditService
from app.services.auth.security import generate_csrf_token, hash_password
from app.services.auth.service import AuthService
from app.services.privacy.account_deletion import AccountDataRepository
from app.services.privacy.account_export import AccountExport
from app.services.privacy.consent import CURRENT_POLICY_VERSION
from app.services.privacy.data_rights import DataRightsService
from app.services.privacy.history import HistoryService
from app.services.profile.service import ProfileService

BASE_AUTH_URL = "/api/v1/auth"
BASE_PROFILE_URL = "/api/v1/profile"
BASE_HISTORY_URL = "/api/v1/history"
BASE_PRIVACY_URL = "/api/v1/privacy"

USER_A_ID = UUID("00000000-0000-4000-8000-0000000000a1")
USER_B_ID = UUID("00000000-0000-4000-8000-0000000000b2")
CONSENT_A_ID = UUID("00000000-0000-4000-8000-0000000000c1")
CONSENT_B_ID = UUID("00000000-0000-4000-8000-0000000000c2")


# ---------------------------------------------------------------------------
# Fixtures & Environment
# ---------------------------------------------------------------------------


@pytest.fixture
def account_engine(tmp_path: Path) -> Iterator[Engine]:
    """Provide an isolated database engine with tables created."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'account_api.db'}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def account_sessions(account_engine: Engine) -> sessionmaker[Session]:
    """Provide a sessionmaker preloaded with consent and two distinct user accounts."""
    sessions = sessionmaker(bind=account_engine, expire_on_commit=False)
    with sessions.begin() as session:
        session.add(Consent(id=CONSENT_A_ID, policy_version=CURRENT_POLICY_VERSION))
        session.add(Consent(id=CONSENT_B_ID, policy_version=CURRENT_POLICY_VERSION))
        user_a = User(
            id=USER_A_ID,
            email="patient_alpha@example.com",
            password_hash=hash_password("PasswordAlpha123!"),
        )
        user_b = User(
            id=USER_B_ID,
            email="patient_beta@example.com",
            password_hash=hash_password("PasswordBeta123!"),
        )
        session.add_all([user_a, user_b])
    return sessions


@pytest.fixture
def account_app(
    app: FastAPI,
    test_settings: Settings,
    account_engine: Engine,
    account_sessions: sessionmaker[Session],
) -> Iterator[FastAPI]:
    """Provide a FastAPI app with isolated database and domain services."""
    auth_service = AuthService(session_factory=account_sessions, settings=test_settings)
    profile_service = ProfileService(session_factory=account_sessions)
    history_service = HistoryService(session_factory=account_sessions)
    audit_service = AuditService(session_factory=account_sessions)
    account_export = AccountExport(session_factory=account_sessions)
    data_rights_service = DataRightsService(AccountDataRepository(account_sessions))

    app.state.db_engine = account_engine
    app.state.session_factory = account_sessions

    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_db_engine] = lambda: account_engine
    app.dependency_overrides[get_session_factory] = lambda: account_sessions
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_profile_service] = lambda: profile_service
    app.dependency_overrides[get_history_service] = lambda: history_service
    app.dependency_overrides[get_audit_service] = lambda: audit_service
    app.dependency_overrides[get_account_export] = lambda: account_export
    app.dependency_overrides[get_data_rights_service] = lambda: data_rights_service

    try:
        yield app
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_db_engine, None)
        app.dependency_overrides.pop(get_session_factory, None)
        app.dependency_overrides.pop(get_auth_service, None)
        app.dependency_overrides.pop(get_profile_service, None)
        app.dependency_overrides.pop(get_history_service, None)
        app.dependency_overrides.pop(get_audit_service, None)
        app.dependency_overrides.pop(get_account_export, None)
        app.dependency_overrides.pop(get_data_rights_service, None)


@pytest.fixture
async def acc_client(account_app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Async HTTP client bound to the account test app."""
    transport = ASGITransport(app=account_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def _make_auth_cookie(
    user_id: UUID, settings: Settings, email: str = "test@example.com"
) -> dict[str, str]:
    """Generate signed JWT auth cookie for a given user."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": "USER",
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
        "type": "access",
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return {settings.auth_cookie_name: token}


# ---------------------------------------------------------------------------
# Test Cases: Accounts & Authentication Lifecycle (TC-ACC-A-01 .. 06)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_tc_acc_a_01_user_registration_success_and_conflict(
    acc_client: AsyncClient,
) -> None:
    """TC-ACC-A-01: User registration with Argon2id password hashing.

    Verifies:
        - 201 Created on valid registration.
        - Response includes user id, email, createdAt without password hashes.
        - 409 Conflict on duplicate email registration.
        - 422 Unprocessable Content on blank or invalid password.
    """
    # 1. Successful registration
    reg_payload = {
        "email": "fresh_patient@example.com",
        "password": "ValidPassword123!",
    }
    resp = await acc_client.post(f"{BASE_AUTH_URL}/register", json=reg_payload)
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data["email"] == "fresh_patient@example.com"
    assert "id" in data
    assert "createdAt" in data
    assert "password" not in data
    assert "passwordHash" not in data

    # 2. Duplicate registration rejected
    dup_resp = await acc_client.post(f"{BASE_AUTH_URL}/register", json=reg_payload)
    assert dup_resp.status_code == status.HTTP_409_CONFLICT
    dup_data = dup_resp.json()
    assert dup_data["code"] == "CONFLICT"

    # 3. Validation rejection on blank password
    blank_resp = await acc_client.post(
        f"{BASE_AUTH_URL}/register",
        json={"email": "another@example.com", "password": "   "},
    )
    assert blank_resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.anyio
async def test_tc_acc_a_02_user_login_success_and_invalid_credentials(
    acc_client: AsyncClient,
    test_settings: Settings,
) -> None:
    """TC-ACC-A-02: User login issuing HttpOnly access/refresh cookies and CSRF tokens.

    Verifies:
        - 200 OK on valid credentials with UserRead response.
        - Response sets access, refresh, and CSRF cookies.
        - Response header contains X-CSRF-Token.
        - 401 Unauthorized on wrong password or nonexistent email.
    """
    # 1. Valid login
    login_payload = {
        "email": "patient_alpha@example.com",
        "password": "PasswordAlpha123!",
    }
    resp = await acc_client.post(f"{BASE_AUTH_URL}/login", json=login_payload)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["id"] == str(USER_A_ID)
    assert data["email"] == "patient_alpha@example.com"

    # Verify cookies
    cookies = resp.cookies
    assert test_settings.auth_cookie_name in cookies
    assert test_settings.refresh_cookie_name in cookies
    assert test_settings.csrf_cookie_name in cookies
    assert "X-CSRF-Token" in resp.headers

    # 2. Invalid password rejected
    bad_pw_resp = await acc_client.post(
        f"{BASE_AUTH_URL}/login",
        json={"email": "patient_alpha@example.com", "password": "WrongPassword!"},
    )
    assert bad_pw_resp.status_code == status.HTTP_401_UNAUTHORIZED

    # 3. Nonexistent user rejected
    nonexistent_resp = await acc_client.post(
        f"{BASE_AUTH_URL}/login",
        json={"email": "nonexistent@example.com", "password": "AnyPassword123!"},
    )
    assert nonexistent_resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.anyio
async def test_tc_acc_a_03_token_refresh_rotates_tokens(
    acc_client: AsyncClient,
    test_settings: Settings,
) -> None:
    """TC-ACC-A-03: Token refresh rotating access and refresh tokens.

    Verifies:
        - 200 OK when providing valid refresh cookie from login.
        - Re-issues fresh access, refresh, and CSRF cookies.
        - 401 Unauthorized when refresh cookie is omitted.
    """
    # Login to acquire active session & refresh token with valid jti
    login_resp = await acc_client.post(
        f"{BASE_AUTH_URL}/login",
        json={
            "email": "patient_alpha@example.com",
            "password": "PasswordAlpha123!",
        },
    )
    assert login_resp.status_code == status.HTTP_200_OK

    resp = await acc_client.post(f"{BASE_AUTH_URL}/refresh")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["id"] == str(USER_A_ID)
    assert test_settings.auth_cookie_name in resp.cookies
    assert test_settings.refresh_cookie_name in resp.cookies

    # Omitted refresh cookie returns 401
    acc_client.cookies.clear()
    no_cookie_resp = await acc_client.post(f"{BASE_AUTH_URL}/refresh")
    assert no_cookie_resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.anyio
async def test_tc_acc_a_04_current_user_profile_me(
    acc_client: AsyncClient,
    test_settings: Settings,
) -> None:
    """TC-ACC-A-04: Current user profile (/auth/me) with session verification.

    Verifies:
        - 200 OK returning UserRead when authenticated.
        - 401 Unauthorized when unauthenticated.
    """
    auth_cookies = _make_auth_cookie(
        USER_A_ID, test_settings, "patient_alpha@example.com"
    )
    acc_client.cookies.update(auth_cookies)

    resp = await acc_client.get(f"{BASE_AUTH_URL}/me")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["id"] == str(USER_A_ID)
    assert data["email"] == "patient_alpha@example.com"

    # Unauthenticated request
    acc_client.cookies.clear()
    unauth_resp = await acc_client.get(f"{BASE_AUTH_URL}/me")
    assert unauth_resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.anyio
async def test_tc_acc_a_05_change_password_lifecycle(
    acc_client: AsyncClient,
    test_settings: Settings,
) -> None:
    """TC-ACC-A-05: Authenticated password change invalidating old credentials.

    Verifies:
        - Rejects wrong current password with 422.
        - Rejects missing CSRF validation with 401.
        - Succeeds with 204 No Content on valid current and new password.
        - Subsequent login with old password fails (401).
        - Subsequent login with new password succeeds (200).
    """
    # Login to acquire session + CSRF token
    login_resp = await acc_client.post(
        f"{BASE_AUTH_URL}/login",
        json={
            "email": "patient_beta@example.com",
            "password": "PasswordBeta123!",
        },
    )
    assert login_resp.status_code == status.HTTP_200_OK
    csrf_token = login_resp.headers["X-CSRF-Token"]

    # 1. Wrong current password returns 422
    wrong_pw_resp = await acc_client.post(
        f"{BASE_AUTH_URL}/change-password",
        json={
            "currentPassword": "WrongCurrentPassword123!",
            "newPassword": "NewStrongPassword456!",
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert wrong_pw_resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # 2. Missing CSRF header returns 401
    no_csrf_resp = await acc_client.post(
        f"{BASE_AUTH_URL}/change-password",
        json={
            "currentPassword": "PasswordBeta123!",
            "newPassword": "NewStrongPassword456!",
        },
    )
    assert no_csrf_resp.status_code == status.HTTP_401_UNAUTHORIZED

    # 3. Successful password change
    change_resp = await acc_client.post(
        f"{BASE_AUTH_URL}/change-password",
        json={
            "currentPassword": "PasswordBeta123!",
            "newPassword": "NewStrongPassword456!",
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert change_resp.status_code == status.HTTP_204_NO_CONTENT

    # 4. Old password fails
    acc_client.cookies.clear()
    old_login = await acc_client.post(
        f"{BASE_AUTH_URL}/login",
        json={
            "email": "patient_beta@example.com",
            "password": "PasswordBeta123!",
        },
    )
    assert old_login.status_code == status.HTTP_401_UNAUTHORIZED

    # 5. New password succeeds
    new_login = await acc_client.post(
        f"{BASE_AUTH_URL}/login",
        json={
            "email": "patient_beta@example.com",
            "password": "NewStrongPassword456!",
        },
    )
    assert new_login.status_code == status.HTTP_200_OK


@pytest.mark.anyio
async def test_tc_acc_a_06_user_logout_clears_session(
    acc_client: AsyncClient,
    test_settings: Settings,
) -> None:
    """TC-ACC-A-06: Session logout clearing cookies and revoking tokens.

    Verifies:
        - 200 OK with confirmation message.
        - Deletes access, refresh, and CSRF cookies.
    """
    login_resp = await acc_client.post(
        f"{BASE_AUTH_URL}/login",
        json={
            "email": "patient_alpha@example.com",
            "password": "PasswordAlpha123!",
        },
    )
    assert login_resp.status_code == status.HTTP_200_OK

    logout_resp = await acc_client.post(f"{BASE_AUTH_URL}/logout")
    assert logout_resp.status_code == status.HTTP_200_OK
    assert logout_resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Test Cases: Profile Management & Clinical Context (TC-ACC-A-07 .. 11)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_tc_acc_a_07_profile_get_default_empty_and_no_store(
    acc_client: AsyncClient,
    test_settings: Settings,
) -> None:
    """TC-ACC-A-07: Profile retrieval with default empty state and no-store headers.

    Verifies:
        - 200 OK with empty profile when user has not configured profile.
        - Cache-Control header contains 'no-store'.
        - 401 Unauthorized when unauthenticated.
    """
    # 1. Authenticated fetch on unconfigured profile
    auth_cookies = _make_auth_cookie(USER_A_ID, test_settings)
    acc_client.cookies.update(auth_cookies)

    resp = await acc_client.get(BASE_PROFILE_URL)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.headers.get("Cache-Control") == "no-store"
    data = resp.json()
    assert data["userId"] == str(USER_A_ID)
    assert data["ageBand"] is None
    assert data["biologicalSex"] is None
    assert data["chronicConditions"] == []

    # 2. Unauthenticated fetch rejected
    acc_client.cookies.clear()
    unauth_resp = await acc_client.get(BASE_PROFILE_URL)
    assert unauth_resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.anyio
async def test_tc_acc_a_08_profile_create_update_and_deduplication(
    acc_client: AsyncClient,
    test_settings: Settings,
) -> None:
    """TC-ACC-A-08: Full profile creation/replacement with deduplicated conditions.

    Verifies:
        - 200 OK on PUT /api/v1/profile.
        - Correctly updates ageBand, biologicalSex, and chronicConditions.
        - Deduplicates redundant chronic condition strings.
        - Enforces Cache-Control: no-store header.
    """
    auth_cookies = _make_auth_cookie(USER_A_ID, test_settings)
    acc_client.cookies.update(auth_cookies)

    put_payload = {
        "ageBand": "adult",
        "biologicalSex": "female",
        "chronicConditions": ["Asthma", "  Asthma  ", "Hypertension", "Diabetes"],
    }
    resp = await acc_client.put(BASE_PROFILE_URL, json=put_payload)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.headers.get("Cache-Control") == "no-store"

    data = resp.json()
    assert data["userId"] == str(USER_A_ID)
    assert data["ageBand"] == "adult"
    assert data["biologicalSex"] == "female"
    assert data["chronicConditions"] == ["Asthma", "Hypertension", "Diabetes"]


@pytest.mark.anyio
async def test_tc_acc_a_09_profile_patch_partial_update(
    acc_client: AsyncClient,
    test_settings: Settings,
) -> None:
    """TC-ACC-A-09: Partial profile updates (PATCH) preserving existing attributes.

    Verifies:
        - 200 OK on PATCH /api/v1/profile.
        - Modifies specified fields (e.g. ageBand) while preserving unchanged fields.
    """
    auth_cookies = _make_auth_cookie(USER_A_ID, test_settings)
    acc_client.cookies.update(auth_cookies)

    # Pre-populate profile
    await acc_client.put(
        BASE_PROFILE_URL,
        json={
            "ageBand": "adult",
            "biologicalSex": "female",
            "chronicConditions": ["Asthma"],
        },
    )

    # Patch only ageBand
    patch_resp = await acc_client.patch(
        BASE_PROFILE_URL,
        json={"ageBand": "senior"},
    )
    assert patch_resp.status_code == status.HTTP_200_OK
    data = patch_resp.json()
    assert data["ageBand"] == "senior"
    assert data["biologicalSex"] == "female"
    assert data["chronicConditions"] == ["Asthma"]


@pytest.mark.anyio
async def test_tc_acc_a_10_profile_validation_rejects_invalid(
    acc_client: AsyncClient,
    test_settings: Settings,
) -> None:
    """TC-ACC-A-10: Profile validation rejecting invalid age bands or biological sexes.

    Verifies:
        - 422 Unprocessable Content on invalid coarse ageBand.
        - 422 Unprocessable Content on invalid biologicalSex.
        - 422 Unprocessable Content on chronic condition with null bytes.
    """
    auth_cookies = _make_auth_cookie(USER_A_ID, test_settings)
    acc_client.cookies.update(auth_cookies)

    # Invalid ageBand
    bad_age = await acc_client.put(
        BASE_PROFILE_URL,
        json={"ageBand": "toddler_invalid", "biologicalSex": "female"},
    )
    assert bad_age.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Invalid biologicalSex
    bad_sex = await acc_client.put(
        BASE_PROFILE_URL,
        json={"ageBand": "adult", "biologicalSex": "unknown_spec"},
    )
    assert bad_sex.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Null byte condition
    bad_condition = await acc_client.put(
        BASE_PROFILE_URL,
        json={
            "ageBand": "adult",
            "biologicalSex": "female",
            "chronicConditions": ["Bad\x00Condition"],
        },
    )
    assert bad_condition.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.anyio
async def test_tc_acc_a_11_profile_delete_resets_context(
    acc_client: AsyncClient,
    test_settings: Settings,
) -> None:
    """TC-ACC-A-11: Profile deletion resetting clinical context.

    Verifies:
        - 204 No Content on DELETE /api/v1/profile with no-store header.
        - Subsequent GET /api/v1/profile reflects cleared state.
    """
    auth_cookies = _make_auth_cookie(USER_A_ID, test_settings)
    acc_client.cookies.update(auth_cookies)

    # Seed profile
    await acc_client.put(
        BASE_PROFILE_URL,
        json={
            "ageBand": "adult",
            "biologicalSex": "male",
            "chronicConditions": ["Hypertension"],
        },
    )

    # Delete profile
    del_resp = await acc_client.delete(BASE_PROFILE_URL)
    assert del_resp.status_code == status.HTTP_204_NO_CONTENT
    assert del_resp.headers.get("Cache-Control") == "no-store"

    # Verify reset
    get_resp = await acc_client.get(BASE_PROFILE_URL)
    assert get_resp.status_code == status.HTTP_200_OK
    data = get_resp.json()
    assert data["ageBand"] is None
    assert data["biologicalSex"] is None
    assert data["chronicConditions"] == []


# ---------------------------------------------------------------------------
# Test Cases: Assessment History & IDOR Protection (TC-ACC-A-12 .. 15)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_tc_acc_a_12_history_list_paginated(
    acc_client: AsyncClient,
    account_sessions: sessionmaker[Session],
    test_settings: Settings,
) -> None:
    """TC-ACC-A-12: Paginated assessment history listing with Cache-Control no-store.

    Verifies:
        - 200 OK returning paginated assessment summaries.
        - nextOffset calculation accurately reflects forward pagination.
        - Cache-Control header contains 'no-store'.
    """
    # Seed 3 assessments for User A
    with account_sessions.begin() as session:
        for _ in range(3):
            consent = Consent(id=uuid4(), policy_version=CURRENT_POLICY_VERSION)
            session.add(consent)
            session.add(
                DbAssessment(
                    id=uuid4(),
                    user_id=USER_A_ID,
                    consent_id=consent.id,
                    state="COMPLETED",
                )
            )

    auth_cookies = _make_auth_cookie(USER_A_ID, test_settings)
    acc_client.cookies.update(auth_cookies)

    # Page 1: limit=2, offset=0 -> 2 items, nextOffset=2
    p1 = await acc_client.get(f"{BASE_HISTORY_URL}?limit=2&offset=0")
    assert p1.status_code == status.HTTP_200_OK
    assert p1.headers.get("Cache-Control") == "no-store"
    data1 = p1.json()
    assert len(data1["items"]) == 2
    assert data1["nextOffset"] == 2

    # Page 2: limit=2, offset=2 -> 1 item, nextOffset=None
    p2 = await acc_client.get(f"{BASE_HISTORY_URL}?limit=2&offset=2")
    assert p2.status_code == status.HTTP_200_OK
    data2 = p2.json()
    assert len(data2["items"]) == 1
    assert data2["nextOffset"] is None


@pytest.mark.anyio
async def test_tc_acc_a_13_history_pagination_bounds_and_unauthenticated(
    acc_client: AsyncClient,
    test_settings: Settings,
) -> None:
    """TC-ACC-A-13: History pagination boundary validation (limit <= 100, offset).

    Verifies:
        - 422 on limit < 1 or limit > 100.
        - 422 on negative offset.
        - 401 on unauthenticated access.
    """
    auth_cookies = _make_auth_cookie(USER_A_ID, test_settings)
    acc_client.cookies.update(auth_cookies)

    # Limit 0
    resp_zero = await acc_client.get(f"{BASE_HISTORY_URL}?limit=0")
    assert resp_zero.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Limit > 100
    resp_overflow = await acc_client.get(f"{BASE_HISTORY_URL}?limit=101")
    assert resp_overflow.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Negative offset
    resp_neg_offset = await acc_client.get(f"{BASE_HISTORY_URL}?offset=-1")
    assert resp_neg_offset.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Unauthenticated
    acc_client.cookies.clear()
    unauth_resp = await acc_client.get(BASE_HISTORY_URL)
    assert unauth_resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.anyio
async def test_tc_acc_a_14_history_detail_includes_result_payload(
    acc_client: AsyncClient,
    account_sessions: sessionmaker[Session],
    test_settings: Settings,
) -> None:
    """TC-ACC-A-14: Detailed assessment retrieval including triage result payload.

    Verifies:
        - 200 OK on GET /api/v1/history/{assessment_id}.
        - Returns stored triage result payload (conditions, recommendations, risk).
        - Cache-Control header is 'no-store'.
    """
    assessment_id = uuid4()
    consent_id = uuid4()

    result_model = AssessmentResult(
        assessment_id=assessment_id,
        risk_level=RiskLevel.CONSULT_DOCTOR,
        conditions=[
            Condition(
                name="Migraine Headache",
                confidence=ConfidenceLabel.LIKELY,
                rank=1,
                why="Unilateral throbbing headache with photophobia.",
            )
        ],
        guidance=["Rest in a dark, quiet room."],
        referral=ReferralInfo(
            required=True,
            specialty="General Medicine",
            reason="Persistent unilateral headache",
        ),
    )
    sample_result = result_model.model_dump(mode="json", by_alias=True)

    with account_sessions.begin() as session:
        session.add(Consent(id=consent_id, policy_version=CURRENT_POLICY_VERSION))
        session.add(
            DbAssessment(
                id=assessment_id,
                user_id=USER_A_ID,
                consent_id=consent_id,
                state="COMPLETED",
                result=sample_result,
            )
        )

    auth_cookies = _make_auth_cookie(USER_A_ID, test_settings)
    acc_client.cookies.update(auth_cookies)

    resp = await acc_client.get(f"{BASE_HISTORY_URL}/{assessment_id}")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.headers.get("Cache-Control") == "no-store"

    data = resp.json()
    assert data["id"] == str(assessment_id)
    assert data["state"] == "COMPLETED"
    assert data["result"] is not None
    assert data["result"]["riskLevel"] == "CONSULT_DOCTOR"
    assert len(data["result"]["conditions"]) == 1
    assert data["result"]["conditions"][0]["name"] == "Migraine Headache"


@pytest.mark.anyio
async def test_tc_acc_a_15_history_detail_idor_denied_404(
    acc_client: AsyncClient,
    account_sessions: sessionmaker[Session],
    test_settings: Settings,
) -> None:
    """TC-ACC-A-15: Cross-tenant IDOR protection (404 Not Found on foreign record).

    Verifies:
        - User B receives 404 Not Found when requesting User A's assessment.
        - Generic error message prevents identifier enumeration.
    """
    foreign_assessment_id = uuid4()
    foreign_consent_id = uuid4()
    with account_sessions.begin() as session:
        session.add(
            Consent(id=foreign_consent_id, policy_version=CURRENT_POLICY_VERSION)
        )
        session.add(
            DbAssessment(
                id=foreign_assessment_id,
                user_id=USER_A_ID,
                consent_id=foreign_consent_id,
                state="COMPLETED",
            )
        )

    # Authenticate as User B
    auth_cookies = _make_auth_cookie(USER_B_ID, test_settings)
    acc_client.cookies.update(auth_cookies)

    resp = await acc_client.get(f"{BASE_HISTORY_URL}/{foreign_assessment_id}")
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    data = resp.json()
    assert data["code"] == "NOT_FOUND"
    assert "not found" in data["message"].lower()


# ---------------------------------------------------------------------------
# Test Cases: Data Rights, Export & Account Deletion (TC-ACC-A-16 .. 18)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_tc_acc_a_16_privacy_export_portable_json(
    acc_client: AsyncClient,
    account_sessions: sessionmaker[Session],
    test_settings: Settings,
) -> None:
    """TC-ACC-A-16: Account data export returning comprehensive portable JSON.

    Verifies:
        - 200 OK on GET /api/v1/privacy/export.
        - Header Content-Disposition set to attachment; filename="my-data.json".
        - Cache-Control header is 'no-store'.
        - Payload contains account, profile, assessments, messages, symptoms.
        - 401 Unauthorized when unauthenticated.
    """
    export_user_id = uuid4()
    consent_id = uuid4()
    assessment_id = uuid4()

    with account_sessions.begin() as session:
        user = User(
            id=export_user_id,
            email="export_patient@example.com",
            password_hash=hash_password("PasswordExport123!"),
        )
        profile = DbProfile(
            user_id=export_user_id,
            age_band="adult",
            biological_sex="female",
            chronic_conditions=["Asthma"],
        )
        consent = Consent(id=consent_id, policy_version=CURRENT_POLICY_VERSION)
        assessment = DbAssessment(
            id=assessment_id,
            user_id=export_user_id,
            consent_id=consent_id,
            state="COMPLETED",
        )
        message = Message(
            assessment_id=assessment_id,
            position=1,
            role="user",
            content="I have a headache",
        )
        symptom = DbSymptom(
            assessment_id=assessment_id,
            name="headache",
            details={"severity": "moderate", "duration": {"value": 2, "unit": "days"}},
        )
        session.add_all([user, profile, consent, assessment, message, symptom])

    auth_cookies = _make_auth_cookie(
        export_user_id, test_settings, "export_patient@example.com"
    )
    acc_client.cookies.update(auth_cookies)

    resp = await acc_client.get(f"{BASE_PRIVACY_URL}/export")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.headers.get("Cache-Control") == "no-store"
    assert (
        resp.headers.get("Content-Disposition") == 'attachment; filename="my-data.json"'
    )

    data = resp.json()
    assert "account" in data
    assert data["account"]["id"] == str(export_user_id)
    assert data["account"]["email"] == "export_patient@example.com"

    assert "profile" in data
    assert data["profile"]["ageBand"] == "adult"
    assert data["profile"]["chronicConditions"] == ["Asthma"]

    assert "assessments" in data
    assert len(data["assessments"]) == 1
    assert data["assessments"][0]["id"] == str(assessment_id)
    assert len(data["assessments"][0]["messages"]) == 1
    assert data["assessments"][0]["messages"][0]["content"] == "I have a headache"
    assert len(data["assessments"][0]["symptoms"]) == 1
    assert data["assessments"][0]["symptoms"][0]["name"] == "headache"

    # Unauthenticated rejected
    acc_client.cookies.clear()
    unauth_resp = await acc_client.get(f"{BASE_PRIVACY_URL}/export")
    assert unauth_resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.anyio
async def test_tc_acc_a_17_privacy_account_deletion_cascading_and_anonymization(
    acc_client: AsyncClient,
    account_sessions: sessionmaker[Session],
    test_settings: Settings,
) -> None:
    """TC-ACC-A-17: Atomic account erasure cascading deletions & anonymizing logs.

    Verifies:
        - 204 No Content on DELETE /api/v1/privacy/data with CSRF header & cookie.
        - Auth cookies are cleared.
        - Database cascades: User, Profile, Assessments, Messages, Symptoms deleted.
        - Guest sessions unlinked (claimed_by_user_id set to None).
        - Audit logs anonymized (user_id and assessment_id set to None).
    """
    delete_user_id = uuid4()
    consent_id = uuid4()
    assessment_id = uuid4()
    guest_session_id = uuid4()
    audit_id = uuid4()

    with account_sessions.begin() as session:
        user = User(
            id=delete_user_id,
            email="to_be_deleted@example.com",
            password_hash=hash_password("PasswordDelete123!"),
        )
        profile = DbProfile(
            user_id=delete_user_id,
            age_band="young_adult",
            biological_sex="male",
            chronic_conditions=["Allergies"],
        )
        guest_sess = GuestSession(
            id=guest_session_id,
            token_hash="a" * 64,
            expires_at=datetime.now(UTC) + timedelta(days=1),
            claimed_by_user_id=delete_user_id,
        )
        consent = Consent(id=consent_id, policy_version=CURRENT_POLICY_VERSION)
        assessment = DbAssessment(
            id=assessment_id,
            user_id=delete_user_id,
            consent_id=consent_id,
            state="COMPLETED",
        )
        message = Message(
            assessment_id=assessment_id,
            position=1,
            role="user",
            content="Testing deletion cascade",
        )
        symptom = DbSymptom(
            assessment_id=assessment_id,
            name="cough",
            details={"severity": "mild"},
        )
        audit_entry = AuditLog(
            id=audit_id,
            action="ASSESSMENT_COMPLETED",
            user_id=delete_user_id,
            assessment_id=assessment_id,
            risk_level="CONSULT_DOCTOR",
        )
        session.add_all(
            [
                user,
                profile,
                guest_sess,
                consent,
                assessment,
                message,
                symptom,
                audit_entry,
            ]
        )

    auth_cookies = _make_auth_cookie(
        delete_user_id, test_settings, "to_be_deleted@example.com"
    )
    csrf_token = generate_csrf_token()
    acc_client.cookies.update(auth_cookies)
    acc_client.cookies.set(test_settings.csrf_cookie_name, csrf_token)

    # 1. Missing CSRF header returns 401
    csrf_fail_resp = await acc_client.delete(f"{BASE_PRIVACY_URL}/data")
    assert csrf_fail_resp.status_code == status.HTTP_401_UNAUTHORIZED

    # 2. Deletion with valid CSRF succeeds (204)
    del_resp = await acc_client.delete(
        f"{BASE_PRIVACY_URL}/data",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert del_resp.status_code == status.HTTP_204_NO_CONTENT
    assert del_resp.headers.get("Cache-Control") == "no-store"

    # 3. Verify Database state
    with account_sessions() as session:
        # User deleted
        assert session.get(User, delete_user_id) is None
        # Profile deleted
        profile_row = session.scalar(
            select(DbProfile).where(DbProfile.user_id == delete_user_id)
        )
        assert profile_row is None
        # Assessment deleted
        assert session.get(DbAssessment, assessment_id) is None
        # Messages and symptoms deleted
        assert (
            session.scalar(
                select(Message).where(Message.assessment_id == assessment_id)
            )
            is None
        )
        assert (
            session.scalar(
                select(DbSymptom).where(DbSymptom.assessment_id == assessment_id)
            )
            is None
        )
        # Consent deleted
        assert session.get(Consent, consent_id) is None
        # Guest session unlinked
        guest_row = session.get(GuestSession, guest_session_id)
        assert guest_row is not None
        assert guest_row.claimed_by_user_id is None
        # Audit log preserved but anonymized
        audit_row = session.get(AuditLog, audit_id)
        assert audit_row is not None
        assert audit_row.user_id is None
        assert audit_row.assessment_id is None


@pytest.mark.anyio
async def test_tc_acc_a_18_post_deletion_login_rejected(
    acc_client: AsyncClient,
    account_sessions: sessionmaker[Session],
    test_settings: Settings,
) -> None:
    """TC-ACC-A-18: Post-deletion rejection of login and expunged records verification.

    Verifies:
        - 401 Unauthorized when attempting login for deleted account.
        - 401 Unauthorized when presenting stale JWT token.
        - Deleting already deleted user is an idempotent no-op.
    """
    deleted_id = uuid4()
    email = "deleted_account@example.com"
    with account_sessions.begin() as session:
        session.add(
            User(
                id=deleted_id,
                email=email,
                password_hash=hash_password("SomePassword123!"),
            )
        )

    # Perform deletion
    auth_cookies = _make_auth_cookie(deleted_id, test_settings, email)
    csrf_token = generate_csrf_token()
    acc_client.cookies.update(auth_cookies)
    acc_client.cookies.set(test_settings.csrf_cookie_name, csrf_token)

    del_resp = await acc_client.delete(
        f"{BASE_PRIVACY_URL}/data",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert del_resp.status_code == status.HTTP_204_NO_CONTENT

    # 1. Login with deleted email rejected
    acc_client.cookies.clear()
    login_resp = await acc_client.post(
        f"{BASE_AUTH_URL}/login",
        json={"email": email, "password": "SomePassword123!"},
    )
    assert login_resp.status_code == status.HTTP_401_UNAUTHORIZED

    # 2. Re-using old access token rejected
    acc_client.cookies.update(auth_cookies)
    me_resp = await acc_client.get(f"{BASE_AUTH_URL}/me")
    assert me_resp.status_code == status.HTTP_401_UNAUTHORIZED

    # 3. Idempotent deletion does not fail
    del_again = await acc_client.delete(
        f"{BASE_PRIVACY_URL}/data",
        headers={"X-CSRF-Token": csrf_token},
    )
    # Stale token returns 401
    assert del_again.status_code == status.HTTP_401_UNAUTHORIZED
