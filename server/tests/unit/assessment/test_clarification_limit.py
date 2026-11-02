"""Unit tests for clarification loop capping and low-confidence flagging.

Responsibilities:
    - Test single-turn clarification progression within budget.
    - Test multi-turn clarification progression up to 3 turns.
    - Test clarification turn cap enforcement at 3 turns.
    - Test forced transition to CONFIRMING with is_low_confidence=True when capped.
    - Test early resolution moves to CONFIRMING with is_low_confidence=False.
    - Test state machine guard rejects manual transition beyond turn limit.
    - Test get_state API exposes clarification metrics and low-confidence flag.
    - Test end-to-end result generation safely preserves low-confidence flag.

Owner: Darshil (assessment orchestration)
Task: S1-DAR-3
Requirements: FR-04, FR-19, FR-20
"""

from uuid import uuid4

import pytest

from app.schemas.enums import AssessmentState, MessageRole, MessageType
from app.services.ai.mock_provider import MockAiProvider
from app.services.assessment import (
    AssessmentContext,
    AssessmentOrchestrator,
    AssessmentStateMachine,
    StateGuardViolationError,
)
from app.services.assessment.exceptions import AssessmentServiceError


@pytest.fixture
def orchestrator() -> AssessmentOrchestrator:
    """Fixture providing an AssessmentOrchestrator backed by MockAiProvider."""
    return AssessmentOrchestrator(ai_gateway=MockAiProvider())


@pytest.fixture
def active_assessment_id(orchestrator: AssessmentOrchestrator):
    """Fixture initializing a consent-backed assessment session."""
    assessment = orchestrator.create_assessment(consent_id=uuid4())
    return assessment.id


# =============================================================================
# 1. Turn 1: Initial Ambiguous Message Enters Clarification Loop
# =============================================================================


@pytest.mark.anyio
async def test_clarification_loop_first_turn_increments_count(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id,
) -> None:
    """Verify first ambiguous message increments count to 1 and asks question.

    Per FR-04, when a symptom lacks required attributes (e.g., duration), the
    orchestrator initiates a clarification turn within the 3-turn budget.
    """
    result = await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="I have a sore throat.",
    )

    assert result.next_state == AssessmentState.CLARIFYING
    assert result.result_type == "CLARIFICATION"
    assert result.is_low_confidence is False
    assert result.assistant_message is not None
    assert result.assistant_message.message_type == MessageType.CLARIFICATION
    assert result.assistant_message.role == MessageRole.ASSISTANT

    state = orchestrator.get_state(active_assessment_id)
    assert state.clarification_count == 1
    assert state.max_clarifications == 3
    assert state.is_low_confidence is False


# =============================================================================
# 2. Turn 2: Second Clarification Turn Remains Within Budget
# =============================================================================


@pytest.mark.anyio
async def test_clarification_loop_second_turn_within_budget(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id,
) -> None:
    """Verify second ambiguous turn increments count to 2 without low confidence."""
    # Turn 1
    await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="I have a cough.",
    )

    # Turn 2: Ambiguous response lacking duration
    result = await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="It is dry and slightly painful.",
    )

    assert result.next_state == AssessmentState.CLARIFYING
    assert result.result_type == "CLARIFICATION"
    assert result.is_low_confidence is False

    state = orchestrator.get_state(active_assessment_id)
    assert state.clarification_count == 2
    assert state.is_low_confidence is False


# =============================================================================
# 3. Turn 3: Third Clarification Turn Reaches Maximum Budget Limit
# =============================================================================


@pytest.mark.anyio
async def test_clarification_loop_third_turn_reaches_budget_limit(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id,
) -> None:
    """Verify third clarification turn increments count to 3 at boundary."""
    # Turn 1
    await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="I have a cough.",
    )
    # Turn 2
    await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="It is dry.",
    )
    # Turn 3: Still ambiguous
    result = await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="I am really not sure.",
    )

    assert result.next_state == AssessmentState.CLARIFYING
    assert result.result_type == "CLARIFICATION"
    assert result.is_low_confidence is False

    state = orchestrator.get_state(active_assessment_id)
    assert state.clarification_count == 3
    assert state.is_low_confidence is False


# =============================================================================
# 4. Turn 4: Cap Reached (3 Turns) Forces Confirmation and Flags Low Confidence
# =============================================================================


@pytest.mark.anyio
async def test_clarification_loop_cap_forces_confirmation_and_low_confidence(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id,
) -> None:
    """Verify exceeding 3 clarification turns forces confirmation and low confidence.

    Requirements: FR-04, FR-19, FR-20.
    When clarification loop reaches 3 turns, further questions are prohibited.
    The orchestrator must transition to CONFIRMING and set is_low_confidence=True.
    """
    # Turn 1
    await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="I have a cough.",
    )
    # Turn 2
    await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="It is dry.",
    )
    # Turn 3 (reaches cap of 3)
    await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="I don't know.",
    )

    # Turn 4: Budget exhausted, ambiguity remains
    result = await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="Still coughing today.",
    )

    # Must force CONFIRMING, never CLARIFYING
    assert result.next_state == AssessmentState.CONFIRMING
    assert result.result_type == "CONFIRMATION"
    assert result.is_low_confidence is True
    assert result.assistant_message is not None
    assert result.assistant_message.message_type == MessageType.CONFIRMATION

    # State machine and session context verification
    state = orchestrator.get_state(active_assessment_id)
    assert state.state == AssessmentState.CONFIRMING
    assert state.clarification_count == 3
    assert state.is_low_confidence is True


# =============================================================================
# 5. Early Resolution: Resolving Clarification Does Not Flag Low Confidence
# =============================================================================


@pytest.mark.anyio
async def test_clarification_resolved_early_does_not_flag_low_confidence(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id,
) -> None:
    """Verify resolving clarification before the cap moves to CONFIRMING normally.

    When user provides necessary details (e.g., duration) on turn 2, the
    assessment moves to CONFIRMING with is_low_confidence=False.
    """
    # Turn 1: Missing duration
    turn1 = await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="I have a headache.",
    )
    assert turn1.next_state == AssessmentState.CLARIFYING
    assert turn1.is_low_confidence is False

    # Turn 2: Clear duration and severity provided
    turn2 = await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="The headache started yesterday and it is mild.",
    )

    assert turn2.next_state == AssessmentState.CONFIRMING
    assert turn2.result_type == "CONFIRMATION"
    assert turn2.is_low_confidence is False

    state = orchestrator.get_state(active_assessment_id)
    assert state.state == AssessmentState.CONFIRMING
    assert state.clarification_count == 1
    assert state.is_low_confidence is False


# =============================================================================
# 6. State Machine Guard: Rejects Transition Beyond Limit with 409 Conflict
# =============================================================================


def test_state_machine_guard_blocks_manual_transition_beyond_limit() -> None:
    """Verify guard_under_clarification_limit blocks transitions when count >= 3."""
    context = AssessmentContext(
        consent_id=uuid4(),
        symptoms=[{"name": "fever"}],
        clarification_count=3,
        max_clarifications=3,
    )
    sm = AssessmentStateMachine(
        initial_state=AssessmentState.CLARIFYING,
        context=context,
    )

    # 1. Guard check returns (False, reason)
    can_transition, reason = sm.can_transition_to(AssessmentState.CLARIFYING)
    assert can_transition is False
    assert reason is not None
    assert "Clarification limit of 3 turns reached" in reason

    # 2. Transition attempt raises StateGuardViolationError (HTTP 409)
    with pytest.raises(StateGuardViolationError) as exc_info:
        sm.transition_to(AssessmentState.CLARIFYING)
    assert exc_info.value.status_code == 409

    # 3. Transition to CONFIRMING remains valid
    can_confirm, _ = sm.can_transition_to(AssessmentState.CONFIRMING)
    assert can_confirm is True
    sm.transition_to(AssessmentState.CONFIRMING)
    assert sm.current_state == AssessmentState.CONFIRMING


# =============================================================================
# 7. Get State API: Exposes Clarification Metrics and Low-Confidence Flag
# =============================================================================


@pytest.mark.anyio
async def test_get_state_exposes_clarification_metrics_and_low_confidence_flag(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id,
) -> None:
    """Verify get_state returns accurate clarification metadata across lifecycle."""
    # Initial state
    state0 = orchestrator.get_state(active_assessment_id)
    assert state0.state == AssessmentState.START
    assert state0.clarification_count == 0
    assert state0.max_clarifications == 3
    assert state0.is_low_confidence is False

    # Simulate reaching clarification limit
    session = orchestrator._sessions[active_assessment_id]
    session.state_machine.context.clarification_count = 3
    session.state_machine.start_symptom_collection()

    await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="My cough still bothers me.",
    )

    state_capped = orchestrator.get_state(active_assessment_id)
    assert state_capped.state == AssessmentState.CONFIRMING
    assert state_capped.clarification_count == 3
    assert state_capped.max_clarifications == 3
    assert state_capped.is_low_confidence is True

    # Unknown assessment raises 404
    with pytest.raises(AssessmentServiceError) as exc_info:
        orchestrator.get_state(uuid4())
    assert exc_info.value.status_code == 404


# =============================================================================
# 8. End-to-End Safety: Low-Confidence Assessment Completes Analysis Safely
# =============================================================================


@pytest.mark.anyio
async def test_result_generation_handles_low_confidence_session_safely(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id,
) -> None:
    """Verify low-confidence assessment safely completes analysis lifecycle.

    Medical safety: sessions flagged as low-confidence proceed through
    confirmation, analysis, and completion deterministically without losing
    the is_low_confidence flag or violating safety invariants.
    """
    # 1. Reach clarification cap to flag low confidence
    session = orchestrator._sessions[active_assessment_id]
    session.state_machine.context.clarification_count = 3
    session.state_machine.start_symptom_collection()

    turn = await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="I have had a cough for some time.",
    )
    assert turn.is_low_confidence is True
    assert turn.next_state == AssessmentState.CONFIRMING

    # 2. Confirm symptoms (CONFIRMING -> READY)
    await orchestrator.confirm_symptoms(active_assessment_id)
    state_ready = orchestrator.get_state(active_assessment_id)
    assert state_ready.state == AssessmentState.READY
    assert state_ready.is_low_confidence is True

    # 3. Generate result (READY -> ANALYZING -> COMPLETED)
    result = await orchestrator.generate_result(active_assessment_id)
    assert result.assessment_id == active_assessment_id
    assert result.disclaimer is not None

    state_completed = orchestrator.get_state(active_assessment_id)
    assert state_completed.state == AssessmentState.COMPLETED
    assert state_completed.is_low_confidence is True
