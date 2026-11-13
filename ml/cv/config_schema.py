"""Immutable dataclasses describing a validated CV training config.

``train_config.load_config`` builds these from YAML; everything else (the
training loop, export and evaluation scripts) reads them and never the raw
YAML. Field meanings are explained in docs/cv-plan.md.

Owner: Nisarg (cv) · Task: S0-NIS-2 · Requirements: NFR-07
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ClassSpec:
    """One model output class.

    Attributes:
        name: Class label, used as the model's output name.
        condition_id: Matching ``conditions.json`` ID; ``None`` for ``unclear``.
    """

    name: str
    condition_id: str | None


@dataclass(frozen=True)
class DataConfig:
    """Data sources, preprocessing and split settings (docs/cv-plan.md §4)."""

    sources: tuple[str, ...]
    resize_size: int
    image_size: int
    mean: tuple[float, float, float]
    std: tuple[float, float, float]
    split: dict[str, float]
    skin_tone_groups: dict[str, tuple[int, ...]]
    min_train_images_per_class: int
    min_test_images_per_class: int
    merged_into_unclear: tuple[str, ...]


@dataclass(frozen=True)
class ModelConfig:
    """Backbone choice (docs/cv-plan.md §5)."""

    backbone: str
    pretrained: bool
    dropout: float


@dataclass(frozen=True)
class TrainingConfig:
    """Optimiser and schedule settings (docs/cv-plan.md §5)."""

    epochs: int
    freeze_backbone_epochs: int
    batch_size: int
    learning_rate: float
    weight_decay: float
    label_smoothing: float
    class_weighting: str
    mixed_precision: bool


@dataclass(frozen=True)
class ExportConfig:
    """ONNX export and budget settings (docs/cv-plan.md §7)."""

    opset: int
    quantization: str
    calibration_images: int
    max_model_mb: int
    max_latency_ms: int


@dataclass(frozen=True)
class TrainConfig:
    """The whole validated config. Build it with :func:`load_config`."""

    version: int
    seed: int
    classes: tuple[ClassSpec, ...]
    data: DataConfig
    model: ModelConfig
    training: TrainingConfig
    abstain_threshold: float
    export: ExportConfig
    wandb_project: str

    @property
    def class_names(self) -> tuple[str, ...]:
        """Class names in model output order."""
        return tuple(spec.name for spec in self.classes)
