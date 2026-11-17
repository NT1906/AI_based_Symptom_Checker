"""Assessment service package: state machine, session coordination, and orchestration.

Responsibilities:
    - Export AssessmentStateMachine and AssessmentContext for assessment
      lifecycle control.
    - Export AssessmentOrchestrator for message processing and AI coordination.
    - Export domain exceptions for state transitions and guard validation.
    - Export constants governing assessment progression rules.
    - Export RESULT_DEADLINE_SECONDS (5.0 s) for NFR-01 / S2-DAR-8 performance SLA.

Owner: Darshil (assessment) · Task: S1-DAR-2, S2-DAR-8
Requirements: FR-03, FR-17, NFR-01
"""

from app.services.assessment.exceptions import (
    AssessmentAccessDeniedError,
    AssessmentServiceError,
    InvalidStateTransitionError,
    StateGuardViolationError,
)
from app.services.assessment.orchestrator import (
    RESULT_DEADLINE_SECONDS,
    AssessmentOrchestrator,
    AssessmentSession,
    merge_symptoms,
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
    "RESULT_DEADLINE_SECONDS",
    "AssessmentAccessDeniedError",
    "AssessmentContext",
    "AssessmentOrchestrator",
    "AssessmentServiceError",
    "AssessmentSession",
    "AssessmentStateMachine",
    "InvalidStateTransitionError",
    "StateGuardViolationError",
    "TransitionRule",
    "guard_analysis_completed",
    "guard_has_consent",
    "guard_has_symptoms",
    "guard_symptoms_confirmed",
    "guard_under_clarification_limit",
    "merge_symptoms",
]
