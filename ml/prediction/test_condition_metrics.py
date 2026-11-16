"""Unit tests for the condition-model ranking metrics.

Covers top-k accuracy, macro-F1 (including missing answers), precision above
a threshold, and the Markdown comparison table, with tiny hand-made inputs.

Owner: Nisarg (prediction) · Task: S2-NIS-3 · Requirements: NFR-07
"""

import pytest
from condition_metrics import (
    comparison_table,
    macro_f1,
    precision_above,
    top_k_accuracy,
)


def test_top_k_accuracy_counts_hits_within_k() -> None:
    rankings = [["a", "b", "c"], ["b", "a"], []]
    truths = ["c", "a", "a"]

    assert top_k_accuracy(rankings, truths, 1) == 0.0
    assert top_k_accuracy(rankings, truths, 3) == pytest.approx(2 / 3)


def test_top_k_accuracy_of_no_cases_is_zero() -> None:
    assert top_k_accuracy([], [], 3) == 0.0


def test_macro_f1_is_perfect_for_perfect_answers() -> None:
    assert macro_f1(["a", "b"], ["a", "b"]) == 1.0


def test_macro_f1_counts_a_missing_answer_as_wrong() -> None:
    assert macro_f1([None, "b"], ["a", "b"]) == pytest.approx(0.5)


def test_macro_f1_of_no_cases_is_zero() -> None:
    assert macro_f1([], []) == 0.0


def test_precision_above_only_counts_confident_answers() -> None:
    assert precision_above([0.9, 0.8, 0.2], [True, False, True], 0.5) == (0.5, 2)
    assert precision_above([0.1], [True], 0.5) == (0.0, 0)


def test_comparison_table_has_one_row_per_model() -> None:
    table = comparison_table([("m1", {"top1": 0.5, "top3": 0.75, "macro_f1": 0.25})])

    assert table.splitlines()[-1] == "| m1 | 0.500 | 0.750 | 0.250 |"
