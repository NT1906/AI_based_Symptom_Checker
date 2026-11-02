"""Typed, validated training config for the skin-image model.

Responsibilities:
    - Read a YAML config (``ml/cv/configs/*.yaml``) into frozen dataclasses.
    - Reject mistakes before a GPU session starts: unknown or missing keys,
      wrong types, out-of-range values, a class list without ``unclear`` last,
      split fractions that do not add up, and budgets above the production
      limits in docs/cv-plan.md §7.

Only the standard library and PyYAML are used, so CI can test it without the
training dependencies.

Owner: Nisarg (cv) · Task: S0-NIS-2 · Requirements: NFR-07
"""

import math
from pathlib import Path
from typing import Any

import yaml
from config_readers import (
    NAME_PATTERN,
    ConfigError,
    read_boolean,
    read_channel_triple,
    read_integer,
    read_mapping,
    read_name,
    read_number,
    read_string_list,
    require_exact_keys,
)
from config_schema import (
    ClassSpec,
    DataConfig,
    ExportConfig,
    ModelConfig,
    TrainConfig,
    TrainingConfig,
)

CONFIG_DIR = Path(__file__).with_name("configs")
DEFAULT_CONFIG_PATH = CONFIG_DIR / "baseline.yaml"

SUPPORTED_VERSION = 1
UNCLEAR_CLASS = "unclear"
BACKBONES = frozenset({"efficientnet_b0", "mobilenetv3_large_100"})
SOURCES = frozenset({"scin", "fitzpatrick17k"})
QUANTIZATIONS = frozenset({"int8_static", "none"})
CLASS_WEIGHTINGS = frozenset({"inverse_sqrt_frequency", "none"})
FITZPATRICK_TYPES = frozenset(range(1, 7))
# Production limits from docs/tech-stack.md §6; a config may be stricter, never looser.
MAX_MODEL_MB = 25
MAX_LATENCY_MS = 1000
SPLIT_TOLERANCE = 1e-6


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> TrainConfig:
    """Read and validate a YAML training config.

    Args:
        path: Location of the YAML file. Defaults to ``configs/baseline.yaml``.

    Returns:
        The validated, immutable config.

    Raises:
        ConfigError: If the file cannot be read, is not valid YAML, or breaks
            any rule. The message names the offending key.

    Example:
        >>> load_config().class_names[-1]
        'unclear'
    """
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"cannot read config {path}: {exc}") from exc
    return parse_config(raw)


def parse_config(raw: Any) -> TrainConfig:  # Any: whatever the YAML parser returned
    """Validate an already-parsed config mapping.

    Args:
        raw: The parsed YAML document.

    Returns:
        The validated, immutable config.

    Raises:
        ConfigError: If any key is missing, unknown, mistyped or out of range.
    """
    root = read_mapping(raw, "config")
    require_exact_keys(
        root,
        {"version", "seed", "classes", "data", "model", "training"}
        | {"inference", "export", "tracking"},
        "config",
    )
    version = read_integer(root, "version", "config", minimum=1)
    if version != SUPPORTED_VERSION:
        raise ConfigError(
            f"config.version: expected {SUPPORTED_VERSION}, got {version}"
        )
    inference = read_mapping(root["inference"], "inference")
    require_exact_keys(inference, {"abstain_threshold"}, "inference")
    tracking = read_mapping(root["tracking"], "tracking")
    require_exact_keys(tracking, {"wandb_project"}, "tracking")
    return TrainConfig(
        version=version,
        seed=read_integer(root, "seed", "config", minimum=0),
        classes=_parse_classes(root["classes"]),
        data=_parse_data(root["data"]),
        model=_parse_model(root["model"]),
        training=_parse_training(root["training"]),
        # Why: 0 would never abstain and 1 would always abstain (docs/cv-plan.md §2).
        abstain_threshold=read_number(
            inference, "abstain_threshold", "inference", 0.0, 1.0, inclusive=False
        ),
        export=_parse_export(root["export"]),
        wandb_project=read_name(
            tracking, "wandb_project", "tracking", pattern=r"^[a-z0-9-]+$"
        ),
    )


def _parse_classes(raw: Any) -> tuple[ClassSpec, ...]:  # Any: parsed YAML
    """Validate the class list: unique names, ``unclear`` last and only there."""
    if not isinstance(raw, list) or len(raw) < 2:
        raise ConfigError("classes: expected a list of at least 2 classes")
    specs = []
    for index, item in enumerate(raw):
        where = f"classes[{index}]"
        entry = read_mapping(item, where)
        require_exact_keys(entry, {"name", "condition_id"}, where)
        name = read_name(entry, "name", where)
        condition_id = entry["condition_id"]
        # Why: `unclear` is the abstain class; it must never map to a condition.
        if (name == UNCLEAR_CLASS) != (condition_id is None):
            raise ConfigError(f"{where}: only '{UNCLEAR_CLASS}' has condition_id null")
        if condition_id is not None:
            condition_id = read_name(entry, "condition_id", where)
        specs.append(ClassSpec(name=name, condition_id=condition_id))
    names = [spec.name for spec in specs]
    if len(set(names)) != len(names):
        raise ConfigError("classes: class names must be unique")
    if names[-1] != UNCLEAR_CLASS:
        raise ConfigError(f"classes: '{UNCLEAR_CLASS}' must be the last class")
    return tuple(specs)


def _parse_data(raw: Any) -> DataConfig:  # Any: parsed YAML
    """Validate data sources, preprocessing sizes, split and skin-tone groups."""
    data = read_mapping(raw, "data")
    require_exact_keys(
        data,
        {"sources", "resize_size", "image_size", "mean", "std", "split"}
        | {"skin_tone_groups", "min_train_images_per_class"}
        | {"min_test_images_per_class"},
        "data",
    )
    sources = read_string_list(data, "sources", "data")
    unknown = set(sources) - SOURCES
    if not sources or unknown:
        raise ConfigError(f"data.sources: expected some of {sorted(SOURCES)}")
    resize_size = read_integer(data, "resize_size", "data", minimum=32)
    image_size = read_integer(data, "image_size", "data", minimum=32)
    if image_size > resize_size:
        raise ConfigError("data.image_size: must not be larger than data.resize_size")
    return DataConfig(
        sources=tuple(sources),
        resize_size=resize_size,
        image_size=image_size,
        mean=read_channel_triple(data, "mean"),
        std=read_channel_triple(data, "std", positive=True),
        split=_parse_split(data["split"]),
        skin_tone_groups=_parse_skin_tone_groups(data["skin_tone_groups"]),
        min_train_images_per_class=read_integer(
            data, "min_train_images_per_class", "data", minimum=1
        ),
        min_test_images_per_class=read_integer(
            data, "min_test_images_per_class", "data", minimum=1
        ),
    )


def _parse_split(raw: Any) -> dict[str, float]:  # Any: parsed YAML
    """Validate train/val/test fractions: each above 0, together exactly 1."""
    split = read_mapping(raw, "data.split")
    require_exact_keys(split, {"train", "val", "test"}, "data.split")
    fractions = {
        key: read_number(split, key, "data.split", 0.0, 1.0, inclusive=False)
        for key in ("train", "val", "test")
    }
    if not math.isclose(sum(fractions.values()), 1.0, abs_tol=SPLIT_TOLERANCE):
        raise ConfigError("data.split: train + val + test must add up to 1")
    return fractions


def _parse_skin_tone_groups(raw: Any) -> dict[str, tuple[int, ...]]:  # Any: YAML
    """Validate that the groups cover Fitzpatrick types 1-6 exactly once."""
    groups = read_mapping(raw, "data.skin_tone_groups")
    seen: list[int] = []
    parsed: dict[str, tuple[int, ...]] = {}
    for group, types in groups.items():
        where = f"data.skin_tone_groups.{group}"
        if not isinstance(group, str) or not NAME_PATTERN.match(group):
            raise ConfigError(f"{where}: group names must be snake_case")
        if (
            not isinstance(types, list)
            or not types
            or not all(isinstance(t, int) and not isinstance(t, bool) for t in types)
        ):
            raise ConfigError(f"{where}: expected a non-empty list of integers")
        parsed[group] = tuple(types)
        seen.extend(types)
    # Why: per-skin-tone metrics (NFR-07) are wrong if a type is missing or counted twice.
    if sorted(seen) != sorted(FITZPATRICK_TYPES):
        raise ConfigError(
            "data.skin_tone_groups: must cover Fitzpatrick types 1-6 exactly once"
        )
    return parsed


def _parse_model(raw: Any) -> ModelConfig:  # Any: parsed YAML
    """Validate the backbone choice."""
    model = read_mapping(raw, "model")
    require_exact_keys(model, {"backbone", "pretrained", "dropout"}, "model")
    backbone = read_name(model, "backbone", "model")
    if backbone not in BACKBONES:
        raise ConfigError(f"model.backbone: expected one of {sorted(BACKBONES)}")
    return ModelConfig(
        backbone=backbone,
        pretrained=read_boolean(model, "pretrained", "model"),
        dropout=read_number(model, "dropout", "model", 0.0, 1.0),
    )


def _parse_training(raw: Any) -> TrainingConfig:  # Any: parsed YAML
    """Validate optimiser and schedule settings."""
    training = read_mapping(raw, "training")
    require_exact_keys(
        training,
        {"epochs", "freeze_backbone_epochs", "batch_size", "learning_rate"}
        | {"weight_decay", "label_smoothing", "class_weighting", "mixed_precision"},
        "training",
    )
    epochs = read_integer(training, "epochs", "training", minimum=1)
    frozen = read_integer(training, "freeze_backbone_epochs", "training", minimum=0)
    if frozen >= epochs:
        raise ConfigError("training.freeze_backbone_epochs: must be below epochs")
    weighting = read_name(training, "class_weighting", "training")
    if weighting not in CLASS_WEIGHTINGS:
        raise ConfigError(
            f"training.class_weighting: expected one of {sorted(CLASS_WEIGHTINGS)}"
        )
    return TrainingConfig(
        epochs=epochs,
        freeze_backbone_epochs=frozen,
        batch_size=read_integer(training, "batch_size", "training", minimum=1),
        learning_rate=read_number(
            training, "learning_rate", "training", 0.0, 1.0, False
        ),
        weight_decay=read_number(training, "weight_decay", "training", 0.0, 1.0),
        label_smoothing=read_number(training, "label_smoothing", "training", 0.0, 0.5),
        class_weighting=weighting,
        mixed_precision=read_boolean(training, "mixed_precision", "training"),
    )


def _parse_export(raw: Any) -> ExportConfig:  # Any: parsed YAML
    """Validate export settings and keep budgets within the production limits."""
    export = read_mapping(raw, "export")
    require_exact_keys(
        export,
        {"opset", "quantization", "calibration_images", "max_model_mb"}
        | {"max_latency_ms"},
        "export",
    )
    quantization = read_name(export, "quantization", "export")
    if quantization not in QUANTIZATIONS:
        raise ConfigError(
            f"export.quantization: expected one of {sorted(QUANTIZATIONS)}"
        )
    return ExportConfig(
        opset=read_integer(export, "opset", "export", minimum=13),
        quantization=quantization,
        calibration_images=read_integer(
            export, "calibration_images", "export", minimum=1
        ),
        max_model_mb=read_integer(
            export, "max_model_mb", "export", minimum=1, maximum=MAX_MODEL_MB
        ),
        max_latency_ms=read_integer(
            export, "max_latency_ms", "export", minimum=1, maximum=MAX_LATENCY_MS
        ),
    )
