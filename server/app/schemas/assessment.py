"""Pydantic schemas for assessment session management and state queries.

Responsibilities:
    - Validate assessment creation requests with mandatory consent linkage.
    - Provide read and state snapshot schemas for assessment lifecycle endpoints.
    - Export AssessmentState and AssessmentResult for cross-module consumption.

Owner: Darshil (orchestration) · Task: S0-DAR-1 · Requirements: N/A
"""

from datetime import datetime, UTC
from uuid import UUID

from pydantic import Field

from app.schemas.base import SchemaBase
from app.schemas.enums import AssessmentState
from app.schemas.result import AssessmentResult
from app.schemas.symptom import Symptom


class AssessmentCreate(SchemaBase):
    """Payload to initialize a new assessment with user consent."""

    consent_id: UUID = Field(..., description="Unique consent record identifier")
    user_id: UUID | None = Field(
        default=None,
        description="Optional registered user ID",
    )


class AssessmentRead(SchemaBase):
    """Summary of an existing assessment."""

    id: UUID = Field(..., description="Unique assessment identifier")
    state: AssessmentState = Field(..., description="Current lifecycle state")
    consent_id: UUID = Field(..., description="Associated consent identifier")
    user_id: UUID | None = Field(default=None, description="Registered user identifier")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp in UTC",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp in UTC",
    )


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


__all__ = [
    "AssessmentCreate",
    "AssessmentRead",
    "AssessmentResult",
    "AssessmentState",
    "AssessmentStateResponse",
]
