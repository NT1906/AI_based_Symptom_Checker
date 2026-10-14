# Wireframe UX-04: Result & Triage Overview Screen

> **Screen:** Result Overview & Triage Guidance  
> **Owner:** Mann · Reviewed by Nisarg & Dimple · **Requirements:** idea §6, §7, §8, FR-22, FR-23, FR-24, DR-01, DR-02

---

## 1. Screen Purpose & Narrative

The comprehensive result screen generated after confirmation. It displays the deterministic risk tier (`SELF_CARE`, `CONSULT_DOCTOR`, or `URGENT`), qualitative confidence labels for top matching conditions (`Likely`, `Possible`, `Less likely` — **never raw percentages**), plain-language contributing factor rationale, self-care guidance, specialist referral recommendations, and mandatory disclaimers.

---

## 2. Desktop & Mobile Wireframe Layout

```text
┌────────────────────────────────────────────────────────────────────────┐
│ [← Start New Assessment] Assessment Summary                  [Call 112]│
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ 🟡 RISK LEVEL: CONSULT A DOCTOR                                │   │
│   │ Medical consultation recommended within 24–48 hours.           │   │
│   │ This is not an emergency, but requires clinical evaluation.    │   │
│   └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ 🩺 POSSIBLE CONDITIONS (Qualitative Confidence)                │   │
│   │ These are possible considerations based on reported symptoms.  │   │
│   │                                                                │   │
│   │ 1. Migraine with Photophobia                  [ Likely ]       │   │
│   │    • Why: Matching unilateral throbbing pain and light         │   │
│   │      sensitivity lasting > 24 hours.                           │   │
│   │    • Recommended Specialty: Neurologist / General Physician   │   │
│   │                                                                │   │
│   │ 2. Tension-type Headache                      [ Possible ]     │   │
│   │    • Why: Common cause of persistent head discomfort.          │   │
│   │    • Recommended Specialty: General Physician                  │   │
│   │                                                                │   │
│   │ 3. Sinusitis                                  [ Less likely ]  │   │
│   │    • Why: Potential overlap, though nasal symptoms absent.     │   │
│   └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ 💡 GENERAL SELF-CARE & NEXT STEPS                              │   │
│   │ • Rest in a quiet, dark room to alleviate photophobia.         │   │
│   │ • Maintain adequate hydration and avoid bright screens.        │   │
│   │ • Seek immediate emergency medical care if you develop sudden  │   │
│   │   fever, confusion, or stiff neck.                             │   │
│   └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ 📍 RECOMMENDED ACTION                                          │   │
│   │ [ Find a General Physician / Neurologist Near Me 🗺️ ]          │   │
│   │ (Opens external map search; no doctor data stored)             │   │
│   └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│   [ 🔄 Start New Assessment ]        [ 📥 Download Summary (PDF) ]  │
│                                                                        │
├────────────────────────────────────────────────────────────────────────┤
│ ⚖️ PERSISTENT DISCLAIMER (DR-01):                                      │
│ This is not a medical diagnosis. Always consult a qualified healthcare │
│ professional. If you experience worsening or red-flag symptoms, call 112.│
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. UI Component Specifications

1. **Risk Level Banner (FR-06, FR-15):**
   - Self-Care: `#ecfdf5` green card with `#065f46` text.
   - Consult Doctor: `#fffbeb` amber card with `#92400e` text.
   - Urgent Care: `#fff1f2` rose card with `#9f1239` text (triggers UX-05).

2. **Qualitative Confidence Badges (AI_RULES.md §2, FR-23):**
   - Strictly `Likely` (teal/blue), `Possible` (amber), `Less likely` (slate).
   - Zero numbers, percentages, or decimal probabilities shown to users.

3. **"Why" Explanation Panel (FR-24):**
   - Displays contributing factors in plain language ("Because you reported X and Y").

4. **External Map Referral (idea §9, FR-08):**
   - External search button opening Google Maps or Apple Maps with the specialty query.
