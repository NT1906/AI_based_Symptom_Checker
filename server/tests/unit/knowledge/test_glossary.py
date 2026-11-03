"""Unit tests for the curated plain-language symptom glossary service.

Covers:
    - Direct lookup by canonical ID, display name, and lay terms.
    - Plain-definition retrieval via functional helpers and class methods.
    - Full search capabilities with prefix, substring, and definition matching.
    - Body-system filtering and catalog listing.
    - Clinical safety standards and Dimple review compliance (non-diagnostic wording).
    - Complete dataset parity and integrity (100 symptoms aligned with symptoms.json).
    - Edge cases: whitespace, casing, punctuation, long queries, and missing entries.

Owner: Kavya (knowledge) · Task: S1-KAV-3 · Requirements: FR-18
"""

import json
from pathlib import Path

import pytest
from app.services.knowledge.glossary import (
    SymptomGlossary,
    get_glossary,
    get_symptom_definition,
    lookup_glossary,
)
from app.services.knowledge.schemas import GlossaryEntry

REPO_ROOT = Path(__file__).parents[4]
SYMPTOMS_DATA_PATH = (
    REPO_ROOT / "server" / "app" / "services" / "knowledge" / "data" / "symptoms.json"
)
GLOSSARY_DATA_PATH = (
    REPO_ROOT / "server" / "app" / "services" / "knowledge" / "data" / "glossary.json"
)


@pytest.fixture(scope="module")
def glossary() -> SymptomGlossary:
    """Fixture providing a cached SymptomGlossary instance."""
    return get_glossary()


# ---------------------------------------------------------------------------
# 1. Happy Paths: Exact, Name & Lay-Term Lookups
# ---------------------------------------------------------------------------


class TestGlossaryHappyPaths:
    """Tests verifying accurate retrieval of plain-language glossary entries."""

    @pytest.mark.parametrize(
        "symptom_id",
        [
            "fever",
            "headache",
            "chest_pain",
            "nausea",
            "shortness_of_breath",
            "dizziness",
            "fatigue",
            "abdominal_pain",
            "skin_rash",
            "thoughts_of_self_harm",
        ],
    )
    def test_lookup_by_canonical_snake_case_id(
        self, glossary: SymptomGlossary, symptom_id: str
    ) -> None:
        """Lookup by exact canonical ID returns correct GlossaryEntry."""
        entry = glossary.get_by_id(symptom_id)
        assert entry is not None
        assert isinstance(entry, GlossaryEntry)
        assert entry.id == symptom_id
        assert len(entry.plain_definition) > 10
        assert len(entry.when_to_seek_care) > 10

    @pytest.mark.parametrize(
        ("query", "expected_id"),
        [
            ("chest pain", "chest_pain"),
            ("lower back pain", "lower_back_pain"),
            ("shortness of breath", "shortness_of_breath"),
            ("runny nose", "runny_nose"),
            ("painful swallowing", "painful_swallowing"),
        ],
    )
    def test_lookup_by_spaced_id(
        self, glossary: SymptomGlossary, query: str, expected_id: str
    ) -> None:
        """Lookup by spaced identifier resolves to canonical entry."""
        entry = glossary.get_entry(query)
        assert entry is not None
        assert entry.id == expected_id

    @pytest.mark.parametrize(
        ("query", "expected_id"),
        [
            ("Fever", "fever"),
            ("Headache", "headache"),
            ("Chills or shivering", "chills"),
            ("Tiredness or weakness", "fatigue"),
            ("Abdominal (stomach) pain", "abdominal_pain"),
        ],
    )
    def test_lookup_by_canonical_display_name(
        self, glossary: SymptomGlossary, query: str, expected_id: str
    ) -> None:
        """Lookup by clinical display name resolves to canonical entry."""
        entry = glossary.get_entry(query)
        assert entry is not None
        assert entry.id == expected_id

    @pytest.mark.parametrize(
        ("lay_term", "expected_id"),
        [
            ("high temperature", "fever"),
            ("throwing up", "vomiting"),
            ("loose motions", "diarrhea"),
            ("tummy ache", "abdominal_pain"),
            ("acidity", "heartburn"),
            ("whistling sound when breathing", "wheezing"),
            ("burning when peeing", "burning_urination"),
            ("shivering", "chills"),
            ("heart racing", "palpitations"),
            ("stiff neck", "stiff_neck"),
        ],
    )
    def test_lookup_by_colloquial_english_lay_terms(
        self, glossary: SymptomGlossary, lay_term: str, expected_id: str
    ) -> None:
        """Colloquial English phrases resolve to canonical glossary entries."""
        entry = glossary.get_entry(lay_term)
        assert entry is not None
        assert entry.id == expected_id

    @pytest.mark.parametrize(
        ("hinglish_phrase", "expected_id"),
        [
            ("bukhar", "fever"),
            ("tez bukhar", "fever"),
            ("sar dard", "headache"),
            ("pet me dard", "abdominal_pain"),
            ("kamzori", "fatigue"),
            ("peshab me jalan", "burning_urination"),
            ("chhati me dard", "chest_pain"),
            ("khansi", "cough"),
            ("saans phoolna", "shortness_of_breath"),
            ("aankh laal", "red_eye"),
        ],
    )
    def test_lookup_by_transliterated_hinglish_terms(
        self, glossary: SymptomGlossary, hinglish_phrase: str, expected_id: str
    ) -> None:
        """Transliterated Hinglish queries resolve to canonical glossary entries."""
        entry = glossary.get_entry(hinglish_phrase)
        assert entry is not None
        assert entry.id == expected_id

    def test_get_definition_returns_plain_text(self, glossary: SymptomGlossary) -> None:
        """get_definition returns plain text for valid canonical query."""
        defn = glossary.get_definition("nausea")
        assert defn is not None
        assert "queasy" in defn.lower() or "vomit" in defn.lower()

    def test_convenience_functions(self) -> None:
        """Module-level convenience functions work identically to methods."""
        entry = lookup_glossary("chest_pain")
        assert entry is not None
        assert entry.id == "chest_pain"

        defn = get_symptom_definition("fever")
        assert defn is not None
        assert "temperature" in defn.lower()


# ---------------------------------------------------------------------------
# 2. Search & Filtering Capabilities
# ---------------------------------------------------------------------------


class TestGlossarySearchAndFilter:
    """Tests verifying keyword search and body-system categorization."""

    def test_search_exact_match_ranks_first(self, glossary: SymptomGlossary) -> None:
        """Exact match appears as the first result in search results."""
        results = glossary.search("cough", limit=5)
        assert len(results) > 0
        assert results[0].id == "cough"

    def test_search_prefix_match(self, glossary: SymptomGlossary) -> None:
        """Prefix search finds matching symptoms."""
        results = glossary.search("palp", limit=5)
        ids = [r.id for r in results]
        assert "palpitations" in ids

    def test_search_definition_content(self, glossary: SymptomGlossary) -> None:
        """Search finds words mentioned within plain-language definitions."""
        results = glossary.search("shivering", limit=5)
        ids = [r.id for r in results]
        assert "chills" in ids

    def test_search_limit_is_respected(self, glossary: SymptomGlossary) -> None:
        """Result count does not exceed specified limit."""
        results = glossary.search("pain", limit=3)
        assert len(results) <= 3

    def test_list_entries_returns_all_100_entries(
        self, glossary: SymptomGlossary
    ) -> None:
        """Unfiltered listing returns all 100 canonical symptom entries."""
        entries = glossary.list_entries()
        assert len(entries) == 100

    @pytest.mark.parametrize(
        ("system", "expected_count"),
        [
            ("general", 16),
            ("neurological", 14),
            ("ent", 10),
            ("respiratory", 7),
            ("eye", 6),
            ("cardiovascular", 3),
            ("gastrointestinal", 15),
            ("urinary", 6),
            ("musculoskeletal", 5),
            ("skin", 17),
            ("mental_health", 1),
        ],
    )
    def test_list_entries_filtered_by_body_system(
        self, glossary: SymptomGlossary, system: str, expected_count: int
    ) -> None:
        """Filtering by body system returns exact count matching system."""
        entries = glossary.list_entries(body_system=system)
        assert len(entries) == expected_count
        assert all(e.body_system == system for e in entries)


# ---------------------------------------------------------------------------
# 3. Medical Safety & Dimple Review Standards
# ---------------------------------------------------------------------------


class TestGlossarySafetyAndWording:
    """Tests ensuring strict compliance with clinical-safety rules (Rule §2)."""

    FORBIDDEN_DIAGNOSTIC_PHRASES = (
        "you have",
        "you are diagnosed",
        "diagnosis:",
        "you suffer from",
        "we prescribe",
        "take 500mg",
        "take antibiotics",
        "take paracetamol",
        "mg daily",
    )

    def test_mandatory_disclaimer_present(self, glossary: SymptomGlossary) -> None:
        """Glossary must include clear non-diagnostic patient disclaimer."""
        assert glossary.disclaimer is not None
        assert "not a medical diagnosis" in glossary.disclaimer.lower()

    def test_no_forbidden_diagnostic_phrasing_in_definitions(
        self, glossary: SymptomGlossary
    ) -> None:
        """No entry may state diagnostic certainty or drug prescriptions."""
        for entry in glossary.list_entries():
            defn_lower = entry.plain_definition.lower()
            for phrase in self.FORBIDDEN_DIAGNOSTIC_PHRASES:
                assert phrase not in defn_lower, (
                    f"Forbidden phrase '{phrase}' found in {entry.id} definition"
                )

    def test_all_entries_have_clinical_care_guidance(
        self, glossary: SymptomGlossary
    ) -> None:
        """Every entry must provide actionable guidance on when to seek care."""
        for entry in glossary.list_entries():
            assert entry.when_to_seek_care.strip() != ""
            assert len(entry.when_to_seek_care) >= 20

    @pytest.mark.parametrize(
        "emergency_symptom_id",
        [
            "chest_pain",
            "sudden_severe_headache",
            "facial_droop",
            "one_sided_weakness",
            "slurred_speech",
            "sudden_vision_loss",
            "seizure",
            "throat_or_tongue_swelling",
            "shortness_of_breath",
            "vomiting_blood",
            "black_or_bloody_stool",
            "non_blanching_rash",
            "thoughts_of_self_harm",
        ],
    )
    def test_critical_red_flags_highlight_emergency_number(
        self, glossary: SymptomGlossary, emergency_symptom_id: str
    ) -> None:
        """Critical red-flag symptoms must explicitly highlight emergency care (112)."""
        entry = glossary.get_by_id(emergency_symptom_id)
        assert entry is not None
        guidance = entry.when_to_seek_care.lower()
        has_emergency_keyword = (
            "112" in guidance
            or "emergency" in guidance
            or "crisis" in guidance
            or "immediate" in guidance
        )
        assert has_emergency_keyword, (
            f"Emergency symptom {emergency_symptom_id} missing emergency indicator"
        )


# ---------------------------------------------------------------------------
# 4. Dataset Parity & Integrity
# ---------------------------------------------------------------------------


class TestGlossaryDatasetIntegrity:
    """Tests verifying 100% parity between glossary.json and canonical symptoms.json."""

    def test_parity_with_symptoms_json(self) -> None:
        """Every symptom in symptoms.json must have an entry in glossary.json."""
        with open(SYMPTOMS_DATA_PATH, encoding="utf-8") as f:
            symptoms_data = json.load(f)
        with open(GLOSSARY_DATA_PATH, encoding="utf-8") as f:
            glossary_data = json.load(f)

        symptom_ids = {s["id"] for s in symptoms_data["symptoms"]}
        glossary_ids = {e["id"] for e in glossary_data["entries"]}

        assert len(symptom_ids) == 100
        assert len(glossary_ids) == 100
        assert symptom_ids == glossary_ids

    def test_no_duplicate_ids(self) -> None:
        """Glossary entries must have unique canonical IDs."""
        with open(GLOSSARY_DATA_PATH, encoding="utf-8") as f:
            data = json.load(f)
        ids = [e["id"] for e in data["entries"]]
        assert len(ids) == len(set(ids))

    def test_schema_version_and_metadata(self) -> None:
        """Glossary JSON metadata must conform to schema requirements."""
        with open(GLOSSARY_DATA_PATH, encoding="utf-8") as f:
            data = json.load(f)
        assert data.get("schema_version") == "1.0"
        assert len(data.get("description", "")) > 10
        assert len(data.get("disclaimer", "")) > 10


# ---------------------------------------------------------------------------
# 5. Edge Cases & Boundary Handling
# ---------------------------------------------------------------------------


class TestGlossaryEdgeCases:
    """Tests verifying graceful handling of malformed queries and edge conditions."""

    def test_case_insensitivity(self, glossary: SymptomGlossary) -> None:
        """Lookups are completely case-insensitive."""
        res_upper = glossary.get_entry("FEVER")
        res_mixed = glossary.get_entry("ChEsT pAiN")
        assert res_upper is not None and res_upper.id == "fever"
        assert res_mixed is not None and res_mixed.id == "chest_pain"

    def test_whitespace_and_punctuation_stripping(
        self, glossary: SymptomGlossary
    ) -> None:
        """Surrounding whitespace and punctuation are cleanly handled."""
        res1 = glossary.get_entry("  fever!  ")
        res2 = glossary.get_entry("?nausea.")
        res3 = glossary.get_entry("[chest_pain]")
        assert res1 is not None and res1.id == "fever"
        assert res2 is not None and res2.id == "nausea"
        assert res3 is not None and res3.id == "chest_pain"

    def test_unknown_query_returns_none(self, glossary: SymptomGlossary) -> None:
        """Unknown or hallucinated symptoms return None without raising."""
        assert glossary.get_entry("completely_unknown_condition") is None
        assert glossary.get_definition("fake_symptom") is None
        assert glossary.get_by_id("non_existent_id") is None

    def test_empty_and_whitespace_only_query(self, glossary: SymptomGlossary) -> None:
        """Empty or whitespace-only queries return None safely."""
        assert glossary.get_entry("") is None
        assert glossary.get_entry("   ") is None
        assert glossary.get_definition("") is None
        assert glossary.get_by_id("") is None

    def test_excessively_long_query(self, glossary: SymptomGlossary) -> None:
        """Queries exceeding MAX_QUERY_LENGTH are rejected safely."""
        huge_query = "headache " * 500
        assert glossary.get_entry(huge_query) is None
        assert glossary.search(huge_query) == []

    def test_search_empty_or_unknown_query(self, glossary: SymptomGlossary) -> None:
        """Empty search or no matches returns empty list."""
        assert glossary.search("") == []
        assert glossary.search("   ") == []
        assert glossary.search("xyz123randomnonexistent") == []

    def test_missing_data_file_raises_error(self, tmp_path: Path) -> None:
        """Non-existent path raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            SymptomGlossary(data_path=tmp_path / "missing.json")

    def test_invalid_json_format_raises_error(self, tmp_path: Path) -> None:
        """Invalid format (missing 'entries' list) raises ValueError."""
        bad_json = tmp_path / "bad.json"
        bad_json.write_text(json.dumps({"entries": "not-a-list"}))
        with pytest.raises(ValueError, match="must be a list"):
            SymptomGlossary(data_path=bad_json)
