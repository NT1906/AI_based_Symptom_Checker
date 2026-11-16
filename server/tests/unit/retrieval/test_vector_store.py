"""Unit tests for the vector stores and the embedding helpers.

Covers:
    - ``InMemoryVectorStore``: nearest phrase, revision isolation, empty
      store, alphabetical tie-break, and shape checks.
    - ``vector_literal`` formatting and ``mean_pool`` (masked tokens ignored,
      no division by zero).
    - ``OnnxSentenceEmbedder`` reports a missing model file.
    - ``PgVectorStore`` against a real pgvector database, only when
      ``RETRIEVAL_TEST_DATABASE_URL`` is set (CI and SQLite skip it).

Owner: Nisarg (retrieval) · Task: S2-NIS-7 · Requirements: FR-03, DR-02
"""

import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest
from app.services.retrieval.embedder import OnnxSentenceEmbedder, mean_pool
from app.services.retrieval.schemas import VocabularyEntry
from app.services.retrieval.vector_store import (
    InMemoryVectorStore,
    PgVectorStore,
    vector_literal,
)
from sqlalchemy import Engine, create_engine, text

ENTRIES = [
    VocabularyEntry(symptom_id="fever", phrase="fever"),
    VocabularyEntry(symptom_id="cough", phrase="cough"),
    VocabularyEntry(symptom_id="headache", phrase="headache"),
]
VECTORS = np.eye(3, dtype=np.float32)


def test_nearest_returns_the_closest_phrase() -> None:
    store = InMemoryVectorStore()
    store.replace("r1", ENTRIES, VECTORS)

    match = store.nearest("r1", np.array([0.1, 0.9, 0.2], dtype=np.float32))

    assert match is not None
    assert (match.symptom_id, match.phrase) == ("cough", "cough")
    assert match.similarity == pytest.approx(0.9)


def test_revisions_are_kept_apart() -> None:
    store = InMemoryVectorStore()
    store.replace("r1", ENTRIES, VECTORS)

    assert store.count("r1") == 3
    assert store.count("r2") == 0
    assert store.nearest("r2", VECTORS[0]) is None


def test_replace_overwrites_the_revision() -> None:
    store = InMemoryVectorStore()
    store.replace("r1", ENTRIES, VECTORS)

    store.replace("r1", ENTRIES[:1], VECTORS[:1])

    assert store.count("r1") == 1


def test_tie_goes_to_the_alphabetically_first_phrase() -> None:
    store = InMemoryVectorStore()
    same = np.ones((2, 2), dtype=np.float32) / np.sqrt(2)
    entries = [
        VocabularyEntry(symptom_id="b_symptom", phrase="zzz"),
        VocabularyEntry(symptom_id="a_symptom", phrase="aaa"),
    ]
    store.replace("r1", entries, same)

    match = store.nearest("r1", same[0])

    assert match is not None and match.phrase == "aaa"


@pytest.mark.parametrize(
    "vectors",
    [np.eye(2, dtype=np.float32), np.ones(3, dtype=np.float32)],
    ids=["too_few_rows", "one_dimensional"],
)
def test_replace_rejects_vectors_that_do_not_match_the_entries(
    vectors: np.ndarray,
) -> None:
    with pytest.raises(ValueError, match="one vector per vocabulary entry"):
        InMemoryVectorStore().replace("r1", ENTRIES, vectors)


def test_vector_literal_uses_fixed_precision() -> None:
    literal = vector_literal(np.array([1.0, -0.123456789], dtype=np.float32))

    assert literal == "[1.00000000,-0.12345679]"


def test_mean_pool_ignores_padding_and_normalises() -> None:
    hidden = np.array([[[3.0, 4.0], [100.0, 100.0]]])
    mask = np.array([[1, 0]])

    pooled = mean_pool(hidden, mask)

    assert pooled.dtype == np.float32
    assert pooled[0].tolist() == pytest.approx([0.6, 0.8])


def test_mean_pool_keeps_an_all_padding_row_at_zero() -> None:
    pooled = mean_pool(np.ones((1, 2, 3)), np.zeros((1, 2)))

    assert not np.isnan(pooled).any()
    assert pooled.tolist() == [[0.0, 0.0, 0.0]]


# --- PgVectorStore against a real pgvector database (opt-in) ---------------------

PG_URL = os.environ.get("RETRIEVAL_TEST_DATABASE_URL")


@pytest.fixture
def pg_engine() -> Iterator[Engine]:
    """An engine whose search path is a fresh schema holding the S2-NIT-4 table."""
    if not PG_URL:
        pytest.skip("set RETRIEVAL_TEST_DATABASE_URL to a pgvector database")
    schema = f"retrieval_test_{uuid.uuid4().hex[:8]}"
    admin = create_engine(PG_URL)
    with admin.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        connection.execute(text(f"CREATE SCHEMA {schema}"))
        connection.execute(
            text(
                f"CREATE TABLE {schema}.symptom_embeddings ("
                " id BIGSERIAL PRIMARY KEY, symptom_id VARCHAR(64) NOT NULL,"
                " phrase VARCHAR(256) NOT NULL, model_revision VARCHAR(64) NOT NULL,"
                " embedding vector(3) NOT NULL,"
                " created_at TIMESTAMPTZ NOT NULL DEFAULT now(),"
                " UNIQUE (model_revision, phrase))"
            )
        )
    engine = create_engine(
        PG_URL, connect_args={"options": f"-csearch_path={schema},public"}
    )
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))
        admin.dispose()


def test_pgvector_store_round_trip(pg_engine: Engine) -> None:
    store = PgVectorStore(pg_engine)
    store.replace("r1", ENTRIES, VECTORS)
    store.replace("r1", ENTRIES, VECTORS)  # replacing twice keeps one copy

    match = store.nearest("r1", np.array([0.1, 0.9, 0.2], dtype=np.float32))

    assert store.count("r1") == 3
    assert store.count("r2") == 0
    assert match is not None and match.symptom_id == "cough"
    assert store.nearest("r2", VECTORS[0]) is None


def test_onnx_embedder_reports_a_missing_model_file(tmp_path: Path) -> None:
    pytest.importorskip("onnxruntime")
    pytest.importorskip("tokenizers")

    with pytest.raises(FileNotFoundError, match="missing.onnx"):
        OnnxSentenceEmbedder(
            tmp_path / "missing.onnx", tmp_path / "tokenizer.json", "r1"
        )
