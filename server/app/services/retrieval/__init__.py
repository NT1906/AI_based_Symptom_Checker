"""Symptom retrieval: map free-text symptom names to canonical IDs.

Responsibilities:
    - Exact matching through the knowledge normalizer, then semantic matching
      with a small ONNX sentence-embedding model and pgvector (S2-NIS-7).
    - Keep the vocabulary index in the ``symptom_embeddings`` table complete.

Typical use (the orchestrator, S2-DAR-9)::

    resolver = build_symptom_resolver(RetrievalSettings(), engine)
    resolved = resolver.resolve("Chest pain")  # symptom_id='chest_pain'

Owner: Nisarg (retrieval) · Task: S2-NIS-7 · Requirements: FR-03, FR-18, DR-02
"""

from app.services.retrieval.config import RetrievalSettings, build_symptom_resolver
from app.services.retrieval.embedder import (
    OnnxSentenceEmbedder,
    SentenceEmbedder,
    download_model,
    mean_pool,
)
from app.services.retrieval.resolver import (
    DEFAULT_THRESHOLD,
    SymptomResolver,
    build_vocabulary,
)
from app.services.retrieval.schemas import (
    MatchMethod,
    ResolvedSymptom,
    VectorMatch,
    VocabularyEntry,
)
from app.services.retrieval.vector_store import (
    InMemoryVectorStore,
    PgVectorStore,
    SymptomVectorStore,
    vector_literal,
)

__all__ = [
    "DEFAULT_THRESHOLD",
    "InMemoryVectorStore",
    "MatchMethod",
    "OnnxSentenceEmbedder",
    "PgVectorStore",
    "ResolvedSymptom",
    "RetrievalSettings",
    "SentenceEmbedder",
    "SymptomResolver",
    "SymptomVectorStore",
    "VectorMatch",
    "VocabularyEntry",
    "build_symptom_resolver",
    "build_vocabulary",
    "download_model",
    "mean_pool",
    "vector_literal",
]
