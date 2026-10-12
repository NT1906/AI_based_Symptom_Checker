"""Domain enums representing assessment states, risk tiers, and symptom classifications.

Responsibilities:
    - Define canonical AssessmentState lifecycle states.
    - Define triage RiskLevel categories compliant with deterministic safety rules.
    - Define ConfidenceLabel buckets (Likely, Possible, Less likely) for non-diagnostic display.
    - Define symptom severity, duration units, and message categorization.

Owner: Darshil (orchestration) · Task: S0-DAR-1 · Requirements: N/A
"""

from enum import Enum


class AssessmentState(str, Enum):
    """Lifecycle states of an assessment session.

    Flow: START -> SYMPTOM_COLLECTION -> CLARIFYING -> CONFIRMING -> READY -> ANALYZING -> COMPLETED
    """

    START = "START"
    SYMPTOM_COLLECTION = "SYMPTOM_COLLECTION"
    CLARIFYING = "CLARIFYING"
    CONFIRMING = "CONFIRMING"
    READY = "READY"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class RiskLevel(str, Enum):
    """Deterministic triage risk tiers.

    URGENT takes precedence on any red-flag symptom.
    """

    SELF_CARE = "SELF_CARE"
    CONSULT_DOCTOR = "CONSULT_DOCTOR"
    URGENT = "URGENT"
    URGENT_EMERGENCY = "URGENT_EMERGENCY"


class ConfidenceLabel(str, Enum):
    """Categorical confidence labels presented to users.

    Raw statistical scores are never exposed directly to users (AI_RULES.md §2).
    """

    LIKELY = "LIKELY"
    POSSIBLE = "POSSIBLE"
    LESS_LIKELY = "LESS_LIKELY"


class Severity(str, Enum):
    """Clinical severity levels reported or inferred for a symptom."""

    MILD = "MILD"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"
    UNKNOWN = "UNKNOWN"


class DurationUnit(str, Enum):
    """Time units for symptom duration tracking."""

    HOUR = "HOUR"
    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"
    YEAR = "YEAR"


class SymptomSource(str, Enum):
    """Origin of the symptom record."""

    USER = "USER"
    AI_EXTRACTED = "AI_EXTRACTED"
    USER_CONFIRMED = "USER_CONFIRMED"
    USER_CORRECTED = "USER_CORRECTED"


class MessageRole(str, Enum):
    """Sender roles in assessment conversational exchange."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageType(str, Enum):
    """Categorization of message intent in the assessment flow."""

    TEXT = "TEXT"
    CLARIFICATION = "CLARIFICATION"
    CONFIRMATION = "CONFIRMATION"
    RESULT = "RESULT"
    ERROR = "ERROR"
