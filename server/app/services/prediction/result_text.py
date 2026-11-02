"""User-facing wording for assessment results: next steps, referral reasons, limits.

Responsibilities:
    - Keep every sentence the result composer can show in one reviewable place
      (Dimple reviews wording, DR-05).
    - Follow the safe-wording rules: "may be related to", never "you have";
      general advice only, never a drug, dose or treatment (AI_RULES.md §2).

The composer still runs every sentence through the safety-wording guard.

Owner: Nisarg (prediction) · Task: S1-NIS-3 · Requirements: FR-07, DR-01, DR-05
"""

from app.schemas.enums import RiskLevel

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
    is_acronym = len(specialty_name) > 1 and specialty_name[1].isupper()
    name = (
        specialty_name
        if is_acronym
        else specialty_name[:1].lower() + specialty_name[1:]
    )
    # Why: "u" usually sounds like "you" ("a urologist"), so only a/e/i/o take "an".
    article = "an" if name[:1].lower() in "aeio" else "a"
    return f"{article} {name}"
