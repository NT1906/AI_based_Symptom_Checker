"""Synthetic symptom cases for condition model v2, generated from the dataset.

Responsibilities:
    - Load ``ml/datasets/conditions/conditions.json`` (conditions with weighted
      symptoms, and the 100 canonical symptom IDs).
    - Generate seeded cases: each symptom of a condition is reported with a
      probability set by its weight (hallmarks most often), plus sometimes one
      unrelated symptom as noise, the way real users mix symptoms.
    - Build fixed train / validation / test sets from separate seeds.

There is no real patient data (dataset card §Intended use). These cases teach
the model the dataset's expert weights; they are not clinical statistics, so
the evaluation measures agreement with the dataset, not real-world accuracy.

Pure Python (no NumPy), so the ML CI can test it.

Owner: Nisarg (prediction) · Task: S2-NIS-3 · Requirements: FR-05, NFR-07
"""

import json
import random
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

DATASET_PATH = (
    Path(__file__).resolve().parents[1] / "datasets" / "conditions" / "conditions.json"
)
# Chance that a user reports a symptom of their condition, by weight (3 = hallmark).
REPORT_PROBABILITY = {3: 0.85, 2: 0.55, 1: 0.25}
NOISE_PROBABILITY = 0.3  # chance of one extra, unrelated symptom
SPLIT_SEEDS = {"train": 1, "val": 2, "test": 3}
CASES_PER_CONDITION = {"train": 200, "val": 50, "test": 50}


@dataclass(frozen=True)
class Condition:
    """One condition as the generator needs it.

    Attributes:
        id: Condition ID, e.g. ``dengue``.
        symptoms: ``(symptom_id, weight)`` pairs, heaviest first.
    """

    id: str
    symptoms: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class Case:
    """One synthetic patient: reported symptoms and the true condition."""

    symptoms: tuple[str, ...]
    condition_id: str


@dataclass(frozen=True)
class Dataset:
    """The parts of ``conditions.json`` used for training.

    Attributes:
        version: Dataset version, e.g. ``v0``.
        conditions: Every condition, in dataset order.
        symptom_ids: All canonical symptom IDs, sorted (the feature order).
    """

    version: str
    conditions: tuple[Condition, ...]
    symptom_ids: tuple[str, ...]


def load_dataset(path: Path = DATASET_PATH) -> Dataset:
    """Read the condition dataset.

    Args:
        path: ``conditions.json``.

    Returns:
        Conditions with weighted symptoms and the sorted symptom vocabulary.

    Raises:
        ValueError: If a condition uses a symptom outside the vocabulary.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    symptom_ids = tuple(sorted(s["id"] for s in data["symptoms"]))
    known = set(symptom_ids)
    conditions = []
    for item in data["conditions"]:
        symptoms = tuple(
            sorted(
                ((s["id"], int(s["weight"])) for s in item["symptoms"]),
                key=lambda pair: (-pair[1], pair[0]),
            )
        )
        unknown = {symptom for symptom, _ in symptoms} - known
        if unknown:
            raise ValueError(f"{item['id']} uses unknown symptoms: {sorted(unknown)}")
        conditions.append(Condition(id=item["id"], symptoms=symptoms))
    return Dataset(
        version=str(data.get("dataset_version", "unknown")),
        conditions=tuple(conditions),
        symptom_ids=symptom_ids,
    )


def sample_case(
    condition: Condition, symptom_ids: Sequence[str], rng: random.Random
) -> Case:
    """Draw one synthetic case for a condition.

    Each symptom is reported with ``REPORT_PROBABILITY[weight]``. If none is
    drawn, one is picked with probability proportional to its weight, so every
    case has at least one symptom of its condition. With
    ``NOISE_PROBABILITY`` one unrelated symptom is added.

    Args:
        condition: The true condition.
        symptom_ids: The whole vocabulary (for noise).
        rng: Seeded random generator.

    Returns:
        The case, with symptoms sorted.
    """
    reported = {
        s for s, w in condition.symptoms if rng.random() < REPORT_PROBABILITY[w]
    }
    if not reported:
        ids = [s for s, _ in condition.symptoms]
        weights = [w for _, w in condition.symptoms]
        reported.add(rng.choices(ids, weights=weights, k=1)[0])
    if rng.random() < NOISE_PROBABILITY:
        own = {s for s, _ in condition.symptoms}
        reported.add(rng.choice([s for s in symptom_ids if s not in own]))
    return Case(symptoms=tuple(sorted(reported)), condition_id=condition.id)


def generate_cases(dataset: Dataset, per_condition: int, seed: int) -> list[Case]:
    """``per_condition`` cases for every condition, from one seed.

    Args:
        dataset: The loaded dataset.
        per_condition: Cases per condition (the sets are balanced).
        seed: Random seed; the same seed always gives the same cases.

    Returns:
        Cases grouped by condition in dataset order.
    """
    rng = random.Random(seed)
    return [
        sample_case(condition, dataset.symptom_ids, rng)
        for condition in dataset.conditions
        for _ in range(per_condition)
    ]


def perturb_cases(
    cases: Sequence[Case],
    dataset: Dataset,
    extra: int,
    drop_hallmarks: bool,
    seed: int,
) -> list[Case]:
    """Harder copies of cases for stress tests.

    Args:
        cases: Cases to copy.
        dataset: The loaded dataset.
        extra: Unrelated symptoms to add to each case.
        drop_hallmarks: Remove the condition's hallmark symptoms; if nothing
            is left, keep its lightest symptom.
        seed: Random seed for the extra symptoms.

    Returns:
        One perturbed case per input case, same order and labels.
    """
    rng = random.Random(seed)
    by_id = {condition.id: condition for condition in dataset.conditions}
    perturbed = []
    for case in cases:
        condition = by_id[case.condition_id]
        own = {s for s, _ in condition.symptoms}
        symptoms = set(case.symptoms)
        if drop_hallmarks:
            symptoms -= {s for s, w in condition.symptoms if w == 3}
            if not symptoms:
                symptoms = {condition.symptoms[-1][0]}
        others = [s for s in dataset.symptom_ids if s not in own and s not in symptoms]
        symptoms |= set(rng.sample(others, extra))
        perturbed.append(
            Case(symptoms=tuple(sorted(symptoms)), condition_id=case.condition_id)
        )
    return perturbed


def build_splits(dataset: Dataset, scale: float = 1.0) -> dict[str, list[Case]]:
    """The fixed train / val / test sets.

    Args:
        dataset: The loaded dataset.
        scale: Multiplies ``CASES_PER_CONDITION`` (smaller for quick tests).

    Returns:
        Split name -> cases.
    """
    return {
        split: generate_cases(
            dataset, max(1, round(CASES_PER_CONDITION[split] * scale)), seed
        )
        for split, seed in SPLIT_SEEDS.items()
    }
