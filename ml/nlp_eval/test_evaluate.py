"""Tests for the NLP evaluation harness.

Covers happy paths, edge cases, metric accuracy, protocol compliance,
CLI behavior, and full integration with the 50-case benchmark dataset.

Owner: Kavya (AI/ML, Database) · Task: S1-KAV-2 · Requirements: NFR-07
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
SimpleWordMatchExtractor = _evaluate_mod.SimpleWordMatchExtractor
compute_metrics = _evaluate_mod.compute_metrics
evaluate_case = _evaluate_mod.evaluate_case
main = _evaluate_mod.main
print_report = _evaluate_mod.print_report

_CASES_PATH = _HERE / "cases.json"
_VOCAB_PATH = _HERE.parent / "datasets" / "symptoms" / "symptoms.json"


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------


class _MockFixedExtractor:
    """Mock extractor returning a fixed set of canonical symptom IDs."""

    def __init__(self, symptom_ids: list[str]) -> None:
        self.symptom_ids = symptom_ids

    def extract(self, text: str) -> ExtractionResult:
        return ExtractionResult(
            symptoms=[ExtractedSymptom(id=s_id) for s_id in self.symptom_ids]
        )


def _build_test_case(
    case_id: str,
    text: str,
    expected_ids: list[str],
    *,
    duration: str | None = None,
) -> dict:
    expected: dict = {"symptoms": [{"id": sid} for sid in expected_ids]}
    if duration:
        expected["duration"] = duration
    return {"id": case_id, "input": text, "expected": expected}


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
    """Verify SimpleWordMatchExtractor accurately maps lay phrases to symptom IDs."""
    extractor = SimpleWordMatchExtractor(vocab_path=_VOCAB_PATH)
    result = extractor.extract(input_text)
    extracted_ids = {s.id for s in result.symptoms}
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
    """Verify severity keywords are correctly identified."""
    extractor = SimpleWordMatchExtractor(vocab_path=_VOCAB_PATH)
    result = extractor.extract(input_text)
    if result.symptoms:
        assert result.symptoms[0].severity == expected_severity


def test_simple_extractor_avoids_duplicate_symptom_ids() -> None:
    """Verify extractor does not return duplicate symptom objects for redundant lay matches."""
    extractor = SimpleWordMatchExtractor(vocab_path=_VOCAB_PATH)
    # Both "headache" and "head hurts" map to headache
    result = extractor.extract("I have a headache and my head hurts")
    ids = [s.id for s in result.symptoms]
    assert len(ids) == len(set(ids))


def test_simple_extractor_handles_empty_string() -> None:
    """Verify extractor returns empty list on empty input without raising."""
    extractor = SimpleWordMatchExtractor(vocab_path=_VOCAB_PATH)
    result = extractor.extract("")
    assert result.symptoms == []


# ---------------------------------------------------------------------------
# Unit Tests: evaluate_case Metrics
# ---------------------------------------------------------------------------


def test_evaluate_case_perfect_match() -> None:
    """Test precision, recall, and F1 calculation on perfect match."""
    case = _build_test_case("c1", "fever and cough", ["fever", "cough"])
    extractor = _MockFixedExtractor(["fever", "cough"])

    result = evaluate_case(case, extractor)
    assert result.precision == pytest.approx(1.0)
    assert result.recall == pytest.approx(1.0)
    assert result.f1 == pytest.approx(1.0)
    assert result.true_positives == 2
    assert result.false_positives == 0
    assert result.false_negatives == 0


def test_evaluate_case_false_negatives_only() -> None:
    """Test recall degradation when expected symptoms are missed."""
    case = _build_test_case("c2", "fever and cough", ["fever", "cough"])
    extractor = _MockFixedExtractor(["fever"])

    result = evaluate_case(case, extractor)
    assert result.precision == pytest.approx(1.0)
    assert result.recall == pytest.approx(0.5)
    assert result.f1 == pytest.approx(2 * 1.0 * 0.5 / 1.5)
    assert result.true_positives == 1
    assert result.false_positives == 0
    assert result.false_negatives == 1


def test_evaluate_case_false_positives_only() -> None:
    """Test precision degradation when extraneous symptoms are predicted."""
    case = _build_test_case("c3", "fever", ["fever"])
    extractor = _MockFixedExtractor(["fever", "headache"])

    result = evaluate_case(case, extractor)
    assert result.precision == pytest.approx(0.5)
    assert result.recall == pytest.approx(1.0)
    assert result.f1 == pytest.approx(2 * 0.5 * 1.0 / 1.5)
    assert result.true_positives == 1
    assert result.false_positives == 1
    assert result.false_negatives == 0


def test_evaluate_case_zero_overlap() -> None:
    """Test metrics when predictions completely mismatch expectations."""
    case = _build_test_case("c4", "fever", ["fever"])
    extractor = _MockFixedExtractor(["headache"])

    result = evaluate_case(case, extractor)
    assert result.precision == pytest.approx(0.0)
    assert result.recall == pytest.approx(0.0)
    assert result.f1 == pytest.approx(0.0)
    assert result.true_positives == 0
    assert result.false_positives == 1
    assert result.false_negatives == 1


def test_evaluate_case_empty_predictions_and_expectations() -> None:
    """Test boundary condition where case has no symptoms expected or predicted."""
    case = _build_test_case("c5", "healthy", [])
    extractor = _MockFixedExtractor([])

    result = evaluate_case(case, extractor)
    assert result.precision == pytest.approx(1.0)
    assert result.recall == pytest.approx(1.0)
    assert result.true_positives == 0
    assert result.false_positives == 0
    assert result.false_negatives == 0


# ---------------------------------------------------------------------------
# Unit Tests: compute_metrics & Aggregation
# ---------------------------------------------------------------------------


def test_compute_metrics_aggregates_totals(tmp_path: Path) -> None:
    """Verify aggregate TP/FP/FN match summation over cases."""
    cases = [
        _build_test_case("c1", "fever", ["fever"]),
        _build_test_case("c2", "cough", ["cough"]),
    ]
    data = {"schema_version": "1.0", "cases": cases}
    cases_file = tmp_path / "test_cases.json"
    cases_file.write_text(json.dumps(data), encoding="utf-8")

    # Extractor always returns ["fever"]
    # c1: TP=1, FP=0, FN=0
    # c2: TP=0, FP=1, FN=1
    results, agg = compute_metrics(cases_file, _MockFixedExtractor(["fever"]))

    assert len(results) == 2
    assert agg.total_cases == 2
    assert agg.total_tp == 1
    assert agg.total_fp == 1
    assert agg.total_fn == 1
    assert agg.micro_precision == pytest.approx(0.5)
    assert agg.micro_recall == pytest.approx(0.5)


def test_compute_metrics_missing_file_raises() -> None:
    """Verify compute_metrics raises FileNotFoundError if cases path does not exist."""
    with pytest.raises(FileNotFoundError):
        compute_metrics(Path("non_existent_cases.json"), _MockFixedExtractor([]))


def test_compute_metrics_invalid_json_raises(tmp_path: Path) -> None:
    """Verify compute_metrics raises TypeError on invalid schema."""
    cases_file = tmp_path / "invalid.json"
    cases_file.write_text(json.dumps({"cases": "not-a-list"}), encoding="utf-8")
    with pytest.raises(TypeError, match="must be a list"):
        compute_metrics(cases_file, _MockFixedExtractor([]))


# ---------------------------------------------------------------------------
# Unit Tests: print_report & CLI
# ---------------------------------------------------------------------------


def test_print_report_outputs_summary(capsys: pytest.CaptureFixture) -> None:
    """Verify print_report writes metrics table to stdout."""
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
    )
    print_report(res, agg, verbose=True)
    captured = capsys.readouterr()
    assert "NLP Symptom Extraction Evaluation Report" in captured.out
    assert "case_001" in captured.out
    assert "Micro-averaged F1 Score" in captured.out


def test_main_cli_execution_success() -> None:
    """Verify main() CLI executes successfully on shipped cases."""
    exit_code = main([])
    assert exit_code == 0


def test_main_cli_json_export(tmp_path: Path) -> None:
    """Verify main() CLI exports JSON summary file when requested."""
    json_out = tmp_path / "eval_metrics.json"
    exit_code = main(["--json", str(json_out)])
    assert exit_code == 0
    assert json_out.exists()

    with open(json_out, encoding="utf-8") as f:
        data = json.load(f)
    assert "aggregate" in data
    assert "cases" in data
    assert data["aggregate"]["total_cases"] == 50


def test_main_cli_missing_files() -> None:
    """Verify main() returns exit code 1 when input files do not exist."""
    assert main(["--cases", "missing_cases.json"]) == 1
    assert main(["--vocab", "missing_vocab.json"]) == 1


# ---------------------------------------------------------------------------
# Integration Tests: Shipped 50-Case Benchmark Dataset
# ---------------------------------------------------------------------------


def test_shipped_dataset_contains_50_cases() -> None:
    """Verify cases.json has exactly 50 benchmark cases."""
    assert _CASES_PATH.exists()
    with open(_CASES_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert len(data.get("cases", [])) == 50


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
    """Verify baseline extractor produces positive micro and macro F1 scores on the 50 cases."""
    extractor = SimpleWordMatchExtractor(vocab_path=_VOCAB_PATH)
    results, agg = compute_metrics(_CASES_PATH, extractor)
    assert len(results) == 50
    assert agg.total_cases == 50
    assert agg.micro_f1 > 0.0
    assert agg.mean_f1 > 0.0
