# Assessment Unit Tests

This directory contains unit tests for the assessment domain, focusing on the assessment state machine, guarded transitions, orchestrator lifecycle, and session contexts.

## Modules Under Test

| Test File | Focus | Owner / Task |
|---|---|---|
| `test_state_machine_transitions.py` | Full 8x8 matrix (23 valid, 41 invalid transitions), isolated guard functions, context validation | Mohit · S1-MOH-1 |
| `test_state_machine.py` | State machine lifecycle and transition helpers | Darshil · S1-DAR-1 |
| `test_clarification_limit.py` | Clarification turn counting and capping logic | Darshil · S1-DAR-3 |
| `test_confirm_and_restart.py` | Symptom confirmation, edit flow, and session restart | Darshil · S1-DAR-4 |
| `test_generate_result.py` | Result generation transition and context mapping | Darshil · S1-DAR-2 |
| `test_idempotent_messages.py` | Idempotent message handling and deduplication | Darshil · S2-DAR-4 |
| `test_image_findings.py` | Image finding integration into assessment context | Darshil · S2-DAR-2 |
| `test_profile_context.py` | User clinical profile injection into assessment context | Darshil · S2-DAR-3 |
| `test_claim_guest_assessment.py` | Guest session migration to registered accounts | Darshil · S2-DAR-1 |
| `test_orchestrator.py` | Orchestration coordinator unit verification | Darshil |

## State Machine Transition Matrix Coverage

The canonical assessment lifecycle defines 8 states:
`START`, `SYMPTOM_COLLECTION`, `CLARIFYING`, `CONFIRMING`, `READY`, `ANALYZING`, `COMPLETED`, `ERROR`.

Across all 64 possible state pairs:
- **23 Valid Transitions:** Verified with passing guards to guarantee valid state progression and history tracking.
- **41 Invalid Transitions:** Verified to ensure illegal state jumps are rejected with `InvalidStateTransitionError` (HTTP 409).
- **Guards Covered:** `guard_has_consent`, `guard_has_symptoms`, `guard_under_clarification_limit`, `guard_symptoms_confirmed`, and `guard_analysis_completed`.

## Running the Tests

```bash
cd server
pytest tests/unit/assessment/test_state_machine_transitions.py
```
