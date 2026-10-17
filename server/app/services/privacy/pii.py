"""Bounded local redaction of common personal identifiers in symptom text.

Responsibilities:
    - Redact supported identifiers without network, logging or persistence.
    - Preserve clinical numbers and reject oversized input rather than truncate it.

Owner: Harsh · Task: S1-HAR-2 · Requirements: NFR-04, DR-06
"""

import re
import unicodedata

MAX_TEXT_LENGTH = 20_000
MAX_KNOWN_NAMES = 32
MAX_NAME_LENGTH = 100

# Explicit contexts avoid treating "I am dizzy" as a person's name. This is
# deliberately not a universal name recognizer; see README for residual risk.
_NAME_WORD = (
    r"(?!(?:and|but|with|have|has|had|is|am|feel|feels|since|aged)\b)"
    r"[^\W\d_]+(?:['’\-][^\W\d_]+)*"
)
_NAME = re.compile(
    rf"\b(?P<label>my\s+name\s+is\s+|(?:patient\s+)?name\s*:\s*)"
    rf"(?P<value>{_NAME_WORD}(?:[ \t]+{_NAME_WORD}){{0,3}})",
    re.IGNORECASE,
)
_EMAIL = re.compile(r"(?<![\w.+-])[\w.!#$%&'*+/=?^`{|}~-]+@[\w-]+(?:\.[\w-]+)+")
_PAN = re.compile(r"(?<!\w)[A-Z]{5}[0-9]{4}[A-Z](?!\w)", re.IGNORECASE)
_UUID = re.compile(r"(?<!\w)[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}(?!\w)", re.I)
_AADHAAR = re.compile(r"(?<!\w)[2-9][0-9]{3}[ -]?[0-9]{4}[ -]?[0-9]{4}(?!\w)")
_LABELED_ID = re.compile(
    r"\b(?P<label>(?:aadhaar|aadhar|pan|passport|patient\s+id|student\s+id|"
    r"employee\s+id|id\s+number)\s*(?:(?:number|no\.?)\s*)?[:#=]?\s*)"
    r"(?P<value>[A-Z0-9][A-Z0-9-]{2,31})(?!\w)",
    re.I,
)
# Require 10–15 digits; do not consume decimal points or slashes used by clinical
# readings such as 38.5 C or 120/80. International prefixes/parentheses supported.
_PHONE = re.compile(r"(?<![\w.])\+?\(?\d(?:[ ()-]*\d){9,14}(?!\w|\.\d|[ ()-]*\d)")


def _normalize(text: str) -> str:
    """Normalize compatibility characters and remove zero-width format controls."""
    return "".join(
        char
        for char in unicodedata.normalize("NFKC", text)
        if unicodedata.category(char) != "Cf"
    )


def _validate_names(known_names: tuple[str, ...]) -> tuple[str, ...]:
    """Validate trusted caller-supplied names without echoing their values."""
    if not isinstance(known_names, tuple) or len(known_names) > MAX_KNOWN_NAMES:
        raise ValueError("Known names must be a bounded tuple.")
    normalized = []
    for name in known_names:
        if not isinstance(name, str) or not 2 <= len(name) <= MAX_NAME_LENGTH:
            raise ValueError("Known name has an invalid type or length.")
        value = _normalize(name).strip()
        if len(value) < 2 or not any(char.isalpha() for char in value):
            raise ValueError("Known name must contain letters.")
        normalized.append(value)
    return tuple(sorted(set(normalized), key=len, reverse=True))


def scrub_pii(text: str, *, known_names: tuple[str, ...] = ()) -> str:
    """Replace supported identifiers with stable category placeholders.

    Args:
        text: A message or history string, at most MAX_TEXT_LENGTH characters.
        known_names: Optional exact names from trusted context, not a name list
            inferred by sending raw text to an external service.

    Returns:
        Normalized text with supported names, emails, phones and IDs redacted.
        Empty text stays empty. This function neither logs nor stores input.

    Raises:
        ValueError: Input type, length or known-name configuration is invalid.
            Errors never include the submitted text or names.

    Example:
        >>> scrub_pii("My name is Sample Person. Fever for 2 days.")
        'My name is [NAME]. Fever for 2 days.'

    Arbitrary unlabelled names, addresses and obfuscated identifiers may remain.
    The caller must not interpret this output as guaranteed anonymous text.
    """
    if not isinstance(text, str) or len(text) > MAX_TEXT_LENGTH:
        raise ValueError("Text must be a string within the privacy input limit.")
    names = _validate_names(known_names)
    result = _normalize(text)
    if len(result) > MAX_TEXT_LENGTH:
        raise ValueError("Normalized text exceeds the privacy input limit.")
    # Stable categories first, so phone matching cannot split an Aadhaar ID.
    for pattern, placeholder in (
        (_EMAIL, "[EMAIL]"),
        (_PAN, "[ID]"),
        (_UUID, "[ID]"),
        (_AADHAAR, "[ID]"),
    ):
        result = pattern.sub(placeholder, result)
    result = _LABELED_ID.sub(lambda m: m["label"] + "[ID]", result)
    result = _PHONE.sub("[PHONE]", result)
    result = _NAME.sub(lambda m: m["label"] + "[NAME]", result)
    for name in names:
        pattern = re.compile(r"(?<!\w)" + re.escape(name) + r"(?!\w)", re.I)
        result = pattern.sub("[NAME]", result)
    return result
