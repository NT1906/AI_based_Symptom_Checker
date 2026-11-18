# AI Symptom Understanding Engine (S2-NIT-5)

**Owner:** Nishith (`@Nishith1130`) · **Issue:** #196 · **Requirements:** NFR-05, NFR-08, NFR-01, FR-03, FR-04, FR-17, FR-18, FR-19, FR-20
**Code:** [`server/app/services/ai/`](../server/app/services/ai/README.md) · **Prompts:** [`server/app/services/ai/prompts/`](../server/app/services/ai/prompts/README.md) · **Tests:** [`server/tests/unit/ai/`](../server/tests/unit/ai/README.md)

---

## 1. Architecture & Safety Boundaries

The AI service is strictly a **natural-language symptom understanding and clarification layer**. It converts free-text patient messages into typed Pydantic payloads (`ExtractionResult`, `ClarificationResult`, `IntentResult`) and never computes risk levels, predicts diagnoses, or recommends medications.

```text
User text (PII scrubbed once)
        │
        ▼
PrivacyAiGateway (S1-HAR-2 — outbound PII redaction, bounded payload checks)
        │
        ▼
FallbackAiGateway (S2-NIT-5 — single 4.5s monotonic LatencyBudget)
  ├── Primary (60% slice, ~2.7s): OpenAiProvider (Structured Outputs + retries)
  └── Fallback (remaining slice, >= 0.5s): GeminiProvider (REST JSON mode + retries)
        │
        ▼
Pydantic strict validation (ExtractionResult / ClarificationResult)
        │
        ▼
Deterministic downstream pipeline (Normalizer → Vector Retrieval → Risk Engine)
```

### Non-Negotiable Invariants (`AI_RULES.md §2`)
1. **Single LLM Boundary:** `AiGateway` (`server/app/services/ai/`) is the only module in the repository allowed to invoke external LLM APIs.
2. **Outbound PII Scrubbing:** `factory.py` always wraps the outermost gateway in `PrivacyAiGateway` so PII is scrubbed **once** before either OpenAI or Gemini receives any text.
3. **Strict Schema Enforcement:** Every LLM payload is validated against frozen Pydantic v2 models (`ExtractionResult`, `ClarificationResult`) before returning to the orchestrator. Invalid or refused payloads raise `AiValidationError`.
4. **Deterministic Risk Separation (`DR-02`):** Neither OpenAI, Gemini, nor the monotonic `LatencyBudget` clock ever determines or lowers a risk tier. AI uncertainty or failure pushes downstream triage toward safe fallback/escalation, never toward reassurance.
5. **Zero PII or Secret Logging:** Structured logs record only non-sensitive metadata (`provider`, `model`, `action`, `attempt`, `elapsed_ms`, `symptom_count`, `error_type`). Gemini authenticates via the `x-goog-api-key` HTTP header (never query strings) so keys cannot leak into URL or proxy logs.
6. **Hard Clarification Ceiling (`FR-20`):** Both `OpenAiProvider` and `GeminiProvider` enforce `MAX_CLARIFICATION_TURNS = 3` and short-circuit immediately if no clinical gaps remain.

---

## 2. Versioned Prompt Catalog

Per `AI_RULES.md §3.1`, **prompts are immutable once merged to `develop`**. Any behavioral refinement creates a new numbered version (`<purpose>.v<N>.txt`).

| Prompt File | Active? | Task | Purpose & Key Safety Directives |
|---|---|---|---|
| `extraction.v1.txt` | Baseline (archived) | S1-NIT-1 | Single-turn extraction of symptom name, severity, duration, onset, and body site across respiratory, cardiovascular, GI, neurological, and dermatological systems. Explicitly forbids diagnosis or treatment advice. |
| `extraction.v2.txt` | **Active** | S2-NIT-1 | Multi-turn context resolution (`{conversation_history}` + `{user_message}`), standalone reply attribution to the previous clarification question, expanded misspelling/phonetic normalization, Hinglish/transliterated phrase coverage, and red-flag preservation. |
| `clarification.v1.txt` | Baseline (archived) | S0-NIT-1 | Baseline follow-up question generator enforcing the 3-turn ceiling. |
| `clarification.v2.txt` | **Active** | S1-NIT-2 | Takes `{structured_state_json}`, `{detected_missing_info_json}`, `{clarification_count}`, and `{previously_asked_questions}`. Asks one concise, non-diagnostic question targeting the highest-priority clinical gap (red-flag severity/onset first) and strictly stops at turn 3. |
| `intent_defence.v1.txt` | **Active** | S2-NIT-2 | System-level adversarial defence prepended to extraction prompts. Treats all user text as untrusted data, rejects role-override / jailbreak instructions, refuses off-topic requests, and reinforces non-diagnostic framing. |

### Deterministic Pre-LLM Intent Gate (`intent.py`)
Before calling any LLM, `classify_intent(message)` runs deterministically offline in sub-millisecond time to:
- Block prompt-injection patterns (`"ignore previous instructions"`, `"act as a doctor"`, system prompt exfiltration).
- Refuse off-topic non-health requests (coding, math, trivia, general chat) with a polite scope reminder.
- Answer curated medical terminology lookups (`"what is nausea?"`, `"what does dyspnea mean?"`) directly from Kavya's curated glossary (`FR-18`) without consuming LLM tokens or latency.

---

## 3. Provider Strategy & Failover

`get_ai_gateway()` in `server/app/services/ai/factory.py` selects and wires providers via environment variables:

| Environment Variable | Default | Purpose |
|---|---|---|
| `AI_PROVIDER` | `mock` | Active primary mode: `mock`, `openai`, or `gemini`. |
| `AI_MODEL` | `gpt-4o-mini` | Model name for `OpenAiProvider`. |
| `OPENAI_API_KEY` | *(unset)* | API key for OpenAI (required when `AI_PROVIDER=openai`). |
| `GEMINI_API_KEY` *(or `GOOGLE_API_KEY`)* | *(unset)* | API key for Gemini. Required when `AI_PROVIDER=gemini`; automatically activates `OpenAiProvider -> GeminiProvider` failover when `AI_PROVIDER=openai`. |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Model name for `GeminiProvider`. |
| `AI_FALLBACK_ENABLED` | `true` | Set to `false` to disable automatic Gemini failover when `AI_PROVIDER=openai`. |
| `AI_LATENCY_BUDGET_SECONDS` | `4.5` | End-to-end monotonic latency ceiling (seconds) across retries and failover. |

### Why Gemini Uses `httpx.AsyncClient` REST Instead of a Heavy SDK
- Calls Google's official `POST /v1beta/models/{model}:generateContent` endpoint with `generationConfig.responseMimeType = "application/json"` and `temperature = 0.0`.
- Avoids pulling in `grpcio` / `google-auth` (~100 MB), keeping the server Docker image and runtime memory safely below Render's 512 MB RAM ceiling.
- Supports 100% hermetic offline testing via `httpx.MockTransport` without external network calls.

### Provider Retry Policy
- **Retryable (up to 2 retries with budget-clamped exponential backoff):**
  - OpenAI: `RateLimitError` (429), `InternalServerError` (5xx), `APIConnectionError`, `APITimeoutError` / `TimeoutError`.
  - Gemini: HTTP `429`, `500`, `502`, `503`, `504`, `httpx.TimeoutException`, `httpx.TransportError`.
- **Fail-Fast (0 retries):**
  - Authentication/authorization/bad request errors (`400`, `401`, `403`, `404`) → immediate `AiError`.
  - Truncated output (`LengthFinishReasonError`, `finishReason=MAX_TOKENS`), model refusal / safety block (`SAFETY`, `RECITATION`, `PROHIBITED_CONTENT`), or Pydantic schema violation → immediate `AiValidationError`.

---

## 4. Latency Budget (`NFR-01` & `NFR-05`)

The target end-to-end assessment response latency is **p95 ≤ 5.0 s** (`NFR-01`). Because LLM calls dominate wall-clock latency, `LatencyBudget` (`server/app/services/ai/latency_budget.py`) enforces a strict monotonic ceiling:

| Stage | Allocation (Default `4.5 s` AI Budget) | Behavior |
|---|---|---|
| Deterministic intent check (`classify_intent`) | `< 1 ms` | Runs offline before any network call. |
| Primary provider slice (`OpenAiProvider`) | `60%` (`2.7 s` cap) | Bounded via `asyncio.wait_for`. Per-attempt timeouts and retry backoff delays are clamped so retries never overshoot the budget. |
| Failover trigger & guard | `>= 0.5 s` required (`MIN_ATTEMPT_TIMEOUT_SECONDS`) | If primary fails/times out and `< 0.5 s` remains, failover is skipped immediately with `AiTimeoutError` rather than starting a doomed request. |
| Fallback provider slice (`GeminiProvider`) | Remaining budget (typically `1.8 s–4.5 s`) | Bounded via `asyncio.wait_for` using remaining monotonic time. |
| Non-AI server work (DB, normalization, pgvector exact scan, risk engine, HTTP) | `0.5 s` reserved headroom | Keeps total HTTP response within the `5.0 s` p95 target. |

---

## 5. Known Limitations

1. **Language & Transliteration Coverage:** Prompts and evaluation sets target English and common Hinglish / transliterated Indian symptom phrases. Pure regional scripts (Devanagari, Gujarati, Tamil, etc.) or uncommon slang may have lower extraction recall and may require clarification or user confirmation on the Symptom Confirmation screen.
2. **Negation & Ambiguous Multi-Symptom Sentences:** Complex negated clauses (e.g., *"no fever anymore, just slight chills after stopping tablets"*) can occasionally extract negated terms or miss implicit modifiers. Downstream **user symptom confirmation** (`CONFIRMING` state) acts as the mandatory human-in-the-loop safeguard before risk analysis.
3. **3-Turn Clarification Ceiling (`FR-20`):** To prevent interrogation fatigue, the engine stops asking follow-ups after 3 turns even if minor optional attributes (e.g., exact body site for a non-red-flag symptom) remain unknown. Missing attributes default to `unknown` and are handled conservatively by the risk engine (uncertainty escalates risk; never lowers it).
4. **Upstream PII Scrubber Boundaries:** `PrivacyAiGateway` (`S1-HAR-2`) scrubs standard PII patterns (emails, phone numbers, Aadhaar/PAN-like IDs, known names) with bounded payload traversal (40,000 chars, depth 12). Unusual free-text personal details not matching scrubber patterns remain the user's responsibility to avoid sharing (disclosed in the consent flow).
5. **Non-Diagnostic Scope:** The AI service does not interpret lab reports, prescription dosages, imaging studies, or pediatric/obstetric specialist histories. It strictly extracts structured symptom descriptions for informational triage.
6. **Non-Deterministic LLM Variance:** Even at `temperature = 0.0`, external hosted LLMs (OpenAI / Gemini) may occasionally vary phrasing of clarification questions or uncanonicalized symptom synonyms. Symptom canonicalization (exact normalizer + deterministic pgvector exact scan) and the 100% deterministic Risk Engine (`DR-02`) isolate triage outcomes from LLM variance.

---

## 6. Failure Modes & Graceful Degradation Matrix

| Failure Mode | Trigger | Gateway Behavior | Typed Exception | Safe Downstream / User Impact |
|---|---|---|---|---|
| **Primary transient error** | OpenAI `429`, `5xx`, connection drop | Retries within primary slice; if still failing, fails over to `GeminiProvider` within remaining budget | None if Gemini succeeds; `AiError` if both fail | Seamless recovery if Gemini succeeds; safe retry prompt if both fail. |
| **Primary slow / hanging** | OpenAI exceeds `60%` primary slice (`2.7 s`) | Cancels primary cleanly via `asyncio.wait_for`; hands remaining `1.8 s` to `GeminiProvider` | None if Gemini succeeds; `AiTimeoutError` if Gemini also times out | Keeps response under `5 s` p95 ceiling; never hangs worker threads. |
| **Primary invalid JSON / refusal** | OpenAI refusal, `LengthFinishReasonError`, or schema mismatch | Fails fast on primary (`AiValidationError`) and immediately fails over to `GeminiProvider` | None if Gemini succeeds; `AiError` if both fail | Unvalidated text never reaches the orchestrator or user. |
| **Gemini safety block / malformed JSON** | `promptFeedback.blockReason`, `finishReason=SAFETY/MAX_TOKENS`, or schema mismatch | Fails fast (0 retries) | `AiValidationError` | Orchestrator catches `AiError` and returns safe typed error; never exposes raw LLM text. |
| **Invalid / revoked API key** | HTTP `401` / `403` on OpenAI or Gemini | Fails fast (0 retries) on affected provider; fails over to healthy provider if configured | `AiError` (if no healthy provider) | Safe generic service error returned to client; keys never logged. |
| **Latency budget exhausted** | Remaining monotonic budget `< 0.5 s` before retry or fallback | Skips doomed retry/fallback immediately | `AiTimeoutError` | Fast bounded error response with safe retry option and emergency `112` banner. |
| **Both providers unavailable** | Simultaneous OpenAI + Gemini outage | Logs both provider error types (zero PII); raises `AiError` or `AiTimeoutError` with safe `details` | `AiError` / `AiTimeoutError` | API returns safe typed error (`503`/service unavailable); client displays retry state + emergency number `112`. |
| **Prompt injection / jailbreak** | User attempts instruction override or system prompt exfiltration | Blocked offline by `IntentClassifier` before LLM call; secondary defence via `intent_defence.v1.txt` | None (returns `IntentResult` with safe refusal) | Safe non-diagnostic redirection; no LLM tokens spent on detected injections. |
| **Off-topic chat request** | Non-health query (code, math, general chat) | Handled offline by `IntentClassifier` | None (returns `IntentResult` with scope reminder) | Politely guides user back to symptom description. |
| **Empty / whitespace input** | Blank user message | Short-circuits immediately before network call | None (empty `ExtractionResult`) | Zero network cost; orchestrator prompts for symptom input. |
| **Missing provider key at startup** | `AI_PROVIDER=openai` without `OPENAI_API_KEY`, or `AI_PROVIDER=gemini` without `GEMINI_API_KEY` | Fails explicitly in `get_ai_gateway()` | `AiError` | Clear operational misconfiguration error (dev/CI default to `AI_PROVIDER=mock`). |
