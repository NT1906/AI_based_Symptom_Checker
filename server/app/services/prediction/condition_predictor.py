"""Baseline condition predictor: weighted symptom-overlap scoring.

Responsibilities:
    - Score every condition against the confirmed symptoms and return the top 3.
    - Map each score to a confidence label (Likely / Possible / Less likely).
      Raw scores stay inside this module and are never returned (FR-23).
    - Stay deterministic: same symptoms, same ranking, same labels.

How a condition is scored (all inputs are canonical symptom IDs):
    coverage  = weight of the reported symptoms the condition has
                / total weight of the condition's symptoms
    explained = number of reported symptoms the condition has
                / number of reported symptoms
    score     = harmonic mean of coverage and explained (0 to 1)

A condition must explain at least one reported symptom to be ranked, and can
only be "Likely" when a hallmark (weight 3) symptom is among them.

Owner: Nisarg (prediction) · Task: S1-NIS-1 · Requirements: FR-05, FR-22, FR-23
"""

from collections.abc import Collection
from dataclasses import dataclass
from typing import Protocol

from app.core.errors import ValidationError
from app.core.logging import get_logger
from app.schemas.enums import ConfidenceLabel
from app.services.prediction.condition_catalog import ConditionCatalog, get_catalog
from app.services.prediction.schemas import (
    HALLMARK_WEIGHT,
    ConditionPrediction,
    ConditionProfile,
)

logger = get_logger(__name__)

TOP_K = 3
# Thresholds chosen on hand-written cases (see tests); revisit with the S2-NIS-3 eval.
LIKELY_MIN_SCORE = 0.6
POSSIBLE_MIN_SCORE = 0.35


class ConditionModel(Protocol):
    """Anything that ranks possible conditions for confirmed symptoms.

    The baseline below and the ONNX model from S2-NIS-3 both implement this,
    so the orchestrator depends on the protocol, not on a concrete model.
    """

    def predict(self, symptom_ids: Collection[str]) -> list[ConditionPrediction]:
        """Rank possible conditions for canonical symptom IDs."""
        ...


@dataclass(frozen=True)
class _Match:
    """Internal scoring result for one condition. Never leaves this module."""

    condition: ConditionProfile
    score: float
    matched_weight: int
    matched_symptom_ids: tuple[str, ...]
    has_hallmark: bool


class BaselineConditionModel:
    """Weighted symptom-overlap predictor over the condition dataset."""

    def __init__(self, catalog: ConditionCatalog | None = None) -> None:
        """Create the predictor.

        Args:
            catalog: Condition data to score against. Defaults to the packaged
                dataset (loaded once per process).
        """
        self._catalog = catalog or get_catalog()

    def predict(self, symptom_ids: Collection[str]) -> list[ConditionPrediction]:
        """Rank the most likely conditions for confirmed symptoms.

        Unknown symptom IDs are ignored: the knowledge service normalizes
        symptoms before they get here, so an unknown ID cannot point at any
        condition. Duplicates count once.

        Args:
            symptom_ids: Canonical symptom IDs confirmed by the user.

        Returns:
            Up to ``TOP_K`` predictions, best first, each with a confidence
            label. Empty when no reported symptom matches any condition.

        Raises:
            ValidationError: If ``symptom_ids`` is empty.

        Example:
            >>> model = BaselineConditionModel()
            >>> top = model.predict(["fever", "pain_behind_eyes", "joint_pain"])[0]
            >>> top.condition_id
            'dengue'
        """
        if not symptom_ids:
            raise ValidationError("At least one confirmed symptom is required.")
        reported = frozenset(symptom_ids) & self._catalog.symptom_ids
        matches = [
            match
            for condition in self._catalog.conditions
            if (match := _score(condition, reported)) is not None
        ]
        # Why: ties are broken by heavier matched symptoms, then by ID, so the
        # ranking never depends on dataset order or hash order (determinism).
        matches.sort(key=lambda m: (-m.score, -m.matched_weight, m.condition.id))
        predictions = [
            _to_prediction(match, rank) for rank, match in enumerate(matches[:TOP_K], 1)
        ]
        logger.info(
            "conditions_predicted",
            symptom_count=len(reported),
            unknown_symptom_count=len(frozenset(symptom_ids)) - len(reported),
            prediction_count=len(predictions),
            dataset_version=self._catalog.dataset_version,
        )
        return predictions


def to_confidence_label(score: float, has_hallmark: bool) -> ConfidenceLabel:
    """Map an internal overlap score to the label shown to users.

    Args:
        score: Overlap score between 0 and 1.
        has_hallmark: Whether a hallmark symptom of the condition was reported.

    Returns:
        ``LIKELY``, ``POSSIBLE`` or ``LESS_LIKELY``.

    Example:
        >>> to_confidence_label(0.8, has_hallmark=False)
        <ConfidenceLabel.POSSIBLE: 'POSSIBLE'>
    """
    # Why: without any hallmark symptom a strong overlap is still only
    # "Possible"; claiming "Likely" would overstate certainty (idea §6).
    if score >= LIKELY_MIN_SCORE and has_hallmark:
        return ConfidenceLabel.LIKELY
    if score >= POSSIBLE_MIN_SCORE:
        return ConfidenceLabel.POSSIBLE
    return ConfidenceLabel.LESS_LIKELY


def _score(condition: ConditionProfile, reported: frozenset[str]) -> _Match | None:
    """Score one condition, or return ``None`` if it explains no symptom."""
    matched = sorted(
        (s for s in condition.symptoms if s.id in reported),
        key=lambda s: (-s.weight, s.id),
    )
    if not matched:
        return None
    matched_weight = sum(s.weight for s in matched)
    coverage = matched_weight / condition.total_weight
    explained = len(matched) / len(reported)
    return _Match(
        condition=condition,
        score=2 * coverage * explained / (coverage + explained),
        matched_weight=matched_weight,
        matched_symptom_ids=tuple(s.id for s in matched),
        has_hallmark=any(s.weight == HALLMARK_WEIGHT for s in matched),
    )


def _to_prediction(match: _Match, rank: int) -> ConditionPrediction:
    """Turn an internal match into the public prediction (score dropped)."""
    condition = match.condition
    return ConditionPrediction(
        condition_id=condition.id,
        name=condition.name,
        icd10_code=condition.icd10,
        specialty=condition.specialty,
        base_risk=condition.base_risk,
        confidence=to_confidence_label(match.score, match.has_hallmark),
        rank=rank,
        matched_symptom_ids=match.matched_symptom_ids,
    )
