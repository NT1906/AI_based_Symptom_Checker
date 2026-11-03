"""Unit tests for the evaluation metrics and report.

Covers:
    - Confusion matrix, per-class scores and macro-F1 (classes without
      examples are skipped, not counted as 0).
    - Calibration error, skin-tone gap, and abstain coverage/selective accuracy.
    - The Markdown report lists every split, class and skin tone.

Owner: Nisarg (cv) · Task: S1-NIS-6 · Requirements: NFR-07
"""

import pytest
from cv_metrics import (
    confusion_matrix,
    evaluate,
    expected_calibration_error,
    format_report,
    macro_f1,
    per_class_scores,
)

NAMES = ("eczema", "urticaria", "unclear")


def test_confusion_matrix_rows_are_truth() -> None:
    assert confusion_matrix([0, 0, 1], [0, 1, 1], 3) == [
        [1, 1, 0],
        [0, 1, 0],
        [0, 0, 0],
    ]


def test_per_class_scores() -> None:
    scores = per_class_scores([[3, 1], [0, 2]])

    assert scores[0] == {
        "precision": 1.0,
        "recall": 0.75,
        "f1": pytest.approx(6 / 7),
        "support": 4,
    }
    assert scores[1]["precision"] == pytest.approx(2 / 3)


def test_macro_f1_skips_classes_without_examples() -> None:
    assert macro_f1([[2, 0, 0], [0, 2, 0], [0, 0, 0]]) == 1.0
    assert macro_f1([[0]]) == 0.0


def test_ece_is_zero_when_confidence_matches_accuracy() -> None:
    assert expected_calibration_error([1.0, 1.0], [True, True]) == 0.0
    assert expected_calibration_error([0.9, 0.9], [False, False]) == pytest.approx(0.9)
    assert expected_calibration_error([], []) == 0.0


def test_evaluate_reports_abstain_and_skin_tone_gap() -> None:
    probabilities = [
        [0.9, 0.05, 0.05],  # eczema, sure, correct
        [0.4, 0.35, 0.25],  # eczema, unsure -> abstains to unclear; truth eczema
        [0.1, 0.8, 0.1],  # urticaria, sure, correct
        [0.7, 0.2, 0.1],  # eczema, sure, wrong (truth unclear)
    ]
    truth = [0, 0, 1, 2]
    tones = ["light", "dark", "light", "dark"]

    m = evaluate(probabilities, truth, tones, NAMES, abstain_threshold=0.55)

    assert m["images"] == 4
    assert m["accuracy"] == 0.75
    assert m["abstain"]["coverage"] == 0.75
    assert m["abstain"]["selective_accuracy"] == pytest.approx(2 / 3)
    assert m["macro_f1_by_skin_tone"]["light"] == 1.0
    assert m["skin_tone_gap"] == pytest.approx(1.0 - m["macro_f1_by_skin_tone"]["dark"])
    assert set(m["per_class"]) == set(NAMES)


def test_report_lists_splits_classes_and_tones() -> None:
    m = evaluate([[0.9, 0.05, 0.05]], [0], ["medium"], NAMES, 0.55)

    report = format_report({"backbone": "efficientnet_b0", "epochs": 1}, {"test": m})

    assert report.startswith("# CV baseline: efficientnet_b0")
    assert "## test (1 images)" in report
    assert all(f"`{name}`" in report for name in NAMES)
    assert "| medium | 1.000 |" in report
