"""Tests for the NLP evaluation cases dataset (``cases.json``).

Covers the shipped ``cases.json`` (verifying schema, uniqueness, severity values,
non-empty inputs, and alignment with the canonical symptom vocabulary in
``symptoms.json``).

Owner: Kavya (AI/ML, Database) · Task: S0-KAV-1 · Requirements: FR-03
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

    def test_at_least_twenty_cases(self, cases_data: dict[str, Any]) -> None:
        """S0-KAV-1 requires at least 20 evaluation cases."""
        assert len(cases_data["cases"]) >= 20

    def test_case_ids_format_and_unique(self, cases_data: dict[str, Any]) -> None:
        """Each case ID must be unique and match the case_NNN pattern."""
        ids = [c.get("id") for c in cases_data["cases"]]
        assert len(ids) == len(set(ids)), "Case IDs must be unique"
        for cid in ids:
            assert isinstance(cid, str) and CASE_ID_PATTERN.match(cid), (
                f"Invalid ID format: {cid}"
            )

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
        """Every symptom ID in expected.symptoms must exist in the canonical vocabulary."""
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
