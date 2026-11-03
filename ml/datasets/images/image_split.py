"""Grouped, stratified train/val/test split for the skin-image dataset.

Responsibilities:
    - Keep every image of one group (a SCIN case) in the same split, so the
      test set never leaks into training.
    - Stratify by class x skin-tone group, so every split has the same mix
      (docs/cv-plan.md §4).
    - Be fully deterministic for a given seed and input, in any order.

Owner: Nisarg (cv) · Task: S1-NIS-5 · Requirements: NFR-07
"""

import random
from collections import defaultdict
from collections.abc import Mapping, Sequence

from image_sources import ImageRecord

SPLITS = ("train", "val", "test")


def assign_splits(
    records: Sequence[ImageRecord], fractions: Mapping[str, float], seed: int
) -> dict[str, str]:
    """Assign each image to a split.

    Within each class x skin-tone stratum, groups are shuffled with a seed
    derived from ``seed`` and the stratum, then each group goes to the split
    that is furthest below its target share of images. Very small strata
    therefore land mostly in ``train``.

    Args:
        records: Every image to split.
        fractions: Target share of images per split (``train``, ``val``,
            ``test``), from the config.
        seed: Base random seed.

    Returns:
        Image ID -> split name.

    Raises:
        ValueError: If image IDs repeat, the split names are wrong, or one
            group mixes classes or skin-tone groups.
    """
    if set(fractions) != set(SPLITS):
        raise ValueError(f"fractions must cover exactly {SPLITS}")
    groups = _groups(records)
    strata: dict[tuple[str, str], list[str]] = defaultdict(list)
    for group_id, members in groups.items():
        strata[(members[0].label, members[0].skin_tone)].append(group_id)

    assignment: dict[str, str] = {}
    for (label, tone), group_ids in sorted(strata.items()):
        rng = random.Random(f"{seed}:{label}:{tone}")
        order = sorted(group_ids)
        rng.shuffle(order)
        counts = dict.fromkeys(SPLITS, 0)
        for group_id in order:
            size = len(groups[group_id])
            total = sum(counts.values()) + size
            split = max(SPLITS, key=lambda s: fractions[s] * total - counts[s])
            counts[split] += size
            for record in groups[group_id]:
                assignment[record.image_id] = split
    return assignment


def _groups(records: Sequence[ImageRecord]) -> dict[str, list[ImageRecord]]:
    """Group records, checking IDs are unique and each group is one stratum."""
    seen: set[str] = set()
    groups: dict[str, list[ImageRecord]] = defaultdict(list)
    for record in records:
        if record.image_id in seen:
            raise ValueError(f"duplicate image ID {record.image_id}")
        seen.add(record.image_id)
        groups[record.group_id].append(record)
    for group_id, members in groups.items():
        if len({(m.label, m.skin_tone) for m in members}) > 1:
            raise ValueError(f"group {group_id} mixes classes or skin tones")
    return groups
