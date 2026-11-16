"""AI service package: symptom understanding engine and gateway interface.

Owner: Nishith · Tasks: S1-NIT-3, S2-NIT-2
Requirements: FR-04, FR-18, FR-19, FR-20, NFR-05, idea "out of scope"
"""

from app.services.ai.factory import get_ai_gateway
from app.services.ai.gateway import (
    AiError,
    AiGateway,
    AiTimeoutError,
    AiValidationError,
)
from app.services.ai.intent import IntentClassifier
from app.services.ai.missing_info import (
    detect_missing_information,
    should_request_clarification,
)
from app.services.ai.mock_provider import MockAiProvider
from app.services.ai.openai_provider import OpenAiProvider
from app.services.ai.schemas import (
    ClarificationResult,
    Duration,
    DurationUnitEnum,
    ExtractedSymptom,
    ExtractionResult,
    GlossaryResponse,
    IntentEnum,
    IntentResult,
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
    "GlossaryResponse",
    "IntentClassifier",
    "IntentEnum",
    "IntentResult",
    "MissingFieldEnum",
    "MissingInfoItem",
    "MockAiProvider",
    "OpenAiProvider",
    "QuestionTypeEnum",
    "SeverityEnum",
    "detect_missing_information",
    "get_ai_gateway",
    "should_request_clarification",
]
