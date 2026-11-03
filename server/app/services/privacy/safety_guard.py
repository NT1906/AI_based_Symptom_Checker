"""Validate generated response wording before it reaches the user.

Owner: Harsh · Task: S1-HAR-3 · Issue: #49 · Requirement: DR-05
"""

import re
import unicodedata

from app.core.errors import AppError

MANDATORY_DISCLAIMER = (
    "This is not a medical diagnosis. "
    "Always consult a qualified healthcare professional."
)

_BANNED_PATTERNS = (
    r"\byou\s+have\b",
    r"\byou\s+are\s+suffering\s+from\b",
    r"\bdiagnosis\b",
    r"\bdiagnosed\s+(?:you\s+)?with\b",
    r"\bthis\s+definitely\s+means\b",
    r"\bconclusive\s+cause\s+is\b",
    r"\btests\s+confirm\s+that\b",
    r"\bprescription\b",
    r"\b(?:we\s+)?prescribe\b",
    r"\btake\s+\d+(?:[.,]\d+)?\s*(?:mg|mcg|g|ml)\b",
    r"\byou\s+need\s+antibiotic\s+treatment\b",
    r"\bstart\s+taking\b",
    r"\bcure\b",
    r"\byou\s+will\s+recover\b",
    r"\b(?:it\s+is|it's)\s+probably\s+nothing\s+to\s+worry\s+about\b",
    r"\bno\s+need\s+to\s+see\s+a\s+doctor\b",
)

_BANNED_WORDING = re.compile("|".join(_BANNED_PATTERNS), re.IGNORECASE)


class UnsafeWordingError(AppError):
    """Signal rejected generated wording without exposing the response text."""

    def __init__(self) -> None:
        """Create a generic server error with no response text in its details."""
        super().__init__(
            message="The generated response failed the safety wording check.",
            code="UNSAFE_WORDING",
            status_code=500,
        )


def assert_safe_wording(text: str) -> None:
    """Reject response text containing prohibited medical wording.

    Args:
        text: Generated user-facing text to validate.

    Returns:
        None when no prohibited pattern is found.

    Raises:
        UnsafeWordingError: If input is not text or contains banned wording.

    This deterministic check performs no logging, I/O or text rewriting.
    It detects configured patterns; it does not prove medical safety.
    """
    if not isinstance(text, str):
        raise UnsafeWordingError()

    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\u2019", "'")
    normalized = " ".join(normalized.split())

    # DR-01 requires this exact disclaimer despite its use of "diagnosis".
    # Remove only the approved sentence, then inspect all remaining content.
    candidate = normalized.replace(MANDATORY_DISCLAIMER, " ")

    if _BANNED_WORDING.search(candidate):
        raise UnsafeWordingError()
