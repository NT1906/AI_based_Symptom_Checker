"""Specialty mapper: which kind of doctor a result should point the user to.

Responsibilities:
    - URGENT -> the emergency department, whatever the conditions are.
    - CONSULT_DOCTOR -> the specialty of the best-ranked condition that drove
      the decision, or a general physician when no condition did.
    - SELF_CARE -> no referral.

The referral is a pointer outward for the external map search (idea §9). No
doctor data is stored or looked up here.

Owner: Nisarg (prediction) · Task: S1-NIS-3 · Requirements: FR-07, DR-04
"""

from collections.abc import Sequence

from app.core.logging import get_logger
from app.schemas.enums import RiskLevel
from app.services.prediction.condition_catalog import (
    ConditionCatalog,
    ConditionDataError,
    get_catalog,
)
from app.services.prediction.risk_schemas import RiskDecision
from app.services.prediction.schemas import ConditionPrediction, Specialty

logger = get_logger(__name__)

EMERGENCY_SPECIALTY_ID = "emergency_medicine"
GENERAL_SPECIALTY_ID = "general_physician"


class SpecialtyMapper:
    """Chooses the referral specialty for a risk decision."""

    def __init__(self, catalog: ConditionCatalog | None = None) -> None:
        """Create the mapper.

        Args:
            catalog: Specialty data. Defaults to the packaged dataset.

        Raises:
            ConditionDataError: If the emergency or general-physician
                specialty is missing, since every referral may need them.
        """
        self._catalog = catalog or get_catalog()
        self._emergency = self._require(EMERGENCY_SPECIALTY_ID)
        self._general = self._require(GENERAL_SPECIALTY_ID)

    def choose(
        self, decision: RiskDecision, predictions: Sequence[ConditionPrediction]
    ) -> Specialty | None:
        """Pick the specialty to refer to.

        Args:
            decision: The risk engine's decision.
            predictions: The ranked conditions the decision was made from.

        Returns:
            The specialty, or ``None`` for ``SELF_CARE``.

        Example:
            >>> from app.services.prediction import assess_risk, ReportedSymptom
            >>> decision = assess_risk([ReportedSymptom(id="seizure")], [])
            >>> SpecialtyMapper().choose(decision, []).id
            'emergency_medicine'
        """
        if decision.level is RiskLevel.URGENT:
            return self._emergency
        if decision.level is RiskLevel.SELF_CARE:
            return None
        by_id = {p.condition_id: p for p in predictions}
        for condition_id in decision.driving_condition_ids:
            prediction = by_id.get(condition_id)
            if prediction is not None:
                return self._specialty_or_general(prediction.specialty)
        return self._general

    def _specialty_or_general(self, specialty_id: str) -> Specialty:
        """Look up a specialty; fall back to a general physician if unknown."""
        specialty = self._catalog.get_specialty(specialty_id)
        if specialty is None:
            # Why: a future model could name a specialty the dataset lacks; a
            # general physician is always a safe referral (never no referral).
            logger.warning("unknown_specialty", specialty_id=specialty_id)
            return self._general
        return specialty

    def _require(self, specialty_id: str) -> Specialty:
        """Return a specialty that must exist in the dataset."""
        specialty = self._catalog.get_specialty(specialty_id)
        if specialty is None:
            raise ConditionDataError(f"specialty {specialty_id!r} is missing")
        return specialty
