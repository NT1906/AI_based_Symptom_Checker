# `ml/prediction/`: condition model v2 (training side)

**Owner:** Nisarg · **Task:** S2-NIS-3 (#150) · **Results and decision:** [docs/condition-model-v2.md](../../docs/condition-model-v2.md)

Trains a scikit-learn condition model on synthetic cases from `ml/datasets/conditions/conditions.json`, compares it with the S1-NIS-1 baseline, and exports it to ONNX for `server/app/services/prediction/onnx_condition_model.py`.
This folder is **never deployed**.

## Layout

| File | What it does |
|---|---|
| `condition_cases.py` | Load the dataset; seeded synthetic cases; train / val / test splits; stress perturbations |
| `baseline_scoring.py` | The server baseline's ranking, re-implemented (the ML folder cannot import the server); `test_condition_cases.py` checks it against server rankings |
| `condition_metrics.py` | Top-k accuracy, macro-F1, precision above a threshold, the comparison table |
| `train_condition_model.py` | Fit, pick C and the "Likely" threshold on validation, compare on test and stress sets, export ONNX, check parity, write the report |
| `requirements.txt` | Training dependencies (scikit-learn, skl2onnx, onnx, onnxruntime, numpy) |
| `test_*.py` | Unit tests. Training and ONNX tests skip without those packages, as in CI |

## Run

```bash
pip install -r ml/prediction/requirements.txt
python ml/prediction/train_condition_model.py --output-dir ml/checkpoints/condition_v2   # a few seconds
```

Outputs go to `--output-dir`, which is git-ignored:
- `condition_v2.onnx` (23 KB);
- `metrics.json`;
- `report.md`.

The ONNX metadata carries `symptom_ids` (feature order), `condition_ids` (classes), `likely_min_probability`, `possible_min_probability`, `dataset_version` and `model_version`. The server checks them against its dataset before using the model.

## Rules

- **No real patient data:** cases are synthetic, so metrics measure agreement with the dataset, not clinical accuracy.
- **Model selection:** choose C and the thresholds on **validation** only. Test is reported, never used to choose.
- **Models are never committed:** they go to Hugging Face Hub (AI_RULES.md §7.8).
- **Keeping things in step:**
  - Changing the dataset version means retraining. The server refuses a model trained on another dataset version.
  - Changing the baseline formula in the server means updating `baseline_scoring.py` and its expected rankings in the same PR.

## Test

```bash
cd ml
ruff check . && pytest prediction
```
