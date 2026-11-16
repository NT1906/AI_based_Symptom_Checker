"""Tests for the NLP evaluation harness.

Covers happy paths, edge cases, metric accuracy, per-field metrics, duration and
severity extraction, category breakdowns, protocol compliance, CLI behavior,
and full integration with the 100-case v2 benchmark dataset.

Owner: Kavya (AI/ML, Database) · Tasks: S1-KAV-2, S2-KAV-2 · Requirements: NFR-07
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Module import (supports both root-level and ml-level test runs)
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
_EVAL_FILE = _HERE / "evaluate.py"

_spec = importlib.util.spec_from_file_location("evaluate", _EVAL_FILE)
assert _spec is not None and _spec.loader is not None, (
    f"Failed to load spec for {_EVAL_FILE}"
)
_evaluate_mod = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("evaluate", _evaluate_mod)
_spec.loader.exec_module(_evaluate_mod)

AggregateMetrics = _evaluate_mod.AggregateMetrics
CaseResult = _evaluate_mod.CaseResult
ExtractionResult = _evaluate_mod.ExtractionResult
ExtractedSymptom = _evaluate_mod.ExtractedSymptom
Extractor = _evaluate_mod.Extractor
FieldMetrics = _evaluate_mod.FieldMetrics
SimpleWordMatchExtractor = _evaluate_mod.SimpleWordMatchExtractor
compute_metrics = _evaluate_mod.compute_metrics
evaluate_case = _evaluate_mod.evaluate_case
generate_markdown_report = _evaluate_mod.generate_markdown_report
main = _evaluate_mod.main
print_report = _evaluate_mod.print_report

_CASES_PATH = _HERE / "cases.json"
_VOCAB_PATH = _HERE.parent / "datasets" / "symptoms" / "symptoms.json"


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------


class _MockFixedExtractor:
    """Mock extractor returning a fixed set of canonical symptom IDs."""

    def __init__(
        self,
        symptom_ids: list[str],
        duration: str | None = None,
        severity: str | None = None,
    ) -> None:
        self.symptom_ids = symptom_ids
        self.duration = duration
        self.severity = severity

    def extract(self, text: str) -> ExtractionResult:
        return ExtractionResult(
            symptoms=[
                ExtractedSymptom(id=s_id, severity=self.severity)
                for s_id in self.symptom_ids
            ],
            duration=self.duration,
        )


def _build_test_case(
    case_id: str,
    text: str,
    expected_ids: list[str],
    *,
    duration: str | None = None,
    severities: dict[str, str] | None = None,
    tags: list[str] | None = None,
) -> dict:
    symptoms: list[dict] = []
    sev_map = severities or {}
    for sid in expected_ids:
        s_dict: dict = {"id": sid}
        if sid in sev_map:
            s_dict["severity"] = sev_map[sid]
        symptoms.append(s_dict)

    expected: dict = {"symptoms": symptoms}
    if duration:
        expected["duration"] = duration
    case_dict: dict = {"id": case_id, "input": text, "expected": expected}
    if tags:
        case_dict["tags"] = tags
    return case_dict


# ---------------------------------------------------------------------------
# Unit Tests: Protocol & Extractor
# ---------------------------------------------------------------------------


def test_simple_extractor_satisfies_protocol() -> None:
    """Verify SimpleWordMatchExtractor conforms to the Extractor runtime protocol."""
    extractor = SimpleWordMatchExtractor(vocab_path=_VOCAB_PATH)
    assert isinstance(extractor, Extractor)


@pytest.mark.parametrize(
    ("input_text", "expected_symptom_id"),
    [
        ("I have a high fever today", "fever"),
        ("severe chest pain", "chest_pain"),
        ("I have throat pain", "sore_throat"),
        ("I feel dizzy and weak", "dizziness"),
        ("itchy skin with rash", "skin_rash"),
        ("loose motions since morning", "diarrhea"),
        ("burning when peeing", "burning_urination"),
        ("shortness of breath", "shortness_of_breath"),
    ],
)
def test_simple_extractor_matches_lay_terms(
    input_text: str, expected_symptom_id: str
) -> None:
    """Verify keyword extractor maps lay phrases to expected canonical IDs."""
    extractor = SimpleWordMatchExtractor(vocab_path=_VOCAB_PATH)
    res = extractor.extract(input_text)
    extracted_ids = {s.id for s in res.symptoms}
    assert expected_symptom_id in extracted_ids


@pytest.mark.parametrize(
    ("input_text", "expected_severity"),
    [
        ("I have severe abdominal pain", "SEVERE"),
        ("really bad headache", "SEVERE"),
        ("bahut dard ho raha hai", "SEVERE"),
        ("moderate joint pain", "MODERATE"),
        ("mild fever since evening", "MILD"),
        ("halka bukhar hai", "MILD"),
        ("I have a cough", None),
    ],
)
def test_simple_extractor_severity_detection(
    input_text: str, expected_severity: str | None
) -> None:
    """Verify keyword extractor detects intensity modifiers accurately."""
    extractor = SimpleWordMatchExtractor(vocab_path=_VOCAB_PATH)
    res = extractor.extract(input_text)
    if res.symptoms:
        assert res.symptoms[0].severity == expected_severity


@pytest.mark.parametrize(
    ("input_text", "expected_duration"),
    [
        ("I have had fever since yesterday", "1 day"),
        ("headache for 24 hours", "1 day"),
        ("cough for 2 days", "2 days"),
        ("chest pain for 3 days", "3 days"),
        ("dizziness for 4 days", "4 days"),
        ("nausea for 5 days", "5 days"),
        ("rash for 1 week", "1 week"),
        ("joint swelling for 2 weeks", "2 weeks"),
        ("fatigue for 3 weeks", "3 weeks"),
        ("weight loss for 1 month", "1 month"),
        ("vision loss about an hour ago", "1 hour"),
        ("no mention of time here", None),
    ],
)
def test_simple_extractor_duration_detection(
    input_text: str, expected_duration: str | None
) -> None:
    """Verify keyword extractor normalizes temporal duration expressions."""
    extractor = SimpleWordMatchExtractor(vocab_path=_VOCAB_PATH)
    res = extractor.extract(input_text)
    assert res.duration == expected_duration


def test_simple_extractor_avoids_duplicate_symptom_ids() -> None:
    """Verify extractor does not return duplicate entries for the same ID."""
    extractor = SimpleWordMatchExtractor(vocab_path=_VOCAB_PATH)
    res = extractor.extract("I have chest pain, chest discomfort, and chest ache")
    symptom_ids = [s.id for s in res.symptoms]
    assert symptom_ids.count("chest_pain") == 1


def test_simple_extractor_handles_empty_string() -> None:
    """Empty or whitespace input returns empty extraction result."""
    extractor = SimpleWordMatchExtractor(vocab_path=_VOCAB_PATH)
    res = extractor.extract("   ")
    assert res.symptoms == []
    assert res.duration is None


# ---------------------------------------------------------------------------
# Unit Tests: Evaluation Scoring & Per-Field Metrics
# ---------------------------------------------------------------------------


def test_evaluate_case_perfect_match() -> None:
    """When predictions exactly match expectations, P=1.0, R=1.0, F1=1.0."""
    case = _build_test_case(
        "case_001",
        "chest pain and fever",
        ["chest_pain", "fever"],
        duration="1 day",
        severities={"chest_pain": "SEVERE"},
    )
    mock = _MockFixedExtractor(
        ["chest_pain", "fever"], duration="1 day", severity="SEVERE"
    )
    result = evaluate_case(case, mock)
    assert result.precision == 1.0
    assert result.recall == 1.0
    assert result.f1 == 1.0
    assert result.true_positives == 2
    assert result.false_positives == 0
    assert result.false_negatives == 0
    assert result.duration_matched is True
    assert result.severity_matches == 1
    assert result.severity_evaluated == 1


def test_evaluate_case_false_negatives_only() -> None:
    """When extractor predicts a strict subset of expected symptoms."""
    case = _build_test_case(
        "case_002", "cough fever chills", ["cough", "fever", "chills"]
    )
    mock = _MockFixedExtractor(["cough"])
    result = evaluate_case(case, mock)
    assert result.true_positives == 1
    assert result.false_positives == 0
    assert result.false_negatives == 2
    assert result.precision == 1.0
    assert result.recall == pytest.approx(1 / 3)
    assert result.f1 == pytest.approx(0.5)


def test_evaluate_case_false_positives_only() -> None:
    """When extractor predicts symptoms not in expectations."""
    case = _build_test_case("case_003", "cough", ["cough"])
    mock = _MockFixedExtractor(["cough", "fever", "fatigue"])
    result = evaluate_case(case, mock)
    assert result.true_positives == 1
    assert result.false_positives == 2
    assert result.false_negatives == 0
    assert result.precision == pytest.approx(1 / 3)
    assert result.recall == 1.0
    assert result.f1 == pytest.approx(0.5)


def test_evaluate_case_zero_overlap() -> None:
    """When predicted symptoms share zero overlap with expected symptoms."""
    case = _build_test_case("case_004", "cough", ["cough"])
    mock = _MockFixedExtractor(["headache"])
    result = evaluate_case(case, mock)
    assert result.true_positives == 0
    assert result.false_positives == 1
    assert result.false_negatives == 1
    assert result.precision == 0.0
    assert result.recall == 0.0
    assert result.f1 == 0.0


def test_evaluate_case_empty_predictions_and_expectations() -> None:
    """Edge case: empty expected and predicted symptoms yields 1.0."""
    case = _build_test_case("case_005", "nothing", [])
    mock = _MockFixedExtractor([])
    result = evaluate_case(case, mock)
    assert result.precision == 1.0
    assert result.recall == 1.0
    assert result.f1 == 1.0


def test_evaluate_case_duration_mismatch() -> None:
    """When predicted duration differs from expected, duration_matched is False."""
    case = _build_test_case("case_006", "text", ["fever"], duration="3 days")
    mock = _MockFixedExtractor(["fever"], duration="1 day")
    result = evaluate_case(case, mock)
    assert result.duration_matched is False
    assert result.expected_duration == "3 days"
    assert result.predicted_duration == "1 day"


def test_compute_metrics_aggregates_totals(tmp_path: Path) -> None:
    """Verify compute_metrics properly aggregates micro/macro metrics and categories."""
    cases = [
        _build_test_case(
            "case_001",
            "t1",
            ["fever", "cough"],
            duration="1 day",
            severities={"fever": "SEVERE"},
            tags=["standard", "multi_symptom"],
        ),
        _build_test_case(
            "case_002",
            "t2",
            ["headache"],
            duration="2 days",
            tags=["hinglish"],
        ),
    ]
    test_cases_file = tmp_path / "test_cases.json"
    with open(test_cases_file, "w", encoding="utf-8") as f:
        json.dump({"schema_version": "1.0", "cases": cases}, f)

    # Mock predicts fever and headache, duration "1 day", severity "SEVERE"
    mock = _MockFixedExtractor(
        ["fever", "headache"], duration="1 day", severity="SEVERE"
    )
    results, agg = compute_metrics(test_cases_file, mock)

    assert len(results) == 2
    assert agg.total_cases == 2
    assert agg.total_tp == 2  # fever in c1, headache in c2
    assert agg.total_fp == 2  # headache in c1, fever in c2
    assert agg.total_fn == 1  # cough in c1
    assert agg.micro_precision == pytest.approx(2 / 4)
    assert agg.micro_recall == pytest.approx(2 / 3)
    assert agg.micro_f1 == pytest.approx(2 * 0.5 * (2 / 3) / (0.5 + 2 / 3))

    # Per-field metrics
    assert agg.severity_metrics is not None
    assert agg.severity_metrics.total_expected == 1
    assert agg.severity_metrics.total_matched == 1
    assert agg.severity_metrics.accuracy == 1.0

    assert agg.duration_metrics is not None
    assert agg.duration_metrics.total_expected == 2
    assert agg.duration_metrics.total_matched == 1  # only case_001 matched
    assert agg.duration_metrics.accuracy == 0.5

    # Subgroups
    assert "standard" in agg.category_metrics
    assert "hinglish" in agg.category_metrics
    assert agg.category_metrics["standard"]["cases"] == 1.0


def test_compute_metrics_missing_file_raises() -> None:
    """FileNotFoundError is raised when cases path does not exist."""
    extractor = SimpleWordMatchExtractor(vocab_path=_VOCAB_PATH)
    with pytest.raises(FileNotFoundError, match="Cases file not found"):
        compute_metrics(Path("non_existent_file.json"), extractor)


def test_compute_metrics_invalid_json_raises(tmp_path: Path) -> None:
    """TypeError is raised when cases key is not a list."""
    invalid_file = tmp_path / "invalid.json"
    with open(invalid_file, "w", encoding="utf-8") as f:
        json.dump({"cases": "not_a_list"}, f)

    extractor = SimpleWordMatchExtractor(vocab_path=_VOCAB_PATH)
    with pytest.raises(TypeError, match="must be a list"):
        compute_metrics(invalid_file, extractor)


def test_print_report_outputs_summary(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify print_report produces formatted output with per-field sections."""
    res = [
        CaseResult(
            case_id="case_001",
            expected_ids={"fever"},
            predicted_ids={"fever"},
            true_positives=1,
            false_positives=0,
            false_negatives=0,
            precision=1.0,
            recall=1.0,
            f1=1.0,
            expected_duration="1 day",
            predicted_duration="1 day",
            duration_matched=True,
            expected_severities={"fever": "SEVERE"},
            predicted_severities={"fever": "SEVERE"},
            severity_matches=1,
            severity_evaluated=1,
        )
    ]
    agg = AggregateMetrics(
        total_cases=1,
        total_tp=1,
        total_fp=0,
        total_fn=0,
        micro_precision=1.0,
        micro_recall=1.0,
        micro_f1=1.0,
        mean_precision=1.0,
        mean_recall=1.0,
        mean_f1=1.0,
        severity_metrics=FieldMetrics(1, 1, 1, 1.0, 1.0, 1.0, 1.0),
        duration_metrics=FieldMetrics(1, 1, 1, 1.0, 1.0, 1.0, 1.0),
        category_metrics={
            "standard": {
                "cases": 1.0,
                "micro_precision": 1.0,
                "micro_recall": 1.0,
                "micro_f1": 1.0,
                "macro_f1": 1.0,
            }
        },
    )
    print_report(res, agg, verbose=True, per_field=True)
    captured = capsys.readouterr()
    assert "NLP Symptom Extraction Evaluation Report" in captured.out
    assert "case_001" in captured.out
    assert "Per-Field Evaluation Breakdown" in captured.out
    assert "Subgroup Linguistic Category Breakdown" in captured.out


def test_generate_markdown_report_structure() -> None:
    """Verify generate_markdown_report contains key sections and recommendations."""
    agg = AggregateMetrics(
        total_cases=100,
        total_tp=71,
        total_fp=18,
        total_fn=173,
        micro_precision=0.7978,
        micro_recall=0.2910,
        micro_f1=0.4264,
        mean_precision=0.4908,
        mean_recall=0.2757,
        mean_f1=0.3392,
        severity_metrics=FieldMetrics(31, 37, 11, 0.2973, 0.3548, 0.3235, 0.3548),
        duration_metrics=FieldMetrics(31, 32, 31, 0.9688, 1.0000, 0.9841, 1.0000),
        category_metrics={
            "standard": {
                "cases": 45.0,
                "micro_precision": 0.8182,
                "micro_recall": 0.3495,
                "micro_f1": 0.4898,
                "macro_f1": 0.4044,
            }
        },
    )
    report = generate_markdown_report(agg, [])
    assert "# NLP Extraction Benchmark Report (Eval Set v2)" in report
    assert "S2-NIT-1" in report
    assert "Per-Field Performance Breakdown" in report
    assert "Linguistic Subgroup Performance" in report
    assert "Misspellings and Phonetic Typos" in report


# ---------------------------------------------------------------------------
# Integration Tests: CLI Execution & Shipped 100-Case Benchmark Dataset
# ---------------------------------------------------------------------------


def test_main_cli_execution_success() -> None:
    """Verify main() CLI executes successfully on shipped cases."""
    exit_code = main([])
    assert exit_code == 0


def test_main_cli_json_export(tmp_path: Path) -> None:
    """Verify main() CLI exports JSON summary file with per-field data."""
    json_out = tmp_path / "eval_metrics.json"
    exit_code = main(["--json", str(json_out)])
    assert exit_code == 0
    assert json_out.exists()

    with open(json_out, encoding="utf-8") as f:
        data = json.load(f)
    assert "aggregate" in data
    assert "cases" in data
    assert data["aggregate"]["total_cases"] == 100
    assert "severity" in data["aggregate"]
    assert "duration" in data["aggregate"]
    assert "categories" in data["aggregate"]
    assert len(data["cases"]) == 100


def test_main_cli_report_export(tmp_path: Path) -> None:
    """Verify main() CLI exports Markdown report file when requested."""
    report_out = tmp_path / "eval_report.md"
    exit_code = main(["--report", str(report_out)])
    assert exit_code == 0
    assert report_out.exists()

    with open(report_out, encoding="utf-8") as f:
        content = f.read()
    assert "NLP Extraction Benchmark Report (Eval Set v2)" in content
    assert "S2-NIT-1" in content


def test_main_cli_missing_files() -> None:
    """Verify main() returns exit code 1 when input files do not exist."""
    assert main(["--cases", "missing_cases.json"]) == 1
    assert main(["--vocab", "missing_vocab.json"]) == 1


def test_shipped_dataset_contains_100_cases() -> None:
    """Verify cases.json has exactly 100 benchmark cases for v2."""
    assert _CASES_PATH.exists()
    with open(_CASES_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert len(data.get("cases", [])) == 100


def test_all_shipped_case_symptoms_exist_in_vocabulary() -> None:
    """Ensure every expected symptom in cases.json aligns with canonical vocabulary."""
    with open(_CASES_PATH, encoding="utf-8") as f:
        cases_data = json.load(f)
    with open(_VOCAB_PATH, encoding="utf-8") as f:
        vocab_data = json.load(f)

    vocab_ids = {s["id"] for s in vocab_data.get("symptoms", [])}

    for case in cases_data.get("cases", []):
        for s in case.get("expected", {}).get("symptoms", []):
            assert s["id"] in vocab_ids, (
                f"Unknown symptom ID '{s['id']}' in {case['id']}"
            )


def test_shipped_dataset_evaluation_produces_positive_f1() -> None:
    """Verify baseline extractor produces positive micro and macro F1 scores on 100 cases."""
    extractor = SimpleWordMatchExtractor(vocab_path=_VOCAB_PATH)
    results, agg = compute_metrics(_CASES_PATH, extractor)
    assert len(results) == 100
    assert agg.total_cases == 100
    assert agg.micro_f1 > 0.0
    assert agg.mean_f1 > 0.0
    assert agg.severity_metrics is not None
    assert agg.duration_metrics is not None
    assert agg.severity_metrics.total_expected > 0
    assert agg.duration_metrics.total_expected > 0
