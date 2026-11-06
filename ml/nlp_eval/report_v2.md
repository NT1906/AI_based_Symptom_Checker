# NLP Extraction Benchmark Report (Eval Set v2)

**Owner:** Kavya (AI/ML, Database) · **Task:** S2-KAV-2 · **Target Consumer:** Nishith (S2-NIT-1, Prompt v2) · **Requirement:** NFR-07

This evaluation report benchmarks the symptom extraction baseline over the expanded 100-case evaluation set, establishing quantitative baseline metrics across canonical symptom extraction, explicit severity detection, duration normalization, and linguistic subgroups.

---

## 1. Executive Summary

- **Total Benchmark Cases:** 100
- **Canonical Vocabulary Coverage:** 100/100 symptoms represented (100% parity)
- **Micro-averaged Symptom F1:** 0.4264 (Precision: 0.7978, Recall: 0.2910)
- **Macro-averaged Symptom F1:** 0.3392 (Precision: 0.4908, Recall: 0.2757)
- **Severity Match Accuracy:** 0.3548 (11/31)
- **Duration Match Accuracy:** 1.0000 (31/31)

---

## 2. Per-Field Performance Breakdown

| Evaluation Field | Expected | Matched | Precision | Recall | F1 Score | Accuracy |
|---|---|---|---|---|---|---|
| **Canonical Symptoms** | 244 | 71 | 0.7978 | 0.2910 | 0.4264 | N/A |
| **Severity Rating** | 31 | 11 | 0.2973 | 0.3548 | 0.3235 | 0.3548 |
| **Duration Normalization** | 31 | 31 | 0.9688 | 1.0000 | 0.9841 | 1.0000 |

---

## 3. Linguistic Subgroup Performance

| Subgroup | Cases | Micro Prec | Micro Recall | Micro F1 | Macro F1 |
|---|---|---|---|---|---|
| `standard` | 45 | 0.8182 | 0.3495 | 0.4898 | 0.4044 |
| `hinglish` | 28 | 0.8000 | 0.3544 | 0.4912 | 0.4126 |
| `misspelling` | 30 | 0.7692 | 0.1429 | 0.2410 | 0.1675 |
| `red_flag` | 31 | 0.6667 | 0.2857 | 0.4000 | 0.2825 |
| `multi_symptom` | 46 | 0.8621 | 0.3521 | 0.5000 | 0.4330 |

---

## 4. Key Findings & Recommendations for S2-NIT-1 (Prompt v2)

### 4.1 Misspellings and Phonetic Typos
- **Issue:** Baseline keyword matching suffers significant recall drops on common patient misspellings (`naucea`, `dizzynes`, `blured vission`, `stomake aking`, `confution`, `droopin face`).
- **Recommendation for Prompt v2:** The LLM prompt should explicitly state: *'Correct common misspellings, colloquial slang, and typos into standard clinical concepts.'*

### 4.2 Hinglish & Transliterated Idiomatic Descriptions
- **Issue:** Lay phrases like *'pet saaf nahi hua'* (constipation), *'dast lag gaye'* (diarrhea), *'sans phoolna'* (shortness of breath), and *'seene me jakdan'* (chest tightness) require cultural and bilingual semantic context.
- **Recommendation for Prompt v2:** Include few-shot Hinglish examples in prompt v2 demonstrating transliterated Hindi clinical mappings.

### 4.3 Red-Flag Syndrome Groupings
- **Issue:** Stroke (FAST triad), Meningitis (stiff neck + fever + altered mental state), and Cauda Equina (saddle numbness + bowel/bladder incontinence) presentations must extract every constituent red-flag symptom without dropping subtle co-occurrences.
- **Recommendation for Prompt v2:** Instruct the model to avoid truncating symptoms when multiple emergency indicators appear in a single passage.

### 4.4 Duration Normalization Invariants
- **Issue:** Ambiguous phrases like *'since yesterday'* vs *'24 hours'* should map consistently to standardized durations (e.g. `'1 day'`).
- **Recommendation for Prompt v2:** Provide clear normalization guidelines for temporal expressions.
