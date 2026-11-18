"""Unit tests for chat assessment database persistence and user history linkage.

Responsibilities:
    - Test happy path: logged-in assessment is saved to DB and appears in GET /history
      with risk level (S2-DAR-11, FR-20).
    - Test audit logging: POST /analyze writes an audit_logs row
      linked to the assessment without foreign key violations (NFR-10).
    - Test guest isolation: guest assessments stay anonymous and do not
      appear in user history.
    - Test mass-assignment protection: user_id is set only from token,
      never request body.
    - Test resilience: a database failure during message turn does not break the chat.

Owner: Darshil (assessment) · Task: S2-DAR-11 · Requirements: FR-01, FR-20, DR-02
"""

from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import (
    get_ai_gateway_dep,
    get_assessment_service,
    get_audit_service,
    get_auth_service,
    get_session_factory,
)
from app.api.orchestrator_service import build_orchestrator_service
from app.core.config import Settings
from app.models.audit_log import AuditLog
from app.models.base import Base
from app.models.consent import Consent
from app.models.user import User
from app.services.audit.service import AuditService
from app.services.auth.security import create_access_token
from app.services.auth.service import AuthService
from app.services.privacy.consent import CURRENT_POLICY_VERSION

CONSENT_ID = UUID("00000000-0000-4000-8000-0000000000c1")
USER_ID = UUID("00000000-0000-4000-8000-0000000000a1")
BASE = "/api/v1/assessments"
HISTORY_BASE = "/api/v1/history"


@pytest.fixture
def test_db_setup(tmp_path: Path) -> Iterator[tuple[sessionmaker[Session], User]]:
    """Create test SQLite database with schema, consent, and user account."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'chat_persistence.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)

    with sessions.begin() as session:
        consent = Consent(id=CONSENT_ID, policy_version=CURRENT_POLICY_VERSION)
        user = User(id=USER_ID, email="darshil-persistence-test@example.com")
        session.add_all([consent, user])

    yield sessions, user
    engine.dispose()


@pytest.fixture
def persistence_app(
    app: FastAPI,
    test_settings: Settings,
    test_db_setup: tuple[sessionmaker[Session], User],
) -> Iterator[tuple[FastAPI, sessionmaker[Session], User]]:
    """Configure FastAPI app with database session factory and orchestrator service."""
    sessions, user = test_db_setup
    gateway = get_ai_gateway_dep(test_settings)
    service = build_orchestrator_service(
        settings=test_settings,
        ai_gateway=gateway,
        engine=None,
        session_factory=sessions,
    )
    auth_service = AuthService(session_factory=sessions, settings=test_settings)
    audit_service = AuditService(session_factory=sessions)

    app.dependency_overrides[get_assessment_service] = lambda: service
    app.dependency_overrides[get_session_factory] = lambda: sessions
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_audit_service] = lambda: audit_service

    yield app, sessions, user

    app.dependency_overrides.pop(get_assessment_service, None)
    app.dependency_overrides.pop(get_session_factory, None)
    app.dependency_overrides.pop(get_auth_service, None)
    app.dependency_overrides.pop(get_audit_service, None)


@pytest.fixture
async def http_client(
    persistence_app: tuple[FastAPI, sessionmaker[Session], User],
) -> AsyncIterator[AsyncClient]:
    """Async client connected to the configured test app."""
    app, _, _ = persistence_app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


def _auth_headers(user: User, settings: Settings) -> dict[str, str]:
    """Generate authorization header with valid JWT access token."""
    token = create_access_token(user_id=user.id, email=user.email, settings=settings)
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# 1. Happy Path: Logged-in assessment saved to DB and appears in GET /history
# =============================================================================


@pytest.mark.anyio
async def test_logged_in_assessment_persists_and_appears_in_history_with_risk_level(
    http_client: AsyncClient,
    test_settings: Settings,
    persistence_app: tuple[FastAPI, sessionmaker[Session], User],
) -> None:
    """Verify that an assessment run by a logged-in user is saved to DB with risk level.

    Turn flow:
    1. POST /assessments while authenticated -> sets user_id from token.
    2. POST /assessments/{id}/messages -> saves user message and symptoms to DB.
    3. POST /assessments/{id}/analyze -> triggers triage, writes audit log,
       updates state.
    4. GET /history -> returns assessment summary with riskLevel populated.
    """
    _, sessions, user = persistence_app
    headers = _auth_headers(user, test_settings)

    # 1. Create assessment as logged-in user
    create_resp = await http_client.post(
        BASE,
        json={"consentId": str(CONSENT_ID)},
        headers=headers,
    )
    assert create_resp.status_code == status.HTTP_201_CREATED
    aid = create_resp.json()["id"]
    assert create_resp.json()["userId"] == str(user.id)

    # 2. Send symptom message
    msg_resp = await http_client.post(
        f"{BASE}/{aid}/messages",
        json={"content": "I have severe chest pain and I can't breathe properly"},
        headers=headers,
    )
    assert msg_resp.status_code == status.HTTP_200_OK
    assert msg_resp.json()["nextState"] == "CONFIRMING"

    # 3. Analyze assessment
    analyze_resp = await http_client.post(
        f"{BASE}/{aid}/analyze",
        headers=headers,
    )
    assert analyze_resp.status_code == status.HTTP_200_OK
    assert analyze_resp.json()["state"] == "COMPLETED"

    # 4. Verify audit_logs row was written without foreign key errors
    with sessions() as db:
        logs = db.scalars(
            select(AuditLog).where(AuditLog.assessment_id == UUID(aid))
        ).all()
        assert len(logs) >= 1
        analysis_log = next(
            (entry for entry in logs if entry.action == "ANALYSIS"), None
        )
        assert analysis_log is not None
        assert analysis_log.risk_level == "URGENT"

    # 5. Verify GET /history returns the assessment with its riskLevel
    history_resp = await http_client.get(HISTORY_BASE, headers=headers)
    assert history_resp.status_code == status.HTTP_200_OK
    data: dict[str, Any] = history_resp.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["id"] == aid
    assert item["userId"] == str(user.id)
    assert item["state"] == "COMPLETED"
    assert item["riskLevel"] == "URGENT"


# =============================================================================
# 2. Edge Case: Guest assessment is isolated and does not appear in history
# =============================================================================


@pytest.mark.anyio
async def test_guest_assessment_does_not_appear_in_user_history(
    http_client: AsyncClient,
    test_settings: Settings,
    persistence_app: tuple[FastAPI, sessionmaker[Session], User],
) -> None:
    """Verify that an assessment by an anonymous guest stays isolated."""
    _, _, user = persistence_app
    headers = _auth_headers(user, test_settings)

    # 1. Create assessment as anonymous guest (no auth header)
    guest_create = await http_client.post(
        BASE,
        json={"consentId": str(CONSENT_ID)},
    )
    assert guest_create.status_code == status.HTTP_201_CREATED
    guest_aid = guest_create.json()["id"]
    assert guest_create.json()["userId"] is None

    # 2. Send message as guest
    guest_msg = await http_client.post(
        f"{BASE}/{guest_aid}/messages",
        json={"content": "I have a sore throat since 2 days"},
    )
    assert guest_msg.status_code == status.HTTP_200_OK

    # 3. Analyze as guest
    guest_analyze = await http_client.post(f"{BASE}/{guest_aid}/analyze")
    assert guest_analyze.status_code == status.HTTP_200_OK

    # 4. History for user must be empty (guest assessment is excluded)
    history_resp = await http_client.get(HISTORY_BASE, headers=headers)
    assert history_resp.status_code == status.HTTP_200_OK
    assert history_resp.json()["items"] == []


# =============================================================================
# 3. Edge Case: Request body userId is ignored (mass-assignment protection)
# =============================================================================


@pytest.mark.anyio
async def test_user_id_set_only_from_token_never_request_body(
    http_client: AsyncClient,
    test_settings: Settings,
    persistence_app: tuple[FastAPI, sessionmaker[Session], User],
) -> None:
    """Verify that sending userId in request body does not spoof account ownership."""
    _, _, user = persistence_app
    headers = _auth_headers(user, test_settings)
    spoofed_uuid = str(uuid4())

    # 1. Unauthenticated request with spoofed userId in body -> remains None (guest)
    guest_resp = await http_client.post(
        BASE,
        json={"consentId": str(CONSENT_ID), "userId": spoofed_uuid},
    )
    assert guest_resp.status_code == status.HTTP_201_CREATED
    assert guest_resp.json()["userId"] is None

    # 2. Authenticated request with different userId in body -> overwritten by token ID
    auth_resp = await http_client.post(
        BASE,
        json={"consentId": str(CONSENT_ID), "userId": spoofed_uuid},
        headers=headers,
    )
    assert auth_resp.status_code == status.HTTP_201_CREATED
    assert auth_resp.json()["userId"] == str(user.id)
    assert auth_resp.json()["userId"] != spoofed_uuid


# =============================================================================
# 4. Failure Case: Database error does not break the chat
# =============================================================================


@pytest.mark.anyio
async def test_database_error_does_not_break_chat(
    http_client: AsyncClient,
    test_settings: Settings,
    persistence_app: tuple[FastAPI, sessionmaker[Session], User],
) -> None:
    """Verify that a database failure during turn persistence does not fail chat.

    Per S2-DAR-4 and S2-DAR-11:
    A failure in the database layer must log a warning and safely fall back,
    returning the in-memory assistant answer and next state to the user without 500.
    """
    _, _, user = persistence_app
    headers = _auth_headers(user, test_settings)

    # 1. Create assessment
    create_resp = await http_client.post(
        BASE,
        json={"consentId": str(CONSENT_ID)},
        headers=headers,
    )
    assert create_resp.status_code == status.HTTP_201_CREATED
    aid = create_resp.json()["id"]

    # 2. Simulate database failure during turn persistence
    with patch(
        "app.repositories.message_repository.create_message",
        side_effect=RuntimeError("Simulated DB disk failure"),
    ):
        msg_resp = await http_client.post(
            f"{BASE}/{aid}/messages",
            json={"content": "I have had a mild headache since yesterday"},
            headers=headers,
        )

    # 3. Must still return 200 OK with valid assistant message
    assert msg_resp.status_code == status.HTTP_200_OK
    data = msg_resp.json()
    assert data["nextState"] == "CONFIRMING"
    assert data["assistantMessage"]["content"] is not None
