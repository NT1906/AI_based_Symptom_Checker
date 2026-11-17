"""Deterministic intent classifier for symptom triage conversation safety.

Responsibilities:
    - Detect prompt-injection attempts and adversarial override instructions.
    - Intercept and politely decline off-topic requests (code, jokes, weather).
    - Detect symptom explanation questions ("what is nausea?") and resolve them
      strictly via the curated symptom glossary, never through free LLM text (FR-18).
    - Pass valid symptom descriptions through to the symptom extraction pipeline.

Owner: Nishith · Task: S2-NIT-2 · Requirements: idea "out of scope", FR-18
"""

import base64
import binascii
import re
from typing import Any

from app.core.logging import get_logger
from app.services.ai.schemas import (
    GlossaryResponse,
    IntentEnum,
    IntentResult,
)
from app.services.knowledge.glossary import get_glossary, lookup_glossary

logger = get_logger(__name__)

# Mandatory safe refusal strings per medical safety and idea § out-of-scope
PROMPT_INJECTION_REFUSAL = (
    "I can only help with health-related symptom questions. "
    "Could you describe what symptoms you're experiencing?"
)

OFF_TOPIC_REFUSAL = (
    "I'm designed to help you understand your health symptoms. "
    "Could you describe what you're feeling so I can assist you?"
)

UNKNOWN_TERM_REFUSAL = (
    "I don't have information about that specific term in the symptom glossary. "
    "Could you describe what symptoms you are experiencing so I can assist you?"
)

# Prompt-injection regex patterns targeting instruction overrides and jailbreaks
_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:ignore|disregard|forget|override)\s+"
        r"(?:all\s+)?(?:previous|prior|above|system)?\s*"
        r"(?:instructions|prompts|rules|commands|constraints|directives)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:you are now|act as|pretend to be|roleplay as)\s+"
        r"(?:an?\s+)?(?:unrestricted|unfiltered|jailbroken|evil|dan|"
        r"developer mode|assistant without rules)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:dan mode|jailbreak|developer mode enabled|"
        r"unrestricted mode|bypass filters)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:reveal|show|display|print|output|repeat|dump)\s+"
        r"(?:your\s+)?(?:system prompt|initial prompt|hidden instructions|"
        r"raw instructions|base instructions)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:system prompt:|system instructions:|new instruction:|assistant prompt:)",
        re.IGNORECASE,
    ),
)

# Off-topic patterns for common non-health requests
_OFF_TOPIC_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:joke|jokes|funny story|riddle|riddles|poem|poems|"
        r"song|songs|rap|essay|fiction)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:write|generate|debug|create|fix)\s+(?:a\s+|an\s+|this\s+|my\s+|the\s+)?"
        r"(?:python|javascript|code|script|sql|html|css|function|program|app|algorithm)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:solve|calculate|compute)\s+(?:a\s+|an\s+|this\s+|my\s+|the\s+)?"
        r"(?:math|equation|integral|derivative|algebra|homework)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:weather|weather forecast|recipe for|how to cook|bake a cake)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:who won the (?:match|game|world cup|ipl|election)|"
        r"current stock price|crypto price)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:help (?:me )?with (?:my )?homework|write my essay|do my assignment)\b",
        re.IGNORECASE,
    ),
)

# Glossary question patterns detecting "what is X?", "tell me about X", etc.
_GLOSSARY_QUESTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"^(?:can you\s+)?what does\s+(.+?)\s+mean[\?\.\!\s]*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:can you\s+)?(?:what(?:'s| is| are)|tell me about|explain|define|"
        r"meaning of)\s+(.+?)[\?\.\!\s]*$",
        re.IGNORECASE,
    ),
)


def _check_obfuscated_injection(text: str) -> bool:
    """Detect base64-encoded or hex-encoded prompt-injection payloads.

    Args:
        text: Raw user message string.

    Returns:
        True if the text contains a decoded adversarial pattern, False otherwise.
    """
    matches = re.findall(r"[A-Za-z0-9+/]{20,}={0,2}", text)
    for seq in matches:
        padded = seq + "=" * (-len(seq) % 4)
        try:
            decoded = base64.b64decode(padded).decode("utf-8", errors="ignore").lower()
            if any(
                kw in decoded
                for kw in (
                    "ignore",
                    "system",
                    "prompt",
                    "instruction",
                    "jailbreak",
                    "dan mode",
                )
            ):
                return True
        except (binascii.Error, UnicodeDecodeError):
            continue
    return False


def _clean_glossary_term(raw_term: str) -> str:
    """Normalize extracted term by stripping articles and extraneous punctuation.

    Args:
        raw_term: Extracted phrase from regex match group.

    Returns:
        Cleaned candidate symptom phrase.
    """
    lowered = raw_term.strip().lower()
    cleaned = re.sub(r"^(?:a|an|the|about)\s+", "", lowered).strip()
    return re.sub(r"[^\w\s-]", "", cleaned).strip()


class IntentClassifier:
    """Deterministic, rule-based intent classifier for symptom assessment chat.

    Guarantees that:
        - Adversarial prompt injections are stopped before reaching the LLM.
        - Off-topic conversations receive polite, fixed refusal messages.
        - Symptom definitions are resolved strictly from the curated glossary
          and never hallucinated or generated by the LLM (FR-18).
    """

    def is_prompt_injection(self, text: str) -> bool:
        """Check whether input text exhibits prompt-injection characteristics.

        Args:
            text: Raw input text from the user.

        Returns:
            True if prompt injection is detected, False otherwise.
        """
        if not text:
            return False

        for pattern in _INJECTION_PATTERNS:
            if pattern.search(text):
                return True

        return _check_obfuscated_injection(text)

    def is_off_topic(self, text: str) -> bool:
        """Check whether input text is a non-health, off-topic request.

        Args:
            text: Raw input text from the user.

        Returns:
            True if off-topic content is detected, False otherwise.
        """
        if not text:
            return False

        for pattern in _OFF_TOPIC_PATTERNS:
            if pattern.search(text):
                return True

        return False

    def check_glossary_query(self, text: str) -> tuple[bool, str | None, Any | None]:
        """Detect and resolve a symptom definition query.

        Args:
            text: Raw user message.

        Returns:
            Tuple of (is_glossary_query, cleaned_term_or_none, glossary_entry_or_none).
        """
        cleaned = text.strip()
        matched_term: str | None = None
        for pattern in _GLOSSARY_QUESTION_PATTERNS:
            match = pattern.match(cleaned)
            if match:
                matched_term = match.group(1)
                break

        if not matched_term:
            return False, None, None

        candidate = _clean_glossary_term(matched_term)
        if not candidate:
            return False, None, None

        entry = lookup_glossary(candidate)
        return True, candidate, entry

    def classify(self, message: str) -> IntentResult:
        """Deterministically classify a user message into an IntentResult.

        Evaluation order:
            1. Prompt injection check (highest priority safety guard).
            2. Off-topic query check (catches weather, jokes, homework, coding).
            3. Glossary inquiry check ("what is nausea?").
            4. Default to standard symptom reporting.

        Args:
            message: Raw user message string.

        Returns:
            Validated IntentResult with classification and any curated content.
        """
        cleaned = message.strip()
        if not cleaned:
            return IntentResult(
                intent=IntentEnum.SYMPTOM_REPORT,
                confidence=1.0,
            )

        # 1. Prompt-injection guard
        if self.is_prompt_injection(cleaned):
            logger.warning(
                "intent_prompt_injection_detected",
                message_length=len(cleaned),
            )
            return IntentResult(
                intent=IntentEnum.PROMPT_INJECTION,
                refusal_message=PROMPT_INJECTION_REFUSAL,
                confidence=1.0,
            )

        # 2. Off-topic filter
        if self.is_off_topic(cleaned):
            logger.info("intent_off_topic_detected")
            return IntentResult(
                intent=IntentEnum.OFF_TOPIC,
                refusal_message=OFF_TOPIC_REFUSAL,
                confidence=1.0,
            )

        # 3. Glossary lookup ("what is X?")
        is_glossary, term, entry = self.check_glossary_query(cleaned)
        if is_glossary and term:
            if entry is not None:
                # Symptom found in curated glossary (FR-18)
                disclaimer = get_glossary().disclaimer
                glossary_resp = GlossaryResponse(
                    symptom_name=entry.name,
                    definition=entry.plain_definition,
                    when_to_seek_care=entry.when_to_seek_care,
                    disclaimer=disclaimer,
                )
                logger.info("intent_glossary_query_resolved", symptom=entry.name)
                return IntentResult(
                    intent=IntentEnum.GLOSSARY_QUERY,
                    glossary_query=term,
                    glossary_response=glossary_resp,
                    confidence=1.0,
                )
            # Term not found in glossary; check if completely off-topic or unknown
            off_topic_prefixes = ("code", "python", "java", "math", "quantum")
            if self.is_off_topic(term) or any(
                term.startswith(prefix) for prefix in off_topic_prefixes
            ):
                return IntentResult(
                    intent=IntentEnum.OFF_TOPIC,
                    refusal_message=OFF_TOPIC_REFUSAL,
                    confidence=1.0,
                )
            # Unknown symptom or non-indexed term
            return IntentResult(
                intent=IntentEnum.GLOSSARY_QUERY,
                glossary_query=term,
                refusal_message=UNKNOWN_TERM_REFUSAL,
                confidence=1.0,
            )

        # 4. Standard symptom report
        return IntentResult(
            intent=IntentEnum.SYMPTOM_REPORT,
            confidence=1.0,
        )
