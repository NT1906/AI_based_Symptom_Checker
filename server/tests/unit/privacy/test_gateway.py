"""Outbound privacy boundary tests using a recording fake AI provider.

Owner: Harsh · Task: S1-HAR-2 · Requirements: NFR-04, DR-06
"""

from copy import deepcopy
from typing import Any

import pytest

from app.services.ai.gateway import AiGateway, AiTimeoutError, AiValidationError
from app.services.ai.schemas import ClarificationResult, ExtractionResult
from app.services.privacy.gateway import PrivacyAiGateway


# Any matches the shared gateway payload contract, including intentional invalid
# values in tests of the runtime validation boundary.
class RecordingProvider:
    """Capture actual provider inputs without using network services."""

    def __init__(self) -> None:
        self.calls: list[object] = []
        self.extraction = ExtractionResult()
        self.clarification = ClarificationResult(should_ask=False)
        self.failure: AiTimeoutError | None = None

    async def extract_symptoms(
        self, message: str, conversation_history: str = ""
    ) -> ExtractionResult:
        """Record inputs and optionally raise a provider failure."""
        self.calls.append((message, conversation_history))
        if self.failure:
            raise self.failure
        return self.extraction

    async def generate_clarification(
        self, structured_state: dict[str, Any], already_asked: list[str]
    ) -> ClarificationResult:
        """Record clarification inputs without modifying them."""
        self.calls.append((structured_state, already_asked))
        if self.failure:
            raise self.failure
        return self.clarification


async def test_message_and_history_are_scrubbed_before_provider() -> None:
    """Neither extraction input bypasses the boundary."""
    provider = RecordingProvider()
    gateway: AiGateway = PrivacyAiGateway(provider)
    result = await gateway.extract_symptoms(
        "Name: Sample Person. Fever 38.5 C for 2 days.",
        "Contact demo@example.invalid or 202-555-0147.",
    )
    assert result is provider.extraction
    assert provider.calls == [
        (
            "Name: [NAME]. Fever 38.5 C for 2 days.",
            "Contact [EMAIL] or [PHONE].",
        )
    ]


async def test_nested_state_questions_and_keys_are_copied_and_scrubbed() -> None:
    """Nested strings and dictionary keys cannot skip redaction."""
    provider = RecordingProvider()
    gateway = PrivacyAiGateway(provider, known_names=("Sample Person",))
    state = {
        "symptoms": [{"name": "fever", "duration": 2, "temperature": 38.5}],
        "note": "Sample Person feels ill",
        "demo@example.invalid": None,
        "confirmed": True,
    }
    questions = ["Sample Person, since when?", "Phone 202-555-0147?"]
    original = deepcopy(state)
    result = await gateway.generate_clarification(state, questions)
    assert result is provider.clarification
    sent_state, sent_questions = provider.calls[0]
    assert sent_state == {
        "symptoms": [{"name": "fever", "duration": 2, "temperature": 38.5}],
        "note": "[NAME] feels ill",
        "[EMAIL]": None,
        "confirmed": True,
    }
    assert sent_questions == ["[NAME], since when?", "Phone [PHONE]?"]
    assert state == original
    assert questions == ["Sample Person, since when?", "Phone 202-555-0147?"]
    assert sent_state is not state
    assert sent_state["symptoms"] is not state["symptoms"]


@pytest.mark.parametrize(
    ("message", "history"),
    [
        (None, ""),
        ("Fever", None),
        ("x" * 20_001, ""),
        ("Fever", "x" * 20_001),
    ],
)
async def test_bad_extraction_input_never_reaches_provider(
    message: Any, history: Any
) -> None:
    """Validation failure must not fall back to sending raw text."""
    provider = RecordingProvider()
    with pytest.raises(
        AiValidationError, match="^AI privacy input validation failed.$"
    ):
        await PrivacyAiGateway(provider).extract_symptoms(message, history)
    assert not provider.calls


@pytest.mark.parametrize(
    "state",
    [
        {"note": b"private"},
        {"note": object()},
        {"reading": float("nan")},
        {"reading": float("inf")},
        {123: "Fever"},
        {"items": ("private",)},
        {"a@example.invalid": "one", "b@example.invalid": "two"},
        {"items": [None] * 2_049},
        {"items": ["x" * 20_000] * 3},
    ],
)
async def test_invalid_nested_values_fail_closed(state: Any) -> None:
    """Unsupported types, collisions and excessive payloads block the call."""
    provider = RecordingProvider()
    with pytest.raises(AiValidationError) as error:
        await PrivacyAiGateway(provider).generate_clarification(state, [])
    assert str(error.value) == "AI privacy input validation failed."
    assert not provider.calls


@pytest.mark.parametrize("questions", [None, "question", [None], [123]])
async def test_invalid_question_container_is_rejected(questions: Any) -> None:
    """Questions must be a list of strings, not arbitrary nested values."""
    provider = RecordingProvider()
    with pytest.raises(AiValidationError):
        await PrivacyAiGateway(provider).generate_clarification({}, questions)
    assert not provider.calls


async def test_cyclic_payload_is_rejected_by_depth_budget() -> None:
    """A caller-created cycle cannot cause unbounded recursion."""
    state: dict[str, Any] = {}
    state["self"] = state
    provider = RecordingProvider()
    with pytest.raises(AiValidationError):
        await PrivacyAiGateway(provider).generate_clarification(state, [])
    assert not provider.calls


async def test_budget_is_shared_with_questions_and_resets_between_calls() -> None:
    """Each call is bounded independently, with no cross-request text state."""
    provider = RecordingProvider()
    gateway = PrivacyAiGateway(provider)
    with pytest.raises(AiValidationError):
        await gateway.generate_clarification({"note": "x" * 20_000}, ["y" * 20_000])
    assert not provider.calls
    await gateway.generate_clarification({}, [])
    await gateway.extract_symptoms("Fever")
    assert len(provider.calls) == 2


@pytest.mark.parametrize("operation", ["extraction", "clarification"])
async def test_provider_errors_propagate_without_retry(operation: str) -> None:
    """A provider failure is not hidden or retried with unredacted input."""
    provider = RecordingProvider()
    provider.failure = AiTimeoutError("Synthetic timeout")
    gateway = PrivacyAiGateway(provider)
    with pytest.raises(AiTimeoutError) as error:
        if operation == "extraction":
            await gateway.extract_symptoms("demo@example.invalid")
        else:
            await gateway.generate_clarification({"note": "demo@example.invalid"}, [])
    assert error.value is provider.failure
    assert len(provider.calls) == 1
    assert "demo@example.invalid" not in repr(provider.calls)


def test_invalid_names_are_rejected_without_leaking_values() -> None:
    """Validate configuration before retaining it or calling the provider."""
    with pytest.raises(
        AiValidationError, match="^AI privacy input validation failed.$"
    ):
        PrivacyAiGateway(RecordingProvider(), known_names=("x",))
