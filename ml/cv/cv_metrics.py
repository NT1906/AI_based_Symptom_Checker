"""Evaluation metrics and the metrics report for the skin-image model.

Responsibilities:
    - Compute the metrics in docs/cv-plan.md §6 from predicted probabilities:
      macro-F1, per-class precision/recall/F1, confusion matrix, macro-F1 per
      skin-tone group and the largest gap, calibration error (ECE), and
      selective accuracy vs coverage at the abstain threshold.
    - Render a Markdown report from those numbers.

Standard library only, so CI can test it without torch or scikit-learn.

Owner: Nisarg (cv) · Task: S1-NIS-6 · Requirements: NFR-07
"""

from collections.abc import Sequence
from typing import Any

Matrix = list[list[int]]
GAP_GROUPS = ("light", "medium", "dark")
ECE_BINS = 15


def confusion_matrix(truth: Sequence[int], predicted: Sequence[int], n: int) -> Matrix:
    """Rows are true classes, columns predicted classes."""
    matrix = [[0] * n for _ in range(n)]
    for t, p in zip(truth, predicted, strict=True):
        matrix[t][p] += 1
    return matrix


def per_class_scores(matrix: Matrix) -> list[dict[str, float]]:
    """Precision, recall, F1 and support for each class (0 when undefined)."""
    scores = []
    for k, row in enumerate(matrix):
        support = sum(row)
        predicted = sum(r[k] for r in matrix)
        hits = row[k]
        precision = hits / predicted if predicted else 0.0
        recall = hits / support if support else 0.0
        total = precision + recall
        f1 = 2 * precision * recall / total if total else 0.0
        scores.append(
            {"precision": precision, "recall": recall, "f1": f1, "support": support}
        )
    return scores


def macro_f1(matrix: Matrix) -> float:
    """Mean F1 over the classes that have at least one true example.

    Example:
        >>> round(macro_f1([[2, 0], [1, 1]]), 3)
        0.733
    """
    scores = [s for s in per_class_scores(matrix) if s["support"]]
    return sum(s["f1"] for s in scores) / len(scores) if scores else 0.0


def expected_calibration_error(
    confidences: Sequence[float], correct: Sequence[bool], bins: int = ECE_BINS
) -> float:
    """Weighted gap between confidence and accuracy over equal-width bins."""
    total = len(confidences)
    if total == 0:
        return 0.0
    error = 0.0
    for b in range(bins):
        low, high = b / bins, (b + 1) / bins
        members = [
            i
            for i, c in enumerate(confidences)
            if low < c <= high or (b == 0 and c == 0.0)
        ]
        if members:
            accuracy = sum(correct[i] for i in members) / len(members)
            confidence = sum(confidences[i] for i in members) / len(members)
            error += len(members) / total * abs(accuracy - confidence)
    return error


def evaluate(
    probabilities: Sequence[Sequence[float]],
    truth: Sequence[int],
    skin_tones: Sequence[str],
    class_names: Sequence[str],
    abstain_threshold: float,
) -> dict[str, Any]:  # Any: JSON-ready nested report
    """All metrics for one split.

    Args:
        probabilities: Softmax output per image.
        truth: True class index per image.
        skin_tones: Skin-tone group per image.
        class_names: Names in model output order; ``unclear`` is last.
        abstain_threshold: Below this top probability the answer is ``unclear``.

    Returns:
        A JSON-ready dict of metrics.
    """
    n = len(class_names)
    unclear = n - 1
    predicted = [max(range(n), key=lambda k: p[k]) for p in probabilities]
    top = [max(p) for p in probabilities]
    answered = [c >= abstain_threshold for c in top]
    final = [p if a else unclear for p, a in zip(predicted, answered, strict=True)]
    correct = [p == t for p, t in zip(predicted, truth, strict=True)]
    matrix = confusion_matrix(truth, predicted, n)

    by_tone: dict[str, float] = {}
    for tone in sorted(set(skin_tones)):
        idx = [i for i, s in enumerate(skin_tones) if s == tone]
        tone_matrix = confusion_matrix(
            [truth[i] for i in idx], [predicted[i] for i in idx], n
        )
        by_tone[tone] = macro_f1(tone_matrix)
    gap_values = [by_tone[g] for g in GAP_GROUPS if g in by_tone]
    kept = [i for i, a in enumerate(answered) if a]
    return {
        "images": len(truth),
        "macro_f1": macro_f1(matrix),
        "accuracy": sum(correct) / len(correct) if correct else 0.0,
        "per_class": dict(zip(class_names, per_class_scores(matrix), strict=True)),
        "confusion_matrix": matrix,
        "macro_f1_by_skin_tone": by_tone,
        "skin_tone_gap": max(gap_values) - min(gap_values) if gap_values else 0.0,
        "ece": expected_calibration_error(top, correct),
        "abstain": {
            "threshold": abstain_threshold,
            "coverage": len(kept) / len(truth) if truth else 0.0,
            "selective_accuracy": (
                sum(correct[i] for i in kept) / len(kept) if kept else 0.0
            ),
            "macro_f1": macro_f1(confusion_matrix(truth, final, n)),
        },
    }


def format_report(run: dict[str, Any], metrics: dict[str, Any]) -> str:  # Any: JSON
    """Markdown report for one run.

    Args:
        run: Run facts (backbone, epochs, best epoch, image counts, ...).
        metrics: Split name -> output of :func:`evaluate`.

    Returns:
        The report text.
    """
    lines = [f"# CV baseline: {run['backbone']}", ""]
    lines += [f"- **{key}:** {value}" for key, value in run.items()]
    for split, m in metrics.items():
        names = list(m["per_class"])
        lines += ["", f"## {split} ({m['images']} images)", ""]
        lines += [
            "| Metric | Value |",
            "|---|---|",
            f"| Macro-F1 | {m['macro_f1']:.3f} |",
            f"| Accuracy | {m['accuracy']:.3f} |",
            f"| Skin-tone gap (macro-F1) | {m['skin_tone_gap']:.3f} |",
            f"| ECE | {m['ece']:.3f} |",
            f"| Coverage at {m['abstain']['threshold']} | {m['abstain']['coverage']:.3f} |",
            f"| Selective accuracy | {m['abstain']['selective_accuracy']:.3f} |",
            f"| Macro-F1 with abstain | {m['abstain']['macro_f1']:.3f} |",
            "",
            "| Class | Precision | Recall | F1 | Support |",
            "|---|---|---|---|---|",
        ]
        lines += [
            f"| `{k}` | {s['precision']:.3f} | {s['recall']:.3f} | {s['f1']:.3f} | {s['support']} |"
            for k, s in m["per_class"].items()
        ]
        lines += ["", "| Skin tone | Macro-F1 |", "|---|---|"]
        lines += [f"| {t} | {v:.3f} |" for t, v in m["macro_f1_by_skin_tone"].items()]
        lines += ["", "Confusion matrix (rows true, columns predicted):", ""]
        lines += ["| | " + " | ".join(names) + " |", "|---" * (len(names) + 1) + "|"]
        lines += [
            f"| {names[i]} | " + " | ".join(str(v) for v in row) + " |"
            for i, row in enumerate(m["confusion_matrix"])
        ]
    return "\n".join(lines) + "\n"
