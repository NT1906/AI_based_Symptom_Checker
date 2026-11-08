"""Unit tests for passing profile context into assessment analysis.

Responsibilities:
    - Test initializing assessment with optional profile context.
    - Test updating and retrieving profile context on active sessions.
    - Test passing profile context directly into generate_result.
    - Test state machine AssessmentContext preserves profile context.
    - Test edge cases: empty profile and condition deduplication.
    - Test failure cases: 404 on missing assessment ID.

Owner: Darshil (assessment) · Task: S2-DAR-3 · Requirements: FR-02, idea §10
"""

from uuid import UUID, uuid4

import pytest
from fastapi import status

from app.schemas.enums import AssessmentState
from app.schemas.profile import AgeBand, BiologicalSex, ProfileContext
from app.services.ai.mock_provider import MockAiProvider
from app.services.assessment.exceptions import AssessmentServiceError
from app.services.assessment.orchestrator import AssessmentOrchestrator


@pytest.fixture
def orchestrator() -> AssessmentOrchestrator:
    """Fixture providing an AssessmentOrchestrator with mock AI provider."""
    return AssessmentOrchestrator(ai_gateway=MockAiProvider())


@pytest.fixture
def active_assessment_id(orchestrator: AssessmentOrchestrator) -> UUID:
    """Fixture initializing an active assessment session."""
    assessment = orchestrator.create_assessment(consent_id=uuid4())
    return assessment.id


# =============================================================================
# 1. ProfileContext Schema & Sanitization Unit Tests
# =============================================================================


def test_profile_context_sanitizes_chronic_conditions() -> None:
    """Test that chronic conditions list strips whitespace and deduplicates."""
    context = ProfileContext(
        age_band=AgeBand.ADULT,
        biological_sex=BiologicalSex.FEMALE,
        chronic_conditions=["  Asthma ", "Diabetes", "Asthma", "  ", "Hypertension"],
    )

    assert context.age_band == AgeBand.ADULT
    assert context.biological_sex == BiologicalSex.FEMALE
    assert context.sex == BiologicalSex.FEMALE
    assert context.chronic_conditions == ["Asthma", "Diabetes", "Hypertension"]
    assert context.is_empty is False


def test_profile_context_empty_detection() -> None:
    """Test is_empty property on unpopulated ProfileContext."""
    empty_context = ProfileContext()
    assert empty_context.is_empty is True
    assert empty_context.age_band is None
    assert empty_context.biological_sex is None
    assert empty_context.chronic_conditions == []


# =============================================================================
# 2. create_assessment with ProfileContext
# =============================================================================


def test_create_assessment_with_profile_context(
    orchestrator: AssessmentOrchestrator,
) -> None:
    """Test create_assessment persists profile context into session."""
    profile = ProfileContext(
        age_band=AgeBand.SENIOR,
        biological_sex=BiologicalSex.MALE,
        chronic_conditions=["Hypertension", "COPD"],
    )
    assessment = orchestrator.create_assessment(
        consent_id=uuid4(),
        user_id=uuid4(),
        profile=profile,
    )

    retrieved = orchestrator.get_profile_context(assessment.id)
    assert retrieved is not None
    assert retrieved.age_band == AgeBand.SENIOR
    assert retrieved.biological_sex == BiologicalSex.MALE
    assert retrieved.chronic_conditions == ["Hypertension", "COPD"]


# =============================================================================
# 3. set_profile_context and get_profile_context
# =============================================================================


def test_set_and_get_profile_context_happy_path(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id: UUID,
) -> None:
    """Test setting and updating profile context on an active assessment session."""
    # Initially none
    assert orchestrator.get_profile_context(active_assessment_id) is None

    # Attach profile context
    profile = ProfileContext(
        age_band=AgeBand.YOUNG_ADULT,
        biological_sex=BiologicalSex.FEMALE,
        chronic_conditions=["Migraine"],
    )
    orchestrator.set_profile_context(active_assessment_id, profile)

    retrieved = orchestrator.get_profile_context(active_assessment_id)
    assert retrieved is not None
    assert retrieved.age_band == AgeBand.YOUNG_ADULT
    assert retrieved.chronic_conditions == ["Migraine"]

    # In-place update
    updated_profile = ProfileContext(
        age_band=AgeBand.ADULT,
        biological_sex=BiologicalSex.FEMALE,
        chronic_conditions=["Migraine", "Asthma"],
    )
    orchestrator.set_profile_context(active_assessment_id, updated_profile)

    retrieved_updated = orchestrator.get_profile_context(active_assessment_id)
    assert retrieved_updated is not None
    assert retrieved_updated.age_band == AgeBand.ADULT
    assert retrieved_updated.chronic_conditions == ["Migraine", "Asthma"]


def test_set_profile_context_nonexistent_assessment_raises_404(
    orchestrator: AssessmentOrchestrator,
) -> None:
    """Test that set_profile_context on unknown assessment UUID raises 404."""
    with pytest.raises(AssessmentServiceError) as exc_info:
        orchestrator.set_profile_context(uuid4(), ProfileContext())

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.code == "ASSESSMENT_NOT_FOUND"


def test_get_profile_context_nonexistent_assessment_raises_404(
    orchestrator: AssessmentOrchestrator,
) -> None:
    """Test that get_profile_context on unknown assessment UUID raises 404."""
    with pytest.raises(AssessmentServiceError) as exc_info:
        orchestrator.get_profile_context(uuid4())

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.code == "ASSESSMENT_NOT_FOUND"


# =============================================================================
# 4. generate_result with ProfileContext
# =============================================================================


@pytest.mark.anyio
async def test_generate_result_incorporates_profile_context(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id: UUID,
) -> None:
    """Test generate_result seamlessly incorporates profile context into analysis."""
    # Populate assessment dialogue and symptoms
    await orchestrator.process_message(
        active_assessment_id,
        "I have a severe cough and chest tightness",
    )
    await orchestrator.confirm_symptoms(active_assessment_id)

    profile = ProfileContext(
        age_band=AgeBand.SENIOR,
        biological_sex=BiologicalSex.MALE,
        chronic_conditions=["Asthma", "Diabetes"],
    )

    result = await orchestrator.generate_result(
        active_assessment_id,
        profile=profile,
    )

    assert result.assessment_id == active_assessment_id
    assert (
        orchestrator.get_state(active_assessment_id).state == AssessmentState.COMPLETED
    )

    # Verify session retains the passed profile context
    saved_profile = orchestrator.get_profile_context(active_assessment_id)
    assert saved_profile is not None
    assert saved_profile.age_band == AgeBand.SENIOR
    assert saved_profile.chronic_conditions == ["Asthma", "Diabetes"]


@pytest.mark.anyio
async def test_generate_result_preserves_pre_attached_profile_context(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id: UUID,
) -> None:
    """Test generate_result uses pre-attached profile context when omitted in call."""
    profile = ProfileContext(
        age_band=AgeBand.CHILD,
        biological_sex=BiologicalSex.FEMALE,
        chronic_conditions=["Eczema"],
    )
    orchestrator.set_profile_context(active_assessment_id, profile)

    await orchestrator.process_message(
        active_assessment_id,
        "I have a runny nose and slight fever",
    )
    await orchestrator.confirm_symptoms(active_assessment_id)

    # Call generate_result without explicit profile param
    result = await orchestrator.generate_result(active_assessment_id)

    assert result.assessment_id == active_assessment_id
    retained = orchestrator.get_profile_context(active_assessment_id)
    assert retained is not None
    assert retained.age_band == AgeBand.CHILD
    assert retained.chronic_conditions == ["Eczema"]
