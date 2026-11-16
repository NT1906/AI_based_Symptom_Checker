# Condition model v2 (S2-NIS-3): results and decision

**Owner:** Nisarg · **Issue:** #150 · **Decided:** 15 Nov 2026 · **Requirements:** FR-05, NFR-07
**Training:** [`ml/prediction/`](../ml/prediction/README.md) · **Serving:** `server/app/services/prediction/onnx_condition_model.py`

## 1. Decision

v2 is built, exported to ONNX and served with ONNX Runtime, but **the baseline (S1-NIS-1) stays the app's condition model.**
On every test, v2 matched or slightly trailed the baseline.
- v2 can be switched on with `CONDITION_MODEL_KIND=onnx`.
- If v2 can't be loaded, the server falls back to the baseline.

## 2. What v2 is

| Part | Choice |
|---|---|
| Data | **Synthetic cases** from `ml/datasets/conditions/conditions.json`. Each condition's symptoms are reported with a chance set by weight (hallmark 0.85, common 0.55, sometimes 0.25), plus one unrelated symptom 30 % of the time. Seeds 1 / 2 / 3 give 7,600 train, 1,900 validation and 1,900 test cases (balanced, 38 conditions). |
| Features | Multi-hot over the 100 canonical symptom IDs |
| Model | Multinomial logistic regression, `C = 3` chosen on validation top-1 accuracy |
| Labels | "Likely" when probability ≥ 0.30 **and** a hallmark symptom was reported (validation precision 0.956); "Possible" when ≥ 0.15. Never a number (FR-23). |
| Ranking | Only conditions that explain a reported symptom, top 3, ties by ID (the same contract as the baseline) |
| Export | `skl2onnx`, opset 17, 23 KB. The metadata holds the feature order, classes, thresholds and dataset version. ONNX Runtime matches scikit-learn to 4.8e-07. |
| Safety | The server refuses a model whose vocabulary, conditions or dataset version differ from the packaged dataset |

## 3. Results (held-out synthetic test set)

Reproduce with `python ml/prediction/train_condition_model.py`.

| Model | Top-1 accuracy | Top-3 accuracy | Macro-F1 (top-1) |
|---|---|---|---|
| **Baseline (S1-NIS-1)** | **0.955** | 0.992 | **0.955** |
| v2 logistic regression | 0.952 | 0.992 | 0.952 |

Stress tests on harder copies of the same test cases (top-1 accuracy):

| Test | Baseline | v2 |
|---|---|---|
| +1 unrelated symptom | **0.931** | 0.925 |
| +2 unrelated symptoms | **0.905** | 0.897 |
| +3 unrelated symptoms | **0.882** | 0.869 |
| Hallmark symptoms missing | **0.416** | 0.385 |
| Hallmarks missing, +2 unrelated | **0.265** | 0.222 |

## 4. Why v2 does not win

- **There is no real patient data** (see the dataset card), so the training cases are generated from the same expert weights the baseline formula already uses. The model can only re-learn the formula, and a learned copy is slightly noisier than the original.
- **These scores measure agreement with the dataset, not real-world accuracy.** The baseline's 0.955 doesn't mean it's right 95 % of the time for real users.
- **v2 becomes worth switching on when labelled cases exist,** for example clinician-reviewed vignettes or the S2-VIV-4 audit log with consent. Then a model can learn patterns the hand-set weights miss. The training, export, parity check and serving code are ready for that.

## 5. Turning v2 on (not recommended for v1.0)

1. **Train:** `python ml/prediction/train_condition_model.py --output-dir ml/checkpoints/condition_v2`.
2. **Publish:** upload `condition_v2.onnx` with a model card to a Hugging Face repo, for example `NT1906/condition-v2`. Note the commit SHA.
3. **Configure:** set `CONDITION_MODEL_KIND=onnx`, `CONDITION_MODEL_REPO` and `CONDITION_MODEL_REVISION` (or `CONDITION_MODEL_PATH`).
4. **Wire it in:** the orchestrator still creates `BaselineConditionModel()` itself. Passing `build_condition_model(ConditionModelSettings())` instead is a one-line change in Darshil's module, to make only if v2 is adopted.
