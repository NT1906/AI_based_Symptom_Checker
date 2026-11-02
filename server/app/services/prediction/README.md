# Prediction Service

**Owner:** Nisarg (prediction) · **Task:** S1-NIS-1 · **Requirements:** FR-05, FR-22, FR-23

Ranks the possible conditions for a set of confirmed symptoms. Each condition gets a confidence **label**
(`LIKELY`, `POSSIBLE`, `LESS_LIKELY`), never a number. The risk engine (S1-NIS-2) and result composer (S1-NIS-3) join this package later.

## Public interface

```python
from app.services.prediction import BaselineConditionModel, ConditionModel

model: ConditionModel = BaselineConditionModel()
predictions = model.predict(["fever", "pain_behind_eyes", "joint_pain"])
# [ConditionPrediction(condition_id='dengue', confidence=LIKELY, rank=1, base_risk=CONSULT_DOCTOR,
#                      matched_symptom_ids=('fever', 'pain_behind_eyes', 'joint_pain'), ...), ...]
```

- **Input:** canonical symptom IDs, already normalized by the knowledge service (`app.services.knowledge`). Unknown IDs are ignored and duplicates count once.
- **Output:** up to 3 `ConditionPrediction`s, best first. The list is empty when nothing matches.
- **Empty input:** raises `ValidationError` (422).
- **`ConditionModel`** is the protocol the orchestrator depends on. The scikit-learn/ONNX model from S2-NIS-3 implements the same protocol.

## How the baseline scores

For each condition, with symptom weights 3 = hallmark, 2 = common, 1 = sometimes:

| Term | Meaning |
|---|---|
| `coverage` | weight of the reported symptoms the condition has ÷ the condition's total weight |
| `explained` | reported symptoms the condition has ÷ all reported symptoms |
| `score` | harmonic mean of the two (0–1); **internal only, never returned** |

Labels:

| Label | Rule |
|---|---|
| `LIKELY` | score ≥ 0.6 **and** at least one hallmark symptom matched |
| `POSSIBLE` | score ≥ 0.35 |
| `LESS_LIKELY` | anything lower |

Ties are broken by matched weight, then by condition ID. The same symptoms always give the same ranking.

**Not modelled yet:** severity, duration and profile context (S2-DAR-3). Red flags are not handled here either: the risk engine checks them separately, and they always produce `URGENT`, whatever this ranking says (DR-02).

## Data

`data/conditions.json` is a **copy** of `ml/datasets/conditions/conditions.json`, because the server image has no `ml/`.
`test_packaged_copy_matches_ml_dataset` fails if the two differ. After editing the dataset:

```bash
cp ml/datasets/conditions/conditions.json server/app/services/prediction/data/conditions.json
```

## Tests

```bash
cd server
pytest tests/unit/prediction -v
```
