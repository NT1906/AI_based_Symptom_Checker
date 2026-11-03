"""AI service package: symptom understanding engine and gateway interface.

Owner: Nishith · Task: S1-NIT-2 · Requirements: FR-04, FR-19, FR-20
"""

from app.services.ai.factory import get_ai_gateway
from app.services.ai.gateway import (
    AiError,
    AiGateway,
    AiTimeoutError,
    AiValidationError,
)
from app.services.ai.missing_info import (
    detect_missing_information,
    should_request_clarification,
)
from app.services.ai.mock_provider import MockAiProvider
from app.services.ai.schemas import (
    ClarificationResult,
    Duration,
    DurationUnitEnum,
    ExtractedSymptom,
    ExtractionResult,
    MissingFieldEnum,
    MissingInfoItem,
    QuestionTypeEnum,
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
    "MissingFieldEnum",
    "MissingInfoItem",
    "MockAiProvider",
    "QuestionTypeEnum",
    "SeverityEnum",
    "detect_missing_information",
    "get_ai_gateway",
    "should_request_clarification",
]
