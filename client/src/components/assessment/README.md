# Assessment Components (`client/src/components/assessment/`)

**Owner:** Mann (Frontend + Deployment · Testing)  
**Sprint 1 Task:** S1-MAN-1 (Issue #59)  
**Sprint 2 Task:** S2-MAN-1 (Issue #184)  
**Requirements:** FR-16, FR-21, FR-03, DR-01, idea §3, DR-06

---

## Purpose

Provides user-facing assessment review, confirmation, and situational image attachment components:
1. **Symptom Review & Confirmation (`SymptomConfirmationCard`)**: Before transitioning to condition analysis, users review extracted symptoms, edit attributes (severity, duration, location), remove incorrect items, and add missing symptoms from a canonical selectable list.
2. **Situational Image Attachment (`ImageAttach`)**: Offered *only* when visual symptoms are identified (rashes, skin discoloration, swelling, bumps, blisters, lesions). Provides direct mobile camera capture (`capture="environment"`), client-side MIME and 5 MB size validation, in-memory preview with removal capability, and mandatory non-retention privacy notices (`DR-06`).

---

## Public Interface

* **`ImageAttach`**: Situational image attachment widget (`idea §3`, `DR-06`).
  * `symptoms?: (string | ConfirmedSymptom | Record<string, unknown>)[] | string | null`: Inputs evaluated to detect visual symptoms.
  * `forceShow?: boolean`: Force rendering regardless of detected symptoms.
  * `selectedFile?: File | null`: Currently attached file (if controlled externally).
  * `onImageSelect: (file: File | null) => void`: Dispatched when a photo is selected, validated, or removed.
  * `onError?: (error: string | null) => void`: Dispatched when validation errors occur.
  * `disabled?: boolean`: Disables attachment buttons and inputs.
  * `className?: string`: Optional container CSS class name.
* **`hasVisualSymptoms`**: Pure helper evaluating text strings, arrays, or domain symptom objects for visual/dermatological indicators.
* **`MAX_IMAGE_SIZE_BYTES`**: Constant defining the 5 MB payload limit (`5 * 1024 * 1024`).
* **`ALLOWED_IMAGE_TYPES`**: Allowed MIME types (`image/jpeg`, `image/png`, `image/webp`).
* **`IMAGE_PRIVACY_DISCLAIMER`**: Mandatory non-retention notice: *"Photos are processed in-memory for visual triage analysis and are never stored, logged, or shared."*
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
npm test src/components/assessment/ImageAttach.test.tsx
npm test src/components/assessment/visualSymptoms.test.ts
npm test src/components/assessment/SymptomConfirmationCard.test.tsx
```


