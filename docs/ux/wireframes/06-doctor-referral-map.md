# Wireframe UX-06: Doctor Referral via External Map

> **Screen:** External Specialist Referral Launcher  
> **Owner:** Mann · **Requirements:** idea §9, FR-08 (Reinterpreted Scope), DR-07 (No Doctor DB)

---

## 1. Screen Purpose & Narrative

When triage indicates that clinical evaluation is appropriate, the application connects the user with external local providers by launching an external map search (e.g. Google Maps or Apple Maps) pre-populated with the relevant specialty (e.g. "Dermatologist near me").

**Explicit Architectural Boundary:**
- No doctor accounts, credentials, bookings, ratings, or doctor databases are stored in this system (`docs/idea.md` §Explicitly Out of Scope).
- The referral is strictly an outbound query helper.

---

## 2. Desktop & Mobile Wireframe Layout

```text
┌────────────────────────────────────────────────────────────────────────┐
│ [← Back to Result] Find Local Specialist                     [Call 112]│
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│                      SPECIALIST REFERRAL ASSISTANT                     │
│               Find healthcare providers in your vicinity               │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ 🩺 RECOMMENDED MEDICAL SPECIALTY                               │   │
│   │                                                                │   │
│   │   Primary Specialty: Dermatologist                             │   │
│   │   Secondary Option:  General Physician / Family Doctor         │   │
│   │                                                                │   │
│   │   Based on your reported rash and mild itching, a clinical     │   │
│   │   examination by a dermatologist is recommended.               │   │
│   └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ 📍 SEARCH NEARBY CLINICS & HOSPITALS                           │   │
│   │                                                                │   │
│   │   Launch an external map search to locate doctors and clinics  │   │
│   │   near your current location:                                  │   │
│   │                                                                │   │
│   │   [ 🗺️ Open in Google Maps ("Dermatologist near me") ]         │   │
│   │                                                                │   │
│   │   [ 🍏 Open in Apple Maps / Local Maps App ]                   │   │
│   │                                                                │   │
│   │   * We do not recommend, endorse, or verify any specific       │   │
│   │     doctor, clinic, or private practice.                       │   │
│   └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ 📝 WHAT TO BRING TO YOUR VISIT                                 │   │
│   │ • A record of when your symptoms first began (duration).       │   │
│   │ • List of any medications or allergies.                       │   │
│   │ • Any photographs showing how the symptom evolved over time.   │   │
│   └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
├────────────────────────────────────────────────────────────────────────┤
│ ⚖️ PERSISTENT DISCLAIMER (DR-01):                                      │
│ External map links are provided for convenience only. We do not book   │
│ appointments or maintain healthcare provider directories.              │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. UI Component Specifications

1. **Specialty Callout Card:**
   - Highlights the medical specialty determined by the prediction service.
   - Includes lay-term explanation of what this specialist treats.

2. **Outbound Map Launch Buttons:**
   - Link formats:
     - Web / Android: `https://www.google.com/maps/search/?api=1&query={specialty}+near+me`
     - iOS / Apple Maps: `maps://?q={specialty}+near+me`
   - Attributes: `target="_blank"` with `rel="noopener noreferrer"`.
