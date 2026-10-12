"""Validator for the condition dataset (``conditions.json``).

Responsibilities:
    - Check the structure of every section: specialties, symptoms, red flags,
      conditions and sources.
    - Check every cross-reference (a condition's symptoms, specialty, red flags
      and sources must exist), so the predictor and risk engine never meet an
      unknown ID at runtime.
    - Catch data mistakes that would silently hurt predictions, such as a
      symptom no one uses. Condition-level rules live in ``condition_checks.py``.

Run it after editing the dataset:
    python ml/datasets/conditions/validate_conditions.py

Owner: Nisarg (prediction) · Task: S0-NIS-1 · Requirements: DR-02, DR-03, DR-04
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from condition_checks import (
    check_conditions,
    check_references,
    only_records,
    require_text,
)

DATASET_PATH = Path(__file__).with_name("conditions.json")

ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

SEVERITIES = frozenset({"MILD", "MODERATE", "SEVERE"})
BODY_SYSTEMS = frozenset(
    {"general", "neurological", "ent", "respiratory", "eye", "cardiovascular"}
    | {"gastrointestinal", "urinary", "musculoskeletal", "skin", "mental_health"}
)
RED_FLAG_CATEGORIES = frozenset(
    {"cardiac", "stroke", "neurological", "breathing", "anaphylaxis"}
    | {"infection", "bleeding", "abdominal", "dehydration", "mental_health"}
)

Dataset = dict[str, Any]  # Any: parsed JSON; every field is checked below before use.


def load_dataset(path: Path = DATASET_PATH) -> Dataset:
    """Read the dataset JSON file.

    Args:
        path: Location of the JSON file. Defaults to the ``conditions.json``
            next to this module.

    Returns:
        The parsed dataset as a dictionary.

    Raises:
        OSError: If the file cannot be read.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    with path.open(encoding="utf-8") as f:
        data: Dataset = json.load(f)
    return data


def validate_dataset(data: Dataset) -> list[str]:
    """Check a parsed dataset and describe every problem found.

    Args:
        data: The parsed dataset, as returned by :func:`load_dataset`.

    Returns:
        Human-readable error messages. An empty list means the dataset is valid.

    Example:
        >>> validate_dataset(load_dataset())
        []
    """
    errors: list[str] = []
    for key in ("schema_version", "dataset_version", "intended_use"):
        if not isinstance(data.get(key), str) or not data[key]:
            errors.append(f"top level: '{key}' must be a non-empty string")
    sections = ("specialties", "symptoms", "red_flags", "conditions", "sources")
    for key in sections:
        if not isinstance(data.get(key), list) or not data[key]:
            errors.append(f"top level: '{key}' must be a non-empty list")
    if errors:
        return errors

    ids = {key: _collect_ids(data[key], key, errors) for key in sections}
    errors += _check_specialties(data["specialties"])
    errors += _check_symptoms(data["symptoms"])
    errors += _check_sources(data["sources"])
    errors += _check_red_flags(data["red_flags"], ids["symptoms"], ids["sources"])
    errors += check_conditions(data["conditions"], ids)
    errors += _check_unused_symptoms(data, ids["symptoms"])
    return errors


def _collect_ids(items: list[Any], section: str, errors: list[str]) -> set[str]:
    """Collect the IDs of one section, reporting malformed records and IDs.

    This is the one place a non-object record is reported; every other check
    skips it through ``only_records`` so the problem is listed once.
    """
    seen: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"{section}[{index}]: must be an object, got {item!r}")
            continue
        item_id = item.get("id")
        if not isinstance(item_id, str) or not ID_PATTERN.match(item_id):
            errors.append(
                f"{section}[{index}]: 'id' must be snake_case, got {item_id!r}"
            )
            continue
        seen.append(item_id)
    for item_id, count in Counter(seen).items():
        if count > 1:
            errors.append(f"{section}: duplicate id '{item_id}'")
    return set(seen)


def _check_specialties(specialties: list[dict[str, Any]]) -> list[str]:
    """Each specialty needs a display name and a map search query (S2 referral)."""
    errors: list[str] = []
    for item in only_records(specialties):
        errors += require_text(
            item, ("name", "map_query"), f"specialty '{item.get('id')}'"
        )
    return errors


def _check_symptoms(symptoms: list[dict[str, Any]]) -> list[str]:
    """Each symptom needs a display name and a known body system."""
    errors: list[str] = []
    for item in only_records(symptoms):
        where = f"symptom '{item.get('id')}'"
        errors += require_text(item, ("name",), where)
        if item.get("body_system") not in BODY_SYSTEMS:
            errors.append(f"{where}: unknown body_system {item.get('body_system')!r}")
    return errors


def _check_sources(sources: list[dict[str, Any]]) -> list[str]:
    """Each source needs a title and an https URL."""
    errors: list[str] = []
    for item in only_records(sources):
        where = f"source '{item.get('id')}'"
        errors += require_text(item, ("title", "url"), where)
        if isinstance(item.get("url"), str) and not item["url"].startswith("https://"):
            errors.append(f"{where}: url must start with https://")
    return errors


def _check_red_flags(
    red_flags: list[dict[str, Any]], symptom_ids: set[str], source_ids: set[str]
) -> list[str]:
    """Check red-flag fields and that every trigger is a well-formed symptom rule."""
    errors: list[str] = []
    for item in only_records(red_flags):
        where = f"red flag '{item.get('id')}'"
        errors += require_text(item, ("label", "rationale"), where)
        if item.get("category") not in RED_FLAG_CATEGORIES:
            errors.append(f"{where}: unknown category {item.get('category')!r}")
        errors += check_references(item.get("sources"), source_ids, where, "sources")
        triggers = item.get("triggers")
        if not isinstance(triggers, list) or not triggers:
            errors.append(f"{where}: 'triggers' must be a non-empty list")
            continue
        for index, trigger in enumerate(triggers):
            errors += _check_trigger(trigger, symptom_ids, f"{where} trigger {index}")
    return errors


def _check_trigger(trigger: Any, symptom_ids: set[str], where: str) -> list[str]:
    """A trigger fires when all of its parts are present (``all_of``)."""
    parts = trigger.get("all_of") if isinstance(trigger, dict) else None
    if not isinstance(parts, list) or not parts:
        return [f"{where}: 'all_of' must be a non-empty list"]
    errors: list[str] = []
    for part in parts:
        symptom = part.get("symptom") if isinstance(part, dict) else None
        if symptom not in symptom_ids:
            errors.append(f"{where}: unknown symptom reference {symptom!r}")
        if (
            isinstance(part, dict)
            and "min_severity" in part
            and part["min_severity"] not in SEVERITIES
        ):
            errors.append(f"{where}: unknown min_severity {part['min_severity']!r}")
    return errors


def _check_unused_symptoms(data: Dataset, symptom_ids: set[str]) -> list[str]:
    """Every listed symptom should be used by a condition or a red flag."""
    used: set[Any] = set()
    for condition in only_records(data["conditions"]):
        used.update(s.get("id") for s in only_records(condition.get("symptoms")))
    for flag in only_records(data["red_flags"]):
        for trigger in only_records(flag.get("triggers")):
            used.update(p.get("symptom") for p in only_records(trigger.get("all_of")))
    return [
        f"symptom '{s}' is not used by any condition or red flag"
        for s in sorted(symptom_ids - used)
    ]


def main(argv: list[str] | None = None) -> int:
    """Validate a dataset file and print the result.

    Args:
        argv: Command-line arguments (without the program name). An optional
            first argument is the path to the dataset; defaults to ``conditions.json``.

    Returns:
        Process exit code: 0 when valid, 1 when problems were found.

    Side effects:
        Writes a summary or the list of problems to stdout/stderr.
    """
    args = sys.argv[1:] if argv is None else argv
    path = Path(args[0]) if args else DATASET_PATH
    data = load_dataset(path)
    errors = validate_dataset(data)
    if errors:
        sys.stderr.write(f"{path}: {len(errors)} problem(s)\n")
        sys.stderr.writelines(f"  - {error}\n" for error in errors)
        return 1
    sys.stdout.write(
        f"{path}: OK ({len(data['conditions'])} conditions, {len(data['symptoms'])} symptoms, "
        f"{len(data['red_flags'])} red flags)\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
