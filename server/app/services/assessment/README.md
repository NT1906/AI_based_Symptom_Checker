# Assessment Service Module

**Owner:** Darshil (Assessment Orchestration) · **Task:** S1-DAR-2 · **Requirements:** FR-03, FR-17

The Assessment Service orchestrates the conversational symptom assessment lifecycle. It provides:
1. **Assessment State Machine**: Strictly governs valid states and enforces medical-safety guards throughout the user experience.
2. **Assessment Orchestrator**: Coordinates user chat intake, calls the AI Gateway for structured symptom extraction and clarification, deterministically merges recognized symptoms, and progresses assessment lifecycle states.

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
- `guard_under_clarification_limit`: Strictly caps clarification follow-up turns at `MAX_CLARIFICATION_TURNS` (3).
- `guard_symptoms_confirmed`: Requires explicit user confirmation (`is_confirmed=True`) before entering `READY`.
- `guard_analysis_completed`: Verifies analysis outcome before marking state as `COMPLETED`.

---

## 3. Orchestration & `process_message()` Flow

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
```

### Usage Example

```python
from uuid import uuid4
from app.services.assessment import AssessmentOrchestrator

orchestrator = AssessmentOrchestrator()

# Initialize an assessment session
consent_id = uuid4()
assessment = orchestrator.create_assessment(consent_id=consent_id)

# Process a user message
result = await orchestrator.process_message(
    assessment_id=assessment.id,
    message="I have had a mild headache and fever since yesterday.",
)

# Inspect results
print(result.next_state)  # AssessmentState.CONFIRMING or CLARIFYING
print(result.symptoms)  # Extracted canonical symptoms
```

---

## 4. Running Unit Tests

From `server/`:

```powershell
pytest tests/unit/assessment -v
```

