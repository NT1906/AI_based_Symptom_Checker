"""Curated plain-language symptom glossary service.

Responsibilities:
    - Load and index the curated symptom glossary v0 (100 symptoms).
    - Provide fast O(1) lookup of plain-language symptom definitions by ID or term.
    - Support keyword search and body-system filtering for user education.
    - Ensure definitions conform to medical safety (no diagnostic statements,
      no medication dosages, clear red-flag guidance).

Owner: Kavya (knowledge) · Task: S1-KAV-3 · Requirements: FR-18
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.services.knowledge.schemas import GlossaryEntry

MAX_QUERY_LENGTH = 1_000
GLOSSARY_FILE = Path(__file__).parent / "data" / "glossary.json"

_WHITESPACE_COLLAPSE = re.compile(r"\s+")
_PUNCTUATION_STRIP = re.compile(r"^[\s.,!?;:\"'()\[\]{}]+|[\s.,!?;:\"'()\[\]{}]+$")


def _clean_query(text: str) -> str:
    """Normalize unicode, lowercase, collapse whitespace, and strip edges.

    Args:
        text: Raw query string.

    Returns:
        Cleaned lowercase query string.
    """
    normalized = unicodedata.normalize("NFKC", text)
    lowered = normalized.lower()
    collapsed = _WHITESPACE_COLLAPSE.sub(" ", lowered).strip()
    return _PUNCTUATION_STRIP.sub("", collapsed)


class SymptomGlossary:
    """In-memory indexed symptom glossary providing plain-language definitions.

    Thread-safe and deterministic. Entries are validated against the
    :class:`GlossaryEntry` schema and indexed by canonical ID, display name,
    and colloquial lay terms.

    Args:
        data_path: Optional custom path to glossary.json. Defaults to
            the packaged data file in ``data/glossary.json``.

    Raises:
        FileNotFoundError: If the glossary JSON data file cannot be found.
        ValueError: If the glossary format or entries are invalid.
    """

    def __init__(self, data_path: Path | None = None) -> None:
        path = data_path or GLOSSARY_FILE
        if not path.is_file():
            raise FileNotFoundError(f"Glossary dataset not found at {path}")

        with open(path, encoding="utf-8") as f:
            raw_data: dict[str, Any] = json.load(f)

        self._schema_version: str = raw_data.get("schema_version", "1.0")
        self._description: str = raw_data.get("description", "")
        self._disclaimer: str = raw_data.get(
            "disclaimer",
            "This information is for guidance only and is not a medical diagnosis.",
        )

        entries_raw = raw_data.get("entries")
        if not isinstance(entries_raw, list):
            msg = f"Invalid glossary format in {path}: 'entries' must be a list"
            raise ValueError(msg)

        self._entries: list[GlossaryEntry] = []
        self._by_id: dict[str, GlossaryEntry] = {}
        self._by_alias: dict[str, GlossaryEntry] = {}
        self._by_system: dict[str, list[GlossaryEntry]] = {}

        for item in entries_raw:
            entry = GlossaryEntry(
                id=item["id"],
                name=item["name"],
                body_system=item["body_system"],
                plain_definition=item["plain_definition"],
                when_to_seek_care=item["when_to_seek_care"],
                lay_terms=tuple(item.get("lay_terms", ())),
            )
            self._entries.append(entry)

            # Index by canonical ID
            self._by_id[entry.id] = entry

            # Index by normalized name
            clean_name = _clean_query(entry.name)
            if clean_name:
                self._by_alias[clean_name] = entry

            # Index by canonical ID with spaces instead of underscores
            spaced_id = entry.id.replace("_", " ")
            self._by_alias[spaced_id] = entry

            # Index by all lay terms
            for lay in entry.lay_terms:
                clean_lay = _clean_query(lay)
                if clean_lay and clean_lay not in self._by_alias:
                    self._by_alias[clean_lay] = entry

            # Group by body system
            system_list = self._by_system.setdefault(entry.body_system, [])
            system_list.append(entry)

    @property
    def disclaimer(self) -> str:
        """Mandatory patient-safety disclaimer accompanying glossary data."""
        return self._disclaimer

    @property
    def total_entries(self) -> int:
        """Total number of indexed canonical symptom glossary entries."""
        return len(self._entries)

    def get_by_id(self, symptom_id: str) -> GlossaryEntry | None:
        """Retrieve a glossary entry by exact canonical snake_case ID.

        Args:
            symptom_id: Canonical symptom identifier (e.g. ``"chest_pain"``).

        Returns:
            GlossaryEntry if found, or None if unknown.
        """
        if not symptom_id or len(symptom_id) > MAX_QUERY_LENGTH:
            return None
        clean_id = _clean_query(symptom_id).replace(" ", "_")
        return self._by_id.get(clean_id)

    def get_entry(self, query: str) -> GlossaryEntry | None:
        """Resolve a symptom query (ID, display name, or colloquial lay term).

        Performs deterministic normalization to find the best matching
        canonical glossary entry.

        Args:
            query: Clinical ID, name, or colloquial term (e.g. ``"tummy ache"``).

        Returns:
            Matched GlossaryEntry or None if no match found.
        """
        if not query or len(query) > MAX_QUERY_LENGTH:
            return None

        clean = _clean_query(query)
        if not clean:
            return None

        # 1. Exact canonical ID check (with underscore)
        snake_id = clean.replace(" ", "_").replace("-", "_")
        if snake_id in self._by_id:
            return self._by_id[snake_id]

        # 2. Check alias index (name, lay terms, spaced IDs)
        if clean in self._by_alias:
            return self._by_alias[clean]

        # 3. Check stripped hyphens / punctuation variations
        hyphen_normalized = clean.replace("-", " ")
        if hyphen_normalized in self._by_alias:
            return self._by_alias[hyphen_normalized]

        # 4. Fall back to symptom normalizer deterministic lookup
        try:
            from app.services.knowledge.normalizer import get_normalizer

            norm = get_normalizer().normalize(clean)
            if norm and norm.canonical_id in self._by_id:
                return self._by_id[norm.canonical_id]
        except Exception:
            pass

        return None

    def get_definition(self, query: str) -> str | None:
        """Retrieve the plain-language definition string for a symptom.

        Args:
            query: Symptom ID, name, or colloquial lay term.

        Returns:
            Plain-language definition text, or None if the symptom is unknown.
        """
        entry = self.get_entry(query)
        return entry.plain_definition if entry else None

    def list_entries(self, body_system: str | None = None) -> list[GlossaryEntry]:
        """List glossary entries, optionally filtered by anatomical body system.

        Args:
            body_system: Optional body system key (e.g. ``"gastrointestinal"``).

        Returns:
            List of GlossaryEntry objects sorted alphabetically by name.
        """
        if body_system:
            clean_sys = _clean_query(body_system)
            entries = self._by_system.get(clean_sys, [])
        else:
            entries = list(self._entries)

        return sorted(entries, key=lambda e: e.name.lower())

    def search(self, query: str, limit: int = 5) -> list[GlossaryEntry]:
        """Search glossary entries by keyword across names, lay terms, and definitions.

        Results are ranked by match specificity:
            1. Exact match on ID, canonical name, or lay term.
            2. Prefix match on name or lay term.
            3. Substring match in name or lay terms.
            4. Substring match in plain definition.

        Args:
            query: Free-text search term.
            limit: Maximum number of results to return (default 5, max 50).

        Returns:
            Ranked list of unique matching GlossaryEntry objects.
        """
        if not query or len(query) > MAX_QUERY_LENGTH or limit < 1:
            return []

        clean = _clean_query(query)
        if not clean:
            return []

        max_results = min(limit, 50)
        exact_matches: list[GlossaryEntry] = []
        prefix_matches: list[GlossaryEntry] = []
        term_matches: list[GlossaryEntry] = []
        definition_matches: list[GlossaryEntry] = []
        seen_ids: set[str] = set()

        # Check direct resolution first
        direct = self.get_entry(clean)
        if direct:
            exact_matches.append(direct)
            seen_ids.add(direct.id)

        for entry in self._entries:
            if entry.id in seen_ids:
                continue

            name_lower = entry.name.lower()
            id_lower = entry.id.lower()

            # Check prefix matches
            if name_lower.startswith(clean) or id_lower.startswith(clean):
                prefix_matches.append(entry)
                seen_ids.add(entry.id)
                continue

            lay_prefix = any(lt.lower().startswith(clean) for lt in entry.lay_terms)
            if lay_prefix:
                prefix_matches.append(entry)
                seen_ids.add(entry.id)
                continue

            # Check substring in name or lay terms
            has_term_match = clean in name_lower or any(
                clean in lt.lower() for lt in entry.lay_terms
            )
            if has_term_match:
                term_matches.append(entry)
                seen_ids.add(entry.id)
                continue

            # Check definition substring
            if clean in entry.plain_definition.lower():
                definition_matches.append(entry)
                seen_ids.add(entry.id)

        combined = exact_matches + prefix_matches + term_matches + definition_matches
        return combined[:max_results]


@lru_cache(maxsize=1)
def get_glossary() -> SymptomGlossary:
    """Return the cached singleton SymptomGlossary instance.

    Returns:
        Shared, immutable SymptomGlossary instance.
    """
    return SymptomGlossary()


def lookup_glossary(query: str) -> GlossaryEntry | None:
    """Convenience functional lookup for a symptom glossary entry.

    Args:
        query: Symptom ID, display name, or colloquial lay term.

    Returns:
        GlossaryEntry if found, otherwise None.
    """
    return get_glossary().get_entry(query)


def get_symptom_definition(query: str) -> str | None:
    """Convenience function retrieving the plain definition of a symptom.

    Args:
        query: Symptom ID, display name, or colloquial lay term.

    Returns:
        Plain-language definition text, or None if unknown.
    """
    return get_glossary().get_definition(query)
