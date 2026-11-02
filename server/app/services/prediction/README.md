# Prediction Service

**Owner:** Nisarg (prediction) · **Tasks:** S1-NIS-1, S1-NIS-2, S1-NIS-3 · **Requirements:** FR-05, FR-06, FR-07, FR-15, FR-22, FR-23, DR-02, DR-04

Three parts, all deterministic:

- **Condition predictor:** ranks the possible conditions for a set of confirmed symptoms. Each condition gets a confidence **label** (`LIKELY`, `POSSIBLE`, `LESS_LIKELY`), never a number.
- **Risk engine:** turns the symptoms and predictions into `SELF_CARE`, `CONSULT_DOCTOR` or `URGENT`. Red flags always win.
- **Specialty mapper + result composer:** pick the kind of doctor to refer to, then build the published `AssessmentResult`.

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

## Specialty mapper and result composer

```python
from app.services.prediction import ResultComposer

composer = ResultComposer(wording_guard=assert_safe_wording)  # S1-HAR-3
result = composer.compose(assessment_id, decision, predictions)
```

**Referral specialty** (`SpecialtyMapper`):

| Level | Specialty |
|---|---|
| `URGENT` | Emergency department, always |
| `CONSULT_DOCTOR` | Specialty of the best-ranked condition that drove the decision; general physician if none did, or if the specialty is unknown |
| `SELF_CARE` | None (no referral) |

**What the composer fills in:**

| Field | Content |
|---|---|
| `risk_level` | Copied from the decision, **never changed** |
| `conditions` | The predictions in the published `Condition` schema, with the specialty display name |
| `guidance` | Next steps for the tier (`result_text.NEXT_STEPS`). Red flags in the `mental_health` category add Tele-MANAS 14416. An assumed severity is explained. Extra self-care guidance (S2-KAV-1) is added for `SELF_CARE` only. |
| `referral` | `required` unless `SELF_CARE`; specialty name; reason (red-flag label, "may be related to …", or no-match); 112 for `URGENT` |
| `limitations` | Always the self-report and coverage limits, plus a red-flag or no-match note |
| `model_version` | The risk engine version |
| `disclaimer` | The fixed default from `app.schemas.result` |

**Wording:** every sentence lives in `result_text.py`, so wording can be reviewed in one place (DR-05).
The composer passes each generated sentence to the **required** `wording_guard` before returning, and a guard error stops the result.
The fixed disclaimer is not passed to the guard: it contains the word "diagnosis" by design.

## Data

`data/conditions.json` is a **copy** of `ml/datasets/conditions/conditions.json`, because the server image has no `ml/`.
`test_packaged_copy_matches_ml_dataset` fails if the two differ. After editing the dataset:

```bash
cp ml/datasets/conditions/conditions.json server/app/services/prediction/data/conditions.json
```

The predictor reads the conditions, the risk engine the red-flag rules, and the composer the specialties.

## Tests

```bash
cd server
pytest tests/unit/prediction -v
```
