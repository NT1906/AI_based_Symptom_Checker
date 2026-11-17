"""Unit tests for authorization audit and ownership boundaries.

Responsibilities:
    - Verify registered user ownership boundaries (no cross-user access / IDOR).
    - Verify anonymous guest session ownership boundaries (no cross-guest access).
    - Verify post-claim boundary (old guest token blocked after claim).
    - Verify database-backed ownership validation via active SQLAlchemy session.
    - Verify check_ownership() boolean helper.
    - Verify 404 for nonexistent assessment.
    - Verify ownership enforcement across all AssessmentOrchestrator methods.

Owner: Darshil (assessment) · Task: S2-DAR-6 · Requirements: NFR-03
"""

from uuid import uuid4

import pytest
from fastapi import status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.assessment import Assessment as DbAssessment
from app.models.base import Base
from app.models.consent import Consent as DbConsent
from app.models.user import User as DbUser
from app.schemas.enums import AssessmentState, Severity
from app.schemas.profile import AgeBand, ProfileContext
from app.schemas.symptom import SymptomCreate, SymptomUpdate
from app.services.ai.mock_provider import MockAiProvider
from app.services.assessment.exceptions import (
    AssessmentAccessDeniedError,
    AssessmentServiceError,
)
from app.services.assessment.orchestrator import AssessmentOrchestrator


@pytest.fixture
def memory_db_session():
    """Create an in-memory SQLite database session fixture."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    db_session = session_factory()
    try:
        yield db_session
    finally:
        db_session.close()


@pytest.fixture
def orchestrator() -> AssessmentOrchestrator:
    """Fixture providing an AssessmentOrchestrator with mock AI gateway."""
    return AssessmentOrchestrator(ai_gateway=MockAiProvider())


# =============================================================================
# 1. Registered User Ownership Tests
# =============================================================================


def test_registered_user_access_authorized_happy_path(
    orchestrator: AssessmentOrchestrator,
) -> None:
    """Test that the true owner of a registered assessment is authorized."""
    owner_id = uuid4()
    assessment = orchestrator.create_assessment(consent_id=uuid4(), user_id=owner_id)

    # Calling assert_ownership with correct user_id must succeed without exception
    orchestrator.assert_ownership(assessment.id, user_id=owner_id)
    assert orchestrator.check_ownership(assessment.id, user_id=owner_id) is True


def test_cross_user_access_rejected_with_403(
    orchestrator: AssessmentOrchestrator,
) -> None:
    """Test that another registered user (User B) is blocked from User A."""
    user_a = uuid4()
    user_b = uuid4()
    assessment = orchestrator.create_assessment(consent_id=uuid4(), user_id=user_a)

    with pytest.raises(AssessmentAccessDeniedError) as exc_info:
        orchestrator.assert_ownership(assessment.id, user_id=user_b)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.code == "ASSESSMENT_ACCESS_DENIED"
    assert exc_info.value.assessment_id == assessment.id
    assert orchestrator.check_ownership(assessment.id, user_id=user_b) is False


def test_unauthenticated_access_to_user_assessment_rejected_with_403(
    orchestrator: AssessmentOrchestrator,
) -> None:
    """Test unauthenticated callers cannot access registered assessment."""
    owner_id = uuid4()
    guest_token = uuid4()
    assessment = orchestrator.create_assessment(consent_id=uuid4(), user_id=owner_id)

    # Anonymous caller with no credentials
    with pytest.raises(AssessmentAccessDeniedError) as exc_info:
        orchestrator.assert_ownership(assessment.id, user_id=None)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.code == "ASSESSMENT_ACCESS_DENIED"

    # Guest presenting a guest token
    with pytest.raises(AssessmentAccessDeniedError) as exc_info:
        orchestrator.assert_ownership(
            assessment.id, user_id=None, guest_session_id=guest_token
        )

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.code == "ASSESSMENT_ACCESS_DENIED"


# =============================================================================
# 2. Anonymous Guest Session Ownership Tests
# =============================================================================


def test_guest_session_access_authorized_happy_path(
    orchestrator: AssessmentOrchestrator,
) -> None:
    """Test that matching guest session token is authorized for guest assessment."""
    guest_id = uuid4()
    assessment = orchestrator.create_assessment(
        consent_id=uuid4(), user_id=None, guest_session_id=guest_id
    )

    orchestrator.assert_ownership(assessment.id, guest_session_id=guest_id)
    assert orchestrator.check_ownership(assessment.id, guest_session_id=guest_id)


def test_cross_guest_access_rejected_with_403(
    orchestrator: AssessmentOrchestrator,
) -> None:
    """Test that mismatched guest session ID (Guest B) is blocked from Guest A."""
    guest_a = uuid4()
    guest_b = uuid4()
    assessment = orchestrator.create_assessment(
        consent_id=uuid4(), user_id=None, guest_session_id=guest_a
    )

    with pytest.raises(AssessmentAccessDeniedError) as exc_info:
        orchestrator.assert_ownership(assessment.id, guest_session_id=guest_b)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.code == "GUEST_SESSION_MISMATCH"
    assert not orchestrator.check_ownership(assessment.id, guest_session_id=guest_b)


def test_registered_user_access_to_unclaimed_guest_without_token_rejected(
    orchestrator: AssessmentOrchestrator,
) -> None:
    """Test registered user cannot access unclaimed guest assessment directly."""
    user_id = uuid4()
    guest_id = uuid4()
    assessment = orchestrator.create_assessment(
        consent_id=uuid4(), user_id=None, guest_session_id=guest_id
    )

    with pytest.raises(AssessmentAccessDeniedError) as exc_info:
        orchestrator.assert_ownership(assessment.id, user_id=user_id)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.code == "ASSESSMENT_ACCESS_DENIED"


# =============================================================================
# 3. Post-Claim Boundary Tests
# =============================================================================


@pytest.mark.asyncio
async def test_post_claim_boundary_revokes_guest_access(
    orchestrator: AssessmentOrchestrator,
) -> None:
    """Test that once claimed, old guest token is blocked and user is authorized."""
    user_id = uuid4()
    guest_id = uuid4()
    assessment = orchestrator.create_assessment(
        consent_id=uuid4(), user_id=None, guest_session_id=guest_id
    )

    # Claim the assessment
    await orchestrator.claim_assessment(
        assessment_id=assessment.id,
        user_id=user_id,
        guest_session_id=guest_id,
    )

    # The claiming user now has full access
    orchestrator.assert_ownership(assessment.id, user_id=user_id)
    assert orchestrator.check_ownership(assessment.id, user_id=user_id) is True

    # The old guest session token can no longer access it
    with pytest.raises(AssessmentAccessDeniedError) as exc_info:
        orchestrator.assert_ownership(assessment.id, guest_session_id=guest_id)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.code == "ASSESSMENT_ACCESS_DENIED"


# =============================================================================
# 4. Database-Backed Ownership Verification Tests
# =============================================================================


def test_database_backed_ownership_verification(
    orchestrator: AssessmentOrchestrator,
    memory_db_session,
) -> None:
    """Test assert_ownership against SQLAlchemy database models."""
    user_id = uuid4()
    other_user_id = uuid4()
    consent_id = uuid4()
    assessment_id = uuid4()

    db_user = DbUser(id=user_id, email="authorized@example.com")
    db_consent = DbConsent(id=consent_id, policy_version="v1.0")
    db_assessment = DbAssessment(
        id=assessment_id,
        user_id=user_id,
        consent_id=consent_id,
        state=AssessmentState.START.value,
    )
    memory_db_session.add_all([db_user, db_consent, db_assessment])
    memory_db_session.commit()

    # Authorized user via db_session
    orchestrator.assert_ownership(
        assessment_id=assessment_id,
        user_id=user_id,
        db_session=memory_db_session,
    )
    assert (
        orchestrator.check_ownership(
            assessment_id=assessment_id,
            user_id=user_id,
            db_session=memory_db_session,
        )
        is True
    )

    # Cross-user via db_session
    with pytest.raises(AssessmentAccessDeniedError) as exc_info:
        orchestrator.assert_ownership(
            assessment_id=assessment_id,
            user_id=other_user_id,
            db_session=memory_db_session,
        )
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# 5. Nonexistent Assessment Tests
# =============================================================================


def test_nonexistent_assessment_raises_404(
    orchestrator: AssessmentOrchestrator,
) -> None:
    """Test that missing assessment raises 404 AssessmentServiceError."""
    missing_id = uuid4()
    with pytest.raises(AssessmentServiceError) as exc_info:
        orchestrator.assert_ownership(missing_id, user_id=uuid4())

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.code == "ASSESSMENT_NOT_FOUND"
    assert orchestrator.check_ownership(missing_id, user_id=uuid4()) is False


# =============================================================================
# 6. Operational Methods Ownership Guard Coverage
# =============================================================================


@pytest.mark.asyncio
async def test_operational_methods_reject_unauthorized_user(
    orchestrator: AssessmentOrchestrator,
) -> None:
    """Test that orchestrator methods strictly enforce ownership guard when called."""
    owner_id = uuid4()
    attacker_id = uuid4()
    assessment = orchestrator.create_assessment(consent_id=uuid4(), user_id=owner_id)
    aid = assessment.id

    # 1. get_assessment
    with pytest.raises(AssessmentAccessDeniedError):
        orchestrator.get_assessment(aid, user_id=attacker_id)

    # 2. get_messages
    with pytest.raises(AssessmentAccessDeniedError):
        orchestrator.get_messages(aid, user_id=attacker_id)

    # 3. list_messages
    with pytest.raises(AssessmentAccessDeniedError):
        await orchestrator.list_messages(aid, user_id=attacker_id)

    # 4. get_symptoms
    with pytest.raises(AssessmentAccessDeniedError):
        orchestrator.get_symptoms(aid, user_id=attacker_id)

    # 5. get_state
    with pytest.raises(AssessmentAccessDeniedError):
        orchestrator.get_state(aid, user_id=attacker_id)

    # 6. get_profile_context
    with pytest.raises(AssessmentAccessDeniedError):
        orchestrator.get_profile_context(aid, user_id=attacker_id)

    # 7. set_profile_context
    with pytest.raises(AssessmentAccessDeniedError):
        orchestrator.set_profile_context(
            aid,
            ProfileContext(age_band=AgeBand.ADULT),
            user_id=attacker_id,
        )

    # 8. process_message
    with pytest.raises(AssessmentAccessDeniedError):
        await orchestrator.process_message(
            aid, "I have a headache", user_id=attacker_id
        )

    # 9. confirm_symptoms
    with pytest.raises(AssessmentAccessDeniedError):
        await orchestrator.confirm_symptoms(aid, user_id=attacker_id)

    # 10. update_symptoms
    with pytest.raises(AssessmentAccessDeniedError):
        await orchestrator.update_symptoms(aid, [], user_id=attacker_id)

    # 11. add_symptom
    with pytest.raises(AssessmentAccessDeniedError):
        await orchestrator.add_symptom(
            aid,
            SymptomCreate(name="Fever", severity=Severity.MILD),
            user_id=attacker_id,
        )

    # 12. remove_symptom
    with pytest.raises(AssessmentAccessDeniedError):
        await orchestrator.remove_symptom(aid, "Fever", user_id=attacker_id)

    # 13. edit_symptom
    with pytest.raises(AssessmentAccessDeniedError):
        await orchestrator.edit_symptom(
            aid,
            SymptomUpdate(name="Fever", severity=Severity.MODERATE),
            user_id=attacker_id,
        )

    # 14. step_back_to_chat
    with pytest.raises(AssessmentAccessDeniedError):
        await orchestrator.step_back_to_chat(aid, user_id=attacker_id)

    # 15. restart_assessment
    with pytest.raises(AssessmentAccessDeniedError):
        await orchestrator.restart_assessment(aid, user_id=attacker_id)

    # 16. generate_result
    with pytest.raises(AssessmentAccessDeniedError):
        await orchestrator.generate_result(aid, user_id=attacker_id)

    # 17. merge_image_findings
    with pytest.raises(AssessmentAccessDeniedError):
        await orchestrator.merge_image_findings(aid, [], user_id=attacker_id)

    # 18. process_image
    with pytest.raises(AssessmentAccessDeniedError):
        await orchestrator.process_image(aid, b"fake_bytes", user_id=attacker_id)


@pytest.mark.asyncio
async def test_operational_methods_allow_authorized_user(
    orchestrator: AssessmentOrchestrator,
) -> None:
    """Test that orchestrator methods succeed when called by the authorized owner."""
    owner_id = uuid4()
    assessment = orchestrator.create_assessment(consent_id=uuid4(), user_id=owner_id)
    aid = assessment.id

    # get_assessment
    read_result = orchestrator.get_assessment(aid, user_id=owner_id)
    assert read_result is not None
    assert read_result.id == aid

    # get_messages
    msgs = orchestrator.get_messages(aid, user_id=owner_id)
    assert isinstance(msgs, list)

    # get_symptoms
    syms = orchestrator.get_symptoms(aid, user_id=owner_id)
    assert isinstance(syms, list)

    # get_state
    state = orchestrator.get_state(aid, user_id=owner_id)
    assert state.state == AssessmentState.START

    # Transition to SYMPTOM_COLLECTION so symptom operations are permitted
    orchestrator._sessions[aid].state_machine.transition_to(
        AssessmentState.SYMPTOM_COLLECTION
    )

    # add_symptom
    added = await orchestrator.add_symptom(
        aid,
        SymptomCreate(name="Headache", severity=Severity.MILD),
        user_id=owner_id,
    )
    assert added.name.lower() == "headache"

    # edit_symptom
    edited = await orchestrator.edit_symptom(
        aid,
        SymptomUpdate(name="Headache", severity=Severity.SEVERE),
        user_id=owner_id,
    )
    assert edited.severity == Severity.SEVERE

    # remove_symptom
    remaining = await orchestrator.remove_symptom(aid, "Headache", user_id=owner_id)
    assert len(remaining) == 0
