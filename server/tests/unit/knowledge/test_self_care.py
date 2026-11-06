"""Unit tests for the curated condition self-care guidance service.

Owner: Kavya (knowledge) · Task: S2-KAV-1 · Requirements: idea §8, DR-05
Reviewed by: Dimple (Medical Safety & Privacy Lead)
"""

import json
from pathlib import Path

import pytest

from app.services.knowledge.schemas import SelfCareGuidance
from app.services.knowledge.self_care import (
    SelfCareService,
    get_self_care_guidance,
    get_self_care_service,
    lookup_self_care,
)
from app.services.privacy.safety_guard import assert_safe_wording


def test_service_initialization_and_len() -> None:
    """Service loads all packaged conditions into memory."""
    service = get_self_care_service()
    assert len(service) == 38
    assert "common_cold" in service
    assert "migraine" in service
    assert "nonexistent_disease" not in service

    all_ids = service.list_condition_ids()
    assert len(all_ids) == 38
    assert all_ids == tuple(sorted(all_ids))
    assert "common_cold" in all_ids
    assert "covid_19" in all_ids


def test_get_guidance_happy_path() -> None:
    """Lookup by condition ID returns valid SelfCareGuidance model."""
    service = get_self_care_service()
    guidance = service.get_guidance("common_cold")
    assert guidance is not None
    assert isinstance(guidance, SelfCareGuidance)
    assert guidance.condition_id == "common_cold"
    assert guidance.condition_name == "Common cold"
    assert len(guidance.general_advice) >= 3
    assert len(guidance.when_to_seek_care) >= 2
    assert len(guidance.monitoring_tips) >= 1

    # Verify convenience lookup function matches
    assert lookup_self_care("common_cold") == guidance


def test_lookup_case_insensitivity_and_whitespace() -> None:
    """Condition ID lookup handles uppercase letters and whitespace."""
    service = get_self_care_service()
    assert service.get_guidance("  COMMON_COLD  ") is not None
    assert service.get_guidance("Covid_19") is not None
    assert "  migraine  " in service


def test_get_guidance_missing_or_invalid() -> None:
    """Lookup returns None for non-existent or blank conditions."""
    service = get_self_care_service()
    assert service.get_guidance("nonexistent_condition") is None
    assert service.get_guidance("") is None
    assert service.get_guidance("   ") is None
    assert lookup_self_care("unknown_id") is None


def test_get_self_care_steps_deduplication_and_limit() -> None:
    """Aggregating advice across multiple conditions deduplicates and limits results."""
    service = get_self_care_service()
    steps = service.get_self_care_steps(
        ["common_cold", "acute_pharyngitis"], max_steps=4
    )
    assert isinstance(steps, tuple)
    assert 0 < len(steps) <= 4

    # Ensure no duplicate strings (case-insensitive)
    lowered = [s.lower() for s in steps]
    assert len(lowered) == len(set(lowered))

    # Verify convenience function
    conv_steps = get_self_care_guidance(
        ["common_cold", "acute_pharyngitis"], max_steps=4
    )
    assert conv_steps == steps


def test_get_self_care_steps_empty_and_zero_limit() -> None:
    """Empty condition lists or zero/negative max_steps return empty tuple."""
    service = get_self_care_service()
    assert service.get_self_care_steps([]) == ()
    assert service.get_self_care_steps(["unknown1", "unknown2"]) == ()
    assert service.get_self_care_steps(["common_cold"], max_steps=0) == ()
    assert service.get_self_care_steps(["common_cold"], max_steps=-3) == ()


def test_get_when_to_seek_care_and_monitoring_tips() -> None:
    """Warning signs and monitoring tips aggregate and deduplicate as expected."""
    service = get_self_care_service()
    warnings = service.get_when_to_seek_care(["influenza", "pneumonia"], max_warnings=3)
    assert isinstance(warnings, tuple)
    assert 0 < len(warnings) <= 3
    assert len(warnings) == len(set(warnings))

    tips = service.get_monitoring_tips(["gerd"], max_tips=2)
    assert isinstance(tips, tuple)
    assert 0 < len(tips) <= 2
    assert len(tips) == len(set(tips))

    # Negative limits
    assert service.get_when_to_seek_care(["influenza"], max_warnings=0) == ()
    assert service.get_monitoring_tips(["gerd"], max_tips=-1) == ()


def test_catalog_condition_coverage_parity() -> None:
    """Every condition in prediction catalog is covered in self_care.json."""
    conditions_json_path = (
        Path(__file__).resolve().parents[3]
        / "app"
        / "services"
        / "prediction"
        / "data"
        / "conditions.json"
    )
    with open(conditions_json_path, encoding="utf-8") as f:
        catalog_data = json.load(f)

    catalog_condition_ids = {c["id"] for c in catalog_data["conditions"]}
    service = get_self_care_service()
    self_care_ids = set(service.list_condition_ids())

    # Every prediction condition must have curated self-care guidance
    missing = catalog_condition_ids - self_care_ids
    assert not missing, f"Missing self-care guidance for catalog conditions: {missing}"
    assert len(catalog_condition_ids) == len(self_care_ids)


def test_all_self_care_guidance_passes_safe_wording_guard() -> None:
    """All 38 conditions pass the automated DR-05 safe wording framework.

    Verifies that no banned phrases (diagnoses, cures, specific drug prescriptions,
    or definitive certainties) exist in the curated self-care content.
    """
    service = get_self_care_service()
    checked_count = 0

    for condition_id in service.list_condition_ids():
        guidance = service.get_guidance(condition_id)
        assert guidance is not None

        for advice in guidance.general_advice:
            assert_safe_wording(advice)
            checked_count += 1

        for warning in guidance.when_to_seek_care:
            assert_safe_wording(warning)
            checked_count += 1

        for tip in guidance.monitoring_tips:
            assert_safe_wording(tip)
            checked_count += 1

    assert checked_count > 250, (
        f"Expected >250 guidance strings, checked {checked_count}"
    )


def test_custom_data_path_file_not_found(tmp_path: Path) -> None:
    """Initializing service with a nonexistent file path raises FileNotFoundError."""
    missing_file = tmp_path / "does_not_exist.json"
    with pytest.raises(FileNotFoundError, match="not found"):
        SelfCareService(missing_file)


def test_custom_data_path_invalid_json(tmp_path: Path) -> None:
    """Initializing service with malformed JSON raises ValueError."""
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed self-care JSON"):
        SelfCareService(bad_json)


def test_custom_data_path_missing_conditions_array(tmp_path: Path) -> None:
    """Initializing service with payload missing 'conditions' key raises ValueError."""
    invalid_structure = tmp_path / "invalid.json"
    invalid_structure.write_text(json.dumps({"wrong_key": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="expected 'conditions' array"):
        SelfCareService(invalid_structure)


def test_custom_data_path_conditions_not_a_list(tmp_path: Path) -> None:
    """Initializing service where 'conditions' is not a list raises ValueError."""
    invalid_type = tmp_path / "invalid_type.json"
    invalid_type.write_text(json.dumps({"conditions": "not_a_list"}), encoding="utf-8")
    with pytest.raises(ValueError, match="Expected list of condition entries"):
        SelfCareService(invalid_type)


def test_custom_data_path_duplicate_condition_id(tmp_path: Path) -> None:
    """Duplicate condition identifiers in data file raise ValueError."""
    dup_file = tmp_path / "duplicates.json"
    payload = {
        "conditions": [
            {
                "condition_id": "test_cond",
                "condition_name": "Test Condition",
                "general_advice": ["Rest and fluids."],
                "when_to_seek_care": ["Severe pain."],
                "monitoring_tips": ["Check temperature."],
            },
            {
                "condition_id": "test_cond",
                "condition_name": "Duplicate Test Condition",
                "general_advice": ["Another step."],
                "when_to_seek_care": ["Fever."],
                "monitoring_tips": ["Log symptoms."],
            },
        ]
    }
    dup_file.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate condition_id"):
        SelfCareService(dup_file)
