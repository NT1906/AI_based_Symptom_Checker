"""Deterministic symptom normalization and canonical vocabulary lookup service.

Responsibilities:
    - Load and index the canonical symptom vocabulary v0 (100 symptoms, 602 lay terms).
    - Provide O(1) deterministic mapping from colloquial lay terms to canonical IDs.
    - Extract and locate canonical symptom mentions in free-text clinical descriptions.
    - Provide vocabulary querying by canonical ID and body system.

Owner: Kavya (knowledge) · Task: S1-KAV-1 · Requirements: FR-03
"""

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.services.knowledge.schemas import (
    CanonicalSymptom,
    NormalizedSymptom,
    TextMatchSpan,
)

MAX_INPUT_LENGTH = 10_000
DATA_FILE = Path(__file__).parent / "data" / "symptoms.json"
FALLBACK_DATA_FILE = (
    Path(__file__).parents[4] / "ml" / "datasets" / "symptoms" / "symptoms.json"
)

_PUNCTUATION_STRIP = re.compile(r"^[\s.,!?;:\"'()\[\]{}]+|[\s.,!?;:\"'()\[\]{}]+$")
_WHITESPACE_COLLAPSE = re.compile(r"\s+")


def _normalize_text(text: str) -> str:
    """Normalize unicode characters, collapse whitespace, and lowercase string.

    Args:
        text: Raw input string.

    Returns:
        Cleaned, NFKC-normalized lowercase string.
    """
    normalized = unicodedata.normalize("NFKC", text)
    lowered = normalized.lower()
    return _WHITESPACE_COLLAPSE.sub(" ", lowered).strip()


def _strip_surrounding_punctuation(text: str) -> str:
    """Strip leading and trailing punctuation while preserving internal spaces.

    Args:
        text: Raw text segment.

    Returns:
        Cleaned string without peripheral punctuation.
    """
    return _PUNCTUATION_STRIP.sub("", text)


class SymptomNormalizer:
    """Deterministic normalizer mapping lay terms to canonical symptom IDs.

    Loads the canonical symptom vocabulary and compiles lookup indices for
    O(1) exact lay-term resolution and word-boundary phrase extraction.
    """

    def __init__(self, data_path: Path | None = None) -> None:
        """Initialize the normalizer with vocabulary data.

        Args:
            data_path: Optional explicit path to symptoms.json. If None,
                checks default packaged location then repo fallback.

        Raises:
            FileNotFoundError: If no vocabulary file can be located.
            ValueError: If vocabulary data is empty or structurally invalid.
        """
        path = data_path or self._resolve_data_path()
        self._symptoms_by_id: dict[str, CanonicalSymptom] = {}
        self._symptoms_by_alias: dict[str, CanonicalSymptom] = {}
        self._alias_to_matched_term: dict[str, str] = {}
        self._body_systems: tuple[str, ...] = ()
        self._search_regex: re.Pattern[str] | None = None
        self._regex_alias_map: dict[str, CanonicalSymptom] = {}

        self._load_and_index(path)

    @staticmethod
    def _resolve_data_path() -> Path:
        """Resolve the path to the symptoms vocabulary file.

        Returns:
            Existing Path to symptoms.json.

        Raises:
            FileNotFoundError: If the vocabulary file is not found.
        """
        if DATA_FILE.exists():
            return DATA_FILE
        if FALLBACK_DATA_FILE.exists():
            return FALLBACK_DATA_FILE
        raise FileNotFoundError(
            f"Symptom vocabulary not found at '{DATA_FILE}' or '{FALLBACK_DATA_FILE}'"
        )

    def _load_and_index(self, path: Path) -> None:
        """Parse symptoms.json and construct lookup indices.

        Args:
            path: Path to symptoms.json.
        """
        with path.open(encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)

        raw_systems = data.get("body_systems", [])
        self._body_systems = tuple(str(bs) for bs in raw_systems)

        raw_symptoms = data.get("symptoms", [])
        if not raw_symptoms:
            raise ValueError(f"Vocabulary at '{path}' contains no symptoms")

        alias_candidates: list[tuple[str, CanonicalSymptom, str]] = []

        for item in raw_symptoms:
            canonical = CanonicalSymptom(
                id=item["id"],
                name=item["name"],
                body_system=item["body_system"],
                lay_terms=tuple(item.get("lay_terms", ())),
            )
            self._symptoms_by_id[canonical.id] = canonical

            # Index 1: exact snake_case id
            clean_id = _normalize_text(canonical.id)
            alias_candidates.append((clean_id, canonical, canonical.id))

            # Index 2: id with underscores as spaces
            id_spaced = _normalize_text(canonical.id.replace("_", " "))
            alias_candidates.append((id_spaced, canonical, canonical.id))

            # Index 3: canonical display name
            clean_name = _normalize_text(canonical.name)
            alias_candidates.append((clean_name, canonical, canonical.name))

            # Index 4: lay terms and Hinglish transliterations
            for lay in canonical.lay_terms:
                clean_lay = _normalize_text(lay)
                if clean_lay:
                    alias_candidates.append((clean_lay, canonical, lay))

        # Sort alias candidates by descending length for greedy matching
        alias_candidates.sort(key=lambda t: len(t[0]), reverse=True)

        regex_patterns: list[str] = []
        for clean_alias, symptom, original_term in alias_candidates:
            if clean_alias not in self._symptoms_by_alias:
                self._symptoms_by_alias[clean_alias] = symptom
                self._alias_to_matched_term[clean_alias] = original_term
                self._regex_alias_map[clean_alias] = symptom
                regex_patterns.append(re.escape(clean_alias))

        if regex_patterns:
            # Word-boundary pattern matching with case insensitivity
            combined = r"\b(" + "|".join(regex_patterns) + r")\b"
            self._search_regex = re.compile(combined, re.IGNORECASE)

    def normalize(self, query: str) -> NormalizedSymptom | None:
        """Map a colloquial term, lay synonym, or symptom name to its canonical record.

        Args:
            query: User symptom phrase (e.g. "tummy ache", "badan dard", "headache").

        Returns:
            NormalizedSymptom with canonical ID and display name, or None if unmatched.
        """
        if not isinstance(query, str) or not query:
            return None
        if len(query) > MAX_INPUT_LENGTH:
            query = query[:MAX_INPUT_LENGTH]

        cleaned = _strip_surrounding_punctuation(_normalize_text(query))
        if not cleaned:
            return None

        # 1. Exact alias lookup
        symptom = self._symptoms_by_alias.get(cleaned)
        if symptom is not None:
            matched_term = self._alias_to_matched_term.get(cleaned, cleaned)
            return NormalizedSymptom(
                canonical_id=symptom.id,
                canonical_name=symptom.name,
                body_system=symptom.body_system,
                matched_term=matched_term,
                confidence=1.0,
            )

        # 2. Check if replacing hyphens/slashes with spaces matches
        alternative = _normalize_text(re.sub(r"[-/]", " ", cleaned))
        symptom = self._symptoms_by_alias.get(alternative)
        if symptom is not None:
            matched_term = self._alias_to_matched_term.get(alternative, alternative)
            return NormalizedSymptom(
                canonical_id=symptom.id,
                canonical_name=symptom.name,
                body_system=symptom.body_system,
                matched_term=matched_term,
                confidence=1.0,
            )

        return None

    def normalize_id(self, query: str) -> str | None:
        """Convenience method returning only the canonical ID string.

        Args:
            query: User symptom phrase.

        Returns:
            Canonical snake_case symptom ID, or None if unmatched.
        """
        result = self.normalize(query)
        return result.canonical_id if result else None

    def extract_symptoms_from_text(self, text: str) -> list[TextMatchSpan]:
        """Identify and extract all canonical symptom mentions in natural language text.

        Uses word-boundary matching and longest-phrase greediness to resolve
        compound mentions without overlapping substring collisions.

        Args:
            text: Free-text clinical narrative or user chat message.

        Returns:
            List of non-overlapping TextMatchSpan objects in text appearance order.
        """
        if not isinstance(text, str) or not text.strip() or self._search_regex is None:
            return []
        if len(text) > MAX_INPUT_LENGTH:
            text = text[:MAX_INPUT_LENGTH]

        normalized_text = unicodedata.normalize("NFKC", text)
        matches: list[TextMatchSpan] = []
        covered_indices: set[int] = set()

        for match in self._search_regex.finditer(normalized_text):
            start, end = match.span()
            # Ensure no overlap with previously matched spans
            if any(i in covered_indices for i in range(start, end)):
                continue

            matched_str = match.group(0)
            clean_matched = _normalize_text(matched_str)
            symptom = self._regex_alias_map.get(clean_matched)
            if symptom is None:
                continue

            for i in range(start, end):
                covered_indices.add(i)

            matches.append(
                TextMatchSpan(
                    canonical_id=symptom.id,
                    canonical_name=symptom.name,
                    body_system=symptom.body_system,
                    matched_term=matched_str,
                    start_char=start,
                    end_char=end,
                )
            )

        matches.sort(key=lambda m: m.start_char)
        return matches

    def get_by_id(self, symptom_id: str) -> CanonicalSymptom | None:
        """Retrieve a canonical symptom by its exact snake_case identifier.

        Args:
            symptom_id: Unique identifier (e.g. "abdominal_pain").

        Returns:
            CanonicalSymptom record or None if not found.
        """
        if not isinstance(symptom_id, str):
            return None
        return self._symptoms_by_id.get(symptom_id.strip().lower())

    def is_canonical_id(self, symptom_id: str) -> bool:
        """Check whether a symptom ID is a recognized canonical identifier.

        Args:
            symptom_id: Identifier string to check.

        Returns:
            True if present in canonical vocabulary, False otherwise.
        """
        return self.get_by_id(symptom_id) is not None

    def list_all(self) -> list[CanonicalSymptom]:
        """List all canonical symptoms in alphabetical order by ID.

        Returns:
            List of all 100 CanonicalSymptom records.
        """
        return sorted(self._symptoms_by_id.values(), key=lambda s: s.id)

    def list_ids(self) -> list[str]:
        """List all canonical symptom IDs in alphabetical order.

        Returns:
            List of 100 unique snake_case IDs.
        """
        return sorted(self._symptoms_by_id.keys())

    def get_by_body_system(self, body_system: str) -> list[CanonicalSymptom]:
        """Filter canonical symptoms by anatomical body system.

        Args:
            body_system: Target body system (e.g. "respiratory", "general").

        Returns:
            List of CanonicalSymptom records belonging to that system.
        """
        clean_bs = body_system.strip().lower()
        return [
            s
            for s in self._symptoms_by_id.values()
            if s.body_system.lower() == clean_bs
        ]

    def list_body_systems(self) -> list[str]:
        """List all known anatomical body system categories.

        Returns:
            Tuple of body system category names.
        """
        return list(self._body_systems)


@lru_cache(maxsize=1)
def get_normalizer() -> SymptomNormalizer:
    """Return the cached singleton instance of SymptomNormalizer.

    Returns:
        Shared, thread-safe SymptomNormalizer instance.
    """
    return SymptomNormalizer()


def normalize_symptom(term: str) -> NormalizedSymptom | None:
    """Normalize a colloquial term or symptom phrase to its canonical record.

    Args:
        term: Symptom phrase or lay term.

    Returns:
        NormalizedSymptom record or None if unrecognized.
    """
    return get_normalizer().normalize(term)


def normalize_symptom_id(term: str) -> str | None:
    """Normalize a colloquial term or symptom phrase to its canonical ID.

    Args:
        term: Symptom phrase or lay term.

    Returns:
        Canonical snake_case symptom ID or None if unrecognized.
    """
    return get_normalizer().normalize_id(term)
