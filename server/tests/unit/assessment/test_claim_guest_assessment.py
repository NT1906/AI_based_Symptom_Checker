"""Unit tests for claiming guest assessments into registered user accounts.

Responsibilities:
    - Verify happy path for claim_assessment() transferring ownership to user.
    - Verify claim_guest_session() bulk transferring all guest assessments.
    - Verify integration with SQLAlchemy database session and repository.
    - Verify edge cases (preserving lifecycle state, symptoms, and guest ID).
    - Verify failure modes (already claimed 409, mismatch 403, missing 404).

Owner: Darshil (assessment) · Task: S2-DAR-1 · Requirements: idea §10
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import status
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.assessment import Assessment as DbAssessment
from app.models.base import Base
from app.models.consent import Consent as DbConsent
from app.models.guest_session import GuestSession as DbGuestSession
from app.models.user import User as DbUser
from app.schemas.enums import AssessmentState
from app.schemas.symptom import Symptom
from app.services.assessment.exceptions import AssessmentServiceError
from app.services.assessment.orchestrator import (
    AssessmentOrchestrator,
    AssessmentSession,
)
from app.services.assessment.state_machine import (
    AssessmentContext,
    AssessmentStateMachine,
)


@pytest.fixture
def sample_consent_id() -> uuid4:
    """Return a fresh consent UUID."""
    return uuid4()


@pytest.fixture
def sample_user_id() -> uuid4:
    """Return a fresh user UUID."""
    return uuid4()


@pytest.fixture
def sample_guest_session_id() -> uuid4:
    """Return a fresh guest session UUID."""
    return uuid4()


@pytest.fixture
def memory_db_session():
    """Create an in-memory SQLite database session fixture."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as session:
        yield session


# ---------------------------------------------------------------------------
# Happy Path Tests
# ---------------------------------------------------------------------------


async def test_claim_guest_assessment_happy_path_in_memory(
    sample_consent_id, sample_user_id, sample_guest_session_id
):
    """Verify claiming an in-memory guest assessment transfers ownership to user."""
    orchestrator = AssessmentOrchestrator()
    created = orchestrator.create_assessment(
        consent_id=sample_consent_id,
        user_id=None,
        guest_session_id=sample_guest_session_id,
    )
    assert created.user_id is None
    assert created.guest_session_id == sample_guest_session_id

    claimed = await orchestrator.claim_assessment(
        assessment_id=created.id,
        user_id=sample_user_id,
    )

    assert claimed.id == created.id
    assert claimed.user_id == sample_user_id
    assert claimed.guest_session_id == sample_guest_session_id

    session = orchestrator._sessions[created.id]
    assert session.user_id == sample_user_id
    assert session.state_machine.context.user_id == sample_user_id


async def test_claim_guest_assessment_with_matching_guest_session_id(
    sample_consent_id, sample_user_id, sample_guest_session_id
):
    """Verify claiming with an explicitly verified guest_session_id succeeds."""
    orchestrator = AssessmentOrchestrator()
    created = orchestrator.create_assessment(
        consent_id=sample_consent_id,
        guest_session_id=sample_guest_session_id,
    )

    claimed = await orchestrator.claim_assessment(
        assessment_id=created.id,
        user_id=sample_user_id,
        guest_session_id=sample_guest_session_id,
    )

    assert claimed.user_id == sample_user_id


async def test_claim_guest_assessment_with_db_session(
    memory_db_session: Session,
    sample_user_id,
    sample_guest_session_id,
):
    """Verify claiming an assessment synchronizes with the database layer."""
    orchestrator = AssessmentOrchestrator()

    user = DbUser(id=sample_user_id, email="registered@example.com")
    consent = DbConsent(policy_version="v1.0")
    guest_session = DbGuestSession(
        id=sample_guest_session_id,
        token_hash="a" * 64,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    memory_db_session.add_all([user, consent, guest_session])
    memory_db_session.flush()

    assessment = DbAssessment(
        consent_id=consent.id,
        guest_session_id=sample_guest_session_id,
        user_id=None,
        state="CONFIRMING",
    )
    memory_db_session.add(assessment)
    memory_db_session.flush()
    assessment_id = assessment.id

    # Register in memory too
    context = AssessmentContext(
        assessment_id=assessment_id,
        consent_id=consent.id,
        guest_session_id=sample_guest_session_id,
    )
    sm = AssessmentStateMachine(AssessmentState.CONFIRMING, context=context)
    orchestrator.register_session(
        assessment_id=assessment_id,
        state_machine=sm,
        consent_id=consent.id,
        guest_session_id=sample_guest_session_id,
    )

    claimed = await orchestrator.claim_assessment(
        assessment_id=assessment_id,
        user_id=sample_user_id,
        guest_session_id=sample_guest_session_id,
        db_session=memory_db_session,
    )

    assert claimed.user_id == sample_user_id

    # Verify DB state
    db_a = memory_db_session.get(DbAssessment, assessment_id)
    assert db_a is not None
    assert db_a.user_id == sample_user_id

    db_g = memory_db_session.get(DbGuestSession, sample_guest_session_id)
    assert db_g is not None
    assert db_g.is_claimed is True
    assert db_g.claimed_by_user_id == sample_user_id
    assert db_g.claimed_at is not None


async def test_claim_guest_session_transfers_multiple_assessments(
    sample_consent_id, sample_user_id, sample_guest_session_id
):
    """Verify claiming an entire guest session transfers all associated assessments."""
    orchestrator = AssessmentOrchestrator()
    a1 = orchestrator.create_assessment(
        consent_id=sample_consent_id,
        guest_session_id=sample_guest_session_id,
    )
    a2 = orchestrator.create_assessment(
        consent_id=uuid4(),
        guest_session_id=sample_guest_session_id,
    )

    claimed_list = await orchestrator.claim_guest_session(
        guest_session_id=sample_guest_session_id,
        user_id=sample_user_id,
    )

    assert len(claimed_list) == 2
    claimed_ids = {a.id for a in claimed_list}
    assert claimed_ids == {a1.id, a2.id}
    for item in claimed_list:
        assert item.user_id == sample_user_id
        assert item.guest_session_id == sample_guest_session_id


async def test_claim_guest_session_with_db_session(
    memory_db_session: Session,
    sample_user_id,
    sample_guest_session_id,
):
    """Verify bulk guest session claiming transfers DB rows via repository."""
    orchestrator = AssessmentOrchestrator()

    user = DbUser(id=sample_user_id, email="guest_claimed@example.com")
    c1 = DbConsent(policy_version="v1.0")
    c2 = DbConsent(policy_version="v1.0")
    guest_session = DbGuestSession(
        id=sample_guest_session_id,
        token_hash="b" * 64,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    memory_db_session.add_all([user, c1, c2, guest_session])
    memory_db_session.flush()

    a1 = DbAssessment(
        consent_id=c1.id, guest_session_id=sample_guest_session_id, state="START"
    )
    a2 = DbAssessment(
        consent_id=c2.id, guest_session_id=sample_guest_session_id, state="READY"
    )
    memory_db_session.add_all([a1, a2])
    memory_db_session.flush()
    a1_id, a2_id = a1.id, a2.id

    claimed_list = await orchestrator.claim_guest_session(
        guest_session_id=sample_guest_session_id,
        user_id=sample_user_id,
        db_session=memory_db_session,
    )

    assert len(claimed_list) == 2
    for item in claimed_list:
        assert item.user_id == sample_user_id

    # Verify DB update
    assert memory_db_session.get(DbAssessment, a1_id).user_id == sample_user_id
    assert memory_db_session.get(DbAssessment, a2_id).user_id == sample_user_id
    g = memory_db_session.get(DbGuestSession, sample_guest_session_id)
    assert g.is_claimed is True
    assert g.claimed_by_user_id == sample_user_id


# ---------------------------------------------------------------------------
# Edge Case Tests
# ---------------------------------------------------------------------------


async def test_create_guest_assessment_sets_guest_session_id(
    sample_consent_id, sample_guest_session_id
):
    """Verify creating assessment with guest_session_id populates read and context."""
    orchestrator = AssessmentOrchestrator()
    created = orchestrator.create_assessment(
        consent_id=sample_consent_id,
        guest_session_id=sample_guest_session_id,
    )

    assert created.user_id is None
    assert created.guest_session_id == sample_guest_session_id
    session = orchestrator._sessions[created.id]
    assert session.guest_session_id == sample_guest_session_id
    assert session.state_machine.context.guest_session_id == sample_guest_session_id


async def test_claim_assessment_preserves_lifecycle_state_and_symptoms(
    sample_consent_id, sample_user_id, sample_guest_session_id
):
    """Verify claiming in CONFIRMING state preserves symptoms and state."""
    orchestrator = AssessmentOrchestrator()
    created = orchestrator.create_assessment(
        consent_id=sample_consent_id,
        guest_session_id=sample_guest_session_id,
    )

    session = orchestrator._sessions[created.id]
    session.state_machine.start_symptom_collection()
    await orchestrator.add_symptom(
        created.id, Symptom(name="headache", severity="MODERATE")
    )

    assert len(session.symptoms) == 1
    state_before = session.state_machine.current_state

    claimed = await orchestrator.claim_assessment(
        assessment_id=created.id,
        user_id=sample_user_id,
    )

    assert claimed.user_id == sample_user_id
    assert claimed.state == state_before
    assert len(session.symptoms) == 1
    assert session.symptoms[0].name == "headache"


async def test_register_session_as_session_instance_retains_guest_id(
    sample_consent_id, sample_guest_session_id
):
    """Verify registering an AssessmentSession instance directly retains guest ID."""
    orchestrator = AssessmentOrchestrator()
    aid = uuid4()
    context = AssessmentContext(
        assessment_id=aid,
        consent_id=sample_consent_id,
        guest_session_id=sample_guest_session_id,
    )
    sm = AssessmentStateMachine(AssessmentState.START, context=context)
    session = AssessmentSession(
        id=aid,
        consent_id=sample_consent_id,
        user_id=None,
        guest_session_id=sample_guest_session_id,
        state_machine=sm,
    )

    registered = orchestrator.register_session(session)
    assert registered.guest_session_id == sample_guest_session_id
    assert orchestrator.get_assessment(aid).guest_session_id == sample_guest_session_id


# ---------------------------------------------------------------------------
# Failure Case Tests
# ---------------------------------------------------------------------------


async def test_claim_assessment_fails_when_assessment_not_found(sample_user_id):
    """Verify claiming an unknown assessment raises 404 ASSESSMENT_NOT_FOUND."""
    orchestrator = AssessmentOrchestrator()
    unknown_id = uuid4()

    with pytest.raises(AssessmentServiceError) as exc_info:
        await orchestrator.claim_assessment(
            assessment_id=unknown_id,
            user_id=sample_user_id,
        )
    assert exc_info.value.code == "ASSESSMENT_NOT_FOUND"
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


async def test_claim_assessment_fails_when_already_claimed(
    sample_consent_id, sample_user_id
):
    """Verify claiming an already claimed assessment raises 409 ALREADY_CLAIMED."""
    orchestrator = AssessmentOrchestrator()
    created = orchestrator.create_assessment(
        consent_id=sample_consent_id,
        user_id=sample_user_id,
    )

    with pytest.raises(AssessmentServiceError) as exc_info:
        await orchestrator.claim_assessment(
            assessment_id=created.id,
            user_id=uuid4(),
        )
    assert exc_info.value.code == "ALREADY_CLAIMED"
    assert exc_info.value.status_code == status.HTTP_409_CONFLICT


async def test_claim_assessment_fails_when_guest_session_mismatches(
    sample_consent_id, sample_user_id, sample_guest_session_id
):
    """Verify claiming with mismatched guest_session_id raises 403 FORBIDDEN."""
    orchestrator = AssessmentOrchestrator()
    created = orchestrator.create_assessment(
        consent_id=sample_consent_id,
        guest_session_id=sample_guest_session_id,
    )

    different_guest_id = uuid4()
    with pytest.raises(AssessmentServiceError) as exc_info:
        await orchestrator.claim_assessment(
            assessment_id=created.id,
            user_id=sample_user_id,
            guest_session_id=different_guest_id,
        )
    assert exc_info.value.code == "GUEST_SESSION_MISMATCH"
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


async def test_claim_guest_session_fails_when_session_not_found(sample_user_id):
    """Verify claiming unknown guest session raises 404 GUEST_SESSION_NOT_FOUND."""
    orchestrator = AssessmentOrchestrator()
    unknown_guest_id = uuid4()

    with pytest.raises(AssessmentServiceError) as exc_info:
        await orchestrator.claim_guest_session(
            guest_session_id=unknown_guest_id,
            user_id=sample_user_id,
        )
    assert exc_info.value.code == "GUEST_SESSION_NOT_FOUND"
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


async def test_claim_guest_session_fails_when_already_claimed(
    sample_consent_id, sample_user_id, sample_guest_session_id
):
    """Verify claiming an already claimed guest session raises 409 ALREADY_CLAIMED."""
    orchestrator = AssessmentOrchestrator()
    orchestrator.create_assessment(
        consent_id=sample_consent_id,
        guest_session_id=sample_guest_session_id,
    )

    # First claim succeeds
    await orchestrator.claim_guest_session(
        guest_session_id=sample_guest_session_id,
        user_id=sample_user_id,
    )

    # Second claim fails
    with pytest.raises(AssessmentServiceError) as exc_info:
        await orchestrator.claim_guest_session(
            guest_session_id=sample_guest_session_id,
            user_id=uuid4(),
        )
    assert exc_info.value.code == "ALREADY_CLAIMED"
    assert exc_info.value.status_code == status.HTTP_409_CONFLICT


async def test_claim_assessment_db_fails_when_user_not_found(
    memory_db_session: Session,
    sample_guest_session_id,
):
    """Verify claiming against DB raises 404 USER_NOT_FOUND if user record missing."""
    orchestrator = AssessmentOrchestrator()

    consent = DbConsent(policy_version="v1.0")
    guest_session = DbGuestSession(
        id=sample_guest_session_id,
        token_hash="c" * 64,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    memory_db_session.add_all([consent, guest_session])
    memory_db_session.flush()

    assessment = DbAssessment(
        consent_id=consent.id,
        guest_session_id=sample_guest_session_id,
        user_id=None,
    )
    memory_db_session.add(assessment)
    memory_db_session.flush()

    nonexistent_user_id = uuid4()
    with pytest.raises(AssessmentServiceError) as exc_info:
        await orchestrator.claim_assessment(
            assessment_id=assessment.id,
            user_id=nonexistent_user_id,
            db_session=memory_db_session,
        )
    assert exc_info.value.code == "USER_NOT_FOUND"
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
