"""Training samples from the cleaned split manifest.

Responsibilities:
    - Read ``clean_v1.csv`` (from ``ml/datasets/images/clean_images.py``) into
      samples per split, with each label turned into a model output index.
    - Train labels in ``data.merged_into_unclear`` as ``unclear``; fail on any
      other label, so a typo never silently becomes a class.
    - Compute class weights (``inverse_sqrt_frequency``).

Standard library only, so CI can test it without torch.

Owner: Nisarg (cv) · Task: S1-NIS-6 · Requirements: NFR-07
"""

import csv
import math
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from config_schema import TrainConfig
from train_config import UNCLEAR_CLASS

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "datasets" / "images"))
from download_images import image_path

SPLITS = ("train", "val", "test")


@dataclass(frozen=True)
class Sample:
    """One training image.

    Attributes:
        image_id: Manifest image ID.
        path: Local image file.
        label: Model output index.
        skin_tone: Skin-tone group, for per-group metrics.
    """

    image_id: str
    path: Path
    label: int
    skin_tone: str


def label_indices(config: TrainConfig) -> dict[str, int]:
    """Manifest label -> model output index, including merged labels.

    Example:
        >>> from train_config import load_config
        >>> label_indices(load_config())["acne"]
        2
    """
    indices = {name: i for i, name in enumerate(config.class_names)}
    unclear = indices[UNCLEAR_CLASS]
    indices.update(dict.fromkeys(config.data.merged_into_unclear, unclear))
    return indices


def read_splits(
    manifest: Path, images: Path, config: TrainConfig, limit: int | None = None
) -> dict[str, list[Sample]]:
    """Read the cleaned manifest into samples per split.

    Args:
        manifest: ``clean_v1.csv``.
        images: Image root used by the download script.
        config: Training config.
        limit: Keep only the first ``limit`` rows per split (smoke runs).

    Returns:
        Split name -> samples, in manifest order.

    Raises:
        ValueError: On a label that is neither a class nor merged, or an
            unknown split name.
    """
    indices = label_indices(config)
    splits: dict[str, list[Sample]] = {name: [] for name in SPLITS}
    with manifest.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["label"] not in indices:
                raise ValueError(f"label {row['label']!r} is not in the config")
            if row["split"] not in splits:
                raise ValueError(f"unknown split {row['split']!r}")
            bucket = splits[row["split"]]
            if limit is not None and len(bucket) >= limit:
                continue
            bucket.append(
                Sample(
                    image_id=row["image_id"],
                    path=image_path(images, row["source"], row["image_id"], row["url"]),
                    label=indices[row["label"]],
                    skin_tone=row["skin_tone"],
                )
            )
    return splits


def class_counts(samples: Sequence[Sample], num_classes: int) -> list[int]:
    """Images per model class."""
    counts = [0] * num_classes
    for sample in samples:
        counts[sample.label] += 1
    return counts


def class_weights(counts: Sequence[int], scheme: str) -> list[float]:
    """Loss weight per class, scaled so the average weight is 1.

    Args:
        counts: Training images per class.
        scheme: ``inverse_sqrt_frequency`` or ``none``.

    Returns:
        One weight per class.

    Raises:
        ValueError: On an unknown scheme or a class with no training images.

    Example:
        >>> [round(w, 2) for w in class_weights([100, 25], "inverse_sqrt_frequency")]
        [0.67, 1.33]
    """
    if scheme == "none":
        return [1.0] * len(counts)
    if scheme != "inverse_sqrt_frequency":
        raise ValueError(f"unknown class weighting {scheme!r}")
    if any(count <= 0 for count in counts):
        raise ValueError(f"every class needs training images, got {list(counts)}")
    raw = [1 / math.sqrt(count) for count in counts]
    mean = sum(raw) / len(raw)
    return [weight / mean for weight in raw]
