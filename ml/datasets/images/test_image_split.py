"""Unit tests for the grouped, stratified split.

Covers:
    - Every image of a group lands in the same split.
    - Shares are close to 70/15/15 within each class x skin-tone stratum.
    - The result is the same for any input order, and changes with the seed.
    - Tiny strata go to train; bad input is rejected.

Owner: Nisarg (cv) · Task: S1-NIS-5 · Requirements: NFR-07
"""

from collections import Counter

import pytest
from image_sources import ImageRecord
from image_split import assign_splits

FRACTIONS = {"train": 0.7, "val": 0.15, "test": 0.15}


def _record(
    image_id: str, group: str, label: str = "acne", tone: str = "light"
) -> ImageRecord:
    return ImageRecord(
        image_id, "scin", group, label, tone, label, "top_label", f"u/{image_id}"
    )


def _dataset() -> list[ImageRecord]:
    records = []
    for label in ("acne", "eczema"):
        for tone in ("light", "dark"):
            for g in range(100):
                group = f"{label}-{tone}-{g}"
                records += [
                    _record(f"{group}-{i}", group, label, tone)
                    for i in range(1 + g % 3)
                ]
    return records


def test_groups_stay_in_one_split() -> None:
    records = _dataset()

    splits = assign_splits(records, FRACTIONS, seed=42)

    by_group: dict[str, set[str]] = {}
    for r in records:
        by_group.setdefault(r.group_id, set()).add(splits[r.image_id])
    assert all(len(s) == 1 for s in by_group.values())


def test_each_stratum_is_close_to_target_shares() -> None:
    records = _dataset()

    splits = assign_splits(records, FRACTIONS, seed=42)

    for stratum in {(r.label, r.skin_tone) for r in records}:
        members = [r for r in records if (r.label, r.skin_tone) == stratum]
        counts = Counter(splits[r.image_id] for r in members)
        for split, share in FRACTIONS.items():
            assert abs(counts[split] / len(members) - share) < 0.02


def test_split_ignores_input_order_and_follows_seed() -> None:
    records = _dataset()

    first = assign_splits(records, FRACTIONS, seed=42)

    assert assign_splits(list(reversed(records)), FRACTIONS, seed=42) == first
    assert assign_splits(records, FRACTIONS, seed=7) != first


def test_tiny_stratum_goes_to_train() -> None:
    splits = assign_splits([_record("only", "g1", "chickenpox")], FRACTIONS, seed=42)

    assert splits == {"only": "train"}


def test_rejects_duplicate_image_ids() -> None:
    with pytest.raises(ValueError, match="duplicate image ID"):
        assign_splits([_record("a", "g1"), _record("a", "g2")], FRACTIONS, seed=42)


def test_rejects_group_mixing_classes() -> None:
    records = [_record("a", "g1", "acne"), _record("b", "g1", "eczema")]

    with pytest.raises(ValueError, match="mixes"):
        assign_splits(records, FRACTIONS, seed=42)


def test_rejects_wrong_split_names() -> None:
    with pytest.raises(ValueError, match="fractions"):
        assign_splits([_record("a", "g1")], {"train": 0.8, "test": 0.2}, seed=42)
