"""Unit tests for label and skin-tone mapping.

Covers:
    - SCIN: top-weighted label wins; ties, look-alikes, no label, outside
      classes; malformed values are rejected.
    - Fitzpatrick17k: mapped labels, unused labels, wrongly-labelled QC.
    - Fitzpatrick type parsing and skin-tone grouping.
    - Every mapping target is a class in the CV config.

Owner: Nisarg (cv) · Task: S1-NIS-5 · Requirements: NFR-07
"""

import sys
from pathlib import Path

import pytest
from image_labels import (
    FITZPATRICK17K_LABELS,
    SCIN_LABELS,
    SCIN_LEFT_OUT,
    UNCLEAR,
    LabelDecision,
    fitzpatrick17k_label,
    parse_fitzpatrick_type,
    scin_case_label,
    scin_top_labels,
    skin_tone_group,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "cv"))
from train_config import load_config

GROUPS = {"light": (1, 2), "medium": (3, 4), "dark": (5, 6)}


def test_scin_top_weighted_class_wins() -> None:
    decision = scin_case_label("{'Tinea': 0.55, 'Eczema': 0.45}")

    assert decision == LabelDecision("fungal_infection", "top_label")


def test_scin_tie_within_one_class_keeps_the_class() -> None:
    weighted = "{'Cellulitis': 0.5, 'Cellulitis of hand excluding finger': 0.5}"

    assert scin_case_label(weighted).label == "cellulitis"


def test_scin_tie_between_outcomes_is_left_out() -> None:
    decision = scin_case_label("{'Eczema': 0.41, 'Psoriasis': 0.41, 'Acne': 0.18}")

    assert decision == LabelDecision(None, "tied_top_labels")


def test_scin_class_look_alike_is_left_out() -> None:
    assert scin_case_label("{'Tinea Versicolor': 1.0}").label is None


def test_scin_label_outside_classes_is_unclear() -> None:
    decision = scin_case_label("{'Psoriasis': 0.7, 'Eczema': 0.3}")

    assert decision == LabelDecision(UNCLEAR, "outside_classes")


@pytest.mark.parametrize("value", ["", "  ", "{}"])
def test_scin_case_without_label_is_unclear(value: str) -> None:
    assert scin_case_label(value) == LabelDecision(UNCLEAR, "no_label")


def test_scin_rejects_malformed_label() -> None:
    with pytest.raises(TypeError):
        scin_case_label("['Eczema']")
    with pytest.raises(ValueError):
        scin_case_label("{'Eczema': ")


def test_scin_top_labels_are_sorted() -> None:
    assert scin_top_labels("{'b': 0.5, 'a': 0.5, 'c': 0.1}") == ("a", "b")


def test_fitzpatrick17k_maps_acne_variants() -> None:
    assert fitzpatrick17k_label("acne vulgaris", "").label == "acne"
    assert fitzpatrick17k_label("acne", "1 Diagnostic").label == "acne"


def test_fitzpatrick17k_unmapped_label_is_left_out_not_unclear() -> None:
    assert fitzpatrick17k_label("psoriasis", "") == LabelDecision(None, "not_used")


def test_fitzpatrick17k_wrongly_labelled_is_left_out() -> None:
    decision = fitzpatrick17k_label("scabies", "3 Wrongly labelled")

    assert decision == LabelDecision(None, "wrongly_labelled")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("FST3", 3),
        ("fst6", 6),
        ("2", 2),
        ("-1", None),
        ("", None),
        ("NONE_IDENTIFIED", None),
        ("7", None),
    ],
)
def test_parse_fitzpatrick_type(value: str, expected: int | None) -> None:
    assert parse_fitzpatrick_type(value) == expected


def test_skin_tone_uses_lower_median_estimate() -> None:
    assert skin_tone_group([5, 2, 3], GROUPS) == "medium"
    assert skin_tone_group([2, 5], GROUPS) == "light"


def test_skin_tone_without_estimate_is_unknown() -> None:
    assert skin_tone_group([], GROUPS) == "unknown"


def test_mapping_targets_are_config_classes_or_merged() -> None:
    config = load_config()
    classes = set(config.class_names) | set(config.data.merged_into_unclear)

    assert set(SCIN_LABELS.values()) <= classes
    assert set(FITZPATRICK17K_LABELS.values()) <= classes
    assert UNCLEAR in classes


def test_look_alikes_never_overlap_the_mapping() -> None:
    assert SCIN_LEFT_OUT.isdisjoint(SCIN_LABELS)
