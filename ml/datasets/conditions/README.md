# Condition dataset v0 (dataset card)

**Owner:** Nisarg (prediction) · **Task:** S0-NIS-1 · **Requirements:** DR-02, DR-03, DR-04

Reference data for the symptom checker's prediction module. It lists common conditions with their ICD-10 codes, weighted symptoms and specialty, plus the red-flag symptom rules that always send a user to urgent care.

| Read by | For |
|---|---|
| Baseline condition predictor (S1-NIS-1) | Weighted symptom-overlap scoring, top 3 conditions |
| Risk engine (S1-NIS-2) | Red-flag rules (always `URGENT`) and each condition's base risk tier |
| Specialty mapper + `ResultComposer` (S1-NIS-3) | Specialty name and map search term for the referral |
| Condition model v2 (S2-NIS-3) | Seed for generating synthetic training cases |
| Symptom vocabulary (S0-KAV-1, Kavya) | The canonical symptom IDs to reuse |

## Intended use and limits

- **Informational triage only.** This data ranks *possible* conditions. It is not a diagnostic reference, and nothing in it is a treatment instruction (DR-05).
- **Not clinically validated yet.** Symptom weights are expert judgement taken from the sources below, not statistics from patient data. A clinician should review the dataset before any real-world use (DR-03).
- **Adults, India context.** Children, pregnancy and older adults have different red flags and are not modelled. Infections common in India (dengue, malaria, typhoid, chikungunya, TB, viral hepatitis) are included on purpose.
- **Duration is not modelled.** Some conditions depend on it (for example, TB is suspected after a cough lasting more than 2 weeks). The predictor has to apply that itself.
- **No real patient data.** Everything here was written by hand from public sources. Nothing was downloaded or derived from records.

## Contents

`conditions.json` (schema version `1.0`, dataset version `v0`):

| Section | Count | What it holds |
|---|---|---|
| `conditions` | 38 | `id`, `name`, `icd10`, `group`, `specialty`, `base_risk`, `visual`, weighted `symptoms`, related `red_flags`, `sources` |
| `symptoms` | 100 | Canonical `id`, plain-language `name`, `body_system` |
| `red_flags` | 13 | `category`, `label`, `triggers`, `rationale`, `sources` |
| `specialties` | 13 | Display `name` and `map_query` for the external map search (idea §9) |
| `sources` | 23 | `title` and `url` of every reference used |

### Conditions by group

| Group | Count | Conditions |
|---|---|---|
| `primary_care` | 17 | Common cold, influenza, COVID-19, pharyngitis, sinusitis, acute bronchitis, allergic rhinitis, gastroenteritis, GERD, migraine, tension-type headache, UTI, kidney stones, iron deficiency anaemia, type 2 diabetes, conjunctivitis, low back pain |
| `infection` | 6 | Dengue, malaria, typhoid, chikungunya, pulmonary TB, viral hepatitis (A/E) |
| `skin` | 7 | Eczema, fungal skin infection, hives, scabies, acne, chickenpox, cellulitis |
| `emergency` | 8 | Heart attack, stroke, appendicitis, anaphylaxis, meningitis, asthma, pneumonia, heat stroke |

Base risk: 18 `SELF_CARE`, 14 `CONSULT_DOCTOR`, 6 `URGENT`. `visual: true` marks the 8 conditions a photo can help with (the 7 skin conditions and conjunctivitis); the CV class list in S0-NIS-2 is aligned with these.

### Fields

- **`icd10`:** WHO ICD-10 Version 2019 codes (the version India uses), **not** ICD-10-CM. Example: stroke is `I64`, which exists only in WHO ICD-10.
- **Symptom `weight`:** `3` = hallmark symptom, `2` = common, `1` = sometimes present. Every condition has at least one hallmark symptom.
- **`base_risk`:** the tier a condition implies on its own (`SELF_CARE`, `CONSULT_DOCTOR`, `URGENT`). The risk engine may only *raise* it: red flags and low confidence push it up, never down.
- **Red-flag `triggers`:** a red flag fires when **any** trigger matches. A trigger matches when **all** of its `all_of` parts are present. A part may set `min_severity` (`MILD` < `MODERATE` < `SEVERE`). Every red flag means `URGENT` (DR-02), so the file has no per-flag tier to get wrong.

```json
{ "all_of": [ { "symptom": "chest_pain" }, { "symptom": "shortness_of_breath" } ] }
```

### Red flags

| ID | Category | Fires on |
|---|---|---|
| `rf_cardiac_chest_pain` | cardiac | Severe chest pain, or chest pain with breathlessness, sweating, fainting or pain spreading to the arm/jaw/back |
| `rf_stroke_signs` | stroke | Face drooping, one-sided weakness, slurred speech or sudden vision loss |
| `rf_thunderclap_headache` | neurological | Sudden, very severe headache |
| `rf_altered_consciousness` | neurological | Confusion or a seizure |
| `rf_cauda_equina` | neurological | Loss of bladder/bowel control, or back pain with groin numbness |
| `rf_severe_breathing_difficulty` | breathing | Severe breathlessness or bluish lips/face |
| `rf_anaphylaxis` | anaphylaxis | Throat/lip/tongue swelling, or hives with breathlessness or wheezing |
| `rf_meningitis_signs` | infection | Fever with stiff neck, or a rash that does not fade under a glass |
| `rf_serious_bleeding` | bleeding | Vomiting blood, coughing up blood, or black/bloody stool |
| `rf_fever_with_bleeding` | bleeding | Fever with bleeding gums or nosebleeds (dengue warning sign) |
| `rf_severe_abdominal_pain` | abdominal | Severe abdominal pain |
| `rf_severe_dehydration` | dehydration | Unable to keep fluids down, or little or no urine |
| `rf_self_harm` | mental_health | Thoughts of self-harm or suicide |

## Sources

Every condition and red flag lists the `sources` it was taken from. The main ones:

- WHO ICD-10 Version 2019 browser: codes and names.
- NHS Health A to Z: symptoms and "when to get urgent help" sections.
- NICE Clinical Knowledge Summaries: red flags and referral criteria.
- WHO fact sheets for dengue (warning signs), malaria, typhoid, chikungunya, TB, hepatitis A and E, influenza, COVID-19, anaemia, diabetes, scabies, cardiovascular disease, stroke, meningitis, asthma and pneumonia.
- India's National Center for Vector Borne Diseases Control (dengue, malaria, chikungunya), NDMA heat-wave guidance, and Tele-MANAS (14416) for the mental-health red flag.

## Validating changes

Run this after every edit. CI runs the same checks through `pytest`.

```bash
python ml/datasets/conditions/validate_conditions.py     # prints "OK (...)" or every problem found
cd ml && ruff check . && pytest
```

The validator (`validate_conditions.py`, with the condition rules in `condition_checks.py`) checks that:

- IDs are unique snake_case and every reference resolves.
- ICD-10 codes are well-formed and not reused.
- Weights are 1–3, and each condition has at least one hallmark symptom.
- Red-flag triggers name real symptoms and valid severities.
- No two conditions share an identical symptom set.
- Every symptom is used somewhere.

## Open questions for later tasks

- **Unknown severity (S1-NIS-2):** if a red-flag part needs `SEVERE` and the user's severity is unknown, the risk engine should treat it as matched or ask a clarifying question. Uncertainty must never lower risk.
- **Symptom vocabulary (S0-KAV-1):** Kavya's canonical vocabulary should reuse these symptom IDs, so extraction and prediction speak the same language.
- **Runtime copy (S1-NIS-1):** the server image does not include `ml/`. The predictor task decides how the server gets this file (a copy under `server/app/services/prediction/data/` checked by a parity test, or a build step).
