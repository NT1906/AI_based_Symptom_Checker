# Safety and Medical Disclaimer Audit Report

> **Owner:** Dimple (Frontend + Deployment · Database)  
> **Task:** S2-DIM-6 · **Issue:** #221  
> **Requirements:** DR-01 (Mandatory Persistent Medical Disclaimer), DR-05 (Clinical Risk Framing & Non-Diagnostic Invariants), DR-02 (Red-Flag Emergency Override), DR-08 (Affirmative Informed Consent)  
> **Date:** November 2026  
> **Target Application:** AI-Based Symptom Checker Web Application & PWA (`client/`)  

---

## 1. Executive Summary & Purpose

The **AI-Based Symptom Checker** is designed and operated strictly as an **informational health-triage aid and clinical decision-support tool**, never as a diagnostic or prescribing authority (DR-01, DR-05, AI_RULES.md §2). In healthcare software, inaccurate framing, diagnostic promises, or medication dosing can directly cause patient harm, delayed care, or fatal consequences.

This report documents the **Final Safety and Medical Disclaimer Audit** conducted across every user-facing string, component, screen, and error state in the frontend application before the Sprint 2 release. 

The audit certifies that:
1. **Zero Diagnostic Claims:** No string asserts that the user has a specific condition, illness, or disease. All outputs are strictly framed as informational suggestions, possibilities, or candidate matches.
2. **Zero Prescription / Drug Advice:** No drug brand names, active pharmaceutical ingredients, or medication dosages (e.g., paracetamol, ibuprofen, antibiotic dosages) are recommended.
3. **Mandatory Persistent Disclaimer (DR-01):** The non-diagnostic medical disclaimer appears prominently and persistently on every single screen, layout, dialog, and result view.
4. **Emergency Prioritization (DR-02):** National emergency hotline **112 (Unified Emergency)** is always displayed first and largest, followed by **108 (Ambulance)**.
5. **Affirmative Informed Consent (DR-08) & DPDP Act 2023:** Users are explicitly notified of ephemeral data processing and must affirmatively consent before any assessment data is stored.

---

## 2. Medical Safety Invariants Checklist (AI_RULES.md §2)

| Invariant ID | Safety Rule | Governing Spec | Audit Status | Implementation Mechanism |
|---|---|---|---|---|
| **SAFE-01** | **Zero Diagnostic Claims** | DR-01, DR-05 | **PASS** | Triage framing only ("Possible matches", "Candidate conditions", "Clinical triage aid"). Never "You have X" or "Diagnosed with X". |
| **SAFE-02** | **Zero Prescriptions / Dosing** | DR-05 | **PASS** | Only non-prescriptive supportive advice (rest, hydration, monitoring). Zero drug names or mg dosages. |
| **SAFE-03** | **Mandatory Persistent Disclaimer** | DR-01 | **PASS** | Persistent footer on `AppLayout`, explicit disclaimer card on `LandingPage`, `ResultPage`, `UrgentCareAlert`, and `ConsentStep`. |
| **SAFE-04** | **Emergency Escalation (112 First)** | DR-02 | **PASS** | In urgent cases and headers, `112` is displayed first and most prominently, with `108` secondary. |
| **SAFE-05** | **Zero Image Persistence** | DR-06, idea §3 | **PASS** | Images processed in-memory only; EXIF stripped; never stored to disk, DB, logs, or cloud storage. |
| **SAFE-06** | **Qualitative Risk Confidence** | DR-05, FR-22 | **PASS** | Uses qualitative labels (`Likely`, `Possible`, `Less likely`). Never raw diagnostic percentages to patients. |
| **SAFE-07** | **Affirmative Consent Gating** | DR-08, DPDP 2023 | **PASS** | Hard gate: user must accept `ConsentStep` before session initialization or assessment message persistence. |
| **SAFE-08** | **High-Uncertainty Escalation** | DR-02, idea §8 | **PASS** | If prediction uncertainty is elevated (>60%), risk automatically escalates to `CONSULT_DOCTOR`. |

---

## 3. Screen-by-Screen String Inventory & Audit Matrix

Every user-facing screen and reusable component was inspected for compliance with DR-01, DR-02, and DR-05:

| Screen / Component | File Path | User-Facing Text Excerpt | Compliance Analysis | Status |
|---|---|---|---|---|
| **Landing Page Header** | `LandingPage.tsx` | "AI Symptom Checker · Informational Triage Aid · DPDP Act 2023 Compliant" | Clearly states informational aid role; displays 112 emergency action | **PASS** |
| **Landing Page Hero** | `LandingPage.tsx` | "Free · 3-minute check · Non-diagnostic clinical aid" | Upfront non-diagnostic framing before user interaction | **PASS** |
| **Landing Page Disclaimer Card** | `LandingPage.tsx` | "This tool is not a medical diagnosis, prescription, or substitute for professional medical advice... Always consult a doctor." | High-contrast callout card (DR-01) with 112/108 emergency numbers | **PASS** |
| **Landing Page Footer** | `LandingPage.tsx` | "This is not a medical diagnosis. Always consult a qualified healthcare professional. Emergency: 112 · 108" | Persistent disclaimer at bottom of page | **PASS** |
| **Consent Agreement Dialog** | `ConsentStep.tsx` | "This tool provides general health information only. It is NOT a medical diagnosis, prescription, or professional medical advice." | Explicit affirmative consent terms required before storage (DR-08) | **PASS** |
| **Chat Welcome Message** | `ChatContainer.tsx` | "Tell me what you're experiencing, and I'll help you organize the information." | Organizational framing; does not promise diagnosis or cure | **PASS** |
| **Chat Offline Alert** | `ChatContainer.tsx` | "You're offline. If this is an emergency, call 112." | Emergency escalation cue when connectivity is interrupted | **PASS** |
| **Symptom Confirmation** | `SymptomConfirmationCard.tsx` | "This is not a medical diagnosis. Confirmation is used to organize informational suggestions only." | Inline disclaimer reminder during clarification step | **PASS** |
| **Triage Result Header** | `ResultPage.tsx` | "Informational Triage Guidance (DR-01) · Clinical Decision Support" | Explicit non-diagnostic framing above candidate conditions | **PASS** |
| **Candidate Conditions** | `ConditionList.tsx` | "Matches reported symptom pattern. This is a suggestion, not a diagnosis." | Qualitative confidence tiers (`Likely`, `Possible`, `Less likely`) without diagnostic certainty | **PASS** |
| **Doctor Referral** | `DoctorReferral.tsx` | "Specialist Recommendation · Search for nearby specialists on an external map. We do not store doctor directories." | External map search only (idea §9); no doctor database | **PASS** |
| **Low-Risk Guidance** | `SelfCareGuidanceCard.tsx` | "A low-risk assessment indicates supportive care is reasonable, but low risk does not mean zero risk. Never ignore professional medical advice." | Supportive care only (rest, hydration, monitoring); zero drug dosing | **PASS** |
| **Urgent Care Alert** | `UrgentCareAlert.tsx` | "Urgent Care Needed · 112 Unified Emergency (Police · Fire · Ambulance) · 108 Ambulance" | 112 first and largest (DR-02); non-diagnostic framing | **PASS** |
| **Global App Layout** | `AppLayout.tsx` | "This application is an informational triage aid and does not provide a medical diagnosis or treatment plan. Always consult a qualified healthcare professional." | Persistent global footer on every application screen | **PASS** |
| **Profile Page** | `ProfilePage.tsx` | "Optional Profile Information · This tool provides informational guidance, not a medical diagnosis." | Minimal data collection (coarse age bands); disclaimer present | **PASS** |
| **Privacy Policy Page** | `PrivacyPolicyPage.tsx` | "Statutory Privacy Notice (DPDP Act 2023) · This is not a medical diagnosis. Data processed ephemerally." | Comprehensive statutory rights and erasure options (DR-06) | **PASS** |

---

## 4. Prohibited Keyword & Pattern Verification

An automated static analysis and dynamic DOM regex scan was executed across all user-facing code in `client/src/`:

| Prohibited Pattern | Intent | Occurrences Found | Action Taken |
|---|---|---|---|
| `/(you have|diagnosed with|our diagnosis|we diagnose)\s+[a-z]+/i` | Prevent affirmative diagnostic assertions | **0** | Verified clean. All occurrences of "diagnosis" are in non-diagnostic disclaimers. |
| `/(prescribe|prescription for|dosage of|take \d+\s*(mg|ml|tablets?))/i` | Prevent illegal drug prescription or dosing | **0** | Verified clean. No medication dosing exists in frontend code. |
| `/(guaranteed cure|will cure|promises? full recovery)/i` | Prevent false medical efficacy claims | **0** | Verified clean. |
| `/(emergency|ambulance).*(108.*112)/i` | Ensure 108 is never prioritized over 112 | **0** | Verified clean. 112 is always first and largest per DR-02. |

---

## 5. Automated Safety Test Suite (`safetyWording.test.ts`)

To prevent future regressions, an automated safety test suite is permanently integrated into the client test pipeline:
- **Location:** `client/src/test/safetyWording.test.ts`
- **Assertions:**
  1. Validates that `MANDATORY_DISCLAIMER_TEXT` in `AppLayout` contains both "not provide a medical diagnosis" and emergency hotline references.
  2. Validates that `ConsentStep` contains verbatim non-diagnostic and non-prescribing terms.
  3. Validates that `SelfCareGuidanceCard` fallback advice contains only safe supportive care (rest, hydration, observation) and zero drug prescriptions.
  4. Validates that `UrgentCareAlert` displays `112` as the primary number and `108` as secondary.
  5. Scans all candidate condition sample datasets to ensure plain-language "why" rationales frame findings as suggestions, not diagnoses.

---

## 6. Conclusion & Release Sign-Off

The final safety and disclaimer audit confirms **100% compliance** with **DR-01**, **DR-05**, **DR-02**, **DR-08**, and **AI_RULES.md §2**. The AI-Based Symptom Checker frontend communicates risk with clinical prudence, enforces transparent disclaimers, prioritizes emergency safety, and avoids all diagnostic overreach.
