"""Condition rules for the condition dataset validator.

Responsibilities:
    - Check each condition's fields: ICD-10 code, group, specialty, base risk,
      weighted symptoms and references to red flags and sources.
    - Check across conditions: no reused ICD-10 code and no two conditions the
      predictor could not tell apart.
    - Provide the small helpers shared with ``validate_conditions.py``.

Owner: Nisarg (prediction) · Task: S0-NIS-1 · Requirements: DR-03, DR-04
"""

import re
from collections import Counter
from collections.abc import Iterable
from typing import Any

# WHO ICD-10 (2019): letter, two digits, optional ".digit(s)". Not ICD-10-CM.
ICD10_PATTERN = re.compile(r"^[A-Z][0-9]{2}(\.[0-9]{1,2})?$")
RISK_LEVELS = frozenset({"SELF_CARE", "CONSULT_DOCTOR", "URGENT"})
CONDITION_GROUPS = frozenset({"primary_care", "infection", "skin", "emergency"})
SYMPTOM_WEIGHTS = frozenset({1, 2, 3})
HALLMARK_WEIGHT = 3
MIN_SYMPTOMS_PER_CONDITION = 2


def require_text(item: dict[str, Any], fields: Iterable[str], where: str) -> list[str]:
    """Report fields that are missing or not a non-empty string.

    Args:
        item: One record from the dataset.
        fields: Names of the fields that must hold text.
        where: Prefix for the error message, e.g. ``"condition 'dengue'"``.

    Returns:
        One error message per missing or empty field.
    """
    return [
        f"{where}: '{field}' must be a non-empty string"
        for field in fields
        if not isinstance(item.get(field), str) or not item[field].strip()
    ]


def check_references(values: Any, known: set[str], where: str, field: str) -> list[str]:
    """Report a reference list that is not a list of known IDs.

    Args:
        values: The field's value, expected to be a list of IDs.
        known: Every valid ID for this kind of reference.
        where: Prefix for the error message.
        field: Field name, used in the error message.

    Returns:
        One error message per unknown ID, or one if ``values`` is not a list.
    """
    if not isinstance(values, list):
        return [f"{where}: '{field}' must be a list"]
    return [
        f"{where}: unknown {field} reference '{value}'"
        for value in values
        if value not in known
    ]


def check_conditions(
    conditions: list[dict[str, Any]], ids: dict[str, set[str]]
) -> list[str]:
    """Check every condition, then look for problems across conditions.

    Args:
        conditions: The dataset's ``conditions`` section.
        ids: Valid IDs per section (``specialties``, ``symptoms``,
            ``red_flags``, ``sources``).

    Returns:
        Human-readable error messages; empty when every condition is valid.
    """
    errors: list[str] = []
    for item in conditions:
        errors += _check_condition(item, ids)
    errors += _check_duplicate_icd10(conditions)
    errors += _check_identical_profiles(conditions)
    return errors


def _check_condition(item: dict[str, Any], ids: dict[str, set[str]]) -> list[str]:
    """Check one condition's fields and references."""
    where = f"condition '{item.get('id')}'"
    errors = require_text(item, ("name",), where)
    if not isinstance(item.get("icd10"), str) or not ICD10_PATTERN.match(item["icd10"]):
        errors.append(f"{where}: invalid ICD-10 code {item.get('icd10')!r}")
    if item.get("group") not in CONDITION_GROUPS:
        errors.append(f"{where}: unknown group {item.get('group')!r}")
    if item.get("specialty") not in ids["specialties"]:
        errors.append(f"{where}: unknown specialty {item.get('specialty')!r}")
    if item.get("base_risk") not in RISK_LEVELS:
        errors.append(f"{where}: unknown base_risk {item.get('base_risk')!r}")
    if not isinstance(item.get("visual"), bool):
        errors.append(f"{where}: 'visual' must be true or false")
    errors += check_references(
        item.get("red_flags"), ids["red_flags"], where, "red_flags"
    )
    errors += check_references(item.get("sources"), ids["sources"], where, "sources")
    if isinstance(item.get("sources"), list) and not item["sources"]:
        errors.append(f"{where}: needs at least one source")
    errors += _check_condition_symptoms(item.get("symptoms"), ids["symptoms"], where)
    return errors


def _check_condition_symptoms(
    symptoms: Any, symptom_ids: set[str], where: str
) -> list[str]:
    """A condition needs enough weighted symptoms, including one hallmark symptom."""
    if not isinstance(symptoms, list) or len(symptoms) < MIN_SYMPTOMS_PER_CONDITION:
        return [f"{where}: needs at least {MIN_SYMPTOMS_PER_CONDITION} symptoms"]
    errors: list[str] = []
    seen: list[Any] = []
    for entry in symptoms:
        symptom = entry.get("id") if isinstance(entry, dict) else None
        weight = entry.get("weight") if isinstance(entry, dict) else None
        seen.append(symptom)
        if symptom not in symptom_ids:
            errors.append(f"{where}: unknown symptom reference {symptom!r}")
        # Why: bool is a subclass of int in Python, so `True` would pass as weight 1.
        if isinstance(weight, bool) or weight not in SYMPTOM_WEIGHTS:
            errors.append(f"{where}: symptom {symptom!r} has invalid weight {weight!r}")
    errors += [
        f"{where}: symptom '{s}' listed twice"
        for s, n in Counter(seen).items()
        if n > 1
    ]
    if not any(
        isinstance(e, dict) and e.get("weight") == HALLMARK_WEIGHT for e in symptoms
    ):
        errors.append(
            f"{where}: needs at least one hallmark symptom (weight {HALLMARK_WEIGHT})"
        )
    return errors


def _check_duplicate_icd10(conditions: list[dict[str, Any]]) -> list[str]:
    """Two conditions with the same ICD-10 code are almost always a copy-paste mistake."""
    codes = Counter(c.get("icd10") for c in conditions)
    return [
        f"conditions: ICD-10 code '{code}' used more than once"
        for code, n in codes.items()
        if n > 1
    ]


def _check_identical_profiles(conditions: list[dict[str, Any]]) -> list[str]:
    """Conditions with identical symptom sets cannot be told apart by the predictor."""
    profiles: dict[frozenset[str], str] = {}
    errors: list[str] = []
    for item in conditions:
        symptoms = item.get("symptoms")
        if not isinstance(symptoms, list):
            continue
        profile = frozenset(str(s.get("id")) for s in symptoms if isinstance(s, dict))
        if profile in profiles:
            first = profiles[profile]
            errors.append(
                f"conditions '{first}' and '{item.get('id')}' have identical symptoms"
            )
        profiles.setdefault(profile, str(item.get("id")))
    return errors
