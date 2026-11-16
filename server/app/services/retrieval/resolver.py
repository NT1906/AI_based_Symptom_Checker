"""Resolve a free-text symptom name to a canonical symptom ID.

Responsibilities:
    - Try the knowledge normalizer first (exact display name or lay term).
    - Otherwise embed the name and take the nearest vocabulary phrase from the
      vector store, but only at or above ``threshold``. Below it the name stays
      unresolved: guessing a wrong symptom could hide or invent a red flag.
    - Build the vocabulary (display names + lay terms) and keep the store's
      index for the current model revision complete.
    - Degrade to exact-only if the model or the database fails; retrieval is
      an aid and must never break an assessment.

Deterministic: same name, model revision and vocabulary, same answer (DR-02).
No LLM is involved, and the result is an input to the risk engine, never a
risk level itself.

Owner: Nisarg (retrieval) · Task: S2-NIS-7 · Requirements: FR-03, FR-18, DR-02
"""

from collections.abc import Sequence

from app.core.logging import get_logger
from app.services.knowledge import SymptomNormalizer, get_normalizer
from app.services.retrieval.embedder import SentenceEmbedder
from app.services.retrieval.schemas import MatchMethod, ResolvedSymptom, VocabularyEntry
from app.services.retrieval.vector_store import SymptomVectorStore

logger = get_logger(__name__)

# Why: measured on the S2-NIS-7 phrase set (docs/vector-retrieval.md): at 0.70
# no symptom or non-symptom phrase mapped to a wrong symptom; at 0.60 one did.
DEFAULT_THRESHOLD = 0.70


def build_vocabulary(normalizer: SymptomNormalizer) -> list[VocabularyEntry]:
    """Every display name and lay term, lowercased, sorted by phrase.

    A phrase that belongs to more than one symptom is left out, because it
    cannot say which symptom the user meant.

    Args:
        normalizer: The knowledge service's symptom vocabulary.

    Returns:
        One entry per unambiguous phrase.
    """
    owners: dict[str, set[str]] = {}
    for symptom in normalizer.list_all():
        for phrase in (symptom.name, *symptom.lay_terms):
            cleaned = " ".join(phrase.lower().split())
            if cleaned:
                owners.setdefault(cleaned, set()).add(symptom.id)
    return [
        VocabularyEntry(symptom_id=next(iter(ids)), phrase=phrase)
        for phrase, ids in sorted(owners.items())
        if len(ids) == 1
    ]


class SymptomResolver:
    """Exact normalizer first, then pgvector semantic matching."""

    def __init__(
        self,
        embedder: SentenceEmbedder | None = None,
        store: SymptomVectorStore | None = None,
        normalizer: SymptomNormalizer | None = None,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> None:
        """Create the resolver.

        Args:
            embedder: Sentence embedder; ``None`` means exact matching only.
            store: Vector store; ``None`` means exact matching only.
            normalizer: Knowledge vocabulary; defaults to the packaged one.
            threshold: Lowest cosine similarity accepted for a semantic match.

        Raises:
            ValueError: If ``threshold`` is not in (0, 1].
        """
        if not 0 < threshold <= 1:
            raise ValueError("threshold must be in (0, 1]")
        self._embedder = embedder
        self._store = store
        self._normalizer = normalizer or get_normalizer()
        self._threshold = threshold

    @property
    def semantic_enabled(self) -> bool:
        """Whether semantic matching is configured."""
        return self._embedder is not None and self._store is not None

    def resolve(self, name: str) -> ResolvedSymptom | None:
        """Map one symptom name to a canonical ID.

        Args:
            name: Symptom name as extracted, e.g. ``"Chest pain"``.

        Returns:
            The resolution, or ``None`` if nothing matched well enough.

        Example:
            >>> SymptomResolver().resolve("throwing up").symptom_id
            'vomiting'
        """
        cleaned = " ".join(name.split())
        if not cleaned:
            return None
        exact = self._normalizer.normalize(cleaned)
        if exact is not None:
            return ResolvedSymptom(
                symptom_id=exact.canonical_id,
                method=MatchMethod.EXACT,
                matched_phrase=exact.matched_term,
            )
        return self._resolve_semantic(cleaned)

    def ensure_index(self) -> bool:
        """Embed and store the vocabulary unless this revision is complete.

        Returns:
            True if the index was (re)built, False if it was already complete
            or semantic matching is off.
        """
        if self._embedder is None or self._store is None:
            return False
        vocabulary = build_vocabulary(self._normalizer)
        revision = self._embedder.revision
        if self._store.count(revision) == len(vocabulary):
            return False
        vectors = self._embedder.embed([entry.phrase for entry in vocabulary])
        self._store.replace(revision, vocabulary, vectors)
        logger.info("symptom_index_built", revision=revision, phrases=len(vocabulary))
        return True

    def resolve_all(self, names: Sequence[str]) -> list[ResolvedSymptom | None]:
        """``resolve`` for each name, in order."""
        return [self.resolve(name) for name in names]

    def _resolve_semantic(self, name: str) -> ResolvedSymptom | None:
        """Nearest vocabulary phrase at or above the threshold, or ``None``."""
        if self._embedder is None or self._store is None:
            return None
        try:
            vector = self._embedder.embed([name])[0]
            match = self._store.nearest(self._embedder.revision, vector)
        except Exception as exc:  # noqa: BLE001
            # Why: any model or database failure falls back to exact-only;
            # the name stays unresolved instead of breaking the assessment.
            logger.warning("semantic_match_failed", error=type(exc).__name__)
            return None
        if match is None or match.similarity < self._threshold:
            logger.info("symptom_unresolved", name_length=len(name))
            return None
        return ResolvedSymptom(
            symptom_id=match.symptom_id,
            method=MatchMethod.SEMANTIC,
            matched_phrase=match.phrase,
            similarity=round(match.similarity, 4),
        )
