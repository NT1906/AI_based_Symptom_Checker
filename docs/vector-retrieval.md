# Vector retrieval for symptom names (S2-NIS-7)

**Owner:** Nisarg · **Issue:** #154 · **Decided:** 15 Nov 2026 · **Requirements:** FR-03, FR-18, DR-02
**Code:** [`server/app/services/retrieval/`](../server/app/services/retrieval/README.md) · **Database:** `symptom_embeddings` table (S2-NIT-4, #160) · **Wiring:** S2-DAR-9 (#249)

## 1. Decision

The plan asked: if deterministic normalization misses too many symptoms, add semantic matching with pgvector and a small ONNX sentence-embedding model.
**We are adding it.** Every symptom name the AI extracts gets resolved in two steps:

1. **Exact:** the knowledge normalizer (S1-KAV-1) matches a display name or lay term.
2. **Semantic:** otherwise, the name is embedded with `all-MiniLM-L6-v2` and compared with the 702 stored phrases (100 display names and their lay terms) in pgvector. The nearest phrase counts only if its cosine similarity is **≥ 0.70**.
   - Below that, the name stays **unresolved**.

Retrieval only maps names to symptom IDs. The deterministic risk engine still decides the risk level, and no LLM is involved (AI_RULES.md §2.4).

## 2. Why it was needed

- **The keyword baseline misses most symptoms.** In Kavya's eval set v2 (`ml/nlp_eval/report_v2.md`) it finds only **29 %** of them: 14 % with misspellings, 35 % in Hinglish.
- **There is a safety gap:** nothing maps the AI's symptom names to canonical IDs before the risk engine.
  - If the AI returns "Difficulty breathing" instead of `shortness_of_breath`, red-flag rules for that symptom cannot fire.
  - S2-DAR-9 (#249) closes the gap by calling the resolver from the orchestrator.

## 3. Evaluation

Phrase set: [`server/app/services/retrieval/data/eval_phrases.json`](../server/app/services/retrieval/data/eval_phrases.json), 65 names in 4 groups.
- Misspellings and Hinglish come from report v2 §4.
- AI-style variants are names an AI might return.
- Non-symptoms must stay unresolved.

Reproduce with `cd server && python -m app.services.retrieval.evaluate`, which downloads the pinned model.

| Method | Misspelling | Hinglish | AI-style variant | Non-symptom | Wrong total |
|---|---|---|---|---|---|
| Exact only | 0/20 | 10/15 | 14/20 | 10/10 | 0 |
| Exact + semantic ≥ 0.60 | 7/20 | 14/15 | 20/20 | 9/10 (1 wrong) | 1 |
| Exact + semantic ≥ 0.65 | 6/20 | 14/15 | 20/20 | 10/10 | 0 |
| **Exact + semantic ≥ 0.70 (chosen)** | **5/20** | **14/15** | **20/20** | **10/10** | **0** |
| Exact + semantic ≥ 0.75 | 2/20 | 13/15 | 20/20 | 10/10 | 0 |
| Exact + semantic ≥ 0.80 | 2/20 | 12/15 | 20/20 | 10/10 | 0 |

**Why 0.70:** a wrong match is worse than no match, because it could invent a red flag or hide one.
- 0.70 is the lowest threshold with zero wrong answers and a margin above 0.60, where the first wrong answer appears.
- At 0.70, resolved phrases rise from 24 of 55 (44 %) to **39 of 55 (71 %)**, and every AI-style variant resolves.

**Models compared:**

| Model (int8 ONNX) | Size | Result |
|---|---|---|
| `all-MiniLM-L6-v2` | 23 MB | Above, **0 wrong** at 0.70 |
| `paraphrase-multilingual-MiniLM-L12-v2` | 118 MB | More misspellings resolved, but **5 wrong** (4 misspellings, 1 non-symptom) at 0.70, and 5× the memory. Rejected. |

## 4. How it runs

| Part | Choice | Reason |
|---|---|---|
| Model | `sentence-transformers/all-MiniLM-L6-v2`, `onnx/model_quint8_avx2.onnx`, pinned commit `1110a24…` (Apache-2.0) | Small (23 MB) and safe on the evaluation; the pin means vectors never change silently |
| Runtime | ONNX Runtime on CPU, 1 thread, downloaded from Hugging Face Hub at startup | No new service, same runtime as the CV model |
| Store | pgvector `symptom_embeddings` on Neon, an **exact scan** (no HNSW/IVFFlat index), ordered by distance then phrase | About 700 rows scan fast, and an approximate index could answer the same input differently (DR-02) |
| Index | Built at startup if the pinned revision is incomplete; one transaction | Self-healing, all or nothing |
| Failure | Model or database unavailable: exact matching only, logged | Retrieval is an aid; it never breaks an assessment |
| Switch | `RETRIEVAL_ENABLED=true`, **off by default** | Turned on per environment once the #160 migration is on the database |

## 5. Limits

- **Misspellings stay weak (5 of 20).** The AI extraction prompt v2 (S2-NIT-1) is the main fix for typos. If more is needed, deterministic fuzzy matching could be added later.
- **Small phrase set.** The threshold was chosen on 65 phrases, so a larger set should confirm it before the threshold changes.
- **English model.** Hinglish works mostly through the lay terms in the vocabulary, not through the model itself.
- **Database test.** The `PgVectorStore` SQL is tested only when `RETRIEVAL_TEST_DATABASE_URL` points to a pgvector database. Run it on Neon staging after #160.
