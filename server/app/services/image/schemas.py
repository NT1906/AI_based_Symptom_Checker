"""Data shapes for skin-image analysis results.

Responsibilities:
    - Define the image labels the CV model can return (docs/cv-plan.md §2).
    - Define why a photo can come back ``unclear``.
    - Define ``ImageAnalysis``, the one result every ``ImageAnalyzer`` returns.

The label is internal. It is never shown to the user as a result: it only adds
visual symptoms to the assessment (docs/cv-plan.md §1).

Owner: Nisarg (image) · Task: S1-NIS-4 · Requirements: idea §3, NFR-07
"""

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ImageLabel(StrEnum):
    """CV model classes, in model output order (ml/cv/configs/baseline.yaml).

    Only conditions with enough training photos are classes; the others were
    merged into ``unclear`` and stay reachable through text symptoms
    (ml/datasets/images/README.md §8).
    """

    ECZEMA = "eczema"
    URTICARIA = "urticaria"
    UNCLEAR = "unclear"


class UnclearReason(StrEnum):
    """Why an analysis is ``unclear``; each one means "carry on with text only"."""

    POOR_QUALITY = "POOR_QUALITY"
    """Blurry, dark or too small; the user can be asked to retake the photo."""

    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    """The top probability is below the abstain threshold."""

    NOT_RECOGNISED = "NOT_RECOGNISED"
    """The model chose the ``unclear`` class itself."""


class ImageAnalysis(BaseModel):
    """Result of analysing one photo.

    Attributes:
        label: The class the analyzer settled on.
        reason: Why the result is unclear; set only when ``label`` is ``UNCLEAR``.
        condition_id: Condition the label belongs to; ``None`` when unclear.
        symptom_ids: Canonical visual symptoms the photo shows; empty when
            unclear.
        analyzer_version: Analyzer or model revision, for traceability.
    """

    model_config = ConfigDict(frozen=True)

    label: ImageLabel
    reason: UnclearReason | None = None
    condition_id: str | None = None
    symptom_ids: tuple[str, ...] = ()
    analyzer_version: str = Field(min_length=1)

    @property
    def is_clear(self) -> bool:
        """Whether the photo added any visual symptoms."""
        return self.label is not ImageLabel.UNCLEAR

    @model_validator(mode="after")
    def _check_consistent(self) -> Self:
        """An unclear result has a reason and no findings; a clear one the reverse."""
        if not self.is_clear:
            if self.reason is None:
                raise ValueError("an unclear analysis needs a reason")
            if self.condition_id is not None or self.symptom_ids:
                raise ValueError("an unclear analysis cannot add findings")
            return self
        if self.reason is not None:
            raise ValueError("only an unclear analysis has a reason")
        if self.condition_id is None or not self.symptom_ids:
            raise ValueError("a clear analysis needs a condition and symptoms")
        return self
