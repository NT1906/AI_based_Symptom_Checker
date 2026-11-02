"""Loader for the condition dataset shipped with the server.

Responsibilities:
    - Read ``data/conditions.json`` (a copy of ``ml/datasets/conditions/``,
      kept identical by a parity test, because the server image has no ``ml/``).
    - Validate every condition and red-flag record, and check that every
      symptom they name exists in the dataset's symptom list, so prediction
      and the risk engine never meet an unknown ID at runtime.
    - Cache the parsed catalog for the life of the process.

Owner: Nisarg (prediction) · Task: S1-NIS-1, S1-NIS-2 · Requirements: FR-05,
DR-02, DR-03
"""

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from pydantic import ValidationError as PydanticValidationError

from app.services.prediction.risk_schemas import RedFlag
from app.services.prediction.schemas import ConditionProfile

DATA_FILE = Path(__file__).parent / "data" / "conditions.json"


class ConditionDataError(RuntimeError):
    """Raised when the condition dataset is missing or invalid.

    This is a deployment fault, not a user error, so it is raised at startup
    or first use and is never turned into a user-facing message.
    """


class _SymptomEntry(BaseModel):
    """Only the symptom ID is needed to check references."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str = Field(min_length=1)


class _DatasetFile(BaseModel):
    """The parts of ``conditions.json`` the predictor reads."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    dataset_version: str = Field(min_length=1)
    symptoms: tuple[_SymptomEntry, ...] = Field(min_length=1)
    conditions: tuple[ConditionProfile, ...] = Field(min_length=1)
    # Why: a dataset without red flags would silently disable URGENT (DR-02).
    red_flags: tuple[RedFlag, ...] = Field(min_length=1)


class ConditionCatalog:
    """Validated, read-only view of the condition dataset."""

    def __init__(
        self,
        conditions: tuple[ConditionProfile, ...],
        symptom_ids: frozenset[str],
        dataset_version: str,
        red_flags: tuple[RedFlag, ...] = (),
    ) -> None:
        """Build a catalog from already-validated records.

        Args:
            conditions: Every condition profile, in dataset order.
            symptom_ids: Every canonical symptom ID in the dataset.
            dataset_version: Dataset version label, e.g. ``v0``.
            red_flags: Every red-flag rule, in dataset order.

        Raises:
            ConditionDataError: If a condition or red-flag ID repeats, or a
                record names a symptom that is not in ``symptom_ids``.
        """
        _check_references(conditions, symptom_ids)
        _check_red_flags(red_flags, symptom_ids)
        self.conditions = conditions
        self.red_flags = red_flags
        self.symptom_ids = symptom_ids
        self.dataset_version = dataset_version
        self._by_id = {condition.id: condition for condition in conditions}

    def get(self, condition_id: str) -> ConditionProfile | None:
        """Return one condition by ID, or ``None`` if it does not exist."""
        return self._by_id.get(condition_id)


def load_catalog(path: Path = DATA_FILE) -> ConditionCatalog:
    """Read and validate a condition dataset file.

    Args:
        path: Location of the JSON file. Defaults to the packaged copy.

    Returns:
        The validated catalog.

    Raises:
        ConditionDataError: If the file cannot be read, is not valid JSON, or
            breaks the schema or a reference check.
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        parsed = _DatasetFile.model_validate(raw)
    except (OSError, json.JSONDecodeError, PydanticValidationError) as exc:
        raise ConditionDataError(f"invalid condition dataset {path}: {exc}") from exc
    return ConditionCatalog(
        conditions=parsed.conditions,
        symptom_ids=frozenset(symptom.id for symptom in parsed.symptoms),
        dataset_version=parsed.dataset_version,
        red_flags=parsed.red_flags,
    )


@lru_cache(maxsize=1)
def get_catalog() -> ConditionCatalog:
    """Return the packaged catalog, loading it once per process.

    Returns:
        The shared, read-only catalog.

    Raises:
        ConditionDataError: If the packaged dataset is missing or invalid.
    """
    return load_catalog()


def _check_references(
    conditions: tuple[ConditionProfile, ...], symptom_ids: frozenset[str]
) -> None:
    """Reject repeated condition IDs and symptoms missing from the dataset."""
    seen: set[str] = set()
    for condition in conditions:
        if condition.id in seen:
            raise ConditionDataError(f"duplicate condition id {condition.id!r}")
        seen.add(condition.id)
        unknown = {s.id for s in condition.symptoms} - symptom_ids
        if unknown:
            raise ConditionDataError(
                f"condition {condition.id!r} uses unknown symptom(s) {sorted(unknown)}"
            )


def _check_red_flags(
    red_flags: tuple[RedFlag, ...], symptom_ids: frozenset[str]
) -> None:
    """Reject repeated red-flag IDs and triggers naming unknown symptoms."""
    seen: set[str] = set()
    for red_flag in red_flags:
        if red_flag.id in seen:
            raise ConditionDataError(f"duplicate red flag id {red_flag.id!r}")
        seen.add(red_flag.id)
        named = {part.symptom for t in red_flag.triggers for part in t.all_of}
        unknown = named - symptom_ids
        if unknown:
            raise ConditionDataError(
                f"red flag {red_flag.id!r} uses unknown symptom(s) {sorted(unknown)}"
            )
