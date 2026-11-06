"""Unit tests for reading the cleaned manifest into training samples.

Covers:
    - Labels map to output indices; merged labels train as ``unclear``.
    - Samples per split, local paths, and the per-split smoke limit.
    - Unknown labels or splits are rejected; class weights.

Owner: Nisarg (cv) · Task: S1-NIS-6 · Requirements: NFR-07
"""

import csv
from pathlib import Path

import pytest
from cv_data import class_counts, class_weights, label_indices, read_splits
from train_config import load_config

COLUMNS = ("split", "image_id", "source", "label", "skin_tone", "url")


def _manifest(path: Path, rows: list[tuple[str, ...]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNS)
        writer.writerows(rows)
    return path


def test_merged_labels_train_as_unclear() -> None:
    config = load_config()
    indices = label_indices(config)
    unclear = config.class_names.index("unclear")

    assert indices["eczema"] == 0
    assert all(indices[m] == unclear for m in config.data.merged_into_unclear)


def test_read_splits_builds_samples(tmp_path: Path) -> None:
    manifest = _manifest(
        tmp_path / "clean.csv",
        [
            ("train", "a", "scin", "eczema", "light", "https://x/a.png"),
            ("train", "b", "fitzpatrick17k", "scabies", "dark", "https://x/b.jpg"),
            ("test", "c", "scin", "urticaria", "unknown", "https://x/c.png"),
        ],
    )

    splits = read_splits(manifest, tmp_path / "img", load_config())

    train = splits["train"]
    assert [(s.image_id, s.label, s.skin_tone) for s in train] == [
        ("a", 0, "light"),
        ("b", 2, "dark"),
    ]
    assert train[1].path == tmp_path / "img" / "fitzpatrick17k" / "b.jpg"
    assert splits["val"] == []
    assert class_counts(train, 3) == [1, 0, 1]


def test_read_splits_limit_keeps_first_rows_per_split(tmp_path: Path) -> None:
    rows = [
        ("train", str(i), "scin", "eczema", "light", f"u/{i}.png") for i in range(5)
    ]
    manifest = _manifest(tmp_path / "clean.csv", rows)

    splits = read_splits(manifest, tmp_path, load_config(), limit=2)

    assert [s.image_id for s in splits["train"]] == ["0", "1"]


@pytest.mark.parametrize(
    ("row", "message"),
    [
        (("train", "a", "scin", "psoriasis", "light", "u/a.png"), "not in the config"),
        (("holdout", "a", "scin", "eczema", "light", "u/a.png"), "unknown split"),
    ],
)
def test_read_splits_rejects_bad_rows(
    tmp_path: Path, row: tuple[str, ...], message: str
) -> None:
    manifest = _manifest(tmp_path / "clean.csv", [row])

    with pytest.raises(ValueError, match=message):
        read_splits(manifest, tmp_path, load_config())


def test_inverse_sqrt_weights_favour_small_classes() -> None:
    weights = class_weights([400, 100, 25], "inverse_sqrt_frequency")

    assert weights[0] < weights[1] < weights[2]
    assert sum(weights) / len(weights) == pytest.approx(1.0)


def test_class_weights_none_and_errors() -> None:
    assert class_weights([5, 1], "none") == [1.0, 1.0]
    with pytest.raises(ValueError, match="needs training images"):
        class_weights([5, 0], "inverse_sqrt_frequency")
    with pytest.raises(ValueError, match="unknown class weighting"):
        class_weights([5, 1], "focal")
