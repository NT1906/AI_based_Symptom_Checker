"""Unit tests for the deterministic symptom normalization service.

Covers:
    - Exact canonical ID, spaced ID, and display name resolution.
    - Colloquial lay terms in English and Indian Hinglish.
    - Free-text multi-symptom extraction with word boundaries and longest match.
    - Vocabulary query interfaces, body systems, and boundary validation.
    - Parity with the canonical vocabulary dataset in ml/datasets/symptoms/.

Owner: Kavya (knowledge) · Task: S1-KAV-1 · Requirements: FR-03
"""

import json
from pathlib import Path

import pytest
from app.services.knowledge.normalizer import (
    SymptomNormalizer,
    get_normalizer,
    normalize_symptom,
    normalize_symptom_id,
)
from app.services.knowledge.schemas import CanonicalSymptom

REPO_ROOT = Path(__file__).parents[4]
ML_SYMPTOMS_PATH = REPO_ROOT / "ml" / "datasets" / "symptoms" / "symptoms.json"


@pytest.fixture(scope="module")
def normalizer() -> SymptomNormalizer:
    """Fixture providing a fresh or cached SymptomNormalizer instance."""
    return get_normalizer()


# ---------------------------------------------------------------------------
# 1. Happy Paths: Exact & Colloquial Lay-Term Normalization
# ---------------------------------------------------------------------------


class TestNormalizerHappyPaths:
    """Tests verifying accurate resolution of canonical names and lay terms."""

    def test_normalizes_canonical_snake_case_id(
        self, normalizer: SymptomNormalizer
    ) -> None:
        """Exact canonical snake_case IDs must normalize to themselves."""
        res = normalizer.normalize("abdominal_pain")
        assert res is not None
        assert res.canonical_id == "abdominal_pain"
        assert res.canonical_name == "Abdominal (stomach) pain"
        assert res.body_system == "gastrointestinal"
        assert res.confidence == 1.0

    def test_normalizes_canonical_id_with_spaces(
        self, normalizer: SymptomNormalizer
    ) -> None:
        """Canonical IDs with underscores replaced by spaces must resolve."""
        res = normalizer.normalize("abdominal pain")
        assert res is not None
        assert res.canonical_id == "abdominal_pain"

    def test_normalizes_canonical_display_name(
        self, normalizer: SymptomNormalizer
    ) -> None:
        """Display names as listed in conditions.json must normalize."""
        res = normalizer.normalize("Chest pain")
        assert res is not None
        assert res.canonical_id == "chest_pain"

    @pytest.mark.parametrize(
        ("lay_term", "expected_id"),
        [
            ("tummy ache", "abdominal_pain"),  # Task explicit example
            ("stomach ache", "abdominal_pain"),
            ("belly ache", "abdominal_pain"),
            ("high temperature", "fever"),
            ("running a temperature", "fever"),
            ("head pain", "headache"),
            ("head hurting", "headache"),
            ("head is pounding", "headache"),
            ("muscle pain", "body_aches"),
            ("body pain", "body_aches"),
            ("throwing up", "vomiting"),
            ("feeling sick", "nausea"),
            ("shortness of breath", "shortness_of_breath"),
            ("difficulty breathing", "shortness_of_breath"),
            ("chest whistling", "wheezing"),
            ("itchy skin", "itchy_skin"),
            ("burning when peeing", "burning_urination"),
            ("hurts to pee", "burning_urination"),
            ("sour taste in mouth", "acid_regurgitation"),
            ("acidity", "heartburn"),
        ],
    )
    def test_normalizes_english_lay_terms(
        self, normalizer: SymptomNormalizer, lay_term: str, expected_id: str
    ) -> None:
        """Common English colloquial terms must map to their canonical IDs."""
        res = normalizer.normalize(lay_term)
        assert res is not None
        assert res.canonical_id == expected_id

    @pytest.mark.parametrize(
        ("hinglish_term", "expected_id"),
        [
            ("bukhar", "fever"),
            ("tez bukhar", "fever"),
            ("badan garam", "fever"),
            ("badan dard", "body_aches"),
            ("pet me dard", "abdominal_pain"),
            ("pet dard", "abdominal_pain"),
            ("ulti", "vomiting"),
            ("chhati me dard", "chest_pain"),
            ("kamzori", "fatigue"),
            ("thakan", "fatigue"),
            ("gale me dard", "sore_throat"),
            ("peshab ka rang gehra", "dark_urine"),
            ("kamar dard", "lower_back_pain"),
            ("chakkar", "dizziness"),
            ("khansi", "cough"),
        ],
    )
    def test_normalizes_hinglish_colloquial_terms(
        self,
        normalizer: SymptomNormalizer,
        hinglish_term: str,
        expected_id: str,
    ) -> None:
        """Indian transliterated Hinglish terms must map to canonical IDs."""
        res = normalizer.normalize(hinglish_term)
        assert res is not None
        assert res.canonical_id == expected_id

    def test_normalize_id_helper_returns_string(
        self, normalizer: SymptomNormalizer
    ) -> None:
        """The helper normalize_id must return a string directly."""
        assert normalizer.normalize_id("tummy ache") == "abdominal_pain"
        assert normalizer.normalize_id("bukhar") == "fever"

    def test_module_level_helpers_delegate_correctly(self) -> None:
        """Module-level helpers normalize_symptom and normalize_symptom_id must work."""
        res = normalize_symptom("tummy ache")
        assert res is not None
        assert res.canonical_id == "abdominal_pain"

        str_id = normalize_symptom_id("tummy ache")
        assert str_id == "abdominal_pain"


# ---------------------------------------------------------------------------
# 2. Text Normalization, Formatting & Case Insensitivity
# ---------------------------------------------------------------------------


class TestNormalizerTextSanitization:
    """Tests verifying robust handling of whitespace, casing, and punctuation."""

    def test_handles_mixed_case(self, normalizer: SymptomNormalizer) -> None:
        """Mixed casing should be normalized seamlessly."""
        assert normalizer.normalize_id("TuMMy AcHe") == "abdominal_pain"
        assert normalizer.normalize_id("BUKHAR") == "fever"

    def test_handles_peripheral_whitespace(self, normalizer: SymptomNormalizer) -> None:
        """Leading, trailing, and redundant internal whitespace must collapse."""
        assert normalizer.normalize_id("   tummy     ache    ") == "abdominal_pain"

    def test_handles_trailing_and_enclosing_punctuation(
        self, normalizer: SymptomNormalizer
    ) -> None:
        """Trailing or surrounding punctuation must not block resolution."""
        assert normalizer.normalize_id("tummy ache!") == "abdominal_pain"
        assert normalizer.normalize_id("(headache)") == "headache"
        assert normalizer.normalize_id("'fever'") == "fever"
        assert normalizer.normalize_id('"cough"') == "cough"

    def test_handles_hyphenated_phrases(self, normalizer: SymptomNormalizer) -> None:
        """Hyphenated variations should resolve cleanly."""
        assert normalizer.normalize_id("stomach-ache") == "abdominal_pain"


# ---------------------------------------------------------------------------
# 3. Free-Text Symptom Extraction
# ---------------------------------------------------------------------------


class TestTextSymptomExtraction:
    """Tests extracting multiple canonical symptoms from free-text messages."""

    def test_extracts_single_symptom_with_offsets(
        self, normalizer: SymptomNormalizer
    ) -> None:
        """Extracts single symptom with precise character boundaries."""
        text = "I have a severe headache since yesterday"
        spans = normalizer.extract_symptoms_from_text(text)
        assert len(spans) == 1
        assert spans[0].canonical_id == "headache"
        assert spans[0].canonical_name == "Headache"
        assert spans[0].start_char == 16
        assert spans[0].end_char == 24

    def test_extracts_multiple_symptoms_in_appearance_order(
        self, normalizer: SymptomNormalizer
    ) -> None:
        """Extracts multiple distinct symptoms ordered by position in text."""
        text = "I have fever with chills and aching all over"
        spans = normalizer.extract_symptoms_from_text(text)
        canonical_ids = [s.canonical_id for s in spans]
        assert canonical_ids == ["fever", "chills", "body_aches"]

    def test_prioritizes_longest_compound_match(
        self, normalizer: SymptomNormalizer
    ) -> None:
        """Compound terms like 'sudden severe headache' match over 'headache'."""
        text = "I woke up with sudden severe headache today"
        spans = normalizer.extract_symptoms_from_text(text)
        assert len(spans) == 1
        assert spans[0].canonical_id == "sudden_severe_headache"

    def test_word_boundary_isolation_prevents_false_positives(
        self, normalizer: SymptomNormalizer
    ) -> None:
        """Substrings within unrelated words must not falsely match."""
        # 'sweat' inside 'sweater', 'cold' inside 'scold'
        text = "I bought a warm sweater because someone scolds me"
        spans = normalizer.extract_symptoms_from_text(text)
        assert spans == []

    def test_extracts_hinglish_multi_symptom_sentence(
        self, normalizer: SymptomNormalizer
    ) -> None:
        """Extracts Hinglish terms in mixed Hindi-English sentences."""
        text = "mujhe tez bukhar hai aur pet me dard ho raha hai"
        spans = normalizer.extract_symptoms_from_text(text)
        canonical_ids = [s.canonical_id for s in spans]
        assert "fever" in canonical_ids
        assert "abdominal_pain" in canonical_ids


# ---------------------------------------------------------------------------
# 4. Vocabulary Lookups & Metadata Interfaces
# ---------------------------------------------------------------------------


class TestVocabularyInterfaces:
    """Tests querying vocabulary metadata by ID and anatomical system."""

    def test_get_by_id_returns_canonical_symptom(
        self, normalizer: SymptomNormalizer
    ) -> None:
        """get_by_id returns full CanonicalSymptom with lay terms."""
        symptom = normalizer.get_by_id("fever")
        assert isinstance(symptom, CanonicalSymptom)
        assert symptom.id == "fever"
        assert symptom.name == "Fever"
        assert symptom.body_system == "general"
        assert "bukhar" in symptom.lay_terms

    def test_is_canonical_id(self, normalizer: SymptomNormalizer) -> None:
        """is_canonical_id validates existing and non-existing IDs."""
        assert normalizer.is_canonical_id("fever") is True
        assert normalizer.is_canonical_id("chest_pain") is True
        assert normalizer.is_canonical_id("non_existent_symptom") is False
        assert normalizer.is_canonical_id("") is False

    def test_list_all_contains_one_hundred_symptoms(
        self, normalizer: SymptomNormalizer
    ) -> None:
        """Vocabulary must contain all 100 canonical symptoms."""
        all_symptoms = normalizer.list_all()
        assert len(all_symptoms) == 100
        assert all(isinstance(s, CanonicalSymptom) for s in all_symptoms)

    def test_list_ids_contains_one_hundred_sorted_ids(
        self, normalizer: SymptomNormalizer
    ) -> None:
        """list_ids must return all 100 unique IDs sorted alphabetically."""
        ids = normalizer.list_ids()
        assert len(ids) == 100
        assert ids == sorted(ids)

    def test_list_body_systems(self, normalizer: SymptomNormalizer) -> None:
        """list_body_systems must return 11 standard body systems."""
        systems = normalizer.list_body_systems()
        assert len(systems) == 11
        assert "gastrointestinal" in systems
        assert "neurological" in systems
        assert "cardiovascular" in systems

    def test_get_by_body_system(self, normalizer: SymptomNormalizer) -> None:
        """Filtering by body system returns only matching symptoms."""
        cardio = normalizer.get_by_body_system("cardiovascular")
        assert len(cardio) > 0
        assert all(s.body_system == "cardiovascular" for s in cardio)
        ids = {s.id for s in cardio}
        assert "chest_pain" in ids


# ---------------------------------------------------------------------------
# 5. Edge Cases and Error Handling
# ---------------------------------------------------------------------------


class TestNormalizerEdgeCases:
    """Tests handling empty inputs, unknown terms, and constructor errors."""

    @pytest.mark.parametrize("invalid_input", ["", "   ", "???", "!!!", None])
    def test_returns_none_for_empty_or_invalid_query(
        self, normalizer: SymptomNormalizer, invalid_input: str | None
    ) -> None:
        """Blank, whitespace-only, punctuation-only, or None inputs return None."""
        assert normalizer.normalize(invalid_input) is None  # type: ignore[arg-type]

    def test_returns_none_for_unknown_phrase(
        self, normalizer: SymptomNormalizer
    ) -> None:
        """Unrecognized colloquial input returns None without raising."""
        assert normalizer.normalize("quantum computing error") is None
        assert normalizer.normalize_id("quantum computing error") is None

    def test_extract_from_empty_text_returns_empty_list(
        self, normalizer: SymptomNormalizer
    ) -> None:
        """Empty free-text extraction returns an empty list."""
        assert normalizer.extract_symptoms_from_text("") == []
        assert normalizer.extract_symptoms_from_text("   ") == []

    def test_truncates_oversized_input_safely(
        self, normalizer: SymptomNormalizer
    ) -> None:
        """Inputs exceeding max length limit are bounded safely."""
        oversized = "headache " * 2000
        # Should not raise recursion or regex overflow errors
        spans = normalizer.extract_symptoms_from_text(oversized)
        assert len(spans) > 0

    def test_raises_file_not_found_on_missing_path(self, tmp_path: Path) -> None:
        """Non-existent path in constructor raises FileNotFoundError."""
        missing = tmp_path / "non_existent.json"
        with pytest.raises(FileNotFoundError):
            SymptomNormalizer(data_path=missing)

    def test_raises_value_error_on_empty_symptoms_dataset(self, tmp_path: Path) -> None:
        """Empty symptoms list in JSON raises ValueError."""
        empty_file = tmp_path / "empty_symptoms.json"
        empty_file.write_text(json.dumps({"symptoms": []}), encoding="utf-8")
        with pytest.raises(ValueError, match="contains no symptoms"):
            SymptomNormalizer(data_path=empty_file)


# ---------------------------------------------------------------------------
# 6. Dataset Parity Test (ml/datasets/symptoms/symptoms.json sync)
# ---------------------------------------------------------------------------


class TestVocabularyParity:
    """Verifies packaged knowledge data matches canonical ML dataset card."""

    def test_packaged_data_matches_ml_dataset(self) -> None:
        """The data packaged in services/knowledge must match ml/datasets/symptoms."""
        packaged_path = (
            Path(__file__).parents[3]
            / "app"
            / "services"
            / "knowledge"
            / "data"
            / "symptoms.json"
        )
        assert packaged_path.exists(), f"Packaged data missing at {packaged_path}"

        if ML_SYMPTOMS_PATH.exists():
            packaged_bytes = packaged_path.read_bytes()
            ml_bytes = ML_SYMPTOMS_PATH.read_bytes()
            assert packaged_bytes == ml_bytes, (
                "server/app/services/knowledge/data/symptoms.json "
                "out of sync with ml/datasets/symptoms/"
            )
