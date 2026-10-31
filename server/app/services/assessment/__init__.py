"""Assessment service package: state machine, session coordination, and orchestration.

Responsibilities:
    - Export AssessmentStateMachine and AssessmentContext for assessment
      lifecycle control.
    - Export domain exceptions for state transitions and guard validation.
    - Export constants governing assessment progression rules.

Owner: Darshil (assessment) · Task: S1-DAR-1 · Requirements: N/A
"""

from app.services.assessment.exceptions import (
    AssessmentServiceError,
    InvalidStateTransitionError,
    StateGuardViolationError,
)
from app.services.assessment.state_machine import (
    MAX_CLARIFICATION_TURNS,
    AssessmentContext,
    AssessmentStateMachine,
    TransitionRule,
    guard_analysis_completed,
    guard_has_consent,
    guard_has_symptoms,
    guard_symptoms_confirmed,
    guard_under_clarification_limit,
)

__all__ = [
    "MAX_CLARIFICATION_TURNS",
    "AssessmentContext",
    "AssessmentServiceError",
    "AssessmentStateMachine",
    "InvalidStateTransitionError",
    "StateGuardViolationError",
    "TransitionRule",
    "guard_analysis_completed",
    "guard_has_consent",
    "guard_has_symptoms",
    "guard_symptoms_confirmed",
    "guard_under_clarification_limit",
]
