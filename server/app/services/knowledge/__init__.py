"""Knowledge service package providing symptom normalization, glossary, and self-care.

Responsibilities:
    - Provide deterministic lay-term to canonical symptom normalization.
    - Expose canonical symptom vocabulary metadata and search interfaces.
    - Provide plain-language curated symptom glossary definitions and search.
    - Provide curated non-prescriptive supportive self-care guidance per condition.

Owner: Kavya (knowledge) · Task: S1-KAV-1, S1-KAV-3, S2-KAV-1
Requirements: FR-03, FR-18, idea §8, DR-05
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
    SelfCareGuidance,
    TextMatchSpan,
)
from app.services.knowledge.self_care import (
    SelfCareService,
    get_self_care_guidance,
    get_self_care_service,
    lookup_self_care,
)

__all__ = [
    "CanonicalSymptom",
    "GlossaryEntry",
    "NormalizedSymptom",
    "SelfCareGuidance",
    "SelfCareService",
    "SymptomGlossary",
    "SymptomNormalizer",
    "TextMatchSpan",
    "get_glossary",
    "get_normalizer",
    "get_self_care_guidance",
    "get_self_care_service",
    "get_symptom_definition",
    "lookup_glossary",
    "lookup_self_care",
    "normalize_symptom",
    "normalize_symptom_id",
]
