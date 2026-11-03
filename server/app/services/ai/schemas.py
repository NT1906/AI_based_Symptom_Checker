"""Pydantic schemas for AI symptom extraction and clarification responses.

Responsibilities:
    - Define typed contracts for extracted symptoms, duration, severity,
      onset, and body site.
    - Define schemas for missing-information detection and clarification questions.
    - Validate AI outputs at the service boundary.

Owner: Nishith · Task: S1-NIT-2 · Requirements: FR-04, FR-19, FR-20, NFR-05
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class QuestionTypeEnum(StrEnum):
    """Categorization of clarification questions for triage completeness."""

    DURATION = "DURATION"
    SEVERITY = "SEVERITY"
    LOCATION = "LOCATION"
    ONSET = "ONSET"
    ASSOCIATED = "ASSOCIATED"
    CONTEXT = "CONTEXT"


class MissingFieldEnum(StrEnum):
    """Clinical attribute fields that may be absent from symptom descriptions."""

    DURATION = "DURATION"
    SEVERITY = "SEVERITY"
    BODY_SITE = "BODY_SITE"
    ONSET = "ONSET"
    ASSOCIATED = "ASSOCIATED"


class MissingInfoItem(BaseModel):
    """Single clinical information gap identified during triage analysis.

    Attributes:
        symptom_name: Canonical symptom name where information is missing.
        missing_field: Specific clinical attribute that is absent or unknown.
        priority: Priority rank (1 = safety-critical / highest, 5 = lowest).
        reason: Plain-text justification for why this detail is needed.
    """

    model_config = ConfigDict(frozen=True)

    symptom_name: str = Field(
        min_length=1,
        max_length=128,
        description="Canonical symptom identifier",
    )
    missing_field: MissingFieldEnum = Field(
        description="Missing clinical attribute type",
    )
    priority: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Clinical triage priority rank (1 = highest urgency)",
    )
    reason: str = Field(
        min_length=1,
        max_length=300,
        description="Justification for the information request",
    )


class Duration(BaseModel):
    """Structured representation of symptom duration."""

    model_config = ConfigDict(frozen=True)

    value: float = Field(gt=0, description="Numerical duration value")
    unit: DurationUnitEnum = Field(
        default=DurationUnitEnum.DAY,
        description="Unit of time",
    )


class ExtractedSymptom(BaseModel):
    """Single extracted symptom with associated clinical attributes.

    Attributes:
        name: Canonical symptom identifier (e.g. headache, fever, abdominal_pain).
        severity: Clinical severity level (MILD, MODERATE, SEVERE, UNKNOWN).
        duration: Structured duration length and time unit, or None if unspecified.
        onset: Relative or explicit onset phrasing (e.g. 'since yesterday').
        body_site: Anatomical site where the symptom occurs
            (e.g. 'lower_right_abdomen').
        body_location: Synonymous with body_site for backward compatibility.
        confidence: Technical extraction confidence between 0.0 and 1.0.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

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
    body_site: str | None = Field(
        default=None,
        max_length=100,
        description="Specific anatomical body site if mentioned",
    )
    body_location: str | None = Field(
        default=None,
        max_length=100,
        description="Specific anatomical location if mentioned (synonym of body_site)",
    )
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="AI extraction confidence score between 0.0 and 1.0",
    )

    @model_validator(mode="before")
    @classmethod
    def sync_body_site_and_location(cls, data: Any) -> Any:
        """Synchronize body_site and body_location for seamless schema usage.

        Args:
            data: Raw input dictionary or object attributes.

        Returns:
            Normalized dictionary with both body_site and body_location populated.

        Raises:
            ValueError: If both fields are provided with conflicting values.
        """
        if isinstance(data, dict):
            site = data.get("body_site")
            loc = data.get("body_location")
            if (
                site is not None
                and loc is not None
                and str(site).strip().lower() != str(loc).strip().lower()
            ):
                raise ValueError(
                    f"Conflicting body_site ('{site}') and body_location ('{loc}')"
                )
            chosen = site if site is not None else loc
            if chosen is not None:
                updated = dict(data)
                updated["body_site"] = chosen
                updated["body_location"] = chosen
                return updated
        return data

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        """Strip and normalize canonical symptom name to lowercase.

        Args:
            value: Raw symptom name string.

        Returns:
            Cleaned lowercase symptom identifier.

        Raises:
            ValueError: If name is blank or only whitespace.
        """
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("Symptom name cannot be blank")
        return cleaned


class ExtractionResult(BaseModel):
    """Complete structured output from an extraction request."""

    model_config = ConfigDict(frozen=True)

    symptoms: list[ExtractedSymptom] = Field(
        default_factory=list,
        description="List of extracted canonical symptoms",
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
    question_type: QuestionTypeEnum | str | None = Field(
        default=None,
        description="Type of question (e.g. DURATION, SEVERITY, LOCATION, ASSOCIATED)",
    )
    target_symptom: str | None = Field(
        default=None,
        description="Canonical symptom name that this question focuses on",
    )
    missing_field: MissingFieldEnum | str | None = Field(
        default=None,
        description="Specific missing clinical attribute triggering this question",
    )
