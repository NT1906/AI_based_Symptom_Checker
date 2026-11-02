"""Tests for the CV training config and its loader.

Covers the shipped ``configs/baseline.yaml`` (it must load and stay aligned
with the condition dataset and docs/cv-plan.md) and the loader itself (each
kind of config mistake must be rejected with a message naming the key).

Owner: Nisarg (cv) · Task: S0-NIS-2 · Requirements: NFR-07
"""

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from config_readers import ConfigError
from train_config import (
    DEFAULT_CONFIG_PATH,
    MAX_LATENCY_MS,
    MAX_MODEL_MB,
    UNCLEAR_CLASS,
    load_config,
    parse_config,
)

CONDITIONS_PATH = (
    Path(__file__).parents[1] / "datasets" / "conditions" / "conditions.json"
)

Raw = dict[str, Any]  # Any: parsed YAML, as the loader receives it.


@pytest.fixture(scope="module")
def shipped_raw() -> Raw:
    """The baseline config as parsed YAML, before validation."""
    parsed: Raw = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    return parsed


@pytest.fixture
def raw(shipped_raw: Raw) -> Raw:
    """A private copy of the baseline config that a test may break."""
    return copy.deepcopy(shipped_raw)


def _visual_skin_condition_ids() -> set[str]:
    """IDs of the skin conditions a photo can help with, from conditions.json."""
    dataset = json.loads(CONDITIONS_PATH.read_text(encoding="utf-8"))
    return {
        c["id"] for c in dataset["conditions"] if c["visual"] and c["group"] == "skin"
    }


# --- the shipped config --------------------------------------------------------


def test_shipped_config_loads() -> None:
    config = load_config()

    assert config.version == 1
    assert config.model.backbone == "efficientnet_b0"
    assert config.class_names[-1] == UNCLEAR_CLASS


def test_shipped_classes_match_visual_skin_conditions() -> None:
    config = load_config()
    mapped = {c.condition_id for c in config.classes if c.condition_id is not None}

    # Every visual skin condition gets a class, and no class points elsewhere.
    assert mapped == _visual_skin_condition_ids()


def test_shipped_split_and_skin_tone_groups_are_complete() -> None:
    data = load_config().data

    assert sum(data.split.values()) == pytest.approx(1.0)
    assert set(data.skin_tone_groups) == {"light", "medium", "dark"}


def test_shipped_budgets_stay_within_production_limits() -> None:
    export = load_config().export

    assert export.max_model_mb <= MAX_MODEL_MB
    assert export.max_latency_ms <= MAX_LATENCY_MS


def test_loaded_config_is_immutable() -> None:
    config = load_config()

    with pytest.raises(AttributeError):
        config.seed = 7  # type: ignore[misc]


# --- edge cases that must stay valid -------------------------------------------


def test_accepts_one_condition_class_plus_unclear(raw: Raw) -> None:
    raw["classes"] = [
        {"name": "acne", "condition_id": "acne"},
        {"name": UNCLEAR_CLASS, "condition_id": None},
    ]

    assert parse_config(raw).class_names == ("acne", UNCLEAR_CLASS)


def test_accepts_inclusive_bounds_and_integer_for_float(raw: Raw) -> None:
    raw["model"]["dropout"] = 0
    raw["export"]["max_model_mb"] = MAX_MODEL_MB

    config = parse_config(raw)

    assert config.model.dropout == 0.0
    assert config.export.max_model_mb == MAX_MODEL_MB


# --- mistakes the loader must reject -------------------------------------------


def _set(path: str, value: Any) -> Callable[[Raw], None]:  # Any: any YAML value
    """Return a mutation that sets a dotted key, e.g. ``"training.epochs"``."""

    def mutate(raw: Raw) -> None:
        *parents, last = path.split(".")
        target = raw
        for part in parents:
            target = target[part]
        target[last] = value

    return mutate


def _move_unclear_first(raw: Raw) -> None:
    raw["classes"].insert(0, raw["classes"].pop())


def _duplicate_first_class(raw: Raw) -> None:
    raw["classes"].insert(1, dict(raw["classes"][0]))


def _drop_key(raw: Raw) -> None:
    del raw["training"]["epochs"]


INVALID_CASES = [
    ("unclear_not_last", _move_unclear_first, "must be the last class"),
    ("duplicate_class", _duplicate_first_class, "must be unique"),
    ("classes_not_a_list", _set("classes", None), "classes: expected a list"),
    ("missing_key", _drop_key, "missing key(s) ['epochs']"),
    ("typo_key", _set("training.epoch", 5), "unknown key(s) ['epoch']"),
    ("wrong_version", _set("version", 2), "config.version"),
    ("split_not_one", _set("data.split.test", 0.2), "add up to 1"),
    ("split_zero", _set("data.split.val", 0), "data.split.val"),
    ("crop_bigger_than_resize", _set("data.image_size", 300), "image_size"),
    ("zero_std", _set("data.std", [0.2, 0, 0.2]), "data.std"),
    ("two_channel_mean", _set("data.mean", [0.5, 0.5]), "data.mean"),
    ("unknown_source", _set("data.sources", ["dermnet"]), "data.sources"),
    ("unknown_backbone", _set("model.backbone", "resnet50"), "model.backbone"),
    ("bool_as_integer", _set("training.batch_size", True), "expected an integer"),
    ("string_as_bool", _set("model.pretrained", "yes"), "expected true or false"),
    ("all_epochs_frozen", _set("training.freeze_backbone_epochs", 20), "below epochs"),
    ("zero_learning_rate", _set("training.learning_rate", 0), "learning_rate"),
    ("threshold_one", _set("inference.abstain_threshold", 1.0), "abstain_threshold"),
    ("model_over_budget", _set("export.max_model_mb", 30), "max_model_mb"),
    ("latency_over_budget", _set("export.max_latency_ms", 2000), "max_latency_ms"),
    ("unknown_quantization", _set("export.quantization", "fp8"), "quantization"),
    ("bad_wandb_project", _set("tracking.wandb_project", "My Project"), "wandb"),
]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [pytest.param(m, msg, id=case_id) for case_id, m, msg in INVALID_CASES],
)
def test_rejects_invalid_config(
    raw: Raw, mutate: Callable[[Raw], None], message: str
) -> None:
    mutate(raw)

    with pytest.raises(ConfigError) as excinfo:
        parse_config(raw)

    assert message in str(excinfo.value)


def test_rejects_unclear_mapped_to_a_condition(raw: Raw) -> None:
    raw["classes"][-1]["condition_id"] = "acne"

    with pytest.raises(ConfigError, match="only 'unclear' has condition_id null"):
        parse_config(raw)


def test_rejects_condition_class_without_condition_id(raw: Raw) -> None:
    raw["classes"][0]["condition_id"] = None

    with pytest.raises(ConfigError, match="only 'unclear' has condition_id null"):
        parse_config(raw)


@pytest.mark.parametrize(
    "groups",
    [
        pytest.param({"light": [1, 2], "medium": [3, 4]}, id="type_missing"),
        pytest.param({"light": [1, 2, 3], "rest": [3, 4, 5, 6]}, id="type_twice"),
        pytest.param({"light": [], "rest": [1, 2, 3, 4, 5, 6]}, id="empty_group"),
    ],
)
def test_rejects_skin_tone_groups_that_do_not_cover_each_type_once(
    raw: Raw, groups: dict[str, list[int]]
) -> None:
    raw["data"]["skin_tone_groups"] = groups

    with pytest.raises(ConfigError, match="skin_tone_groups"):
        parse_config(raw)


def test_rejects_document_that_is_not_a_mapping() -> None:
    with pytest.raises(ConfigError, match="config: expected a mapping"):
        parse_config(["not", "a", "mapping"])


def test_load_config_reports_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="cannot read config"):
        load_config(tmp_path / "missing.yaml")


def test_load_config_reports_invalid_yaml(tmp_path: Path) -> None:
    broken = tmp_path / "broken.yaml"
    broken.write_text("classes: [unclosed\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="cannot read config"):
        load_config(broken)
