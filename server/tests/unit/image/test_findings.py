"""Unit tests for image labels, analysis results and visual-symptom mapping.

Covers:
    - Labels match the CV training config, in model output order.
    - Every label maps to a visual condition and to symptoms of that condition.
    - ``ImageAnalysis`` rejects inconsistent results (unclear with findings,
      clear without a condition).
    - Findings become ``ExtractedSymptom`` items that ``merge_symptoms()``
      accepts; an unclear photo adds nothing.

Owner: Nisarg (image) · Task: S1-NIS-4 · Requirements: idea §3, NFR-07
"""

import json
import re
from pathlib import Path

import pytest
from app.schemas.enums import Severity
from app.services.ai.schemas import SeverityEnum
from app.services.assessment.orchestrator import merge_symptoms
from app.services.image.findings import (
    LABEL_CONDITIONS,
    VISUAL_SYMPTOMS,
    build_analysis,
    to_extracted_symptoms,
)
from app.services.image.schemas import ImageAnalysis, ImageLabel, UnclearReason
from app.services.prediction.condition_catalog import DATA_FILE, get_catalog
from pydantic import ValidationError

CV_CONFIG_PATH = (
    Path(__file__).resolve().parents[4] / "ml" / "cv" / "configs" / "baseline.yaml"
)
CLEAR_LABELS = [label for label in ImageLabel if label is not ImageLabel.UNCLEAR]


@pytest.mark.skipif(not CV_CONFIG_PATH.exists(), reason="ml/ not checked out")
def test_labels_match_cv_config_in_output_order() -> None:
    config = CV_CONFIG_PATH.read_text(encoding="utf-8")
    # Why: the server has no PyYAML; the class list is simple enough to read.
    pairs = re.findall(r"- name: (\w+)\n\s+condition_id: (\w+)", config)

    assert [name for name, _ in pairs] == [str(x) for x in ImageLabel]
    expected = {str(k): v for k, v in LABEL_CONDITIONS.items()} | {"unclear": "null"}
    assert dict(pairs) == expected


@pytest.mark.parametrize("label", CLEAR_LABELS, ids=str)
def test_label_maps_to_visual_condition_and_its_symptoms(label: ImageLabel) -> None:
    condition_id = LABEL_CONDITIONS[label]
    condition = get_catalog().get(condition_id)
    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    visual = {c["id"] for c in raw["conditions"] if c["visual"]}

    assert condition is not None
    assert condition_id in visual
    condition_symptoms = {s.id for s in condition.symptoms}
    assert VISUAL_SYMPTOMS[label]
    assert set(VISUAL_SYMPTOMS[label]) <= condition_symptoms


def test_photo_never_adds_symptoms_it_cannot_show() -> None:
    added = {s for symptoms in VISUAL_SYMPTOMS.values() for s in symptoms}

    assert added.isdisjoint({"itchy_skin", "fever", "warm_tender_skin", "fatigue"})


def test_build_analysis_fills_condition_and_symptoms() -> None:
    analysis = build_analysis(ImageLabel.CELLULITIS, "test")

    assert analysis.is_clear
    assert analysis.condition_id == "cellulitis"
    assert analysis.symptom_ids == ("spreading_redness", "skin_swelling")
    assert analysis.reason is None


def test_unclear_defaults_to_not_recognised_and_adds_nothing() -> None:
    analysis = build_analysis(ImageLabel.UNCLEAR, "test")

    assert not analysis.is_clear
    assert analysis.reason is UnclearReason.NOT_RECOGNISED
    assert analysis.condition_id is None
    assert analysis.symptom_ids == ()


def test_unclear_keeps_given_reason() -> None:
    analysis = build_analysis(ImageLabel.UNCLEAR, "test", UnclearReason.POOR_QUALITY)

    assert analysis.reason is UnclearReason.POOR_QUALITY


def test_rejects_reason_on_clear_label() -> None:
    with pytest.raises(ValidationError, match="only an unclear analysis"):
        build_analysis(ImageLabel.ACNE, "test", UnclearReason.LOW_CONFIDENCE)


def test_rejects_unclear_analysis_with_findings() -> None:
    with pytest.raises(ValidationError, match="cannot add findings"):
        ImageAnalysis(
            label=ImageLabel.UNCLEAR,
            reason=UnclearReason.LOW_CONFIDENCE,
            symptom_ids=("hives",),
            analyzer_version="test",
        )


def test_rejects_unclear_analysis_without_reason() -> None:
    with pytest.raises(ValidationError, match="needs a reason"):
        ImageAnalysis(label=ImageLabel.UNCLEAR, analyzer_version="test")


def test_rejects_clear_analysis_without_symptoms() -> None:
    with pytest.raises(ValidationError, match="needs a condition and symptoms"):
        ImageAnalysis(
            label=ImageLabel.ACNE, condition_id="acne", analyzer_version="test"
        )


def test_findings_become_unknown_severity_symptoms() -> None:
    symptoms = to_extracted_symptoms(build_analysis(ImageLabel.ECZEMA, "test"))

    assert [s.name for s in symptoms] == ["dry_skin", "scaly_skin", "skin_rash"]
    assert {s.severity for s in symptoms} == {SeverityEnum.UNKNOWN}


def test_unclear_photo_adds_no_symptoms() -> None:
    assert to_extracted_symptoms(build_analysis(ImageLabel.UNCLEAR, "test")) == []


def test_findings_merge_into_assessment_symptoms() -> None:
    text_symptoms = merge_symptoms([], [])
    analysis = build_analysis(ImageLabel.URTICARIA, "test")

    merged = merge_symptoms(text_symptoms, to_extracted_symptoms(analysis))

    assert [s.name for s in merged] == ["hives"]
    assert merged[0].severity is Severity.UNKNOWN
