"""Unit tests for the baseline weighted symptom-overlap predictor.

Covers:
    - Realistic symptom sets rank the expected condition first.
    - Confidence labels only (no raw score in the output), with the hallmark
      rule and the label thresholds.
    - Determinism: input order, duplicates and ties never change the result.
    - Edge and failure cases: unknown IDs, no matches, empty input.

Owner: Nisarg (prediction) · Task: S1-NIS-1 · Requirements: FR-05, FR-22, FR-23
"""

import random

import pytest
from app.core.errors import ValidationError
from app.schemas.enums import ConfidenceLabel, RiskLevel
from app.services.prediction.condition_catalog import ConditionCatalog
from app.services.prediction.condition_predictor import (
    LIKELY_MIN_SCORE,
    POSSIBLE_MIN_SCORE,
    TOP_K,
    BaselineConditionModel,
    ConditionModel,
    to_confidence_label,
)
from app.services.prediction.schemas import ConditionProfile, WeightedSymptom

COLD = ["runny_nose", "sneezing", "nasal_congestion"]
DENGUE = ["fever", "headache", "pain_behind_eyes", "joint_pain", "skin_rash"]


@pytest.fixture(scope="module")
def model() -> BaselineConditionModel:
    """Predictor over the packaged dataset."""
    return BaselineConditionModel()


def _profile(
    condition_id: str, symptoms: dict[str, int], base_risk: RiskLevel
) -> ConditionProfile:
    """Build a small condition profile for hand-made catalogs."""
    return ConditionProfile(
        id=condition_id,
        name=condition_id.replace("_", " ").title(),
        icd10="X00",
        specialty="general_physician",
        base_risk=base_risk,
        symptoms=tuple(WeightedSymptom(id=s, weight=w) for s, w in symptoms.items()),
    )


# --- realistic cases -----------------------------------------------------------


@pytest.mark.parametrize(
    ("symptoms", "expected_top"),
    [
        pytest.param(DENGUE, "dengue", id="dengue"),
        pytest.param(["itchy_skin", "ring_shaped_rash"], "fungal_skin_infection"),
        pytest.param(
            ["burning_urination", "frequent_urination"], "urinary_tract_infection"
        ),
        pytest.param(["fever", "headache", "body_aches", "fatigue"], "influenza"),
    ],
)
def test_ranks_expected_condition_first_as_likely(
    model: BaselineConditionModel, symptoms: list[str], expected_top: str
) -> None:
    top = model.predict(symptoms)[0]

    assert top.condition_id == expected_top
    assert top.rank == 1
    assert top.confidence is ConfidenceLabel.LIKELY


def test_cold_symptoms_return_cold_and_allergy_as_likely(
    model: BaselineConditionModel,
) -> None:
    predictions = model.predict(COLD)

    assert {p.condition_id for p in predictions[:2]} == {
        "common_cold",
        "allergic_rhinitis",
    }
    assert [p.confidence for p in predictions[:2]] == [ConfidenceLabel.LIKELY] * 2


def test_returns_at_most_top_k_with_consecutive_ranks(
    model: BaselineConditionModel,
) -> None:
    predictions = model.predict(["fever"])

    assert len(predictions) == TOP_K
    assert [p.rank for p in predictions] == list(range(1, TOP_K + 1))


def test_prediction_carries_dataset_fields_and_matched_symptoms(
    model: BaselineConditionModel,
) -> None:
    dengue = model.predict(DENGUE)[0]

    assert dengue.icd10_code == "A90"
    assert dengue.base_risk is RiskLevel.CONSULT_DOCTOR
    assert set(dengue.matched_symptom_ids) <= set(DENGUE)


def test_output_never_contains_a_raw_score(model: BaselineConditionModel) -> None:
    dumped = model.predict(COLD)[0].model_dump()

    # FR-23 / AI_RULES.md §2: only labels leave the predictor; rank is an order.
    numeric = {k for k, v in dumped.items() if isinstance(v, float)}
    assert numeric == set()
    assert "score" not in dumped


# --- confidence labels ---------------------------------------------------------


@pytest.mark.parametrize(
    ("score", "has_hallmark", "expected"),
    [
        (1.0, True, ConfidenceLabel.LIKELY),
        (LIKELY_MIN_SCORE, True, ConfidenceLabel.LIKELY),
        (LIKELY_MIN_SCORE, False, ConfidenceLabel.POSSIBLE),
        (LIKELY_MIN_SCORE - 0.001, True, ConfidenceLabel.POSSIBLE),
        (POSSIBLE_MIN_SCORE, False, ConfidenceLabel.POSSIBLE),
        (POSSIBLE_MIN_SCORE - 0.001, True, ConfidenceLabel.LESS_LIKELY),
        (0.0, False, ConfidenceLabel.LESS_LIKELY),
    ],
)
def test_maps_score_to_confidence_label(
    score: float, has_hallmark: bool, expected: ConfidenceLabel
) -> None:
    assert to_confidence_label(score, has_hallmark) is expected


def test_strong_overlap_without_hallmark_is_only_possible() -> None:
    catalog = ConditionCatalog(
        conditions=(
            _profile("mild_thing", {"nausea": 2, "fatigue": 1}, RiskLevel.SELF_CARE),
        ),
        symptom_ids=frozenset({"nausea", "fatigue"}),
        dataset_version="test",
    )

    [prediction] = BaselineConditionModel(catalog).predict(["nausea", "fatigue"])

    assert prediction.confidence is ConfidenceLabel.POSSIBLE


def test_unrelated_symptoms_are_never_likely(model: BaselineConditionModel) -> None:
    predictions = model.predict(["sneezing", "burning_urination"])

    assert predictions
    assert all(p.confidence is not ConfidenceLabel.LIKELY for p in predictions)


def test_matched_symptoms_are_heaviest_first() -> None:
    catalog = ConditionCatalog(
        conditions=(_profile("cond", {"a": 1, "b": 3, "c": 2}, RiskLevel.SELF_CARE),),
        symptom_ids=frozenset({"a", "b", "c"}),
        dataset_version="test",
    )

    [prediction] = BaselineConditionModel(catalog).predict(["a", "c", "b"])

    assert prediction.matched_symptom_ids == ("b", "c", "a")


# --- determinism ---------------------------------------------------------------


def test_input_order_and_duplicates_do_not_change_result(
    model: BaselineConditionModel,
) -> None:
    expected = model.predict(DENGUE)
    shuffled = DENGUE * 2
    random.Random(7).shuffle(shuffled)

    assert model.predict(shuffled) == expected
    assert model.predict(tuple(DENGUE)) == expected


def test_ties_are_broken_by_condition_id() -> None:
    same = {"x": 3, "y": 2}
    catalog = ConditionCatalog(
        conditions=(
            _profile("zeta", same, RiskLevel.SELF_CARE),
            _profile("alpha", same, RiskLevel.URGENT),
        ),
        symptom_ids=frozenset(same),
        dataset_version="test",
    )

    predictions = BaselineConditionModel(catalog).predict(["x"])

    assert [p.condition_id for p in predictions] == ["alpha", "zeta"]
    # The higher-risk tie is not dropped; the risk engine sees both.
    assert predictions[0].base_risk is RiskLevel.URGENT


# --- edge and failure cases ----------------------------------------------------


def test_unknown_symptom_ids_are_ignored(model: BaselineConditionModel) -> None:
    assert model.predict([*COLD, "made_up_symptom"]) == model.predict(COLD)


def test_only_unknown_symptoms_return_no_predictions(
    model: BaselineConditionModel,
) -> None:
    assert model.predict(["made_up_symptom"]) == []


def test_empty_input_raises_validation_error(model: BaselineConditionModel) -> None:
    with pytest.raises(ValidationError, match="At least one confirmed symptom"):
        model.predict([])


def test_baseline_satisfies_condition_model_protocol(
    model: BaselineConditionModel,
) -> None:
    typed: ConditionModel = model

    assert typed.predict(COLD)
