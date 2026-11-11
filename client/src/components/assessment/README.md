# Assessment Components (`client/src/components/assessment/`)

**Owner:** Mann (Frontend + Deployment · Testing)  
**Sprint 1 Task:** S1-MAN-1 (Issue #59)  
**Sprint 2 Tasks:** S2-MAN-1 (Issue #184), S2-MAN-3 (Issue #186)  
**Requirements:** FR-16, FR-21, FR-03, DR-01, FR-18

---

## Purpose

Provides user-facing assessment review, confirmation, and symptom educational guidance:
1. **Symptom Review & Confirmation (`SymptomConfirmationCard`)**: Before transitioning to condition analysis, users review extracted symptoms, edit attributes (severity, duration, location), remove incorrect items, and add missing symptoms from a canonical selectable list.
2. **Symptom Definition Tooltips (`SymptomTooltip`)**: Displays plain-language definitions and safe guidance on when to seek prompt medical attention for symptoms from the curated knowledge glossary (FR-18).

---

## Public Interface

* **`SymptomTooltip`**: Accessible symptom popover tooltip displaying plain-language definition and seek-care advice (FR-18).
* **`getSymptomDefinition(identifier)`**: Curated plain-language glossary lookup helper.
* **`SymptomConfirmationCard`**: Main confirmation component.
  * `initialSymptoms: ConfirmedSymptom[]`: Pre-extracted symptom items.
  * `onConfirm: (symptoms: ConfirmedSymptom[]) => void`: Dispatched when the user confirms verified symptoms.
  * `onCancel?: () => void`: Optional callback to navigate back to the guided chat.
  * `isSubmitting?: boolean`: Indicates whether submission / state transition is in progress.
* **`CONFIRMATION_DISCLAIMER_TEXT`**: Non-diagnostic medical disclaimer text (DR-01).
* **`CANONICAL_SYMPTOMS`**: Curated list of common canonical symptoms matching the knowledge dataset.

---

## How to Test

Run the Vitest component test suite:

```bash
cd client
npm test src/components/assessment/SymptomTooltip.test.tsx
npm test src/components/assessment/SymptomConfirmationCard.test.tsx
```

