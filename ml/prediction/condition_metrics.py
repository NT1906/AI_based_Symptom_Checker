"""Ranking metrics for condition models: top-k accuracy and macro-F1.

Responsibilities:
    - Top-1 and top-3 accuracy over ranked condition lists.
    - Macro-F1 of the top-1 answer (every condition counts equally).
    - Precision of the top-1 answer above a confidence threshold, used to
      choose when v2 may say "Likely".
    - A Markdown comparison table for the report.

Pure Python, so the ML CI can test it.

Owner: Nisarg (prediction) · Task: S2-NIS-3 · Requirements: FR-05, NFR-07
"""

from collections.abc import Sequence


def top_k_accuracy(
    rankings: Sequence[Sequence[str]], truths: Sequence[str], k: int
) -> float:
    """Share of cases whose true condition is in the first ``k`` of the ranking.

    Example:
        >>> top_k_accuracy([["a", "b"], ["c"]], ["b", "a"], k=2)
        0.5
    """
    if not truths:
        return 0.0
    hits = sum(
        truth in ranking[:k] for ranking, truth in zip(rankings, truths, strict=True)
    )
    return hits / len(truths)


def macro_f1(predicted: Sequence[str | None], truths: Sequence[str]) -> float:
    """Macro-averaged F1 of top-1 answers over the true labels' classes.

    ``None`` (no answer) counts as wrong for its case.

    Example:
        >>> macro_f1(["a", "b", "b"], ["a", "b", "a"])
        0.6666666666666666
    """
    labels = sorted(set(truths))
    if not labels:
        return 0.0
    scores = []
    for label in labels:
        tp = sum(
            p == label and t == label for p, t in zip(predicted, truths, strict=True)
        )
        fp = sum(
            p == label and t != label for p, t in zip(predicted, truths, strict=True)
        )
        fn = sum(
            p != label and t == label for p, t in zip(predicted, truths, strict=True)
        )
        scores.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    return sum(scores) / len(scores)


def precision_above(
    confidences: Sequence[float], correct: Sequence[bool], threshold: float
) -> tuple[float, int]:
    """Top-1 precision and count among cases with confidence ≥ ``threshold``.

    Example:
        >>> precision_above([0.9, 0.8, 0.2], [True, False, True], 0.5)
        (0.5, 2)
    """
    chosen = [
        ok for conf, ok in zip(confidences, correct, strict=True) if conf >= threshold
    ]
    if not chosen:
        return 0.0, 0
    return sum(chosen) / len(chosen), len(chosen)


def comparison_table(rows: Sequence[tuple[str, dict[str, float]]]) -> str:
    """Markdown table: one row per model, columns top-1, top-3, macro-F1."""
    lines = [
        "| Model | Top-1 accuracy | Top-3 accuracy | Macro-F1 (top-1) |",
        "|---|---|---|---|",
    ]
    for name, m in rows:
        lines.append(
            f"| {name} | {m['top1']:.3f} | {m['top3']:.3f} | {m['macro_f1']:.3f} |"
        )
    return "\n".join(lines)
