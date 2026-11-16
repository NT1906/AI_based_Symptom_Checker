# `app/services/retrieval/`: symptom name → canonical ID

**Owner:** Nisarg · **Task:** S2-NIS-7 (#154) · **Decision record:** [docs/vector-retrieval.md](../../../../docs/vector-retrieval.md)

Maps a free-text symptom name (as the AI extracted it) to a canonical symptom ID. Matching happens in two steps:
1. exact, through the knowledge normalizer;
2. if that fails, semantic: an ONNX sentence embedding compared with the vocabulary stored in pgvector.

Below the similarity threshold (0.70), the name stays unresolved.

## Public interface

```python
from app.services.retrieval import RetrievalSettings, build_symptom_resolver

resolver = build_symptom_resolver(RetrievalSettings(), engine)  # exact-only if off
resolved = resolver.resolve("Difficulty breathing")
# ResolvedSymptom(symptom_id='shortness_of_breath', method=SEMANTIC, matched_phrase=..., similarity=...)
resolver.resolve("pizza")  # None
```

| Name | What it is |
|---|---|
| `SymptomResolver` | `resolve(name)`, `resolve_all(names)`, `ensure_index()` |
| `ResolvedSymptom` | `symptom_id`, `method` (`EXACT` / `SEMANTIC`), `matched_phrase`, `similarity` (internal; never shown to users) |
| `RetrievalSettings` | `RETRIEVAL_ENABLED` (default `false`), `RETRIEVAL_THRESHOLD` (0.70), `RETRIEVAL_MODEL_*`, `RETRIEVAL_CACHE_DIR` |
| `build_symptom_resolver` | The app's resolver. It never raises: if the model or database fails, it falls back to exact-only |
| `PgVectorStore` / `InMemoryVectorStore` | The `symptom_embeddings` table / a NumPy stand-in for tests and evaluation |
| `OnnxSentenceEmbedder` | `all-MiniLM-L6-v2` int8 on ONNX Runtime, at a pinned Hugging Face revision |

## Rules

- **Deterministic:** the same name, model revision and vocabulary always give the same answer. pgvector does an exact scan, ordered by distance and then phrase, with no approximate index.
- **Never shown to users:** the similarity score isn't shown, and the name text isn't logged (only its length).
- **No real model in tests:** tests use `tests/unit/retrieval/fakes.py`.
- **Changing the model or threshold:** rerun `python -m app.services.retrieval.evaluate` and update `docs/vector-retrieval.md` in the same PR.

## Files

| File | What it does |
|---|---|
| `resolver.py` | Exact, then semantic resolution; vocabulary; index building |
| `embedder.py` | `SentenceEmbedder` protocol, ONNX embedder, mean pooling, model download |
| `vector_store.py` | `SymptomVectorStore` protocol, pgvector and in-memory stores |
| `config.py` | Settings and `build_symptom_resolver` |
| `schemas.py` | `VocabularyEntry`, `VectorMatch`, `ResolvedSymptom`, `MatchMethod` |
| `evaluate.py`, `data/eval_phrases.json` | Manual evaluation with the real model (not run in CI) |

## Tests

```bash
cd server
pytest tests/unit/retrieval -v
RETRIEVAL_TEST_DATABASE_URL=postgresql+psycopg://... pytest tests/unit/retrieval -k pgvector   # needs pgvector
```
