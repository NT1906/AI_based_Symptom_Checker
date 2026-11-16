"""Comprehensive unit tests for assessment state machine transitions and guards.

Responsibilities:
    - Test every valid state transition in the lifecycle graph (23 transitions).
    - Test every invalid transition across all state pairs (41 transitions).
    - Test every guard function in isolation (pure-function coverage).
    - Test guard violation handling and error attributes.
    - Test is_low_confidence flag lifecycle and preservation.
    - Test transition history immutability and record integrity.
    - Test AssessmentContext defaults, attributes, and validation.

Owner: Mohit (testing) · Task: S1-MOH-1 · Requirements: N/A
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.schemas.enums import AssessmentState
from app.services.assessment import (
    MAX_CLARIFICATION_TURNS,
    AssessmentContext,
    AssessmentStateMachine,
    InvalidStateTransitionError,
    StateGuardViolationError,
    guard_analysis_completed,
    guard_has_consent,
    guard_has_symptoms,
    guard_symptoms_confirmed,
    guard_under_clarification_limit,
)
from app.services.assessment.state_machine import TRANSITIONS


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_consent_id() -> UUID:
    """Return a deterministic fake UUID for testing consent validation."""
    return uuid4()


@pytest.fixture
def sample_symptom() -> dict[str, Any]:
    """Return a minimal structured symptom dictionary."""
    return {"name": "headache", "severity": "mild", "duration": "1 day"}


@pytest.fixture
def fully_valid_context(
    sample_consent_id: UUID, sample_symptom: dict[str, Any]
) -> AssessmentContext:
    """Return an AssessmentContext preconfigured to satisfy all transition guards.

    Args:
        sample_consent_id: Valid UUID fixture for consent.
        sample_symptom: Structured symptom dictionary fixture.

    Returns:
        AssessmentContext: Context with consent, symptoms, confirmation, and result.
    """
    return AssessmentContext(
        consent_id=sample_consent_id,
        symptoms=[sample_symptom],
        clarification_count=0,
        is_confirmed=True,
        has_analysis_result=True,
        is_low_confidence=False,
    )


# ---------------------------------------------------------------------------
# Helper: Extract all valid and invalid state pairs from TRANSITIONS
# ---------------------------------------------------------------------------


def _get_transition_pairs() -> tuple[
    list[tuple[AssessmentState, AssessmentState]],
    list[tuple[AssessmentState, AssessmentState]],
]:
    """Calculate the complete partition of valid and invalid state transitions.

    Returns:
        tuple containing (valid_pairs, invalid_pairs) covering all 64 combinations.
    """
    all_states = list(AssessmentState)
    valid: list[tuple[AssessmentState, AssessmentState]] = []
    invalid: list[tuple[AssessmentState, AssessmentState]] = []

    for source in all_states:
        allowed = {rule.target_state for rule in TRANSITIONS.get(source, [])}
        for target in all_states:
            if target in allowed:
                valid.append((source, target))
            else:
                invalid.append((source, target))

    return valid, invalid


VALID_TRANSITIONS, INVALID_TRANSITIONS = _get_transition_pairs()


# ---------------------------------------------------------------------------
# 1. Exhaustive Valid Transitions (23 transitions)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("from_state,to_state", VALID_TRANSITIONS)
def test_all_valid_transitions_succeed_with_satisfied_guards(
    from_state: AssessmentState,
    to_state: AssessmentState,
    fully_valid_context: AssessmentContext,
) -> None:
    """Every allowed transition defined in TRANSITIONS succeeds when guards pass.

    Args:
        from_state: The initial source state.
        to_state: The target state configured as valid in the graph.
        fully_valid_context: Fixture satisfying all guards.
    """
    sm = AssessmentStateMachine(from_state, context=fully_valid_context)

    # can_transition_to must return True
    can_transition, reason = sm.can_transition_to(to_state)
    assert can_transition is True, (
        f"Expected can_transition_to({to_state}) from {from_state} to be True, "
        f"got False with reason: {reason}"
    )
    assert reason is None

    # transition_to must succeed and update current state
    result_state = sm.transition_to(to_state)
    assert result_state == to_state
    assert sm.current_state == to_state

    # history must record this transition
    assert len(sm.history) == 1
    assert sm.history[0][0] == from_state
    assert sm.history[0][1] == to_state
    assert isinstance(sm.history[0][2], datetime)


# ---------------------------------------------------------------------------
# 2. Exhaustive Invalid Transitions (41 transitions)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("from_state,to_state", INVALID_TRANSITIONS)
def test_all_invalid_transitions_are_blocked(
    from_state: AssessmentState,
    to_state: AssessmentState,
    fully_valid_context: AssessmentContext,
) -> None:
    """Any state transition not declared in the transition graph is strictly blocked.

    Args:
        from_state: The source state.
        to_state: An invalid destination state not in the graph.
        fully_valid_context: Satisfied context fixture.
    """
    sm = AssessmentStateMachine(from_state, context=fully_valid_context)

    # can_transition_to must return False
    can_transition, reason = sm.can_transition_to(to_state)
    assert can_transition is False, (
        f"Expected can_transition_to({to_state}) from {from_state} to be False"
    )
    assert reason is not None
    assert "not permitted" in reason.lower()

    # transition_to must raise InvalidStateTransitionError
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        sm.transition_to(to_state)

    err = exc_info.value
    assert err.current_state == from_state
    assert err.target_state == to_state
    assert err.code == "INVALID_STATE_TRANSITION"
    assert err.status_code == 409


# ---------------------------------------------------------------------------
# 3. Guard Functions in Isolation (Unit Pure Functions)
# ---------------------------------------------------------------------------


def test_guard_has_consent_passes(sample_consent_id: UUID) -> None:
    """guard_has_consent returns True when consent_id is present."""
    ctx = AssessmentContext(consent_id=sample_consent_id)
    passed, reason = guard_has_consent(ctx)
    assert passed is True
    assert reason is None


def test_guard_has_consent_fails_when_none() -> None:
    """guard_has_consent returns False when consent_id is None."""
    ctx = AssessmentContext(consent_id=None)
    passed, reason = guard_has_consent(ctx)
    assert passed is False
    assert reason is not None
    assert "consent" in reason.lower()


def test_guard_has_symptoms_passes(sample_symptom: dict[str, Any]) -> None:
    """guard_has_symptoms returns True when symptoms list has at least one item."""
    ctx = AssessmentContext(symptoms=[sample_symptom])
    passed, reason = guard_has_symptoms(ctx)
    assert passed is True
    assert reason is None


def test_guard_has_symptoms_fails_when_empty() -> None:
    """guard_has_symptoms returns False when symptoms list is empty."""
    ctx = AssessmentContext(symptoms=[])
    passed, reason = guard_has_symptoms(ctx)
    assert passed is False
    assert reason is not None
    assert "symptom" in reason.lower()


def test_guard_under_clarification_limit_passes_below_limit(
    sample_consent_id: UUID,
) -> None:
    """guard_under_clarification_limit passes when turn count is strictly below max."""
    ctx = AssessmentContext(
        consent_id=sample_consent_id,
        clarification_count=MAX_CLARIFICATION_TURNS - 1,
    )
    passed, reason = guard_under_clarification_limit(ctx)
    assert passed is True
    assert reason is None


def test_guard_under_clarification_limit_fails_at_limit(
    sample_consent_id: UUID,
) -> None:
    """guard_under_clarification_limit fails when turn count reaches the cap."""
    ctx = AssessmentContext(
        consent_id=sample_consent_id,
        clarification_count=MAX_CLARIFICATION_TURNS,
    )
    passed, reason = guard_under_clarification_limit(ctx)
    assert passed is False
    assert reason is not None
    assert "Clarification limit" in reason


def test_guard_under_clarification_limit_fails_above_limit(
    sample_consent_id: UUID,
) -> None:
    """guard_under_clarification_limit fails when turn count exceeds the cap."""
    ctx = AssessmentContext(
        consent_id=sample_consent_id,
        clarification_count=MAX_CLARIFICATION_TURNS + 2,
    )
    passed, reason = guard_under_clarification_limit(ctx)
    assert passed is False
    assert reason is not None


def test_guard_symptoms_confirmed_passes(
    sample_consent_id: UUID, sample_symptom: dict[str, Any]
) -> None:
    """guard_symptoms_confirmed passes when confirmed and symptoms list is non-empty."""
    ctx = AssessmentContext(
        consent_id=sample_consent_id,
        is_confirmed=True,
        symptoms=[sample_symptom],
    )
    passed, reason = guard_symptoms_confirmed(ctx)
    assert passed is True
    assert reason is None


def test_guard_symptoms_confirmed_fails_when_unconfirmed(
    sample_consent_id: UUID, sample_symptom: dict[str, Any]
) -> None:
    """guard_symptoms_confirmed fails when is_confirmed is False."""
    ctx = AssessmentContext(
        consent_id=sample_consent_id,
        is_confirmed=False,
        symptoms=[sample_symptom],
    )
    passed, reason = guard_symptoms_confirmed(ctx)
    assert passed is False
    assert reason is not None
    assert "confirmed" in reason.lower()


def test_guard_symptoms_confirmed_fails_when_empty_symptoms(
    sample_consent_id: UUID,
) -> None:
    """guard_symptoms_confirmed fails when confirmed but symptoms list is empty."""
    ctx = AssessmentContext(
        consent_id=sample_consent_id,
        is_confirmed=True,
        symptoms=[],
    )
    passed, reason = guard_symptoms_confirmed(ctx)
    assert passed is False
    assert reason is not None
    assert "empty" in reason.lower()


def test_guard_analysis_completed_passes(
    sample_consent_id: UUID, sample_symptom: dict[str, Any]
) -> None:
    """guard_analysis_completed passes when has_analysis_result is True."""
    ctx = AssessmentContext(
        consent_id=sample_consent_id,
        has_analysis_result=True,
        symptoms=[sample_symptom],
    )
    passed, reason = guard_analysis_completed(ctx)
    assert passed is True
    assert reason is None


def test_guard_analysis_completed_fails_when_no_result(
    sample_consent_id: UUID,
) -> None:
    """guard_analysis_completed fails when has_analysis_result is False."""
    ctx = AssessmentContext(
        consent_id=sample_consent_id,
        has_analysis_result=False,
    )
    passed, reason = guard_analysis_completed(ctx)
    assert passed is False
    assert reason is not None
    assert "result" in reason.lower()


# ---------------------------------------------------------------------------
# 4. Guard Violations Trigger StateGuardViolationError
# ---------------------------------------------------------------------------


def test_guard_violation_raises_typed_error_with_status_409() -> None:
    """Attempting START -> SYMPTOM_COLLECTION without consent raises 409 error."""
    ctx = AssessmentContext(consent_id=None)
    sm = AssessmentStateMachine(AssessmentState.START, context=ctx)

    with pytest.raises(StateGuardViolationError) as exc_info:
        sm.start_symptom_collection()

    err = exc_info.value
    assert err.status_code == 409
    assert err.guard_name == "guard_has_consent"
    assert err.current_state == AssessmentState.START
    assert err.target_state == AssessmentState.SYMPTOM_COLLECTION


def test_confirming_to_ready_without_confirmation_raises_guard_violation(
    sample_consent_id: UUID, sample_symptom: dict[str, Any]
) -> None:
    """CONFIRMING -> READY without user confirmation raises StateGuardViolationError."""
    ctx = AssessmentContext(
        consent_id=sample_consent_id,
        symptoms=[sample_symptom],
        is_confirmed=False,
    )
    sm = AssessmentStateMachine(AssessmentState.CONFIRMING, context=ctx)

    with pytest.raises(StateGuardViolationError) as exc_info:
        sm.transition_to(AssessmentState.READY)

    assert exc_info.value.guard_name == "guard_symptoms_confirmed"


def test_analyzing_to_completed_without_results_raises_guard_violation(
    sample_consent_id: UUID, sample_symptom: dict[str, Any]
) -> None:
    """ANALYZING -> COMPLETED without result flag raises StateGuardViolationError."""
    ctx = AssessmentContext(
        consent_id=sample_consent_id,
        symptoms=[sample_symptom],
        has_analysis_result=False,
    )
    sm = AssessmentStateMachine(AssessmentState.ANALYZING, context=ctx)

    with pytest.raises(StateGuardViolationError) as exc_info:
        sm.transition_to(AssessmentState.COMPLETED)

    assert exc_info.value.guard_name == "guard_analysis_completed"


# ---------------------------------------------------------------------------
# 5. AssessmentContext Defaults and Attributes
# ---------------------------------------------------------------------------


def test_assessment_context_defaults() -> None:
    """AssessmentContext initializes with secure and sensible default values."""
    ctx = AssessmentContext()
    assert ctx.assessment_id is None
    assert ctx.consent_id is None
    assert ctx.user_id is None
    assert ctx.guest_session_id is None
    assert ctx.profile is None
    assert ctx.symptoms == []
    assert ctx.clarification_count == 0
    assert ctx.max_clarifications == MAX_CLARIFICATION_TURNS
    assert ctx.is_confirmed is False
    assert ctx.has_analysis_result is False
    assert ctx.is_low_confidence is False


# ---------------------------------------------------------------------------
# 6. is_low_confidence Flag Lifecycle (Preservation & Reset)
# ---------------------------------------------------------------------------


def test_is_low_confidence_flag_reset_on_restart(
    sample_consent_id: UUID, sample_symptom: dict[str, Any]
) -> None:
    """is_low_confidence is reset to False when restarting the assessment."""
    ctx = AssessmentContext(
        consent_id=sample_consent_id,
        symptoms=[sample_symptom],
        is_low_confidence=True,
        has_analysis_result=True,
    )
    sm = AssessmentStateMachine(AssessmentState.COMPLETED, context=ctx)
    assert sm.context.is_low_confidence is True

    sm.restart(AssessmentState.START)
    assert sm.context.is_low_confidence is False
    assert sm.current_state == AssessmentState.START


def test_is_low_confidence_flag_persists_across_analysis_flow(
    sample_consent_id: UUID, sample_symptom: dict[str, Any]
) -> None:
    """is_low_confidence remains True from CONFIRMING through READY to ANALYZING."""
    ctx = AssessmentContext(
        consent_id=sample_consent_id,
        symptoms=[sample_symptom],
        is_confirmed=True,
        is_low_confidence=True,
    )
    sm = AssessmentStateMachine(AssessmentState.READY, context=ctx)
    sm.start_analysis()
    assert sm.context.is_low_confidence is True


# ---------------------------------------------------------------------------
# 7. Transition History Recording & Immutability
# ---------------------------------------------------------------------------


def test_transition_history_immutability(sample_consent_id: UUID) -> None:
    """Mutating the returned history list does not corrupt internal state records."""
    ctx = AssessmentContext(consent_id=sample_consent_id)
    sm = AssessmentStateMachine(AssessmentState.START, context=ctx)
    sm.start_symptom_collection()

    external_history = sm.history
    assert len(external_history) == 1

    external_history.clear()
    assert len(sm.history) == 1


# ---------------------------------------------------------------------------
# 8. get_allowed_transitions for Every State
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", list(AssessmentState))
def test_get_allowed_transitions_returns_correct_targets(
    state: AssessmentState,
) -> None:
    """sm.get_allowed_transitions() matches the target states in TRANSITIONS table.

    Args:
        state: Each of the 8 AssessmentState members.
    """
    sm = AssessmentStateMachine(state)
    expected_targets = {rule.target_state for rule in TRANSITIONS.get(state, [])}
    assert set(sm.get_allowed_transitions()) == expected_targets
