"""AI service package: symptom understanding engine and gateway interface.

Owner: Nishith · Tasks: S1-NIT-3, S2-NIT-2, S2-NIT-5
Requirements: FR-04, FR-18, FR-19, FR-20, NFR-01, NFR-05, NFR-08, idea "out of scope"
"""

from app.services.ai.factory import get_ai_gateway
from app.services.ai.fallback_gateway import FallbackAiGateway
from app.services.ai.gateway import (
    AiError,
    AiGateway,
    AiTimeoutError,
    AiValidationError,
)
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.intent import IntentClassifier
from app.services.ai.latency_budget import (
    DEFAULT_LATENCY_BUDGET_SECONDS,
    MIN_ATTEMPT_TIMEOUT_SECONDS,
    LatencyBudget,
    resolve_latency_budget_seconds,
)
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
    "DEFAULT_LATENCY_BUDGET_SECONDS",
    "MIN_ATTEMPT_TIMEOUT_SECONDS",
    "AiError",
    "AiGateway",
    "AiTimeoutError",
    "AiValidationError",
    "ClarificationResult",
    "Duration",
    "DurationUnitEnum",
    "ExtractedSymptom",
    "ExtractionResult",
    "FallbackAiGateway",
    "GeminiProvider",
    "GlossaryResponse",
    "IntentClassifier",
    "IntentEnum",
    "IntentResult",
    "LatencyBudget",
    "MissingFieldEnum",
    "MissingInfoItem",
    "MockAiProvider",
    "OpenAiProvider",
    "QuestionTypeEnum",
    "SeverityEnum",
    "detect_missing_information",
    "get_ai_gateway",
    "resolve_latency_budget_seconds",
    "should_request_clarification",
]
