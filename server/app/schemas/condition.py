"""Pydantic schema for predicted health conditions.

Responsibilities:
    - Represent candidate conditions with categorical confidence labels.
    - Provide metadata such as ICD-10 code, medical specialty, and rank.
    - Guarantee non-diagnostic presentation compliance (AI_RULES.md §2).

Owner: Darshil (orchestration) · Task: S0-DAR-1 · Requirements: N/A
"""

from pydantic import Field, field_validator

from app.schemas.base import SchemaBase
from app.schemas.enums import ConfidenceLabel


class Condition(SchemaBase):
    """A possible condition associated with the reported symptoms.

    Attributes:
        name: Clinical or plain-language name of the potential condition.
        confidence: Categorical confidence tier (Likely, Possible, Less likely).
        rank: Rank index based on symptom-overlap scoring (1 = highest match).
        icd10_code: Standard ICD-10 clinical coding classification, if available.
        specialty: Recommended medical specialty for clinical evaluation.
        description: Brief informational summary of the condition.
        why: Plain-language contributing factors, e.g. "Because you reported
            fever and joint pain." (FR-24, S2-NIS-2).
    """

    name: str = Field(..., min_length=1, max_length=256, description="Condition name")
    confidence: ConfidenceLabel = Field(
        ...,
        description="Categorical confidence label (never a raw percentage)",
    )
    rank: int = Field(default=1, ge=1, description="Relative match rank")
    icd10_code: str | None = Field(
        default=None,
        max_length=32,
        description="ICD-10 code",
    )
    specialty: str | None = Field(
        default=None,
        max_length=128,
        description="Medical specialty",
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Overview",
    )
    why: str | None = Field(
        default=None,
        max_length=500,
        description="Plain-language contributing factors (FR-24)",
    )

    @field_validator("name")
    @classmethod
    def validate_name_not_blank(cls, value: str) -> str:
        """Ensure condition name is not whitespace and contains no null bytes.

        Args:
            value: Condition name string.

        Returns:
            Stripped condition name.

        Raises:
            ValueError: If name is blank or contains null bytes.
        """
        if "\x00" in value:
            raise ValueError("Condition name cannot contain null bytes")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Condition name cannot be blank")
        return cleaned
