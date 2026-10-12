# Wireframe UX-05: Urgent Care & Red-Flag Alert Screen

> **Screen:** Urgent Care & Red-Flag Emergency Override  
> **Owner:** Mann · Reviewed by Dimple · **Requirements:** DR-02 (Red-Flag Override), FR-06, FR-15, NFR-06

---

## 1. Screen Purpose & Narrative

Triggered immediately when red-flag symptoms are identified (e.g. crushing chest pain, difficulty breathing, sudden stroke-like symptoms, anaphylaxis signs). It overrides all normal triage paths, dismisses lower-priority information, and displays the emergency contact number (**112**) first and foremost.

---

## 2. Desktop & Mobile Wireframe Layout

```text
┌────────────────────────────────────────────────────────────────────────┐
│ 🚨 EMERGENCY MEDICAL ALERT                                  [ Call 112 ]│
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                                                                │   │
│   │                 ⚠️ SEEK IMMEDIATE EMERGENCY CARE               │   │
│   │                                                                │   │
│   │   Based on the symptoms you reported, this may be a            │   │
│   │   life-threatening condition requiring urgent medical care.    │   │
│   │                                                                │   │
│   │   ┌────────────────────────────────────────────────────────┐   │   │
│   │   │                                                        │   │   │
│   │   │                  📞 CALL 112 NOW                       │   │   │
│   │   │             National Emergency Number                  │   │   │
│   │   │                                                        │   │   │
│   │   └────────────────────────────────────────────────────────┘   │   │
│   │                                                                │   │
│   │   [ 🏥 Find Nearest Emergency Room (Hospital Map) 🗺️ ]         │   │
│   │                                                                │   │
│   │   Identified Red-Flag Symptom:                                 │   │
│   │   • Severe chest tightness with radiation to left arm          │   │
│   │                                                                │   │
│   │   CRITICAL ADVICE:                                             │   │
│   │   • Do not attempt to drive yourself to the hospital.          │   │
│   │   • Stay seated and rest quietly while awaiting emergency aid. │   │
│   │   • If someone is with you, alert them immediately.            │   │
│   │                                                                │   │
│   └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│   [ Start Over (If entered by mistake) ]                               │
│                                                                        │
├────────────────────────────────────────────────────────────────────────┤
│ ⚖️ PERSISTENT DISCLAIMER (DR-01):                                      │
│ This system is an informational tool only. In any emergency situation, │
│ call 112 immediately or go to the nearest emergency department.        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. UI Component Specifications

1. **High-Visibility Emergency Callout (DR-02):**
   - Full-bleed or high-contrast red container (`bg-rose-600 text-white` or `bg-rose-50 border-2 border-rose-600`).
   - Emergency CTA button: Extra-large touch target (`min-h-16 w-full text-2xl font-bold bg-rose-600 hover:bg-rose-700 text-white rounded-xl shadow-lg`).
   - Links directly to `tel:112`.

2. **Hospital Search Secondary Action:**
   - External map search trigger: "Find Nearest Emergency Room" with geo-intent query `https://maps.google.com/?q=emergency+room+hospital+near+me`.

3. **Accessibility Attributes:**
   - Role: `role="alert"` and `aria-live="assertive"` to immediately notify screen-reader users of urgent danger.
