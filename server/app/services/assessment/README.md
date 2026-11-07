# Assessment Service Module

**Owner:** Darshil (Assessment Orchestration) · **Task:** S1-DAR-2, S1-DAR-3, S1-DAR-4, S2-DAR-2 · **Requirements:** FR-03, FR-04, FR-05, FR-06, FR-07, FR-16, FR-17, FR-19, FR-20, FR-21, FR-25, DR-05, idea §3

The Assessment Service orchestrates the conversational symptom assessment lifecycle. It provides:
1. **Assessment State Machine**: Strictly governs valid states and enforces medical-safety guards throughout the user experience.
2. **Assessment Orchestrator**: Coordinates user chat intake, calls the AI Gateway for structured symptom extraction and clarification, deterministically merges recognized symptoms, and progresses assessment lifecycle states.
3. **Clarification Turn Limiting & Low-Confidence Flagging**: Strictly enforces a maximum of 3 clarification questions (FR-04, FR-19). If ambiguity remains after 3 turns, forces transition to CONFIRMING and marks the session with `is_low_confidence=True` (FR-20).
4. **Clinical Analysis & Triage Results**: Executes the clinical prediction and risk evaluation pipeline upon symptom confirmation (`generate_result()`), applying the safety-wording guard before user delivery (FR-05, FR-06, FR-07, DR-05).
5. **Symptom Confirmation, Editing & Session Restart**: Enables user review and modification (add, remove, edit severity/duration, bulk update) of recognized symptoms before analysis (`confirm_symptoms()`, `update_symptoms()`), stepping back to chat (`step_back_to_chat()`), and cleanly starting over (`restart_assessment()`) per FR-16, FR-21, and FR-25.

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

## 7. Image Findings Integration (S2-DAR-2)

Per **idea §3**:
For visibly assessable conditions (e.g. eczema, hives, rashes), optional photos are analyzed into canonical visual symptoms via Nisarg's `ImageAnalyzer` (S1-NIS-4). Visual findings join the assessment state seamlessly:

- **`merge_image_findings(assessment_id, findings)`**: Ingests an `ImageAnalysis` or list of `ExtractedSymptom` records.
  - Clear analyses map to recognized visual symptoms with `Severity.UNKNOWN` and provenance `SymptomSource.IMAGE_FINDING`.
  - Unclear photos (`ImageLabel.UNCLEAR`) are gracefully ignored, and the assessment continues with text symptoms only.
  - Image findings are deduplicated with pre-existing text symptoms; confirmed symptoms retain their confirmed status and specific severity.
- **`process_image(assessment_id, image_bytes)`**: Ingests validated, sanitized in-memory image bytes, executes the configured `ImageAnalyzer`, and merges visual findings into the assessment session. Analyzer errors (`ImageAnalysisError`) are caught gracefully to carry on with text without interrupting the assessment.
- **Safety**: Photos are analyzed in memory only (never written to disk or logged). Triage risk is always computed deterministically from combined confirmed symptoms (AI_RULES.md §2).

---

## 8. Running Unit Tests

From `server/`:

```powershell
pytest tests/unit/assessment -v
```
