# Assessment Service Module

**Owner:** Darshil (Assessment Orchestration) · **Task:** S1-DAR-2, S1-DAR-3, S1-DAR-4, S2-DAR-1, S2-DAR-2, S2-DAR-3, S2-DAR-4, S2-DAR-6, S2-DAR-7, S2-DAR-8, S2-DAR-9, S2-DAR-10 · **Requirements:** idea §3, idea §10, FR-02, FR-03, FR-04, FR-05, FR-06, FR-07, FR-15, FR-16, FR-17, FR-19, FR-20, FR-21, FR-25, DR-02, DR-05, NFR-01, NFR-03, NFR-05

The Assessment Service orchestrates the conversational symptom assessment lifecycle. It provides:
1. **Assessment State Machine**: Strictly governs valid states and enforces medical-safety guards throughout the user experience.
2. **Assessment Orchestrator**: Coordinates user chat intake, calls the AI Gateway for structured symptom extraction and clarification, deterministically merges recognized symptoms, and progresses assessment lifecycle states.
3. **Clarification Turn Limiting & Low-Confidence Flagging**: Strictly enforces a maximum of 3 clarification questions (FR-04, FR-19). If ambiguity remains after 3 turns, forces transition to CONFIRMING and marks the session with `is_low_confidence=True` (FR-20).
4. **Clinical Analysis & Triage Results**: Executes the clinical prediction and risk evaluation pipeline upon symptom confirmation (`generate_result()`), applying the safety-wording guard before user delivery (FR-05, FR-06, FR-07, DR-05).
5. **Symptom Confirmation, Editing & Session Restart**: Enables user review and modification (add, remove, edit severity/duration, bulk update) of recognized symptoms before analysis (`confirm_symptoms()`, `update_symptoms()`), stepping back to chat (`step_back_to_chat()`), and cleanly starting over (`restart_assessment()`) per FR-16, FR-21, and FR-25.
6. **Guest Assessment Claiming**: Allows anonymous guests to transfer assessment history into a registered user account upon sign-up (`claim_assessment()`, `claim_guest_session()`) per idea §10.
7. **Idempotent Message Processing & Transactions**: Eliminates double answers on client retry, handles rapid concurrent submissions via per-session async locks, and enforces atomic transactions across database and in-memory session changes (NFR-05).
8. **Performance SLA & Result Latency Budget**: Guarantees that `generate_result()` computes triage classification within `RESULT_DEADLINE_SECONDS = 5.0` s (p95 latency ≤ 5 s on staging per NFR-01). Structured logs emit elapsed time on completion and warn on budget overruns.
9. **Canonical Symptom ID Mapping (S2-DAR-9)**: Injects `SymptomResolver` to map free-text extracted symptom names (e.g. "Chest pain", "tummy ache", "seene me dard") to canonical symptom IDs (`chest_pain`, `abdominal_pain`) before reaching the condition predictor and deterministic risk engine (DR-02, FR-03, FR-06). Unresolved names remain in session for user confirmation but are safely excluded from risk evaluation.
10. **Red Flag Skip-Clarification Fast Path (S2-DAR-10)**: Evaluates mapped symptoms with deterministic `find_red_flags()` directly after intake. When any red flag is detected, immediately skips further clarification turns and transitions to `CONFIRMING` with fixed safe 112 emergency notice (`RED_FLAG_EMERGENCY_PROMPT`), allowing rapid confirmation and immediate urgent triage (FR-06, FR-15, DR-02, AI_RULES.md §2.5).

---

## 1. Lifecycle State Graph

```text
START
  │
  ▼ [has_consent]
SYMPTOM_COLLECTION ◄────────────┐
  │         │                   │
  │         ▼ [under_limit]     │ [edit]
  │       CLARIFYING            │
  │         │                   │
  ▼         ▼ [has_symptoms]    │
CONFIRMING ─────────────────────┘
  │
  ▼ [symptoms_confirmed & has_symptoms]
READY
  │
  ▼ [has_symptoms]
ANALYZING
  │
  ▼ [analysis_completed]
COMPLETED
```

Invalid transitions reject with `InvalidStateTransitionError` (`HTTP 409 Conflict`), adhering to `docs/api-contract.md`.

---

## 2. Guard Conditions

- `guard_has_consent`: Requires a valid `consent_id` before transitioning `START → SYMPTOM_COLLECTION`.
- `guard_has_symptoms`: Ensures at least 1 symptom is recorded before entering `CONFIRMING`, `READY`, or `ANALYZING`.
- `guard_under_clarification_limit`: Strictly caps clarification follow-up turns at `MAX_CLARIFICATION_TURNS` (3). Rejects transitions into `CLARIFYING` with HTTP 409 Conflict once limit is reached.
- `guard_symptoms_confirmed`: Requires explicit user confirmation (`is_confirmed=True`) before entering `READY`.
- `guard_analysis_completed`: Verifies analysis outcome before marking state as `COMPLETED`.

---

## 3. Clarification Loop & Low-Confidence Safety Policy

Per **FR-04**, **FR-19**, and **FR-20**:
- **Turn Cap:** The clarification loop is capped at a strict maximum of 3 turns (`MAX_CLARIFICATION_TURNS = 3`).
- **Forced Confirmation:** When `clarification_count >= 3` and the patient's symptoms still have unresolved ambiguity, the orchestrator terminates the clarification loop and automatically forces transition to `CONFIRMING`.
- **Low-Confidence Flagging:** The orchestrator sets `is_low_confidence = True` on both the runtime session and the state machine context.
- **Medical Safety Invariant:** Per `AI_RULES.md` §2, uncertainty may escalate risk or flag caveats, but must never artificially lower the risk level. Downstream triage uses `is_low_confidence` to ensure conservative, safe recommendations.

---

## 4. Orchestration & `process_message()` Flow

The `AssessmentOrchestrator` is the central coordination service for assessment dialogues:

```text
User Message
    │
    ▼
1. Validate & Store User Message (ordered position)
    │
    ▼
2. AI Gateway Extraction (dialogue context, timeout-safe)
    │
    ▼
3. Deterministic Symptom Merging (merge attributes, deduplicate)
    │
    ▼
4. State Decision & Response Formatting:
   ├── No symptoms → Stay in SYMPTOM_COLLECTION, ask detail
   ├── Needs clarification (< 3 turns) → CLARIFYING, pose AI follow-up
   └── Clarification done or capped (>= 3) → CONFIRMING, review prompt
       (if capped with ambiguity: is_low_confidence = True)
```

---

## 5. Clinical Analysis Pipeline (`generate_result()`)

Per **FR-05**, **FR-06**, **FR-07**, and **DR-05**:
Once symptoms are confirmed and the session enters `READY`, calling `generate_result()` executes the end-to-end evaluation pipeline:

```text
READY State
    │
    ▼ sm.start_analysis()
ANALYZING State
    │
    ├── 1. Map confirmed symptoms to ReportedSymptom(id, severity)
    ├── 2. Condition Prediction: BaselineConditionModel().predict(symptom_ids)
    ├── 3. Deterministic Risk Engine: assess_risk(reported, predictions)
    └── 4. Result Composition & Safety Check:
           ResultComposer(wording_guard=assert_safe_wording).compose(...)
               │
               ├── Safe wording passes ──► sm.complete_analysis() ──► COMPLETED State
               │                                                      (returns AssessmentResult)
               │
               └── Unsafe wording fails ─► sm.transition_to_error() ──► ERROR State
                                           (re-raises UnsafeWordingError 500)
```

### Safety & Guarding Rules
- **No Diagnostic Language:** Composed text is validated against `assert_safe_wording` (DR-05) to block banned phrases.
- **Fail-Closed on Unsafe Wording:** If `UnsafeWordingError` is raised, the state transitions to `ERROR` and the error propagates; the assessment never reaches `COMPLETED` and no result is leaked.
- **Deterministic Risk:** Red-flag symptoms (e.g. chest pain + sweating) always trigger `URGENT` triage with 112 referral instructions.
- **Dependency Injection:** Custom `ResultComposer` and `ConditionModel` instances can be injected into `AssessmentOrchestrator` for testing and model extension.

---

---

## 6. Symptom Confirmation, Editing & Restart (S1-DAR-4)

Per **FR-16**, **FR-21**, and **FR-25**:
Before triage analysis, the application reflects back extracted symptoms for user review on the confirmation card (Wireframe UX-03). The user has full control to modify symptoms:

- **`confirm_symptoms(assessment_id, symptoms=None)`**: Confirms recorded symptoms, updates provenance to `USER_CONFIRMED`, and advances state machine to `READY` (FR-21). Accepts an optional replacement or updated symptoms sequence. Empty symptom lists are rejected with HTTP 400 `EMPTY_SYMPTOMS`.
- **`add_symptom(assessment_id, symptom)`**: Adds a new symptom with `USER` provenance or updates attributes if the symptom name already exists with `USER_CORRECTED` (FR-16).
- **`remove_symptom(assessment_id, symptom_id)`**: Removes a symptom by UUID or name string (FR-16).
- **`edit_symptom(assessment_id, symptom_update)`**: Updates severity, duration, or anatomical body site, recording provenance as `USER_CORRECTED`.
- **`update_symptoms(assessment_id, symptoms)`**: Bulk applies symptom additions, edits, and confirmations.
- **`step_back_to_chat(assessment_id)`**: Reverts session state from `CONFIRMING` or `READY` to `SYMPTOM_COLLECTION` when user clicks "Back to Chat" for conversational re-entry.
- **`restart_assessment(assessment_id, to_state=START)`**: Handles "Start Over" (FR-25). Resets state machine, clears dialogue history and recorded symptoms, resets clarification counters and confidence flags, allowing a clean assessment restart.

---

---

## 7. Guest Assessment Claiming (S2-DAR-1)

Per **idea §10** and `docs/database.md`:
The application allows anonymous guests to start and complete assessments with zero registration friction (`user_id = None`, optionally bound to a `guest_session_id`). When the user registers or logs in:

- **`claim_assessment(assessment_id, user_id, guest_session_id=None, db_session=None)`**: Transfers ownership of an individual assessment to the new account (`assessment.user_id = user_id`). Verifies the assessment was not already claimed (HTTP 409 `ALREADY_CLAIMED`) and optionally verifies matching `guest_session_id` (HTTP 403 `GUEST_SESSION_MISMATCH`). Synchronizes with SQLAlchemy database session when provided.
- **`claim_guest_session(guest_session_id, user_id, db_session=None)`**: Bulk transfers all assessments associated with an anonymous guest session to the newly registered account, updating `guest_sessions.claimed_at` and `guest_sessions.claimed_by_user_id`. Prevents double-claiming already claimed sessions.

---

## 8. Image Findings Integration (S2-DAR-2)

Per **idea §3**:
For visibly assessable conditions (e.g. eczema, hives, rashes), optional photos are analyzed into canonical visual symptoms via Nisarg's `ImageAnalyzer` (S1-NIS-4). Visual findings join the assessment state seamlessly:

- **`merge_image_findings(assessment_id, findings)`**: Ingests an `ImageAnalysis` or list of `ExtractedSymptom` records.
  - Clear analyses map to recognized visual symptoms with `Severity.UNKNOWN` and provenance `SymptomSource.IMAGE_FINDING`.
  - Unclear photos (`ImageLabel.UNCLEAR`) are gracefully ignored, and the assessment continues with text symptoms only.
  - Image findings are deduplicated with pre-existing text symptoms; confirmed symptoms retain their confirmed status and specific severity.
- **`process_image(assessment_id, image_bytes)`**: Ingests validated, sanitized in-memory image bytes, executes the configured `ImageAnalyzer`, and merges visual findings into the assessment session. Analyzer errors (`ImageAnalysisError`) are caught gracefully to carry on with text without interrupting the assessment.
- **Safety**: Photos are analyzed in memory only (never written to disk or logged). Triage risk is always computed deterministically from combined confirmed symptoms (AI_RULES.md §2).

---

## 9. Clinical Profile Context (S2-DAR-3)

Per **FR-02** and **idea §10**:
Users with registered accounts may optionally supply coarse demographic and chronic health details to provide clinical context for assessments without building an invasive medical dossier.

- **`ProfileContext`**: Data model capturing optional coarse `AgeBand` (`child`, `teen`, `young_adult`, `adult`, `senior`), `BiologicalSex` (`female`, `male`, `other`, `prefer_not_to_say`), and self-reported `chronic_conditions` (e.g. Asthma, Diabetes).
- **Session Integration**: `AssessmentSession` and `AssessmentContext` support storing optional profile context attached at session initialization (`create_assessment()`), updated mid-assessment (`set_profile_context()`), or inspected (`get_profile_context()`).
- **Analysis Integration**: `generate_result(assessment_id, profile=...)` accepts optional profile context to contextualize clinical triage and passes it forward into downstream analysis.
- **Privacy Compliance**: Profile collection is strictly optional, minimal, and fully compliant with data minimization under the DPDP Act 2023.

---

## 10. Idempotent Message Processing & Transactions (S2-DAR-4)

Per **NFR-05** (Resilience) and `docs/database.md`:
Network retries and rapid client resubmissions must never create duplicate answers, corrupt conversation ordering, or advance lifecycle states multiple times.

- **Idempotency Deduplication**:
  - **Explicit Key (`idempotency_key` / `client_message_id`)**: `process_message()` checks the session's idempotency cache. If a turn with the matching key was already completed, it returns the cached `ProcessResult` immediately without invoking AI extraction or appending duplicate messages.
  - **Turn/Content-based Retry Detection**: If no explicit key is provided, the orchestrator inspects the last completed dialogue turn. If the incoming message text matches the immediately preceding user message, it treats the request as a retry and returns the existing response.
- **Concurrency Safety**:
  - Per-session asynchronous locking (`async with session.lock`) prevents race conditions between rapid concurrent submissions, ensuring only one intake pipeline runs at a time and any concurrent duplicates wait to receive the cached result.
- **Transactional Integrity**:
  - **In-Memory**: A complete state snapshot is captured before intake begins. Any unexpected processing failure automatically rolls back messages, symptoms, and state machine context to the snapshot.
  - **Database Persistence**: When an active SQLAlchemy `db_session` is supplied, user messages, symptoms, assistant replies, and assessment state updates are executed inside a savepoint transaction (`db_session.begin_nested()`). Failures trigger a clean rollback.
- **Cache Management**:
  - `get_idempotent_result(assessment_id, key)`: Inspects cached results.
  - `clear_idempotency_cache(assessment_id)`: Flushes cached keys (automatically invoked during `restart_assessment()`).

---

## 11. Authorization Audit & Ownership Boundaries (S2-DAR-6)

Per **NFR-03** (Security & Access Control), OWASP API Security Top 10 (A01: Broken Object Level Authorization / IDOR), and `docs/api-contract.md`:
Every assessment resource is strictly scoped to its owner. Cross-user access is systematically blocked across all operational methods in the Assessment Orchestrator:

- **Ownership Invariants**:
  - **Registered User Assessments (`session.user_id` is set)**: Only requests authenticated with the exact matching `user_id` may read or modify the assessment. Anonymous callers and different registered users are blocked with `AssessmentAccessDeniedError` (`HTTP 403 Forbidden`).
  - **Anonymous Guest Assessments (`session.user_id is None`, `session.guest_session_id` is set)**: Only requests presenting the matching `guest_session_id` bearer token may access the assessment. Mismatched guest session tokens or unlinked registered users attempting to access unclaimed guest sessions without claiming are rejected with `HTTP 403 Forbidden` (`GUEST_SESSION_MISMATCH`).
  - **Post-Claim Invariant**: Once an assessment is claimed by a registered user (`claim_assessment()` / `claim_guest_session()`), ownership permanently shifts to `user_id`. The prior `guest_session_id` can no longer access or modify the assessment.
- **Audit Logging**:
  - Security violations emit structured audit warning logs: `logger.warning("unauthorized_access", assessment_id=..., reason=...)`.
  - Authorized accesses emit structured audit logs: `logger.info("assessment_access_authorized", assessment_id=...)`.
- **Enforcement Helpers**:
  - `assert_ownership(assessment_id, user_id=None, guest_session_id=None, db_session=None)`: Validates ownership against in-memory runtime session and SQLAlchemy persistence layer, raising `AssessmentAccessDeniedError` (403) or `AssessmentServiceError` (404).
  - `check_ownership(assessment_id, user_id=None, guest_session_id=None, db_session=None) -> bool`: Safe boolean predicate for route guards and conditional evaluation.
- **Protected Methods**:
  - Read access: `get_assessment`, `get_messages`, `list_messages`, `get_symptoms`, `get_state`, `get_profile_context`.
  - Write access: `process_message`, `confirm_symptoms`, `update_symptoms`, `add_symptom`, `remove_symptom`, `edit_symptom`, `step_back_to_chat`, `restart_assessment`, `set_profile_context`, `generate_result`, `merge_image_findings`, `process_image`.

---

## 12. Performance SLA & Latency Budget (S2-DAR-8)

Per **NFR-01** (Performance & Responsiveness), the clinical assessment result generation pipeline must guarantee p95 latency ≤ 5 seconds on staging:

- **Latency Budget**: `RESULT_DEADLINE_SECONDS = 5.0` s defined and exported from the package.
- **Timing Instrumentation**: `generate_result()` captures wall-clock monotonic timing `_t0 = time.monotonic()` around condition prediction, risk calculation, and result composition.
- **Structured Telemetry**:
  - Normal execution: `logger.info("result_generated", assessment_id=..., elapsed_ms=..., budget_ms=5000)`.
  - Overrun warning: If execution exceeds 5.0 s, `logger.warning("result_latency_budget_exceeded", assessment_id=..., elapsed_ms=..., budget_ms=5000)` alerts the system for latency regressions.
- **Benchmarks & Unit Tests**: Verified via `tests/unit/assessment/test_performance_p95.py` across single symptoms, multi-symptom loads (10 symptoms), maximum batch loads (50 symptoms), and 20-sample p95 quantile estimates completing within budget.

---

## 13. Canonical Symptom ID Mapping (S2-DAR-9)

Per **DR-02**, **FR-03**, and **FR-06**, free-text symptom names extracted by the AI or visual findings must be mapped to canonical symptom IDs before reaching the condition predictor and the deterministic risk engine:

- **The Safety Gap**: LLM extractors may return colloquial, capitalized, or hyphenated variants (e.g. `"Chest pain"` or `"chest-pain"` instead of canonical `"chest_pain"`). Unmapped names prevent deterministic red-flag rules from firing, creating a clinical safety risk.
- **SymptomResolver Integration**: The orchestrator injects `SymptomResolver` (S2-NIS-7):
  - Normalizes symptom names via exact dictionary lookup (display names, lay terms, transliterations).
  - Matches approximate terms via pgvector semantic embeddings (`MatchMethod.SEMANTIC`).
  - Degrades gracefully to exact-only if embedding or database components are unavailable.
- **Intake & Execution Pipeline**:
  - `process_message()`: Resolves extracted AI symptoms before merging into the assessment session.
  - `merge_image_findings()`: Resolves visual finding symptom names to canonical IDs.
  - `generate_result()`: Maps all confirmed symptoms to canonical IDs before evaluating condition predictions and risk engine red flags.
- **Unresolved Symptom Policy**:
  - Symptoms that do not match canonical vocabulary remain in `session.symptoms` so the patient still sees their reported symptoms on the confirmation screen.
  - Unresolved symptoms are excluded from predictor and risk engine inputs to avoid misleading scoring.
  - Unresolved symptoms emit a privacy-compliant telemetry log: `logger.info("symptom_unresolved", name_length=len(name))` (recording name length only, never the raw text).
- **Test Coverage**: Verified in `tests/unit/assessment/test_canonical_symptom_mapping.py` covering exact matches, colloquial lay terms, Hindi phrases, semantic embeddings, and privacy logging.

---

## 14. Red Flag Skip-Clarification Fast Path (S2-DAR-10)

Per **FR-06**, **FR-15**, **DR-02**, and **AI_RULES.md §2.5**:
When an intake message reports severe red-flag symptoms (such as crushing chest pain or severe shortness of breath), delaying triage with clarifying questions poses an acute medical safety risk:

- **Clinical Rationale**:
  - Asking follow-up clarification questions (e.g. "Did the pain build up gradually?") when red flags are already present stalls emergency care.
  - In a medical emergency, the user must be directed to call **112** immediately while allowing swift confirmation so the final urgent triage screen can be presented at once.
- **Deterministic Red Flag Detection**:
  - In `AssessmentOrchestrator.process_message()`, mapped symptoms are immediately checked via `find_red_flags()` from `app.services.prediction.risk_engine`.
  - The check is 100% deterministic with zero LLM involvement.
  - If any red flag triggers, clarification is completely bypassed and state transitions straight to `CONFIRMING`.
- **Fixed Safety Text**:
  - The orchestrator issues `RED_FLAG_EMERGENCY_PROMPT`:
    `"Some of what you describe can be serious. If you think this is an emergency, call 112 now. Please confirm your symptoms so we can show your result."`
  - Assistant message type is set to `MessageType.CONFIRMATION` and result type is `"CONFIRMATION"`.
- **Fault-Tolerant Fallback**:
  - If `find_red_flags()` raises an exception or fails, the orchestrator logs a structured warning (`red_flag_check_failed`) and safely falls back to standard clarification logic without crashing.
- **Test Coverage**:
  - Verified in `tests/unit/assessment/test_red_flag_skip_clarification.py` covering first-message red flags, non-red-flag clarification paths, red flags introduced during clarification turns, and fault-tolerant fallback behavior.

---

## 15. Running Unit Tests

From `server/`:

```powershell
pytest tests/unit/assessment -v
```
