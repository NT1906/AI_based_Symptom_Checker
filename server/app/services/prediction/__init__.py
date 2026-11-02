"""Prediction service: ranks possible conditions for confirmed symptoms.

Responsibilities:
    - Load the condition dataset shipped with the server.
    - Provide the ``ConditionModel`` protocol and the baseline overlap model.
    - Provide the deterministic risk engine with its red-flag override.

The result composer (S1-NIS-3) joins this package later.

Owner: Nisarg (prediction) · Task: S1-NIS-1, S1-NIS-2 · Requirements: FR-05,
FR-06, FR-15, FR-22, FR-23, DR-02
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
    WeightedSymptom,
)

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
    "RiskDecision",
    "RiskRule",
    "WeightedSymptom",
    "assess_risk",
    "condition_tier",
    "find_red_flags",
    "get_catalog",
    "load_catalog",
    "to_confidence_label",
]
