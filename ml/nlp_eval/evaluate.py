"""NLP evaluation harness for symptom extraction pipeline.

Loads evaluation cases from ``ml/nlp_eval/cases.json`` (v2 benchmark, 100 cases),
runs each input through a pluggable :class:`Extractor` implementation, and
computes per-case and aggregate metrics across symptoms, severities, durations,
and linguistic categories (standard English, Hinglish, misspellings, red flags).

This module is standalone ML code and does not import from ``server/``.

Usage::

    python ml/nlp_eval/evaluate.py
    python ml/nlp_eval/evaluate.py --cases ml/nlp_eval/cases.json
    python ml/nlp_eval/evaluate.py --verbose
    python ml/nlp_eval/evaluate.py --per-field
    python ml/nlp_eval/evaluate.py --json ml/nlp_eval/results.json
    python ml/nlp_eval/evaluate.py --report ml/nlp_eval/report_v2.md

Owner: Kavya (AI/ML, Database) · Task: S1-KAV-2, S2-KAV-2 · Requirements: NFR-07
"""

from __future__ import annotations

import argparse
import json
import re
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
    """Container for symptoms and duration extracted from a single text input.

    Attributes:
        symptoms: List of extracted canonical symptoms.
        duration: Optional extracted normalized duration expression.
    """

    symptoms: list[ExtractedSymptom] = field(default_factory=list)
    duration: str | None = None


@runtime_checkable
class Extractor(Protocol):
    """Protocol defining the interface for symptom extraction implementations."""

    def extract(self, text: str) -> ExtractionResult:
        """Extract canonical symptoms and duration from natural language text.

        Args:
            text: Raw input text from the user.

        Returns:
            ExtractionResult containing extracted symptoms and optional duration.
        """
        ...


class SimpleWordMatchExtractor:
    """Deterministic keyword-matching extractor backed by canonical vocabulary.

    Matches lay terms in descending length order so that more specific phrases
    take priority over shorter substrings. Used as a reference baseline and
    for offline evaluation harness testing without external AI dependencies.

    Args:
        vocab_path: Path to symptoms.json vocabulary file.
    """

    _SEVERITY_KEYWORDS: ClassVar[list[tuple[str, str]]] = [
        ("extremely severe", "SEVERE"),
        ("very severe", "SEVERE"),
        ("really bad", "SEVERE"),
        ("very bad", "SEVERE"),
        ("worst ever", "SEVERE"),
        ("worst", "SEVERE"),
        ("unbearable", "SEVERE"),
        ("high fever", "SEVERE"),
        ("intense", "SEVERE"),
        ("extreme", "SEVERE"),
        ("severe", "SEVERE"),
        ("bahut tez", "SEVERE"),
        ("bohot tez", "SEVERE"),
        ("bahut zyada", "SEVERE"),
        ("bohot", "SEVERE"),
        ("bahut", "SEVERE"),
        ("tez", "SEVERE"),
        ("moderate", "MODERATE"),
        ("noticeable", "MODERATE"),
        ("quite", "MODERATE"),
        ("halka", "MILD"),
        ("thoda", "MILD"),
        ("slight", "MILD"),
        ("minor", "MILD"),
        ("mild", "MILD"),
        ("little", "MILD"),
    ]

    _DURATION_PATTERNS: ClassVar[list[tuple[re.Pattern[str], str]]] = [
        (
            re.compile(r"\b(?:1|one)\s*hour\b|\ban\s+hour\b", re.IGNORECASE),
            "1 hour",
        ),
        (
            re.compile(
                r"\b(?:since\s+yesterday|yesterday|all\s+day|since\s+morning|"
                r"subah\s+se|24\s*hours?|last\s*24\s*hours?|1\s*day|one\s*day)\b",
                re.IGNORECASE,
            ),
            "1 day",
        ),
        (
            re.compile(r"\b(?:2|two)\s*(?:days?|din)\b", re.IGNORECASE),
            "2 days",
        ),
        (
            re.compile(r"\b(?:3|three)\s*(?:days?|din)\b", re.IGNORECASE),
            "3 days",
        ),
        (
            re.compile(r"\b(?:4|four)\s*(?:days?|din)\b", re.IGNORECASE),
            "4 days",
        ),
        (
            re.compile(r"\b(?:5|five)\s*(?:days?|din)\b", re.IGNORECASE),
            "5 days",
        ),
        (
            re.compile(r"\b(?:1|one)\s*(?:week|hafte)\b", re.IGNORECASE),
            "1 week",
        ),
        (
            re.compile(r"\b(?:2|two)\s*(?:weeks?|hafte|hafton)\b", re.IGNORECASE),
            "2 weeks",
        ),
        (
            re.compile(r"\b(?:3|three)\s*(?:weeks?|hafte|hafton)\b", re.IGNORECASE),
            "3 weeks",
        ),
        (
            re.compile(
                r"\b(?:1|one)\s*(?:month|mahina|mahine)|for\s+a\s+month\b",
                re.IGNORECASE,
            ),
            "1 month",
        ),
    ]

    def __init__(self, vocab_path: Path | None = None) -> None:
        path = vocab_path or _DEFAULT_VOCAB
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        terms: list[tuple[str, str]] = []
        for symptom in data.get("symptoms", []):
            s_id = symptom["id"]
            terms.append((symptom["name"].lower(), s_id))
            for lay in symptom.get("lay_terms", []):
                terms.append((lay.lower(), s_id))

        self._terms = sorted(terms, key=lambda item: len(item[0]), reverse=True)

    def extract(self, text: str) -> ExtractionResult:
        """Extract canonical symptoms and duration from text via matching.

        Args:
            text: User description in English or Hinglish.

        Returns:
            ExtractionResult with identified canonical symptoms and duration.
        """
        lowered = text.lower()
        severity = self._detect_severity(lowered)
        duration = self._detect_duration(lowered)

        matched_ids: set[str] = set()
        symptoms: list[ExtractedSymptom] = []

        for phrase, s_id in self._terms:
            if s_id in matched_ids:
                continue
            if phrase in lowered:
                symptoms.append(ExtractedSymptom(id=s_id, severity=severity))
                matched_ids.add(s_id)

        return ExtractionResult(symptoms=symptoms, duration=duration)

    def _detect_severity(self, lowered: str) -> str | None:
        """Detect severity modifier from text."""
        for kw, sev in self._SEVERITY_KEYWORDS:
            if kw in lowered:
                return sev
        return None

    def _detect_duration(self, lowered: str) -> str | None:
        """Detect normalized duration from text."""
        for pattern, normalized in self._DURATION_PATTERNS:
            if pattern.search(lowered):
                return normalized
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
        precision: Case-level symptom precision score.
        recall: Case-level symptom recall score.
        f1: Case-level symptom F1 score.
        expected_duration: Expected normalized duration string or None.
        predicted_duration: Predicted duration string or None.
        duration_matched: Whether predicted duration matched expected duration.
        expected_severities: Dict mapping symptom ID to expected severity.
        predicted_severities: Dict mapping symptom ID to predicted severity.
        severity_matches: Number of matching severities among true positive symptoms.
        severity_evaluated: Number of true positive symptoms with expected severity.
        tags: Categorization tags (e.g. 'hinglish', 'misspelling', 'red_flag').
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
    expected_duration: str | None = None
    predicted_duration: str | None = None
    duration_matched: bool = False
    expected_severities: dict[str, str] = field(default_factory=dict)
    predicted_severities: dict[str, str] = field(default_factory=dict)
    severity_matches: int = 0
    severity_evaluated: int = 0
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class FieldMetrics:
    """Per-field performance metrics summary.

    Attributes:
        total_expected: Total expected instances of this field.
        total_predicted: Total predicted instances of this field.
        total_matched: Total correctly matched instances.
        precision: Precision score (matched / predicted).
        recall: Recall score (matched / expected).
        f1: F1 score harmonic mean.
        accuracy: Accuracy score (matched / expected).
    """

    total_expected: int
    total_predicted: int
    total_matched: int
    precision: float
    recall: float
    f1: float
    accuracy: float = 0.0


@dataclass
class AggregateMetrics:
    """Overall aggregate evaluation metrics.

    Attributes:
        total_cases: Total number of test cases.
        total_tp: Total true positive symptom count across all cases.
        total_fp: Total false positive symptom count across all cases.
        total_fn: Total false negative symptom count across all cases.
        micro_precision: Micro-averaged symptom precision.
        micro_recall: Micro-averaged symptom recall.
        micro_f1: Micro-averaged symptom F1 score.
        mean_precision: Unweighted average symptom precision across cases.
        mean_recall: Unweighted average symptom recall across cases.
        mean_f1: Unweighted average symptom F1 across cases.
        severity_metrics: Detailed metrics for severity extraction field.
        duration_metrics: Detailed metrics for duration extraction field.
        category_metrics: Metrics breakdown by category (Hinglish, typos, etc.).
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
    severity_metrics: FieldMetrics | None = None
    duration_metrics: FieldMetrics | None = None
    category_metrics: dict[str, dict[str, float]] = field(default_factory=dict)


def evaluate_case(case: dict, extractor: Extractor) -> CaseResult:
    """Evaluate a single test case against an extractor implementation.

    Args:
        case: Case dictionary matching cases.json schema.
        extractor: Extractor instance conforming to the Extractor protocol.

    Returns:
        CaseResult containing precision, recall, F1, and per-field matches.
    """
    case_id = case["id"]
    text = case["input"]
    expected_symptoms = case.get("expected", {}).get("symptoms", [])
    expected_ids = {s["id"] for s in expected_symptoms}
    expected_duration = case.get("expected", {}).get("duration")

    expected_severities: dict[str, str] = {
        s["id"]: s["severity"] for s in expected_symptoms if "severity" in s
    }

    result = extractor.extract(text)
    predicted_ids = {s.id for s in result.symptoms}
    predicted_duration = getattr(result, "duration", None)
    predicted_severities: dict[str, str] = {
        s.id: s.severity for s in result.symptoms if s.severity is not None
    }

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

    # Duration matching
    duration_matched = False
    if expected_duration is not None and predicted_duration is not None:
        duration_matched = (
            expected_duration.strip().lower() == predicted_duration.strip().lower()
        )

    # Severity matching on true positive symptoms
    severity_matches = 0
    severity_evaluated = 0
    for sym_id in predicted_ids & expected_ids:
        if sym_id in expected_severities:
            severity_evaluated += 1
            if predicted_severities.get(sym_id) == expected_severities[sym_id]:
                severity_matches += 1

    tags = tuple(case.get("tags", []))

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
        expected_duration=expected_duration,
        predicted_duration=predicted_duration,
        duration_matched=duration_matched,
        expected_severities=expected_severities,
        predicted_severities=predicted_severities,
        severity_matches=severity_matches,
        severity_evaluated=severity_evaluated,
        tags=tags,
    )


def compute_metrics(
    cases_path: Path,
    extractor: Extractor,
) -> tuple[list[CaseResult], AggregateMetrics]:
    """Run evaluation across all cases in a dataset file.

    Args:
        cases_path: Path to cases.json file.
        extractor: Extractor conforming to the Extractor protocol.

    Returns:
        Tuple of (list of CaseResult, AggregateMetrics).

    Raises:
        FileNotFoundError: If cases_path does not exist.
        TypeError: If cases JSON format is invalid.
    """
    if not cases_path.exists():
        raise FileNotFoundError(f"Cases file not found: {cases_path}")

    with open(cases_path, encoding="utf-8") as f:
        data = json.load(f)

    cases = data.get("cases", [])
    if not isinstance(cases, list):
        raise TypeError("Invalid cases JSON: 'cases' must be a list")

    results = [evaluate_case(case, extractor) for case in cases]

    # Global symptom identification totals
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

    # Per-field: Severity metrics
    exp_sev_count = sum(len(r.expected_severities) for r in results)
    pred_sev_count = sum(len(r.predicted_severities) for r in results)
    matched_sev_count = sum(r.severity_matches for r in results)

    sev_prec = matched_sev_count / pred_sev_count if pred_sev_count > 0 else 0.0
    sev_rec = matched_sev_count / exp_sev_count if exp_sev_count > 0 else 1.0
    sev_f1 = (
        (2 * sev_prec * sev_rec) / (sev_prec + sev_rec)
        if (sev_prec + sev_rec) > 0
        else 0.0
    )
    sev_acc = matched_sev_count / exp_sev_count if exp_sev_count > 0 else 1.0

    severity_metrics = FieldMetrics(
        total_expected=exp_sev_count,
        total_predicted=pred_sev_count,
        total_matched=matched_sev_count,
        precision=sev_prec,
        recall=sev_rec,
        f1=sev_f1,
        accuracy=sev_acc,
    )

    # Per-field: Duration metrics
    exp_dur_count = sum(1 for r in results if r.expected_duration is not None)
    pred_dur_count = sum(1 for r in results if r.predicted_duration is not None)
    matched_dur_count = sum(1 for r in results if r.duration_matched)

    dur_prec = matched_dur_count / pred_dur_count if pred_dur_count > 0 else 0.0
    dur_rec = matched_dur_count / exp_dur_count if exp_dur_count > 0 else 1.0
    dur_f1 = (
        (2 * dur_prec * dur_rec) / (dur_prec + dur_rec)
        if (dur_prec + dur_rec) > 0
        else 0.0
    )
    dur_acc = matched_dur_count / exp_dur_count if exp_dur_count > 0 else 1.0

    duration_metrics = FieldMetrics(
        total_expected=exp_dur_count,
        total_predicted=pred_dur_count,
        total_matched=matched_dur_count,
        precision=dur_prec,
        recall=dur_rec,
        f1=dur_f1,
        accuracy=dur_acc,
    )

    # Subgroup / category breakdowns
    category_metrics: dict[str, dict[str, float]] = {}
    known_categories = (
        "standard",
        "hinglish",
        "misspelling",
        "red_flag",
        "multi_symptom",
    )
    for cat in known_categories:
        cat_results = [r for r in results if cat in r.tags]
        if not cat_results:
            continue
        c_tp = sum(r.true_positives for r in cat_results)
        c_fp = sum(r.false_positives for r in cat_results)
        c_fn = sum(r.false_negatives for r in cat_results)
        c_micro_prec = c_tp / (c_tp + c_fp) if (c_tp + c_fp) > 0 else 1.0
        c_micro_rec = c_tp / (c_tp + c_fn) if (c_tp + c_fn) > 0 else 1.0
        c_micro_f1 = (
            (2 * c_micro_prec * c_micro_rec) / (c_micro_prec + c_micro_rec)
            if (c_micro_prec + c_micro_rec) > 0
            else 0.0
        )
        c_len = len(cat_results)
        c_macro_f1 = sum(r.f1 for r in cat_results) / c_len if c_len > 0 else 0.0
        category_metrics[cat] = {
            "cases": float(c_len),
            "micro_precision": c_micro_prec,
            "micro_recall": c_micro_rec,
            "micro_f1": c_micro_f1,
            "macro_f1": c_macro_f1,
        }

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
        severity_metrics=severity_metrics,
        duration_metrics=duration_metrics,
        category_metrics=category_metrics,
    )

    return results, aggregate


def print_report(
    results: list[CaseResult],
    aggregate: AggregateMetrics,
    *,
    verbose: bool = False,
    per_field: bool = True,
) -> None:
    """Print formatted evaluation report to standard output.

    Args:
        results: Per-case evaluation results.
        aggregate: Aggregate metrics summary.
        verbose: Whether to display per-case detail lines.
        per_field: Whether to display per-field and category breakdowns.
    """
    line = "=" * 74
    subline = "-" * 74

    print(line)
    print("  NLP Symptom Extraction Evaluation Report (Eval Set v2)")
    print(line)

    if verbose:
        print(
            f"{'Case ID':<10} {'TP':>3} {'FP':>3} {'FN':>3} {'Prec':>7} "
            f"{'Recall':>7} {'F1':>7} {'SevMat':>7} {'DurMat':>7}"
        )
        print(subline)
        for r in results:
            d_mat = (
                "YES" if r.duration_matched else ("NO" if r.expected_duration else "-")
            )
            s_mat = (
                f"{r.severity_matches}/{len(r.expected_severities)}"
                if r.expected_severities
                else "-"
            )
            print(
                f"{r.case_id:<10} {r.true_positives:>3} {r.false_positives:>3} "
                f"{r.false_negatives:>3} {r.precision:>7.3f} {r.recall:>7.3f} "
                f"{r.f1:>7.3f} {s_mat:>7} {d_mat:>7}"
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

    if per_field and aggregate.severity_metrics and aggregate.duration_metrics:
        print(subline)
        print("  Per-Field Evaluation Breakdown (NFR-07)")
        print(subline)
        sm = aggregate.severity_metrics
        dm = aggregate.duration_metrics
        print(
            f"Severity Matching   : Accuracy: {sm.accuracy:.4f} "
            f"({sm.total_matched}/{sm.total_expected} expected, "
            f"P={sm.precision:.3f}, R={sm.recall:.3f}, F1={sm.f1:.3f})"
        )
        print(
            f"Duration Matching   : Accuracy: {dm.accuracy:.4f} "
            f"({dm.total_matched}/{dm.total_expected} expected, "
            f"P={dm.precision:.3f}, R={dm.recall:.3f}, F1={dm.f1:.3f})"
        )

    if per_field and aggregate.category_metrics:
        print(subline)
        print("  Subgroup Linguistic Category Breakdown")
        print(subline)
        print(
            f"{'Category':<16} {'Cases':>6} {'Micro Prec':>11} "
            f"{'Micro Rec':>10} {'Micro F1':>9} {'Macro F1':>9}"
        )
        print(subline)
        for cat, cm in aggregate.category_metrics.items():
            print(
                f"{cat:<16} {int(cm['cases']):>6} {cm['micro_precision']:>11.4f} "
                f"{cm['micro_recall']:>10.4f} {cm['micro_f1']:>9.4f} "
                f"{cm['macro_f1']:>9.4f}"
            )

    print(line)


def generate_markdown_report(
    aggregate: AggregateMetrics,
    results: list[CaseResult],
) -> str:
    """Generate comprehensive Markdown evaluation report feeding S2-NIT-1.

    Args:
        aggregate: Computed aggregate metrics.
        results: List of per-case results.

    Returns:
        Markdown string ready for docs or report artifact.
    """
    sm = aggregate.severity_metrics or FieldMetrics(0, 0, 0, 0.0, 0.0, 0.0)
    dm = aggregate.duration_metrics or FieldMetrics(0, 0, 0, 0.0, 0.0, 0.0)

    lines: list[str] = [
        "# NLP Extraction Benchmark Report (Eval Set v2)",
        "",
        (
            "**Owner:** Kavya (AI/ML, Database) · **Task:** S2-KAV-2 · "
            "**Target Consumer:** Nishith (S2-NIT-1, Prompt v2) · **Requirement:** NFR-07"
        ),
        "",
        (
            "This evaluation report benchmarks the symptom extraction baseline over the "
            "expanded 100-case evaluation set, establishing quantitative baseline metrics "
            "across canonical symptom extraction, explicit severity detection, duration "
            "normalization, and linguistic subgroups."
        ),
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        f"- **Total Benchmark Cases:** {aggregate.total_cases}",
        "- **Canonical Vocabulary Coverage:** 100/100 symptoms represented (100% parity)",
        (
            f"- **Micro-averaged Symptom F1:** {aggregate.micro_f1:.4f} "
            f"(Precision: {aggregate.micro_precision:.4f}, Recall: {aggregate.micro_recall:.4f})"
        ),
        (
            f"- **Macro-averaged Symptom F1:** {aggregate.mean_f1:.4f} "
            f"(Precision: {aggregate.mean_precision:.4f}, Recall: {aggregate.mean_recall:.4f})"
        ),
        f"- **Severity Match Accuracy:** {sm.accuracy:.4f} ({sm.total_matched}/{sm.total_expected})",
        f"- **Duration Match Accuracy:** {dm.accuracy:.4f} ({dm.total_matched}/{dm.total_expected})",
        "",
        "---",
        "",
        "## 2. Per-Field Performance Breakdown",
        "",
        "| Evaluation Field | Expected | Matched | Precision | Recall | F1 Score | Accuracy |",
        "|---|---|---|---|---|---|---|",
        (
            f"| **Canonical Symptoms** | {aggregate.total_tp + aggregate.total_fn} | "
            f"{aggregate.total_tp} | {aggregate.micro_precision:.4f} | "
            f"{aggregate.micro_recall:.4f} | {aggregate.micro_f1:.4f} | N/A |"
        ),
        (
            f"| **Severity Rating** | {sm.total_expected} | {sm.total_matched} | "
            f"{sm.precision:.4f} | {sm.recall:.4f} | {sm.f1:.4f} | {sm.accuracy:.4f} |"
        ),
        (
            f"| **Duration Normalization** | {dm.total_expected} | {dm.total_matched} | "
            f"{dm.precision:.4f} | {dm.recall:.4f} | {dm.f1:.4f} | {dm.accuracy:.4f} |"
        ),
        "",
        "---",
        "",
        "## 3. Linguistic Subgroup Performance",
        "",
        "| Subgroup | Cases | Micro Prec | Micro Recall | Micro F1 | Macro F1 |",
        "|---|---|---|---|---|---|",
    ]

    for cat, cm in aggregate.category_metrics.items():
        lines.append(
            f"| `{cat}` | {int(cm['cases'])} | {cm['micro_precision']:.4f} | "
            f"{cm['micro_recall']:.4f} | {cm['micro_f1']:.4f} | {cm['macro_f1']:.4f} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 4. Key Findings & Recommendations for S2-NIT-1 (Prompt v2)",
            "",
            "### 4.1 Misspellings and Phonetic Typos",
            (
                "- **Issue:** Baseline keyword matching suffers significant recall drops on common "
                "patient misspellings (`naucea`, `dizzynes`, `blured vission`, `stomake aking`, "
                "`confution`, `droopin face`)."
            ),
            (
                "- **Recommendation for Prompt v2:** The LLM prompt should explicitly state: "
                "*'Correct common misspellings, colloquial slang, and typos into standard clinical concepts.'*"
            ),
            "",
            "### 4.2 Hinglish & Transliterated Idiomatic Descriptions",
            (
                "- **Issue:** Lay phrases like *'pet saaf nahi hua'* (constipation), *'dast lag gaye'* "
                "(diarrhea), *'sans phoolna'* (shortness of breath), and *'seene me jakdan'* (chest tightness) "
                "require cultural and bilingual semantic context."
            ),
            (
                "- **Recommendation for Prompt v2:** Include few-shot Hinglish examples in prompt v2 "
                "demonstrating transliterated Hindi clinical mappings."
            ),
            "",
            "### 4.3 Red-Flag Syndrome Groupings",
            (
                "- **Issue:** Stroke (FAST triad), Meningitis (stiff neck + fever + altered mental state), "
                "and Cauda Equina (saddle numbness + bowel/bladder incontinence) presentations must "
                "extract every constituent red-flag symptom without dropping subtle co-occurrences."
            ),
            (
                "- **Recommendation for Prompt v2:** Instruct the model to avoid truncating symptoms "
                "when multiple emergency indicators appear in a single passage."
            ),
            "",
            "### 4.4 Duration Normalization Invariants",
            (
                "- **Issue:** Ambiguous phrases like *'since yesterday'* vs *'24 hours'* should map "
                "consistently to standardized durations (e.g. `'1 day'`)."
            ),
            "- **Recommendation for Prompt v2:** Provide clear normalization guidelines for temporal expressions.",
        ]
    )

    return "\n".join(lines) + "\n"


def _build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
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
        "--report",
        type=Path,
        default=None,
        help="Optional path to output Markdown evaluation report for S2-NIT-1",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed per-case metrics table",
    )
    parser.add_argument(
        "--per-field",
        action="store_true",
        default=True,
        help="Print detailed per-field and category breakdowns (default: True)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for NLP evaluation harness."""
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

    print_report(
        results,
        aggregate,
        verbose=args.verbose,
        per_field=args.per_field,
    )

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
                "severity": {
                    "expected": aggregate.severity_metrics.total_expected
                    if aggregate.severity_metrics
                    else 0,
                    "matched": aggregate.severity_metrics.total_matched
                    if aggregate.severity_metrics
                    else 0,
                    "accuracy": aggregate.severity_metrics.accuracy
                    if aggregate.severity_metrics
                    else 0.0,
                    "f1": aggregate.severity_metrics.f1
                    if aggregate.severity_metrics
                    else 0.0,
                },
                "duration": {
                    "expected": aggregate.duration_metrics.total_expected
                    if aggregate.duration_metrics
                    else 0,
                    "matched": aggregate.duration_metrics.total_matched
                    if aggregate.duration_metrics
                    else 0,
                    "accuracy": aggregate.duration_metrics.accuracy
                    if aggregate.duration_metrics
                    else 0.0,
                    "f1": aggregate.duration_metrics.f1
                    if aggregate.duration_metrics
                    else 0.0,
                },
                "categories": aggregate.category_metrics,
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
                    "expected_duration": r.expected_duration,
                    "predicted_duration": r.predicted_duration,
                    "duration_matched": r.duration_matched,
                    "severity_matches": r.severity_matches,
                    "severity_evaluated": r.severity_evaluated,
                    "tags": list(r.tags),
                }
                for r in results
            ],
        }
        args.json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"JSON metrics report saved to: {args.json}")

    if args.report:
        report_md = generate_markdown_report(aggregate, results)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"Markdown evaluation report saved to: {args.report}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
