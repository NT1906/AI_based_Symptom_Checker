"""Condition model v2 served with ONNX Runtime (S2-NIS-3).

Responsibilities:
    - Load the ONNX model exported by ``ml/prediction/train_condition_model.py``
      and read its metadata: feature order, condition classes, thresholds.
    - Refuse a model that does not fit the packaged dataset (other symptom
      vocabulary, unknown conditions or another dataset version), so a stale
      model can never rank conditions silently wrong.
    - Rank like the baseline's contract (``ConditionModel``): only conditions
      that explain at least one reported symptom, top 3, ties by ID, and a
      confidence label, never a number (FR-23). "Likely" also needs a hallmark
      symptom, as in the baseline.

Deterministic: CPU inference on fixed weights, same input, same output.
The model only ranks; risk stays with the deterministic risk engine.

Owner: Nisarg (prediction) · Task: S2-NIS-3 · Requirements: FR-05, FR-23, NFR-07
Empty input returns no predictions: Nisarg · S2-NIS-28 (#348)
"""

import json
from collections.abc import Collection
from pathlib import Path

import numpy as np

from app.core.logging import get_logger
from app.schemas.enums import ConfidenceLabel
from app.services.prediction.condition_catalog import (
    ConditionCatalog,
    ConditionDataError,
    get_catalog,
)
from app.services.prediction.condition_predictor import TOP_K
from app.services.prediction.schemas import (
    HALLMARK_WEIGHT,
    ConditionPrediction,
    ConditionProfile,
)

logger = get_logger(__name__)

INPUT_NAME = "symptoms"
OUTPUT_NAME = "probabilities"
REQUIRED_METADATA = (
    "model_version",
    "dataset_version",
    "symptom_ids",
    "condition_ids",
    "likely_min_probability",
    "possible_min_probability",
)


class OnnxConditionModel:
    """``ConditionModel`` backed by the exported logistic-regression ONNX file."""

    def __init__(
        self, model_path: Path, catalog: ConditionCatalog | None = None
    ) -> None:
        """Load the model and check it fits the dataset.

        Args:
            model_path: The ``condition_v2.onnx`` file.
            catalog: Condition data. Defaults to the packaged dataset.

        Raises:
            FileNotFoundError: If the file is missing.
            ConditionDataError: If the metadata is missing or does not match
                the dataset.
        """
        # Why: imported here so the baseline path never loads ONNX Runtime.
        import onnxruntime  # type: ignore[import-untyped]

        if not model_path.is_file():
            raise FileNotFoundError(f"condition model file missing: {model_path.name}")
        self._catalog = catalog or get_catalog()
        options = onnxruntime.SessionOptions()
        options.intra_op_num_threads = 1
        self._session = onnxruntime.InferenceSession(
            str(model_path), options, providers=["CPUExecutionProvider"]
        )
        meta = dict(self._session.get_modelmeta().custom_metadata_map)
        missing = [key for key in REQUIRED_METADATA if key not in meta]
        if missing:
            raise ConditionDataError(f"condition model metadata missing: {missing}")
        self.model_version = meta["model_version"]
        self._symptom_ids: list[str] = json.loads(meta["symptom_ids"])
        self._condition_ids: list[str] = json.loads(meta["condition_ids"])
        self._likely = float(meta["likely_min_probability"])
        self._possible = float(meta["possible_min_probability"])
        self._check_fits_catalog(meta["dataset_version"])
        self._column = {symptom: i for i, symptom in enumerate(self._symptom_ids)}

    def predict(self, symptom_ids: Collection[str]) -> list[ConditionPrediction]:
        """Rank the most likely conditions for confirmed symptoms.

        Args:
            symptom_ids: Canonical symptom IDs; unknown IDs are ignored and
                duplicates count once.

        Returns:
            Up to ``TOP_K`` predictions, best first; empty when no reported
            symptom matches any condition, including when ``symptom_ids`` is
            empty (#348).
        """
        reported = frozenset(symptom_ids) & self._catalog.symptom_ids
        ranked: list[tuple[float, str, ConditionProfile, tuple[str, ...], bool]] = []
        if reported:
            for condition_id, probability in zip(
                self._condition_ids, self._probabilities(reported), strict=True
            ):
                profile = self._catalog.get(condition_id)
                if profile is None:  # pragma: no cover - checked at load time
                    continue
                matched = sorted(
                    (s for s in profile.symptoms if s.id in reported),
                    key=lambda s: (-s.weight, s.id),
                )
                if matched:
                    hallmark = any(s.weight == HALLMARK_WEIGHT for s in matched)
                    ids = tuple(s.id for s in matched)
                    ranked.append((-probability, condition_id, profile, ids, hallmark))
        ranked.sort(key=lambda item: (item[0], item[1]))
        predictions = [
            ConditionPrediction(
                condition_id=profile.id,
                name=profile.name,
                icd10_code=profile.icd10,
                specialty=profile.specialty,
                base_risk=profile.base_risk,
                confidence=self.confidence_label(-negative, hallmark),
                rank=rank,
                matched_symptom_ids=ids,
            )
            for rank, (negative, _, profile, ids, hallmark) in enumerate(
                ranked[:TOP_K], 1
            )
        ]
        logger.info(
            "conditions_predicted",
            model="onnx_v2",
            model_version=self.model_version,
            symptom_count=len(reported),
            prediction_count=len(predictions),
        )
        return predictions

    def confidence_label(
        self, probability: float, has_hallmark: bool
    ) -> ConfidenceLabel:
        """Map a model probability to the label shown to users.

        Args:
            probability: The condition's probability from the model.
            has_hallmark: Whether a hallmark symptom of it was reported.

        Returns:
            ``LIKELY`` only above the Likely threshold *and* with a hallmark,
            ``POSSIBLE`` above the Possible threshold, else ``LESS_LIKELY``.
        """
        if probability >= self._likely and has_hallmark:
            return ConfidenceLabel.LIKELY
        if probability >= self._possible:
            return ConfidenceLabel.POSSIBLE
        return ConfidenceLabel.LESS_LIKELY

    def _probabilities(self, reported: frozenset[str]) -> list[float]:
        """Run the model on one multi-hot vector."""
        features = np.zeros((1, len(self._symptom_ids)), dtype=np.float32)
        for symptom in reported:
            features[0, self._column[symptom]] = 1.0
        output = self._session.run([OUTPUT_NAME], {INPUT_NAME: features})[0]
        return [float(p) for p in output[0]]

    def _check_fits_catalog(self, dataset_version: str) -> None:
        """Raise ``ConditionDataError`` unless the model matches the dataset."""
        if dataset_version != self._catalog.dataset_version:
            raise ConditionDataError(
                f"condition model trained on dataset {dataset_version}, "
                f"server has {self._catalog.dataset_version}"
            )
        if set(self._symptom_ids) != self._catalog.symptom_ids:
            raise ConditionDataError("condition model symptom vocabulary differs")
        unknown = [cid for cid in self._condition_ids if self._catalog.get(cid) is None]
        if unknown:
            raise ConditionDataError(
                f"condition model has unknown conditions: {unknown}"
            )
