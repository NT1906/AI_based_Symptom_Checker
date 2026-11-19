# Full AI Regression Run & Evaluation Report (Final Hardening)

**Owner:** Kavya (AI/ML, Database) · **Task:** S2-KAV-5 · **Requirement:** NFR-07 · **Target Issue:** #197

This report documents the final AI regression run across the complete symptom extraction, deterministic normalization, and symptom glossary pipeline. It benchmarks performance over the 100-case evaluation set (`cases.json`), verifying compliance with NFR-07 (Extraction F1 $\ge 85\%$, Normalization accuracy $\ge 90\%$, zero unreviewed glossary terms).

---

## 1. Executive Summary & Before/After Comparison

| Metric | S2-KAV-2 Baseline | S2-KAV-5 Final Post-Fixes | Delta | NFR-07 Target | Status |
|---|---|---|---|---|---|
| **Total Benchmark Cases** | 100 | 100 | — | 100 | Passed |
| **Canonical Vocabulary Parity** | 100 / 100 | 100 / 100 | 100% | 100% | Passed |
| **Micro-averaged Precision** | 0.7978 | **0.9782** | +18.04% | $\ge 85\%$ | Passed |
| **Micro-averaged Recall** | 0.2910 | **0.9180** | +62.70% | $\ge 85\%$ | Passed |
| **Micro-averaged F1 Score** | 0.4264 | **0.9471** | **+52.07%** | $\ge 85\%$ | **PASSED** |
| **Macro-averaged F1 Score** | 0.3392 | **0.9274** | +58.82% | $\ge 85\%$ | Passed |
| **Duration Normalization Acc.** | 1.0000 | **1.0000** | 0.00% | $\ge 90\%$ | Passed |
| **Severity Match Accuracy** | 0.3548 | **0.8387** | +48.39% | $\ge 80\%$ | Passed |
| **Glossary Terms Reviewed** | 100 / 100 | 100 / 100 | 100% | 100% | Passed |

---

## 2. Per-Field Performance Breakdown

| Evaluation Field | Expected | Matched | Precision | Recall | F1 Score | Accuracy |
|---|---|---|---|---|---|---|
| **Canonical Symptoms** | 244 | 224 | 0.9782 | 0.9180 | 0.9471 | 0.9180 |
| **Severity Rating** | 31 | 26 | 0.3514 | 0.8387 | 0.4952 | 0.8387 |
| **Duration Normalization** | 31 | 31 | 0.9688 | 1.0000 | 0.9841 | 1.0000 |

---

## 3. Linguistic Subgroup Performance

| Subgroup | Cases | Micro Prec | Micro Recall | Micro F1 | Macro F1 | Baseline F1 | Improvement |
|---|---|---|---|---|---|---|---|
| `standard` | 45 | 0.9783 | 0.8738 | **0.9231** | 0.8968 | 0.4898 | +43.33% |
| `hinglish` | 28 | 0.9744 | 0.9620 | **0.9682** | 0.9684 | 0.4912 | +47.70% |
| `misspelling` | 30 | 0.9851 | 0.9429 | **0.9635** | 0.9422 | 0.2410 | +72.25% |
| `red_flag` | 31 | 0.9697 | 0.9143 | **0.9412** | 0.9215 | 0.4000 | +54.12% |
| `multi_symptom` | 46 | 0.9852 | 0.9366 | **0.9603** | 0.9559 | 0.5000 | +46.03% |

---

## 4. Normalization & Glossary Verification

### 4.1 Canonical Symptom Normalization
- **Vocabulary Expansion:** Expanded `symptoms.json` from 602 lay terms to 1,083 lay terms (+481 curated colloquial terms, Hinglish transliterations, and phonetic misspellings).
- **Parity Guarantee:** Complete synchronization verified between `server/app/services/knowledge/data/symptoms.json` and `ml/datasets/symptoms/symptoms.json` with zero ambiguous duplicate terms across symptoms.
- **Deterministic Heuristics:** `SymptomNormalizer` enhanced with prefix/filler stripping (e.g., "i have ...", "feeling ...", "severe ..."), punctuation normalization, and greedy longest-span compound match extraction.

### 4.2 Symptom Glossary Hardening
- **Coverage:** 100/100 canonical symptoms have verified, clinically reviewed entries in `glossary.json`.
- **Zero Hallucination Guarantee:** Definitions and triage guidance are curated in static JSON, never generated on-the-fly by an LLM.
- **Safety Compliance:** Adheres strictly to `AI_RULES.md §2`:
  - No diagnostic claims ("You have...", "Diagnosis: ...").
  - No medication prescriptions, drug dosages, or therapeutic guarantees.
  - Clear emergency guidance advising clinical healthcare evaluation.

---

## 5. Regression Suite Quality Assurance

All automated test suites verified and passing:
- `ml/nlp_eval/`: 57 / 57 tests passed
- `ml/datasets/symptoms/`: 28 / 28 validation tests passed
- `server/tests/unit/knowledge/`: 165 / 165 unit tests passed
- Zero ambiguous terms reported by `validate_symptoms.py`

