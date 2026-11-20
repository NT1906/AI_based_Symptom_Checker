"""Risk-consistency verification: same input, same output (DR-02, AI_RULES.md §2.4).

Runs the whole deterministic pipeline (predictor → risk engine → result
composer with the real wording guard) and checks that nothing but the input
decides the output.

Covers:
    - Happy path: each reference case (self-care, consult, urgent condition,
      red flag, assumed severity, mental health, uncertainty, no match) gives
      byte-identical output 1000 times, with the symptoms in a new order each
      run.
    - Breadth: 1000 seeded, varied inputs each give the same output in reverse
      order.
    - Across processes: the same 1000 inputs give the same digest in fresh
      interpreters with different ``PYTHONHASHSEED`` values, so set and dict
      ordering cannot leak into the result.
    - Edge case: a repeated symptom does not change the output.
    - Edge case: an empty input (every symptom unknown, #348) gives the same
      safe no-match result every time.

Owner: Nisarg (prediction) · Task: S2-NIS-9 · Requirements: DR-02
Empty input gives the no-match result: Nisarg · S2-NIS-28 (#348)
"""

import hashlib
import json
import os
import random
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from app.schemas.enums import Severity
from app.services.prediction.condition_catalog import get_catalog
from app.services.prediction.condition_predictor import BaselineConditionModel
from app.services.prediction.result_composer import ResultComposer
from app.services.prediction.risk_engine import assess_risk
from app.services.prediction.risk_schemas import ReportedSymptom, UncertaintyReason
from app.services.privacy.safety_guard import assert_safe_wording

RUNS = 1000
CORPUS_SIZE = 1000
CORPUS_SEED = 192
HASH_SEEDS = ("1", "4242")
SERVER_DIR = Path(__file__).resolve().parents[3]
ASSESSMENT_ID = UUID("00000000-0000-0000-0000-000000000192")
# Fields that differ per call by design (a new timestamp each time).
VOLATILE_FIELDS = {"created_at"}


@dataclass(frozen=True)
class Case:
    """One pipeline input: symptoms with severities, plus caller uncertainty."""

    symptoms: tuple[ReportedSymptom, ...]
    uncertainty: tuple[UncertaintyReason, ...] = field(default=())


def _case(
    *pairs: tuple[str, Severity], uncertainty: tuple[UncertaintyReason, ...] = ()
) -> Case:
    """Build a case from (symptom ID, severity) pairs."""
    symptoms = tuple(ReportedSymptom(id=i, severity=s) for i, s in pairs)
    return Case(symptoms, uncertainty)


MODERATE = Severity.MODERATE
REFERENCE_CASES = {
    "self_care": _case(
        ("runny_nose", MODERATE), ("sneezing", MODERATE), ("nasal_congestion", MODERATE)
    ),
    "consult": _case(
        ("fever", MODERATE), ("pain_behind_eyes", MODERATE), ("joint_pain", MODERATE)
    ),
    "red_flag": _case(("chest_pain", Severity.SEVERE), ("sweating", MODERATE)),
    "assumed_severity": _case(("chest_pain", Severity.UNKNOWN)),
    "mental_health": _case(("thoughts_of_self_harm", MODERATE)),
    "uncertain_photo": _case(
        ("runny_nose", MODERATE),
        ("sneezing", MODERATE),
        uncertainty=(UncertaintyReason.IMAGE_UNCLEAR,),
    ),
    "many_symptoms": _case(
        ("fever", Severity.MILD),
        ("headache", Severity.SEVERE),
        ("rash", Severity.UNKNOWN),
        ("joint_pain", MODERATE),
        ("fatigue", MODERATE),
        ("nausea", Severity.MILD),
    ),
    "no_match": _case(("not_a_known_symptom", MODERATE)),
}


def run_pipeline(case: Case) -> dict[str, Any]:
    """Predict, assess and compose one case; return the output as plain JSON data.

    Args:
        case: The input.

    Returns:
        The predictions, the risk decision and the composed result, without
        fields that change per call by design.
    """
    ids = [symptom.id for symptom in case.symptoms]
    predictions = BaselineConditionModel().predict(ids)
    decision = assess_risk(case.symptoms, predictions, uncertainty=case.uncertainty)
    result = ResultComposer(assert_safe_wording).compose(
        ASSESSMENT_ID, decision, predictions
    )
    return {
        "predictions": [p.model_dump(mode="json") for p in predictions],
        "decision": decision.model_dump(mode="json"),
        "result": result.model_dump(mode="json", exclude=VOLATILE_FIELDS),
    }


def build_corpus(size: int = CORPUS_SIZE, seed: int = CORPUS_SEED) -> list[Case]:
    """Seeded, varied inputs: 1–6 dataset symptoms, any severity, any uncertainty.

    Args:
        size: Number of cases.
        seed: Random seed, so every process builds the same corpus.

    Returns:
        The cases, in a fixed order.
    """
    rng = random.Random(seed)
    symptom_ids = sorted(get_catalog().symptom_ids)
    severities = list(Severity)
    reasons = list(UncertaintyReason)
    corpus = []
    for _ in range(size):
        ids = rng.sample(symptom_ids, rng.randint(1, 6))
        pairs = tuple((i, rng.choice(severities)) for i in ids)
        uncertainty = tuple(r for r in reasons if rng.random() < 0.1)
        corpus.append(_case(*pairs, uncertainty=uncertainty))
    return corpus


def corpus_digest() -> str:
    """SHA-256 of the pipeline output for the whole corpus (used across processes)."""
    outputs = [run_pipeline(case) for case in build_corpus()]
    payload = json.dumps(outputs, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _reordered(case: Case, order: list[int]) -> Case:
    """The same case with its symptoms in another order."""
    return Case(tuple(case.symptoms[i] for i in order), case.uncertainty)


@pytest.mark.parametrize("name", sorted(REFERENCE_CASES))
def test_reference_case_gives_identical_output_1000_times(name: str) -> None:
    case = REFERENCE_CASES[name]
    expected = run_pipeline(case)
    rng = random.Random(name)
    order = list(range(len(case.symptoms)))

    for _ in range(RUNS):
        rng.shuffle(order)
        assert run_pipeline(_reordered(case, order)) == expected


def test_reference_cases_cover_every_risk_tier_and_rule() -> None:
    outputs = [run_pipeline(case)["decision"] for case in REFERENCE_CASES.values()]

    assert {o["level"] for o in outputs} == {"SELF_CARE", "CONSULT_DOCTOR", "URGENT"}
    assert {o["rule"] for o in outputs} >= {
        "RED_FLAG",
        "CONDITION",
        "NO_CONDITION_MATCH",
        "UNCERTAINTY",
    }


def test_1000_varied_inputs_are_stable_in_reverse_order() -> None:
    corpus = build_corpus()

    for case in corpus:
        reverse = list(range(len(case.symptoms)))[::-1]
        assert run_pipeline(_reordered(case, reverse)) == run_pipeline(case)


def test_corpus_is_the_same_on_every_build() -> None:
    assert build_corpus() == build_corpus()
    assert len(build_corpus()) == CORPUS_SIZE


@pytest.mark.parametrize("hash_seed", HASH_SEEDS)
def test_same_output_in_a_fresh_process_with_another_hash_seed(hash_seed: str) -> None:
    code = (
        "from tests.unit.prediction.test_risk_consistency import corpus_digest; "
        "print('DIGEST=' + corpus_digest())"
    )
    env = {**os.environ, "PYTHONHASHSEED": hash_seed}

    completed = subprocess.run(  # noqa: S603 (fixed command, no user input)
        [sys.executable, "-c", code],
        cwd=SERVER_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=300,
    )

    digests = [
        line.removeprefix("DIGEST=")
        for line in completed.stdout.splitlines()
        if line.startswith("DIGEST=")
    ]
    assert digests == [corpus_digest()]


def test_repeated_symptom_does_not_change_the_output() -> None:
    case = REFERENCE_CASES["consult"]
    doubled = Case(case.symptoms + case.symptoms[:1], case.uncertainty)

    assert run_pipeline(doubled) == run_pipeline(case)


def test_empty_input_gives_the_same_safe_result_every_time() -> None:
    first = run_pipeline(Case(symptoms=()))
    assert first["predictions"] == []
    assert first["result"]["risk_level"] == "CONSULT_DOCTOR"
    assert first["result"]["referral"]["specialty"] == "General physician"
    for _ in range(RUNS):
        assert run_pipeline(Case(symptoms=())) == first
