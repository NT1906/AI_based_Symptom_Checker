"""Domain exceptions for assessment lifecycle and state machine operations.

Responsibilities:
    - Define InvalidStateTransitionError for illegal or unguarded state transitions.
    - Provide structured error payloads compliant with API contracts (HTTP 409).
    - Support guard violation details for debugging and audit logs.

Owner: Darshil (assessment) · Task: S1-DAR-1 · Requirements: N/A
"""

from typing import Any

from fastapi import status

from app.core.errors import AppError
from app.schemas.enums import AssessmentState


class AssessmentServiceError(AppError):
    """Base exception for assessment domain operations.

    Attributes:
        message: Safe, user-facing error message.
        code: Machine-readable error code.
        status_code: Corresponding HTTP status code.
        details: Optional supplementary error context.
    """

    def __init__(
        self,
        message: str,
        code: str = "ASSESSMENT_ERROR",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Any | None = None,
    ) -> None:
        """Initialize an AssessmentServiceError.

        Args:
            message: Safe, human-readable error description.
            code: Machine-readable uppercase error code.
            status_code: HTTP status code.
            details: Optional structured context.
        """
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
        )


class InvalidStateTransitionError(AssessmentServiceError):
    """Raised when an illegal lifecycle state transition is attempted.

    Complies with API contract Section 1.4: returns HTTP 409 Conflict with
    code INVALID_STATE_TRANSITION and currentState / targetState in details.
    """

    def __init__(
        self,
        current_state: AssessmentState,
        target_state: AssessmentState,
        message: str | None = None,
        reason: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize InvalidStateTransitionError with 409 status code.

        Args:
            current_state: Current assessment lifecycle state.
            target_state: Attempted target assessment state.
            message: Optional override for human-readable error message.
            reason: Specific reason why transition was disallowed.
            details: Optional additional diagnostic details.
        """
        error_msg = message or (
            f"Cannot transition from {current_state.value} to {target_state.value}"
            + (f": {reason}" if reason else ".")
        )
        payload: dict[str, Any] = {
            "currentState": current_state.value,
            "targetState": target_state.value,
        }
        if reason:
            payload["reason"] = reason
        if details:
            payload.update(details)

        super().__init__(
            message=error_msg,
            code="INVALID_STATE_TRANSITION",
            status_code=status.HTTP_409_CONFLICT,
            details=payload,
        )
        self.current_state = current_state
        self.target_state = target_state
        self.reason = reason


class StateGuardViolationError(InvalidStateTransitionError):
    """Raised when a defined transition fails one or more guard conditions.

    Attributes:
        guard_name: The identifier of the guard condition that failed.
    """

    def __init__(
        self,
        current_state: AssessmentState,
        target_state: AssessmentState,
        guard_name: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize StateGuardViolationError with guard details.

        Args:
            current_state: Current assessment lifecycle state.
            target_state: Target assessment state.
            guard_name: Name of the guard condition that failed.
            reason: Explanation of the guard failure.
            details: Optional structured context.
        """
        guard_details: dict[str, Any] = {"guard": guard_name}
        if details:
            guard_details.update(details)

        super().__init__(
            current_state=current_state,
            target_state=target_state,
            message=(
                f"Transition from {current_state.value} to {target_state.value} "
                f"blocked by guard '{guard_name}': {reason}"
            ),
            reason=reason,
            details=guard_details,
        )
        self.guard_name = guard_name


__all__ = [
    "AssessmentServiceError",
    "InvalidStateTransitionError",
    "StateGuardViolationError",
]
