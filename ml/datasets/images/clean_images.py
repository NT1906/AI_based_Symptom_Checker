"""Clean the downloaded images against the frozen split (run on Kaggle or Colab).

Responsibilities:
    - Drop images that are missing, fail to decode, or have a side shorter
      than 128 px (docs/cv-plan.md §4).
    - Find near-duplicates by perceptual hash (dHash), within and across
      datasets. Each duplicate set keeps one image, preferring test, then val,
      so a test image can never also sit in training; sets with conflicting
      labels are dropped entirely.
    - Write ``clean_v1.csv`` (the manifest rows that survive) and
      ``clean_report.json`` (drops by reason, final counts, class-size rule).

Cleaning only removes rows; it never moves an image to another split.

Usage::

    python ml/datasets/images/clean_images.py --images /kaggle/working/images

Owner: Nisarg (cv) · Task: S1-NIS-5 · Requirements: NFR-07
"""

import argparse
import csv
import json
import logging
import sys
from collections import Counter, defaultdict
from collections.abc import Sequence
from pathlib import Path

from download_images import image_path
from PIL import Image, ImageOps, UnidentifiedImageError

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "cv"))
from train_config import DEFAULT_CONFIG_PATH, load_config

DEFAULT_MANIFEST = HERE / "manifest" / "split_v1.csv"
DEFAULT_IMAGES = HERE.parents[1] / "data" / "images"
MIN_SIDE_PX = 128
HASH_BANDS = 4
# Why: with 4 bands of 16 bits, any two hashes this close share a whole band
# (pigeonhole), so comparing within band buckets finds every such pair.
MAX_HASH_DISTANCE = HASH_BANDS - 1
SPLIT_PRIORITY = {"test": 0, "val": 1, "train": 2}

log = logging.getLogger("images.clean")

Row = dict[str, str]


def dhash(image: Image.Image) -> int:
    """64-bit difference hash: is each pixel brighter than its right neighbour?

    Args:
        image: Any decoded image.

    Returns:
        The hash as an integer.
    """
    small = image.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
    pixels = small.tobytes()  # one byte per pixel in mode "L"
    bits = 0
    for row in range(8):
        for col in range(8):
            left = pixels[row * 9 + col]
            right = pixels[row * 9 + col + 1]
            bits = (bits << 1) | (left > right)
    return bits


def check_image(path: Path) -> tuple[str | None, int | None]:
    """Check one file.

    Returns:
        ``(drop_reason, hash)``: a reason (``missing``, ``undecodable``,
        ``too_small``) and no hash, or no reason and the image's dHash.
    """
    if not path.exists():
        return "missing", None
    try:
        with Image.open(path) as opened:
            image = ImageOps.exif_transpose(opened)
            image.load()
            if min(image.size) < MIN_SIDE_PX:
                return "too_small", None
            return None, dhash(image)
    except (UnidentifiedImageError, OSError, ValueError):
        return "undecodable", None


def duplicate_sets(hashes: dict[str, int]) -> list[list[str]]:
    """Group image IDs whose hashes differ in at most ``MAX_HASH_DISTANCE`` bits.

    Args:
        hashes: Image ID -> dHash.

    Returns:
        Every set with more than one image, each sorted, in sorted order.
    """
    parent = {image_id: image_id for image_id in hashes}

    def root(image_id: str) -> str:
        while parent[image_id] != image_id:
            parent[image_id] = parent[parent[image_id]]
            image_id = parent[image_id]
        return image_id

    for band in range(HASH_BANDS):
        buckets: dict[int, list[str]] = defaultdict(list)
        for image_id, value in hashes.items():
            buckets[(value >> (16 * band)) & 0xFFFF].append(image_id)
        for members in buckets.values():
            for i, first in enumerate(members):
                for second in members[i + 1 :]:
                    distance = (hashes[first] ^ hashes[second]).bit_count()
                    if distance <= MAX_HASH_DISTANCE:
                        parent[root(first)] = root(second)
    sets: dict[str, list[str]] = defaultdict(list)
    for image_id in hashes:
        sets[root(image_id)].append(image_id)
    return sorted(sorted(s) for s in sets.values() if len(s) > 1)


def resolve_duplicates(rows: dict[str, Row], sets: list[list[str]]) -> dict[str, str]:
    """Decide which duplicates to drop.

    Args:
        rows: Image ID -> manifest row.
        sets: Duplicate sets from :func:`duplicate_sets`.

    Returns:
        Dropped image ID -> reason.
    """
    dropped: dict[str, str] = {}
    for members in sets:
        if len({rows[m]["label"] for m in members}) > 1:
            dropped.update(dict.fromkeys(members, "duplicate_conflicting_labels"))
            continue
        keep = min(
            members,
            key=lambda m: (SPLIT_PRIORITY[rows[m]["split"]], rows[m]["source"], m),
        )
        dropped.update({m: "duplicate" for m in members if m != keep})
    return dropped


def clean(
    rows: Sequence[Row], images: Path, min_train: int, min_test: int
) -> tuple[list[Row], dict[str, object]]:
    """Clean every manifest row.

    Args:
        rows: Manifest rows.
        images: Image root folder used by ``download_images.py``.
        min_train: Class-size rule, training images per class.
        min_test: Class-size rule, test images per class.

    Returns:
        The surviving rows (manifest order) and the report.
    """
    by_id = {row["image_id"]: row for row in rows}
    dropped: dict[str, str] = {}
    hashes: dict[str, int] = {}
    for row in rows:
        path = image_path(images, row["source"], row["image_id"], row["url"])
        reason, value = check_image(path)
        if reason is not None:
            dropped[row["image_id"]] = reason
        elif value is not None:
            hashes[row["image_id"]] = value
    dropped.update(resolve_duplicates(by_id, duplicate_sets(hashes)))
    kept = [row for row in rows if row["image_id"] not in dropped]
    return kept, _report(kept, dropped, by_id, min_train, min_test)


def _report(
    kept: Sequence[Row],
    dropped: dict[str, str],
    by_id: dict[str, Row],
    min_train: int,
    min_test: int,
) -> dict[str, object]:
    """Counts after cleaning, for the dataset card."""
    by_split: dict[str, Counter[str]] = defaultdict(Counter)
    by_tone: dict[str, Counter[str]] = defaultdict(Counter)
    for row in kept:
        by_split[row["split"]][row["label"]] += 1
        by_tone[row["label"]][row["skin_tone"]] += 1
    drops = Counter(f"{by_id[i]['source']}:{reason}" for i, reason in dropped.items())
    labels = sorted(by_tone)
    return {
        "stage": "after download and cleaning",
        "images": len(kept),
        "dropped": dict(sorted(drops.items())),
        "by_split": {s: dict(sorted(c.items())) for s, c in sorted(by_split.items())},
        "by_label_skin_tone": {k: dict(sorted(by_tone[k].items())) for k in labels},
        "class_size_check": {
            k: {
                "train": by_split["train"][k],
                "test": by_split["test"][k],
                "meets_minimum": by_split["train"][k] >= min_train
                and by_split["test"][k] >= min_test,
            }
            for k in labels
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Clean the downloaded images and write the clean manifest and report.

    Args:
        argv: Command-line arguments; defaults to ``sys.argv[1:]``.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--images", type=Path, default=DEFAULT_IMAGES)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    data = load_config(args.config).data
    with args.manifest.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        rows = list(reader)
    kept, report = clean(
        rows,
        args.images,
        data.min_train_images_per_class,
        data.min_test_images_per_class,
    )
    with (args.images / "clean_v1.csv").open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(kept)
    report_path = args.images / "clean_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    log.info(
        "%d of %d images kept; dropped: %s", len(kept), len(rows), report["dropped"]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
