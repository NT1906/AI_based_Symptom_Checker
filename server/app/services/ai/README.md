# AI Service Module

**Owner:** Nishith (AI/ML Lead) · **Task:** S0-NIT-1 · **Requirements:** NFR-05

The AI service manages natural-language symptom extraction and targeted clarification. It serves as the single gateway for LLM interactions across the system.

## Architectural Boundaries

- **Single Gateway Policy:** The `AiGateway` protocol is the only entry point for LLM interactions. API routes and orchestrators must never call LLMs directly.
- **Dependency Inversion:** Consumers import and depend on the abstract `AiGateway` protocol and Pydantic schemas, not concrete provider implementations.
- **Mock Provider for Dev/CI:** The `MockAiProvider` operates whenever `AI_PROVIDER=mock`, returning deterministic fixture extractions without requiring an OpenAI API key.

## Public Interface
 
```python
from app.services.ai import (
    AiGateway,
    AiError,
    AiTimeoutError,
    AiValidationError,
    MockAiProvider,
    get_ai_gateway,
    ExtractionResult,
    ClarificationResult,
)

# Instantiate the configured gateway
gateway: AiGateway = get_ai_gateway()

# Extract symptoms from user message
result: ExtractionResult = await gateway.extract_symptoms(
    message="I have had a severe headache since yesterday",
    conversation_history="",
)

# Generate targeted follow-up question
clarification: ClarificationResult = await gateway.generate_clarification(
    structured_state={"symptoms": [{"name": "headache"}]},
    already_asked=[],
)
```

## Running Unit Tests

From `server/`:

```powershell
py -3.11 -m pytest tests/unit/ai -v
```
