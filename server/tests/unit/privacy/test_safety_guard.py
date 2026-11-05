"""Regression tests for response wording validation.

Owner: Harsh · Task: S1-HAR-3 · Issue: #49 · Requirement: DR-05
"""

import pytest

from app.services.privacy.safety_guard import (
    MANDATORY_DISCLAIMER,
    UnsafeWordingError,
    assert_safe_wording,
)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "Possible conditions include seasonal allergies.",
        "Your symptoms may be related to a common infection.",
        "Rest and drink fluids. Seek medical advice if symptoms worsen.",
        "Call 112 immediately for a life-threatening emergency.",
        "Likelihood: Possible.",
        MANDATORY_DISCLAIMER,
        f"Possible conditions include allergies. {MANDATORY_DISCLAIMER}",
        MANDATORY_DISCLAIMER.replace(" ", "\n"),
        "Discuss medication options with a qualified healthcare professional.",
    ],
)
def test_allows_safe_wording(text: str) -> None:
    """Allow safe guidance and the mandatory disclaimer."""
    assert assert_safe_wording(text) is None


@pytest.mark.parametrize(
    "text",
    [
        "You have influenza.",
        "YOU HAVE influenza.",
        "You\nhave influenza.",
        "You are suffering from influenza.",
        "Diagnosis: influenza.",
        "We diagnosed you with influenza.",
        "You were diagnosed with influenza.",
        "This definitely means influenza.",
        "Conclusive cause is influenza.",
        "Tests confirm that influenza is present.",
        "A prescription is required.",
        "We prescribe a drug.",
        "Take 500 mg of ExampleDrug.",
        "Take 0.5mg of ExampleDrug.",
        "Take 500 mcg of ExampleDrug.",
        "Take 5 ml of ExampleDrug.",
        "You need antibiotic treatment.",
        "Start taking ExampleDrug daily.",
        "This will cure your condition.",
        "You will recover in 2 days.",
        "It is probably nothing to worry about.",
        "It's probably nothing to worry about.",
        "It’s probably nothing to worry about.",
        "No need to see a doctor.",
        "Ｙｏｕ ｈａｖｅ influenza.",
        "You\u00a0have influenza.",
    ],
)
def test_rejects_prohibited_wording(text: str) -> None:
    """Reject banned phrases and normalized variations."""
    with pytest.raises(UnsafeWordingError):
        assert_safe_wording(text)


@pytest.mark.parametrize(
    "text",
    [
        f"{MANDATORY_DISCLAIMER} You have influenza.",
        f"You have influenza. {MANDATORY_DISCLAIMER}",
        f"{MANDATORY_DISCLAIMER} Diagnosis: influenza.",
        f"{MANDATORY_DISCLAIMER} Take 500 mg of ExampleDrug.",
    ],
)
def test_disclaimer_does_not_bypass_other_checks(text: str) -> None:
    """Reject unsafe content even when the disclaimer is present."""
    with pytest.raises(UnsafeWordingError):
        assert_safe_wording(text)


@pytest.mark.parametrize("value", [None, 42, b"Possible", [], {}])
def test_rejects_non_text_input(value: object) -> None:
    """Reject values outside the string input contract."""
    with pytest.raises(UnsafeWordingError):
        assert_safe_wording(value)  # type: ignore[arg-type]


def test_error_does_not_expose_rejected_text() -> None:
    """Keep rejected content out of exception messages and details."""
    rejected_text = "You have ExamplePrivateCondition."
    with pytest.raises(UnsafeWordingError) as caught:
        assert_safe_wording(rejected_text)

    error = caught.value
    assert error.code == "UNSAFE_WORDING"
    assert error.status_code == 500
    assert error.details is None
    assert rejected_text not in str(error)
    assert "ExamplePrivateCondition" not in repr(error)
