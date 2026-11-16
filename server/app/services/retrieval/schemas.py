"""Domain models for symptom retrieval: vocabulary entries, matches, resolutions.

Responsibilities:
    - Describe one phrase of the symptom vocabulary that gets embedded.
    - Describe the nearest stored phrase for a query vector.
    - Describe how a free-text symptom name was resolved to a canonical ID.

The similarity score is internal: it is logged for evaluation but never shown
to the user (AI_RULES.md §2.3).

Owner: Nisarg (retrieval) · Task: S2-NIS-7 · Requirements: FR-03, FR-18, DR-02
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class MatchMethod(StrEnum):
    """How a symptom name was resolved."""

    EXACT = "EXACT"
    """The knowledge normalizer matched a display name or lay term."""

    SEMANTIC = "SEMANTIC"
    """The nearest stored phrase by embedding similarity, above the threshold."""


class VocabularyEntry(BaseModel):
    """One phrase that stands for a canonical symptom.

    Attributes:
        symptom_id: Canonical symptom ID, e.g. ``chest_pain``.
        phrase: Display name or lay term, lowercased, e.g. ``seene me dard``.
    """

    model_config = ConfigDict(frozen=True)

    symptom_id: str = Field(min_length=1, max_length=64)
    phrase: str = Field(min_length=1, max_length=256)


class VectorMatch(BaseModel):
    """The stored phrase nearest to a query vector.

    Attributes:
        symptom_id: Canonical symptom ID of that phrase.
        phrase: The stored phrase.
        similarity: Cosine similarity in [-1, 1]; higher is closer.
    """

    model_config = ConfigDict(frozen=True)

    symptom_id: str
    phrase: str
    similarity: float


class ResolvedSymptom(BaseModel):
    """A free-text symptom name mapped to a canonical symptom ID.

    Attributes:
        symptom_id: Canonical symptom ID, safe to pass to the risk engine.
        method: ``EXACT`` or ``SEMANTIC``.
        matched_phrase: The vocabulary phrase that matched.
        similarity: Cosine similarity for ``SEMANTIC``; ``None`` for ``EXACT``.
    """

    model_config = ConfigDict(frozen=True)

    symptom_id: str
    method: MatchMethod
    matched_phrase: str
    similarity: float | None = None
