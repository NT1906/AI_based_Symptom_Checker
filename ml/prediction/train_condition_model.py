"""Train condition model v2 (scikit-learn), compare it with the baseline, export ONNX.

Responsibilities:
    - Turn cases into multi-hot vectors over the 100 canonical symptoms.
    - Fit a multinomial logistic regression; pick its regularisation on the
      validation set (never on test).
    - Rank like the server will: only conditions that explain at least one
      reported symptom, by probability, ties by ID.
    - Choose the "Likely" probability threshold on validation so that Likely
      answers are right at least ``LIKELY_TARGET_PRECISION`` of the time.
    - Compare v2 with the baseline on the same held-out test cases.
    - Export to ONNX (``skl2onnx``) with the feature order, classes and
      thresholds in the model metadata, then check ONNX Runtime matches
      scikit-learn (parity).
    - Write ``condition_v2.onnx``, ``metrics.json`` and ``report.md``.

Usage (from the repository root; needs ``ml/prediction/requirements.txt``)::

    python ml/prediction/train_condition_model.py --output-dir ml/checkpoints/condition_v2

Takes a few seconds on a laptop CPU. Outputs are git-ignored; the model goes to
Hugging Face Hub (AI_RULES.md §7.8).

Owner: Nisarg (prediction) · Task: S2-NIS-3 · Requirements: FR-05, NFR-07
"""

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
from baseline_scoring import baseline_ranking
from condition_cases import Case, Dataset, build_splits, load_dataset, perturb_cases
from condition_metrics import (
    comparison_table,
    macro_f1,
    precision_above,
    top_k_accuracy,
)

log = logging.getLogger("prediction.train")

MODEL_VERSION = "2.0.0"
C_GRID = (0.1, 0.3, 1.0, 3.0, 10.0)
LIKELY_TARGET_PRECISION = 0.9
THRESHOLD_GRID = tuple(round(0.30 + 0.05 * i, 2) for i in range(14))  # 0.30 … 0.95
POSSIBLE_MIN_PROBABILITY = 0.15
PARITY_ATOL = 1e-5
STRESS_SEED = 99
# (name, unrelated symptoms added, hallmarks removed)
STRESS_TESTS = (
    ("+1 unrelated symptom", 1, False),
    ("+2 unrelated symptoms", 2, False),
    ("+3 unrelated symptoms", 3, False),
    ("hallmarks missing", 0, True),
    ("hallmarks missing, +2 unrelated", 2, True),
)
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "checkpoints" / "condition_v2"


def featurize(cases: Sequence[Case], symptom_ids: Sequence[str]) -> np.ndarray:
    """Multi-hot float32 matrix: one row per case, one column per symptom ID."""
    column = {symptom: i for i, symptom in enumerate(symptom_ids)}
    matrix = np.zeros((len(cases), len(symptom_ids)), dtype=np.float32)
    for row, case in enumerate(cases):
        for symptom in case.symptoms:
            matrix[row, column[symptom]] = 1.0
    return matrix


def rank_with_probabilities(
    probabilities: np.ndarray, classes: Sequence[str], case: Case, dataset: Dataset
) -> list[tuple[str, float]]:
    """Matching conditions by probability (ties by ID), as the server ranks them."""
    reported = set(case.symptoms)
    explains = {
        c.id for c in dataset.conditions if any(s in reported for s, _ in c.symptoms)
    }
    scored = [(-float(p), cid) for cid, p in zip(classes, probabilities, strict=True)]
    return [(cid, -neg) for neg, cid in sorted(scored) if cid in explains]


def evaluate_model(
    probabilities: np.ndarray,
    classes: Sequence[str],
    cases: Sequence[Case],
    dataset: Dataset,
) -> dict[str, float]:
    """Top-1, top-3 and macro-F1 of the model's rankings."""
    rankings = [
        [cid for cid, _ in rank_with_probabilities(p, classes, case, dataset)]
        for p, case in zip(probabilities, cases, strict=True)
    ]
    return _metrics(rankings, cases)


def evaluate_baseline(cases: Sequence[Case], dataset: Dataset) -> dict[str, float]:
    """Top-1, top-3 and macro-F1 of the S1-NIS-1 baseline on the same cases."""
    rankings = [baseline_ranking(dataset.conditions, case.symptoms) for case in cases]
    return _metrics(rankings, cases)


def _metrics(rankings: list[list[str]], cases: Sequence[Case]) -> dict[str, float]:
    truths = [case.condition_id for case in cases]
    top1 = [ranking[0] if ranking else None for ranking in rankings]
    return {
        "top1": top_k_accuracy(rankings, truths, 1),
        "top3": top_k_accuracy(rankings, truths, 3),
        "macro_f1": macro_f1(top1, truths),
    }


def choose_likely_threshold(
    probabilities: np.ndarray,
    classes: Sequence[str],
    cases: Sequence[Case],
    dataset: Dataset,
) -> tuple[float, float, int]:
    """Lowest threshold whose top-1 answers are right ≥ the target precision.

    Returns:
        ``(threshold, precision, cases above it)``; the highest grid value if
        none reaches the target, so "Likely" stays rare rather than wrong.
    """
    confidences, correct = [], []
    for p, case in zip(probabilities, cases, strict=True):
        ranking = rank_with_probabilities(p, classes, case, dataset)
        confidences.append(ranking[0][1] if ranking else 0.0)
        correct.append(bool(ranking) and ranking[0][0] == case.condition_id)
    for threshold in THRESHOLD_GRID:
        precision, count = precision_above(confidences, correct, threshold)
        if count and precision >= LIKELY_TARGET_PRECISION:
            return threshold, precision, count
    precision, count = precision_above(confidences, correct, THRESHOLD_GRID[-1])
    return THRESHOLD_GRID[-1], precision, count


def fit(splits: dict[str, list[Case]], dataset: Dataset) -> tuple[Any, float]:
    """Fit logistic regression for each C; keep the best validation top-1."""
    from sklearn.linear_model import LogisticRegression

    x_train = featurize(splits["train"], dataset.symptom_ids)
    y_train = [case.condition_id for case in splits["train"]]
    x_val = featurize(splits["val"], dataset.symptom_ids)
    best: tuple[float, float, Any] | None = None
    for c in C_GRID:
        model = LogisticRegression(C=c, max_iter=5000)
        model.fit(x_train, y_train)
        top1 = evaluate_model(
            model.predict_proba(x_val), model.classes_, splits["val"], dataset
        )["top1"]
        log.info("C=%s val top-1 %.4f", c, top1)
        if best is None or top1 > best[0]:
            best = (top1, c, model)
    assert best is not None
    return best[2], best[1]


def export_onnx(
    model: Any, dataset: Dataset, metadata: dict[str, str], path: Path
) -> None:
    """Export to ONNX with probabilities as a plain tensor and metadata attached."""
    import onnx
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType

    onx = convert_sklearn(
        model,
        initial_types=[("symptoms", FloatTensorType([None, len(dataset.symptom_ids)]))],
        options={id(model): {"zipmap": False}},
        target_opset=17,
    )
    onnx.helper.set_model_props(onx, metadata)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(onx.SerializeToString())


def onnx_parity(model: Any, path: Path, features: np.ndarray) -> float:
    """Largest absolute difference between ONNX Runtime and scikit-learn probabilities."""
    import onnxruntime

    session = onnxruntime.InferenceSession(
        str(path), providers=["CPUExecutionProvider"]
    )
    onnx_probs = session.run(["probabilities"], {"symptoms": features})[0]
    return float(np.max(np.abs(onnx_probs - model.predict_proba(features))))


def run(output_dir: Path, scale: float = 1.0) -> dict[str, Any]:
    """Train, compare, export and check parity; write the report files."""
    dataset = load_dataset()
    splits = build_splits(dataset, scale)
    model, c = fit(splits, dataset)
    classes = [str(cid) for cid in model.classes_]
    val_probs = model.predict_proba(featurize(splits["val"], dataset.symptom_ids))
    likely, likely_precision, likely_count = choose_likely_threshold(
        val_probs, classes, splits["val"], dataset
    )
    x_test = featurize(splits["test"], dataset.symptom_ids)
    results = {
        "baseline": evaluate_baseline(splits["test"], dataset),
        "v2": evaluate_model(
            model.predict_proba(x_test), classes, splits["test"], dataset
        ),
    }
    metadata = {
        "model_version": MODEL_VERSION,
        "dataset_version": dataset.version,
        "symptom_ids": json.dumps(list(dataset.symptom_ids)),
        "condition_ids": json.dumps(classes),
        "likely_min_probability": str(likely),
        "possible_min_probability": str(POSSIBLE_MIN_PROBABILITY),
    }
    onnx_path = output_dir / "condition_v2.onnx"
    export_onnx(model, dataset, metadata, onnx_path)
    parity = onnx_parity(model, onnx_path, x_test)
    if parity > PARITY_ATOL:
        raise RuntimeError(f"ONNX parity failed: max difference {parity:.2e}")
    report = {
        "model_version": MODEL_VERSION,
        "dataset_version": dataset.version,
        "cases": {split: len(cases) for split, cases in splits.items()},
        "regularisation_c": c,
        "likely_min_probability": likely,
        "likely_val_precision": round(likely_precision, 4),
        "likely_val_cases": likely_count,
        "possible_min_probability": POSSIBLE_MIN_PROBABILITY,
        "onnx_parity_max_abs_diff": parity,
        "onnx_bytes": onnx_path.stat().st_size,
        "test": results,
        "stress": stress_tests(model, classes, splits["test"], dataset),
    }
    (output_dir / "metrics.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "report.md").write_text(format_report(report), encoding="utf-8")
    return report


def stress_tests(
    model: Any, classes: Sequence[str], cases: Sequence[Case], dataset: Dataset
) -> dict[str, dict[str, dict[str, float]]]:
    """Baseline vs v2 on harder copies of the test cases (``STRESS_TESTS``)."""
    results = {}
    for name, extra, drop in STRESS_TESTS:
        hard = perturb_cases(cases, dataset, extra, drop, STRESS_SEED)
        probabilities = model.predict_proba(featurize(hard, dataset.symptom_ids))
        results[name] = {
            "baseline": evaluate_baseline(hard, dataset),
            "v2": evaluate_model(probabilities, classes, hard, dataset),
        }
    return results


def format_report(report: dict[str, Any]) -> str:
    """Markdown summary of one training run."""
    table = comparison_table(
        [
            ("Baseline (S1-NIS-1)", report["test"]["baseline"]),
            ("v2 logistic regression", report["test"]["v2"]),
        ]
    )
    return (
        "# Condition model v2: training report\n\n"
        f"Dataset {report['dataset_version']}, synthetic cases {report['cases']}, "
        f"C = {report['regularisation_c']}.\n\n"
        f"## Held-out test cases\n\n{table}\n\n"
        f"- Likely when probability ≥ {report['likely_min_probability']} "
        f"(validation precision {report['likely_val_precision']}, "
        f"{report['likely_val_cases']} cases); Possible when ≥ {report['possible_min_probability']}.\n"
        f"- ONNX parity: max difference {report['onnx_parity_max_abs_diff']:.2e}; "
        f"file size {report['onnx_bytes']} bytes.\n\n"
        "## Stress tests (top-1 accuracy, baseline → v2)\n\n"
        + "\n".join(
            f"- {name}: {r['baseline']['top1']:.3f} → {r['v2']['top1']:.3f}"
            for name, r in report["stress"].items()
        )
        + "\n"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Command line entry point."""
    parser = argparse.ArgumentParser(description="Train condition model v2.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--scale", type=float, default=1.0, help="case count multiplier"
    )
    args = parser.parse_args(argv)
    report = run(args.output_dir, args.scale)
    log.info("test: %s", json.dumps(report["test"]))
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sys.exit(main())
