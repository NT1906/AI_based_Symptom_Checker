"""Symptom embedding persistence for semantic vector retrieval.

Responsibilities:
    - Persist 384-dimensional dense sentence embeddings for symptoms and lay terms.
    - Track model revision commit hash for strict reproducibility (DR-02).
    - Provide deterministic linear scan retrieval without approximate indexing.

Owner: Nishith (Database) · Task: S2-NIT-4 · Requirements: FR-03, FR-18, DR-02, NFR-01
"""

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.sqlite.base import SQLiteDialect
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# Register VECTOR with SQLite dialect for seamless reflection in test environments
SQLiteDialect.ischema_names.setdefault("VECTOR", Vector)

EMBEDDING_DIMENSIONS = 384


class SymptomEmbedding(Base):
    """Dense vector embedding for a canonical symptom ID and lay phrase.

    Supports semantic search in vector retrieval (S2-NIS-7). Plain scan
    guarantees deterministic nearest neighbor ranking across all 700+ rows.
    """

    __tablename__ = "symptom_embeddings"
    __table_args__ = (
        CheckConstraint(
            "length(trim(symptom_id)) > 0",
            name="symptom_id_not_blank",
        ),
        CheckConstraint(
            "length(trim(phrase)) > 0",
            name="phrase_not_blank",
        ),
        UniqueConstraint(
            "model_revision",
            "phrase",
            name="uq_symptom_embeddings_revision_phrase",
        ),
        Index("ix_symptom_embeddings_model_revision", "model_revision"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    symptom_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    phrase: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )
    model_revision: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize embedding record to dictionary format.

        Returns:
            Dictionary containing embedding attributes.
        """
        return {
            "id": self.id,
            "symptom_id": self.symptom_id,
            "phrase": self.phrase,
            "model_revision": self.model_revision,
            "created_at": (self.created_at.isoformat() if self.created_at else None),
        }
