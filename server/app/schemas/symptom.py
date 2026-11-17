"""Pydantic schemas for symptom representation, extraction, and updates.

Responsibilities:
    - Validate symptom structures, durations, and clinical severities.
    - Provide Create, Update, and Read contract models for symptom API endpoints.
    - Enforce non-empty normalized symptom naming, null byte rejection, and bounds.
    - Prevent mass assignment and unbounded list updates (NFR-03).

Owner: Darshil (orchestration) · Task: S0-DAR-1, S2-DAR-7 · Requirements: NFR-03
"""

from uuid import UUID, uuid4

from pydantic import Field, field_validator, model_validator

from app.schemas.base import RequestSchemaBase, SchemaBase
from app.schemas.enums import DurationUnit, Severity, SymptomSource


class Duration(RequestSchemaBase):
    """Structured duration of a symptom.

    Attributes:
        value: Non-negative duration length (capped at 36500.0, NaN/Inf forbidden).
        unit: Duration time unit (HOUR, DAY, WEEK, MONTH, YEAR).
    """

    value: float = Field(
        ...,
        ge=0.0,
        le=36500.0,
        allow_inf_nan=False,
        description="Duration numeric value (non-negative, max 36500)",
    )
    unit: DurationUnit = Field(default=DurationUnit.DAY, description="Duration unit")


class Symptom(SchemaBase):
    """Canonical representation of an extracted or user-reported symptom.

    Attributes:
        id: Unique identifier for the symptom record.
        name: Normalized canonical symptom name.
        severity: Clinical severity level.
        duration: Structured duration or None if unknown.
        body_location: Anatomical body site or None if systemic.
        source: Provenance of the symptom report.
        extraction_confidence: AI extraction confidence score between 0.0 and 1.0.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique symptom identifier")
    name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Canonical symptom name",
    )
    severity: Severity = Field(default=Severity.UNKNOWN, description="Symptom severity")
    duration: Duration | None = Field(default=None, description="Symptom duration")
    body_location: str | None = Field(
        default=None,
        max_length=128,
        description="Body site",
    )
    source: SymptomSource = Field(
        default=SymptomSource.USER,
        description="Symptom source",
    )
    extraction_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="AI extraction confidence (technical metric, not diagnosis)",
    )

    @field_validator("name")
    @classmethod
    def validate_name_not_blank(cls, value: str) -> str:
        """Ensure symptom name is stripped, non-empty, and contains no null bytes.

        Args:
            value: Raw symptom name string.

        Returns:
            Normalized stripped symptom name.

        Raises:
            ValueError: If name contains null bytes or is blank.
        """
        if "\x00" in value:
            raise ValueError("Symptom name cannot contain null bytes")
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("Symptom name cannot be blank")
        return cleaned

    @field_validator("body_location")
    @classmethod
    def validate_body_location(cls, value: str | None) -> str | None:
        """Strip and validate optional body location."""
        if value is None:
            return None
        if "\x00" in value:
            raise ValueError("Body location cannot contain null bytes")
        cleaned = value.strip()
        return cleaned if cleaned else None


class SymptomCreate(RequestSchemaBase):
    """Schema for adding a new symptom to an assessment.

    Enforces mass-assignment protection (extra='forbid'), null byte rejection,
    and string length limits.
    """

    name: str = Field(..., min_length=1, max_length=128, description="Symptom name")
    severity: Severity = Field(default=Severity.UNKNOWN, description="Symptom severity")
    duration: Duration | None = Field(default=None, description="Symptom duration")
    body_location: str | None = Field(
        default=None,
        max_length=128,
        description="Body site",
    )
    source: SymptomSource = Field(
        default=SymptomSource.USER,
        description="Symptom source",
    )

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        """Strip and normalize symptom name to lowercase, rejecting null bytes."""
        if "\x00" in value:
            raise ValueError("Symptom name cannot contain null bytes")
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("Symptom name cannot be blank")
        return cleaned

    @field_validator("body_location")
    @classmethod
    def normalize_body_location(cls, value: str | None) -> str | None:
        """Strip and validate optional body location."""
        if value is None:
            return None
        if "\x00" in value:
            raise ValueError("Body location cannot contain null bytes")
        cleaned = value.strip()
        return cleaned if cleaned else None


class SymptomUpdate(RequestSchemaBase):
    """Schema for editing or confirming an existing symptom.

    Enforces mass-assignment protection (extra='forbid'), null byte rejection,
    and requires at least one field to update.
    """

    id: UUID | None = Field(
        default=None,
        description="Existing symptom identifier if updating",
    )
    name: str | None = Field(default=None, min_length=1, max_length=128)
    severity: Severity | None = None
    duration: Duration | None = None
    body_location: str | None = Field(default=None, max_length=128)
    source: SymptomSource | None = Field(
        default=None,
        description="Updated symptom source",
    )

    @field_validator("name")
    @classmethod
    def normalize_optional_name(cls, value: str | None) -> str | None:
        """Strip and normalize optional symptom name, rejecting null bytes."""
        if value is None:
            return None
        if "\x00" in value:
            raise ValueError("Symptom name cannot contain null bytes")
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("Symptom name cannot be blank")
        return cleaned

    @field_validator("body_location")
    @classmethod
    def normalize_optional_body_location(cls, value: str | None) -> str | None:
        """Strip and validate optional body location."""
        if value is None:
            return None
        if "\x00" in value:
            raise ValueError("Body location cannot contain null bytes")
        cleaned = value.strip()
        return cleaned if cleaned else None

    @model_validator(mode="after")
    def validate_has_at_least_one_field(self) -> "SymptomUpdate":
        """Ensure that update payload is not completely empty."""
        if (
            self.id is None
            and self.name is None
            and self.severity is None
            and self.duration is None
            and self.body_location is None
            and self.source is None
        ):
            raise ValueError("SymptomUpdate must specify at least one field to update")
        return self


class UpdateSymptomsRequest(RequestSchemaBase):
    """Request payload to confirm, add, or update recorded symptoms (NFR-03).

    Enforces bounds on the batch size (1 to 50 symptoms per update) and
    mass-assignment protection (extra='forbid').
    """

    symptoms: list[SymptomUpdate] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of updated, added, or confirmed symptoms (1-50 items)",
    )


class SymptomRead(Symptom):
    """Response schema returning full symptom details."""

    pass


__all__ = [
    "Duration",
    "Symptom",
    "SymptomCreate",
    "SymptomRead",
    "SymptomUpdate",
    "UpdateSymptomsRequest",
]
