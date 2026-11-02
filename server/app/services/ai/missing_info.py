"""Missing-information detection engine for guided symptom assessment.

Responsibilities:
    - Identify missing duration, severity, onset, or anatomical location.
    - Rank information gaps by clinical triage priority (red flags first).
    - Provide deterministic guidance on whether clarification is warranted.

Owner: Nishith · Task: S1-NIT-2 · Requirements: FR-04, FR-19, FR-20
"""

from collections.abc import Sequence
from typing import Any

from app.services.ai.schemas import (
    Duration,
    ExtractedSymptom,
    MissingFieldEnum,
    MissingInfoItem,
    SeverityEnum,
)

# Symptoms that strongly require anatomical location for meaningful triage
SITE_SENSITIVE_SYMPTOMS: frozenset[str] = frozenset(
    {
        "skin_rash",
        "rash",
        "itchy_skin",
        "hives",
        "fluid_filled_blisters",
        "pimples",
        "small_itchy_bumps",
        "ring_shaped_rash",
        "skin_swelling",
        "joint_pain",
        "joint_swelling",
        "abdominal_pain",
        "lower_right_abdominal_pain",
        "upper_right_abdominal_pain",
        "lower_abdominal_pain",
        "abdominal_cramping",
        "lower_back_pain",
        "back_pain",
        "flank_pain",
        "ear_pain",
        "eye_pain",
        "pain_behind_eyes",
        "swollen_neck_glands",
        "muscle_stiffness",
        "spreading_redness",
        "non_blanching_rash",
        "saddle_numbness",
    }
)

# Safety-critical red flags where sudden onset or severity significantly alters triage
SAFETY_CRITICAL_SYMPTOMS: frozenset[str] = frozenset(
    {
        "chest_pain",
        "chest_tightness",
        "pressure_or_squeezing_in_chest",
        "pain_spreading_to_arm_jaw_or_back",
        "sudden_severe_headache",
        "facial_droop",
        "one_sided_weakness",
        "slurred_speech",
        "sudden_vision_loss",
        "difficulty_breathing",
        "shortness_of_breath",
        "bluish_lips_or_face",
        "throat_or_tongue_swelling",
        "vomiting_blood",
        "coughing_blood",
        "black_or_bloody_stool",
        "thoughts_of_self_harm",
        "seizure",
        "stiff_neck",
        "non_blanching_rash",
        "loss_of_bladder_or_bowel_control",
        "saddle_numbness",
        "confusion",
    }
)


def _to_extracted_symptom(raw: ExtractedSymptom | dict[str, Any]) -> ExtractedSymptom:
    """Normalize raw input dict or ExtractedSymptom into a typed ExtractedSymptom.

    Defensively sanitizes names, severities, and non-conforming structures.

    Args:
        raw: Raw dict representation or existing ExtractedSymptom model.

    Returns:
        Validated ExtractedSymptom instance.
    """
    if isinstance(raw, ExtractedSymptom):
        return raw

    clean_dict = dict(raw)
    raw_name = clean_dict.get("name")
    if not raw_name or not str(raw_name).strip():
        clean_dict["name"] = "unspecified_symptom"
    else:
        clean_dict["name"] = str(raw_name).strip().lower()

    # Normalize severity if invalid or string
    sev = clean_dict.get("severity")
    if isinstance(sev, str):
        try:
            clean_dict["severity"] = SeverityEnum(sev.upper())
        except ValueError:
            clean_dict["severity"] = SeverityEnum.UNKNOWN
    elif not isinstance(sev, SeverityEnum):
        clean_dict["severity"] = SeverityEnum.UNKNOWN

    # Normalize duration if invalid
    dur = clean_dict.get("duration")
    if dur is not None and not isinstance(dur, (Duration, dict)):
        clean_dict["duration"] = None

    return ExtractedSymptom.model_validate(clean_dict)


def detect_missing_information(
    symptoms: Sequence[ExtractedSymptom | dict[str, Any]],
) -> list[MissingInfoItem]:
    """Identify missing clinical attributes across reported symptoms.

    Evaluates duration, severity, anatomical body site, and onset for each
    reported symptom, ordering results by clinical urgency (safety-critical
    gaps first).

    Args:
        symptoms: Sequence of extracted or active symptoms.

    Returns:
        List of MissingInfoItem models sorted in priority order (1 = highest urgency).

    Example:
        >>> s = [ExtractedSymptom(name="chest_pain")]
        >>> gaps = detect_missing_information(s)
        >>> gaps[0].priority
        1
        >>> gaps[0].missing_field
        <MissingFieldEnum.ONSET: 'ONSET'>
    """
    if not symptoms:
        return []

    items: list[MissingInfoItem] = []
    normalized_symptoms = [_to_extracted_symptom(s) for s in symptoms]

    for idx, sym in enumerate(normalized_symptoms):
        name = sym.name.lower()
        is_primary = idx == 0
        is_safety_critical = name in SAFETY_CRITICAL_SYMPTOMS

        # Check 1: Onset on safety-critical symptoms (e.g. sudden onset of chest pain)
        if is_safety_critical and not sym.onset:
            items.append(
                MissingInfoItem(
                    symptom_name=sym.name,
                    missing_field=MissingFieldEnum.ONSET,
                    priority=1,
                    reason=(
                        f"Onset timing for safety-critical symptom '{sym.name}' is"
                        " required to assess emergency triage status."
                    ),
                )
            )

        # Check 2: Severity check
        if sym.severity == SeverityEnum.UNKNOWN:
            priority = 1 if is_safety_critical else (2 if is_primary else 4)
            items.append(
                MissingInfoItem(
                    symptom_name=sym.name,
                    missing_field=MissingFieldEnum.SEVERITY,
                    priority=priority,
                    reason=(
                        f"Clinical severity for '{sym.name}' is unknown; needed to"
                        " differentiate self-care from physician consult."
                    ),
                )
            )

        # Check 3: Duration check
        if sym.duration is None:
            priority = 1 if is_safety_critical else (2 if is_primary else 4)
            items.append(
                MissingInfoItem(
                    symptom_name=sym.name,
                    missing_field=MissingFieldEnum.DURATION,
                    priority=priority,
                    reason=(
                        f"Duration of '{sym.name}' is unspecified; required for"
                        " acute vs chronic assessment."
                    ),
                )
            )

        # Check 4: Anatomical site check on site-sensitive symptoms
        has_site = bool(sym.body_site or sym.body_location)
        if name in SITE_SENSITIVE_SYMPTOMS and not has_site:
            items.append(
                MissingInfoItem(
                    symptom_name=sym.name,
                    missing_field=MissingFieldEnum.BODY_SITE,
                    priority=3,
                    reason=(
                        f"Specific anatomical location for '{sym.name}' is needed"
                        " to identify condition pattern."
                    ),
                )
            )

    # Sort deterministically by priority ascending, then symptom name
    items.sort(key=lambda item: (item.priority, item.symptom_name))
    return items


def should_request_clarification(
    symptoms: Sequence[ExtractedSymptom | dict[str, Any]],
) -> tuple[bool, str | None]:
    """Determine whether active symptoms warrant follow-up clarification.

    Clarification is indicated if:
    1. Any safety-critical red-flag symptom is missing onset, severity, or duration.
    2. Any reported symptom is missing duration.
    3. Any site-sensitive symptom lacks anatomical body site.

    Args:
        symptoms: Sequence of extracted or active symptoms.

    Returns:
        Tuple of (requires_clarification: bool, reason: str | None).
    """
    gaps = detect_missing_information(symptoms)
    if not gaps:
        return False, None

    # Filter for gaps that mandate clarification during intake
    mandatory_gaps = [
        g
        for g in gaps
        if g.priority == 1
        or g.missing_field in (MissingFieldEnum.DURATION, MissingFieldEnum.BODY_SITE)
    ]
    if mandatory_gaps:
        return True, mandatory_gaps[0].reason

    return False, None
