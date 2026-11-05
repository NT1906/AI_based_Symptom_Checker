"""Read SCIN and Fitzpatrick17k metadata into one list of image records.

Responsibilities:
    - Define ``ImageRecord``, one row of the split manifest.
    - Turn SCIN cases (up to 3 images each) and Fitzpatrick17k rows into
      records with class, skin-tone group, split group and download URL.
    - Count every left-out image by reason, for the dataset summary.

Only metadata is read here; no image is downloaded or opened.

Owner: Nisarg (cv) · Task: S1-NIS-5 · Requirements: NFR-07
"""

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath

from image_labels import (
    fitzpatrick17k_label,
    parse_fitzpatrick_type,
    scin_case_label,
    scin_top_labels,
    skin_tone_group,
)

SCIN = "scin"
FITZPATRICK17K = "fitzpatrick17k"
SCIN_BUCKET_URL = "https://storage.googleapis.com/dx-scin-public-data"
SCIN_IMAGE_COLUMNS = ("image_1_path", "image_2_path", "image_3_path")
SCIN_SKIN_TYPE_COLUMNS = tuple(
    f"dermatologist_fitzpatrick_skin_type_label_{i}" for i in (1, 2, 3)
)

Row = Mapping[str, str]


@dataclass(frozen=True)
class ImageRecord:
    """One image in the dataset.

    Attributes:
        image_id: Unique ID (SCIN file stem, Fitzpatrick17k md5 hash).
        source: ``scin`` or ``fitzpatrick17k``.
        group_id: Images with the same group always land in the same split
            (one SCIN case; one Fitzpatrick17k image).
        label: Model class.
        skin_tone: Skin-tone group, or ``unknown``.
        source_label: The source's own condition name (SCIN: the top-weighted
            names joined by ``|``), for review.
        reason: Why the label was chosen (``top_label``, ``no_label``, ...).
        url: Where the image is downloaded from.
    """

    image_id: str
    source: str
    group_id: str
    label: str
    skin_tone: str
    source_label: str
    reason: str
    url: str


def read_scin(
    cases: Iterable[Row],
    labels: Iterable[Row],
    groups: Mapping[str, tuple[int, ...]],
) -> tuple[list[ImageRecord], Counter[str]]:
    """Build records for every image of every SCIN case.

    Args:
        cases: Rows of ``scin_cases.csv``.
        labels: Rows of ``scin_labels.csv``.
        groups: Skin-tone groups from the config.

    Returns:
        The records, and left-out image counts by reason.

    Raises:
        ValueError: If a case has no row in ``scin_labels.csv``.
    """
    labels_by_case = {row["case_id"]: row for row in labels}
    paths_by_case = {
        case["case_id"]: [c.strip() for c in _image_paths(case)] for case in cases
    }
    # Why: SCIN reuses a few image files across cases, which would put one
    # image in two splits (or under two labels); those images are left out.
    uses = Counter(path for paths in paths_by_case.values() for path in paths)
    records: list[ImageRecord] = []
    left_out: Counter[str] = Counter()
    for case_id, all_paths in paths_by_case.items():
        if case_id not in labels_by_case:
            raise ValueError(f"SCIN case {case_id} has no labels row")
        label_row = labels_by_case[case_id]
        paths = [path for path in all_paths if uses[path] == 1]
        if len(paths) < len(all_paths):
            left_out[f"{SCIN}:shared_between_cases"] += len(all_paths) - len(paths)
        weighted = label_row["weighted_skin_condition_label"]
        decision = scin_case_label(weighted)
        if decision.label is None:
            left_out[f"{SCIN}:{decision.reason}"] += len(paths)
            continue
        types = [
            t
            for c in SCIN_SKIN_TYPE_COLUMNS
            if (t := parse_fitzpatrick_type(label_row.get(c, ""))) is not None
        ]
        tone = skin_tone_group(types, groups)
        for path in paths:
            records.append(
                ImageRecord(
                    image_id=PurePosixPath(path).stem,
                    source=SCIN,
                    group_id=f"{SCIN}:{case_id}",
                    label=decision.label,
                    skin_tone=tone,
                    source_label="|".join(scin_top_labels(weighted)),
                    reason=decision.reason,
                    url=f"{SCIN_BUCKET_URL}/{path}",
                )
            )
    return records, left_out


def _image_paths(case: Row) -> list[str]:
    """The non-empty image paths of one SCIN case."""
    return [case[c] for c in SCIN_IMAGE_COLUMNS if case.get(c, "").strip()]


def read_fitzpatrick17k(
    rows: Iterable[Row], groups: Mapping[str, tuple[int, ...]]
) -> tuple[list[ImageRecord], Counter[str]]:
    """Build records for the Fitzpatrick17k images of the mapped classes.

    Args:
        rows: Rows of ``fitzpatrick17k.csv``.
        groups: Skin-tone groups from the config.

    Returns:
        The records, and left-out image counts by reason.
    """
    records: list[ImageRecord] = []
    left_out: Counter[str] = Counter()
    for row in rows:
        decision = fitzpatrick17k_label(row["label"], row.get("qc", ""))
        if decision.label is None:
            left_out[f"{FITZPATRICK17K}:{decision.reason}"] += 1
            continue
        if not row["url"].strip():
            left_out[f"{FITZPATRICK17K}:no_url"] += 1
            continue
        skin_type = parse_fitzpatrick_type(row["fitzpatrick_scale"])
        image_id = row["md5hash"].strip()
        records.append(
            ImageRecord(
                image_id=image_id,
                source=FITZPATRICK17K,
                # Why: atlas pages group images by condition, not by patient,
                # so each image is its own group; near-duplicates are caught
                # by the perceptual-hash step in clean_images.py.
                group_id=f"{FITZPATRICK17K}:{image_id}",
                label=decision.label,
                skin_tone=skin_tone_group(
                    [] if skin_type is None else [skin_type], groups
                ),
                source_label=row["label"].strip(),
                reason=decision.reason,
                url=row["url"].strip(),
            )
        )
    return records, left_out
