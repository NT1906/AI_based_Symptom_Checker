"""Tests for the condition dataset and its validator.

Covers the shipped ``conditions.json`` (it must be valid and meet the S0-NIS-1
acceptance criteria) and the validator itself (each kind of data mistake must
be reported).

Owner: Nisarg (prediction) · Task: S0-NIS-1 · Requirements: DR-02, DR-03, DR-04
"""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from validate_conditions import load_dataset, main, validate_dataset

REQUIRED_RED_FLAG_CATEGORIES = {
    "cardiac",
    "stroke",
    "breathing",
    "bleeding",
    "infection",
    "anaphylaxis",
    "mental_health",
}
REQUIRED_GROUPS = {"primary_care", "infection", "skin", "emergency"}


@pytest.fixture(scope="module")
def shipped() -> dict[str, Any]:
    """The dataset as committed in the repository."""
    return load_dataset()


@pytest.fixture
def dataset(shipped: dict[str, Any]) -> dict[str, Any]:
    """A private copy of the dataset that a test may break."""
    return copy.deepcopy(shipped)


def _condition(data: dict[str, Any], condition_id: str) -> dict[str, Any]:
    return next(c for c in data["conditions"] if c["id"] == condition_id)


# --- the shipped dataset -------------------------------------------------------


def test_shipped_dataset_has_no_errors(shipped: dict[str, Any]) -> None:
    assert validate_dataset(shipped) == []


def test_shipped_dataset_has_about_thirty_five_conditions(
    shipped: dict[str, Any],
) -> None:
    assert 30 <= len(shipped["conditions"]) <= 40


def test_shipped_dataset_covers_every_condition_group(shipped: dict[str, Any]) -> None:
    assert {c["group"] for c in shipped["conditions"]} == REQUIRED_GROUPS


def test_shipped_red_flags_cover_required_categories(shipped: dict[str, Any]) -> None:
    categories = {flag["category"] for flag in shipped["red_flags"]}
    assert REQUIRED_RED_FLAG_CATEGORIES <= categories


def test_every_shipped_condition_has_three_or_more_symptoms(
    shipped: dict[str, Any],
) -> None:
    too_few = [c["id"] for c in shipped["conditions"] if len(c["symptoms"]) < 3]
    # Low back pain is the one deliberate exception: two symptoms describe it fully.
    assert too_few == ["low_back_pain"]


def test_severe_chest_pain_is_a_red_flag(shipped: dict[str, Any]) -> None:
    cardiac = next(
        f for f in shipped["red_flags"] if f["id"] == "rf_cardiac_chest_pain"
    )
    assert {"all_of": [{"symptom": "chest_pain", "min_severity": "SEVERE"}]} in cardiac[
        "triggers"
    ]


def test_severe_pain_in_any_abdominal_location_is_a_red_flag(
    shipped: dict[str, Any],
) -> None:
    # The extractor may code pain by location; every location must escalate (DR-02).
    flag = next(
        f for f in shipped["red_flags"] if f["id"] == "rf_severe_abdominal_pain"
    )
    abdominal = [
        s["id"] for s in shipped["symptoms"] if s["id"].endswith("abdominal_pain")
    ]
    assert len(abdominal) == 4
    for symptom in abdominal:
        trigger = {"all_of": [{"symptom": symptom, "min_severity": "SEVERE"}]}
        assert trigger in flag["triggers"], symptom


def test_chest_pain_conditions_route_to_cardiology(shipped: dict[str, Any]) -> None:
    # DR-04 example from the project report: chest pain -> cardiology.
    assert _condition(shipped, "heart_attack")["specialty"] == "cardiology"


def test_every_emergency_with_urgent_base_risk_has_a_red_flag(
    shipped: dict[str, Any],
) -> None:
    urgent = [c for c in shipped["conditions"] if c["base_risk"] == "URGENT"]
    assert urgent
    assert all(c["red_flags"] for c in urgent)


# --- validator: edge cases ------------------------------------------------------


@pytest.mark.parametrize("code", ["A90", "J11.1", "M54.5", "B86"])
def test_accepts_icd10_codes_with_and_without_subcategory(
    dataset: dict[str, Any], code: str
) -> None:
    _condition(dataset, "dengue")["icd10"] = code
    errors = validate_dataset(dataset)
    # The code may now clash with another condition; only the format matters here.
    assert not any("invalid ICD-10" in e for e in errors)


def test_red_flag_trigger_without_severity_is_valid(dataset: dict[str, Any]) -> None:
    cardiac = next(
        f for f in dataset["red_flags"] if f["id"] == "rf_cardiac_chest_pain"
    )
    del cardiac["triggers"][0]["all_of"][0]["min_severity"]
    assert validate_dataset(dataset) == []


# --- validator: failure cases ---------------------------------------------------


def test_reports_missing_top_level_section(dataset: dict[str, Any]) -> None:
    del dataset["red_flags"]
    assert "top level: 'red_flags' must be a non-empty list" in validate_dataset(
        dataset
    )


def test_reports_unknown_symptom_in_condition(dataset: dict[str, Any]) -> None:
    _condition(dataset, "dengue")["symptoms"].append({"id": "tummy_ache", "weight": 2})
    assert (
        "condition 'dengue': unknown symptom reference 'tummy_ache'"
        in validate_dataset(dataset)
    )


def test_reports_invalid_icd10_code(dataset: dict[str, Any]) -> None:
    _condition(dataset, "dengue")["icd10"] = "a90"
    assert "condition 'dengue': invalid ICD-10 code 'a90'" in validate_dataset(dataset)


def test_reports_duplicate_icd10_code(dataset: dict[str, Any]) -> None:
    _condition(dataset, "malaria")["icd10"] = "A90"
    assert "conditions: ICD-10 code 'A90' used more than once" in validate_dataset(
        dataset
    )


def test_reports_duplicate_condition_id(dataset: dict[str, Any]) -> None:
    _condition(dataset, "malaria")["id"] = "dengue"
    assert "conditions: duplicate id 'dengue'" in validate_dataset(dataset)


def test_reports_unknown_specialty(dataset: dict[str, Any]) -> None:
    _condition(dataset, "dengue")["specialty"] = "astrology"
    assert "condition 'dengue': unknown specialty 'astrology'" in validate_dataset(
        dataset
    )


def test_reports_unknown_base_risk(dataset: dict[str, Any]) -> None:
    _condition(dataset, "dengue")["base_risk"] = "LOW"
    assert "condition 'dengue': unknown base_risk 'LOW'" in validate_dataset(dataset)


def test_reports_unknown_red_flag_reference(dataset: dict[str, Any]) -> None:
    _condition(dataset, "dengue")["red_flags"].append("rf_missing")
    assert (
        "condition 'dengue': unknown red_flags reference 'rf_missing'"
        in validate_dataset(dataset)
    )


def test_reports_invalid_symptom_weight(dataset: dict[str, Any]) -> None:
    _condition(dataset, "dengue")["symptoms"][0]["weight"] = 5
    assert any(
        "dengue" in e and "invalid weight 5" in e for e in validate_dataset(dataset)
    )


def test_reports_boolean_symptom_weight(dataset: dict[str, Any]) -> None:
    _condition(dataset, "dengue")["symptoms"][-1]["weight"] = True
    assert any(
        "dengue" in e and "invalid weight True" in e for e in validate_dataset(dataset)
    )


def test_reports_condition_without_hallmark_symptom(dataset: dict[str, Any]) -> None:
    for entry in _condition(dataset, "acne")["symptoms"]:
        entry["weight"] = 1
    assert (
        "condition 'acne': needs at least one hallmark symptom (weight 3)"
        in validate_dataset(dataset)
    )


def test_reports_condition_with_too_few_symptoms(dataset: dict[str, Any]) -> None:
    _condition(dataset, "acne")["symptoms"] = [{"id": "pimples", "weight": 3}]
    assert "condition 'acne': needs at least 2 symptoms" in validate_dataset(dataset)


def test_reports_identical_symptom_profiles(dataset: dict[str, Any]) -> None:
    _condition(dataset, "malaria")["symptoms"] = copy.deepcopy(
        _condition(dataset, "dengue")["symptoms"]
    )
    assert (
        "conditions 'dengue' and 'malaria' have identical symptoms"
        in validate_dataset(dataset)
    )


def test_reports_red_flag_with_unknown_severity(dataset: dict[str, Any]) -> None:
    dataset["red_flags"][0]["triggers"] = [
        {"all_of": [{"symptom": "chest_pain", "min_severity": "HUGE"}]}
    ]
    assert any("unknown min_severity 'HUGE'" in e for e in validate_dataset(dataset))


def test_reports_red_flag_with_empty_trigger(dataset: dict[str, Any]) -> None:
    dataset["red_flags"][0]["triggers"] = [{"all_of": []}]
    assert any(
        "'all_of' must be a non-empty list" in e for e in validate_dataset(dataset)
    )


def test_reports_unused_symptom(dataset: dict[str, Any]) -> None:
    dataset["symptoms"].append(
        {"id": "hiccups", "name": "Hiccups", "body_system": "general"}
    )
    assert (
        "symptom 'hiccups' is not used by any condition or red flag"
        in validate_dataset(dataset)
    )


def test_reports_source_without_https(dataset: dict[str, Any]) -> None:
    dataset["sources"][0]["url"] = "http://example.org"
    assert any("url must start with https://" in e for e in validate_dataset(dataset))


@pytest.mark.parametrize(
    "section", ["specialties", "symptoms", "red_flags", "conditions", "sources"]
)
def test_reports_non_object_record_without_crashing(
    dataset: dict[str, Any], section: str
) -> None:
    dataset[section].append("not an object")
    index = len(dataset[section]) - 1
    errors = validate_dataset(dataset)
    assert f"{section}[{index}]: must be an object, got 'not an object'" in errors


def test_reports_condition_whose_symptoms_are_not_a_list(
    dataset: dict[str, Any],
) -> None:
    _condition(dataset, "acne")["symptoms"] = 5
    assert "condition 'acne': needs at least 2 symptoms" in validate_dataset(dataset)


# --- command line -----------------------------------------------------------------


def test_cli_returns_zero_for_shipped_dataset() -> None:
    assert main([]) == 0


def test_cli_returns_one_for_invalid_file(
    dataset: dict[str, Any], tmp_path: Path
) -> None:
    _condition(dataset, "dengue")["specialty"] = "astrology"
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps(dataset), encoding="utf-8")
    assert main([str(broken)]) == 1
