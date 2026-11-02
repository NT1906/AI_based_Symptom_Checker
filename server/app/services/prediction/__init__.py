"""Prediction service: ranks possible conditions for confirmed symptoms.

Responsibilities:
    - Load the condition dataset shipped with the server.
    - Provide the ``ConditionModel`` protocol and the baseline overlap model.

The risk engine (S1-NIS-2) and result composer (S1-NIS-3) join this package later.

Owner: Nisarg (prediction) · Task: S1-NIS-1 · Requirements: FR-05, FR-22, FR-23
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
from app.services.prediction.schemas import (
    ConditionPrediction,
    ConditionProfile,
    WeightedSymptom,
)

__all__ = [
    "TOP_K",
    "BaselineConditionModel",
    "ConditionCatalog",
    "ConditionDataError",
    "ConditionModel",
    "ConditionPrediction",
    "ConditionProfile",
    "WeightedSymptom",
    "get_catalog",
    "load_catalog",
    "to_confidence_label",
]
