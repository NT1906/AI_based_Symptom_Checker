# UX Foundation & Screen Wireframes

> **Task:** S0-MAN-1 · **Owner:** Mann (Frontend + Deployment · Testing)  
> **Requirements:** DR-01 (Mandatory Persistent Medical Disclaimer), NFR-06 (Accessibility & WCAG 2.1 AA Compliance)

---

## 1. Overview & Experience Principles

The AI-Based Symptom Checker is an **informational triage aid, not a diagnostic or prescribing authority** (`docs/idea.md` §0).  
The user experience must balance four non-negotiable principles:

1. **Immediate Safety Framing (DR-01, DR-02):** Every screen clearly indicates that the tool is not a medical diagnosis. Red-flag symptoms and emergencies prioritize the emergency contact number (**112**) above all conversational actions.
2. **Conversational Low-Friction Intake (idea §1, §2):** Users are not overwhelmed by complex medical intake forms. Symptoms are collected step by step in plain language.
3. **Transparency & User Control (idea §4, FR-16, FR-21):** Users inspect and edit what the system extracted before any analysis or triage decisions are calculated.
4. **Accessible by Design (NFR-06, WCAG 2.1 AA):** High-contrast color choices (≥ 4.5:1 text, ≥ 3:1 graphical elements), semantic landmark HTML, keyboard-navigable interactive controls, and `aria-live` screen-reader announcements for chat updates.

---

## 2. Screen Inventory & Journey Map

```text
[01. Landing & Consent Screen]
             │
             ▼ (Explicit Consent Granted)
[02. Guided Chat & Symptom Entry] ──(Red-flag detected)──► [05. Urgent Alert Screen (112)]
             │
             ▼ (Max 3 clarification turns completed)
[03. Symptom Confirmation & Editing]
             │
             ▼ (User confirms symptoms)
[04. Result & Triage Screen] ──(Elevated risk specialty)──► [06. Doctor Referral via Map]
             │
             ▼ (Always available)
    [Start New Assessment]
```

### Detailed Wireframes

| Screen ID | File | Description | Core Requirements |
|---|---|---|---|
| **UX-01** | [01-landing-and-consent.md](wireframes/01-landing-and-consent.md) | Initial landing page with medical disclaimer and plain-language consent modal. | DR-01, DR-08, idea §12 |
| **UX-02** | [02-guided-chat.md](wireframes/02-guided-chat.md) | Conversational symptom intake, clarifying follow-up questions, and optional image upload. | idea §1, §2, §3, §5, FR-03, FR-19 |
| **UX-03** | [03-symptom-confirmation.md](wireframes/03-symptom-confirmation.md) | Structured card displaying extracted symptoms with edit/remove/add controls. | idea §4, FR-16, FR-21 |
| **UX-04** | [04-result-and-triage.md](wireframes/04-result-and-triage.md) | Risk badge, top matched conditions with qualitative confidence, self-care, and "why" panel. | idea §6, §7, §8, FR-22, FR-23, FR-24 |
| **UX-05** | [05-urgent-alert-112.md](wireframes/05-urgent-alert-112.md) | Full-screen red-flag emergency alert showing **112** first and immediate actions. | DR-02, FR-06, FR-15 |
| **UX-06** | [06-doctor-referral-map.md](wireframes/06-doctor-referral-map.md) | External map search modal launching specialist search without storing doctor data. | idea §9, FR-08 |
| **UX-07** | [07-offline-and-error.md](wireframes/07-offline-and-error.md) | PWA offline fallback banner and graceful error recovery with emergency phone numbers. | NFR-05, NFR-09 |

---

## 3. Design Tokens & Theme Specification

See [design-tokens.md](design-tokens.md) for full token definitions, including:
- **Color Palettes:** Deep Healthcare Teal (`#0f766e`), Slate neutrals, and semantic Risk Tiers (Emerald for Self-Care, Amber for Consult Doctor, Rose for Urgent Care).
- **Typography:** Inter / system font scale with accessible line heights.
- **Spacing:** 4px baseline grid (`space-1` through `space-16`).
- **Elevation:** Tailwind-compatible elevation shadows with soft ambient falloff.
- **Accessibility:** Color-contrast audit table proving WCAG 2.1 AA compliance.
