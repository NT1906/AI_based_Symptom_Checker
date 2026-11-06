"""Curated condition-specific self-care guidance service.

Responsibilities:
    - Load and index curated non-prescriptive supportive guidance per condition.
    - Provide fast O(1) condition lookup for self-care suggestions and warning signs.
    - Format and deduplicate guidance steps for triage result presentation (DR-05).
    - Guarantee zero diagnostic claims, zero drug prescriptions, and full compliance
      with the medical safety framework (idea §8, DR-05).

Owner: Kavya (knowledge) · Task: S2-KAV-1 · Requirements: idea §8, DR-05
Reviewed by: Dimple (Medical Safety & Privacy Lead)
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.knowledge.schemas import SelfCareGuidance

if TYPE_CHECKING:
    from collections.abc import Sequence

SELF_CARE_FILE = Path(__file__).parent / "data" / "self_care.json"


def _normalize_condition_id(raw_id: str) -> str:
    """Normalize condition identifier for lookup (stripped, lowercase).

    Args:
        raw_id: Raw condition string.

    Returns:
        Cleaned lowercase identifier.
    """
    return raw_id.strip().lower()


class SelfCareService:
    """Thread-safe in-memory index for condition self-care guidance.

    Validates and indexes curated guidance from ``data/self_care.json``.
    Provides fast lookup and deduplicated advice synthesis for triage results.

    Args:
        data_path: Optional path to custom self_care JSON file. Defaults to
            the packaged data in ``data/self_care.json``.

    Raises:
        FileNotFoundError: If the specified data file does not exist.
        ValueError: If JSON data is malformed or missing required schema fields.
    """

    def __init__(self, data_path: Path | None = None) -> None:
        path = data_path or SELF_CARE_FILE
        if not path.is_file():
            raise FileNotFoundError(f"Self-care data file not found at: {path}")

        try:
            with open(path, encoding="utf-8") as f:
                raw_payload = json.load(f)
        except json.JSONDecodeError as err:
            raise ValueError(f"Malformed self-care JSON in {path}: {err}") from err

        if not isinstance(raw_payload, dict) or "conditions" not in raw_payload:
            raise ValueError(
                f"Invalid self-care data format in {path}: expected 'conditions' array"
            )

        conditions_list = raw_payload["conditions"]
        if not isinstance(conditions_list, list):
            raise ValueError(f"Expected list of condition entries in {path}")

        self._index: dict[str, SelfCareGuidance] = {}
        for entry in conditions_list:
            model = SelfCareGuidance.model_validate(entry)
            norm_id = _normalize_condition_id(model.condition_id)
            if norm_id in self._index:
                raise ValueError(f"Duplicate condition_id in self-care data: {norm_id}")
            self._index[norm_id] = model

    def __len__(self) -> int:
        """Return the total number of indexed conditions."""
        return len(self._index)

    def __contains__(self, condition_id: str) -> bool:
        """Check if guidance exists for a given condition identifier."""
        return _normalize_condition_id(condition_id) in self._index

    def get_guidance(self, condition_id: str) -> SelfCareGuidance | None:
        """Look up curated self-care guidance for a single condition ID.

        Args:
            condition_id: Canonical condition identifier (case-insensitive).

        Returns:
            The matching SelfCareGuidance record, or None if not found.
        """
        if not condition_id or not isinstance(condition_id, str):
            return None
        return self._index.get(_normalize_condition_id(condition_id))

    def get_self_care_steps(
        self,
        condition_ids: Sequence[str],
        max_steps: int = 5,
    ) -> tuple[str, ...]:
        """Aggregate and deduplicate self-care advice across multiple conditions.

        Useful for feeding directly into ResultComposer or Orchestrator
        for low-risk (SELF_CARE) triage result displays per idea §8.

        Args:
            condition_ids: Sequence of candidate condition IDs in rank order.
            max_steps: Maximum total steps to return (default 5).

        Returns:
            Deduplicated tuple of general self-care advice strings.
        """
        if max_steps <= 0:
            return ()

        seen: set[str] = set()
        steps: list[str] = []

        for cid in condition_ids:
            guidance = self.get_guidance(cid)
            if guidance is None:
                continue
            for advice in guidance.general_advice:
                cleaned = advice.strip()
                norm = cleaned.lower()
                if norm not in seen:
                    seen.add(norm)
                    steps.append(cleaned)
                    if len(steps) >= max_steps:
                        return tuple(steps)

        return tuple(steps)

    def get_when_to_seek_care(
        self,
        condition_ids: Sequence[str],
        max_warnings: int = 4,
    ) -> tuple[str, ...]:
        """Aggregate and deduplicate clinical warning signs across conditions.

        Args:
            condition_ids: Sequence of candidate condition IDs in rank order.
            max_warnings: Maximum total warning signs to return (default 4).

        Returns:
            Deduplicated tuple of warning sign strings.
        """
        if max_warnings <= 0:
            return ()

        seen: set[str] = set()
        warnings: list[str] = []

        for cid in condition_ids:
            guidance = self.get_guidance(cid)
            if guidance is None:
                continue
            for warn in guidance.when_to_seek_care:
                cleaned = warn.strip()
                norm = cleaned.lower()
                if norm not in seen:
                    seen.add(norm)
                    warnings.append(cleaned)
                    if len(warnings) >= max_warnings:
                        return tuple(warnings)

        return tuple(warnings)

    def get_monitoring_tips(
        self,
        condition_ids: Sequence[str],
        max_tips: int = 3,
    ) -> tuple[str, ...]:
        """Aggregate and deduplicate monitoring tips across conditions.

        Args:
            condition_ids: Sequence of candidate condition IDs.
            max_tips: Maximum total tips to return (default 3).

        Returns:
            Deduplicated tuple of monitoring tip strings.
        """
        if max_tips <= 0:
            return ()

        seen: set[str] = set()
        tips: list[str] = []

        for cid in condition_ids:
            guidance = self.get_guidance(cid)
            if guidance is None:
                continue
            for tip in guidance.monitoring_tips:
                cleaned = tip.strip()
                norm = cleaned.lower()
                if norm not in seen:
                    seen.add(norm)
                    tips.append(cleaned)
                    if len(tips) >= max_tips:
                        return tuple(tips)

        return tuple(tips)

    def list_condition_ids(self) -> tuple[str, ...]:
        """Return all supported condition IDs in alphabetical order."""
        return tuple(sorted(self._index.keys()))


@lru_cache(maxsize=1)
def get_self_care_service(data_path: Path | None = None) -> SelfCareService:
    """Return the cached singleton instance of SelfCareService.

    Args:
        data_path: Optional custom path. If omitted, uses default self_care.json.

    Returns:
        Shared SelfCareService instance.
    """
    return SelfCareService(data_path)


def lookup_self_care(condition_id: str) -> SelfCareGuidance | None:
    """Convenience function to look up guidance for a condition.

    Args:
        condition_id: Canonical condition identifier.

    Returns:
        SelfCareGuidance or None.
    """
    return get_self_care_service().get_guidance(condition_id)


def get_self_care_guidance(
    condition_ids: Sequence[str],
    max_steps: int = 5,
) -> tuple[str, ...]:
    """Convenience function to aggregate self-care steps for multiple conditions.

    Args:
        condition_ids: Candidate condition IDs.
        max_steps: Max steps to return.

    Returns:
        Tuple of advice strings.
    """
    return get_self_care_service().get_self_care_steps(
        condition_ids, max_steps=max_steps
    )
