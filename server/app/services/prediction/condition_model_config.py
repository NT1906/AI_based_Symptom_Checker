"""Choose the condition model: the baseline, or v2 on ONNX (env ``CONDITION_MODEL_*``).

Responsibilities:
    - Read the settings: which model, and where the v2 ONNX file comes from
      (a local path, or a Hugging Face repo at a pinned revision).
    - Build the ``ConditionModel`` the app should use. The baseline is the
      default, and also the fallback whenever v2 cannot be loaded (logged,
      never raised), so predictions always work.

v2 matched but did not beat the baseline on the S2-NIS-3 evaluation
(``docs/condition-model-v2.md``), so it stays off unless
``CONDITION_MODEL_KIND=onnx`` is set.

Owner: Nisarg (prediction) · Task: S2-NIS-3 · Requirements: FR-05, NFR-07
"""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.logging import get_logger
from app.services.prediction.condition_catalog import ConditionCatalog
from app.services.prediction.condition_predictor import (
    BaselineConditionModel,
    ConditionModel,
)
from app.services.prediction.onnx_condition_model import OnnxConditionModel

logger = get_logger(__name__)


class ConditionModelSettings(BaseSettings):
    """Condition model settings from ``CONDITION_MODEL_*`` environment variables.

    Attributes:
        kind: ``baseline`` (default) or ``onnx`` (v2).
        path: Local ``condition_v2.onnx``; used before ``repo``.
        repo: Hugging Face repo holding the model, e.g. ``NT1906/condition-v2``.
        revision: Pinned commit SHA in ``repo``.
        file: File name inside ``repo``.
        cache_dir: Download cache; the Hugging Face default if unset.
    """

    model_config = SettingsConfigDict(env_prefix="CONDITION_MODEL_", extra="ignore")

    kind: Literal["baseline", "onnx"] = "baseline"
    path: Path | None = None
    repo: str | None = None
    revision: str | None = None
    file: str = "condition_v2.onnx"
    cache_dir: Path | None = None


def build_condition_model(
    settings: ConditionModelSettings, catalog: ConditionCatalog | None = None
) -> ConditionModel:
    """The condition model for the running app.

    Args:
        settings: Condition model settings.
        catalog: Condition data. Defaults to the packaged dataset.

    Returns:
        ``OnnxConditionModel`` when configured and loadable, otherwise
        ``BaselineConditionModel``.
    """
    if settings.kind == "baseline":
        return BaselineConditionModel(catalog)
    try:
        model = OnnxConditionModel(_model_path(settings), catalog)
    except Exception as exc:  # noqa: BLE001
        # Why: a missing or mismatched model must never stop predictions.
        logger.warning("condition_model_unavailable", error=type(exc).__name__)
        return BaselineConditionModel(catalog)
    logger.info("condition_model_loaded", model_version=model.model_version)
    return model


def _model_path(settings: ConditionModelSettings) -> Path:
    """Local path of the v2 model, downloading it from the Hub if needed."""
    if settings.path is not None:
        return settings.path
    if not settings.repo or not settings.revision:
        raise ValueError("set CONDITION_MODEL_PATH, or both _REPO and _REVISION")
    from huggingface_hub import hf_hub_download

    return Path(
        hf_hub_download(
            settings.repo,
            settings.file,
            revision=settings.revision,
            cache_dir=settings.cache_dir,
        )
    )
