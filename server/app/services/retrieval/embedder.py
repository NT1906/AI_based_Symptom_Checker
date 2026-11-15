"""Sentence embeddings with a small ONNX model (no LLM, no external service).

Responsibilities:
    - Define the ``SentenceEmbedder`` protocol the resolver depends on, so
      tests can use a fake and never load the real model (AI_RULES.md §6).
    - Run ``all-MiniLM-L6-v2`` (int8 ONNX) with ONNX Runtime: tokenize,
      mean-pool over real tokens, L2-normalise.
    - Download the model files from Hugging Face Hub at a pinned revision.

onnxruntime, tokenizers and huggingface_hub are imported only when the real
model is used, so importing this module stays cheap.

Owner: Nisarg (retrieval) · Task: S2-NIS-7 · Requirements: FR-03, NFR-01
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray

MAX_TOKENS = 64

Vectors = NDArray[np.float32]


class SentenceEmbedder(Protocol):
    """Turns short texts into L2-normalised vectors."""

    @property
    def revision(self) -> str:
        """Model revision; stored vectors are only compared within one revision."""
        ...

    def embed(self, texts: Sequence[str]) -> Vectors:
        """Embed texts as an ``(n, dimension)`` float32 array of unit vectors."""
        ...


def mean_pool(hidden: NDArray[Any], mask: NDArray[Any]) -> Vectors:
    """Average token vectors over real (unmasked) tokens, then L2-normalise.

    Args:
        hidden: Token vectors, shape ``(batch, tokens, dimension)``.
        mask: Attention mask, shape ``(batch, tokens)``; 1 for real tokens.

    Returns:
        Unit vectors, shape ``(batch, dimension)``. An all-padding row stays
        zero instead of dividing by zero.

    Example:
        >>> mean_pool(np.ones((1, 2, 3)), np.array([[1, 0]])).round(3).tolist()
        [[0.577, 0.577, 0.577]]
    """
    weights = mask[..., None].astype(np.float32)
    summed = (hidden.astype(np.float32) * weights).sum(axis=1)
    pooled = summed / np.clip(weights.sum(axis=1), 1e-9, None)
    norms = np.linalg.norm(pooled, axis=1, keepdims=True)
    unit: Vectors = (pooled / np.clip(norms, 1e-12, None)).astype(np.float32)
    return unit


class OnnxSentenceEmbedder:
    """``all-MiniLM-L6-v2`` sentence embeddings on ONNX Runtime (CPU)."""

    def __init__(self, model_path: Path, tokenizer_path: Path, revision: str) -> None:
        """Load the model and tokenizer.

        Args:
            model_path: The ``.onnx`` file.
            tokenizer_path: The ``tokenizer.json`` file.
            revision: Hugging Face commit the files came from.

        Raises:
            FileNotFoundError: If either file is missing.
        """
        # Why: heavy imports only when the real model is used (never in tests).
        import onnxruntime  # type: ignore[import-untyped]
        from tokenizers import Tokenizer

        for path in (model_path, tokenizer_path):
            if not path.is_file():
                raise FileNotFoundError(f"embedding model file missing: {path.name}")
        self._revision = revision
        self._tokenizer = Tokenizer.from_file(str(tokenizer_path))
        self._tokenizer.enable_padding()
        self._tokenizer.enable_truncation(max_length=MAX_TOKENS)
        options = onnxruntime.SessionOptions()
        options.intra_op_num_threads = 1  # small model; keeps results and RAM steady
        self._session = onnxruntime.InferenceSession(
            str(model_path), options, providers=["CPUExecutionProvider"]
        )
        self._inputs = {i.name for i in self._session.get_inputs()}

    @property
    def revision(self) -> str:
        """Hugging Face commit of the loaded model."""
        return self._revision

    def embed(self, texts: Sequence[str]) -> Vectors:
        """Embed lowercased texts; see ``SentenceEmbedder.embed``."""
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        encodings = self._tokenizer.encode_batch([t.lower() for t in texts])
        ids = np.array([e.ids for e in encodings], dtype=np.int64)
        mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
        feeds = {"input_ids": ids, "attention_mask": mask}
        if "token_type_ids" in self._inputs:
            feeds["token_type_ids"] = np.zeros_like(ids)
        hidden = self._session.run(None, feeds)[0]
        return mean_pool(hidden, mask)


def download_model(
    repo_id: str, revision: str, model_file: str, cache_dir: Path | None = None
) -> tuple[Path, Path]:
    """Fetch the ONNX model and tokenizer from Hugging Face Hub (cached).

    Args:
        repo_id: e.g. ``sentence-transformers/all-MiniLM-L6-v2``.
        revision: Pinned commit SHA, so the vectors never change silently.
        model_file: Path of the ``.onnx`` file inside the repo.
        cache_dir: Download cache; the Hugging Face default if ``None``.

    Returns:
        Local paths of the model and ``tokenizer.json``.
    """
    from huggingface_hub import hf_hub_download

    def fetch(filename: str) -> Path:
        return Path(
            hf_hub_download(repo_id, filename, revision=revision, cache_dir=cache_dir)
        )

    return fetch(model_file), fetch("tokenizer.json")
