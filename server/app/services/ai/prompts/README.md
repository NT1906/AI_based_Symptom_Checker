# AI Prompts Directory

**Owner:** Nishith (AI/ML Lead) · **Task:** S2-NIT-1 · **Requirements:** FR-03, FR-04, FR-17, FR-19, FR-20, NFR-05, NFR-07

This folder contains versioned, immutable prompt templates for the AI Symptom Understanding Engine.

## Versioning & Immutability Policy (AI_RULES.md §3.1)

1. **Prompts are immutable once merged.** Never edit an existing prompt file (e.g. `extraction.v1.txt` or `clarification.v1.txt`) after it is merged to `develop`.
2. **Create new versions for enhancements:** When refining prompts based on evaluation metrics or regression tests, create a new versioned file:
   - `clarification.v2.txt` (Sprint 1, Task S1-NIT-2: prioritized missing-information detection & 3-turn question cap)
   - `extraction.v2.txt` (Sprint 2, Task S2-NIT-1: multi-turn context resolution & eval-driven extraction improvements)
   - `extraction.v3.txt` (Sprint 3)
3. **Naming Convention:** `<purpose>.v<N>.txt` (e.g., `extraction.v1.txt`, `clarification.v1.txt`, `clarification.v2.txt`, `extraction.v2.txt`).
4. **Non-Diagnostic Framing:** Prompts must explicitly enforce that output is informational only, never diagnostic, and never prescribing.

## Current Prompts

| File | Purpose | Version | Task |
|---|---|---|---|
| `extraction.v1.txt` | Complete natural-language symptom extraction and clinical attribute parsing (symptom, severity, duration, onset, body site) | v1 | S1-NIT-1 |
| `extraction.v2.txt` | Multi-turn symptom extraction attributing standalone replies to target questions, with expanded Hinglish, misspelling, and emergency coverage | v2 | S2-NIT-1 |
| `clarification.v1.txt` | Targeted follow-up question generator baseline | v1 | S0-NIT-1 |
| `clarification.v2.txt` | Missing-information detection + targeted non-diagnostic clarification question generator (capped at 3 turns, safety priority ranking) | v2 | S1-NIT-2 |
