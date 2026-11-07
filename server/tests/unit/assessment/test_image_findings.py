"""Unit tests for merging image findings into assessment state.

Responsibilities:
    - Test merging visual findings from clear image analysis (happy path).
    - Test handling unclear image analysis without modifying symptom state.
    - Test merging with pre-existing text symptoms (deduplication & attribute retain).
    - Test process_image handling analyzer failures gracefully (ImageAnalysisError).
    - Test rejecting image merging on missing assessment (HTTP 404).
    - Test rejecting image merging on completed/terminal states (HTTP 409).
    - Test multiple sequential image findings merging.
    - Test confirm_symptoms with visual findings transitioning to READY.

Owner: Darshil (assessment) · Task: S2-DAR-2 · Requirements: idea §3, FR-16, FR-21
"""

from uuid import UUID, uuid4

import pytest
from fastapi import status

from app.schemas.enums import AssessmentState, Severity, SymptomSource
from app.services.ai.mock_provider import MockAiProvider
from app.services.ai.schemas import ExtractedSymptom, SeverityEnum
from app.services.assessment.exceptions import (
    AssessmentServiceError,
    InvalidStateTransitionError,
)
from app.services.assessment.orchestrator import (
    AssessmentOrchestrator,
    merge_symptoms,
)
from app.services.image.findings import build_analysis, to_extracted_symptoms
from app.services.image.mock_analyzer import MockImageAnalyzer
from app.services.image.schemas import ImageLabel, UnclearReason


@pytest.fixture
def orchestrator() -> AssessmentOrchestrator:
    """Fixture providing an AssessmentOrchestrator backed by mock providers."""
    return AssessmentOrchestrator(
        ai_gateway=MockAiProvider(),
        image_analyzer=MockImageAnalyzer(),
    )


@pytest.fixture
def active_assessment_id(orchestrator: AssessmentOrchestrator) -> UUID:
    """Fixture initializing a consent-backed assessment session."""
    assessment = orchestrator.create_assessment(consent_id=uuid4())
    return assessment.id


# =============================================================================
# 1. merge_symptoms unit tests with IMAGE_FINDING provenance
# =============================================================================


def test_merge_symptoms_default_source_image_finding() -> None:
    """Test merge_symptoms tags new findings with IMAGE_FINDING when specified."""
    analysis = build_analysis(ImageLabel.URTICARIA, "test-v1")
    extracted = to_extracted_symptoms(analysis)

    merged = merge_symptoms(
        existing=[],
        extracted_symptoms=extracted,
        default_source=SymptomSource.IMAGE_FINDING,
    )

    assert len(merged) == 1
    assert merged[0].name == "hives"
    assert merged[0].severity == Severity.UNKNOWN
    assert merged[0].source == SymptomSource.IMAGE_FINDING


def test_merge_symptoms_preserves_confirmed_status() -> None:
    """Test that image findings do not overwrite already confirmed text symptoms."""
    # User confirmed hives previously
    existing_symptom = merge_symptoms(
        [],
        [ExtractedSymptom(name="hives", severity=SeverityEnum.MODERATE)],
        default_source=SymptomSource.USER,
    )[0]
    existing_symptom.source = SymptomSource.USER_CONFIRMED

    # Photo analysis also found hives
    analysis = build_analysis(ImageLabel.URTICARIA, "test-v1")
    extracted = to_extracted_symptoms(analysis)

    merged = merge_symptoms(
        existing=[existing_symptom],
        extracted_symptoms=extracted,
        default_source=SymptomSource.IMAGE_FINDING,
    )

    assert len(merged) == 1
    assert merged[0].name == "hives"
    assert merged[0].severity == Severity.MODERATE  # Kept moderate over UNKNOWN
    assert merged[0].source == SymptomSource.USER_CONFIRMED


# =============================================================================
# 2. merge_image_findings on AssessmentOrchestrator
# =============================================================================


@pytest.mark.anyio
async def test_merge_image_findings_happy_path(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id: UUID,
) -> None:
    """Test merging clear photo findings into an active assessment."""
    analysis = build_analysis(ImageLabel.ECZEMA, "mock-1")
    symptoms = await orchestrator.merge_image_findings(
        active_assessment_id,
        analysis,
    )

    names = {s.name for s in symptoms}
    assert "dry_skin" in names
    assert "scaly_skin" in names
    assert "skin_rash" in names
    assert all(s.severity == Severity.UNKNOWN for s in symptoms)
    assert all(s.source == SymptomSource.IMAGE_FINDING for s in symptoms)

    # State machine context should mirror the orchestrator session symptoms
    state = orchestrator.get_state(active_assessment_id)
    assert len(state.symptoms) == 3


@pytest.mark.anyio
async def test_merge_image_findings_unclear_photo_ignored(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id: UUID,
) -> None:
    """Test that unclear image findings do not add symptoms or alter state."""
    # First, add a text symptom via process_message
    await orchestrator.process_message(
        active_assessment_id,
        "I have a fever since yesterday",
    )
    initial_symptoms = orchestrator.get_symptoms(active_assessment_id)
    initial_count = len(initial_symptoms)
    assert initial_count > 0

    # Submit an unclear analysis
    unclear_analysis = build_analysis(
        ImageLabel.UNCLEAR,
        "mock-1",
        reason=UnclearReason.POOR_QUALITY,
    )
    symptoms_after = await orchestrator.merge_image_findings(
        active_assessment_id,
        unclear_analysis,
    )

    assert len(symptoms_after) == initial_count
    assert [s.name for s in symptoms_after] == [s.name for s in initial_symptoms]


@pytest.mark.anyio
async def test_merge_image_findings_combines_with_existing_text_symptoms(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id: UUID,
) -> None:
    """Test that photo findings join previously reported text symptoms."""
    # Ingest text symptom
    await orchestrator.process_message(
        active_assessment_id,
        "I have itchy skin and fatigue",
    )
    text_symptoms = orchestrator.get_symptoms(active_assessment_id)
    text_names = {s.name for s in text_symptoms}

    # Ingest photo analysis (cellulitis -> spreading_redness, skin_swelling)
    analysis = build_analysis(ImageLabel.CELLULITIS, "mock-1")
    updated_symptoms = await orchestrator.merge_image_findings(
        active_assessment_id,
        analysis,
    )

    updated_names = {s.name for s in updated_symptoms}
    assert text_names.issubset(updated_names)
    assert "spreading_redness" in updated_names
    assert "skin_swelling" in updated_names


@pytest.mark.anyio
async def test_merge_image_findings_missing_assessment_raises_404(
    orchestrator: AssessmentOrchestrator,
) -> None:
    """Test that attempting to merge findings into nonexistent session raises 404."""
    random_id = uuid4()
    analysis = build_analysis(ImageLabel.ACNE, "mock-1")

    with pytest.raises(AssessmentServiceError) as exc_info:
        await orchestrator.merge_image_findings(random_id, analysis)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.code == "ASSESSMENT_NOT_FOUND"


@pytest.mark.anyio
async def test_merge_image_findings_terminal_state_raises_409(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id: UUID,
) -> None:
    """Test that merging image findings after analysis completion is rejected."""
    # Move through assessment flow to COMPLETED
    await orchestrator.process_message(
        active_assessment_id,
        "I have a mild headache",
    )
    await orchestrator.confirm_symptoms(active_assessment_id)
    await orchestrator.generate_result(active_assessment_id)

    assert (
        orchestrator.get_state(active_assessment_id).state == AssessmentState.COMPLETED
    )

    analysis = build_analysis(ImageLabel.SCABIES, "mock-1")
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        await orchestrator.merge_image_findings(active_assessment_id, analysis)

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT


# =============================================================================
# 3. process_image orchestrator method
# =============================================================================


@pytest.mark.anyio
async def test_process_image_happy_path() -> None:
    """Test process_image executes analyzer and merges visual findings."""
    mock_analyzer = MockImageAnalyzer(label=ImageLabel.CHICKENPOX)
    orch = AssessmentOrchestrator(
        ai_gateway=MockAiProvider(),
        image_analyzer=mock_analyzer,
    )
    assessment = orch.create_assessment(consent_id=uuid4())

    image_data = b"fake_jpeg_data"
    symptoms = await orch.process_image(assessment.id, image_data)

    assert len(symptoms) == 1
    assert symptoms[0].name == "fluid_filled_blisters"
    assert symptoms[0].source == SymptomSource.IMAGE_FINDING


@pytest.mark.anyio
async def test_process_image_analyzer_failure_continues_gracefully(
    active_assessment_id: UUID,
) -> None:
    """Test process_image catches ImageAnalysisError and continues without crashing."""
    failing_analyzer = MockImageAnalyzer(fail=True)
    orch = AssessmentOrchestrator(
        ai_gateway=MockAiProvider(),
        image_analyzer=failing_analyzer,
    )
    orch.create_assessment(
        consent_id=uuid4(),
        assessment_id=active_assessment_id,
    )

    # Process a message first so symptoms exist
    await orch.process_message(active_assessment_id, "I have back pain")
    initial_count = len(orch.get_symptoms(active_assessment_id))

    # Photo analysis fails with ImageAnalysisError
    symptoms = await orch.process_image(active_assessment_id, b"some_image_bytes")

    # Assessment must not crash, and existing symptoms remain intact
    assert len(symptoms) == initial_count
    assert orch.get_state(active_assessment_id).state != AssessmentState.ERROR


@pytest.mark.anyio
async def test_process_image_nonexistent_assessment_raises_404(
    orchestrator: AssessmentOrchestrator,
) -> None:
    """Test process_image on nonexistent assessment raises 404."""
    with pytest.raises(AssessmentServiceError) as exc_info:
        await orchestrator.process_image(uuid4(), b"valid_image_bytes")

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# 4. End-to-end confirmation with visual symptoms
# =============================================================================


@pytest.mark.anyio
async def test_confirm_symptoms_with_visual_findings_reaches_ready(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id: UUID,
) -> None:
    """Test that visual findings can be confirmed and advance state to READY."""
    analysis = build_analysis(ImageLabel.URTICARIA, "mock-1")
    await orchestrator.merge_image_findings(active_assessment_id, analysis)

    # Transition to confirmation and confirm
    confirmed = await orchestrator.confirm_symptoms(active_assessment_id)

    assert len(confirmed) == 1
    assert confirmed[0].name == "hives"
    assert confirmed[0].source == SymptomSource.USER_CONFIRMED
    assert orchestrator.get_state(active_assessment_id).state == AssessmentState.READY
