"""S2-DAR-12 — Black-box integration tests for assessment state transitions.

Responsibilities:
    - Test the complete state transition graph via HTTP API endpoints:
      START -> SYMPTOM_COLLECTION -> CLARIFYING -> CONFIRMING -> READY ->
      ANALYZING -> COMPLETED.
    - Test invalid state transitions (confirm before symptoms, result before
      analyze, message after completed) rejected with 409 Conflict.
    - Test boundary values: clarification loop cap at exactly 3 questions;
      the 4th turn forces transition to CONFIRMING with low confidence flagged.
    - Test symptom confirmation modifications: add, edit severity/duration,
      and remove symptoms in CONFIRMING state.
    - Test state step-back from READY to CONFIRMING upon symptom edits.
    - Test idempotent message retry eliminating duplicate turns / double answers.
    - Test clean assessment restart wiping dialogue and symptoms (FR-25).
    - Test guest assessment ownership claiming into registered user account.

Owner: Darshil Kanani (@darshil2501) · Task: S2-DAR-12
Requirements: FR-03, FR-04, FR-16, FR-19, FR-20, FR-21, FR-25, NFR-05, idea §10
"""

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import jwt
import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.api.deps import (
    get_ai_gateway_dep,
    get_assessment_service,
    get_db_engine,
    get_session_factory,
)
from app.api.orchestrator_service import build_orchestrator_service
from app.core.config import Settings
from app.models.base import Base
from app.models.consent import Consent
from app.models.user import User
from app.schemas.result import DEFAULT_DISCLAIMER
from app.services.ai.mock_provider import MockAiProvider
from app.services.assessment.orchestrator import AssessmentOrchestrator
from app.services.auth.security import hash_password
from app.services.privacy.consent import CURRENT_POLICY_VERSION

BASE_URL = "/api/v1/assessments"
CONSENT_UUID = UUID("00000000-0000-4000-8000-0000000000c1")


# ---------------------------------------------------------------------------
# Test Fixtures & Environment
# ---------------------------------------------------------------------------


@pytest.fixture
def flow_engine(tmp_path: Path):
    """Provide an isolated database engine with tables created."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'assessment_flow_api.db'}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def flow_sessions(flow_engine) -> sessionmaker[Session]:
    """Provide a sessionmaker with preloaded verified consent and test user."""
    sessions = sessionmaker(bind=flow_engine, expire_on_commit=False)
    with sessions.begin() as session:
        session.add(Consent(id=CONSENT_UUID, policy_version=CURRENT_POLICY_VERSION))
        user = User(
            id=UUID("00000000-0000-4000-8000-0000000000a1"),
            email="flow_tester@example.com",
            password_hash=hash_password("SecureFlowPass123!"),
        )
        session.add(user)
    return sessions


@pytest.fixture
def flow_app(
    app: FastAPI,
    test_settings: Settings,
    flow_engine,
    flow_sessions: sessionmaker[Session],
) -> Iterator[FastAPI]:
    """Provide a FastAPI application configured with isolated orchestrator service."""
    orchestrator = AssessmentOrchestrator(ai_gateway=MockAiProvider())
    service = build_orchestrator_service(
        settings=test_settings,
        ai_gateway=get_ai_gateway_dep(test_settings),
        engine=flow_engine,
        session_factory=flow_sessions,
    )
    service._orchestrator = orchestrator

    app.state.db_engine = flow_engine
    app.state.session_factory = flow_sessions
    app.state.assessment_service = service

    app.dependency_overrides[get_db_engine] = lambda: flow_engine
    app.dependency_overrides[get_session_factory] = lambda: flow_sessions
    app.dependency_overrides[get_assessment_service] = lambda: service

    try:
        yield app
    finally:
        app.dependency_overrides.pop(get_db_engine, None)
        app.dependency_overrides.pop(get_session_factory, None)
        app.dependency_overrides.pop(get_assessment_service, None)
        app.state.assessment_service = None


@pytest.fixture
async def http_client(flow_app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Async HTTP client bound to the isolated flow app."""
    transport = ASGITransport(app=flow_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def _make_auth_header(user_id: UUID, settings: Settings) -> dict[str, str]:
    """Generate valid Bearer authorization header for test user."""
    payload = {
        "sub": str(user_id),
        "email": "flow_tester@example.com",
        "role": "USER",
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. Valid State Transitions
# ===========================================================================


@pytest.mark.anyio
async def test_tc_flow_a_01_start_to_confirming_direct_clear_symptoms(
    http_client: AsyncClient,
) -> None:
    """TC-FLOW-A-01: Valid transition START -> CONFIRMING on clear symptoms.

    Requirements: FR-03, FR-20.
    Clear initial symptoms bypass clarification and transition straight to
    CONFIRMING with low_confidence=False.
    """
    create_resp = await http_client.post(
        BASE_URL,
        json={"consentId": str(CONSENT_UUID)},
    )
    assert create_resp.status_code == status.HTTP_201_CREATED
    aid = create_resp.json()["id"]
    assert create_resp.json()["state"] == "START"

    # Send clear symptom description with severity and duration
    msg_resp = await http_client.post(
        f"{BASE_URL}/{aid}/messages",
        json={
            "content": ("I have had a mild headache and mild fatigue since yesterday")
        },
    )
    assert msg_resp.status_code == status.HTTP_200_OK
    msg_data = msg_resp.json()
    assert msg_data["nextState"] == "CONFIRMING"

    state_resp = await http_client.get(f"{BASE_URL}/{aid}/state")
    assert state_resp.status_code == status.HTTP_200_OK
    state_data = state_resp.json()
    assert state_data["state"] == "CONFIRMING"
    assert state_data["isLowConfidence"] is False
    assert len(state_data["symptoms"]) >= 1


@pytest.mark.anyio
async def test_tc_flow_a_02_start_to_clarifying_ambiguous_symptoms(
    http_client: AsyncClient,
) -> None:
    """TC-FLOW-A-02: Valid transition START -> CLARIFYING on ambiguous symptoms.

    Requirements: FR-04, FR-19.
    Ambiguous initial symptom reports lacking duration/severity transition
    into CLARIFYING state within budget.
    """
    create_resp = await http_client.post(
        BASE_URL,
        json={"consentId": str(CONSENT_UUID)},
    )
    aid = create_resp.json()["id"]

    # Send ambiguous symptom lacking duration
    msg_resp = await http_client.post(
        f"{BASE_URL}/{aid}/messages",
        json={"content": "I have a sore throat."},
    )
    assert msg_resp.status_code == status.HTTP_200_OK
    msg_data = msg_resp.json()
    assert msg_data["nextState"] == "CLARIFYING"
    assert msg_data["assistantMessage"]["messageType"] == "CLARIFICATION"

    state_resp = await http_client.get(f"{BASE_URL}/{aid}/state")
    assert state_resp.status_code == status.HTTP_200_OK
    state_data = state_resp.json()
    assert state_data["state"] == "CLARIFYING"
    assert state_data["clarificationCount"] == 1
    assert state_data["isLowConfidence"] is False


@pytest.mark.anyio
async def test_tc_flow_a_03_clarifying_to_confirming_resolved_clarification(
    http_client: AsyncClient,
) -> None:
    """TC-FLOW-A-03: Valid transition CLARIFYING -> CONFIRMING on resolved details.

    Requirements: FR-04, FR-20.
    When a clarifying answer resolves ambiguities before turn budget, session
    progresses to CONFIRMING without low confidence flag.
    """
    create_resp = await http_client.post(
        BASE_URL,
        json={"consentId": str(CONSENT_UUID)},
    )
    aid = create_resp.json()["id"]

    # Turn 1: Enter CLARIFYING
    await http_client.post(
        f"{BASE_URL}/{aid}/messages",
        json={"content": "I have a sore throat."},
    )

    # Turn 2: Provide clarifying details resolving duration and severity
    resolve_resp = await http_client.post(
        f"{BASE_URL}/{aid}/messages",
        json={"content": "It started 2 days ago and is moderate pain."},
    )
    assert resolve_resp.status_code == status.HTTP_200_OK
    resolve_data = resolve_resp.json()
    assert resolve_data["nextState"] == "CONFIRMING"

    state_resp = await http_client.get(f"{BASE_URL}/{aid}/state")
    state_data = state_resp.json()
    assert state_data["state"] == "CONFIRMING"
    assert state_data["isLowConfidence"] is False


# ===========================================================================
# 2. Boundary Value Analysis: Clarification Loop Capping
# ===========================================================================


@pytest.mark.anyio
async def test_tc_flow_a_04_clarification_loop_boundary_three_questions_cap(
    http_client: AsyncClient,
) -> None:
    """TC-FLOW-A-04: Boundary test: clarification count caps at exactly 3 turns.

    Requirements: FR-04, FR-19.
    Tests boundary value of maximum allowed clarification questions (turns 1, 2, 3).
    """
    create_resp = await http_client.post(
        BASE_URL,
        json={"consentId": str(CONSENT_UUID)},
    )
    aid = create_resp.json()["id"]

    # Turn 1: Ambiguous intake
    t1 = await http_client.post(
        f"{BASE_URL}/{aid}/messages",
        json={"content": "I have a cough."},
    )
    assert t1.json()["nextState"] == "CLARIFYING"

    # Turn 2: Ambiguous reply
    t2 = await http_client.post(
        f"{BASE_URL}/{aid}/messages",
        json={"content": "It is dry."},
    )
    assert t2.json()["nextState"] == "CLARIFYING"

    # Turn 3: 3rd turn reaching maximum budget
    t3 = await http_client.post(
        f"{BASE_URL}/{aid}/messages",
        json={"content": "I am really not sure."},
    )
    assert t3.json()["nextState"] == "CLARIFYING"

    state_resp = await http_client.get(f"{BASE_URL}/{aid}/state")
    state_data = state_resp.json()
    assert state_data["clarificationCount"] == 3
    assert state_data["maxClarifications"] == 3
    assert state_data["state"] == "CLARIFYING"
    assert state_data["isLowConfidence"] is False


@pytest.mark.anyio
async def test_tc_flow_a_05_clarification_loop_boundary_turn_four_low_confidence(
    http_client: AsyncClient,
) -> None:
    """TC-FLOW-A-05: Boundary test: 4th turn forces CONFIRMING with low confidence.

    Requirements: FR-04, FR-19, FR-20.
    Exceeding the 3-turn budget forces transition to CONFIRMING and marks
    is_low_confidence=True to inform clinical risk evaluation.
    """
    create_resp = await http_client.post(
        BASE_URL,
        json={"consentId": str(CONSENT_UUID)},
    )
    aid = create_resp.json()["id"]

    # Turns 1-3: Exhaust clarification budget
    await http_client.post(
        f"{BASE_URL}/{aid}/messages",
        json={"content": "I have a cough."},
    )
    await http_client.post(
        f"{BASE_URL}/{aid}/messages",
        json={"content": "It is dry."},
    )
    await http_client.post(
        f"{BASE_URL}/{aid}/messages",
        json={"content": "I don't know."},
    )

    # Turn 4: Budget exhausted, persistent ambiguity
    t4 = await http_client.post(
        f"{BASE_URL}/{aid}/messages",
        json={"content": "It's just there."},
    )
    assert t4.status_code == status.HTTP_200_OK
    t4_data = t4.json()
    assert t4_data["nextState"] == "CONFIRMING"

    state_resp = await http_client.get(f"{BASE_URL}/{aid}/state")
    state_data = state_resp.json()
    assert state_data["state"] == "CONFIRMING"
    assert state_data["clarificationCount"] == 3
    assert state_data["isLowConfidence"] is True


# ===========================================================================
# 3. Symptom Confirmation & Editing in CONFIRMING State
# ===========================================================================


@pytest.mark.anyio
async def test_tc_flow_a_06_confirming_to_ready_via_symptom_confirmation(
    http_client: AsyncClient,
) -> None:
    """TC-FLOW-A-06: Valid transition: symptoms confirmed before analysis.

    Requirements: FR-16, FR-21.
    Confirms symptoms via PATCH /assessments/{id}/symptoms updating symptom
    records and preparing session for clinical prediction.
    """
    create_resp = await http_client.post(
        BASE_URL,
        json={"consentId": str(CONSENT_UUID)},
    )
    aid = create_resp.json()["id"]

    await http_client.post(
        f"{BASE_URL}/{aid}/messages",
        json={"content": "I have had a mild headache since yesterday."},
    )

    syms_resp = await http_client.get(f"{BASE_URL}/{aid}/symptoms")
    assert syms_resp.status_code == status.HTTP_200_OK
    symptoms = syms_resp.json()
    assert len(symptoms) >= 1

    # Confirm symptoms
    patch_resp = await http_client.patch(
        f"{BASE_URL}/{aid}/symptoms",
        json={
            "symptoms": [
                {
                    "name": symptoms[0]["name"],
                    "severity": "MILD",
                    "duration": {"value": 1.0, "unit": "DAY"},
                }
            ]
        },
    )
    assert patch_resp.status_code == status.HTTP_200_OK
    confirmed = patch_resp.json()
    assert len(confirmed) >= 1
    assert confirmed[0]["name"] == symptoms[0]["name"]


@pytest.mark.anyio
async def test_tc_flow_a_07_confirm_step_add_symptom(
    http_client: AsyncClient,
) -> None:
    """TC-FLOW-A-07: Confirm step: user adds a new symptom.

    Requirements: FR-16, FR-21.
    Allows user to supplement recognized symptoms with unmentioned symptoms.
    """
    create_resp = await http_client.post(
        BASE_URL,
        json={"consentId": str(CONSENT_UUID)},
    )
    aid = create_resp.json()["id"]

    await http_client.post(
        f"{BASE_URL}/{aid}/messages",
        json={"content": "I have had a mild headache since yesterday."},
    )

    # Add fever to recognized headache
    add_resp = await http_client.patch(
        f"{BASE_URL}/{aid}/symptoms",
        json={
            "symptoms": [
                {
                    "name": "headache",
                    "severity": "MODERATE",
                    "duration": {"value": 2.0, "unit": "DAY"},
                },
                {
                    "name": "fever",
                    "severity": "MILD",
                    "duration": {"value": 1.0, "unit": "DAY"},
                },
            ]
        },
    )
    assert add_resp.status_code == status.HTTP_200_OK
    symptoms = add_resp.json()
    names = {s["name"].lower() for s in symptoms}
    assert "headache" in names
    assert "fever" in names


@pytest.mark.anyio
async def test_tc_flow_a_08_confirm_step_edit_symptom_severity_and_duration(
    http_client: AsyncClient,
) -> None:
    """TC-FLOW-A-08: Confirm step: user edits symptom severity and duration.

    Requirements: FR-16, FR-21.
    Enables user correction of AI-extracted severity and duration values.
    """
    create_resp = await http_client.post(
        BASE_URL,
        json={"consentId": str(CONSENT_UUID)},
    )
    aid = create_resp.json()["id"]

    await http_client.post(
        f"{BASE_URL}/{aid}/messages",
        json={"content": "I have had a mild headache since yesterday."},
    )

    # Edit severity to SEVERE and duration to 4 days
    edit_resp = await http_client.patch(
        f"{BASE_URL}/{aid}/symptoms",
        json={
            "symptoms": [
                {
                    "name": "headache",
                    "severity": "SEVERE",
                    "duration": {"value": 4.0, "unit": "DAY"},
                    "bodyLocation": "head",
                }
            ]
        },
    )
    assert edit_resp.status_code == status.HTTP_200_OK
    symptoms = edit_resp.json()
    headache = next(s for s in symptoms if s["name"].lower() == "headache")
    assert headache["severity"] == "SEVERE"
    assert headache["duration"]["value"] == 4.0


@pytest.mark.anyio
async def test_tc_flow_a_09_confirm_step_remove_symptom(
    http_client: AsyncClient,
) -> None:
    """TC-FLOW-A-09: Confirm step: user removes an erroneously attributed symptom.

    Requirements: FR-16, FR-21.
    Allows user to remove false-positive extractions before clinical analysis.
    """
    create_resp = await http_client.post(
        BASE_URL,
        json={"consentId": str(CONSENT_UUID)},
    )
    aid = create_resp.json()["id"]

    # Send message to reach CONFIRMING state with multiple symptoms
    await http_client.post(
        f"{BASE_URL}/{aid}/messages",
        json={"content": "I have had a mild headache and fever since yesterday."},
    )

    # Initial symptoms list has both headache and fever
    syms_before = await http_client.get(f"{BASE_URL}/{aid}/symptoms")
    assert len(syms_before.json()) >= 2

    # User removes all symptoms by sending an empty symptoms list
    remove_resp = await http_client.patch(
        f"{BASE_URL}/{aid}/symptoms",
        json={"symptoms": []},
    )
    assert remove_resp.status_code == status.HTTP_200_OK
    assert remove_resp.json() == []

    # Verify symptoms endpoint now reflects empty symptoms
    syms_after_clear = await http_client.get(f"{BASE_URL}/{aid}/symptoms")
    assert syms_after_clear.json() == []

    # Re-add only headache, verifying removal was persistent
    # and only desired symptom exists
    readd_resp = await http_client.patch(
        f"{BASE_URL}/{aid}/symptoms",
        json={"symptoms": [{"name": "headache", "severity": "MILD"}]},
    )
    assert readd_resp.status_code == status.HTTP_200_OK
    symptoms = readd_resp.json()
    assert len(symptoms) == 1
    assert symptoms[0]["name"].lower() == "headache"


# ===========================================================================
# 4. Clinical Analysis & Result Completion
# ===========================================================================


@pytest.mark.anyio
async def test_tc_flow_a_10_transition_confirming_to_analyzing_to_completed(
    http_client: AsyncClient,
) -> None:
    """TC-FLOW-A-10: Valid transition: CONFIRMING -> ANALYZING -> COMPLETED.

    Requirements: FR-03, DR-02.
    Executing POST /analyze transitions session to COMPLETED and generates
    final triage results with mandatory disclaimer.
    """
    create_resp = await http_client.post(
        BASE_URL,
        json={"consentId": str(CONSENT_UUID)},
    )
    aid = create_resp.json()["id"]

    await http_client.post(
        f"{BASE_URL}/{aid}/messages",
        json={"content": "I have had a mild headache and fatigue since yesterday."},
    )

    analyze_resp = await http_client.post(f"{BASE_URL}/{aid}/analyze")
    assert analyze_resp.status_code == status.HTTP_200_OK
    analyze_data = analyze_resp.json()
    assert analyze_data["state"] == "COMPLETED"
    assert analyze_data["resultAvailable"] is True

    result_resp = await http_client.get(f"{BASE_URL}/{aid}/result")
    assert result_resp.status_code == status.HTTP_200_OK
    result_data = result_resp.json()
    assert result_data["riskLevel"] in ("SELF_CARE", "CONSULT_DOCTOR", "URGENT")
    assert result_data["disclaimer"] == DEFAULT_DISCLAIMER


# ===========================================================================
# 5. Invalid State Transitions (Rejection with Status Codes)
# ===========================================================================


@pytest.mark.anyio
async def test_tc_flow_a_11_invalid_transition_analyze_from_start_state_rejected(
    http_client: AsyncClient,
) -> None:
    """TC-FLOW-A-11: Invalid transition: analyze before symptoms recorded rejected.

    Requirements: FR-03, DR-02.
    Attempting to trigger analysis from START state with zero symptoms
    must be rejected with HTTP 409 Conflict.
    """
    create_resp = await http_client.post(
        BASE_URL,
        json={"consentId": str(CONSENT_UUID)},
    )
    aid = create_resp.json()["id"]

    # Attempt to analyze immediately without reporting symptoms
    analyze_resp = await http_client.post(f"{BASE_URL}/{aid}/analyze")
    assert analyze_resp.status_code == status.HTTP_409_CONFLICT


@pytest.mark.anyio
async def test_tc_flow_a_12_invalid_transition_result_before_analyze_rejected(
    http_client: AsyncClient,
) -> None:
    """TC-FLOW-A-12: Invalid transition: result retrieval before analysis rejected.

    Requirements: DR-02.
    Querying GET /result before POST /analyze has executed must be rejected
    with HTTP 409 Conflict.
    """
    create_resp = await http_client.post(
        BASE_URL,
        json={"consentId": str(CONSENT_UUID)},
    )
    aid = create_resp.json()["id"]

    await http_client.post(
        f"{BASE_URL}/{aid}/messages",
        json={"content": "I have had a mild headache since yesterday."},
    )

    # Attempt to get result before running analysis
    result_resp = await http_client.get(f"{BASE_URL}/{aid}/result")
    assert result_resp.status_code == status.HTTP_409_CONFLICT


@pytest.mark.anyio
async def test_tc_flow_a_13_invalid_transition_message_after_completed_rejected(
    http_client: AsyncClient,
) -> None:
    """TC-FLOW-A-13: Invalid transition: sending message after completed rejected.

    Requirements: FR-03, DR-02.
    Once an assessment reaches terminal COMPLETED state, further dialogue
    turns must be rejected with HTTP 409 Conflict.
    """
    create_resp = await http_client.post(
        BASE_URL,
        json={"consentId": str(CONSENT_UUID)},
    )
    aid = create_resp.json()["id"]

    await http_client.post(
        f"{BASE_URL}/{aid}/messages",
        json={"content": "I have had a mild headache since yesterday."},
    )
    await http_client.post(f"{BASE_URL}/{aid}/analyze")

    # Post message to completed assessment
    msg_resp = await http_client.post(
        f"{BASE_URL}/{aid}/messages",
        json={"content": "Also my knee hurts."},
    )
    assert msg_resp.status_code == status.HTTP_409_CONFLICT


# ===========================================================================
# 6. Session Restart & Clean Assessment State
# ===========================================================================


@pytest.mark.anyio
async def test_tc_flow_a_14_restart_assessment_cleans_dialogue_and_symptoms(
    flow_app: FastAPI,
    http_client: AsyncClient,
) -> None:
    """TC-FLOW-A-14: Assessment restart cleanly wipes conversation and symptoms.

    Requirements: FR-25.
    Resetting an assessment session clears dialogue messages, recorded symptoms,
    and clarification loop counters, returning to START per FR-25.
    Also verifies POST /assessments starts with clean, isolated state.
    """
    create_resp = await http_client.post(
        BASE_URL,
        json={"consentId": str(CONSENT_UUID)},
    )
    aid = UUID(create_resp.json()["id"])

    # Progress assessment into CLARIFYING
    await http_client.post(
        f"{BASE_URL}/{aid}/messages",
        json={"content": "I have a cough."},
    )
    state_before = await http_client.get(f"{BASE_URL}/{aid}/state")
    assert state_before.json()["state"] == "CLARIFYING"
    assert len(state_before.json()["symptoms"]) >= 1

    # Restart session via orchestrator service
    service = flow_app.state.assessment_service
    await service._orchestrator.restart_assessment(aid)

    # Verify session returned cleanly to START
    state_after = await http_client.get(f"{BASE_URL}/{aid}/state")
    data = state_after.json()
    assert data["state"] == "START"
    assert len(data["symptoms"]) == 0
    assert data["clarificationCount"] == 0
    assert data["isLowConfidence"] is False

    # Verify messages history is wiped
    msgs_resp = await http_client.get(f"{BASE_URL}/{aid}/messages")
    assert msgs_resp.json() == []


# ===========================================================================
# 7. Idempotent Message Processing & Turn Retry
# ===========================================================================


@pytest.mark.anyio
async def test_tc_flow_a_15_idempotent_message_retry_avoids_duplicate_turns(
    http_client: AsyncClient,
) -> None:
    """TC-FLOW-A-15: Repeated identical message returns prior answer.

    Requirements: NFR-05.
    When a network retry submits the identical turn, orchestrator returns
    cached response and maintains dialogue integrity (len=2, no double answers).
    """
    create_resp = await http_client.post(
        BASE_URL,
        json={"consentId": str(CONSENT_UUID)},
    )
    aid = create_resp.json()["id"]
    content = "I have had a mild headache since yesterday."

    # First submission
    resp1 = await http_client.post(
        f"{BASE_URL}/{aid}/messages",
        json={"content": content},
    )
    assert resp1.status_code == status.HTTP_200_OK
    d1 = resp1.json()

    # Second submission (identical network retry)
    resp2 = await http_client.post(
        f"{BASE_URL}/{aid}/messages",
        json={"content": content},
    )
    assert resp2.status_code == status.HTTP_200_OK
    d2 = resp2.json()

    # Replies must match exactly
    assert d1["assistantMessage"]["content"] == d2["assistantMessage"]["content"]
    assert d1["nextState"] == d2["nextState"]

    # History must contain only 1 user turn + 1 assistant reply (no double answer)
    msgs_resp = await http_client.get(f"{BASE_URL}/{aid}/messages")
    assert len(msgs_resp.json()) == 2


# ===========================================================================
# 8. Guest Assessment Claiming into User Account
# ===========================================================================


@pytest.mark.anyio
async def test_tc_flow_a_16_guest_assessment_claimed_into_registered_user_account(
    flow_app: FastAPI,
    http_client: AsyncClient,
    test_settings: Settings,
    flow_sessions: sessionmaker[Session],
) -> None:
    """TC-FLOW-A-16: Anonymous guest assessment claimed into user account after sign-up.

    Requirements: idea §10, FR-20.
    A guest assessment created anonymously (user_id=None) is claimed into
    the registered account, transferring ownership and appearing in user history.
    """
    user_id = UUID("00000000-0000-4000-8000-0000000000a1")
    headers = _make_auth_header(user_id, test_settings)

    # 1. Anonymous guest creates and conducts assessment
    create_resp = await http_client.post(
        BASE_URL,
        json={"consentId": str(CONSENT_UUID)},
    )
    assert create_resp.status_code == status.HTTP_201_CREATED
    guest_aid = UUID(create_resp.json()["id"])
    assert create_resp.json()["userId"] is None

    # Guest reports symptoms and completes assessment
    await http_client.post(
        f"{BASE_URL}/{guest_aid}/messages",
        json={"content": "I have had a mild headache since yesterday."},
    )
    await http_client.post(f"{BASE_URL}/{guest_aid}/analyze")

    # 2. Claim assessment into registered user account
    service = flow_app.state.assessment_service
    with flow_sessions() as db:
        claimed = await service._orchestrator.claim_assessment(
            assessment_id=guest_aid,
            user_id=user_id,
            db_session=db,
        )
        db.commit()

    assert claimed.user_id == user_id

    # 3. Assessment now surfaces under authenticated user's history
    history_resp = await http_client.get("/api/v1/history", headers=headers)
    assert history_resp.status_code == status.HTTP_200_OK
    history_data = history_resp.json()
    owned_ids = [item["id"] for item in history_data["items"]]
    assert str(guest_aid) in owned_ids


# ===========================================================================
# 9. State Step-Back: READY to CONFIRMING on Symptom Modification
# ===========================================================================


@pytest.mark.anyio
async def test_tc_flow_a_17_state_stepback_from_ready_to_confirming_on_symptom_edit(
    flow_app: FastAPI,
    http_client: AsyncClient,
) -> None:
    """TC-FLOW-A-17: State steps back from READY to CONFIRMING upon symptom edits.

    Requirements: FR-16, FR-21.
    If symptoms were confirmed (session reached READY), modifying symptoms
    automatically steps back to CONFIRMING so the user can re-verify.
    """
    create_resp = await http_client.post(
        BASE_URL,
        json={"consentId": str(CONSENT_UUID)},
    )
    aid = UUID(create_resp.json()["id"])

    await http_client.post(
        f"{BASE_URL}/{aid}/messages",
        json={"content": "I have had a mild headache since yesterday."},
    )

    # Transition to READY via confirm_symptoms
    service = flow_app.state.assessment_service
    await service._orchestrator.confirm_symptoms(aid)

    state_ready = await http_client.get(f"{BASE_URL}/{aid}/state")
    assert state_ready.json()["state"] == "READY"

    # User modifies symptoms in READY -> steps back to CONFIRMING
    edit_resp = await http_client.patch(
        f"{BASE_URL}/{aid}/symptoms",
        json={
            "symptoms": [
                {
                    "name": "headache",
                    "severity": "SEVERE",
                }
            ]
        },
    )
    assert edit_resp.status_code == status.HTTP_200_OK

    state_stepback = await http_client.get(f"{BASE_URL}/{aid}/state")
    assert state_stepback.json()["state"] == "CONFIRMING"
