"""Pydantic schemas and domain models for the symptom knowledge service.

Responsibilities:
    - Define immutable data models for canonical symptoms and lay-term mappings.
    - Define normalization result structures for deterministic resolution.
    - Define curated symptom glossary entries for user-friendly definitions.
    - Validate symptom structures at service boundaries.

Owner: Kavya (knowledge) · Task: S1-KAV-1, S1-KAV-3 · Requirements: FR-03, FR-18
"""

from pydantic import BaseModel, ConfigDict, Field


class CanonicalSymptom(BaseModel):
    """Immutable record for a canonical symptom in the vocabulary.

    Attributes:
        id: Unique snake_case symptom identifier aligned with conditions.json.
        name: Human-readable display name.
        body_system: Anatomical body system category.
        lay_terms: Colloquial, patient-facing synonyms and transliterations.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        min_length=1,
        max_length=64,
        description="Canonical snake_case symptom ID",
    )
    name: str = Field(
        min_length=1,
        max_length=128,
        description="Canonical display name",
    )
    body_system: str = Field(
        min_length=1,
        max_length=64,
        description="Anatomical body system",
    )
    lay_terms: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Colloquial synonyms and lay terms",
    )


class NormalizedSymptom(BaseModel):
    """Result of normalizing a colloquial symptom or lay term to a canonical ID.

    Attributes:
        canonical_id: Resolved snake_case canonical identifier.
        canonical_name: Canonical display name from the vocabulary.
        body_system: Body system category associated with the symptom.
        matched_term: Exact lay term or alias that matched the user input.
        confidence: Deterministic match confidence (1.0 for exact/alias match).
    """

    model_config = ConfigDict(frozen=True)

    canonical_id: str = Field(description="Normalized canonical symptom ID")
    canonical_name: str = Field(description="Canonical display name")
    body_system: str = Field(description="Associated body system")
    matched_term: str = Field(description="Colloquial term or phrase that matched")
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Normalization confidence (1.0 for deterministic match)",
    )


class TextMatchSpan(BaseModel):
    """A canonical symptom match identified within a free-text sentence.

    Attributes:
        canonical_id: Resolved canonical symptom identifier.
        canonical_name: Canonical display name.
        body_system: Body system category.
        matched_term: The lay term or canonical name matched in the text.
        start_char: 0-indexed start character offset in original text.
        end_char: 0-indexed end character offset in original text.
    """

    model_config = ConfigDict(frozen=True)

    canonical_id: str = Field(description="Canonical symptom ID")
    canonical_name: str = Field(description="Canonical display name")
    body_system: str = Field(description="Associated body system")
    matched_term: str = Field(description="Term matched in the text")
    start_char: int = Field(ge=0, description="Start character offset")
    end_char: int = Field(ge=0, description="End character offset")


class GlossaryEntry(BaseModel):
    """Immutable curated plain-language glossary entry for a canonical symptom.

    Provides user-friendly, non-diagnostic symptom descriptions and safety
    guidance for tooltips, user clarification, and off-topic explanation.

    Attributes:
        id: Canonical snake_case symptom ID aligned with symptoms.json.
        name: Human-readable clinical display name.
        body_system: Anatomical body system classification.
        plain_definition: Empathetic, lay-language description of the symptom.
        when_to_seek_care: Safe guidance on when doctor evaluation is advised.
        lay_terms: Colloquial synonyms and search aliases (English & Hinglish).
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        min_length=1,
        max_length=64,
        description="Canonical snake_case symptom ID",
    )
    name: str = Field(
        min_length=1,
        max_length=128,
        description="Canonical display name",
    )
    body_system: str = Field(
        min_length=1,
        max_length=64,
        description="Anatomical body system",
    )
    plain_definition: str = Field(
        min_length=10,
        max_length=1024,
        description="Empathetic, lay-language description",
    )
    when_to_seek_care: str = Field(
        min_length=10,
        max_length=1024,
        description="Guidance on when medical care is recommended",
    )
    lay_terms: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Colloquial synonyms and lay terms for search lookup",
    )
