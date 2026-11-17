"""Symptom embedding repository providing typed persistence for vector retrieval.

Responsibilities:
    - Persist dense sentence embeddings for symptoms and natural language lay terms.
    - Provide query methods scoped to pinned model revisions (DR-02).
    - Support deterministic linear scan retrieval across ~700 canonical entries.
    - Guarantee caller-owned transaction boundaries with session.flush().

Owner: Nishith (Database) · Task: S2-NIT-4 · Requirements: FR-03, FR-18, DR-02, NFR-01
"""

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.symptom_embedding import SymptomEmbedding


def insert_symptom_embeddings(
    session: Session,
    embeddings: Sequence[Mapping[str, Any]],
) -> int:
    """Bulk insert dense symptom embedding records.

    Flushes the session to populate generated keys without committing,
    preserving caller ownership of the transaction boundary.

    Args:
        session: Active SQLAlchemy database session.
        embeddings: Sequence of dictionaries containing symptom_id, phrase,
            model_revision, and embedding vector.

    Returns:
        Number of embedding records inserted.

    Raises:
        ValueError: If embeddings sequence is empty or an entry has blank fields.
    """
    if not embeddings:
        return 0

    records: list[SymptomEmbedding] = []
    for item in embeddings:
        symptom_id = str(item.get("symptom_id", "")).strip()
        phrase = str(item.get("phrase", "")).strip()
        model_revision = str(item.get("model_revision", "")).strip()
        raw_vector = item.get("embedding")

        if not symptom_id:
            raise ValueError("symptom_id must not be blank")
        if not phrase:
            raise ValueError("phrase must not be blank")
        if not model_revision:
            raise ValueError("model_revision must not be blank")
        if raw_vector is None:
            raise ValueError("embedding vector must not be None")

        records.append(
            SymptomEmbedding(
                symptom_id=symptom_id,
                phrase=phrase,
                model_revision=model_revision,
                embedding=raw_vector,
            )
        )

    session.add_all(records)
    session.flush()
    return len(records)


def get_symptom_embedding_by_phrase(
    session: Session,
    model_revision: str,
    phrase: str,
) -> SymptomEmbedding | None:
    """Retrieve an embedding record by exact phrase and model revision.

    Args:
        session: Active SQLAlchemy database session.
        model_revision: Pinned model commit hash.
        phrase: Exact natural language phrase or symptom name.

    Returns:
        SymptomEmbedding if found, None otherwise.
    """
    stmt = select(SymptomEmbedding).where(
        SymptomEmbedding.model_revision == model_revision,
        SymptomEmbedding.phrase == phrase.strip(),
    )
    return session.scalar(stmt)


def list_symptom_embeddings_by_revision(
    session: Session,
    model_revision: str,
) -> Sequence[SymptomEmbedding]:
    """Retrieve all embeddings for a pinned model revision.

    Used by the vector retrieval service (S2-NIS-7) to execute an exact,
    deterministic linear scan without approximate index distortions (DR-02).

    Args:
        session: Active SQLAlchemy database session.
        model_revision: Pinned model commit hash.

    Returns:
        Sequence of SymptomEmbedding records for the revision.
    """
    stmt = (
        select(SymptomEmbedding)
        .where(SymptomEmbedding.model_revision == model_revision)
        .order_by(SymptomEmbedding.id.asc())
    )
    return session.scalars(stmt).all()


def count_symptom_embeddings(
    session: Session,
    model_revision: str | None = None,
) -> int:
    """Count stored symptom embedding records.

    Args:
        session: Active SQLAlchemy database session.
        model_revision: Optional filter by model revision.

    Returns:
        Count of matching symptom embedding records.
    """
    stmt = select(func.count(SymptomEmbedding.id))
    if model_revision is not None:
        stmt = stmt.where(SymptomEmbedding.model_revision == model_revision)
    return session.scalar(stmt) or 0
