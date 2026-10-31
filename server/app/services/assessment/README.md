# Assessment Service Module

**Owner:** Darshil (Assessment Orchestration) · **Task:** S1-DAR-1 · **Requirements:** N/A

The Assessment Service orchestrates the conversational symptom assessment lifecycle. At its core is the **Assessment State Machine**, which strictly governs valid states and enforces safety guards throughout the user experience.

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

## 3. Usage Example

```python
from uuid import uuid4
from app.schemas.enums import AssessmentState
from app.services.assessment import (
    AssessmentContext,
    AssessmentStateMachine,
    InvalidStateTransitionError,
)

# Initialize session
sm = AssessmentStateMachine(AssessmentState.START)
sm.context.consent_id = uuid4()

# Begin collection
sm.start_symptom_collection()

# Record symptoms and ask clarification
sm.context.symptoms.append({"name": "headache", "severity": "SEVERE"})
sm.request_clarification()  # clarification_count = 1

# Complete clarification and proceed to confirmation
sm.proceed_to_confirmation()

# Confirm symptoms
sm.confirm_symptoms()  # moves to READY

# Trigger analysis
sm.start_analysis()  # moves to ANALYZING

# Complete
sm.complete_analysis()  # moves to COMPLETED
```

---

## 4. Running Unit Tests

From `server/`:

```powershell
pytest tests/unit/assessment -v
```
