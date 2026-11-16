"""Where the symptom vectors live: pgvector on Neon, or memory for tests.

Responsibilities:
    - Define the ``SymptomVectorStore`` protocol: replace one model revision's
      vectors, count them, and find the nearest phrase to a query vector.
    - ``PgVectorStore``: the ``symptom_embeddings`` table (migration S2-NIT-4).
      It uses an exact scan, ordered by distance and then phrase, because an
      approximate index could return different rows for the same input (DR-02).
    - ``InMemoryVectorStore``: the same contract in NumPy, for unit tests and
      evaluation without a database.

Vectors are passed to PostgreSQL as ``vector`` text literals, so no pgvector
Python package is needed.

Owner: Nisarg (retrieval) · Task: S2-NIS-7 · Requirements: FR-03, FR-18, DR-02
"""

from collections.abc import Sequence
from typing import Protocol

import numpy as np
from sqlalchemy import Engine, text

from app.services.retrieval.embedder import Vectors
from app.services.retrieval.schemas import VectorMatch, VocabularyEntry

TABLE = "symptom_embeddings"


class SymptomVectorStore(Protocol):
    """Stores one vector per vocabulary phrase and model revision."""

    def replace(
        self, revision: str, entries: Sequence[VocabularyEntry], vectors: Vectors
    ) -> None:
        """Replace every vector of ``revision`` with these, atomically."""
        ...

    def count(self, revision: str) -> int:
        """How many phrases are stored for ``revision``."""
        ...

    def nearest(self, revision: str, vector: Vectors) -> VectorMatch | None:
        """The closest stored phrase by cosine similarity, or ``None`` if empty."""
        ...


def _check_shapes(entries: Sequence[VocabularyEntry], vectors: Vectors) -> None:
    """Reject vectors that do not line up one-to-one with the entries."""
    if vectors.ndim != 2 or vectors.shape[0] != len(entries):
        raise ValueError("need exactly one vector per vocabulary entry")


def vector_literal(vector: Vectors) -> str:
    """Format a vector as a pgvector text literal with fixed precision.

    Example:
        >>> vector_literal(np.array([0.5, -0.25], dtype=np.float32))
        '[0.50000000,-0.25000000]'
    """
    return "[" + ",".join(f"{float(x):.8f}" for x in vector.ravel()) + "]"


class InMemoryVectorStore:
    """NumPy implementation of ``SymptomVectorStore`` (tests and evaluation)."""

    def __init__(self) -> None:
        """Start empty."""
        self._data: dict[str, tuple[list[VocabularyEntry], Vectors]] = {}

    def replace(
        self, revision: str, entries: Sequence[VocabularyEntry], vectors: Vectors
    ) -> None:
        """See ``SymptomVectorStore.replace``; rows are kept sorted by phrase."""
        _check_shapes(entries, vectors)
        order = sorted(range(len(entries)), key=lambda i: entries[i].phrase)
        self._data[revision] = (
            [entries[i] for i in order],
            vectors[order].astype(np.float32),
        )

    def count(self, revision: str) -> int:
        """See ``SymptomVectorStore.count``."""
        entries, _ = self._data.get(revision, ([], np.zeros((0, 0), np.float32)))
        return len(entries)

    def nearest(self, revision: str, vector: Vectors) -> VectorMatch | None:
        """See ``SymptomVectorStore.nearest``; ties go to the first phrase."""
        if not self.count(revision):
            return None
        entries, matrix = self._data[revision]
        similarities = matrix @ vector.ravel().astype(np.float32)
        best = int(np.argmax(similarities))  # first maximum = alphabetical tie-break
        entry = entries[best]
        return VectorMatch(
            symptom_id=entry.symptom_id,
            phrase=entry.phrase,
            similarity=float(similarities[best]),
        )


class PgVectorStore:
    """``SymptomVectorStore`` on the ``symptom_embeddings`` pgvector table."""

    def __init__(self, engine: Engine) -> None:
        """Use an injected engine (``app.db.session.create_db_engine``)."""
        self._engine = engine

    def replace(
        self, revision: str, entries: Sequence[VocabularyEntry], vectors: Vectors
    ) -> None:
        """See ``SymptomVectorStore.replace``; one transaction, so all or nothing."""
        _check_shapes(entries, vectors)
        rows = [
            {
                "symptom_id": entry.symptom_id,
                "phrase": entry.phrase,
                "revision": revision,
                "embedding": vector_literal(vectors[i]),
            }
            for i, entry in enumerate(entries)
        ]
        with self._engine.begin() as connection:
            connection.execute(
                text(f"DELETE FROM {TABLE} WHERE model_revision = :revision"),
                {"revision": revision},
            )
            connection.execute(
                text(
                    f"INSERT INTO {TABLE}"
                    " (symptom_id, phrase, model_revision, embedding) VALUES"
                    " (:symptom_id, :phrase, :revision, CAST(:embedding AS vector))"
                ),
                rows,
            )

    def count(self, revision: str) -> int:
        """See ``SymptomVectorStore.count``."""
        with self._engine.connect() as connection:
            value = connection.execute(
                text(f"SELECT count(*) FROM {TABLE} WHERE model_revision = :revision"),
                {"revision": revision},
            ).scalar_one()
        return int(value)

    def nearest(self, revision: str, vector: Vectors) -> VectorMatch | None:
        """See ``SymptomVectorStore.nearest``; ``<=>`` is cosine distance."""
        query = text(
            f"SELECT symptom_id, phrase, 1 - (embedding <=> CAST(:q AS vector)) AS sim"
            f" FROM {TABLE} WHERE model_revision = :revision"
            " ORDER BY embedding <=> CAST(:q AS vector), phrase LIMIT 1"
        )
        with self._engine.connect() as connection:
            row = connection.execute(
                query, {"q": vector_literal(vector), "revision": revision}
            ).first()
        if row is None:
            return None
        return VectorMatch(
            symptom_id=row.symptom_id, phrase=row.phrase, similarity=row.sim
        )
