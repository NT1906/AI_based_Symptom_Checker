"""Knowledge service package providing symptom normalization and curated glossary.

Responsibilities:
    - Provide deterministic lay-term to canonical symptom normalization.
    - Expose canonical symptom vocabulary metadata and search interfaces.
    - Provide plain-language curated symptom glossary definitions and search.

Owner: Kavya (knowledge) · Task: S1-KAV-1, S1-KAV-3 · Requirements: FR-03, FR-18
"""

from app.services.knowledge.glossary import (
    SymptomGlossary,
    get_glossary,
    get_symptom_definition,
    lookup_glossary,
)
from app.services.knowledge.normalizer import (
    SymptomNormalizer,
    get_normalizer,
    normalize_symptom,
    normalize_symptom_id,
)
from app.services.knowledge.schemas import (
    CanonicalSymptom,
    GlossaryEntry,
    NormalizedSymptom,
    TextMatchSpan,
)

__all__ = [
    "CanonicalSymptom",
    "GlossaryEntry",
    "NormalizedSymptom",
    "SymptomGlossary",
    "SymptomNormalizer",
    "TextMatchSpan",
    "get_glossary",
    "get_normalizer",
    "get_symptom_definition",
    "lookup_glossary",
    "normalize_symptom",
    "normalize_symptom_id",
]
