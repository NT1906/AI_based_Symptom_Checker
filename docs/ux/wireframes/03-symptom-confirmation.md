# Wireframe UX-03: Symptom Confirmation & Editing Screen

> **Screen:** Symptom Confirmation & Modification  
> **Owner:** Mann · Reviewed by Darshil · **Requirements:** idea §4, FR-16, FR-21, FR-03

---

## 1. Screen Purpose & Narrative

Before generating conditions or assessing risk, the application reflects back the extracted symptoms in a structured card. The user can review, edit severity/duration, remove erroneous symptoms, and add missing symptoms from a canonical glossary. This builds critical trust and prevents garbage-in/garbage-out errors.

---

## 2. Desktop & Mobile Wireframe Layout

```text
┌────────────────────────────────────────────────────────────────────────┐
│ [← Back to Chat] Review Extracted Symptoms                   [Call 112]│
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│                      CONFIRM YOUR SYMPTOMS                             │
│       Please verify the symptoms we understood before analysis         │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ 📋 REPORTED SYMPTOMS (2 identified)                            │   │
│   ├────────────────────────────────────────────────────────────────┤   │
│   │                                                                │   │
│   │ [1] Headache                                                   │   │
│   │     • Severity: Severe (throbbing)                             │   │
│   │     • Duration: Since yesterday (≈ 24 hours)                   │   │
│   │     • Body Site: Head / Temples                                │   │
│   │     [ ✏️ Edit Details ]                      [ 🗑️ Remove ]       │   │
│   │                                                                │   │
│   │ ────────────────────────────────────────────────────────────── │   │
│   │                                                                │   │
│   │ [2] Photophobia (Sensitivity to Light)                         │   │
│   │     • Severity: Moderate                                       │   │
│   │     • Duration: 12 hours                                       │   │
│   │     [ ✏️ Edit Details ]                      [ 🗑️ Remove ]       │   │
│   │                                                                │   │
│   ├────────────────────────────────────────────────────────────────┤   │
│   │ [ + Add Another Symptom from List ]                            │   │
│   │   [ Search symptoms e.g. nausea, dizziness...        🔍 ]     │   │
│   └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                 [ CONFIRM & ANALYZE NOW ➤ ]                    │   │
│   │  Generates qualitative condition likelihood and risk tier      │   │
│   └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
├────────────────────────────────────────────────────────────────────────┤
│ ⚖️ PERSISTENT DISCLAIMER (DR-01):                                      │
│ This is not a medical diagnosis. Confirmation is used to organize      │
│ informational suggestions only. In life-threatening emergencies, call 112.│
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. UI Component Specifications

1. **Symptom Card Item:**
   - Displays canonical symptom title and extracted attributes (severity, duration, body site).
   - "Edit" button opens inline editing popover with standardized dropdowns (e.g. Mild, Moderate, Severe).
   - "Remove" button removes the item with undo toast notification.

2. **Add Symptom Selectable List (FR-03, idea §4):**
   - Live search input querying canonical symptoms (`ml/datasets/symptoms/`).
   - Autocomplete dropdown with keyboard arrow-key navigation.

3. **Confirm & Analyze Primary Action:**
   - High-contrast Teal button (`bg-teal-700 hover:bg-teal-800 text-white`).
   - Transitions state to `ANALYZING` and renders progress skeleton.
