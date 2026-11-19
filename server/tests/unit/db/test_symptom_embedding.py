"""Unit tests for symptom vector embeddings and repository operations.

Responsibilities:
    - Validate typed embedding persistence and attribute mapping.
    - Test unique constraint on (model_revision, phrase).
    - Verify check constraints against empty symptom_id and phrase.
    - Test bulk insertion with caller-owned transaction semantics.
    - Validate model revision filtering and phrase resolution.
    - Test exact linear scan determinism across repeated queries (DR-02).

Owner: Nishith (Database) · Task: S2-NIT-4 · Requirements: FR-03, FR-18, DR-02, NFR-01
"""

import math
from typing import Any

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError

from app.db.session import create_session_factory
from app.repositories.symptom_embedding_repository import (
    count_symptom_embeddings,
    get_symptom_embedding_by_phrase,
    insert_symptom_embeddings,
    list_symptom_embeddings_by_revision,
)

REVISION_A = "a1b2c3d4e5f67890123456789012345678901234"
REVISION_B = "b2c3d4e5f678901234567890123456789012345a"


def _make_dummy_vector(dim: int = 384, seed: float = 1.0) -> list[float]:
    """Generate a reproducible, unit-normalized dummy vector."""
    raw = [math.sin(seed * (i + 1)) for i in range(dim)]
    norm = math.sqrt(sum(x * x for x in raw)) or 1.0
    return [x / norm for x in raw]


def test_create_and_query_symptom_embedding(engine: Engine) -> None:
    """Symptom embedding persists vector and can be resolved by phrase."""
    factory = create_session_factory(engine)
    vec = _make_dummy_vector(seed=1.0)

    with factory.begin() as session:
        count = insert_symptom_embeddings(
            session=session,
            embeddings=[
                {
                    "symptom_id": "chest_pain",
                    "phrase": "tightness in chest",
                    "model_revision": REVISION_A,
                    "embedding": vec,
                }
            ],
        )
        assert count == 1

    with factory() as session:
        retrieved = get_symptom_embedding_by_phrase(
            session=session,
            model_revision=REVISION_A,
            phrase="tightness in chest",
        )
        assert retrieved is not None
        assert retrieved.id is not None
        assert retrieved.symptom_id == "chest_pain"
        assert retrieved.phrase == "tightness in chest"
        assert retrieved.model_revision == REVISION_A
        assert retrieved.created_at is not None

        as_dict = retrieved.to_dict()
        assert as_dict["symptom_id"] == "chest_pain"
        assert as_dict["phrase"] == "tightness in chest"


def test_unique_constraint_revision_phrase(engine: Engine) -> None:
    """Duplicate (model_revision, phrase) raises IntegrityError."""
    factory = create_session_factory(engine)
    vec = _make_dummy_vector(seed=2.0)

    with factory.begin() as session:
        insert_symptom_embeddings(
            session,
            [
                {
                    "symptom_id": "headache",
                    "phrase": "severe headache",
                    "model_revision": REVISION_A,
                    "embedding": vec,
                }
            ],
        )

    with pytest.raises(IntegrityError), factory.begin() as session:
        insert_symptom_embeddings(
            session,
            [
                {
                    "symptom_id": "migraine",
                    "phrase": "severe headache",
                    "model_revision": REVISION_A,
                    "embedding": vec,
                }
            ],
        )


def test_same_phrase_different_revision_allowed(engine: Engine) -> None:
    """Same phrase under different model revisions persists without conflict."""
    factory = create_session_factory(engine)
    vec = _make_dummy_vector(seed=3.0)

    with factory.begin() as session:
        c1 = insert_symptom_embeddings(
            session,
            [
                {
                    "symptom_id": "cough",
                    "phrase": "dry cough",
                    "model_revision": REVISION_A,
                    "embedding": vec,
                }
            ],
        )
        c2 = insert_symptom_embeddings(
            session,
            [
                {
                    "symptom_id": "cough",
                    "phrase": "dry cough",
                    "model_revision": REVISION_B,
                    "embedding": vec,
                }
            ],
        )
        assert c1 == 1
        assert c2 == 1

    with factory() as session:
        assert count_symptom_embeddings(session, REVISION_A) == 1
        assert count_symptom_embeddings(session, REVISION_B) == 1
        assert count_symptom_embeddings(session) == 2


def test_check_constraints_blank_values(engine: Engine) -> None:
    """Blank symptom_id or phrase is rejected by repository validation."""
    factory = create_session_factory(engine)
    vec = _make_dummy_vector(seed=4.0)

    with factory.begin() as session:
        with pytest.raises(ValueError, match="symptom_id must not be blank"):
            insert_symptom_embeddings(
                session,
                [
                    {
                        "symptom_id": "",
                        "phrase": "valid phrase",
                        "model_revision": REVISION_A,
                        "embedding": vec,
                    }
                ],
            )

        with pytest.raises(ValueError, match="phrase must not be blank"):
            insert_symptom_embeddings(
                session,
                [
                    {
                        "symptom_id": "nausea",
                        "phrase": "   ",
                        "model_revision": REVISION_A,
                        "embedding": vec,
                    }
                ],
            )

        with pytest.raises(ValueError, match="model_revision must not be blank"):
            insert_symptom_embeddings(
                session,
                [
                    {
                        "symptom_id": "nausea",
                        "phrase": "feeling sick",
                        "model_revision": "",
                        "embedding": vec,
                    }
                ],
            )


def test_bulk_insert_and_revision_filtering(engine: Engine) -> None:
    """Bulk inserting multiple rows and listing by revision returns expected rows."""
    factory = create_session_factory(engine)
    items: list[dict[str, Any]] = [
        {
            "symptom_id": f"symptom_{i}",
            "phrase": f"lay phrase {i}",
            "model_revision": REVISION_A if i < 3 else REVISION_B,
            "embedding": _make_dummy_vector(seed=float(i + 1)),
        }
        for i in range(5)
    ]

    with factory.begin() as session:
        inserted = insert_symptom_embeddings(session, items)
        assert inserted == 5

    with factory() as session:
        rows_a = list_symptom_embeddings_by_revision(session, REVISION_A)
        rows_b = list_symptom_embeddings_by_revision(session, REVISION_B)
        assert len(rows_a) == 3
        assert len(rows_b) == 2
        assert count_symptom_embeddings(session, REVISION_A) == 3
        assert count_symptom_embeddings(session, REVISION_B) == 2


def test_deterministic_linear_scan_ranking(engine: Engine) -> None:
    """Exact linear scan ranking returns identical results across runs (DR-02)."""
    factory = create_session_factory(engine)

    query_vec = _make_dummy_vector(seed=42.0)
    items = [
        {
            "symptom_id": f"s_{i}",
            "phrase": f"symptom phrase {i}",
            "model_revision": REVISION_A,
            "embedding": _make_dummy_vector(seed=float(i * 10 + 1)),
        }
        for i in range(10)
    ]

    with factory.begin() as session:
        insert_symptom_embeddings(session, items)

    def _rank_nearest(session) -> list[str]:
        embeddings = list_symptom_embeddings_by_revision(session, REVISION_A)
        # Cosine similarity for L2-normalized vectors is dot product
        scored: list[tuple[float, str]] = []
        for e in embeddings:
            dot = sum(q * float(v) for q, v in zip(query_vec, e.embedding, strict=True))
            scored.append((dot, e.symptom_id))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [symptom_id for _, symptom_id in scored[:3]]

    with factory() as session:
        first_run = _rank_nearest(session)
        for _ in range(5):
            repeat_run = _rank_nearest(session)
            assert repeat_run == first_run, (
                "Linear scan must be strictly deterministic (DR-02)"
            )


def test_caller_owned_transaction_rollback(engine: Engine) -> None:
    """Session rollback discards uncommitted embedding insertions."""
    factory = create_session_factory(engine)
    session = factory()
    try:
        insert_symptom_embeddings(
            session,
            [
                {
                    "symptom_id": "dizziness",
                    "phrase": "feeling lightheaded",
                    "model_revision": REVISION_A,
                    "embedding": _make_dummy_vector(seed=9.0),
                }
            ],
        )
        session.rollback()
    finally:
        session.close()

    with factory() as session:
        assert count_symptom_embeddings(session, REVISION_A) == 0
