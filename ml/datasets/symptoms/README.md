# Symptom vocabulary v0 (dataset card)

**Owner:** Kavya (AI/ML, Database) · **Task:** S0-KAV-1 · **Requirements:** FR-03

Canonical symptom vocabulary for the AI-Based Symptom Checker. Maps lay terms (natural-language phrases users actually type) to canonical symptom IDs so that extraction, normalization and prediction all speak the same language.

| Read by | For |
|---|---|
| Symptom normalizer (S1-KAV-1) | Deterministic lay-term → canonical-ID lookup |
| NLP eval harness (S1-KAV-2) | Expected symptoms in evaluation cases use these IDs |
| Symptom glossary (S1-KAV-3) | Definitions keyed by these IDs |
| AI extraction prompts (S1-NIT-1) | Output schema uses these IDs |
| Condition predictor (S1-NIS-1) | Input symptoms use these IDs |

## Intended use and limits

- **Informational triage only.** This vocabulary powers a triage aid, not a diagnostic tool.
- **Aligned with the condition dataset.** The 100 symptom IDs, display names and body systems are copied from `conditions.json` (S0-NIS-1). If that file changes, this file must be updated to match.
- **Lay terms are not exhaustive.** They cover common English and Hinglish (Hindi–English) phrases. The normalization service (S1-KAV-1) may add fuzzy matching later, but the initial lookup is deterministic.
- **No medical jargon as primary.** Lay terms are what a user would type, not clinical terms. Clinical synonyms are included only when commonly used by patients (e.g., "acidity" for heartburn).
- **Hinglish terms are transliterated.** Hindi terms are written in Latin script as an Indian user would type them on a phone keyboard.

## Contents

`symptoms.json` (schema version `1.0`, dataset version `v0`):

| Field | Type | Description |
|---|---|---|
| `schema_version` | string | Schema version for forward compatibility |
| `dataset_version` | string | Dataset revision (`v0`, `v1`, …) |
| `intended_use` | string | What this data is for and what it is not |
| `body_systems` | string[] | Every body system used (enum) |
| `symptoms` | object[] | The 100 canonical symptoms |

Each symptom object:

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique `snake_case` identifier, matching `conditions.json` |
| `name` | string | Display name, identical to `conditions.json` |
| `body_system` | string | Body system, identical to `conditions.json` |
| `lay_terms` | string[] | Lay-language synonyms the normalizer will match against |

### Lay-term design decisions

1. **Case-insensitive matching.** The normalizer lowercases both the user input and the lay terms before comparison.
2. **Hinglish included.** Indian users often mix Hindi and English (e.g., "pet me dard" for abdominal pain, "bukhar" for fever). These transliterations use the most common Romanization.
3. **No ambiguity.** A lay term may map to at most one symptom. If a phrase is genuinely ambiguous (e.g., "pain" without context), it is not listed; the clarification loop handles it instead.
4. **Substrings are not matches.** "head" does not match "headache". The normalizer must match the complete lay term as a phrase within the user's text.

## Validating changes

Run this after every edit. CI runs the same checks through `pytest`.

```bash
python ml/datasets/symptoms/validate_symptoms.py     # prints "OK (...)" or every problem found
cd ml && ruff check . && pytest
```

The validator (`validate_symptoms.py`) checks that:

- IDs are unique snake_case and every ID exists in `conditions.json`.
- Every symptom from `conditions.json` is present (coverage).
- Names and body systems match `conditions.json` exactly.
- Lay terms are non-empty strings.
- No lay term maps to more than one symptom (ambiguity check).

## Sources

- Lay terms were sourced from NHS Health A to Z patient-facing pages (the "Symptoms" sections use plain English).
- Hinglish terms were sourced from common Indian health forums and transliterated.
- All terms were reviewed for medical-safety compliance (no diagnostic language).

## Open questions for later tasks

- **Fuzzy matching (S1-KAV-1):** The normalizer may add Levenshtein-distance or stemming-based matching for misspellings, but the initial version is exact phrase matching.
- **Hinglish eval cases (S2-KAV-2):** The v2 evaluation set will include Hinglish and misspelled inputs to test the normalizer's coverage.
- **Vector retrieval (S2-NIS-7):** If deterministic normalization misses too many eval cases, semantic matching may be added as a fallback.
