"""Measure exact vs exact + semantic resolution on the S2-NIS-7 phrase set.

Responsibilities:
    - Load ``data/eval_phrases.json`` (misspellings, Hinglish, AI-style
      variants, and non-symptoms that must stay unresolved).
    - Count correct, wrong and unresolved answers per group, for exact-only
      matching and for exact + semantic matching at several thresholds.
    - Print a Markdown table for ``docs/vector-retrieval.md``.

Manual tool: it downloads the real model, so it never runs in CI. The unit
tests check ``score`` with a fake embedder.

Usage (from ``server/``)::

    python -m app.services.retrieval.evaluate

Owner: Nisarg (retrieval) · Task: S2-NIS-7 · Requirements: FR-03, NFR-07
"""

import json
from collections.abc import Callable, Sequence
from pathlib import Path

from app.services.retrieval.schemas import ResolvedSymptom

PHRASES_PATH = Path(__file__).parent / "data" / "eval_phrases.json"
THRESHOLDS = (0.6, 0.65, 0.7, 0.75, 0.8)

Resolve = Callable[[str], ResolvedSymptom | None]
Counts = dict[str, tuple[int, int, int]]


def load_phrases(path: Path = PHRASES_PATH) -> dict[str, list[tuple[str, str | None]]]:
    """Phrase groups as ``(name, expected symptom ID or None)`` pairs."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        group: [(item["name"], item["expected"]) for item in items]
        for group, items in data["groups"].items()
    }


def score(groups: dict[str, list[tuple[str, str | None]]], resolve: Resolve) -> Counts:
    """Count ``(correct, wrong, unresolved)`` per group.

    A non-symptom that stays unresolved counts as correct; any symptom ID for
    it counts as wrong.

    Args:
        groups: Output of ``load_phrases``.
        resolve: The resolution function under test.

    Returns:
        Group name -> (correct, wrong, unresolved).
    """
    counts: Counts = {}
    for group, items in groups.items():
        correct = wrong = unresolved = 0
        for name, expected in items:
            result = resolve(name)
            got = result.symptom_id if result else None
            if got == expected:
                correct += 1
            elif got is None:
                unresolved += 1
            else:
                wrong += 1
        counts[group] = (correct, wrong, unresolved)
    return counts


def format_table(rows: Sequence[tuple[str, Counts]]) -> str:
    """Markdown table: one row per method, ``correct/total (wrong)`` per group."""
    groups = list(rows[0][1])
    lines = [
        "| Method | " + " | ".join(groups) + " | Wrong total |",
        "|---|" + "---|" * (len(groups) + 1),
    ]
    for label, counts in rows:
        cells = [
            f"{c}/{c + w + u}" + (f" ({w} wrong)" if w else "")
            for c, w, u in counts.values()
        ]
        wrong = sum(w for _, w, _ in counts.values())
        lines.append(f"| {label} | " + " | ".join(cells) + f" | {wrong} |")
    return "\n".join(lines)


def main() -> int:
    """Run the evaluation with the real model and an in-memory index."""
    # Why: imported here so the unit tests never load the real model.
    from app.services.retrieval.config import RetrievalSettings
    from app.services.retrieval.embedder import OnnxSentenceEmbedder, download_model
    from app.services.retrieval.resolver import SymptomResolver
    from app.services.retrieval.vector_store import InMemoryVectorStore

    settings = RetrievalSettings()
    paths = download_model(
        settings.model_repo,
        settings.model_revision,
        settings.model_file,
        settings.cache_dir,
    )
    embedder = OnnxSentenceEmbedder(*paths, settings.model_revision)
    store = InMemoryVectorStore()
    SymptomResolver(embedder, store).ensure_index()
    groups = load_phrases()
    rows = [("Exact only", score(groups, SymptomResolver().resolve))]
    for threshold in THRESHOLDS:
        resolver = SymptomResolver(embedder, store, threshold=threshold)
        rows.append(
            (f"Exact + semantic ≥ {threshold}", score(groups, resolver.resolve))
        )
    print(format_table(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
