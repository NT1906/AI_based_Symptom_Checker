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
| 4 | Any uncertainty, and the level so far is `SELF_CARE` | raised to `CONSULT_DOCTOR` | `UNCERTAINTY` |

**Red-flag triggers:** a red flag fires when **any** trigger fires, and a trigger fires when **all** of its parts are present.
A part with `min_severity` needs that severity or worse.

**Unknown severity:** if the user did not say how bad a symptom is, a severity minimum counts as **met**, because uncertainty never lowers risk (AI_RULES.md §2.6).
The hit is marked `assumed_severity=True`. The orchestrator should ask about severity while the user can still answer (clarification or confirmation), so the assumption is rarely needed.

**Uncertainty escalation (S2-NIS-1, AI_RULES.md §2.6).** Uncertainty only ever raises the tier.
It stops at `CONSULT_DOCTOR`: `URGENT` stays reserved for red flags and Likely urgent conditions.

| `UncertaintyReason` | When | Who sets it |
|---|---|---|
| `LOW_CONFIDENCE` | No prediction is `LIKELY` | The risk engine itself |
| `IMAGE_UNCLEAR` | The user sent a photo and the analyzer answered `unclear` | The caller: `assess_risk(..., uncertainty=[...])` |
| `AI_ERROR` | The AI gateway failed during the conversation | The caller |

```python
from app.services.prediction import UncertaintyReason

decision = assess_risk(
    symptoms, predictions, uncertainty=[UncertaintyReason.IMAGE_UNCLEAR]
)
decision.uncertainty  # every reason that applied, in enum order, even if the level did not change
```

`RiskDecision` also carries `driving_condition_ids` (for the "why" panel and the referral specialty, also after an escalation), `uncertainty` and `engine_version` (for the audit log).
Bump `RISK_ENGINE_VERSION` whenever a rule changes (now `1.1.0`, for uncertainty escalation).

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
| `conditions` | The predictions in the published `Condition` schema, with the specialty display name and a `why` line (below) |
| `guidance` | Next steps for the tier (`result_text.NEXT_STEPS`). Red flags in the `mental_health` category add Tele-MANAS 14416. An assumed severity is explained. Extra self-care guidance (S2-KAV-1) is added for `SELF_CARE` only. |
| `referral` | `required` unless `SELF_CARE`; specialty name; reason (red-flag label, "may be related to …", no-match, or uncertain match); 112 for `URGENT` |
| `limitations` | Always the self-report and coverage limits, plus a red-flag, no-match or "raised to the safer level" note, plus one note per unclear photo or AI error |
| `model_version` | The risk engine version |
| `disclaimer` | The fixed default from `app.schemas.result` |

**"Why" line per condition (S2-NIS-2, FR-24).** `ConditionExplainer` (`explanations.py`) turns each prediction's `matched_symptom_ids` (heaviest first) into one sentence.
Mann's `ConditionList` shows it as the "Why:" line.

- **Names:** symptom display names come from the knowledge service, lowercased inside the sentence unless they start with an acronym.
- **Length:** at most 3 symptoms are named, and the rest are counted.
- **Wording:** it names only what the user reported, never what the user has, and it goes through the wording guard like every other sentence.

```text
Dengue [Likely]       → Because you reported fever, pain behind the eyes, headache and 1 other symptom.
Chikungunya [Likely]  → Because you reported fever, joint pain and headache.
```

**Wording:** every sentence lives in `result_text.py`, so wording can be reviewed in one place (DR-05).
The composer passes each generated sentence to the **required** `wording_guard` before returning, and a guard error stops the result.
The fixed disclaimer is not passed to the guard: it contains the word "diagnosis" by design.

## Condition model v2 (S2-NIS-3)

`OnnxConditionModel` (`onnx_condition_model.py`) is a second `ConditionModel`: a logistic regression trained in `ml/prediction/`, exported to ONNX and run with ONNX Runtime.
**The baseline stays the default.** v2 matched but did not beat it on synthetic cases; see [docs/condition-model-v2.md](../../../../docs/condition-model-v2.md).

```python
from app.services.prediction.condition_model_config import (
    ConditionModelSettings,
    build_condition_model,
)

model = build_condition_model(
    ConditionModelSettings()
)  # baseline unless CONDITION_MODEL_KIND=onnx
```

- **Settings:** `CONDITION_MODEL_KIND` (`baseline` / `onnx`), plus either `CONDITION_MODEL_PATH`, or `CONDITION_MODEL_REPO` and `CONDITION_MODEL_REVISION` (a pinned Hub commit).
- **Same contract as the baseline:** only conditions that explain a reported symptom, top 3, ties by ID, labels only. "Likely" needs the model's threshold **and** a hallmark symptom.
- **Model checks:** a model whose vocabulary, conditions or dataset version differ from the packaged dataset is refused.
- **Fallback:** if v2 can't be loaded, `build_condition_model` falls back to the baseline and logs it.

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

### Consistency verification (S2-NIS-9, DR-02)

`tests/unit/prediction/test_risk_consistency.py` checks that only the input decides the output (AI_RULES.md §2.4).
It runs the full pipeline (predictor → risk engine → composer with the real wording guard) and compares everything except `created_at`:

| Check | Runs |
|---|---|
| Each reference case (self-care, consult, red flag, assumed severity, mental health, unclear photo, many symptoms, no match) gives identical output, with the symptoms in a new order each run | 8 × 1000 |
| 1000 seeded, varied inputs (1–6 symptoms, any severity, any uncertainty) give the same output in reverse order | 1000 × 2 |
| The same 1000 inputs give the same SHA-256 digest in fresh processes with other `PYTHONHASHSEED` values, so set or dict order can never leak into a result | 2 processes |
| A repeated symptom changes nothing; an empty input fails the same way every time | 1 + 1000 |

The varied inputs reach every outcome: red flag, condition (self-care and consult), uncertainty and no match.
The whole file runs in about 3 seconds, so it runs in CI on every PR.
