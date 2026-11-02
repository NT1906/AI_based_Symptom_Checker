# Prediction Service

**Owner:** Nisarg (prediction) · **Tasks:** S1-NIS-1, S1-NIS-2 · **Requirements:** FR-05, FR-06, FR-15, FR-22, FR-23, DR-02

Two parts, both deterministic:

- **Condition predictor:** ranks the possible conditions for a set of confirmed symptoms. Each condition gets a confidence **label** (`LIKELY`, `POSSIBLE`, `LESS_LIKELY`), never a number.
- **Risk engine:** turns the symptoms and predictions into `SELF_CARE`, `CONSULT_DOCTOR` or `URGENT`. Red flags always win.

The result composer (S1-NIS-3) joins this package later.

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

## Risk engine

```python
from app.schemas.enums import Severity
from app.services.prediction import ReportedSymptom, assess_risk, find_red_flags

symptoms = [ReportedSymptom(id="chest_pain", severity=Severity.SEVERE)]
decision = assess_risk(symptoms, predictions)
# RiskDecision(level=URGENT, rule=RED_FLAG,
#              red_flags=(RedFlagHit(id='rf_cardiac_chest_pain', category='cardiac', assumed_severity=False),), ...)

# Red-flag check alone: call it after every chat message, not only at the end.
find_red_flags(symptoms)
```

Rules, in order:

| # | Rule | Level | `rule` |
|---|---|---|---|
| 1 | Any red flag fires | `URGENT`, whatever the predictions say (DR-02) | `RED_FLAG` |
| 2 | Otherwise, the highest tier from the predictions: `LIKELY` gives the condition's full `base_risk`, `POSSIBLE` at most `CONSULT_DOCTOR`, `LESS_LIKELY` nothing | that tier | `CONDITION` |
| 3 | No prediction is at least `POSSIBLE` | `CONSULT_DOCTOR` (not knowing is never "probably nothing", idea §7) | `NO_CONDITION_MATCH` |

**Red-flag triggers:** a red flag fires when **any** trigger fires, and a trigger fires when **all** of its parts are present.
A part with `min_severity` needs that severity or worse.

**Unknown severity:** if the user did not say how bad a symptom is, a severity minimum counts as **met**, because uncertainty never lowers risk (AI_RULES.md §2.6).
The hit is marked `assumed_severity=True`. The orchestrator should ask about severity while the user can still answer (clarification or confirmation), so the assumption is rarely needed.

`RiskDecision` also carries `driving_condition_ids` (for the "why" panel) and `engine_version` (for the audit log).
Bump `RISK_ENGINE_VERSION` whenever a rule changes. Uncertainty escalation on low confidence is added in S2-NIS-1.

## Data

`data/conditions.json` is a **copy** of `ml/datasets/conditions/conditions.json`, because the server image has no `ml/`.
`test_packaged_copy_matches_ml_dataset` fails if the two differ. After editing the dataset:

```bash
cp ml/datasets/conditions/conditions.json server/app/services/prediction/data/conditions.json
```

Both the predictor and the risk engine read this file: the conditions, and the red-flag rules.

## Tests

```bash
cd server
pytest tests/unit/prediction -v
```
