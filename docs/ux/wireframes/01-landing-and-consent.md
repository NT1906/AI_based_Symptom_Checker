# Wireframe UX-01: Landing & Consent Screen

> **Screen:** Landing & Data Consent Flow  
> **Owner:** Mann · Reviewed by Dimple · **Requirements:** DR-01 (Disclaimer), DR-08 (Consent), idea §10, §12

---

## 1. Screen Purpose & Narrative

The initial entry point before any medical information is collected. It establishes immediate trust, sets clear boundaries (this is an informational triage aid, not a doctor), highlights emergency contact information (112), and captures required user consent before data capture begins.

---

## 2. Desktop & Mobile Wireframe Layout

```text
┌────────────────────────────────────────────────────────────────────────┐
│ [Logo] AI-Based Symptom Checker              [ Emergency: Call 112 ]   │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│                       AI-BASED SYMPTOM CHECKER                         │
│                    Understand your symptoms safely                     │
│                                                                        │
│   Get fast, private guidance on what might be causing your symptoms    │
│   and understand how urgently you should seek professional care.       │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ ⚠️ MEDICAL EMERGENCY ADVISORY                                  │   │
│   │ If you are experiencing chest pain, severe shortness of        │   │
│   │ breath, uncontrolled bleeding, or sudden numbness, call 112    │   │
│   │ immediately. Do not use this tool for emergency triage.        │   │
│   └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ 🔒 PRIVACY & INFORMATIONAL USE CONSENT                         │   │
│   │                                                                │   │
│   │ Before we begin, please review our core principles:            │   │
│   │                                                                │   │
│   │ • Informational Only: This tool provides general health        │   │
│   │   information and does not provide a medical diagnosis or      │   │
│   │   prescriptions. Always consult a qualified physician.         │   │
│   │ • Data Privacy: Your symptoms are processed securely and       │   │
│   │   temporarily. Images are analyzed in-memory and never saved.   │   │
│   │ • Guest Friendly: No registration is required to check your    │   │
│   │   symptoms today.                                              │   │
│   │                                                                │   │
│   │ [x] I understand this is an informational tool, not a doctor,  │   │
│   │     and I consent to processing my symptoms for triage.        │   │
│   │                                                                │   │
│   │               [ START ASSESSMENT BUTTON ]                      │   │
│   └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│   [ How It Works ]    [ Privacy Policy ]    [ About Us ]               │
│                                                                        │
├────────────────────────────────────────────────────────────────────────┤
│ ⚖️ PERSISTENT DISCLAIMER (DR-01):                                      │
│ This application is an informational triage aid and does not provide   │
│ a medical diagnosis or prescription. Always consult a healthcare       │
│ professional for clinical advice. If in urgent distress, call 112.     │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. UI Component Specifications

1. **Emergency Header Banner:**
   - Visual: Alert pill button linking directly to `tel:112`.
   - Accessibility: `aria-label="Call emergency services at 112"`.

2. **Hero Copy & Context Card:**
   - Non-diagnostic messaging: "Understand what might be happening", never "Diagnose your condition".
   - Emergency callout card with `#fff1f2` background and `#9f1239` border/text.

3. **Consent Container (DR-08):**
   - Checkbox: Accessible custom checkbox with keyboard toggle (`Space`/`Enter`).
   - CTA Button: Disabled state with `aria-disabled="true"` until checkbox is checked; active state uses `#0f766e` with clear focus ring.

4. **Persistent Disclaimer Footer (DR-01):**
   - Fixed or sticky at bottom of viewport; minimum font size `13px` with high contrast `#475569` text on `#f8fafc`.
