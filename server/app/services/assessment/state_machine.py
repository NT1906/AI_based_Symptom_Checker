"""Assessment state machine: manages lifecycle states and guarded transitions.

Responsibilities:
    - Enforce the canonical assessment state lifecycle:
      START -> SYMPTOM_COLLECTION -> CLARIFYING -> CONFIRMING -> READY ->
      ANALYZING -> COMPLETED.
    - Provide guarded transitions ensuring medical-safety rules hold
      (e.g., blocking analysis if state != READY, capping clarifications).
    - Prevent invalid transitions and raise typed InvalidStateTransitionError.

Owner: Darshil (assessment) · Task: S1-DAR-1 · Requirements: N/A
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.schemas.enums import AssessmentState
from app.services.assessment.exceptions import (
    InvalidStateTransitionError,
    StateGuardViolationError,
)

logger = get_logger(__name__)

MAX_CLARIFICATION_TURNS: int = 3


@dataclass
class AssessmentContext:
    """Runtime context for an active assessment session.

    Attributes:
        assessment_id: Unique assessment session identifier.
        consent_id: Validated consent record identifier.
        user_id: Optional registered user identifier.
        symptoms: List of extracted or confirmed symptoms.
        clarification_count: Number of clarification turns asked so far.
        max_clarifications: Hard limit on clarification questions (default 3).
        is_confirmed: True when user has reviewed and confirmed symptoms.
        has_analysis_result: True when prediction and risk triage finished.
    """

    assessment_id: UUID | None = None
    consent_id: UUID | None = None
    user_id: UUID | None = None
    symptoms: list[Any] = field(default_factory=list)
    clarification_count: int = 0
    max_clarifications: int = MAX_CLARIFICATION_TURNS
    is_confirmed: bool = False
    has_analysis_result: bool = False


GuardCallable = Callable[[AssessmentContext], tuple[bool, str | None]]


def guard_has_consent(context: AssessmentContext) -> tuple[bool, str | None]:
    """Ensure session has validated consent before symptom collection."""
    if context.consent_id is None:
        return False, "Valid user consent is required before symptom collection."
    return True, None


def guard_has_symptoms(context: AssessmentContext) -> tuple[bool, str | None]:
    """Ensure at least one symptom exists before confirmation or ready."""
    if not context.symptoms:
        return False, "At least one symptom must be recorded before proceeding."
    return True, None


def guard_under_clarification_limit(
    context: AssessmentContext,
) -> tuple[bool, str | None]:
    """Ensure clarification turns do not exceed the configured limit."""
    if context.clarification_count >= context.max_clarifications:
        return (
            False,
            f"Clarification limit of {context.max_clarifications} turns reached. "
            "Must proceed to confirmation.",
        )
    return True, None


def guard_symptoms_confirmed(context: AssessmentContext) -> tuple[bool, str | None]:
    """Ensure symptoms have been explicitly confirmed by the user."""
    if not context.is_confirmed:
        return False, "Symptoms must be confirmed by the user before moving to READY."
    if not context.symptoms:
        return False, "Cannot confirm an empty symptom list."
    return True, None


def guard_analysis_completed(context: AssessmentContext) -> tuple[bool, str | None]:
    """Ensure analysis produced valid results before marking completed."""
    if not context.has_analysis_result:
        return False, "Analysis results must be generated before completing session."
    return True, None


@dataclass(frozen=True)
class TransitionRule:
    """Rule defining an allowed target state and its guard conditions.

    Attributes:
        target_state: Destination AssessmentState.
        guards: Sequence of guard functions that must all pass.
        description: Brief description of the transition purpose.
    """

    target_state: AssessmentState
    guards: tuple[GuardCallable, ...] = ()
    description: str = ""


# Transition rules defining the canonical lifecycle graph
TRANSITIONS: dict[AssessmentState, list[TransitionRule]] = {
    AssessmentState.START: [
        TransitionRule(
            target_state=AssessmentState.SYMPTOM_COLLECTION,
            guards=(guard_has_consent,),
            description="Begin symptom collection with verified consent.",
        ),
        TransitionRule(
            target_state=AssessmentState.ERROR,
            description="Initialization failure.",
        ),
    ],
    AssessmentState.SYMPTOM_COLLECTION: [
        TransitionRule(
            target_state=AssessmentState.SYMPTOM_COLLECTION,
            description="Collect additional symptom message from user.",
        ),
        TransitionRule(
            target_state=AssessmentState.CLARIFYING,
            guards=(guard_under_clarification_limit,),
            description="Ask follow-up question for ambiguous symptoms.",
        ),
        TransitionRule(
            target_state=AssessmentState.CONFIRMING,
            guards=(guard_has_symptoms,),
            description="Proceed directly to symptom review when clear.",
        ),
        TransitionRule(
            target_state=AssessmentState.ERROR,
            description="Extraction error.",
        ),
    ],
    AssessmentState.CLARIFYING: [
        TransitionRule(
            target_state=AssessmentState.CLARIFYING,
            guards=(guard_under_clarification_limit,),
            description="Next clarification question within turn budget.",
        ),
        TransitionRule(
            target_state=AssessmentState.SYMPTOM_COLLECTION,
            description="Resume general symptom collection if needed.",
        ),
        TransitionRule(
            target_state=AssessmentState.CONFIRMING,
            guards=(guard_has_symptoms,),
            description="Clarification finished or capped; proceed to confirm.",
        ),
        TransitionRule(
            target_state=AssessmentState.ERROR,
            description="Clarification generation error.",
        ),
    ],
    AssessmentState.CONFIRMING: [
        TransitionRule(
            target_state=AssessmentState.CONFIRMING,
            description="User modifies symptom attributes or list.",
        ),
        TransitionRule(
            target_state=AssessmentState.SYMPTOM_COLLECTION,
            description="User edits symptoms back in conversation.",
        ),
        TransitionRule(
            target_state=AssessmentState.READY,
            guards=(guard_has_symptoms, guard_symptoms_confirmed),
            description="User confirms symptom list, locking state for analysis.",
        ),
        TransitionRule(
            target_state=AssessmentState.ERROR,
            description="Confirmation error.",
        ),
    ],
    AssessmentState.READY: [
        TransitionRule(
            target_state=AssessmentState.ANALYZING,
            guards=(guard_has_symptoms,),
            description="Trigger deterministic risk engine and condition models.",
        ),
        TransitionRule(
            target_state=AssessmentState.CONFIRMING,
            description="User revisits symptom list before analysis.",
        ),
        TransitionRule(
            target_state=AssessmentState.SYMPTOM_COLLECTION,
            description="User returns to chat before analysis.",
        ),
        TransitionRule(
            target_state=AssessmentState.ERROR,
            description="Pre-analysis setup error.",
        ),
    ],
    AssessmentState.ANALYZING: [
        TransitionRule(
            target_state=AssessmentState.COMPLETED,
            guards=(guard_analysis_completed,),
            description="Analysis complete with triage result composed.",
        ),
        TransitionRule(
            target_state=AssessmentState.ERROR,
            description="Model timeout or computation error.",
        ),
    ],
    AssessmentState.COMPLETED: [
        TransitionRule(
            target_state=AssessmentState.START,
            description="Reset assessment session for a new inquiry.",
        ),
    ],
    AssessmentState.ERROR: [
        TransitionRule(
            target_state=AssessmentState.START,
            description="Restart assessment session after error.",
        ),
        TransitionRule(
            target_state=AssessmentState.SYMPTOM_COLLECTION,
            guards=(guard_has_consent,),
            description="Resume symptom collection after transient error.",
        ),
    ],
}


class AssessmentStateMachine:
    """State machine governing assessment lifecycle and guarded transitions.

    Enforces the canonical assessment progression:
    START -> SYMPTOM_COLLECTION -> CLARIFYING -> CONFIRMING -> READY ->
    ANALYZING -> COMPLETED.

    Example:
        >>> sm = AssessmentStateMachine(AssessmentState.START)
        >>> sm.context.consent_id = UUID("11111111-1111-1111-1111-111111111111")
        >>> sm.start_symptom_collection()
        <AssessmentState.SYMPTOM_COLLECTION: 'SYMPTOM_COLLECTION'>
    """

    def __init__(
        self,
        initial_state: AssessmentState = AssessmentState.START,
        context: AssessmentContext | None = None,
    ) -> None:
        """Initialize the assessment state machine.

        Args:
            initial_state: The initial lifecycle state (default: START).
            context: Optional runtime assessment context.
        """
        self._current_state = initial_state
        self._context = context or AssessmentContext()
        self._history: list[tuple[AssessmentState, AssessmentState, datetime]] = []

    @property
    def current_state(self) -> AssessmentState:
        """Return the current lifecycle state."""
        return self._current_state

    @property
    def context(self) -> AssessmentContext:
        """Return the current assessment context."""
        return self._context

    @property
    def history(self) -> list[tuple[AssessmentState, AssessmentState, datetime]]:
        """Return the chronological state transition history."""
        return list(self._history)

    def get_allowed_transitions(self) -> list[AssessmentState]:
        """Return a list of all potential target states from current state.

        Returns:
            List of AssessmentState values defined in the transition table.
        """
        rules = TRANSITIONS.get(self._current_state, [])
        return [rule.target_state for rule in rules]

    def can_transition_to(
        self,
        target_state: AssessmentState,
        context: AssessmentContext | None = None,
    ) -> tuple[bool, str | None]:
        """Check whether a transition to target_state is permitted.

        Evaluates transition existence and any associated guard conditions.

        Args:
            target_state: The prospective destination state.
            context: Context to evaluate guards against, defaults to self.context.

        Returns:
            Tuple of (is_allowed, failure_reason).
        """
        ctx = context or self._context
        rules = TRANSITIONS.get(self._current_state, [])
        matching_rules = [r for r in rules if r.target_state == target_state]

        if not matching_rules:
            return (
                False,
                f"Transition from {self._current_state.value} to "
                f"{target_state.value} is not permitted in the lifecycle graph.",
            )

        # Check guards for the matching rule
        rule = matching_rules[0]
        for guard in rule.guards:
            passed, reason = guard(ctx)
            if not passed:
                return False, reason or f"Guard '{guard.__name__}' failed."

        return True, None

    def transition_to(
        self,
        target_state: AssessmentState,
        context: AssessmentContext | None = None,
    ) -> AssessmentState:
        """Transition the assessment to target_state, enforcing all guards.

        Args:
            target_state: The target AssessmentState.
            context: Optional updated context to evaluate guards against.

        Returns:
            The new AssessmentState after successful transition.

        Raises:
            InvalidStateTransitionError: If the transition is illegal.
            StateGuardViolationError: If a guard condition rejects the transition.
        """
        if context is not None:
            self._context = context

        rules = TRANSITIONS.get(self._current_state, [])
        matching_rules = [r for r in rules if r.target_state == target_state]

        if not matching_rules:
            logger.warning(
                "invalid_state_transition_attempted",
                current_state=self._current_state.value,
                target_state=target_state.value,
            )
            raise InvalidStateTransitionError(
                current_state=self._current_state,
                target_state=target_state,
                reason=(
                    f"Transition from {self._current_state.value} to "
                    f"{target_state.value} is not permitted."
                ),
            )

        rule = matching_rules[0]
        for guard in rule.guards:
            passed, reason = guard(self._context)
            if not passed:
                guard_name = guard.__name__
                reason_msg = reason or f"Guard '{guard_name}' failed."
                logger.warning(
                    "state_guard_violation",
                    current_state=self._current_state.value,
                    target_state=target_state.value,
                    guard=guard_name,
                    reason=reason_msg,
                )
                raise StateGuardViolationError(
                    current_state=self._current_state,
                    target_state=target_state,
                    guard_name=guard_name,
                    reason=reason_msg,
                )

        from_state = self._current_state
        self._current_state = target_state
        self._history.append((from_state, target_state, datetime.now(UTC)))

        logger.info(
            "assessment_state_transition",
            from_state=from_state.value,
            to_state=target_state.value,
            description=rule.description,
        )
        return self._current_state

    # -------------------------------------------------------------------------
    # Convenience lifecycle transition methods
    # -------------------------------------------------------------------------

    def start_symptom_collection(self) -> AssessmentState:
        """Transition from START to SYMPTOM_COLLECTION with validated consent."""
        return self.transition_to(AssessmentState.SYMPTOM_COLLECTION)

    def request_clarification(self) -> AssessmentState:
        """Transition to CLARIFYING and increment the clarification counter."""
        new_state = self.transition_to(AssessmentState.CLARIFYING)
        self._context.clarification_count += 1
        return new_state

    def proceed_to_confirmation(self) -> AssessmentState:
        """Transition to CONFIRMING once sufficient symptoms are gathered."""
        return self.transition_to(AssessmentState.CONFIRMING)

    def edit_symptoms(self) -> AssessmentState:
        """Transition back to SYMPTOM_COLLECTION when user requests editing."""
        return self.transition_to(AssessmentState.SYMPTOM_COLLECTION)

    def confirm_symptoms(self) -> AssessmentState:
        """Mark symptoms confirmed and transition to READY state."""
        self._context.is_confirmed = True
        return self.transition_to(AssessmentState.READY)

    def start_analysis(self) -> AssessmentState:
        """Transition from READY to ANALYZING to begin triage evaluation."""
        return self.transition_to(AssessmentState.ANALYZING)

    def complete_analysis(self) -> AssessmentState:
        """Mark analysis complete and transition to COMPLETED."""
        self._context.has_analysis_result = True
        return self.transition_to(AssessmentState.COMPLETED)

    def transition_to_error(self, reason: str | None = None) -> AssessmentState:
        """Transition session to ERROR on unrecoverable failure.

        Args:
            reason: Optional description of the failure.

        Returns:
            AssessmentState.ERROR.
        """
        return self.transition_to(AssessmentState.ERROR)

    def restart(
        self,
        to_state: AssessmentState = AssessmentState.START,
    ) -> AssessmentState:
        """Reset the assessment session to START or SYMPTOM_COLLECTION.

        Args:
            to_state: The state to reset to (default: START).

        Returns:
            The resulting state after restart.
        """
        # If already at COMPLETED or ERROR, normal transition works
        if to_state in self.get_allowed_transitions():
            self._context.clarification_count = 0
            self._context.is_confirmed = False
            self._context.has_analysis_result = False
            return self.transition_to(to_state)

        # Force reset across other states (e.g. user clicks "Start Over" mid-flow)
        from_state = self._current_state
        self._current_state = to_state
        self._context.clarification_count = 0
        self._context.is_confirmed = False
        self._context.has_analysis_result = False
        self._history.append((from_state, to_state, datetime.now(UTC)))

        logger.info(
            "assessment_session_reset",
            from_state=from_state.value,
            to_state=to_state.value,
        )
        return self._current_state


__all__ = [
    "MAX_CLARIFICATION_TURNS",
    "AssessmentContext",
    "AssessmentStateMachine",
    "TransitionRule",
    "guard_analysis_completed",
    "guard_has_consent",
    "guard_has_symptoms",
    "guard_symptoms_confirmed",
    "guard_under_clarification_limit",
]
