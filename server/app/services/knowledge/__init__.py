"""Knowledge service package providing symptom normalization and vocabulary lookup.

Responsibilities:
    - Provide deterministic lay-term to canonical symptom normalization.
    - Expose canonical symptom vocabulary metadata and search interfaces.

Owner: Kavya (knowledge) · Task: S1-KAV-1 · Requirements: FR-03
"""

from app.services.knowledge.normalizer import (
    SymptomNormalizer,
    get_normalizer,
    normalize_symptom,
    normalize_symptom_id,
)
from app.services.knowledge.schemas import (
    CanonicalSymptom,
    NormalizedSymptom,
    TextMatchSpan,
)

__all__ = [
    "CanonicalSymptom",
    "NormalizedSymptom",
    "SymptomNormalizer",
    "TextMatchSpan",
    "get_normalizer",
    "normalize_symptom",
    "normalize_symptom_id",
]
