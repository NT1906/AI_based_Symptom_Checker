"""Prediction service: ranks possible conditions for confirmed symptoms.

Responsibilities:
    - Load the condition dataset shipped with the server.
    - Provide the ``ConditionModel`` protocol and the baseline overlap model.
    - Provide the deterministic risk engine with its red-flag override.
    - Map a decision to a referral specialty and compose the final result.

Owner: Nisarg (prediction) · Task: S1-NIS-1, S1-NIS-2, S1-NIS-3 · Requirements:
FR-05, FR-06, FR-07, FR-15, FR-22, FR-23, DR-02, DR-04
"""

from app.services.prediction.condition_catalog import (
    ConditionCatalog,
    ConditionDataError,
    get_catalog,
    load_catalog,
)
from app.services.prediction.condition_predictor import (
    TOP_K,
    BaselineConditionModel,
    ConditionModel,
    to_confidence_label,
)
from app.services.prediction.result_composer import ResultComposer, WordingGuard
from app.services.prediction.risk_engine import (
    RISK_ENGINE_VERSION,
    assess_risk,
    condition_tier,
    find_red_flags,
)
from app.services.prediction.risk_schemas import (
    RedFlag,
    RedFlagHit,
    ReportedSymptom,
    RiskDecision,
    RiskRule,
)
from app.services.prediction.schemas import (
    ConditionPrediction,
    ConditionProfile,
    Specialty,
    WeightedSymptom,
)
from app.services.prediction.specialty_mapper import SpecialtyMapper

__all__ = [
    "RISK_ENGINE_VERSION",
    "TOP_K",
    "BaselineConditionModel",
    "ConditionCatalog",
    "ConditionDataError",
    "ConditionModel",
    "ConditionPrediction",
    "ConditionProfile",
    "RedFlag",
    "RedFlagHit",
    "ReportedSymptom",
    "ResultComposer",
    "RiskDecision",
    "RiskRule",
    "Specialty",
    "SpecialtyMapper",
    "WeightedSymptom",
    "WordingGuard",
    "assess_risk",
    "condition_tier",
    "find_red_flags",
    "get_catalog",
    "load_catalog",
    "to_confidence_label",
]
