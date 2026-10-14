"""Pydantic schemas for symptom representation, extraction, and updates.

Responsibilities:
    - Validate symptom structures, durations, and clinical severities.
    - Provide Create, Update, and Read contract models for symptom API endpoints.
    - Enforce non-empty normalized symptom naming.

Owner: Darshil (orchestration) · Task: S0-DAR-1 · Requirements: N/A
"""

from uuid import UUID, uuid4

from pydantic import Field, field_validator

from app.schemas.base import SchemaBase
from app.schemas.enums import DurationUnit, Severity, SymptomSource


class Duration(SchemaBase):
    """Structured duration of a symptom.

    Attributes:
        value: Non-negative duration length.
        unit: Duration time unit (HOUR, DAY, WEEK, MONTH, YEAR).
    """

    value: float = Field(..., ge=0.0, description="Duration numeric value")
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
    name: str = Field(..., min_length=1, max_length=128, description="Canonical symptom name")
    severity: Severity = Field(default=Severity.UNKNOWN, description="Symptom severity")
    duration: Duration | None = Field(default=None, description="Symptom duration")
    body_location: str | None = Field(default=None, max_length=128, description="Body site")
    source: SymptomSource = Field(default=SymptomSource.USER, description="Symptom source")
    extraction_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="AI extraction confidence (technical metric, not medical certainty)",
    )

    @field_validator("name")
    @classmethod
    def validate_name_not_blank(cls, value: str) -> str:
        """Ensure symptom name is stripped and non-empty.

        Args:
            value: Raw symptom name string.

        Returns:
            Normalized stripped symptom name.

        Raises:
            ValueError: If name is blank or only whitespace.
        """
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("Symptom name cannot be blank")
        return cleaned


class SymptomCreate(SchemaBase):
    """Schema for adding a new symptom to an assessment."""

    name: str = Field(..., min_length=1, max_length=128, description="Symptom name")
    severity: Severity = Field(default=Severity.UNKNOWN, description="Symptom severity")
    duration: Duration | None = Field(default=None, description="Symptom duration")
    body_location: str | None = Field(default=None, max_length=128, description="Body site")
    source: SymptomSource = Field(default=SymptomSource.USER, description="Symptom source")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        """Strip and normalize symptom name to lowercase."""
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("Symptom name cannot be blank")
        return cleaned


class SymptomUpdate(SchemaBase):
    """Schema for editing or confirming an existing symptom."""

    id: UUID | None = Field(default=None, description="Existing symptom identifier if updating")
    name: str | None = Field(default=None, min_length=1, max_length=128)
    severity: Severity | None = None
    duration: Duration | None = None
    body_location: str | None = Field(default=None, max_length=128)
    source: SymptomSource | None = Field(default=None, description="Updated symptom source")

    @field_validator("name")
    @classmethod
    def normalize_optional_name(cls, value: str | None) -> str | None:
        """Strip and normalize optional symptom name."""
        if value is None:
            return None
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("Symptom name cannot be blank")
        return cleaned


class SymptomRead(Symptom):
    """Response schema returning full symptom details."""

    pass
