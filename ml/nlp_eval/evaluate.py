"""NLP evaluation harness for symptom extraction pipeline.

Loads evaluation cases from ``ml/nlp_eval/cases.json``, runs each input
through a pluggable :class:`Extractor` implementation, and computes
per-case and aggregate precision, recall, and F1 scores.

This module is standalone ML code and does not import from ``server/``.

Usage::

    python ml/nlp_eval/evaluate.py
    python ml/nlp_eval/evaluate.py --cases ml/nlp_eval/cases.json
    python ml/nlp_eval/evaluate.py --verbose

Owner: Kavya (AI/ML, Database) · Task: S1-KAV-2 · Requirements: NFR-07
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Protocol, runtime_checkable

_HERE = Path(__file__).resolve().parent
_DEFAULT_CASES = _HERE / "cases.json"
_DEFAULT_VOCAB = _HERE.parent / "datasets" / "symptoms" / "symptoms.json"


@dataclass
class ExtractedSymptom:
    """A canonical symptom extracted from free-text input.

    Attributes:
        id: Canonical symptom ID (snake_case).
        severity: Optional severity rating (MILD, MODERATE, SEVERE).
    """

    id: str
    severity: str | None = None


@dataclass
class ExtractionResult:
    """Container for symptoms extracted from a single text input.

    Attributes:
        symptoms: List of extracted canonical symptoms.
    """

    symptoms: list[ExtractedSymptom] = field(default_factory=list)


@runtime_checkable
class Extractor(Protocol):
    """Protocol defining the interface for symptom extraction implementations."""

    def extract(self, text: str) -> ExtractionResult:
        """Extract canonical symptoms from natural language text.

        Args:
            text: Raw input text from the user.

        Returns:
            ExtractionResult containing extracted canonical symptoms.
        """
        ...


class SimpleWordMatchExtractor:
    """Deterministic keyword-matching extractor backed by the canonical vocabulary.

    Matches lay terms in descending length order so that more specific phrases
    take priority over shorter substrings. Used as a reference baseline and
    for offline evaluation harness testing without external AI dependencies.

    Args:
        vocab_path: Path to symptoms.json vocabulary file.
    """

    _SEVERITY_KEYWORDS: ClassVar[list[tuple[str, str]]] = [
        ("very severe", "SEVERE"),
        ("extremely severe", "SEVERE"),
        ("worst", "SEVERE"),
        ("really bad", "SEVERE"),
        ("very bad", "SEVERE"),
        ("tez", "SEVERE"),
        ("bahut", "SEVERE"),
        ("high fever", "SEVERE"),
        ("severe", "SEVERE"),
        ("extreme", "SEVERE"),
        ("intense", "SEVERE"),
        ("moderate", "MODERATE"),
        ("noticeable", "MODERATE"),
        ("halka", "MILD"),
        ("mild", "MILD"),
        ("slight", "MILD"),
        ("little", "MILD"),
    ]

    def __init__(self, vocab_path: Path | None = None) -> None:
        path = vocab_path or _DEFAULT_VOCAB
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        terms: list[tuple[str, str]] = []
        for symptom in data.get("symptoms", []):
            s_id = symptom["id"]
            # Also include symptom name lowercase
            terms.append((symptom["name"].lower(), s_id))
            for lay in symptom.get("lay_terms", []):
                terms.append((lay.lower(), s_id))

        # Sort by phrase length descending to match longest phrases first
        self._terms = sorted(terms, key=lambda item: len(item[0]), reverse=True)

    def extract(self, text: str) -> ExtractionResult:
        """Extract canonical symptoms from user text via lay term matching.

        Args:
            text: User description in English or Hinglish.

        Returns:
            ExtractionResult with identified canonical symptoms.
        """
        lowered = text.lower()
        severity = self._detect_severity(lowered)

        matched_ids: set[str] = set()
        symptoms: list[ExtractedSymptom] = []

        for phrase, s_id in self._terms:
            if s_id in matched_ids:
                continue
            if phrase in lowered:
                symptoms.append(ExtractedSymptom(id=s_id, severity=severity))
                matched_ids.add(s_id)

        return ExtractionResult(symptoms=symptoms)

    def _detect_severity(self, lowered: str) -> str | None:
        """Detect severity modifier from text.

        Args:
            lowered: Lowercase input text.

        Returns:
            Canonical severity string or None.
        """
        for kw, sev in self._SEVERITY_KEYWORDS:
            if kw in lowered:
                return sev
        return None


@dataclass
class CaseResult:
    """Evaluation result for an individual evaluation case.

    Attributes:
        case_id: Unique case identifier.
        expected_ids: Expected canonical symptom IDs.
        predicted_ids: Predicted canonical symptom IDs.
        true_positives: Count of correctly predicted symptoms.
        false_positives: Count of falsely predicted symptoms.
        false_negatives: Count of missed expected symptoms.
        precision: Case-level precision score.
        recall: Case-level recall score.
        f1: Case-level F1 score.
    """

    case_id: str
    expected_ids: set[str]
    predicted_ids: set[str]
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float


@dataclass
class AggregateMetrics:
    """Overall aggregate evaluation metrics.

    Attributes:
        total_cases: Total number of test cases.
        total_tp: Total true positive count across all cases.
        total_fp: Total false positive count across all cases.
        total_fn: Total false negative count across all cases.
        micro_precision: Micro-averaged precision.
        micro_recall: Micro-averaged recall.
        micro_f1: Micro-averaged F1 score.
        mean_precision: Unweighted average precision across cases.
        mean_recall: Unweighted average recall across cases.
        mean_f1: Unweighted average F1 across cases.
    """

    total_cases: int
    total_tp: int
    total_fp: int
    total_fn: int
    micro_precision: float
    micro_recall: float
    micro_f1: float
    mean_precision: float
    mean_recall: float
    mean_f1: float


def evaluate_case(case: dict, extractor: Extractor) -> CaseResult:
    """Evaluate a single test case against an extractor.

    Args:
        case: Case dictionary matching cases.json schema.
        extractor: Extractor instance conforming to the Extractor protocol.

    Returns:
        CaseResult containing precision, recall, and F1 for the case.
    """
    case_id = case["id"]
    text = case["input"]
    expected_symptoms = case.get("expected", {}).get("symptoms", [])
    expected_ids = {s["id"] for s in expected_symptoms}

    result = extractor.extract(text)
    predicted_ids = {s.id for s in result.symptoms}

    tp = len(predicted_ids & expected_ids)
    fp = len(predicted_ids - expected_ids)
    fn = len(expected_ids - predicted_ids)

    precision = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if not expected_ids else 0.0)
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = (
        (2 * precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return CaseResult(
        case_id=case_id,
        expected_ids=expected_ids,
        predicted_ids=predicted_ids,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        precision=precision,
        recall=recall,
        f1=f1,
    )


def compute_metrics(
    cases_path: Path,
    extractor: Extractor,
) -> tuple[list[CaseResult], AggregateMetrics]:
    """Run evaluation across all cases in a dataset file.

    Args:
        cases_path: Path to cases.json file.
        extractor: Extractor instance conforming to the Extractor protocol.

    Returns:
        Tuple of (list of CaseResult, AggregateMetrics).

    Raises:
        FileNotFoundError: If cases_path does not exist.
        ValueError: If cases JSON format is invalid.
    """
    if not cases_path.exists():
        raise FileNotFoundError(f"Cases file not found: {cases_path}")

    with open(cases_path, encoding="utf-8") as f:
        data = json.load(f)

    cases = data.get("cases", [])
    if not isinstance(cases, list):
        raise TypeError("Invalid cases JSON: 'cases' must be a list")

    results = [evaluate_case(case, extractor) for case in cases]

    total_tp = sum(r.true_positives for r in results)
    total_fp = sum(r.false_positives for r in results)
    total_fn = sum(r.false_negatives for r in results)

    micro_precision = (
        total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 1.0
    )
    micro_recall = (
        total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 1.0
    )
    micro_f1 = (
        (2 * micro_precision * micro_recall) / (micro_precision + micro_recall)
        if (micro_precision + micro_recall) > 0
        else 0.0
    )

    n = len(results)
    mean_precision = sum(r.precision for r in results) / n if n > 0 else 0.0
    mean_recall = sum(r.recall for r in results) / n if n > 0 else 0.0
    mean_f1 = sum(r.f1 for r in results) / n if n > 0 else 0.0

    aggregate = AggregateMetrics(
        total_cases=n,
        total_tp=total_tp,
        total_fp=total_fp,
        total_fn=total_fn,
        micro_precision=micro_precision,
        micro_recall=micro_recall,
        micro_f1=micro_f1,
        mean_precision=mean_precision,
        mean_recall=mean_recall,
        mean_f1=mean_f1,
    )

    return results, aggregate


def print_report(
    results: list[CaseResult],
    aggregate: AggregateMetrics,
    *,
    verbose: bool = False,
) -> None:
    """Print a formatted evaluation report to standard output.

    Args:
        results: Per-case evaluation results.
        aggregate: Aggregate metrics summary.
        verbose: Whether to display per-case detail lines.
    """
    line = "=" * 70
    subline = "-" * 70

    print(line)
    print("  NLP Symptom Extraction Evaluation Report")
    print(line)

    if verbose:
        print(
            f"{'Case ID':<12} {'TP':>4} {'FP':>4} {'FN':>4} {'Prec':>8} {'Recall':>8} {'F1':>8}"
        )
        print(subline)
        for r in results:
            print(
                f"{r.case_id:<12} {r.true_positives:>4} {r.false_positives:>4} {r.false_negatives:>4} "
                f"{r.precision:>8.3f} {r.recall:>8.3f} {r.f1:>8.3f}"
            )
        print(subline)

    print(f"Total Cases Evaluated : {aggregate.total_cases}")
    print(f"Total True Positives  : {aggregate.total_tp}")
    print(f"Total False Positives : {aggregate.total_fp}")
    print(f"Total False Negatives : {aggregate.total_fn}")
    print(subline)
    print(f"Micro-averaged Precision : {aggregate.micro_precision:.4f}")
    print(f"Micro-averaged Recall    : {aggregate.micro_recall:.4f}")
    print(f"Micro-averaged F1 Score  : {aggregate.micro_f1:.4f}")
    print(subline)
    print(f"Macro-averaged Precision : {aggregate.mean_precision:.4f}")
    print(f"Macro-averaged Recall    : {aggregate.mean_recall:.4f}")
    print(f"Macro-averaged F1 Score  : {aggregate.mean_f1:.4f}")
    print(line)


def _build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser.

    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        description="NLP symptom extraction evaluation harness (precision/recall/F1 report)."
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=_DEFAULT_CASES,
        help=f"Path to evaluation cases JSON (default: {_DEFAULT_CASES})",
    )
    parser.add_argument(
        "--vocab",
        type=Path,
        default=_DEFAULT_VOCAB,
        help=f"Path to canonical symptoms JSON (default: {_DEFAULT_VOCAB})",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Optional path to output JSON evaluation metrics summary",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed per-case metrics table",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for NLP evaluation harness.

    Args:
        argv: Command-line arguments. Defaults to sys.argv[1:].

    Returns:
        Exit code: 0 on success, 1 on error.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.cases.exists():
        print(f"Error: Cases file not found at {args.cases}", file=sys.stderr)
        return 1

    if not args.vocab.exists():
        print(f"Error: Vocabulary file not found at {args.vocab}", file=sys.stderr)
        return 1

    extractor = SimpleWordMatchExtractor(vocab_path=args.vocab)

    try:
        results, aggregate = compute_metrics(args.cases, extractor)
    except Exception as exc:  # noqa: BLE001
        print(f"Error running evaluation: {exc}", file=sys.stderr)
        return 1

    print_report(results, aggregate, verbose=args.verbose)

    if args.json:
        payload = {
            "aggregate": {
                "total_cases": aggregate.total_cases,
                "total_tp": aggregate.total_tp,
                "total_fp": aggregate.total_fp,
                "total_fn": aggregate.total_fn,
                "micro_precision": aggregate.micro_precision,
                "micro_recall": aggregate.micro_recall,
                "micro_f1": aggregate.micro_f1,
                "mean_precision": aggregate.mean_precision,
                "mean_recall": aggregate.mean_recall,
                "mean_f1": aggregate.mean_f1,
            },
            "cases": [
                {
                    "case_id": r.case_id,
                    "expected": sorted(r.expected_ids),
                    "predicted": sorted(r.predicted_ids),
                    "tp": r.true_positives,
                    "fp": r.false_positives,
                    "fn": r.false_negatives,
                    "precision": r.precision,
                    "recall": r.recall,
                    "f1": r.f1,
                }
                for r in results
            ],
        }
        args.json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"JSON metrics report saved to: {args.json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
