# AI Gateway, Failover, Latency Budget & Prompt Tests

**Owner:** Nishith · **Tasks:** S1-NIT-3, S2-NIT-1, S2-NIT-2, S2-NIT-5 · **Requirements:** FR-04, FR-18, FR-19, FR-20, NFR-01, NFR-05, NFR-08

This suite validates the `AiGateway` protocol, `MockAiProvider`, `OpenAiProvider`, `GeminiProvider`, `FallbackAiGateway`, `LatencyBudget`, deterministic intent handling, missing-information detection, clarification generation, and versioned prompt files. All tests run completely offline with hermetic mocking (never calling real OpenAI or Gemini endpoints).

## Coverage Areas

* **`test_openai_provider.py`**: Validates `OpenAiProvider` conformance to `AiGateway`, Structured Outputs parsing, 2 automatic retries on transient errors (`429`, `5xx`, connection failure), timeout handling, fail-fast terminal errors (`401`, `400`), defensive clarification triggers, and 3-turn clarification ceiling.
* **`test_gemini_provider.py`**: Validates `GeminiProvider` conformance to `AiGateway`, `httpx.MockTransport` REST requests (`x-goog-api-key` header only, never query string), JSON schema validation, markdown fence stripping, safety/truncation blocks, transient retries (`429`, `5xx`, timeout, transport errors), fail-fast `4xx`, and latency-budget clamping.
* **`test_fallback_and_latency.py`**: Validates `LatencyBudget` monotonic deadline math and backoff clamping, plus `FallbackAiGateway` primary-to-Gemini failover on errors/timeouts, primary slice cancellation, budget exhaustion before fallback, dual-provider failure metadata, and deterministic `classify_intent`.
* **`test_intent.py`**: Validates prompt-injection defence, off-topic chat refusal, curated glossary lookups (`FR-18`), and gateway integration.
* **`test_prompt_v2.py`**: Validates multi-turn context resolution, standalone reply attribution, Hinglish/misspelling mappings, and `extraction.v2.txt`.
* **`test_missing_info.py`**: Validates deterministic detection of missing duration, unknown severity, absent anatomical body site, and missing onset for safety-critical symptoms with clinical triage priority ordering.
* **`test_clarification.py`**: Enforces the strict 3-question maximum turn cap (`FR-20`), question deduplication (`already_asked`), safe non-diagnostic medical phrasing, and question type classification.
* **`test_mock_provider.py`**: Validates extraction heuristics, duration parsing, body site mapping, negation exclusions, and testing hooks.
* **`test_gateway.py`**: Validates `AiGateway` protocol interface, factory resolution (`mock`, `openai`, `gemini`, and `openai` + `gemini` failover) wrapped in `PrivacyAiGateway`, and versioned prompt invariants.

## Running Tests

From `server/`:

```powershell
pytest tests/unit/ai -v
```
