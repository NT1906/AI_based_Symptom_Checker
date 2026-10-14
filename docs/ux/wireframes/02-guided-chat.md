# Wireframe UX-02: Guided Chat & Symptom Entry Screen

> **Screen:** Conversational Symptom Intake  
> **Owner:** Mann · Reviewed by Rutva · **Requirements:** idea §1, §2, §3, §5, FR-03, FR-19

---

## 1. Screen Purpose & Narrative

The core interactive experience. The user describes symptoms in natural, layperson language. The bot responds conversationally, acknowledges reported symptoms, asks targeted clarifying questions (capped strictly at 3 turns), and conditionally offers image upload if visible symptoms are detected.

---

## 2. Desktop & Mobile Wireframe Layout

```text
┌────────────────────────────────────────────────────────────────────────┐
│ [← Exit] Symptom Assessment                  [ Start Over ] [ Call 112 ]│
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ 🤖 AI Assistant                                        09:30 AM│   │
│   │ Hello. What symptoms are you experiencing today? Please        │   │
│   │ describe what you are feeling in your own words.               │   │
│   └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│                                  ┌─────────────────────────────────┐   │
│                                  │ 👤 You                  09:31 AM│   │
│                                  │ I've had a bad headache and     │   │
│                                  │ throbbing pain since yesterday. │   │
│                                  └─────────────────────────────────┘   │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ 🤖 AI Assistant                                        09:31 AM│   │
│   │ I understand you have a headache with throbbing pain.          │   │
│   │                                                                │   │
│   │ Clarification (Turn 1 of 3):                                   │   │
│   │ Are you also experiencing any sensitivity to light, nausea,    │   │
│   │ or neck stiffness?                                             │   │
│   └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ 📷 Visual Symptom Option (Situational)                         │   │
│   │ If you also have a visible rash or skin symptom, you may       │   │
│   │ [ 📎 Attach Photo ] (optional, processed in-memory only)       │   │
│   └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ [Type your response here...]                   [ 📎 ] [ Send ➤ ]│   │
│   └────────────────────────────────────────────────────────────────┘   │
│   (Turn 1/3 • Capped at 3 follow-ups to respect your time)             │
│                                                                        │
├────────────────────────────────────────────────────────────────────────┤
│ ⚖️ PERSISTENT DISCLAIMER (DR-01):                                      │
│ This is not a medical diagnosis. Always consult a healthcare           │
│ professional. If you experience severe distress or red flags, call 112.│
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. UI Component Specifications

1. **Top Bar Actions:**
   - "Start Over" button with confirmation modal (FR-25).
   - Emergency quick-dial button (`tel:112`).

2. **Message List & Accessibility:**
   - Role container: `role="log"` with `aria-live="polite"` so screen readers announce incoming bot responses.
   - User messages aligned right (`bg-teal-700 text-white rounded-2xl`).
   - Bot messages aligned left (`bg-white border border-slate-200 text-slate-900 rounded-2xl`).

3. **Clarification Counter Badge:**
   - Clear visual indicator: "Question 1 of 3", preventing endless conversational loops.

4. **Situational Image Upload (idea §3):**
   - Triggered only when skin or external visual symptoms are extracted.
   - Explicit disclaimer that images are never stored or logged (DR-06).

5. **Input Box & Controls:**
   - Multi-line accessible `textarea` with auto-expand up to 4 lines.
   - Keyboard shortcut: `Enter` to send, `Shift+Enter` for newline.
