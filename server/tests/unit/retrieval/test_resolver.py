"""Unit tests for the symptom resolver.

Covers:
    - Exact matches through the knowledge normalizer (display names, lay terms,
      "Chest pain" / "chest-pain" style variants).
    - Semantic matches at or above the threshold, nothing below it, and
      nothing for blank input.
    - Fallback: a failing model or store leaves the name unresolved, never
      raises.
    - Index building: built once per revision, rebuilt when incomplete.
    - The vocabulary: every symptom, sorted, lowercased, ambiguous phrases out.
    - Determinism and threshold validation.

Owner: Nisarg (retrieval) · Task: S2-NIS-7 · Requirements: FR-03, FR-18, DR-02
"""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pytest
from app.services.knowledge import get_normalizer
from app.services.retrieval.embedder import Vectors
from app.services.retrieval.resolver import SymptomResolver, build_vocabulary
from app.services.retrieval.schemas import (
    MatchMethod,
    VectorMatch,
    VocabularyEntry,
)
from app.services.retrieval.vector_store import InMemoryVectorStore

from tests.unit.retrieval.fakes import FailingEmbedder, TrigramEmbedder


def _semantic(threshold: float = 0.7) -> SymptomResolver:
    """A semantic resolver over the real vocabulary with the fake embedder."""
    resolver = SymptomResolver(
        TrigramEmbedder(), InMemoryVectorStore(), None, threshold
    )
    resolver.ensure_index()
    return resolver


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Chest pain", "chest_pain"),
        ("chest-pain", "chest_pain"),
        ("  throwing   up ", "vomiting"),
        ("vomiting", "vomiting"),
    ],
)
def test_exact_match_uses_the_normalizer(name: str, expected: str) -> None:
    resolved = SymptomResolver().resolve(name)

    assert resolved is not None
    assert (resolved.symptom_id, resolved.method) == (expected, MatchMethod.EXACT)
    assert resolved.similarity is None


def test_exact_only_resolver_leaves_unknown_names_unresolved() -> None:
    resolver = SymptomResolver()

    assert resolver.semantic_enabled is False
    assert resolver.resolve("chest pian") is None


def test_semantic_match_maps_a_misspelling_above_the_threshold() -> None:
    resolved = _semantic().resolve("sore throt")

    assert resolved is not None
    assert resolved.symptom_id == "sore_throat"
    assert resolved.method is MatchMethod.SEMANTIC
    assert resolved.similarity is not None and resolved.similarity >= 0.7


def test_exact_match_wins_over_semantic() -> None:
    resolved = _semantic().resolve("Chest pain")

    assert resolved is not None and resolved.method is MatchMethod.EXACT


@pytest.mark.parametrize("name", ["pizza", "my mother", "the weather is cold"])
def test_unrelated_text_stays_unresolved(name: str) -> None:
    assert _semantic().resolve(name) is None


@pytest.mark.parametrize("name", ["", "   ", "\n\t"])
def test_blank_name_is_unresolved_without_embedding(name: str) -> None:
    embedder = TrigramEmbedder()
    resolver = SymptomResolver(embedder, InMemoryVectorStore())

    assert resolver.resolve(name) is None
    assert embedder.calls == 0


def test_higher_threshold_rejects_a_weaker_match() -> None:
    loose = _semantic(threshold=0.5).resolve("sore throt")
    assert loose is not None and loose.similarity is not None

    strict = _semantic(threshold=min(1.0, loose.similarity + 0.01))

    assert strict.resolve("sore throt") is None


def test_failing_model_leaves_the_name_unresolved() -> None:
    resolver = SymptomResolver(FailingEmbedder(), InMemoryVectorStore())

    assert resolver.resolve("sore throt") is None
    # Exact matching still works while the model is down.
    resolved = resolver.resolve("Chest pain")
    assert resolved is not None and resolved.symptom_id == "chest_pain"


@dataclass
class _BrokenStore:
    """Vector store whose database is unreachable."""

    def replace(
        self, revision: str, entries: Sequence[VocabularyEntry], vectors: Vectors
    ) -> None:
        raise ConnectionError("database down")

    def count(self, revision: str) -> int:
        raise ConnectionError("database down")

    def nearest(self, revision: str, vector: Vectors) -> VectorMatch | None:
        raise ConnectionError("database down")


def test_failing_store_leaves_the_name_unresolved() -> None:
    resolver = SymptomResolver(TrigramEmbedder(), _BrokenStore())

    assert resolver.resolve("sore throt") is None


def test_index_is_built_once_per_revision() -> None:
    embedder = TrigramEmbedder()
    store = InMemoryVectorStore()
    resolver = SymptomResolver(embedder, store)

    assert resolver.ensure_index() is True
    assert resolver.ensure_index() is False
    assert store.count(embedder.revision) == len(build_vocabulary(get_normalizer()))
    assert embedder.calls == 1


def test_incomplete_index_is_rebuilt() -> None:
    embedder = TrigramEmbedder()
    store = InMemoryVectorStore()
    one = [VocabularyEntry(symptom_id="fever", phrase="fever")]
    store.replace(embedder.revision, one, np.ones((1, 256), dtype=np.float32))

    assert SymptomResolver(embedder, store).ensure_index() is True
    assert store.count(embedder.revision) > 1


def test_ensure_index_without_semantic_matching_does_nothing() -> None:
    assert SymptomResolver().ensure_index() is False


def test_vocabulary_covers_every_symptom_sorted_and_lowercased() -> None:
    normalizer = get_normalizer()

    vocabulary = build_vocabulary(normalizer)

    phrases = [entry.phrase for entry in vocabulary]
    assert phrases == sorted(phrases)
    assert len(phrases) == len(set(phrases))
    assert all(phrase == phrase.lower() for phrase in phrases)
    assert {entry.symptom_id for entry in vocabulary} == set(normalizer.list_ids())


@dataclass(frozen=True)
class _Symptom:
    """Minimal stand-in for a knowledge ``CanonicalSymptom``."""

    id: str
    name: str
    lay_terms: tuple[str, ...]


@dataclass(frozen=True)
class _TinyNormalizer:
    """Two symptoms that share the lay term "pain"."""

    def list_all(self) -> list[_Symptom]:
        return [
            _Symptom("chest_pain", "Chest pain", ("pain", "seene me dard")),
            _Symptom("headache", "Headache", ("Pain", "sir dard")),
        ]


def test_vocabulary_drops_a_phrase_shared_by_two_symptoms() -> None:
    vocabulary = build_vocabulary(_TinyNormalizer())  # type: ignore[arg-type]

    phrases = {entry.phrase: entry.symptom_id for entry in vocabulary}
    assert "pain" not in phrases
    assert phrases["seene me dard"] == "chest_pain"
    assert phrases["sir dard"] == "headache"


def test_same_name_always_resolves_the_same_way() -> None:
    resolver = _semantic()
    first = resolver.resolve_all(["sore throt", "Chest pain", "pizza"])

    for _ in range(100):
        assert resolver.resolve_all(["sore throt", "Chest pain", "pizza"]) == first


@pytest.mark.parametrize("threshold", [0.0, -0.1, 1.5])
def test_threshold_outside_zero_to_one_is_rejected(threshold: float) -> None:
    with pytest.raises(ValueError, match="threshold"):
        SymptomResolver(threshold=threshold)
