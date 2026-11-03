"""Unit tests for real analysis in generate_result() with safety-wording guard.

Responsibilities:
    - Test real clinical analysis pipeline (prediction -> risk engine -> composer).
    - Test URGENT result with 112 referral on red-flag symptoms (chest pain + sweating).
    - Test SELF_CARE result with conditions listed for mild cold symptoms.
    - Test real assert_safe_wording passes for valid clinical results.
    - Test rejecting wording guard raises UnsafeWordingError and transitions to ERROR.
    - Test session never reaches COMPLETED when guard fails.
    - Test dependency injection of result composer and condition model.

Owner: Darshil (assessment) · Task: S2-DAR-5 · Requirements: FR-05, FR-06, FR-07, DR-05
"""

from collections.abc import Collection
from uuid import UUID, uuid4

import pytest

from app.schemas.enums import AssessmentState, RiskLevel, Severity
from app.schemas.result import DEFAULT_DISCLAIMER
from app.schemas.symptom import Symptom, SymptomRead
from app.services.ai.mock_provider import MockAiProvider
from app.services.assessment import (
    AssessmentOrchestrator,
    AssessmentServiceError,
    InvalidStateTransitionError,
)
from app.services.prediction.condition_predictor import BaselineConditionModel
from app.services.prediction.result_composer import ResultComposer
from app.services.prediction.schemas import ConditionPrediction
from app.services.privacy.safety_guard import (
    UnsafeWordingError,
    assert_safe_wording,
)


@pytest.fixture
def orchestrator() -> AssessmentOrchestrator:
    """Fixture providing an AssessmentOrchestrator with real analysis pipeline."""
    return AssessmentOrchestrator(ai_gateway=MockAiProvider())


async def _create_ready_session(
    orchestrator: AssessmentOrchestrator,
    symptoms: list[Symptom],
) -> UUID:
    """Helper creating an assessment session and advancing it to READY state."""
    assessment = orchestrator.create_assessment(consent_id=uuid4())
    aid = assessment.id
    session = orchestrator._sessions[aid]
    session.symptoms = [SymptomRead.model_validate(s.model_dump()) for s in symptoms]
    session.state_machine.context.symptoms = [s.model_dump() for s in symptoms]
    session.state_machine.start_symptom_collection()
    session.state_machine.proceed_to_confirmation()
    await orchestrator.confirm_symptoms(aid, symptoms=symptoms)
    assert session.state_machine.current_state == AssessmentState.READY
    return aid


# =============================================================================
# 1. Happy Path: Red-Flag Symptoms Trigger URGENT and 112 Referral
# =============================================================================


@pytest.mark.anyio
async def test_generate_result_urgent_on_chest_pain_and_sweating(
    orchestrator: AssessmentOrchestrator,
) -> None:
    """Verify red-flag symptom combination produces URGENT tier with 112 referral.

    Per FR-06, FR-15, and DR-02:
    - Red flags (chest_pain + sweating) always trigger URGENT.
    - Referral must be required and emergency number set to 112.
    - State transitions from READY -> ANALYZING -> COMPLETED.
    """
    symptoms = [
        Symptom(name="chest_pain", severity=Severity.MODERATE),
        Symptom(name="sweating", severity=Severity.MODERATE),
    ]
    aid = await _create_ready_session(orchestrator, symptoms)

    result = await orchestrator.generate_result(aid)

    # 1. Verify risk tier and 112 emergency referral
    assert result.assessment_id == aid
    assert result.risk_level == RiskLevel.URGENT
    assert result.referral.required is True
    assert result.referral.emergency_number == "112"
    assert result.referral.specialty is not None

    # 2. Verify candidate conditions are predicted
    assert len(result.conditions) > 0
    condition_names = [c.name for c in result.conditions]
    assert any("heart attack" in name.lower() for name in condition_names)

    # 3. Verify mandatory non-diagnostic disclaimer
    assert result.disclaimer == DEFAULT_DISCLAIMER

    # 4. Verify session state is COMPLETED
    state = orchestrator.get_state(aid)
    assert state.state == AssessmentState.COMPLETED


# =============================================================================
# 2. Happy Path: Mild Cold Symptoms Produce SELF_CARE Tier with Conditions
# =============================================================================


@pytest.mark.anyio
async def test_generate_result_self_care_on_mild_cold(
    orchestrator: AssessmentOrchestrator,
) -> None:
    """Verify mild upper-respiratory symptoms produce SELF_CARE with candidate list.

    Per FR-05, FR-07, and FR-22:
    - Non-emergency symptoms (runny_nose + sneezing) map to low risk (SELF_CARE).
    - Emergency referral is not required.
    - Candidate conditions include Common cold or Allergic rhinitis.
    - State reaches COMPLETED deterministically.
    """
    symptoms = [
        Symptom(name="runny_nose", severity=Severity.MILD),
        Symptom(name="sneezing", severity=Severity.MILD),
    ]
    aid = await _create_ready_session(orchestrator, symptoms)

    result = await orchestrator.generate_result(aid)

    # 1. Verify risk tier and referral
    assert result.assessment_id == aid
    assert result.risk_level == RiskLevel.SELF_CARE
    assert result.referral.required is False
    assert result.referral.emergency_number is None

    # 2. Verify candidate conditions
    assert len(result.conditions) > 0
    condition_names = [c.name for c in result.conditions]
    assert any(
        "cold" in name.lower() or "rhinitis" in name.lower() for name in condition_names
    )

    # 3. Verify guidance and disclaimer
    assert len(result.guidance) > 0
    assert result.disclaimer == DEFAULT_DISCLAIMER

    # 4. Verify state progression
    state = orchestrator.get_state(aid)
    assert state.state == AssessmentState.COMPLETED


# =============================================================================
# 3. Safety Guard Validation: Real assert_safe_wording Passes for Normal Results
# =============================================================================


@pytest.mark.anyio
async def test_generate_result_real_assert_safe_wording_passes(
    orchestrator: AssessmentOrchestrator,
) -> None:
    """Verify real assert_safe_wording check passes on generated results.

    Per DR-05 and S1-HAR-3:
    Every sentence in guidance, limitations, and referral reason is verified
    against assert_safe_wording and must not raise UnsafeWordingError.
    """
    symptoms = [
        Symptom(name="cough", severity=Severity.MILD),
        Symptom(name="fatigue", severity=Severity.MILD),
    ]
    aid = await _create_ready_session(orchestrator, symptoms)

    result = await orchestrator.generate_result(aid)

    assert result.risk_level in (RiskLevel.SELF_CARE, RiskLevel.CONSULT_DOCTOR)
    # Manually re-check each generated text piece with real assert_safe_wording
    for sentence in (
        *result.guidance,
        *result.limitations,
        result.referral.reason or "",
    ):
        if sentence:
            assert_safe_wording(sentence)

    state = orchestrator.get_state(aid)
    assert state.state == AssessmentState.COMPLETED


# =============================================================================
# 4. Safety Guard Failure: Rejecting Guard Transitions to ERROR and Re-Raises
# =============================================================================


@pytest.mark.anyio
async def test_generate_result_rejecting_guard_transitions_to_error() -> None:
    """Verify a rejecting wording guard raises UnsafeWordingError and moves to ERROR.

    Requirements: DR-05, acceptance criteria:
    - Inject a composer with a guard that raises UnsafeWordingError.
    - orchestrator.generate_result() must re-raise UnsafeWordingError (500).
    - Session state must transition to ERROR, never reaching COMPLETED.
    - No result object is returned.
    """

    def rejecting_guard(text: str) -> None:
        """Reject all text simulating a safety check violation."""
        raise UnsafeWordingError()

    strict_composer = ResultComposer(wording_guard=rejecting_guard)
    strict_orchestrator = AssessmentOrchestrator(
        ai_gateway=MockAiProvider(),
        result_composer=strict_composer,
    )

    aid = await _create_ready_session(
        strict_orchestrator,
        symptoms=[Symptom(name="headache", severity=Severity.MILD)],
    )

    # Calling generate_result must raise UnsafeWordingError
    with pytest.raises(UnsafeWordingError) as exc_info:
        await strict_orchestrator.generate_result(aid)

    assert exc_info.value.status_code == 500
    assert exc_info.value.code == "UNSAFE_WORDING"

    # State machine must be in ERROR, NOT COMPLETED
    state = strict_orchestrator.get_state(aid)
    assert state.state == AssessmentState.ERROR

    session = strict_orchestrator._sessions[aid]
    assert session.state_machine.current_state == AssessmentState.ERROR
    assert session.state_machine.context.has_analysis_result is False


# =============================================================================
# 5. Dependency Injection: Custom ConditionModel Protocol Implementation
# =============================================================================


@pytest.mark.anyio
async def test_generate_result_custom_condition_model_injection() -> None:
    """Verify AssessmentOrchestrator accepts an injected ConditionModel protocol.

    Demonstrates architectural extensibility (e.g. S2-NIS-3 ONNX model injection)
    via constructor dependency injection.
    """
    called_model = False

    class CustomModel:
        def predict(self, symptom_ids: Collection[str]) -> list[ConditionPrediction]:
            nonlocal called_model
            called_model = True
            return BaselineConditionModel().predict(symptom_ids)

    custom_orchestrator = AssessmentOrchestrator(
        ai_gateway=MockAiProvider(),
        condition_model=CustomModel(),
    )

    aid = await _create_ready_session(
        custom_orchestrator,
        symptoms=[Symptom(name="fever", severity=Severity.MODERATE)],
    )

    result = await custom_orchestrator.generate_result(aid)
    assert called_model is True
    assert result.risk_level is not None
    state = custom_orchestrator.get_state(aid)
    assert state.state == AssessmentState.COMPLETED


# =============================================================================
# 6. Edge Cases & Guard Violations: Missing Assessment and Illegal Transitions
# =============================================================================


@pytest.mark.anyio
async def test_generate_result_raises_404_for_unknown_assessment(
    orchestrator: AssessmentOrchestrator,
) -> None:
    """Verify querying an unrecorded assessment ID raises 404."""
    unknown_id = uuid4()
    with pytest.raises(AssessmentServiceError) as exc_info:
        await orchestrator.generate_result(unknown_id)
    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "ASSESSMENT_NOT_FOUND"


@pytest.mark.anyio
async def test_generate_result_rejects_non_ready_state(
    orchestrator: AssessmentOrchestrator,
) -> None:
    """Verify calling generate_result before reaching READY raises 409 Conflict.

    Guards require START -> SYMPTOM_COLLECTION -> CONFIRMING -> READY before
    analysis can begin.
    """
    assessment = orchestrator.create_assessment(consent_id=uuid4())
    aid = assessment.id

    # Assessment is in START state
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        await orchestrator.generate_result(aid)
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "INVALID_STATE_TRANSITION"


@pytest.mark.anyio
async def test_generate_result_with_custom_self_care_guidance(
    orchestrator: AssessmentOrchestrator,
) -> None:
    """Verify optional self-care guidance parameter is forwarded to composer."""
    symptoms = [
        Symptom(name="runny_nose", severity=Severity.MILD),
        Symptom(name="sneezing", severity=Severity.MILD),
    ]
    aid = await _create_ready_session(orchestrator, symptoms)

    custom_advice = ("Ensure adequate hydration with warm fluids.",)
    result = await orchestrator.generate_result(aid, self_care_guidance=custom_advice)

    assert result.risk_level == RiskLevel.SELF_CARE
    assert custom_advice[0] in result.guidance
