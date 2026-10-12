# Wireframe UX-07: Offline & Error States

> **Screen:** PWA Offline Fallback & Graceful Error Recovery  
> **Owner:** Mann · Reviewed by Rutva · **Requirements:** NFR-05 (Resilience), NFR-09 (PWA Capabilities), DR-02

---

## 1. Screen Purpose & Narrative

When the client loses network connectivity or the backend API encounters transient errors, the application must never leave the user confused or stranded with an incomplete medical flow. The offline screen serves the cached app shell, warns that fresh analysis is paused, and provides immediate emergency numbers.

---

## 2. Desktop & Mobile Wireframe Layout

```text
┌────────────────────────────────────────────────────────────────────────┐
│ [Logo] AI-Based Symptom Checker                  [ Emergency: Call 112 ]│
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ ⚡ NO INTERNET CONNECTION DETECTED                             │   │
│   │ You are currently offline. Live symptom analysis requires an   │   │
│   │ active internet connection.                                    │   │
│   │                                                                │   │
│   │ 🚨 EMERGENCY REMINDER:                                         │   │
│   │ If this is a medical emergency, do not wait for internet       │   │
│   │ connectivity. Call 112 immediately.                           │   │
│   │                                                                │   │
│   │                      [ 📞 CALL 112 NOW ]                       │   │
│   │                                                                │   │
│   │ ────────────────────────────────────────────────────────────── │   │
│   │                                                                │   │
│   │ [ 🔄 Check Connection & Retry ]                                │   │
│   │ (Your ongoing assessment state is safely retained in memory)   │   │
│   └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
├────────────────────────────────────────────────────────────────────────┤
│ ⚖️ PERSISTENT DISCLAIMER (DR-01):                                      │
│ Offline mode runs using cached local resources. No health information  │
│ or API responses are stored on device storage. Call 112 in emergencies.│
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. UI Component Specifications

1. **Offline Indicator Banner:**
   - Visual: Alert pill fixed at the top of the viewport when `navigator.onLine === false`.
   - Text: "You're offline. If this is an emergency, call 112."
   - Accessibility: `role="status"` with `aria-live="polite"`.

2. **Retry Mechanism:**
   - Button triggering connection probe to `/api/v1/health`.
   - Automatic resume when window triggers `online` event.
