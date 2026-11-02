# Assessment Components (`client/src/components/assessment/`)

**Owner:** Mann (Frontend + Deployment · Testing)  
**Sprint 1 Task:** S1-MAN-1 (Issue #59)  
**Requirements:** FR-16, FR-21, FR-03, DR-01

---

## Purpose

Provides user-facing assessment review and confirmation cards. Before transitioning to condition analysis, users review extracted symptoms, edit attributes (severity, duration, location), remove incorrect items, and add missing symptoms from a canonical selectable list.

---

## Public Interface

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
npm test src/components/assessment/SymptomConfirmationCard.test.tsx
```

