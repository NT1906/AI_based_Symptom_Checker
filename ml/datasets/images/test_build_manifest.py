"""Tests for the manifest builder and the committed, frozen manifest.

Covers:
    - Metadata whose checksum changed upstream stops the build.
    - The committed manifest: valid splits and classes, every group in one
      split, unique IDs, and counts that match the committed summary.

Owner: Nisarg (cv) · Task: S1-NIS-5 · Requirements: NFR-07
"""

import csv
import json
from collections import Counter
from pathlib import Path

import pytest
from build_manifest import (
    MANIFEST_COLUMNS,
    MANIFEST_DIR,
    METADATA_FILES,
    fetch_metadata,
    load_config,
)
from image_split import SPLITS

MANIFEST = MANIFEST_DIR / "split_v1.csv"
SUMMARY = MANIFEST_DIR / "summary_v1.json"


@pytest.fixture(scope="module")
def rows() -> list[dict[str, str]]:
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_changed_metadata_stops_the_build(tmp_path: Path) -> None:
    for meta in METADATA_FILES:
        (tmp_path / meta.name).write_text("changed upstream", encoding="utf-8")

    with pytest.raises(ValueError, match="changed upstream"):
        fetch_metadata(tmp_path)


def test_manifest_has_expected_columns() -> None:
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        assert tuple(next(csv.reader(handle))) == MANIFEST_COLUMNS


def test_manifest_rows_are_valid(rows: list[dict[str, str]]) -> None:
    classes = set(load_config().class_names)

    assert {r["split"] for r in rows} <= set(SPLITS)
    assert {r["label"] for r in rows} <= classes
    assert {r["source"] for r in rows} == {"scin", "fitzpatrick17k"}
    assert len({r["image_id"] for r in rows}) == len(rows)
    assert all(r["url"].startswith(("https://", "http://")) for r in rows)


def test_every_group_is_in_one_split(rows: list[dict[str, str]]) -> None:
    splits: dict[str, set[str]] = {}
    for r in rows:
        splits.setdefault(r["group_id"], set()).add(r["split"])

    assert all(len(s) == 1 for s in splits.values())


def test_summary_matches_manifest(rows: list[dict[str, str]]) -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    counts: dict[str, Counter[str]] = {s: Counter() for s in SPLITS}
    for r in rows:
        counts[r["split"]][r["label"]] += 1

    assert summary["images"] == len(rows)
    assert summary["by_split"] == {
        s: dict(sorted(c.items())) for s, c in counts.items()
    }
    assert summary["seed"] == load_config().seed
