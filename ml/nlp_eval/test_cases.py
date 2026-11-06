"""Tests for the NLP evaluation cases dataset (``cases.json``).

Covers the shipped ``cases.json`` (verifying schema, uniqueness, severity values,
non-empty inputs, 100-case coverage, and alignment with the canonical symptom
vocabulary in ``symptoms.json``).

Owner: Kavya (AI/ML, Database) · Tasks: S0-KAV-1, S2-KAV-2 · Requirements: FR-03, NFR-07
"""

import json
import re
from pathlib import Path
from typing import Any

import pytest

CASES_PATH = Path(__file__).with_name("cases.json")
SYMPTOMS_PATH = Path(__file__).parent.parent / "datasets" / "symptoms" / "symptoms.json"

CASE_ID_PATTERN = re.compile(r"^case_\d{3}$")
VALID_SEVERITIES = frozenset({"MILD", "MODERATE", "SEVERE"})
VALID_TAGS = frozenset(
    {"standard", "hinglish", "misspelling", "red_flag", "multi_symptom"}
)


def load_json(path: Path) -> dict[str, Any]:
    """Read and parse a JSON file.

    Args:
        path: Path to the JSON file.

    Returns:
        Parsed JSON dictionary.
    """
    with path.open(encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return data


@pytest.fixture(scope="module")
def cases_data() -> dict[str, Any]:
    """The NLP eval dataset as committed in the repository."""
    return load_json(CASES_PATH)


@pytest.fixture(scope="module")
def valid_symptom_ids() -> set[str]:
    """All symptom IDs defined in the canonical vocabulary."""
    data = load_json(SYMPTOMS_PATH)
    return {s["id"] for s in data["symptoms"]}


class TestShippedEvalCases:
    """Tests that the committed cases.json meets all requirements."""

    def test_top_level_fields(self, cases_data: dict[str, Any]) -> None:
        """Top-level metadata fields must be present and valid."""
        assert cases_data.get("schema_version") == "1.0"
        assert isinstance(cases_data.get("description"), str)
        assert cases_data["description"].strip()
        assert set(cases_data.get("severities", [])) == VALID_SEVERITIES
        assert isinstance(cases_data.get("cases"), list)

    def test_exactly_one_hundred_cases(self, cases_data: dict[str, Any]) -> None:
        """S2-KAV-2 requires exactly 100 evaluation cases in eval set v2."""
        assert len(cases_data["cases"]) == 100

    def test_case_ids_format_and_unique(self, cases_data: dict[str, Any]) -> None:
        """Each case ID must be unique and match the case_NNN pattern."""
        ids = [c.get("id") for c in cases_data["cases"]]
        assert len(ids) == len(set(ids)), "Case IDs must be unique"
        for i, cid in enumerate(ids):
            assert isinstance(cid, str) and CASE_ID_PATTERN.match(cid), (
                f"Invalid ID format: {cid}"
            )
            assert cid == f"case_{i + 1:03d}", f"ID out of sequence: {cid}"

    def test_case_inputs_and_notes_non_empty(self, cases_data: dict[str, Any]) -> None:
        """Every case must contain realistic non-empty input and explanatory notes."""
        for case in cases_data["cases"]:
            cid = case.get("id", "unknown")
            user_input = case.get("input")
            assert isinstance(user_input, str) and user_input.strip(), (
                f"{cid}: 'input' must be non-empty string"
            )
            notes = case.get("notes")
            assert isinstance(notes, str) and notes.strip(), (
                f"{cid}: 'notes' must be non-empty string"
            )

    def test_all_expected_symptoms_align_with_vocabulary(
        self,
        cases_data: dict[str, Any],
        valid_symptom_ids: set[str],
    ) -> None:
        """Every symptom ID in expected.symptoms must exist in canonical vocabulary."""
        for case in cases_data["cases"]:
            cid = case.get("id", "unknown")
            expected = case.get("expected", {})
            symptoms = expected.get("symptoms", [])
            assert isinstance(symptoms, list) and symptoms, (
                f"{cid}: expected.symptoms must be a non-empty list"
            )

            for sym in symptoms:
                assert isinstance(sym, dict), f"{cid}: symptom must be an object"
                sym_id = sym.get("id")
                assert sym_id in valid_symptom_ids, (
                    f"{cid}: symptom id '{sym_id}' not found in canonical vocabulary"
                )

    def test_full_vocabulary_coverage(
        self,
        cases_data: dict[str, Any],
        valid_symptom_ids: set[str],
    ) -> None:
        """The 100 benchmark cases cover 100% of all 100 canonical symptom IDs."""
        covered = {
            sym["id"]
            for case in cases_data["cases"]
            for sym in case.get("expected", {}).get("symptoms", [])
        }
        missing = valid_symptom_ids - covered
        assert not missing, f"Missing coverage for canonical symptoms: {missing}"
        assert len(covered) == len(valid_symptom_ids) == 100

    def test_severities_valid_when_specified(self, cases_data: dict[str, Any]) -> None:
        """When severity is specified, it must be MILD, MODERATE, or SEVERE."""
        for case in cases_data["cases"]:
            cid = case.get("id", "unknown")
            for sym in case.get("expected", {}).get("symptoms", []):
                sev = sym.get("severity")
                if sev is not None:
                    assert sev in VALID_SEVERITIES, (
                        f"{cid}: invalid severity '{sev}' for symptom '{sym.get('id')}'"
                    )

    def test_duration_is_non_empty_string_when_present(
        self, cases_data: dict[str, Any]
    ) -> None:
        """Duration must be a non-empty string if provided."""
        for case in cases_data["cases"]:
            cid = case.get("id", "unknown")
            expected = case.get("expected", {})
            if "duration" in expected:
                dur = expected["duration"]
                assert isinstance(dur, str) and dur.strip(), (
                    f"{cid}: duration must be a non-empty string"
                )

    def test_tags_are_valid_when_present(self, cases_data: dict[str, Any]) -> None:
        """Case tags must belong to recognized linguistic categories."""
        for case in cases_data["cases"]:
            cid = case.get("id", "unknown")
            tags = case.get("tags", [])
            assert isinstance(tags, list), f"{cid}: 'tags' must be a list"
            for tag in tags:
                assert tag in VALID_TAGS, f"{cid}: unrecognized tag '{tag}'"
