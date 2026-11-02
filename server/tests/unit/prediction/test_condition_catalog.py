"""Unit tests for the packaged condition dataset and its loader.

Covers:
    - The packaged copy loads and is byte-identical to ml/datasets/conditions/.
    - Lookups by condition ID, the red-flag rules (S1-NIS-2) and the
      specialties (S1-NIS-3).
    - Each kind of broken dataset raises ConditionDataError.

Owner: Nisarg (prediction) · Task: S1-NIS-1, S1-NIS-2, S1-NIS-3 · Requirements:
FR-05, FR-07, DR-02, DR-03, DR-04
"""

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from app.services.prediction.condition_catalog import (
    DATA_FILE,
    ConditionDataError,
    get_catalog,
    load_catalog,
)

REPO_ROOT = Path(__file__).parents[4]
ML_CONDITIONS_PATH = REPO_ROOT / "ml" / "datasets" / "conditions" / "conditions.json"

Raw = dict[str, Any]  # Any: parsed JSON, as the loader receives it.


@pytest.fixture(scope="module")
def shipped_raw() -> Raw:
    """The packaged dataset as parsed JSON."""
    parsed: Raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return parsed


def _write(tmp_path: Path, data: Raw) -> Path:
    """Write ``data`` to a temporary dataset file and return its path."""
    path = tmp_path / "conditions.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_packaged_catalog_loads_every_condition(shipped_raw: Raw) -> None:
    catalog = get_catalog()

    assert len(catalog.conditions) == len(shipped_raw["conditions"])
    assert catalog.dataset_version == shipped_raw["dataset_version"]
    assert "fever" in catalog.symptom_ids


@pytest.mark.skipif(not ML_CONDITIONS_PATH.exists(), reason="ml/ not checked out")
def test_packaged_copy_matches_ml_dataset() -> None:
    # Why: the server image has no ml/, so it ships a copy; it must never drift.
    assert DATA_FILE.read_bytes() == ML_CONDITIONS_PATH.read_bytes(), (
        "Copy ml/datasets/conditions/conditions.json to "
        "server/app/services/prediction/data/conditions.json"
    )


def test_get_returns_condition_or_none() -> None:
    catalog = get_catalog()

    cold = catalog.get("common_cold")
    assert cold is not None
    assert cold.icd10 == "J00"
    assert catalog.get("not_a_condition") is None


def test_total_weight_sums_symptom_weights() -> None:
    cold = get_catalog().get("common_cold")

    assert cold is not None
    assert cold.total_weight == sum(s.weight for s in cold.symptoms)


def test_packaged_catalog_loads_every_red_flag(shipped_raw: Raw) -> None:
    red_flags = get_catalog().red_flags

    assert [r.id for r in red_flags] == [r["id"] for r in shipped_raw["red_flags"]]
    assert all(r.triggers for r in red_flags)


def test_packaged_catalog_resolves_every_condition_specialty() -> None:
    catalog = get_catalog()

    for condition in catalog.conditions:
        assert catalog.get_specialty(condition.specialty) is not None
    assert catalog.get_specialty("not_a_specialty") is None


def test_get_red_flag_returns_rule_or_none() -> None:
    catalog = get_catalog()

    red_flag = catalog.get_red_flag("rf_self_harm")
    assert red_flag is not None
    assert red_flag.category == "mental_health"
    assert catalog.get_red_flag("rf_not_a_rule") is None


def _bad_weight(data: Raw) -> None:
    data["conditions"][0]["symptoms"][0]["weight"] = 4


def _unknown_symptom(data: Raw) -> None:
    data["conditions"][0]["symptoms"].append({"id": "made_up_symptom", "weight": 1})


def _duplicate_condition(data: Raw) -> None:
    data["conditions"].append(copy.deepcopy(data["conditions"][0]))


def _bad_base_risk(data: Raw) -> None:
    data["conditions"][0]["base_risk"] = "PROBABLY_FINE"


def _no_conditions(data: Raw) -> None:
    data["conditions"] = []


def _no_red_flags(data: Raw) -> None:
    data["red_flags"] = []


def _red_flag_unknown_symptom(data: Raw) -> None:
    data["red_flags"][0]["triggers"][0]["all_of"][0]["symptom"] = "made_up_symptom"


def _duplicate_red_flag(data: Raw) -> None:
    data["red_flags"].append(copy.deepcopy(data["red_flags"][0]))


def _unknown_min_severity(data: Raw) -> None:
    data["red_flags"][0]["triggers"][0]["all_of"][0]["min_severity"] = "UNKNOWN"


def _no_specialties(data: Raw) -> None:
    data["specialties"] = []


def _unknown_condition_specialty(data: Raw) -> None:
    data["conditions"][0]["specialty"] = "astrology"


def _duplicate_specialty(data: Raw) -> None:
    data["specialties"].append(copy.deepcopy(data["specialties"][0]))


def _typo_in_trigger(data: Raw) -> None:
    data["red_flags"][0]["triggers"][0]["all_of"][0]["min_severty"] = "SEVERE"


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        pytest.param(_bad_weight, "invalid condition dataset", id="weight_4"),
        pytest.param(_unknown_symptom, "made_up_symptom", id="unknown_symptom"),
        pytest.param(_duplicate_condition, "duplicate condition", id="duplicate"),
        pytest.param(_bad_base_risk, "invalid condition dataset", id="bad_risk"),
        pytest.param(_no_conditions, "invalid condition dataset", id="empty"),
        pytest.param(_no_red_flags, "invalid condition dataset", id="no_red_flags"),
        pytest.param(_red_flag_unknown_symptom, "made_up_symptom", id="rf_unknown"),
        pytest.param(_duplicate_red_flag, "duplicate red flag", id="rf_duplicate"),
        pytest.param(_unknown_min_severity, "cannot be UNKNOWN", id="rf_unknown_min"),
        pytest.param(_typo_in_trigger, "invalid condition dataset", id="rf_typo"),
        pytest.param(_no_specialties, "invalid condition dataset", id="no_specs"),
        pytest.param(_unknown_condition_specialty, "astrology", id="unknown_spec"),
        pytest.param(_duplicate_specialty, "duplicate specialty", id="dup_spec"),
    ],
)
def test_rejects_broken_dataset(
    tmp_path: Path,
    shipped_raw: Raw,
    mutate: Callable[[Raw], None],
    message: str,
) -> None:
    data = copy.deepcopy(shipped_raw)
    mutate(data)

    with pytest.raises(ConditionDataError, match=message):
        load_catalog(_write(tmp_path, data))


def test_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConditionDataError, match="invalid condition dataset"):
        load_catalog(tmp_path / "missing.json")


def test_rejects_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "conditions.json"
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(ConditionDataError, match="invalid condition dataset"):
        load_catalog(path)
