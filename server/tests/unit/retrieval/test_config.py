"""Unit tests for retrieval settings, wiring and the evaluation helpers.

Covers:
    - Settings: off by default, pinned model revision, ``RETRIEVAL_*`` env vars,
      threshold bounds.
    - ``build_symptom_resolver``: exact-only when off or without a database;
      semantic with a built index when on; exact-only (never a crash) when
      the model download fails.
    - The evaluation phrase set and its scoring and table helpers.

Owner: Nisarg (retrieval) · Task: S2-NIS-7 · Requirements: FR-03, NFR-07
"""

from pathlib import Path
from typing import Any

import pytest
from app.services.retrieval import config, evaluate
from app.services.retrieval.config import RetrievalSettings, build_symptom_resolver
from app.services.retrieval.resolver import SymptomResolver
from app.services.retrieval.vector_store import InMemoryVectorStore
from pydantic import ValidationError
from sqlalchemy import create_engine

from tests.unit.retrieval.fakes import TrigramEmbedder


def test_retrieval_is_off_by_default_with_a_pinned_model() -> None:
    settings = RetrievalSettings()

    assert settings.enabled is False
    assert settings.model_revision == config.MODEL_REVISION
    assert len(settings.model_revision) == 40  # a full commit SHA, not a branch


def test_settings_read_retrieval_environment_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RETRIEVAL_ENABLED", "true")
    monkeypatch.setenv("RETRIEVAL_THRESHOLD", "0.8")

    settings = RetrievalSettings()

    assert (settings.enabled, settings.threshold) == (True, 0.8)


@pytest.mark.parametrize("threshold", [0, 1.2])
def test_settings_reject_a_threshold_outside_zero_to_one(threshold: float) -> None:
    with pytest.raises(ValidationError):
        RetrievalSettings(threshold=threshold)


def test_disabled_retrieval_gives_an_exact_only_resolver() -> None:
    resolver = build_symptom_resolver(RetrievalSettings(enabled=False), None)

    assert resolver.semantic_enabled is False


def test_enabled_without_a_database_gives_an_exact_only_resolver() -> None:
    resolver = build_symptom_resolver(RetrievalSettings(enabled=True), None)

    assert resolver.semantic_enabled is False


def _fake_wiring(monkeypatch: pytest.MonkeyPatch) -> InMemoryVectorStore:
    """Replace the download, the ONNX model and pgvector with fakes."""
    store = InMemoryVectorStore()

    def fake_download(*args: Any) -> tuple[Path, Path]:
        return Path("model.onnx"), Path("tokenizer.json")

    monkeypatch.setattr(config, "download_model", fake_download)
    monkeypatch.setattr(config, "OnnxSentenceEmbedder", lambda *a: TrigramEmbedder())
    monkeypatch.setattr(config, "PgVectorStore", lambda engine: store)
    return store


def test_enabled_retrieval_builds_the_index(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _fake_wiring(monkeypatch)

    resolver = build_symptom_resolver(
        RetrievalSettings(enabled=True), create_engine("sqlite://")
    )

    assert resolver.semantic_enabled is True
    assert store.count(TrigramEmbedder.revision) > 100


def test_failed_model_download_falls_back_to_exact_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken_download(*args: Any) -> tuple[Path, Path]:
        raise OSError("Hugging Face Hub unreachable")

    monkeypatch.setattr(config, "download_model", broken_download)

    resolver = build_symptom_resolver(
        RetrievalSettings(enabled=True), create_engine("sqlite://")
    )

    assert resolver.semantic_enabled is False
    resolved = resolver.resolve("Chest pain")
    assert resolved is not None and resolved.symptom_id == "chest_pain"


def test_evaluation_phrase_set_has_every_group() -> None:
    groups = evaluate.load_phrases()

    assert set(groups) == {"misspelling", "hinglish", "ai_variant", "negative"}
    assert sum(len(items) for items in groups.values()) == 65
    assert all(expected is None for _, expected in groups["negative"])


def test_score_counts_correct_wrong_and_unresolved() -> None:
    groups = {"g": [("Chest pain", "chest_pain"), ("chest pian", "chest_pain")]}
    groups["n"] = [("Headache", None)]

    counts = evaluate.score(groups, SymptomResolver().resolve)

    assert counts == {"g": (1, 0, 1), "n": (0, 1, 0)}
    table = evaluate.format_table([("Exact only", counts)])
    assert table.splitlines()[0] == "| Method | g | n | Wrong total |"
    assert "| Exact only | 1/2 | 0/1 (1 wrong) | 1 |" in table
