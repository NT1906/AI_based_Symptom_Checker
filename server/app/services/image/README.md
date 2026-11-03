# Image service

**Owner:** Nisarg · **Task:** S1-NIS-4 · **Plan:** [docs/cv-plan.md](../../../../docs/cv-plan.md)

Turns an optional skin photo into **visual symptoms** for the assessment. The label the analyzer picks is internal: it is never shown to the user as a result, and it never lowers risk. Photo findings join the assessment like text findings, so the deterministic risk engine still makes every risk decision (AI_RULES.md §2).

Images are analysed in memory only, and never stored or logged ([privacy-and-safety.md](../../../../docs/privacy-and-safety.md)).

## Files

| File | What it holds |
|---|---|
| `schemas.py` | `ImageLabel` (CV classes, in model output order), `UnclearReason`, `ImageAnalysis` |
| `analyzer.py` | `ImageAnalyzer` protocol, `ImageAnalysisError` (503, `IMAGE_ANALYSIS_UNAVAILABLE`) |
| `findings.py` | Label → condition and visual symptoms; `build_analysis()`; `to_extracted_symptoms()` |
| `mock_analyzer.py` | `MockImageAnalyzer`, used when `CV_PROVIDER=mock` |
| `factory.py` | `build_image_analyzer(provider)` and the FastAPI dependency `get_image_analyzer` |

## Interface

```python
class ImageAnalyzer(Protocol):
    async def analyze(self, image: bytes) -> ImageAnalysis: ...
```

`image` is bytes that already passed upload validation (size, type, EXIF stripped; S1-VIV-4).

| Outcome | What comes back | What the caller does |
|---|---|---|
| Photo shows a known pattern | `ImageAnalysis` with `label`, `condition_id`, `symptom_ids` | Merge the symptoms (below) |
| Photo is blurry, dark or too small | `label=UNCLEAR`, `reason=POOR_QUALITY` | Ask for a retake, or carry on with text |
| Model is unsure, or chose `unclear` | `label=UNCLEAR`, `reason=LOW_CONFIDENCE` / `NOT_RECOGNISED` | Carry on with text only |
| Empty bytes | raises `ValidationError` (422) | Reject the upload |
| Analyzer cannot run | raises `ImageAnalysisError` (503) | Carry on with text only |

An unclear result is a normal answer, not an error, and it never changes the risk.

## Visual symptoms per label

Only symptoms a photo can show are added. Itching, pain, warmth and fever always come from the user.

| Label | Condition | Symptoms added |
|---|---|---|
| `eczema` | `atopic_dermatitis` | `dry_skin`, `scaly_skin`, `skin_rash` |
| `fungal_infection` | `fungal_skin_infection` | `ring_shaped_rash`, `scaly_skin` |
| `urticaria` | `urticaria` | `hives` |
| `scabies` | `scabies` | `small_itchy_bumps`, `skin_burrows` |
| `acne` | `acne` | `pimples`, `blackheads_or_whiteheads` |
| `chickenpox` | `chickenpox` | `fluid_filled_blisters` |
| `cellulitis` | `cellulitis` | `spreading_redness`, `skin_swelling` |
| `unclear` | — | nothing |

Tests check that the labels match `ml/cv/configs/baseline.yaml` in order, and that every added symptom belongs to that condition in the dataset.
`hives` from a photo plus breathing trouble from the chat still triggers the anaphylaxis red flag.

## Using it (S1-VIV-4 endpoint, S2-DAR-2 merge)

```python
from app.services.assessment.orchestrator import merge_symptoms
from app.services.image import get_image_analyzer, to_extracted_symptoms

analysis = await analyzer.analyze(image_bytes)  # analyzer = Depends(...)
symptoms = merge_symptoms(symptoms, to_extracted_symptoms(analysis))
```

Added symptoms have severity `UNKNOWN`, because a photo cannot say how bad a symptom feels. The user still confirms every symptom before the result.

## Providers (`CV_PROVIDER`)

| Value | Analyzer |
|---|---|
| `mock` (local, CI) | `MockImageAnalyzer`: returns `eczema` for any non-empty photo. Tests can pick another label, an unclear reason, or `fail=True`. |
| `onnx` (staging, production) | Raises `ImageAnalysisError` until `OnnxImageAnalyzer` lands in S2-NIS-6. It does **not** fall back to the mock, so fake findings can never reach real users. |
| anything else | Raises `ImageAnalysisError` |

## Tests

```bash
cd server && pytest tests/unit/image -q
```
