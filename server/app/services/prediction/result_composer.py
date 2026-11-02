"""Result composer: builds the final ``AssessmentResult`` the user sees.

Responsibilities:
    - Combine the risk decision, ranked conditions and referral specialty into
      the published ``AssessmentResult`` contract (``app.schemas.result``).
    - Add next steps, the referral reason and limitations from ``result_text``,
      plus any self-care guidance supplied by the caller (S2-KAV-1).
    - Run every generated sentence through the safety-wording guard before it
      can reach the user (DR-05). The fixed disclaimer is not generated text,
      so it is not passed to the guard.

The risk level is copied from the decision unchanged: composing never changes
risk (AI_RULES.md §2.4).

Owner: Nisarg (prediction) · Task: S1-NIS-3 · Requirements: FR-07, DR-01, DR-04
"""

from collections.abc import Callable, Sequence
from uuid import UUID

from app.core.logging import get_logger
from app.schemas.condition import Condition
from app.schemas.enums import RiskLevel
from app.schemas.result import AssessmentResult, ReferralInfo
from app.services.prediction import result_text as text
from app.services.prediction.condition_catalog import ConditionCatalog, get_catalog
from app.services.prediction.risk_schemas import RiskDecision, RiskRule
from app.services.prediction.schemas import ConditionPrediction, Specialty
from app.services.prediction.specialty_mapper import SpecialtyMapper

logger = get_logger(__name__)

WordingGuard = Callable[[str], None]
"""Raises if a sentence breaks the safe-wording rules (S1-HAR-3)."""


class ResultComposer:
    """Turns a risk decision and predictions into an ``AssessmentResult``."""

    def __init__(
        self, wording_guard: WordingGuard, catalog: ConditionCatalog | None = None
    ) -> None:
        """Create the composer.

        Args:
            wording_guard: Safety-wording check, normally Harsh's
                ``assert_safe_wording`` (S1-HAR-3). Required on purpose, so a
                result can never be composed without it.
            catalog: Condition data. Defaults to the packaged dataset.
        """
        self._guard = wording_guard
        self._catalog = catalog or get_catalog()
        self._mapper = SpecialtyMapper(self._catalog)

    def compose(
        self,
        assessment_id: UUID,
        decision: RiskDecision,
        predictions: Sequence[ConditionPrediction],
        self_care_guidance: Sequence[str] = (),
    ) -> AssessmentResult:
        """Build the result for one completed assessment.

        Args:
            assessment_id: The assessment being completed.
            decision: The risk engine's decision for it.
            predictions: The ranked conditions the decision was made from.
            self_care_guidance: Extra general advice for ``SELF_CARE``
                results (S2-KAV-1); ignored for higher tiers.

        Returns:
            The result, with the decision's risk level unchanged.

        Raises:
            Exception: Whatever ``wording_guard`` raises for an unsafe sentence;
                the result is never returned half-checked.
        """
        specialty = self._mapper.choose(decision, predictions)
        guidance = self._guidance(decision, specialty, self_care_guidance)
        referral = self._referral(decision, predictions, specialty)
        limitations = self._limitations(decision)
        for sentence in (*guidance, *limitations, referral.reason or ""):
            if sentence:
                self._guard(sentence)
        result = AssessmentResult(
            assessment_id=assessment_id,
            risk_level=decision.level,
            conditions=[self._to_condition(p) for p in predictions],
            guidance=guidance,
            referral=referral,
            limitations=limitations,
            model_version=decision.engine_version,
        )
        logger.info(
            "result_composed",
            assessment_id=str(assessment_id),
            risk_level=decision.level.value,
            condition_count=len(result.conditions),
        )
        return result

    def _guidance(
        self,
        decision: RiskDecision,
        specialty: Specialty | None,
        self_care_guidance: Sequence[str],
    ) -> list[str]:
        """Next steps for the tier, plus red-flag and self-care additions."""
        name = text.with_article(specialty.name) if specialty else ""
        steps = [
            step.format(specialty=name) for step in text.NEXT_STEPS[decision.level]
        ]
        categories = {hit.category for hit in decision.red_flags}
        if text.MENTAL_HEALTH_CATEGORY in categories:
            steps.append(text.MENTAL_HEALTH_STEP)
        if decision.red_flags and all(h.assumed_severity for h in decision.red_flags):
            steps.append(text.ASSUMED_SEVERITY_STEP)
        if decision.level is RiskLevel.SELF_CARE:
            steps.extend(self_care_guidance)
        return steps

    def _referral(
        self,
        decision: RiskDecision,
        predictions: Sequence[ConditionPrediction],
        specialty: Specialty | None,
    ) -> ReferralInfo:
        """Referral block; ``AssessmentResult`` adds 112 itself for URGENT."""
        return ReferralInfo(
            required=decision.level is not RiskLevel.SELF_CARE,
            specialty=specialty.name if specialty else None,
            reason=self._reason(decision, predictions),
            emergency_number=(
                text.EMERGENCY_NUMBER if decision.level is RiskLevel.URGENT else None
            ),
        )

    def _reason(
        self, decision: RiskDecision, predictions: Sequence[ConditionPrediction]
    ) -> str | None:
        """Plain-language reason for the referral, or ``None`` for self-care."""
        if decision.rule is RiskRule.RED_FLAG:
            red_flag = self._catalog.get_red_flag(decision.red_flags[0].id)
            label = red_flag.label if red_flag else "a warning sign"
            return text.RED_FLAG_REASON.format(label=label)
        if decision.rule is RiskRule.NO_CONDITION_MATCH:
            return text.NO_MATCH_REASON
        if decision.level is RiskLevel.SELF_CARE:
            return None
        names = {p.condition_id: p.name for p in predictions}
        condition = names.get(decision.driving_condition_ids[0], "a condition")
        template = (
            text.URGENT_CONDITION_REASON
            if decision.level is RiskLevel.URGENT
            else text.CONDITION_REASON
        )
        return template.format(condition=condition)

    @staticmethod
    def _limitations(decision: RiskDecision) -> list[str]:
        """Limits that always apply, plus the ones specific to this rule."""
        limitations = list(text.LIMITATIONS_ALWAYS)
        if decision.rule is RiskRule.RED_FLAG:
            limitations.append(text.RED_FLAG_LIMITATION)
        elif decision.rule is RiskRule.NO_CONDITION_MATCH:
            limitations.append(text.NO_MATCH_LIMITATION)
        return limitations

    def _to_condition(self, prediction: ConditionPrediction) -> Condition:
        """Map an internal prediction to the published ``Condition`` schema."""
        specialty = self._catalog.get_specialty(prediction.specialty)
        return Condition(
            name=prediction.name,
            confidence=prediction.confidence,
            rank=prediction.rank,
            icd10_code=prediction.icd10_code,
            specialty=specialty.name if specialty else None,
        )
