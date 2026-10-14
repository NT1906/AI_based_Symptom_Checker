"""Pydantic schemas for AI symptom extraction and clarification responses.

Responsibilities:
 - Define typed contracts for extracted symptoms, duration, and severity.
 - Define schema for targeted follow-up clarification questions.
 - Validate AI outputs at the service boundary.

Owner: Nishith · Task: S0-NIT-1 · Requirements: NFR-05
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SeverityEnum(StrEnum):
    """Normalized symptom severity level."""

    MILD = "MILD"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"
    UNKNOWN = "UNKNOWN"


class DurationUnitEnum(StrEnum):
    """Allowed time units for symptom duration."""

    HOUR = "HOUR"
    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"
    YEAR = "YEAR"


class Duration(BaseModel):
    """Structured representation of symptom duration."""

    model_config = ConfigDict(frozen=True)

    value: float = Field(gt=0, description="Numerical duration value")
    unit: DurationUnitEnum = Field(description="Unit of time")


class ExtractedSymptom(BaseModel):
    """Single extracted symptom with associated clinical attributes."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(
        min_length=1,
        max_length=128,
        description="Canonical symptom identifier in snake_case (e.g. headache, fever)",
    )
    severity: SeverityEnum = Field(
        default=SeverityEnum.UNKNOWN,
        description="Symptom severity assessment",
    )
    duration: Duration | None = Field(
        default=None,
        description="Duration if explicitly specified by the patient",
    )
    onset: str | None = Field(
        default=None,
        max_length=100,
        description="Relative or explicit onset phrasing (e.g. 'since yesterday')",
    )
    body_location: str | None = Field(
        default=None,
        max_length=100,
        description="Specific anatomical location if mentioned",
    )


class ExtractionResult(BaseModel):
    """Complete structured output from an extraction request."""

    model_config = ConfigDict(frozen=True)

    symptoms: list[ExtractedSymptom] = Field(
        default_factory=list,
        description="List of extracted symptoms",
    )
    associated_symptoms: list[str] = Field(
        default_factory=list,
        description="Related or secondary symptoms mentioned by user",
    )
    requires_clarification: bool = Field(
        default=False,
        description=(
            "Whether missing safety or triage information warrants clarification"
        ),
    )
    clarification_reason: str | None = Field(
        default=None,
        max_length=500,
        description="Reason why follow-up clarification is indicated",
    )


class ClarificationResult(BaseModel):
    """Output from the clarification question generator."""

    model_config = ConfigDict(frozen=True)

    should_ask: bool = Field(
        description="Whether a clarification question should be sent to the user",
    )
    question: str | None = Field(
        default=None,
        max_length=500,
        description="Conversational, non-diagnostic follow-up question text",
    )
    question_type: str | None = Field(
        default=None,
        description="Type of question (e.g. DURATION, SEVERITY, LOCATION, ASSOCIATED)",
    )
    target_symptom: str | None = Field(
        default=None,
        description="Canonical symptom name that this question focuses on",
    )
