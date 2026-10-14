"""Validator for the symptom vocabulary dataset (``symptoms.json``).

Responsibilities:
    - Check structure: every symptom record has the required fields.
    - Verify alignment: every symptom ID, name and body system matches the
      condition dataset (``conditions.json``).
    - Verify coverage: every symptom from the condition dataset is present.
    - Check lay terms: each is a non-empty string, and no term maps to more
      than one symptom (ambiguity check).

Run after editing the dataset::

    python ml/datasets/symptoms/validate_symptoms.py

Owner: Kavya (AI/ML, Database) · Task: S0-KAV-1 · Requirements: FR-03
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SYMPTOMS_PATH = Path(__file__).with_name("symptoms.json")
CONDITIONS_PATH = Path(__file__).parent.parent / "conditions" / "conditions.json"

ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

BODY_SYSTEMS = frozenset(
    {"general", "neurological", "ent", "respiratory", "eye", "cardiovascular"}
    | {"gastrointestinal", "urinary", "musculoskeletal", "skin", "mental_health"}
)


def load_json(path: Path) -> dict[str, Any]:
    """Read and parse a JSON file.

    Args:
        path: Absolute or relative path to the JSON file.

    Returns:
        The parsed JSON as a dictionary.

    Raises:
        OSError: If the file cannot be read.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    with path.open(encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return data


def _load_condition_symptoms(path: Path) -> dict[str, dict[str, str]]:
    """Build a lookup of symptom ID → {name, body_system} from the condition dataset.

    Args:
        path: Path to ``conditions.json``.

    Returns:
        A dict keyed by symptom ID whose values contain ``name`` and
        ``body_system`` as strings.
    """
    data = load_json(path)
    result: dict[str, dict[str, str]] = {}
    for item in data.get("symptoms", []):
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            result[item["id"]] = {
                "name": item.get("name", ""),
                "body_system": item.get("body_system", ""),
            }
    return result


def validate_symptoms(
    data: dict[str, Any],
    condition_symptoms: dict[str, dict[str, str]] | None = None,
) -> list[str]:
    """Check a parsed symptom vocabulary and describe every problem found.

    Args:
        data: The parsed symptom vocabulary, as returned by :func:`load_json`.
        condition_symptoms: Optional pre-loaded condition symptom lookup.
            If ``None``, it is loaded from the default ``conditions.json`` path.

    Returns:
        Human-readable error messages.  An empty list means the dataset is valid.

    Example:
        >>> validate_symptoms(load_json(SYMPTOMS_PATH))
        []
    """
    errors: list[str] = []

    # --- top-level fields ---
    for key in ("schema_version", "dataset_version", "intended_use"):
        if not isinstance(data.get(key), str) or not data[key]:
            errors.append(f"top level: '{key}' must be a non-empty string")

    body_systems = data.get("body_systems")
    if not isinstance(body_systems, list) or not body_systems:
        errors.append("top level: 'body_systems' must be a non-empty list")
    else:
        unknown = set(body_systems) - BODY_SYSTEMS
        if unknown:
            errors.append(f"top level: unknown body_systems {sorted(unknown)}")
        missing = BODY_SYSTEMS - set(body_systems)
        if missing:
            errors.append(f"top level: missing body_systems {sorted(missing)}")

    symptoms = data.get("symptoms")
    if not isinstance(symptoms, list) or not symptoms:
        errors.append("top level: 'symptoms' must be a non-empty list")
        return errors

    # --- load condition reference ---
    if condition_symptoms is None:
        try:
            condition_symptoms = _load_condition_symptoms(CONDITIONS_PATH)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"cannot load condition dataset: {exc}")
            return errors

    # --- per-symptom checks ---
    seen_ids: list[str] = []
    all_lay_terms: list[tuple[str, str]] = []  # (normalised term, symptom id)

    for index, item in enumerate(symptoms):
        if not isinstance(item, dict):
            errors.append(f"symptoms[{index}]: must be an object, got {item!r}")
            continue

        item_id = item.get("id")
        where = f"symptom '{item_id}'"

        # id format
        if not isinstance(item_id, str) or not ID_PATTERN.match(item_id):
            errors.append(
                f"symptoms[{index}]: 'id' must be snake_case, got {item_id!r}"
            )
            continue

        seen_ids.append(item_id)

        # name
        if not isinstance(item.get("name"), str) or not item["name"].strip():
            errors.append(f"{where}: 'name' must be a non-empty string")

        # body_system
        bs = item.get("body_system")
        if bs not in BODY_SYSTEMS:
            errors.append(f"{where}: unknown body_system {bs!r}")

        # alignment with condition dataset
        if item_id in condition_symptoms:
            cond = condition_symptoms[item_id]
            if item.get("name") != cond["name"]:
                errors.append(
                    f"{where}: name {item.get('name')!r} does not match "
                    f"conditions.json {cond['name']!r}"
                )
            if item.get("body_system") != cond["body_system"]:
                errors.append(
                    f"{where}: body_system {item.get('body_system')!r} does not match "
                    f"conditions.json {cond['body_system']!r}"
                )
        else:
            errors.append(
                f"{where}: id not found in conditions.json — vocabularies are out of sync"
            )

        # lay_terms
        lay = item.get("lay_terms")
        if not isinstance(lay, list):
            errors.append(f"{where}: 'lay_terms' must be a list")
        elif not lay:
            errors.append(f"{where}: 'lay_terms' must not be empty")
        else:
            for term in lay:
                if not isinstance(term, str) or not term.strip():
                    errors.append(f"{where}: lay term must be a non-empty string")
                else:
                    all_lay_terms.append((term.strip().lower(), item_id))

    # duplicate IDs
    for item_id, count in Counter(seen_ids).items():
        if count > 1:
            errors.append(f"symptoms: duplicate id '{item_id}'")

    # coverage: every condition symptom must be present
    missing_ids = set(condition_symptoms.keys()) - set(seen_ids)
    for mid in sorted(missing_ids):
        errors.append(
            f"symptom '{mid}' exists in conditions.json but is missing from "
            f"the vocabulary"
        )

    # ambiguity: no lay term should map to more than one symptom
    term_to_ids: dict[str, set[str]] = {}
    for term, sid in all_lay_terms:
        term_to_ids.setdefault(term, set()).add(sid)
    for term, sids in sorted(term_to_ids.items()):
        if len(sids) > 1:
            errors.append(f"ambiguous lay term '{term}' maps to {sorted(sids)}")

    return errors


def main(argv: list[str] | None = None) -> int:
    """Validate a symptom vocabulary file and print the result.

    Args:
        argv: Command-line arguments (without the program name).  An optional
            first argument is the path to the symptoms file; defaults to
            ``symptoms.json``.

    Returns:
        Process exit code: 0 when valid, 1 when problems were found.

    Side effects:
        Writes a summary or the list of problems to stdout/stderr.
    """
    args = sys.argv[1:] if argv is None else argv
    path = Path(args[0]) if args else SYMPTOMS_PATH
    data = load_json(path)
    errors = validate_symptoms(data)
    if errors:
        sys.stderr.write(f"{path}: {len(errors)} problem(s)\n")
        sys.stderr.writelines(f"  - {error}\n" for error in errors)
        return 1
    symptom_count = len(data.get("symptoms", []))
    lay_count = sum(len(s.get("lay_terms", [])) for s in data.get("symptoms", []))
    sys.stdout.write(f"{path}: OK ({symptom_count} symptoms, {lay_count} lay terms)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
