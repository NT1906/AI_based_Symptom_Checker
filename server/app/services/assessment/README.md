# Assessment Service Module

**Owner:** Darshil (Assessment Orchestration) · **Task:** S1-DAR-2, S1-DAR-3, S2-DAR-5 · **Requirements:** FR-03, FR-04, FR-05, FR-06, FR-07, FR-17, FR-19, FR-20, DR-05

The Assessment Service orchestrates the conversational symptom assessment lifecycle. It provides:
1. **Assessment State Machine**: Strictly governs valid states and enforces medical-safety guards throughout the user experience.
2. **Assessment Orchestrator**: Coordinates user chat intake, calls the AI Gateway for structured symptom extraction and clarification, deterministically merges recognized symptoms, and progresses assessment lifecycle states.
3. **Clarification Turn Limiting & Low-Confidence Flagging**: Strictly enforces a maximum of 3 clarification questions (FR-04, FR-19). If ambiguity remains after 3 turns, forces transition to CONFIRMING and marks the session with `is_low_confidence=True` (FR-20).
4. **Clinical Analysis & Triage Results**: Executes the clinical prediction and risk evaluation pipeline upon symptom confirmation (`generate_result()`), applying the safety-wording guard before user delivery (FR-05, FR-06, FR-07, DR-05).

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

## 6. Running Unit Tests

From `server/`:

```powershell
pytest tests/unit/assessment -v
```
