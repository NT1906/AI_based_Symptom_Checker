"""Synthetic redaction and clinical-text preservation tests.

Owner: Harsh · Task: S1-HAR-2 · Requirements: NFR-04, DR-06
"""

import pytest

from app.services.privacy.pii import MAX_TEXT_LENGTH, scrub_pii


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Email demo.person@example.invalid please", "Email [EMAIL] please"),
        ("demo+tag@example.invalid, fever", "[EMAIL], fever"),
        ("Call +1 (202) 555-0147 now", "Call [PHONE] now"),
        ("202-555-0147", "[PHONE]"),
        ("2025550147", "[PHONE]"),
        ("PAN ABCDE1234F", "PAN [ID]"),
        ("Aadhaar 2345 6789 0123", "Aadhaar [ID]"),
        ("2345-6789-0123", "[ID]"),
        ("student ID: DEMO-123", "student ID: [ID]"),
        ("passport: Z0000000", "passport: [ID]"),
        ("123e4567-e89b-12d3-a456-426614174000", "[ID]"),
        (
            "My name is Sample Person. Fever for 2 days.",
            "My name is [NAME]. Fever for 2 days.",
        ),
        (
            "my name is sample person and I have fever",
            "my name is [NAME] and I have fever",
        ),
        ("Name: Sample O'Example; headache", "Name: [NAME]; headache"),
        ("Name: Élodie Exemple, cough", "Name: [NAME], cough"),
        ("Patient name: Sample Person\nfever", "Patient name: [NAME]\nfever"),
        ("ｄｅｍｏ＠ｅｘａｍｐｌｅ．ｉｎｖａｌｉｄ", "[EMAIL]"),
        ("demo\u200b@example.invalid", "[EMAIL]"),
    ],
)
def test_redacts_supported_patterns(raw: str, expected: str) -> None:
    """Supported fictional identifiers are replaced without surrounding loss."""
    assert scrub_pii(raw) == expected
    assert scrub_pii(expected) == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "I am dizzy and nauseous.",
        "I am 25 years old.",
        "Fever 38.5 C for 2 days.",
        "BP 120/80 and pulse 110.",
        "SpO2 92%, pain 8/10, temperature 102.2 F.",
        "Symptoms started 2026-10-17.",
        "Call 112 in an emergency.",
        "No chest pain. Trouble breathing since yesterday.",
        "[EMAIL] [PHONE] [NAME] [ID]",
    ],
)
def test_preserves_clinical_text(text: str) -> None:
    """Numbers, negation and clinically meaningful words are retained."""
    assert scrub_pii(text) == text


def test_known_names_are_case_insensitive_literal_and_word_bounded() -> None:
    """Trusted names match literally without matching inside another word."""
    assert (
        scrub_pii(
            "Sample Person has fever; sample person too.",
            known_names=("Sample Person",),
        )
        == "[NAME] has fever; [NAME] too."
    )
    assert scrub_pii("Ann has nausea; annual check.", known_names=("Ann",)) == (
        "[NAME] has nausea; annual check."
    )
    assert scrub_pii("A.B has fever", known_names=("A.B",)) == "[NAME] has fever"


def test_multiple_categories_and_history() -> None:
    """A history string is treated with the same rules as a single message."""
    raw = "Name: Sample Person. demo@example.invalid\nCall 202-555-0147. Fever 2 days."
    assert scrub_pii(raw) == "Name: [NAME]. [EMAIL]\nCall [PHONE]. Fever 2 days."


def test_unlabelled_name_limit_is_explicit() -> None:
    """Pattern detection must not be represented as universal anonymization."""
    assert scrub_pii("Sample Person has fever.") == "Sample Person has fever."


@pytest.mark.parametrize("bad", [None, 123, b"private", "x" * (MAX_TEXT_LENGTH + 1)])
def test_rejects_invalid_input_without_echo(bad: object) -> None:
    """Invalid input is rejected rather than silently passed or truncated."""
    with pytest.raises(ValueError, match="privacy input limit"):
        scrub_pii(bad)  # type: ignore[arg-type]  # Exercise runtime boundary.


@pytest.mark.parametrize("names", [("x",), ("123",), ("Sample",) * 33, ("",)])
def test_rejects_bad_known_name_configuration(names: tuple[str, ...]) -> None:
    """Misconfigured names fail before any text is returned."""
    with pytest.raises(ValueError, match="[Kk]nown name"):
        scrub_pii("Fever", known_names=names)


def test_input_limit_and_normalization_expansion() -> None:
    """Compatibility normalization cannot bypass the bounded input contract."""
    assert scrub_pii("x" * MAX_TEXT_LENGTH) == "x" * MAX_TEXT_LENGTH
    with pytest.raises(ValueError, match="Normalized text"):
        scrub_pii("\ufb03" * MAX_TEXT_LENGTH)
