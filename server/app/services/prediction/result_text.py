"""User-facing wording for assessment results: next steps, referral reasons, limits.

Responsibilities:
    - Keep every sentence the result composer can show in one reviewable place
      (Dimple reviews wording, DR-05).
    - Follow the safe-wording rules: "may be related to", never "you have";
      general advice only, never a drug, dose or treatment (AI_RULES.md §2).

The composer still runs every sentence through the safety-wording guard.

Owner: Nisarg (prediction) · Task: S1-NIS-3, S2-NIS-1, S2-NIS-2 · Requirements: FR-07,
FR-24, DR-01, DR-05
"""

from app.schemas.enums import RiskLevel
from app.services.prediction.risk_schemas import UncertaintyReason

EMERGENCY_NUMBER = "112"
MENTAL_HEALTH_HELPLINE = "14416"  # Tele-MANAS, India's national mental-health line
MENTAL_HEALTH_CATEGORY = "mental_health"

NEXT_STEPS: dict[RiskLevel, tuple[str, ...]] = {
    RiskLevel.URGENT: (
        f"Call {EMERGENCY_NUMBER} now, or go to the nearest emergency department.",
        "Do not wait to see if the symptoms pass, and do not drive yourself.",
    ),
    RiskLevel.CONSULT_DOCTOR: (
        "Book a visit with {specialty} soon to get your symptoms checked.",
        f"If your symptoms get much worse, call {EMERGENCY_NUMBER} "
        "or go to the nearest emergency department.",
    ),
    RiskLevel.SELF_CARE: (
        "Your symptoms may be manageable at home with rest and plenty of fluids.",
        "See a doctor if your symptoms get worse or do not improve in a few days.",
        f"If you notice a warning sign such as trouble breathing or chest pain, "
        f"call {EMERGENCY_NUMBER}.",
    ),
}

MENTAL_HEALTH_STEP = (
    f"You can also call the Tele-MANAS helpline on {MENTAL_HEALTH_HELPLINE} "
    "at any time to talk to someone now."
)
ASSUMED_SEVERITY_STEP = (
    "You did not say how severe a symptom is, so to be safe this is treated as urgent."
)

RED_FLAG_REASON = "Warning sign reported: {label}."
CONDITION_REASON = "Your symptoms may be related to {condition}."
URGENT_CONDITION_REASON = (
    "Your symptoms may be related to {condition}, which needs urgent care."
)
NO_MATCH_REASON = (
    "Your symptoms did not clearly match a common condition, "
    "so a general check-up is the safest next step."
)
WHY_TEMPLATE = "Because you reported {symptoms}."
UNCERTAINTY_REASON = (
    "The match with your symptoms was not certain enough to suggest home care, "
    "so a doctor's check is the safer next step."
)

LIMITATIONS_ALWAYS = (
    "This result is based only on the symptoms you reported; "
    "no physical examination was done.",
    "Only a limited set of common conditions is covered.",
)
NO_MATCH_LIMITATION = "None of the covered conditions matched your symptoms well."
RED_FLAG_LIMITATION = (
    "A warning-sign rule raised this result to urgent, whatever the possible "
    "conditions are."
)
UNCERTAINTY_LIMITATION = (
    "Because the match was uncertain, this result was raised to the safer level."
)
UNCERTAINTY_LIMITATIONS: dict[UncertaintyReason, str] = {
    UncertaintyReason.IMAGE_UNCLEAR: (
        "The photo could not be assessed, so only the symptoms you described were used."
    ),
    UncertaintyReason.AI_ERROR: (
        "Part of the conversation could not be processed, so some symptoms "
        "may be missing."
    ),
}


def other_symptoms(count: int) -> str:
    """Phrase for symptoms left out of a "Because you reported …" list.

    Args:
        count: How many symptoms were not listed (at least 1).

    Returns:
        "1 other symptom" or "<count> other symptoms".

    Example:
        >>> other_symptoms(2)
        '2 other symptoms'
    """
    return "1 other symptom" if count == 1 else f"{count} other symptoms"


def lower_first(name: str) -> str:
    """Lowercase a display name's first letter for use inside a sentence.

    Names that start with an acronym ("ENT specialist") are kept as they are.

    Args:
        name: Display name from a dataset, e.g. "Joint pain".

    Returns:
        The in-sentence form, e.g. "joint pain".

    Example:
        >>> lower_first("ENT specialist")
        'ENT specialist'
    """
    if len(name) > 1 and name[1].isupper():
        return name
    return name[:1].lower() + name[1:]


def with_article(specialty_name: str) -> str:
    """Put "a" or "an" before a specialty name for use inside a sentence.

    The first letter is lowercased unless the name starts with an acronym, so
    "Dermatologist" becomes "a dermatologist" and "ENT specialist" stays
    "an ENT specialist".

    Args:
        specialty_name: Display name from the dataset.

    Returns:
        The name with its article.

    Example:
        >>> with_article("Eye specialist")
        'an eye specialist'
    """
    name = lower_first(specialty_name)
    # Why: "u" usually sounds like "you" ("a urologist"), so only a/e/i/o take "an".
    article = "an" if name[:1].lower() in "aeio" else "a"
    return f"{article} {name}"
