"""Unit tests for missing-information detection engine.

Owner: Nishith · Task: S1-NIT-2 · Requirements: FR-04, FR-19, FR-20
"""

from app.services.ai.missing_info import (
    detect_missing_information,
    should_request_clarification,
)
from app.services.ai.schemas import (
    Duration,
    DurationUnitEnum,
    ExtractedSymptom,
    MissingFieldEnum,
    SeverityEnum,
)


def test_empty_symptom_list_returns_no_gaps() -> None:
    """Empty symptom collection returns no missing information gaps."""
    gaps = detect_missing_information([])
    assert gaps == []

    should_ask, reason = should_request_clarification([])
    assert should_ask is False
    assert reason is None


def test_detects_missing_duration_and_severity() -> None:
    """Detects missing duration and severity on primary symptom."""
    symptoms = [ExtractedSymptom(name="headache", severity=SeverityEnum.UNKNOWN)]
    gaps = detect_missing_information(symptoms)

    missing_fields = {g.missing_field for g in gaps}
    assert MissingFieldEnum.DURATION in missing_fields
    assert MissingFieldEnum.SEVERITY in missing_fields


def test_detects_missing_body_site_for_site_sensitive_symptoms() -> None:
    """Detects missing anatomical body site for localized complaints like rashes."""
    symptoms = [
        ExtractedSymptom(
            name="skin_rash",
            severity=SeverityEnum.MILD,
            duration=Duration(value=2.0, unit=DurationUnitEnum.DAY),
            body_site=None,
            body_location=None,
        )
    ]
    gaps = detect_missing_information(symptoms)

    assert any(
        g.missing_field == MissingFieldEnum.BODY_SITE
        and g.symptom_name == "skin_rash"
        and g.priority == 3
        for g in gaps
    )


def test_prioritizes_safety_critical_red_flags() -> None:
    """Assigns priority 1 to red-flag symptoms lacking onset or severity."""
    symptoms = [
        ExtractedSymptom(name="cough"),
        ExtractedSymptom(name="chest_pain"),
    ]
    gaps = detect_missing_information(symptoms)

    # Chest pain should have priority 1 items (onset, severity, duration)
    p1_items = [g for g in gaps if g.priority == 1]
    assert len(p1_items) > 0
    assert all(item.symptom_name == "chest_pain" for item in p1_items)


def test_complete_symptom_requires_no_clarification() -> None:
    """Symptom with known severity, duration, and site requires no clarification."""
    symptoms = [
        ExtractedSymptom(
            name="skin_rash",
            severity=SeverityEnum.MILD,
            duration=Duration(value=3.0, unit=DurationUnitEnum.DAY),
            onset="3 days ago",
            body_site="left arm",
        )
    ]
    gaps = detect_missing_information(symptoms)
    assert gaps == []

    should_ask, reason = should_request_clarification(symptoms)
    assert should_ask is False
    assert reason is None


def test_handles_dictionary_inputs() -> None:
    """Handles raw dictionary symptom structures seamlessly."""
    raw_symptoms = [
        {
            "name": "abdominal_pain",
            "severity": "UNKNOWN",
            "duration": None,
            "body_site": None,
        }
    ]
    gaps = detect_missing_information(raw_symptoms)
    missing_fields = [g.missing_field for g in gaps]
    assert MissingFieldEnum.SEVERITY in missing_fields
    assert MissingFieldEnum.DURATION in missing_fields
    assert MissingFieldEnum.BODY_SITE in missing_fields


def test_red_flag_severity_triggers_priority_1_clarification() -> None:
    """Symptoms with severe red-flag triggers require severity at Priority 1."""
    symptoms = [
        ExtractedSymptom(
            name="abdominal_pain",
            severity=SeverityEnum.UNKNOWN,
            duration=Duration(value=1.0, unit=DurationUnitEnum.DAY),
            body_site="abdomen",
        )
    ]
    gaps = detect_missing_information(symptoms)
    # Severity must be Priority 1 so risk engine won't assume worst-case URGENT
    sev_gap = next(g for g in gaps if g.missing_field == MissingFieldEnum.SEVERITY)
    assert sev_gap.priority == 1
    assert "emergency severity" in sev_gap.reason

    should_ask, reason = should_request_clarification(symptoms)
    assert should_ask is True
    assert reason is not None
    assert "emergency severity" in reason
