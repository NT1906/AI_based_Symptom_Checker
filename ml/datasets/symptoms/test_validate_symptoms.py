"""Tests for the symptom vocabulary dataset and its validator.

Covers the shipped ``symptoms.json`` (it must be valid, aligned with
``conditions.json``, and meet the S0-KAV-1 acceptance criteria) and the
validator itself (each kind of data mistake must be reported).

Owner: Kavya (AI/ML, Database) · Task: S0-KAV-1 · Requirements: FR-03
"""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from validate_symptoms import (
    BODY_SYSTEMS,
    load_json,
    main,
    validate_symptoms,
)

CONDITIONS_PATH = Path(__file__).parent.parent / "conditions" / "conditions.json"


@pytest.fixture(scope="module")
def shipped() -> dict[str, Any]:
    """The symptom vocabulary as committed in the repository."""
    return load_json(Path(__file__).with_name("symptoms.json"))


@pytest.fixture(scope="module")
def conditions() -> dict[str, Any]:
    """The condition dataset as committed in the repository."""
    return load_json(CONDITIONS_PATH)


@pytest.fixture(scope="module")
def condition_symptom_ids(conditions: dict[str, Any]) -> set[str]:
    """All symptom IDs from the condition dataset."""
    return {s["id"] for s in conditions["symptoms"]}


@pytest.fixture(scope="module")
def condition_symptom_lookup(conditions: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Symptom ID → {name, body_system} from conditions.json."""
    return {
        s["id"]: {"name": s["name"], "body_system": s["body_system"]}
        for s in conditions["symptoms"]
    }


@pytest.fixture
def dataset(shipped: dict[str, Any]) -> dict[str, Any]:
    """A private copy of the vocabulary that a test may break."""
    return copy.deepcopy(shipped)


def _symptom(data: dict[str, Any], symptom_id: str) -> dict[str, Any]:
    """Return the symptom record with the requested ID, or raise StopIteration."""
    return next(s for s in data["symptoms"] if s["id"] == symptom_id)


# ---------------------------------------------------------------------------
# the shipped dataset
# ---------------------------------------------------------------------------


class TestShippedDataset:
    """Tests that the committed symptoms.json passes all rules."""

    def test_has_no_errors(self, shipped: dict[str, Any]) -> None:
        """The shipped dataset must pass all validation rules."""
        assert validate_symptoms(shipped) == []

    def test_has_one_hundred_symptoms(self, shipped: dict[str, Any]) -> None:
        """The vocabulary must contain exactly 100 symptoms."""
        assert len(shipped["symptoms"]) == 100

    def test_covers_every_condition_symptom(
        self,
        shipped: dict[str, Any],
        condition_symptom_ids: set[str],
    ) -> None:
        """Every symptom ID from conditions.json must be present."""
        vocab_ids = {s["id"] for s in shipped["symptoms"]}
        missing = condition_symptom_ids - vocab_ids
        assert not missing, f"Missing from vocabulary: {sorted(missing)}"

    def test_ids_match_conditions_exactly(
        self,
        shipped: dict[str, Any],
        condition_symptom_ids: set[str],
    ) -> None:
        """No extra IDs beyond what conditions.json defines."""
        vocab_ids = {s["id"] for s in shipped["symptoms"]}
        extra = vocab_ids - condition_symptom_ids
        assert not extra, f"Extra in vocabulary: {sorted(extra)}"

    def test_names_match_conditions(
        self,
        shipped: dict[str, Any],
        condition_symptom_lookup: dict[str, dict[str, str]],
    ) -> None:
        """Display names must be identical to conditions.json."""
        for symptom in shipped["symptoms"]:
            cond = condition_symptom_lookup[symptom["id"]]
            assert symptom["name"] == cond["name"], symptom["id"]

    def test_body_systems_match_conditions(
        self,
        shipped: dict[str, Any],
        condition_symptom_lookup: dict[str, dict[str, str]],
    ) -> None:
        """Body systems must be identical to conditions.json."""
        for symptom in shipped["symptoms"]:
            cond = condition_symptom_lookup[symptom["id"]]
            assert symptom["body_system"] == cond["body_system"], symptom["id"]

    def test_every_symptom_has_lay_terms(self, shipped: dict[str, Any]) -> None:
        """Every symptom must have at least one lay term."""
        empty = [s["id"] for s in shipped["symptoms"] if not s.get("lay_terms")]
        assert not empty, f"Symptoms without lay terms: {empty}"

    def test_all_body_systems_represented(self, shipped: dict[str, Any]) -> None:
        """The vocabulary must cover every known body system."""
        systems = {s["body_system"] for s in shipped["symptoms"]}
        assert systems == BODY_SYSTEMS

    def test_no_ambiguous_lay_terms(self, shipped: dict[str, Any]) -> None:
        """No lay term should map to more than one symptom."""
        term_map: dict[str, list[str]] = {}
        for symptom in shipped["symptoms"]:
            for term in symptom.get("lay_terms", []):
                normalised = term.strip().lower()
                term_map.setdefault(normalised, []).append(symptom["id"])
        ambiguous = {t: ids for t, ids in term_map.items() if len(ids) > 1}
        assert not ambiguous, f"Ambiguous lay terms: {ambiguous}"

    def test_body_systems_list_matches_enum(self, shipped: dict[str, Any]) -> None:
        """The top-level body_systems list must match the known set exactly."""
        assert set(shipped["body_systems"]) == BODY_SYSTEMS


# ---------------------------------------------------------------------------
# validator: edge cases
# ---------------------------------------------------------------------------


class TestValidatorAccepts:
    """Tests that valid variations are accepted."""

    def test_accepts_extra_lay_terms(
        self,
        dataset: dict[str, Any],
    ) -> None:
        """Adding more lay terms should not cause errors."""
        _symptom(dataset, "fever")["lay_terms"].append("pyrexia")
        assert validate_symptoms(dataset) == []

    def test_accepts_single_lay_term(
        self,
        dataset: dict[str, Any],
    ) -> None:
        """A single lay term is enough."""
        _symptom(dataset, "fever")["lay_terms"] = ["high temperature"]
        assert validate_symptoms(dataset) == []


# ---------------------------------------------------------------------------
# validator: failure cases
# ---------------------------------------------------------------------------


class TestValidatorRejects:
    """Tests that each kind of data mistake is reported."""

    def test_reports_missing_top_level_section(
        self,
        dataset: dict[str, Any],
    ) -> None:
        """Report when the symptoms list is missing."""
        del dataset["symptoms"]
        assert "top level: 'symptoms' must be a non-empty list" in validate_symptoms(
            dataset
        )

    def test_reports_non_object_record(
        self,
        dataset: dict[str, Any],
    ) -> None:
        """Report a non-object entry in the symptoms list."""
        dataset["symptoms"].append("not an object")
        index = len(dataset["symptoms"]) - 1
        errors = validate_symptoms(dataset)
        assert f"symptoms[{index}]: must be an object, got 'not an object'" in errors

    def test_reports_duplicate_id(
        self,
        dataset: dict[str, Any],
    ) -> None:
        """Report duplicate symptom IDs."""
        dataset["symptoms"].append(copy.deepcopy(_symptom(dataset, "fever")))
        assert "symptoms: duplicate id 'fever'" in validate_symptoms(dataset)

    def test_reports_missing_name(
        self,
        dataset: dict[str, Any],
    ) -> None:
        """Report a symptom with no name."""
        _symptom(dataset, "fever")["name"] = ""
        assert (
            "symptom 'fever': 'name' must be a non-empty string"
            in validate_symptoms(dataset)
        )

    def test_reports_unknown_body_system(
        self,
        dataset: dict[str, Any],
    ) -> None:
        """Report a body system not in the known set."""
        _symptom(dataset, "fever")["body_system"] = "astral"
        assert "symptom 'fever': unknown body_system 'astral'" in validate_symptoms(
            dataset
        )

    def test_reports_name_mismatch_with_conditions(
        self,
        dataset: dict[str, Any],
    ) -> None:
        """Report when a symptom name does not match conditions.json."""
        _symptom(dataset, "fever")["name"] = "High Fever"
        errors = validate_symptoms(dataset)
        assert any(
            "fever" in e and "does not match" in e and "name" in e for e in errors
        )

    def test_reports_body_system_mismatch_with_conditions(
        self,
        dataset: dict[str, Any],
    ) -> None:
        """Report when a body_system does not match conditions.json."""
        _symptom(dataset, "headache")["body_system"] = "general"
        errors = validate_symptoms(dataset)
        assert any(
            "headache" in e and "does not match" in e and "body_system" in e
            for e in errors
        )

    def test_reports_missing_lay_terms(
        self,
        dataset: dict[str, Any],
    ) -> None:
        """Report a symptom with an empty lay_terms list."""
        _symptom(dataset, "fever")["lay_terms"] = []
        assert "symptom 'fever': 'lay_terms' must not be empty" in validate_symptoms(
            dataset
        )

    def test_reports_lay_terms_not_a_list(
        self,
        dataset: dict[str, Any],
    ) -> None:
        """Report when lay_terms is not a list."""
        _symptom(dataset, "fever")["lay_terms"] = "high temperature"
        assert "symptom 'fever': 'lay_terms' must be a list" in validate_symptoms(
            dataset
        )

    def test_reports_empty_lay_term_string(
        self,
        dataset: dict[str, Any],
    ) -> None:
        """Report a lay term that is an empty string."""
        _symptom(dataset, "fever")["lay_terms"].append("")
        assert (
            "symptom 'fever': lay term must be a non-empty string"
            in validate_symptoms(dataset)
        )

    def test_reports_ambiguous_lay_term(
        self,
        dataset: dict[str, Any],
    ) -> None:
        """Report when the same lay term maps to two different symptoms."""
        _symptom(dataset, "fever")["lay_terms"].append("unique test term")
        _symptom(dataset, "chills")["lay_terms"].append("unique test term")
        errors = validate_symptoms(dataset)
        assert any(
            "ambiguous lay term" in e and "unique test term" in e for e in errors
        )

    def test_reports_symptom_missing_from_conditions(
        self,
        dataset: dict[str, Any],
    ) -> None:
        """Report a symptom ID not found in conditions.json."""
        dataset["symptoms"].append(
            {
                "id": "hiccups",
                "name": "Hiccups",
                "body_system": "general",
                "lay_terms": ["hiccupping"],
            }
        )
        errors = validate_symptoms(dataset)
        assert any(
            "hiccups" in e and "not found in conditions.json" in e for e in errors
        )

    def test_reports_missing_coverage(
        self,
        dataset: dict[str, Any],
    ) -> None:
        """Report when a condition symptom is missing from the vocabulary."""
        # Why: remove one symptom and check the coverage error fires.
        dataset["symptoms"] = [s for s in dataset["symptoms"] if s["id"] != "fever"]
        errors = validate_symptoms(dataset)
        assert any("fever" in e and "missing from" in e for e in errors)

    def test_reports_unknown_body_systems_in_top_level_list(
        self,
        dataset: dict[str, Any],
    ) -> None:
        """Report unknown entries in the top-level body_systems list."""
        dataset["body_systems"].append("astral")
        errors = validate_symptoms(dataset)
        assert any("unknown body_systems" in e for e in errors)


# ---------------------------------------------------------------------------
# command line
# ---------------------------------------------------------------------------


class TestCli:
    """Tests for the command-line interface."""

    def test_returns_zero_for_shipped_dataset(self) -> None:
        """The CLI returns success for the default dataset."""
        assert main([]) == 0

    def test_returns_one_for_invalid_file(
        self,
        dataset: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Write an invalid dataset to a temporary file and verify CLI failure."""
        _symptom(dataset, "fever")["body_system"] = "astral"
        broken = tmp_path / "broken.json"
        broken.write_text(json.dumps(dataset), encoding="utf-8")
        assert main([str(broken)]) == 1
