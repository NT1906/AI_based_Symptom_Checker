"""Unit tests for condition model v2 training, export and ONNX parity.

Covers:
    - A small end-to-end run writes the ONNX model, metrics and report; the
      ONNX metadata carries the feature order, classes and thresholds; ONNX
      Runtime matches scikit-learn.
    - Features are multi-hot in vocabulary order.
    - Rankings leave out conditions that explain no reported symptom.
    - The "Likely" threshold falls back to the strictest value when no
      threshold reaches the target precision.

Skipped when NumPy, scikit-learn, skl2onnx or ONNX Runtime are missing (the ML
CI installs only light dependencies).

Owner: Nisarg (prediction) · Task: S2-NIS-3 · Requirements: FR-05, NFR-07
"""

import json
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("sklearn")
pytest.importorskip("skl2onnx")
onnxruntime = pytest.importorskip("onnxruntime")

from condition_cases import Case, load_dataset
from train_condition_model import (
    THRESHOLD_GRID,
    choose_likely_threshold,
    featurize,
    rank_with_probabilities,
    run,
)

DATASET = load_dataset()


def test_small_run_writes_model_metrics_and_report(tmp_path: Path) -> None:
    report = run(tmp_path, scale=0.05)

    model_path = tmp_path / "condition_v2.onnx"
    assert model_path.exists() and (tmp_path / "report.md").exists()
    assert (
        json.loads((tmp_path / "metrics.json").read_text())["model_version"] == "2.0.0"
    )
    assert report["onnx_parity_max_abs_diff"] <= 1e-5
    assert set(report["test"]) == {"baseline", "v2"}
    assert len(report["stress"]) == 5
    meta = onnxruntime.InferenceSession(str(model_path)).get_modelmeta()
    props = meta.custom_metadata_map
    assert json.loads(props["symptom_ids"]) == list(DATASET.symptom_ids)
    assert len(json.loads(props["condition_ids"])) == 38
    assert float(props["likely_min_probability"]) in THRESHOLD_GRID


def test_features_are_multi_hot_in_vocabulary_order() -> None:
    first, last = DATASET.symptom_ids[0], DATASET.symptom_ids[-1]

    matrix = featurize([Case((first, last), "x")], DATASET.symptom_ids)

    assert matrix.dtype == np.float32
    assert matrix[0, 0] == matrix[0, -1] == 1.0
    assert matrix.sum() == 2.0


def test_ranking_leaves_out_conditions_that_explain_nothing() -> None:
    classes = [c.id for c in DATASET.conditions]
    probabilities = np.full(len(classes), 1 / len(classes))
    case = Case(("pain_behind_eyes",), "dengue")

    ranking = rank_with_probabilities(probabilities, classes, case, DATASET)

    explaining = {
        c.id for c in DATASET.conditions if "pain_behind_eyes" in dict(c.symptoms)
    }
    assert {cid for cid, _ in ranking} == explaining


def test_likely_threshold_falls_back_to_the_strictest_value() -> None:
    classes = [c.id for c in DATASET.conditions]
    wrong = np.zeros((1, len(classes)))
    wrong[0, classes.index("common_cold")] = 1.0
    case = Case(("runny_nose",), "allergic_rhinitis")

    threshold, precision, _ = choose_likely_threshold(wrong, classes, [case], DATASET)

    assert threshold == THRESHOLD_GRID[-1]
    assert precision == 0.0
