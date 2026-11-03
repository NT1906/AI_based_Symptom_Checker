"""Maps image labels to visual symptoms, and findings to orchestrator input.

Responsibilities:
    - Map each image label to its condition and to the canonical symptoms a
      photo can actually show (``itchy_skin`` or ``fever`` never come from a
      photo).
    - Build a consistent ``ImageAnalysis`` from a label.
    - Turn an analysis into the ``ExtractedSymptom`` list that the
      orchestrator's ``merge_symptoms()`` accepts (S2-DAR-2), so photo
      findings join the assessment like text findings and reach the
      deterministic risk engine.

Owner: Nisarg (image) · Task: S1-NIS-4 · Requirements: idea §3, NFR-07
"""

from types import MappingProxyType

from app.services.ai.schemas import ExtractedSymptom, SeverityEnum
from app.services.image.schemas import ImageAnalysis, ImageLabel, UnclearReason

LABEL_CONDITIONS: MappingProxyType[ImageLabel, str] = MappingProxyType(
    {
        ImageLabel.ECZEMA: "atopic_dermatitis",
        ImageLabel.FUNGAL_INFECTION: "fungal_skin_infection",
        ImageLabel.URTICARIA: "urticaria",
        ImageLabel.SCABIES: "scabies",
        ImageLabel.ACNE: "acne",
        ImageLabel.CHICKENPOX: "chickenpox",
        ImageLabel.CELLULITIS: "cellulitis",
    }
)

VISUAL_SYMPTOMS: MappingProxyType[ImageLabel, tuple[str, ...]] = MappingProxyType(
    {
        ImageLabel.ECZEMA: ("dry_skin", "scaly_skin", "skin_rash"),
        ImageLabel.FUNGAL_INFECTION: ("ring_shaped_rash", "scaly_skin"),
        ImageLabel.URTICARIA: ("hives",),
        ImageLabel.SCABIES: ("small_itchy_bumps", "skin_burrows"),
        ImageLabel.ACNE: ("pimples", "blackheads_or_whiteheads"),
        ImageLabel.CHICKENPOX: ("fluid_filled_blisters",),
        ImageLabel.CELLULITIS: ("spreading_redness", "skin_swelling"),
    }
)


def build_analysis(
    label: ImageLabel,
    analyzer_version: str,
    reason: UnclearReason | None = None,
) -> ImageAnalysis:
    """Build the analysis for one label, filling in its condition and symptoms.

    Args:
        label: The label the analyzer settled on.
        analyzer_version: Analyzer or model revision.
        reason: Why the result is unclear. Defaults to ``NOT_RECOGNISED``
            for ``UNCLEAR`` and must be ``None`` for any other label.

    Returns:
        The analysis.

    Raises:
        pydantic.ValidationError: If ``reason`` is given for a clear label.

    Example:
        >>> build_analysis(ImageLabel.URTICARIA, "mock-1").symptom_ids
        ('hives',)
    """
    if label is ImageLabel.UNCLEAR:
        return ImageAnalysis(
            label=label,
            reason=reason or UnclearReason.NOT_RECOGNISED,
            analyzer_version=analyzer_version,
        )
    return ImageAnalysis(
        label=label,
        reason=reason,
        condition_id=LABEL_CONDITIONS[label],
        symptom_ids=VISUAL_SYMPTOMS[label],
        analyzer_version=analyzer_version,
    )


def to_extracted_symptoms(analysis: ImageAnalysis) -> list[ExtractedSymptom]:
    """Turn photo findings into symptoms the orchestrator can merge.

    Severity is ``UNKNOWN`` because a photo cannot say how bad a symptom
    feels; the user still confirms every symptom before the result.

    Args:
        analysis: The analyzer's result.

    Returns:
        One symptom per visual finding; empty for an unclear analysis, so the
        assessment carries on with text only.

    Example:
        >>> analysis = build_analysis(ImageLabel.URTICARIA, "mock-1")
        >>> [s.name for s in to_extracted_symptoms(analysis)]
        ['hives']
    """
    return [
        ExtractedSymptom(name=symptom_id, severity=SeverityEnum.UNKNOWN)
        for symptom_id in analysis.symptom_ids
    ]
