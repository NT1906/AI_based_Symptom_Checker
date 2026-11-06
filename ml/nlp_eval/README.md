# NLP extraction evaluation cases & harness

**Owner:** Kavya (AI/ML, Database) · **Tasks:** S1-KAV-2, S2-KAV-2 · **Requirements:** NFR-07, FR-03, FR-19

Benchmark cases and evaluation harness for measuring symptom-extraction precision, recall, and F1 across canonical symptoms, explicit severity ratings, duration normalization, and linguistic subgroups.

| Read by | For |
|---|---|
| NLP eval harness (`evaluate.py`) | Computing precision, recall and F1 reports across test cases |
| Prompt engineering (S2-NIT-1, Nishith) | Regression testing and target recommendations for prompt v2 |
| Quality assurance (S2-MOH-4, Mohit) | Baseline NLP benchmark verification |

---

## 1. Case format (`cases.json`)

`cases.json` (schema version `1.0`, dataset version `2.0`):

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
  "notes": "Tests 'bad headache' → severity SEVERE, 'throwing up' → nausea",
  "tags": ["standard"]
}
```

### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique case identifier (`case_NNN`, `case_001` – `case_100`) |
| `input` | string | yes | Raw user text as entered (English, Hinglish, or misspelled) |
| `expected.symptoms` | object[] | yes | Canonical symptoms the extractor should find |
| `expected.symptoms[].id` | string | yes | Canonical symptom ID from `ml/datasets/symptoms/symptoms.json` |
| `expected.symptoms[].severity` | string | no | `MILD`, `MODERATE` or `SEVERE` — omit if not inferable |
| `expected.duration` | string | no | Normalized duration (e.g., `"1 day"`, `"3 days"`, `"1 week"`) |
| `notes` | string | yes | Specific clinical and NLP extraction challenge tested |
| `tags` | string[] | no | Category tags (`standard`, `hinglish`, `misspelling`, `red_flag`, `multi_symptom`) |

### Severity rules

- `SEVERE`: "really bad", "worst ever", "extreme", "unbearable", "severe", "tez", "bahut", "bohot tez"
- `MODERATE`: "quite", "noticeable", "moderate", "significant"
- `MILD`: "slight", "mild", "a little", "minor", "thoda", "halka"
- Omit severity when the user does not indicate intensity.

---

## 2. Dataset coverage (v2, 100 cases)

The v2 benchmark includes 100 diverse cases covering 100% of the canonical symptoms in `symptoms.json`:

| Dimension | Count | Details |
|---|---|---|
| **Total cases** | 100 | `case_001` through `case_100` |
| **Canonical vocabulary coverage** | 100 / 100 | All 100 clinical symptoms represented in benchmark expectations |
| **Multi-symptom (3+ symptoms)** | 46 | Complex multi-system complaints testing co-occurrence extraction |
| **With normalized duration** | 31 | Temporal durations ("1 hour", "1 day", "3 days", "2 weeks", "1 month") |
| **With explicit severity** | 31 | Explicit mild, moderate, and severe markers |
| **Transliterated Hinglish** | 28 | Indian linguistic patterns ("sir me dard", "pet saaf nahi", "dast lag gaye") |
| **Misspelled / colloquial input** | 30 | Phonetic typos ("naucea", "dizzynes", "blured vission", "stomake aking") |
| **Emergency red flags** | 31 | Stroke (FAST), meningitis, cauda equina, GI bleed, psychiatric emergencies |

---

## 3. Evaluation harness (`evaluate.py`)

The evaluation script `evaluate.py` is standalone ML code (no server dependencies) that runs test cases through any implementation satisfying the `Extractor` protocol and produces precision, recall, and F1 reports.

### Per-field evaluation metrics (NFR-07)

1. **Canonical Symptoms:** Micro- and Macro-averaged Precision, Recall, and F1 at the symptom ID level.
2. **Severity Rating:** Accuracy and F1 score for matching severity ratings on true positive symptoms.
3. **Duration Normalization:** Precision, recall, and match accuracy on extracted temporal expressions.
4. **Linguistic Subgroups:** Granular performance breakdowns across `standard`, `hinglish`, `misspelling`, `red_flag`, and `multi_symptom` subsets.

### Running the evaluation

Default run (all 100 cases with baseline extractor and per-field report):

```bash
python ml/nlp_eval/evaluate.py
```

Generate Markdown report feeding S2-NIT-1:

```bash
python ml/nlp_eval/evaluate.py --report ml/nlp_eval/report_v2.md
```

Export detailed metrics to JSON:

```bash
python ml/nlp_eval/evaluate.py --json ml/nlp_eval/results.json
```

Verbose per-case breakdown:

```bash
python ml/nlp_eval/evaluate.py --verbose
```

---

## 4. Testing

The evaluation harness and dataset are verified by unit and integration tests:

```bash
python -m pytest ml/nlp_eval/
```

- `test_cases.py`: Schema validation, 100-case count, 100% vocabulary parity, severity and duration checks.
- `test_evaluate.py`: Per-field metrics, duration and severity scoring, subgroup aggregation, protocol conformance, and CLI options.
