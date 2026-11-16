"""Test doubles for symptom retrieval: a deterministic fake sentence embedder.

Responsibilities:
    - ``TrigramEmbedder``: hashes character trigrams into a fixed-size unit
      vector, so similar spellings get similar vectors without loading the
      real ONNX model (AI_RULES.md §6).
    - ``FailingEmbedder``: raises on every call, for the fallback path.

Owner: Nisarg (retrieval) · Task: S2-NIS-7 · Requirements: FR-03
"""

import hashlib
from collections.abc import Sequence

import numpy as np
from app.services.retrieval.embedder import Vectors

DIMENSION = 256


class TrigramEmbedder:
    """Deterministic character-trigram embedder (stable across processes)."""

    revision = "fake-trigram-1"

    def __init__(self) -> None:
        """Start with no calls counted."""
        self.calls = 0

    def embed(self, texts: Sequence[str]) -> Vectors:
        """One unit vector per text; see ``SentenceEmbedder.embed``."""
        self.calls += 1
        vectors = np.zeros((len(texts), DIMENSION), dtype=np.float32)
        for row, text in enumerate(texts):
            padded = f"  {text.lower()} "
            for i in range(len(padded) - 2):
                digest = hashlib.md5(padded[i : i + 3].encode()).digest()
                vectors[row, int.from_bytes(digest[:4], "little") % DIMENSION] += 1
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        unit: Vectors = vectors / np.clip(norms, 1e-12, None)
        return unit


class FailingEmbedder:
    """Embedder whose model "crashed"."""

    revision = "fake-failing-1"

    def embed(self, texts: Sequence[str]) -> Vectors:
        """Always raise, like a broken ONNX session."""
        raise RuntimeError("model failed")
