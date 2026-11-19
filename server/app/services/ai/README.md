# AI Service Module

**Owner:** Nishith (AI/ML Lead) · **Tasks:** S1-NIT-3, S2-NIT-1, S2-NIT-2, S2-NIT-5 · **Requirements:** FR-03, FR-04, FR-17, FR-18, FR-19, FR-20, NFR-01, NFR-05, NFR-08
**Full AI Documentation (prompts, latency budget, limitations, failure modes):** [`docs/ai.md`](../../../../docs/ai.md)

The AI service manages natural-language symptom extraction, deterministic intent classification, missing-information detection, and targeted clarification question generation. It serves as the single gateway for LLM interactions across the system.

## Architectural Boundaries

- **Single Gateway Policy:** The `AiGateway` protocol is the only entry point for LLM interactions. API routes and orchestrators must never call LLMs directly.
- **Dependency Inversion:** Consumers import and depend on the abstract `AiGateway` protocol and Pydantic schemas, not concrete provider implementations.
- **Primary OpenAI Provider (`OpenAiProvider`):** Implements `AiGateway` using `AsyncOpenAI` and native Structured Outputs (`beta.chat.completions.parse`) with Pydantic schemas (`ExtractionResult`, `ClarificationResult`).
- **Groq Provider (`GroqProvider`, S2-NIS-14 #308):** Subclass of `OpenAiProvider` that points `AsyncOpenAI` at Groq's OpenAI-compatible endpoint (`https://api.groq.com/openai/v1`). Selected with `AI_PROVIDER=groq` plus `GROQ_API_KEY`; the model comes from `GROQ_MODEL` (default `openai/gpt-oss-120b`), which must support Groq's strict JSON-schema structured outputs.
- **Gemini Fallback Provider (`GeminiProvider`):** Implements `AiGateway` over Google's Gemini REST `generateContent` endpoint using lightweight `httpx.AsyncClient` (`x-goog-api-key` header, `responseMimeType: application/json`, strict Pydantic validation).
- **Automatic Failover (`FallbackAiGateway`):** When `AI_PROVIDER` is `openai` or `groq` and `GEMINI_API_KEY` is configured, `factory.py` automatically composes `FallbackAiGateway(primary=OpenAiProvider | GroqProvider, fallback=GeminiProvider)` inside `PrivacyAiGateway`.
- **End-to-End Latency Budget (`LatencyBudget`, NFR-01 / NFR-05):** Enforces a monotonic wall-clock ceiling (default `4.5s` via `AI_LATENCY_BUDGET_SECONDS`) across retries and failover (`60%` primary slice, remaining time for Gemini fallback, backoff clamping) to stay within the `5.0s` p95 response budget.
- **Typed Error Hierarchy:** All upstream failures map to typed `AiError` subclasses (`AiTimeoutError`, `AiValidationError`, `AiError`).
- **Outbound PII Scrubbing:** All provider instances returned by `factory.py` are wrapped inside `PrivacyAiGateway` (`S1-HAR-2`), ensuring outbound prompts are scrubbed once before either provider is called.
- **Deterministic Intent Gate (`intent.py`):** Blocks prompt-injection attempts, refuses off-topic chat, and answers curated glossary lookups (`FR-18`) offline before any LLM call.
- **Missing-Information Detection & Hard Turn Cap (`FR-20`):** `missing_info.py` ranks clinical gaps (safety-critical red flags first), and clarification stops strictly at 3 turns (`should_ask=False`).
- **Mock Provider for Dev/CI:** `MockAiProvider` operates whenever `AI_PROVIDER=mock`, returning deterministic fixture extractions without requiring API keys.

## Public Interface

```python
from app.services.ai import (
    DEFAULT_LATENCY_BUDGET_SECONDS,
    AiError,
    AiGateway,
    AiTimeoutError,
    AiValidationError,
    ClarificationResult,
    ExtractionResult,
    FallbackAiGateway,
    GeminiProvider,
    LatencyBudget,
    MockAiProvider,
    OpenAiProvider,
    detect_missing_information,
    get_ai_gateway,
    should_request_clarification,
)

# Instantiate the configured gateway (wrapped in PrivacyAiGateway)
gateway: AiGateway = get_ai_gateway()

# Classify intent deterministically before extraction
intent = await gateway.classify_intent("I have had a severe headache since yesterday")

# Extract symptoms from user message (with automatic Gemini failover if configured)
result: ExtractionResult = await gateway.extract_symptoms(
    message="I have had a severe headache since yesterday",
    conversation_history="",
)

# Generate targeted follow-up question (max 3 turns)
clarification: ClarificationResult = await gateway.generate_clarification(
    structured_state={"symptoms": [s.model_dump() for s in result.symptoms]},
    already_asked=[],
)
```

## Running Unit Tests

From `server/`:

```powershell
pytest tests/unit/ai -v
```
