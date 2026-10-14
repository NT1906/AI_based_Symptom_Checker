"""AI service package: symptom understanding engine and gateway interface.

Owner: Nishith · Task: S0-NIT-1 · Requirements: NFR-05
"""

from app.services.ai.factory import get_ai_gateway
from app.services.ai.gateway import (
    AiError,
    AiGateway,
    AiTimeoutError,
    AiValidationError,
)
from app.services.ai.mock_provider import MockAiProvider
from app.services.ai.schemas import (
    ClarificationResult,
    Duration,
    DurationUnitEnum,
    ExtractedSymptom,
    ExtractionResult,
    SeverityEnum,
)

__all__ = [
    "AiError",
    "AiGateway",
    "AiTimeoutError",
    "AiValidationError",
    "ClarificationResult",
    "Duration",
    "DurationUnitEnum",
    "ExtractedSymptom",
    "ExtractionResult",
    "MockAiProvider",
    "SeverityEnum",
    "get_ai_gateway",
]
