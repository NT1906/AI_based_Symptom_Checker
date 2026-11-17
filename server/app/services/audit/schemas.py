"""Pydantic schemas for audit logging service.

Responsibilities:
    - Typed schemas for audit event actions, creation payloads, and read models.
    - Zero PII enforcement at the schema validation layer (NFR-10, DR-06, S2-HAR-7).

Owner: Vivek (services/audit) · Task: S2-VIV-4 · Requirements: NFR-10
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.base import SchemaBase


class AuditEventType(StrEnum):
    """Permitted audit event action categories."""

    ANALYSIS = "ANALYSIS"
    RECOMMENDATION = "RECOMMENDATION"
    TRIAGE = "TRIAGE"


# Keys strictly prohibited in audit details to prevent PII leakage (NFR-10, DR-06)
FORBIDDEN_AUDIT_KEYS: frozenset[str] = frozenset(
    {
        "name",
        "email",
        "phone",
        "password",
        "message_text",
        "raw_text",
        "chat_history",
        "image_data",
        "image_bytes",
    }
)


class AuditLogCreate(SchemaBase):
    """Payload to record an audit log event."""

    action: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Audited action category (e.g. ANALYSIS, RECOMMENDATION)",
    )
    assessment_id: UUID | None = Field(
        default=None,
        description="Associated assessment identifier",
    )
    user_id: UUID | None = Field(
        default=None,
        description="Registered user account ID (None for guest sessions)",
    )
    guest_session_id: UUID | None = Field(
        default=None,
        description="Guest session ID (None for registered accounts)",
    )
    risk_level: str | None = Field(
        default=None,
        description="Triage severity tier (SELF_CARE, CONSULT_DOCTOR, URGENT)",
    )
    risk_engine_version: str | None = Field(
        default=None,
        max_length=32,
        description="Deterministic risk engine rule version",
    )
    condition_model_version: str | None = Field(
        default=None,
        max_length=64,
        description="Condition predictor model version",
    )
    cv_model_version: str | None = Field(
        default=None,
        max_length=64,
        description="CV classifier model version",
    )
    ai_model: str | None = Field(
        default=None,
        max_length=64,
        description="AI gateway LLM identifier",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Non-PII operational details and telemetry",
    )

    @field_validator("action")
    @classmethod
    def validate_action_not_blank(cls, v: str) -> str:
        """Ensure action string is not empty or whitespace."""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("action must not be blank")
        return cleaned

    @field_validator("details")
    @classmethod
    def validate_zero_pii_in_details(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Guarantee no forbidden PII keys exist in audit details."""
        for key in v:
            if key.lower() in FORBIDDEN_AUDIT_KEYS:
                raise ValueError(
                    f"Forbidden key '{key}' in audit details violates "
                    "zero-PII rule (NFR-10)"
                )
        return v


class AuditLogRead(SchemaBase):
    """Representation of an immutable audit record."""

    id: UUID = Field(..., description="Unique audit record identifier")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp of the audit record",
    )
    action: str = Field(..., description="Audited action category")
    assessment_id: UUID | None = Field(
        default=None,
        description="Associated assessment identifier",
    )
    user_id: UUID | None = Field(
        default=None,
        description="Registered user account ID",
    )
    guest_session_id: UUID | None = Field(
        default=None,
        description="Guest session ID",
    )
    risk_level: str | None = Field(
        default=None,
        description="Triage severity tier",
    )
    risk_engine_version: str | None = Field(
        default=None,
        description="Deterministic risk engine rule version",
    )
    condition_model_version: str | None = Field(
        default=None,
        description="Condition predictor model version",
    )
    cv_model_version: str | None = Field(
        default=None,
        description="CV classifier model version",
    )
    ai_model: str | None = Field(
        default=None,
        description="AI gateway LLM identifier",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Non-PII operational details",
    )
