"""Settings and wiring for symptom retrieval (env prefix ``RETRIEVAL_``).

Responsibilities:
    - Read the retrieval settings: on/off, pinned model, threshold, cache.
    - Build the ``SymptomResolver`` the app should use: exact-only when
      retrieval is off, otherwise the ONNX embedder plus ``PgVectorStore``
      with a complete index for the pinned model revision.

Retrieval is **off by default** until the ``symptom_embeddings`` migration
(S2-NIT-4) is on the database. Turning it on is ``RETRIEVAL_ENABLED=true``.

Owner: Nisarg (retrieval) · Task: S2-NIS-7 · Requirements: FR-03, NFR-01
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Engine

from app.core.logging import get_logger
from app.services.retrieval.embedder import OnnxSentenceEmbedder, download_model
from app.services.retrieval.resolver import DEFAULT_THRESHOLD, SymptomResolver
from app.services.retrieval.vector_store import PgVectorStore

logger = get_logger(__name__)

MODEL_REPO = "sentence-transformers/all-MiniLM-L6-v2"
# Pinned commit, so stored vectors never change under us (DR-02).
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
MODEL_FILE = "onnx/model_quint8_avx2.onnx"  # int8, 23 MB, x86-64 production CPUs


class RetrievalSettings(BaseSettings):
    """Retrieval settings from ``RETRIEVAL_*`` environment variables.

    Attributes:
        enabled: Use semantic matching; otherwise exact matching only.
        model_repo: Hugging Face repo of the embedding model.
        model_revision: Pinned commit SHA of that repo.
        model_file: ONNX file inside the repo.
        threshold: Lowest cosine similarity accepted for a semantic match.
        cache_dir: Model download cache; the Hugging Face default if unset.
    """

    model_config = SettingsConfigDict(env_prefix="RETRIEVAL_", extra="ignore")

    enabled: bool = False
    model_repo: str = MODEL_REPO
    model_revision: str = Field(default=MODEL_REVISION, min_length=7)
    model_file: str = MODEL_FILE
    threshold: float = Field(default=DEFAULT_THRESHOLD, gt=0, le=1)
    cache_dir: Path | None = None


def build_symptom_resolver(
    settings: RetrievalSettings, engine: Engine | None
) -> SymptomResolver:
    """The resolver for the running app.

    Args:
        settings: Retrieval settings.
        engine: Database engine; semantic matching needs it.

    Returns:
        A semantic resolver with a complete index, or an exact-only resolver
        when retrieval is off, there is no engine, or the model or the
        database cannot be reached (logged, never raised).
    """
    if not settings.enabled or engine is None:
        return SymptomResolver(threshold=settings.threshold)
    try:
        model_path, tokenizer_path = download_model(
            settings.model_repo,
            settings.model_revision,
            settings.model_file,
            settings.cache_dir,
        )
        embedder = OnnxSentenceEmbedder(
            model_path, tokenizer_path, settings.model_revision
        )
        resolver = SymptomResolver(
            embedder, PgVectorStore(engine), threshold=settings.threshold
        )
        resolver.ensure_index()
    except Exception as exc:  # noqa: BLE001
        # Why: the app must still start; exact matching keeps working.
        logger.warning("retrieval_unavailable", error=type(exc).__name__)
        return SymptomResolver(threshold=settings.threshold)
    return resolver
