"""AI Gateway protocol and exception definitions.

Responsibilities:
 - Define the abstract AiGateway protocol for dependency injection.
 - Define typed error hierarchy (AiError, AiTimeoutError, AiValidationError).

Owner: Nishith · Task: S0-NIT-1 · Requirements: NFR-05
"""

from typing import Any, Protocol, runtime_checkable

from app.services.ai.schemas import ClarificationResult, ExtractionResult


class AiError(Exception):
    """Base exception for all AI gateway and provider failures."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AiTimeoutError(AiError):
    """Raised when an AI provider call exceeds its configured timeout budget."""


class AiValidationError(AiError):
    """Raised when an AI provider returns an output that violates schema constraints."""


@runtime_checkable
class AiGateway(Protocol):
    """Abstract protocol for symptom understanding and clarification providers.

    All AI providers (OpenAI, Gemini, Mock) implement this interface.
    Callers must interact solely through this protocol to maintain dependency inversion.
    """

    async def extract_symptoms(
        self,
        message: str,
        conversation_history: str = "",
    ) -> ExtractionResult:
        """Extract structured symptoms and clinical attributes from natural language.

        Args:
            message: Current user message containing symptom descriptions.
            conversation_history: Previous conversational turns for context resolution.

        Returns:
            Structured ExtractionResult with validated symptoms and clarification status.

        Raises:
            AiTimeoutError: If the provider call times out.
            AiValidationError: If the response cannot be parsed into valid schemas.
            AiError: For unhandled provider failures or network drops.
        """
        ...

    async def generate_clarification(
        self,
        structured_state: dict[str, Any],
        already_asked: list[str],
    ) -> ClarificationResult:
        """Generate a targeted, non-diagnostic clarifying question when info is missing.

        Args:
            structured_state: Currently confirmed or extracted symptom state dictionary.
            already_asked: List of previously asked questions to prevent repetition.

        Returns:
            ClarificationResult indicating whether to ask and containing the question text.

        Raises:
            AiTimeoutError: If the provider call times out.
            AiError: For unhandled provider failures.
        """
        ...
