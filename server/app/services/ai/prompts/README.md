# AI Prompts Directory

**Owner:** Nishith (AI/ML Lead) · **Task:** S1-NIT-1 · **Requirements:** FR-03, FR-17, NFR-05, NFR-07

This folder contains versioned, immutable prompt templates for the AI Symptom Understanding Engine.

## Versioning & Immutability Policy (AI_RULES.md §3.1)

1. **Prompts are immutable once merged.** Never edit an existing prompt file (e.g. `extraction.v1.txt`) after it is merged to `develop`.
2. **Create new versions for enhancements:** When refining prompts based on evaluation metrics or regression tests, create a new versioned file:
   - `extraction.v2.txt` (Sprint 2, Task S2-NIT-1)
   - `extraction.v3.txt` (Sprint 3)
3. **Naming Convention:** `<purpose>.v<N>.txt` (e.g., `extraction.v1.txt`, `clarification.v1.txt`).
4. **Non-Diagnostic Framing:** Prompts must explicitly enforce that output is informational only, never diagnostic, and never prescribing.

## Current Prompts

| File | Purpose | Version | Task |
|---|---|---|---|
| `extraction.v1.txt` | Complete natural-language symptom extraction and clinical attribute parsing (symptom, severity, duration, onset, body site) | v1 | S1-NIT-1 |
| `clarification.v1.txt` | Targeted follow-up question generator (capped at 3 turns) | v1 | S0-NIT-1 |

