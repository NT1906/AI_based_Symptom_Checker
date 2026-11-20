"""Unit tests for condition model v2 on ONNX Runtime and its settings.

The tests build a tiny ONNX model in memory (MatMul + Add + Softmax, the same
inputs, outputs and metadata as the skl2onnx export), so no real model file
is downloaded or committed.

Covers:
    - Ranking: top 3, only conditions that explain a reported symptom,
      matched symptoms heaviest first, ties by condition ID, deterministic.
    - Labels: Likely needs the threshold and a hallmark; never a number.
    - Inputs: empty (error), unknown and duplicate IDs.
    - Loading: missing file, missing metadata, another dataset version,
      another vocabulary, unknown condition.
    - Settings: baseline by default; v2 from a path or the Hub; baseline
      fallback when v2 cannot load. End to end with the risk engine.

Owner: Nisarg (prediction) · Task: S2-NIS-3 · Requirements: FR-05, FR-23, NFR-07
Empty input returns no predictions: Nisarg · S2-NIS-28 (#348)
"""

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import pytest
from app.schemas.enums import ConfidenceLabel
from app.services.prediction import condition_model_config as config
from app.services.prediction.condition_catalog import ConditionDataError, get_catalog
from app.services.prediction.condition_model_config import (
    ConditionModelSettings,
    build_condition_model,
)
from app.services.prediction.condition_predictor import BaselineConditionModel
from app.services.prediction.onnx_condition_model import OnnxConditionModel
from app.services.prediction.result_composer import ResultComposer
from app.services.prediction.risk_engine import assess_risk
from app.services.prediction.risk_schemas import ReportedSymptom
from app.services.privacy.safety_guard import assert_safe_wording

onnx = pytest.importorskip("onnx")
from onnx import TensorProto, helper, numpy_helper  # noqa: E402

CATALOG = get_catalog()
SYMPTOMS = sorted(CATALOG.symptom_ids)
CONDITIONS = sorted(c.id for c in CATALOG.conditions)


def _weights(scale: float = 1.5) -> np.ndarray:
    """Symptom x condition weights: each condition's own symptoms, by weight."""
    weights = np.zeros((len(SYMPTOMS), len(CONDITIONS)), dtype=np.float32)
    for column, condition_id in enumerate(CONDITIONS):
        profile = CATALOG.get(condition_id)
        assert profile is not None
        for symptom in profile.symptoms:
            weights[SYMPTOMS.index(symptom.id), column] = scale * symptom.weight
    return weights


def _write_model(
    path: Path,
    weights: np.ndarray | None = None,
    symptoms: list[str] | None = None,
    conditions: list[str] | None = None,
    **meta: str,
) -> Path:
    """Write a softmax(x @ W) model with export-style metadata."""
    symptoms = symptoms or SYMPTOMS
    conditions = conditions or CONDITIONS
    w = _weights() if weights is None else weights
    graph = helper.make_graph(
        [
            helper.make_node("MatMul", ["symptoms", "W"], ["logits"]),
            helper.make_node("Softmax", ["logits"], ["probabilities"], axis=1),
        ],
        "tiny_condition_model",
        [
            helper.make_tensor_value_info(
                "symptoms", TensorProto.FLOAT, [None, len(symptoms)]
            )
        ],
        [
            helper.make_tensor_value_info(
                "probabilities", TensorProto.FLOAT, [None, len(conditions)]
            )
        ],
        initializer=[numpy_helper.from_array(w, name="W")],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    model.ir_version = 8
    props = {
        "model_version": "2.0.0-test",
        "dataset_version": CATALOG.dataset_version,
        "symptom_ids": json.dumps(symptoms),
        "condition_ids": json.dumps(conditions),
        "likely_min_probability": "0.5",
        "possible_min_probability": "0.15",
    }
    props.update(meta)
    helper.set_model_props(model, {k: v for k, v in props.items() if v != "-"})
    path.write_bytes(model.SerializeToString())
    return path


@pytest.fixture
def model(tmp_path: Path) -> OnnxConditionModel:
    return OnnxConditionModel(_write_model(tmp_path / "m.onnx"))


def test_ranks_top_three_conditions_that_explain_the_symptoms(
    model: OnnxConditionModel,
) -> None:
    predictions = model.predict(["fever", "pain_behind_eyes", "joint_pain"])

    assert [p.rank for p in predictions] == [1, 2, 3]
    assert predictions[0].condition_id == "dengue"
    for p in predictions:
        profile = CATALOG.get(p.condition_id)
        assert profile is not None
        assert set(p.matched_symptom_ids) <= {s.id for s in profile.symptoms}
        weights = [
            next(s.weight for s in profile.symptoms if s.id == m)
            for m in p.matched_symptom_ids
        ]
        assert weights == sorted(weights, reverse=True)
    assert "probab" not in predictions[0].model_dump_json()


def test_ties_are_broken_by_condition_id(tmp_path: Path) -> None:
    flat = np.zeros((len(SYMPTOMS), len(CONDITIONS)), dtype=np.float32)
    model = OnnxConditionModel(_write_model(tmp_path / "flat.onnx", weights=flat))

    ids = [p.condition_id for p in model.predict(["fever"])]

    explaining = sorted(
        c.id for c in CATALOG.conditions if any(s.id == "fever" for s in c.symptoms)
    )
    assert ids == explaining[:3]


def test_same_input_gives_the_same_ranking(model: OnnxConditionModel) -> None:
    first = model.predict(["cough", "fever", "fatigue"])

    for _ in range(50):
        assert model.predict(["fatigue", "cough", "fever"]) == first


def test_unknown_and_duplicate_ids_are_ignored(model: OnnxConditionModel) -> None:
    assert model.predict(["fever", "fever", "not_a_symptom"]) == model.predict(
        ["fever"]
    )
    assert model.predict(["not_a_symptom"]) == []


def test_empty_input_returns_no_predictions(model: OnnxConditionModel) -> None:
    assert model.predict([]) == []


@pytest.mark.parametrize(
    ("probability", "hallmark", "expected"),
    [
        (0.9, True, ConfidenceLabel.LIKELY),
        (0.9, False, ConfidenceLabel.POSSIBLE),
        (0.3, True, ConfidenceLabel.POSSIBLE),
        (0.15, True, ConfidenceLabel.POSSIBLE),
        (0.1, True, ConfidenceLabel.LESS_LIKELY),
    ],
)
def test_confidence_label_needs_threshold_and_hallmark_for_likely(
    model: OnnxConditionModel,
    probability: float,
    hallmark: bool,
    expected: ConfidenceLabel,
) -> None:
    assert model.confidence_label(probability, hallmark) is expected


def test_missing_model_file_is_reported(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="nothing.onnx"):
        OnnxConditionModel(tmp_path / "nothing.onnx")


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"likely_min_probability": "-"}, "metadata missing"),
        ({"dataset_version": "v99"}, "trained on dataset v99"),
        ({"symptoms": SYMPTOMS[:-1]}, "vocabulary differs"),
        ({"conditions": [*CONDITIONS[:-1], "made_up"]}, "unknown conditions"),
    ],
)
def test_model_that_does_not_fit_the_dataset_is_refused(
    tmp_path: Path, kwargs: dict[str, Any], message: str
) -> None:
    symptoms = kwargs.pop("symptoms", SYMPTOMS)
    weights = np.zeros((len(symptoms), len(CONDITIONS)), dtype=np.float32)
    path = _write_model(
        tmp_path / "bad.onnx", weights=weights, symptoms=symptoms, **kwargs
    )

    with pytest.raises(ConditionDataError, match=message):
        OnnxConditionModel(path)


def test_baseline_is_the_default_model() -> None:
    assert isinstance(
        build_condition_model(ConditionModelSettings()), BaselineConditionModel
    )


def test_onnx_model_loads_from_a_local_path(tmp_path: Path) -> None:
    path = _write_model(tmp_path / "m.onnx")

    built = build_condition_model(ConditionModelSettings(kind="onnx", path=path))

    assert isinstance(built, OnnxConditionModel)


def test_onnx_model_downloads_from_the_hub_at_a_pinned_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write_model(tmp_path / "hub.onnx")
    calls: list[tuple[Any, ...]] = []

    def fake_download(repo: str, file: str, revision: str, cache_dir: Any) -> str:
        calls.append((repo, file, revision))
        return str(path)

    monkeypatch.setattr("huggingface_hub.hf_hub_download", fake_download)
    settings = ConditionModelSettings(
        kind="onnx", repo="NT1906/condition-v2", revision="abc1234"
    )

    assert isinstance(build_condition_model(settings), OnnxConditionModel)
    assert calls == [("NT1906/condition-v2", "condition_v2.onnx", "abc1234")]


@pytest.mark.parametrize(
    "settings",
    [
        ConditionModelSettings(kind="onnx", path=Path("missing.onnx")),
        ConditionModelSettings(kind="onnx"),  # neither path nor repo
    ],
    ids=["missing_file", "not_configured"],
)
def test_unloadable_onnx_model_falls_back_to_the_baseline(
    settings: ConditionModelSettings,
) -> None:
    assert isinstance(build_condition_model(settings), BaselineConditionModel)


def test_settings_read_condition_model_environment_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CONDITION_MODEL_KIND", "onnx")
    monkeypatch.setenv("CONDITION_MODEL_PATH", "/models/condition_v2.onnx")

    settings = config.ConditionModelSettings()

    assert (settings.kind, settings.path) == ("onnx", Path("/models/condition_v2.onnx"))


def test_v2_predictions_work_with_the_risk_engine_and_composer(
    model: OnnxConditionModel,
) -> None:
    ids = ["fever", "pain_behind_eyes", "joint_pain"]
    predictions = model.predict(ids)
    decision = assess_risk([ReportedSymptom(id=i) for i in ids], predictions)

    result = ResultComposer(assert_safe_wording).compose(uuid4(), decision, predictions)

    assert result.conditions[0].name == "Dengue"
    assert result.risk_level is decision.level
