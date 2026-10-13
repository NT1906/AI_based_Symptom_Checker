# NLP extraction evaluation cases

**Owner:** Kavya (AI/ML, Database) · **Task:** S0-KAV-1 · **Requirements:** FR-03

Benchmark cases for evaluating the symptom-extraction pipeline. Each case pairs a realistic user input with the expected canonical symptoms the extractor should produce.

| Read by | For |
|---|---|
| NLP eval harness (S1-KAV-2, `evaluate.py`) | Computing precision, recall and F1 |
| Prompt engineering (S2-NIT-1, Nishith) | Regression testing when prompts change |
| Eval set v2 (S2-KAV-2) | Expanding to 100 cases with Hinglish and misspellings |

## Case format

`cases.json` (schema version `1.0`):

```json
{
  "id": "case_001",
  "input": "I've had a really bad headache and feel like throwing up since yesterday",
  "expected": {
    "symptoms": [
      { "id": "headache", "severity": "SEVERE" },
      { "id": "nausea" }
    ],
    "duration": "1 day"
  },
  "notes": "Tests 'bad headache' → severity SEVERE, 'throwing up' → nausea"
}
```

### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique case identifier (`case_NNN`) |
| `input` | string | yes | Raw user text as they would type it |
| `expected.symptoms` | object[] | yes | Canonical symptoms the extractor should find |
| `expected.symptoms[].id` | string | yes | Canonical symptom ID from `ml/datasets/symptoms/symptoms.json` |
| `expected.symptoms[].severity` | string | no | `MILD`, `MODERATE` or `SEVERE` — omit if not inferable from the text |
| `expected.duration` | string | no | Normalized duration (e.g., `"3 days"`, `"1 week"`) — omit if not mentioned |
| `notes` | string | no | Why this case exists and what it tests |

### Severity rules

- `SEVERE`: "really bad", "worst ever", "extreme", "unbearable", "severe", "tez", "bahut"
- `MODERATE`: "quite", "noticeable", "moderate", "significant"
- `MILD`: "slight", "mild", "a little", "minor", "thoda"
- Omit severity when the user does not indicate intensity.

## Current coverage (v0, 20 cases)

| Category | Cases | IDs |
|---|---|---|
| ENT / respiratory | 3 | 002, 006, 018 |
| General / systemic | 2 | 003, 008 |
| Cardiac emergency | 1 | 005 |
| Neurological / red flag | 1 | 015 |
| Gastrointestinal | 3 | 010, 011, 016 |
| Urinary | 2 | 009, 019 |
| Skin / dermatological | 2 | 007, 014 |
| Eye | 1 | 012 |
| Musculoskeletal | 1 | 020 |
| Hinglish input | 2 | 004, 020 |
| Multi-symptom (3+) | 8 | 002, 003, 005, 008, 009, 016, 017, 018 |
| With severity | 5 | 001, 004, 011, 015, 017 |
| With duration | 7 | 001, 002, 003, 006, 016, 017, 020 |
| Tropical / India-specific | 1 | 017 |

## Adding cases

1. Every symptom ID must exist in `ml/datasets/symptoms/symptoms.json`.
2. Case IDs are sequential (`case_021`, `case_022`, …).
3. Each case should test at least one specific extraction challenge (noted in `notes`).
4. Avoid identical symptom sets across cases — each case should add new coverage.
5. The target for S1-KAV-2 is 50 cases; S2-KAV-2 expands to 100.

## Running the evaluation

The eval harness does not exist yet (S1-KAV-2). When it does:

```bash
python ml/nlp_eval/evaluate.py    # prints precision, recall, F1
```
