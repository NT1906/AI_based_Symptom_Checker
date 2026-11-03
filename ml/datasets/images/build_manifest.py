"""Build the frozen split manifest for the skin-image dataset from metadata.

Responsibilities:
    - Download the SCIN and Fitzpatrick17k metadata CSVs (pinned, checksummed).
    - Map labels and skin tones, split 70/15/15 grouped by case and
      stratified by class x skin tone (docs/cv-plan.md §4).
    - Write ``manifest/split_v1.csv`` (image ID -> split, class, skin tone,
      URL; no images) and ``manifest/summary_v1.json`` (counts).

The split uses metadata only, so it does not change when atlas links die.
Run once; later tasks read the committed manifest and never re-split.

Usage::

    python ml/datasets/images/build_manifest.py
    python ml/datasets/images/build_manifest.py --metadata-dir /kaggle/input/meta

Owner: Nisarg (cv) · Task: S1-NIS-5 · Requirements: NFR-07
"""

import argparse
import csv
import hashlib
import json
import logging
import sys
import urllib.request
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

from image_labels import UNKNOWN_SKIN_TONE
from image_sources import ImageRecord, read_fitzpatrick17k, read_scin
from image_split import SPLITS, assign_splits

HERE = Path(__file__).resolve().parent
ML_DIR = HERE.parents[1]
sys.path.insert(0, str(ML_DIR / "cv"))
from train_config import DEFAULT_CONFIG_PATH, load_config

log = logging.getLogger("images.build_manifest")

DATASET_VERSION = "v1"
DEFAULT_METADATA_DIR = ML_DIR / "data" / "images" / "metadata"
MANIFEST_DIR = HERE / "manifest"
MANIFEST_COLUMNS = ("split", *(f.name for f in fields(ImageRecord)))


@dataclass(frozen=True)
class MetadataFile:
    """One pinned metadata file."""

    name: str
    url: str
    sha256: str


# Why: SCIN's bucket is not versioned, so the checksums are what pin it; a
# changed file stops the build instead of silently changing the frozen split.
METADATA_FILES = (
    MetadataFile(
        "scin_cases.csv",
        "https://storage.googleapis.com/dx-scin-public-data/dataset/scin_cases.csv",
        "7923ee9ba9775af413ca115c4587dc1bd32259d7936aa97fa80d88dd616ca3c3",
    ),
    MetadataFile(
        "scin_labels.csv",
        "https://storage.googleapis.com/dx-scin-public-data/dataset/scin_labels.csv",
        "616ad03c24c304f5f7ef01b4116e4d3274f1c71c9b19a0e3d5620698b081a9fe",
    ),
    MetadataFile(
        "fitzpatrick17k.csv",
        "https://raw.githubusercontent.com/mattgroh/fitzpatrick17k/"
        "9865ce95b4b2035a1b311644ca00e028d1c4e74c/fitzpatrick17k.csv",
        "851dfaabf1791c2a8b1c2957619f3e0673cf0002f4ce924a5c02d185c7d4a1cd",
    ),
)


def fetch_metadata(directory: Path) -> dict[str, Path]:
    """Download any missing metadata file and check every checksum.

    Args:
        directory: Where the CSVs live (git-ignored ``ml/data/`` by default).

    Returns:
        File name -> local path.

    Raises:
        ValueError: If a file's SHA-256 differs from the pinned one.
    """
    directory.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for meta in METADATA_FILES:
        path = directory / meta.name
        if not path.exists():
            log.info("downloading %s", meta.url)
            urllib.request.urlretrieve(meta.url, path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != meta.sha256:
            raise ValueError(
                f"{meta.name} changed upstream (sha256 {digest}); the frozen "
                "split must not be rebuilt from different metadata"
            )
        paths[meta.name] = path
    return paths


def build_records(
    paths: dict[str, Path], groups: dict[str, tuple[int, ...]]
) -> tuple[list[ImageRecord], Counter[str]]:
    """Read both sources into records, sorted by source and image ID."""
    with (
        paths["scin_cases.csv"].open(encoding="utf-8", newline="") as cases,
        paths["scin_labels.csv"].open(encoding="utf-8", newline="") as labels,
        paths["fitzpatrick17k.csv"].open(encoding="utf-8", newline="") as fitz,
    ):
        scin, scin_left_out = read_scin(
            csv.DictReader(cases), csv.DictReader(labels), groups
        )
        fitz_records, fitz_left_out = read_fitzpatrick17k(csv.DictReader(fitz), groups)
    records = sorted([*scin, *fitz_records], key=lambda r: (r.source, r.image_id))
    return records, scin_left_out + fitz_left_out


def summarise(
    records: Sequence[ImageRecord],
    splits: dict[str, str],
    left_out: Counter[str],
    min_train: int,
    min_test: int,
    seed: int,
    fractions: dict[str, float],
) -> dict[str, Any]:
    """Counts for the dataset card, before cleaning.

    Args:
        records: The split images.
        splits: Image ID -> split.
        left_out: Left-out image counts by reason.
        min_train: Class-size rule, training images per class.
        min_test: Class-size rule, test images per class.
        seed: Split seed.
        fractions: Split fractions.

    Returns:
        A JSON-ready summary.
    """
    by_split: dict[str, Counter[str]] = {s: Counter() for s in SPLITS}
    by_tone: dict[str, Counter[str]] = defaultdict(Counter)
    by_source: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        by_split[splits[record.image_id]][record.label] += 1
        by_tone[record.label][record.skin_tone] += 1
        by_source[record.label][record.source] += 1
    labels = sorted({r.label for r in records})
    return {
        "dataset_version": DATASET_VERSION,
        "stage": "metadata (before download and cleaning)",
        "seed": seed,
        "fractions": fractions,
        "metadata": {
            m.name: {"url": m.url, "sha256": m.sha256} for m in METADATA_FILES
        },
        "images": len(records),
        "groups": len({r.group_id for r in records}),
        "by_split": {s: dict(sorted(by_split[s].items())) for s in SPLITS},
        "by_label_skin_tone": {k: dict(sorted(by_tone[k].items())) for k in labels},
        "by_label_source": {k: dict(sorted(by_source[k].items())) for k in labels},
        "left_out": dict(sorted(left_out.items())),
        "class_size_check": {
            label: {
                "train": by_split["train"][label],
                "test": by_split["test"][label],
                "meets_minimum": by_split["train"][label] >= min_train
                and by_split["test"][label] >= min_test,
            }
            for label in labels
        },
    }


def write_manifest(
    path: Path, records: Sequence[ImageRecord], splits: dict[str, str]
) -> None:
    """Write the split manifest CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=MANIFEST_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        for record in records:
            writer.writerow({"split": splits[record.image_id], **asdict(record)})


def main(argv: Sequence[str] | None = None) -> int:
    """Build the manifest and summary.

    Args:
        argv: Command-line arguments; defaults to ``sys.argv[1:]``.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--metadata-dir", type=Path, default=DEFAULT_METADATA_DIR)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--output-dir", type=Path, default=MANIFEST_DIR)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    config = load_config(args.config)
    groups = dict(config.data.skin_tone_groups)
    if UNKNOWN_SKIN_TONE in groups:
        raise ValueError(f"{UNKNOWN_SKIN_TONE!r} is reserved for missing skin types")

    records, left_out = build_records(fetch_metadata(args.metadata_dir), groups)
    unexpected = {r.label for r in records} - set(config.class_names)
    if unexpected:
        raise ValueError(f"labels not in the config: {sorted(unexpected)}")
    splits = assign_splits(records, config.data.split, config.seed)

    write_manifest(args.output_dir / f"split_{DATASET_VERSION}.csv", records, splits)
    summary = summarise(
        records,
        splits,
        left_out,
        config.data.min_train_images_per_class,
        config.data.min_test_images_per_class,
        config.seed,
        dict(config.data.split),
    )
    summary_path = args.output_dir / f"summary_{DATASET_VERSION}.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    log.info("%d images -> %s", len(records), args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
