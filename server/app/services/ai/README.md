# AI Service Module

**Owner:** Nishith (AI/ML Lead) · **Task:** S1-NIT-2 · **Requirements:** FR-03, FR-04, FR-17, FR-19, FR-20, NFR-05

The AI service manages natural-language symptom extraction, missing-information detection, and targeted clarification question generation. It serves as the single gateway for LLM interactions across the system.

## Architectural Boundaries

- **Single Gateway Policy:** The `AiGateway` protocol is the only entry point for LLM interactions. API routes and orchestrators must never call LLMs directly.
- **Dependency Inversion:** Consumers import and depend on the abstract `AiGateway` protocol and Pydantic schemas, not concrete provider implementations.
- **Missing-Information Detection:** `missing_info.py` evaluates clinical attributes (duration, severity, anatomical location, and acute onset) in strict clinical priority order (safety-critical red flags first).
- **Hard Turn Cap (FR-20):** Follow-up questions are strictly capped at a maximum of 3 turns to prevent conversational interrogation. Once 3 questions have been asked or all critical gaps are filled, clarification terminates (`should_ask=False`).
- **Mock Provider for Dev/CI:** The `MockAiProvider` operates whenever `AI_PROVIDER=mock`, returning deterministic fixture extractions without requiring an OpenAI API key.

## Public Interface

```python
from app.services.ai import (
    AiGateway,
    AiError,
    AiTimeoutError,
    AiValidationError,
    ClarificationResult,
    ExtractionResult,
    MockAiProvider,
    detect_missing_information,
    get_ai_gateway,
    should_request_clarification,
)

# Instantiate the configured gateway
gateway: AiGateway = get_ai_gateway()

# Extract symptoms from user message
result: ExtractionResult = await gateway.extract_symptoms(
    message="I have had a severe headache since yesterday",
    conversation_history="",
)

# Detect missing clinical information
gaps = detect_missing_information(result.symptoms)

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
