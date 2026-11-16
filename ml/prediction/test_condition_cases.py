"""Unit tests for synthetic case generation and the baseline mirror.

Covers:
    - The dataset loads (38 conditions, 100 sorted symptoms); an unknown
      symptom is rejected.
    - Cases always contain a symptom of their condition, are deterministic
      per seed, and the splits have the configured sizes.
    - Stress perturbation adds unrelated symptoms and removes hallmarks.
    - The baseline mirror ranks exactly like the server predictor (rankings
      checked against server/app/services/prediction on 15 Nov 2026).

Owner: Nisarg (prediction) · Task: S2-NIS-3 · Requirements: FR-05, NFR-07
"""

import json
import random
from pathlib import Path

import pytest
from baseline_scoring import baseline_ranking, baseline_score
from condition_cases import (
    CASES_PER_CONDITION,
    Case,
    Condition,
    build_splits,
    generate_cases,
    load_dataset,
    perturb_cases,
    sample_case,
)

DATASET = load_dataset()


def test_dataset_loads_conditions_and_sorted_vocabulary() -> None:
    assert len(DATASET.conditions) == 38
    assert len(DATASET.symptom_ids) == 100
    assert list(DATASET.symptom_ids) == sorted(DATASET.symptom_ids)
    assert DATASET.version == "v0"


def test_unknown_symptom_in_a_condition_is_rejected(tmp_path: Path) -> None:
    bad = {
        "symptoms": [{"id": "fever"}],
        "conditions": [{"id": "x", "symptoms": [{"id": "not_real", "weight": 3}]}],
    }
    path = tmp_path / "conditions.json"
    path.write_text(json.dumps(bad), encoding="utf-8")

    with pytest.raises(ValueError, match="unknown symptoms"):
        load_dataset(path)


def test_every_case_has_a_symptom_of_its_condition() -> None:
    by_id = {c.id: {s for s, _ in c.symptoms} for c in DATASET.conditions}

    for case in generate_cases(DATASET, per_condition=20, seed=7):
        assert set(case.symptoms) & by_id[case.condition_id]
        assert list(case.symptoms) == sorted(case.symptoms)


def test_a_condition_whose_draws_all_fail_still_gets_one_symptom() -> None:
    class NeverReport(random.Random):
        def random(self) -> float:
            return 0.99  # above every report and noise probability

    condition = Condition("x", (("fever", 1), ("cough", 1)))

    case = sample_case(condition, DATASET.symptom_ids, NeverReport(1))

    assert len(case.symptoms) == 1 and case.symptoms[0] in {"fever", "cough"}


def test_same_seed_gives_the_same_cases_and_other_seeds_differ() -> None:
    first = generate_cases(DATASET, per_condition=5, seed=1)

    assert generate_cases(DATASET, per_condition=5, seed=1) == first
    assert generate_cases(DATASET, per_condition=5, seed=2) != first


def test_splits_have_the_configured_sizes() -> None:
    splits = build_splits(DATASET, scale=0.1)

    for split, per_condition in CASES_PER_CONDITION.items():
        assert len(splits[split]) == round(per_condition * 0.1) * 38


def test_perturbation_adds_unrelated_symptoms_and_drops_hallmarks() -> None:
    dengue = next(c for c in DATASET.conditions if c.id == "dengue")
    hallmarks = {s for s, w in dengue.symptoms if w == 3}
    case = Case(tuple(sorted(s for s, _ in dengue.symptoms)), "dengue")

    [hard] = perturb_cases([case], DATASET, extra=2, drop_hallmarks=True, seed=5)

    own = {s for s, _ in dengue.symptoms}
    assert not set(hard.symptoms) & hallmarks
    assert len(set(hard.symptoms) - own) == 2
    assert hard.condition_id == "dengue"


def test_baseline_score_matches_the_documented_example() -> None:
    cold = Condition("cold", (("runny_nose", 3), ("sneezing", 2)))

    assert baseline_score(cold, ["runny_nose", "fever"]) == pytest.approx(6 / 11)
    assert baseline_score(cold, ["fever"]) is None


@pytest.mark.parametrize(
    ("symptoms", "expected_top3"),
    [
        (
            ["fever", "pain_behind_eyes", "joint_pain"],
            ["dengue", "chikungunya", "typhoid"],
        ),
        (
            ["runny_nose", "sneezing", "nasal_congestion"],
            ["allergic_rhinitis", "common_cold", "acute_sinusitis"],
        ),
        (
            ["chest_pain", "sweating", "shortness_of_breath"],
            ["heart_attack", "pneumonia", "asthma"],
        ),
        (
            ["itchy_skin", "skin_rash"],
            ["atopic_dermatitis", "scabies", "fungal_skin_infection"],
        ),
        (
            ["headache", "nausea", "light_sensitivity", "fever"],
            ["migraine", "meningitis", "malaria"],
        ),
    ],
)
def test_baseline_mirror_ranks_like_the_server(
    symptoms: list[str], expected_top3: list[str]
) -> None:
    assert baseline_ranking(DATASET.conditions, symptoms)[:3] == expected_top3


def test_baseline_ranking_skips_conditions_that_explain_nothing() -> None:
    assert baseline_ranking(DATASET.conditions, ["not_a_symptom"]) == []
