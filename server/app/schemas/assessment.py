"""Pydantic schemas for assessment session management and state queries.

Responsibilities:
    - Validate assessment creation requests with mandatory consent linkage.
    - Support guest assessment claiming and ownership transfer into user accounts.
    - Provide read and state snapshot schemas for assessment lifecycle endpoints.
    - Export AssessmentState and AssessmentResult for cross-module consumption.
    - Include final triage risk level on AssessmentRead for assessment
      history (S2-DAR-11).

Owner: Darshil (orchestration) · Task: S2-DAR-1, S2-DAR-7, S2-DAR-11
Requirements: idea §10, NFR-03, FR-20
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas.base import RequestSchemaBase, SchemaBase
from app.schemas.enums import AssessmentState
from app.schemas.message import MessageRead
from app.schemas.result import AssessmentResult
from app.schemas.symptom import Symptom, SymptomRead


class AssessmentCreate(RequestSchemaBase):
    """Payload to initialize a new assessment with user consent.

    Enforces mass-assignment protection (extra='forbid') and validates consentId.
    """

    consent_id: UUID = Field(..., description="Unique consent record identifier")
    user_id: UUID | None = Field(
        default=None,
        description="Optional registered user ID",
    )
    guest_session_id: UUID | None = Field(
        default=None,
        description="Optional anonymous guest session ID",
    )


class AssessmentRead(SchemaBase):
    """Summary of an existing assessment."""

    id: UUID = Field(..., description="Unique assessment identifier")
    state: AssessmentState = Field(..., description="Current lifecycle state")
    consent_id: UUID = Field(..., description="Associated consent identifier")
    user_id: UUID | None = Field(default=None, description="Registered user identifier")
    guest_session_id: UUID | None = Field(
        default=None,
        description="Optional associated guest session identifier",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp in UTC",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp in UTC",
    )
    risk_level: str | None = Field(
        default=None,
        description="Final triage risk level (e.g. SELF_CARE, CONSULT_DOCTOR, URGENT)",
    )
    top_condition: str | None = Field(
        default=None,
        description="Name of the best-ranked possible condition in the saved result",
    )

    @model_validator(mode="before")
    @classmethod
    def _populate_risk_level(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data
        if hasattr(data, "id"):
            current_risk = getattr(data, "risk_level", None)
            if current_risk is None:
                try:
                    from sqlalchemy import desc, select
                    from sqlalchemy.orm import object_session

                    from app.models.audit_log import AuditLog

                    sess = object_session(data)
                    if sess is not None:
                        risk = sess.scalar(
                            select(AuditLog.risk_level)
                            .where(
                                AuditLog.assessment_id == data.id,
                                AuditLog.risk_level.is_not(None),
                            )
                            .order_by(desc(AuditLog.created_at))
                            .limit(1)
                        )
                        if risk is not None:
                            try:
                                data.risk_level = risk
                            except AttributeError:
                                pass
                except Exception:
                    pass
            elif hasattr(current_risk, "value"):
                try:
                    data.risk_level = current_risk.value
                except AttributeError:
                    pass
        return data


class AssessmentStateResponse(SchemaBase):
    """Detailed state snapshot for state polling and validation."""

    assessment_id: UUID = Field(..., description="Unique assessment identifier")
    state: AssessmentState = Field(..., description="Current lifecycle state")
    symptoms: list[Symptom] = Field(
        default_factory=list,
        description="Currently recorded symptoms",
    )
    clarification_count: int = Field(
        default=0,
        ge=0,
        le=3,
        description="Clarification loop count (capped at 3)",
    )
    max_clarifications: int = Field(default=3, description="Hard cap on clarifications")
    is_low_confidence: bool = Field(
        default=False,
        description=(
            "Whether low confidence was flagged due to capped clarification loop"
        ),
    )


class ClaimAssessmentRequest(RequestSchemaBase):
    """Payload to claim a guest assessment into a registered user account.

    Enforces mass-assignment protection (extra='forbid') and validates credentials.
    """

    user_id: UUID = Field(
        ...,
        description="Registered user account ID claiming the assessment",
    )
    guest_session_id: UUID | None = Field(
        default=None,
        description="Optional guest session ID for ownership verification",
    )


class ClaimAssessmentResponse(SchemaBase):
    """Result of claiming a guest assessment into a user account."""

    assessment_id: UUID = Field(..., description="Claimed assessment ID")
    user_id: UUID = Field(..., description="Owner user ID")
    claimed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when claim completed",
    )


class ProcessResult(SchemaBase):
    """Result returned after processing a user message in an assessment.

    Attributes:
        assessment_id: Unique assessment identifier.
        user_message: Recorded user message.
        message: Alias for user_message for backwards compatibility.
        assistant_message: Assistant response message if generated.
        next_state: Lifecycle state after message processing.
        symptoms: Current list of recognized/merged symptoms.
        result_type: Message intent classification
            (TEXT, CLARIFICATION, CONFIRMATION, ERROR).
        is_low_confidence: Flag set when clarification loop cap was reached.
    """

    assessment_id: UUID = Field(..., description="Unique assessment identifier")
    user_message: MessageRead = Field(
        ..., description="User message recorded in session"
    )
    message: MessageRead | None = Field(
        default=None,
        description="Alias for user_message for API compatibility",
    )
    assistant_message: MessageRead | None = Field(
        default=None,
        description="Assistant reply message or fallback prompt",
    )
    next_state: AssessmentState = Field(
        ...,
        description="Lifecycle state after message processing",
    )
    symptoms: list[SymptomRead] = Field(
        default_factory=list,
        description="Current merged canonical symptoms",
    )
    result_type: str = Field(
        default="TEXT",
        description="Result intent: CLARIFICATION, CONFIRMATION, TEXT, or ERROR",
    )
    is_low_confidence: bool = Field(
        default=False,
        description=(
            "Whether low confidence is flagged after reaching clarification limit"
        ),
    )

    def model_post_init(self, __context: object) -> None:
        """Ensure message alias mirrors user_message if not explicitly provided."""
        if self.message is None:
            object.__setattr__(self, "message", self.user_message)


__all__ = [
    "AssessmentCreate",
    "AssessmentRead",
    "AssessmentResult",
    "AssessmentState",
    "AssessmentStateResponse",
    "ClaimAssessmentRequest",
    "ClaimAssessmentResponse",
    "ProcessResult",
]
