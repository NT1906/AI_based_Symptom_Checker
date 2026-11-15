"""The S1-NIS-1 baseline ranking, re-implemented for offline comparison.

Responsibilities:
    - Score a condition exactly like ``server/app/services/prediction/
      condition_predictor.py``: harmonic mean of weighted coverage and the
      share of reported symptoms explained; ties by matched weight, then ID.
    - Rank conditions for a case, so v2 can be compared on the same cases.

The ML folder cannot import the server package, so this mirrors it. The
expected values in ``test_baseline_scoring.py`` were checked against the
server predictor; change both together.

Owner: Nisarg (prediction) · Task: S2-NIS-3 · Requirements: FR-05, NFR-07
"""

from collections.abc import Collection

from condition_cases import Condition


def baseline_score(condition: Condition, reported: Collection[str]) -> float | None:
    """The baseline overlap score, or ``None`` if no reported symptom matches.

    Args:
        condition: One condition with weighted symptoms.
        reported: Reported symptom IDs (non-empty).

    Returns:
        A score between 0 and 1, or ``None``.

    Example:
        >>> cold = Condition("cold", (("runny_nose", 3), ("sneezing", 2)))
        >>> round(baseline_score(cold, ["runny_nose", "fever"]), 3)
        0.545
    """
    unique = set(reported)
    matched = [w for s, w in condition.symptoms if s in unique]
    if not matched:
        return None
    coverage = sum(matched) / sum(w for _, w in condition.symptoms)
    explained = len(matched) / len(unique)
    return 2 * coverage * explained / (coverage + explained)


def baseline_ranking(
    conditions: Collection[Condition], reported: Collection[str]
) -> list[str]:
    """Condition IDs ranked like the server baseline (only matching conditions).

    Args:
        conditions: Every condition.
        reported: Reported symptom IDs (non-empty).

    Returns:
        Condition IDs, best first.
    """
    unique = set(reported)
    scored = []
    for condition in conditions:
        score = baseline_score(condition, unique)
        if score is not None:
            weight = sum(w for s, w in condition.symptoms if s in unique)
            scored.append((-score, -weight, condition.id))
    return [condition_id for _, _, condition_id in sorted(scored)]
