"""Unit tests for the assessment state machine and guarded transitions.

Responsibilities:
    - Verify full happy path lifecycle from START to COMPLETED.
    - Verify guarded transitions (consent, symptom presence, clarification caps).
    - Verify illegal transitions are blocked with InvalidStateTransitionError.
    - Verify alternative flows: direct confirmation, edits, restarts, and error states.

Owner: Darshil (assessment) · Task: S1-DAR-1 · Requirements: N/A
"""

from uuid import uuid4

import pytest

from app.schemas.enums import AssessmentState
from app.services.assessment import (
    MAX_CLARIFICATION_TURNS,
    AssessmentContext,
    AssessmentStateMachine,
    InvalidStateTransitionError,
    StateGuardViolationError,
)


@pytest.fixture
def sample_consent_id():
    """Return a valid UUID for consent fixture."""
    return uuid4()


@pytest.fixture
def sample_symptom():
    """Return a dictionary representing a structured symptom."""
    return {"name": "fever", "severity": "MODERATE", "duration": "1 day"}


# =============================================================================
# 1. Happy Path Lifecycle Tests
# =============================================================================


def test_full_lifecycle_happy_path(sample_consent_id, sample_symptom):
    """Verify standard happy-path progression through all assessment states.

    START -> SYMPTOM_COLLECTION -> CLARIFYING -> CONFIRMING -> READY ->
    ANALYZING -> COMPLETED.
    """
    context = AssessmentContext(consent_id=sample_consent_id)
    sm = AssessmentStateMachine(AssessmentState.START, context=context)

    # 1. START -> SYMPTOM_COLLECTION
    assert sm.current_state == AssessmentState.START
    assert sm.can_transition_to(AssessmentState.SYMPTOM_COLLECTION)[0] is True
    sm.start_symptom_collection()
    assert sm.current_state == AssessmentState.SYMPTOM_COLLECTION

    # Record extracted symptom
    sm.context.symptoms.append(sample_symptom)

    # 2. SYMPTOM_COLLECTION -> CLARIFYING
    assert sm.can_transition_to(AssessmentState.CLARIFYING)[0] is True
    sm.request_clarification()
    assert sm.current_state == AssessmentState.CLARIFYING
    assert sm.context.clarification_count == 1

    # 3. CLARIFYING -> CONFIRMING
    assert sm.can_transition_to(AssessmentState.CONFIRMING)[0] is True
    sm.proceed_to_confirmation()
    assert sm.current_state == AssessmentState.CONFIRMING

    # 4. CONFIRMING -> READY
    assert sm.context.is_confirmed is False
    sm.confirm_symptoms()
    assert sm.current_state == AssessmentState.READY
    assert sm.context.is_confirmed is True

    # 5. READY -> ANALYZING
    assert sm.can_transition_to(AssessmentState.ANALYZING)[0] is True
    sm.start_analysis()
    assert sm.current_state == AssessmentState.ANALYZING

    # 6. ANALYZING -> COMPLETED
    can_complete, _ = sm.can_transition_to(
        AssessmentState.COMPLETED, context=sm.context
    )
    assert can_complete is False
    sm.complete_analysis()
    assert sm.current_state == AssessmentState.COMPLETED
    assert sm.context.has_analysis_result is True

    # Validate transition history
    history = sm.history
    assert len(history) == 6
    assert history[0][0] == AssessmentState.START
    assert history[-1][1] == AssessmentState.COMPLETED


def test_happy_path_direct_confirmation_without_clarification(
    sample_consent_id, sample_symptom
):
    """Verify flow when symptoms are clear and clarification is not required."""
    context = AssessmentContext(
        consent_id=sample_consent_id,
        symptoms=[sample_symptom],
    )
    sm = AssessmentStateMachine(AssessmentState.START, context=context)

    sm.start_symptom_collection()
    sm.proceed_to_confirmation()
    assert sm.current_state == AssessmentState.CONFIRMING

    sm.confirm_symptoms()
    assert sm.current_state == AssessmentState.READY

    sm.start_analysis()
    sm.complete_analysis()
    assert sm.current_state == AssessmentState.COMPLETED


# =============================================================================
# 2. Alternative & Edge Transition Flows
# =============================================================================


def test_multi_turn_symptom_collection(sample_consent_id, sample_symptom):
    """Verify multiple messages can be exchanged in SYMPTOM_COLLECTION state."""
    context = AssessmentContext(consent_id=sample_consent_id)
    sm = AssessmentStateMachine(AssessmentState.START, context=context)

    sm.start_symptom_collection()
    assert sm.current_state == AssessmentState.SYMPTOM_COLLECTION

    # Self-transition for subsequent user messages
    sm.transition_to(AssessmentState.SYMPTOM_COLLECTION)
    sm.context.symptoms.append(sample_symptom)
    sm.transition_to(AssessmentState.SYMPTOM_COLLECTION)
    assert sm.current_state == AssessmentState.SYMPTOM_COLLECTION


def test_multi_turn_clarification_up_to_limit(sample_consent_id, sample_symptom):
    """Verify clarification questions up to max limit (turn 1, 2, 3)."""
    context = AssessmentContext(
        consent_id=sample_consent_id,
        symptoms=[sample_symptom],
    )
    sm = AssessmentStateMachine(AssessmentState.SYMPTOM_COLLECTION, context=context)

    # Turn 1
    sm.request_clarification()
    assert sm.current_state == AssessmentState.CLARIFYING
    assert sm.context.clarification_count == 1

    # Turn 2
    sm.request_clarification()
    assert sm.current_state == AssessmentState.CLARIFYING
    assert sm.context.clarification_count == 2

    # Turn 3
    sm.request_clarification()
    assert sm.current_state == AssessmentState.CLARIFYING
    assert sm.context.clarification_count == 3


def test_clarification_limit_blocks_fourth_turn(sample_consent_id, sample_symptom):
    """Verify that exceeding MAX_CLARIFICATION_TURNS is blocked by guard."""
    context = AssessmentContext(
        consent_id=sample_consent_id,
        symptoms=[sample_symptom],
        clarification_count=MAX_CLARIFICATION_TURNS,
    )
    sm = AssessmentStateMachine(AssessmentState.CLARIFYING, context=context)

    can_clarify, reason = sm.can_transition_to(AssessmentState.CLARIFYING)
    assert can_clarify is False
    assert "Clarification limit" in (reason or "")

    with pytest.raises(StateGuardViolationError) as exc_info:
        sm.request_clarification()

    assert exc_info.value.guard_name == "guard_under_clarification_limit"
    assert exc_info.value.status_code == 409


def test_edit_symptoms_from_confirming(sample_consent_id, sample_symptom):
    """Verify user editing symptoms from CONFIRMING moves back to SYMPTOM_COLLECTION."""
    context = AssessmentContext(
        consent_id=sample_consent_id,
        symptoms=[sample_symptom],
    )
    sm = AssessmentStateMachine(AssessmentState.CONFIRMING, context=context)

    sm.edit_symptoms()
    assert sm.current_state == AssessmentState.SYMPTOM_COLLECTION


def test_edit_symptoms_within_confirming_state(sample_consent_id, sample_symptom):
    """Verify self-transition in CONFIRMING state when user edits list."""
    context = AssessmentContext(
        consent_id=sample_consent_id,
        symptoms=[sample_symptom],
    )
    sm = AssessmentStateMachine(AssessmentState.CONFIRMING, context=context)

    sm.transition_to(AssessmentState.CONFIRMING)
    assert sm.current_state == AssessmentState.CONFIRMING


def test_edit_from_ready_before_analysis(sample_consent_id, sample_symptom):
    """Verify user can step back from READY to CONFIRMING or SYMPTOM_COLLECTION."""
    context = AssessmentContext(
        consent_id=sample_consent_id,
        symptoms=[sample_symptom],
        is_confirmed=True,
    )
    sm = AssessmentStateMachine(AssessmentState.READY, context=context)

    # Step back to CONFIRMING
    sm.transition_to(AssessmentState.CONFIRMING)
    assert sm.current_state == AssessmentState.CONFIRMING

    # Re-confirm
    sm.confirm_symptoms()
    assert sm.current_state == AssessmentState.READY

    # Step back to SYMPTOM_COLLECTION
    sm.transition_to(AssessmentState.SYMPTOM_COLLECTION)
    assert sm.current_state == AssessmentState.SYMPTOM_COLLECTION


def test_restart_from_completed(sample_consent_id):
    """Verify restarting session after completed assessment resets to START."""
    context = AssessmentContext(
        consent_id=sample_consent_id,
        has_analysis_result=True,
    )
    sm = AssessmentStateMachine(AssessmentState.COMPLETED, context=context)

    sm.restart(AssessmentState.START)
    assert sm.current_state == AssessmentState.START
    assert sm.context.has_analysis_result is False
    assert sm.context.clarification_count == 0


def test_restart_mid_assessment(sample_consent_id, sample_symptom):
    """Verify resetting session mid-assessment via restart() helper."""
    context = AssessmentContext(
        consent_id=sample_consent_id,
        symptoms=[sample_symptom],
        clarification_count=2,
        is_confirmed=True,
    )
    sm = AssessmentStateMachine(AssessmentState.CLARIFYING, context=context)

    sm.restart(AssessmentState.START)
    assert sm.current_state == AssessmentState.START
    assert sm.context.clarification_count == 0
    assert sm.context.is_confirmed is False


def test_error_transitions_and_recovery(sample_consent_id):
    """Verify transitioning to ERROR from various states and recovering to START."""
    sm = AssessmentStateMachine(AssessmentState.START)
    sm.transition_to_error("Failed initialization")
    assert sm.current_state == AssessmentState.ERROR

    # Recover to START
    sm.restart(AssessmentState.START)
    assert sm.current_state == AssessmentState.START

    # Recover from ERROR to SYMPTOM_COLLECTION when consent is present
    sm.context.consent_id = sample_consent_id
    sm.start_symptom_collection()
    sm.transition_to_error("Network timeout")
    assert sm.current_state == AssessmentState.ERROR
    sm.transition_to(AssessmentState.SYMPTOM_COLLECTION)
    assert sm.current_state == AssessmentState.SYMPTOM_COLLECTION


# =============================================================================
# 3. Guard Violation & Safety Failure Tests
# =============================================================================


def test_start_without_consent_fails_guard():
    """Verify transition to SYMPTOM_COLLECTION fails without consent (DR-08)."""
    context = AssessmentContext(consent_id=None)
    sm = AssessmentStateMachine(AssessmentState.START, context=context)

    can_transition, reason = sm.can_transition_to(AssessmentState.SYMPTOM_COLLECTION)
    assert can_transition is False
    assert "consent" in (reason or "").lower()

    with pytest.raises(StateGuardViolationError) as exc_info:
        sm.start_symptom_collection()

    assert exc_info.value.guard_name == "guard_has_consent"
    assert exc_info.value.status_code == 409


def test_confirming_without_symptoms_fails_guard(sample_consent_id):
    """Verify transition to CONFIRMING fails if no symptoms have been recorded."""
    context = AssessmentContext(consent_id=sample_consent_id, symptoms=[])
    sm = AssessmentStateMachine(AssessmentState.SYMPTOM_COLLECTION, context=context)

    can_transition, reason = sm.can_transition_to(AssessmentState.CONFIRMING)
    assert can_transition is False
    assert "At least one symptom" in (reason or "")

    with pytest.raises(StateGuardViolationError) as exc_info:
        sm.proceed_to_confirmation()

    assert exc_info.value.guard_name == "guard_has_symptoms"


def test_ready_without_confirmation_fails_guard(sample_consent_id, sample_symptom):
    """Verify transition to READY fails if user has not explicitly confirmed."""
    context = AssessmentContext(
        consent_id=sample_consent_id,
        symptoms=[sample_symptom],
        is_confirmed=False,
    )
    sm = AssessmentStateMachine(AssessmentState.CONFIRMING, context=context)

    can_transition, reason = sm.can_transition_to(AssessmentState.READY)
    assert can_transition is False
    assert "confirmed" in (reason or "").lower()

    with pytest.raises(StateGuardViolationError) as exc_info:
        sm.transition_to(AssessmentState.READY)

    assert exc_info.value.guard_name == "guard_symptoms_confirmed"


def test_complete_without_analysis_result_fails_guard(
    sample_consent_id, sample_symptom
):
    """Verify transition to COMPLETED fails if analysis results are missing."""
    context = AssessmentContext(
        consent_id=sample_consent_id,
        symptoms=[sample_symptom],
        is_confirmed=True,
        has_analysis_result=False,
    )
    sm = AssessmentStateMachine(AssessmentState.ANALYZING, context=context)

    with pytest.raises(StateGuardViolationError) as exc_info:
        sm.transition_to(AssessmentState.COMPLETED)

    assert exc_info.value.guard_name == "guard_analysis_completed"


# =============================================================================
# 4. Disallowed / Illegal Transitions (409 Conflict)
# =============================================================================


@pytest.mark.parametrize(
    "from_state,to_state",
    [
        (AssessmentState.START, AssessmentState.READY),
        (AssessmentState.START, AssessmentState.ANALYZING),
        (AssessmentState.START, AssessmentState.COMPLETED),
        (AssessmentState.SYMPTOM_COLLECTION, AssessmentState.READY),
        (AssessmentState.SYMPTOM_COLLECTION, AssessmentState.ANALYZING),
        (AssessmentState.SYMPTOM_COLLECTION, AssessmentState.COMPLETED),
        (AssessmentState.CLARIFYING, AssessmentState.READY),
        (AssessmentState.CLARIFYING, AssessmentState.ANALYZING),
        (AssessmentState.CLARIFYING, AssessmentState.COMPLETED),
        (AssessmentState.CONFIRMING, AssessmentState.ANALYZING),
        (AssessmentState.CONFIRMING, AssessmentState.COMPLETED),
        (AssessmentState.ANALYZING, AssessmentState.START),
        (AssessmentState.ANALYZING, AssessmentState.SYMPTOM_COLLECTION),
        (AssessmentState.ANALYZING, AssessmentState.CONFIRMING),
        (AssessmentState.COMPLETED, AssessmentState.ANALYZING),
        (AssessmentState.COMPLETED, AssessmentState.CLARIFYING),
        (AssessmentState.COMPLETED, AssessmentState.CONFIRMING),
    ],
)
def test_illegal_state_transitions_raise_409(from_state, to_state, sample_consent_id):
    """Verify illegal transitions are rejected with InvalidStateTransitionError."""
    context = AssessmentContext(consent_id=sample_consent_id)
    sm = AssessmentStateMachine(from_state, context=context)

    assert sm.can_transition_to(to_state)[0] is False

    with pytest.raises(InvalidStateTransitionError) as exc_info:
        sm.transition_to(to_state)

    err = exc_info.value
    assert err.status_code == 409
    assert err.code == "INVALID_STATE_TRANSITION"
    assert err.current_state == from_state
    assert err.target_state == to_state
    assert err.details["currentState"] == from_state.value
    assert err.details["targetState"] == to_state.value


def test_get_allowed_transitions():
    """Verify get_allowed_transitions returns the configured targets."""
    sm = AssessmentStateMachine(AssessmentState.START)
    targets = sm.get_allowed_transitions()
    assert AssessmentState.SYMPTOM_COLLECTION in targets
    assert AssessmentState.ERROR in targets
    assert AssessmentState.COMPLETED not in targets
