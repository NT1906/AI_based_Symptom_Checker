"""AI gateway decorator that minimizes outbound text before provider calls.

Responsibilities:
    - Scrub extraction and clarification inputs through a single boundary.
    - Reject invalid or excessive payloads before invoking a provider.

Owner: Harsh · Task: S1-HAR-2 · Requirements: NFR-04, DR-06
"""

import math
from dataclasses import dataclass
from typing import Any

from app.services.ai.gateway import AiGateway, AiValidationError
from app.services.ai.schemas import ClarificationResult, ExtractionResult
from app.services.privacy.pii import scrub_pii

MAX_PAYLOAD_DEPTH = 12
MAX_PAYLOAD_NODES = 2_048
MAX_PAYLOAD_CHARACTERS = 40_000
_INVALID_INPUT = "AI privacy input validation failed."


@dataclass
class _Budget:
    """Track per-call bounds without retaining text or identifiers."""

    nodes: int = 0
    characters: int = 0

    def add(self, depth: int, characters: int = 0) -> None:
        """Reject excessive work without including submitted data in errors."""
        self.nodes += 1
        self.characters += characters
        if (
            depth > MAX_PAYLOAD_DEPTH
            or self.nodes > MAX_PAYLOAD_NODES
            or self.characters > MAX_PAYLOAD_CHARACTERS
        ):
            raise ValueError(_INVALID_INPUT)


# Any is confined to the existing AiGateway's dict[str, Any] JSON boundary.
# Runtime validation below rejects non-JSON objects instead of stringifying them.
def _scrub_value(
    value: Any, names: tuple[str, ...], budget: _Budget, depth: int = 0
) -> Any:
    """Copy and scrub JSON values and keys with a shared bounded traversal."""
    budget.add(depth)
    if isinstance(value, str):
        budget.add(depth, len(value))
        result = scrub_pii(value, known_names=names)
        budget.characters += max(0, len(result) - len(value))
        if budget.characters > MAX_PAYLOAD_CHARACTERS:
            raise ValueError(_INVALID_INPUT)
        return result
    if value is None or type(value) in (bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if isinstance(value, list):
        return [_scrub_value(item, names, budget, depth + 1) for item in value]
    if isinstance(value, dict):
        return _scrub_mapping(value, names, budget, depth)
    raise ValueError(_INVALID_INPUT)


def _scrub_mapping(
    value: dict[str, Any], names: tuple[str, ...], budget: _Budget, depth: int
) -> dict[str, Any]:
    """Scrub keys too, rejecting collisions instead of losing clinical fields."""
    result: dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise ValueError(_INVALID_INPUT)
        clean_key = _scrub_value(key, names, budget, depth + 1)
        if clean_key in result:
            raise ValueError(_INVALID_INPUT)
        result[clean_key] = _scrub_value(item, names, budget, depth + 1)
    return result


class PrivacyAiGateway:
    """Wrap a provider with bounded outbound redaction, without logging input.

    This implements AiGateway and inherits scrub_pii's documented detection
    limits. It must be wired by the AI owner before application calls are covered.
    Provider outputs and failures pass through; safe wording is a separate task.
    """

    def __init__(
        self, provider: AiGateway, *, known_names: tuple[str, ...] = ()
    ) -> None:
        """Configure a wrapper around an existing provider.

        Args:
            provider: Gateway implementation; this wrapper makes no HTTP calls.
            known_names: Optional trusted names retained only in this instance.
                Use a per-assessment instance if supplying personal names; never
                put these names into a globally cached wrapper or logs.

        Raises:
            AiValidationError: Known-name configuration is invalid.
        """
        try:
            scrub_pii("", known_names=known_names)
        except ValueError:
            raise AiValidationError(_INVALID_INPUT) from None
        self._provider = provider
        self._known_names = known_names

    async def extract_symptoms(
        self, message: str, conversation_history: str = ""
    ) -> ExtractionResult:
        """Scrub message and history before requesting symptom extraction.

        Args:
            message: Current text, subject to the scrubber's per-string limit.
            conversation_history: Previous turns; the same redaction applies.

        Returns:
            The provider's validated extraction result unchanged.

        Raises:
            AiValidationError: Input is invalid; the provider is not called.
            AiError: Provider failures propagate without raw-input retry.
        """
        try:
            if not isinstance(message, str) or not isinstance(
                conversation_history, str
            ):
                raise ValueError(_INVALID_INPUT)
            budget = _Budget()
            clean_message = _scrub_value(message, self._known_names, budget)
            clean_history = _scrub_value(
                conversation_history, self._known_names, budget
            )
        except ValueError:
            raise AiValidationError(_INVALID_INPUT) from None
        return await self._provider.extract_symptoms(clean_message, clean_history)

    async def generate_clarification(
        self, structured_state: dict[str, Any], already_asked: list[str]
    ) -> ClarificationResult:
        """Scrub nested JSON state and previous questions before clarification.

        Args:
            structured_state: JSON-compatible dictionary; serialize models with
                model_dump(mode="json") before calling this method.
            already_asked: Previously asked questions, all strings.

        Returns:
            The provider's validated clarification result unchanged.

        Raises:
            AiValidationError: Invalid type, excessive size/depth or key collision;
                the provider is not called and caller-owned data is unchanged.
            AiError: Provider failures propagate without raw-input retry.
        """
        try:
            if not isinstance(structured_state, dict) or not isinstance(
                already_asked, list
            ):
                raise ValueError(_INVALID_INPUT)
            if not all(isinstance(item, str) for item in already_asked):
                raise ValueError(_INVALID_INPUT)
            budget = _Budget()
            clean_state = _scrub_value(structured_state, self._known_names, budget)
            clean_questions = _scrub_value(already_asked, self._known_names, budget)
        except ValueError:
            raise AiValidationError(_INVALID_INPUT) from None
        return await self._provider.generate_clarification(clean_state, clean_questions)
