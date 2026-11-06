# CV Plan — Skin-Image Model

**Owner:** Nisarg (AI/ML) · **Task:** S0-NIS-2 · **Requirements:** NFR-07, idea §3
**Code:** [`ml/cv/`](../ml/cv/) · **Config:** [`ml/cv/configs/baseline.yaml`](../ml/cv/configs/baseline.yaml)

This document fixes the decisions the CV tasks build on: what the model predicts, which data it learns from,
how the data is split, how it is measured, which backbone it uses, and the size and speed it must fit in production.
Changing a decision here needs a PR that updates this file and the config together.

---

## 1. Where the CV model sits in the product

The user can attach a photo **only** when the chat has picked up a visible symptom (idea §3).
The server analyses the photo in memory and throws it away ([privacy-and-safety.md](privacy-and-safety.md)).

```text
photo (in memory) ──► quality checks ──► ONNX model ──► class + probability
                         │ fail                            │ below threshold, or `unclear`
                         ▼                                 ▼
                "please retake" message           text-only chat continues
                                                           │ confident class
                                                           ▼
                              visual symptoms added to the assessment ──► deterministic risk engine
```

Safety boundaries (AI_RULES.md §2), which every CV task must keep:

- The model's output is **one more input** to the risk engine. It can add symptoms or raise the risk tier. It can never lower the risk, override a red flag, or produce a diagnosis by itself.
- The class name is **never shown to the user as a result**. The user sees the normal result screen (conditions as Likely / Possible / Less likely, risk level, disclaimer).
- `unclear`, low confidence and model errors all mean "carry on with text only". Uncertainty never lowers the risk.
- Images are never stored, logged or sent anywhere. Training data and model files are never committed to git.

---

## 2. Target classes

> **Outcome after S1-NIS-5 (3 Nov 2026):** only `eczema` and `urticaria` (plus `unclear`) have enough photos after cleaning.
> The other five failed the class-size rule below: DermaAmin's images are gone and SCIN has few of them. They are listed in
> `data.merged_into_unclear` and trained as `unclear`, and stay reachable through text symptoms.
> Counts: [dataset card §8](../ml/datasets/images/README.md). The table below is the original candidate list.

The candidate classes are the 7 skin conditions marked `visual: true` in
[`ml/datasets/conditions/conditions.json`](../ml/datasets/conditions/conditions.json), plus `unclear`.
Conjunctivitis is also `visual: true`, but it is an eye photo, not a skin photo, so this model leaves it out.

| Output index | Class | `condition_id` | Base risk | Why it is in |
|---|---|---|---|---|
| 0 | `eczema` | `atopic_dermatitis` | SELF_CARE | Very common; dry, itchy, scaly patches |
| 1 | `fungal_infection` | `fungal_skin_infection` | SELF_CARE | Common in India; ring-shaped rash |
| 2 | `urticaria` | `urticaria` | SELF_CARE | Hives; links to the anaphylaxis red flag through text symptoms |
| 3 | `scabies` | `scabies` | CONSULT_DOCTOR | Needs a doctor; often missed |
| 4 | `acne` | `acne` | SELF_CARE | Very common; clear visual pattern |
| 5 | `chickenpox` | `chickenpox` | SELF_CARE | Fluid-filled blisters |
| 6 | `cellulitis` | `cellulitis` | CONSULT_DOCTOR | Spreading skin infection; must not be missed |
| 7 | `unclear` | — | — | Anything the model should not judge (see below) |

**`unclear`** is trained as a real class *and* used as the abstain result:

- **Trained examples:** skin conditions outside the 7 classes, images the source marks as poor quality or not gradable, and a small set of non-skin photos.
- **Abstain rule:** if the top probability is below `inference.abstain_threshold` (start: 0.55), the answer is `unclear` whatever the top class is. The threshold is tuned on the validation set in S2-NIS-6.

**Class-size rule.** After the S1-NIS-5 pipeline, a class needs at least `data.min_train_images_per_class` (150)
training images and `data.min_test_images_per_class` (30) test images. If a class falls short even with the
supplement dataset, it is **dropped from the model**. Its images then go to `unclear`, and the condition is still reachable through text symptoms.
The dataset card records the real counts.

---

## 3. Datasets and licences

Licences were checked against the source pages on 2 Nov 2026. S1-NIS-5 copies the exact licence text and URLs into the dataset card (`ml/datasets/images/README.md`).

| Dataset | What it is | Licence | Decision |
|---|---|---|---|
| **SCIN** (Google Research) | ~5,000 volunteer cases / 10,000+ phone photos, dermatologist labels, self-reported and estimated Fitzpatrick skin type, Monk skin tone | **SCIN Data Use License**: worldwide, royalty-free; may reproduce, share and adapt; **attribution required**; **any attempt to re-identify contributors is prohibited** and ends the licence | **Primary** source for training, validation and test. Consumer phone photos match how our users take pictures. |
| **Fitzpatrick17k** | ~16,500 clinical atlas images (DermaAmin, Atlas Dermatologico), 114 conditions, Fitzpatrick skin type 1–6 | **CC BY-NC-SA 3.0**; images are downloaded from their original URLs, not from a mirror | **Supplement** for classes SCIN is short on, and the main **skin-tone fairness check** (its type V–VI images). Non-commercial use only. The share-alike term carries over to the published model, so the model card says so. |
| **DermNet** | Large dermatology atlas | Watermarked images: **CC BY-NC-ND 3.0**; unwatermarked images need a paid licence | **Not used.** "No derivatives" rules out the cropping, resizing and augmentation that training needs. Kaggle copies of DermNet have no clear permission either. |

Licence obligations we take on:

- Credit SCIN and Fitzpatrick17k, and link to their licences, in the model card, the dataset card and the Hugging Face repo.
- The published model is for **non-commercial, educational use**, because it is partly trained on NC-SA data. The model card states this.
- Never try to identify anyone in the images. Images are never shown in W&B, the app or the docs.
- Raw images stay in Kaggle datasets or Drive (`ml/data/` and `ml/datasets/raw/` are git-ignored). Git only holds manifests and download scripts.

---

## 4. Data pipeline and split strategy (S1-NIS-5)

Code, counts and the reviewed mapping table: [`ml/datasets/images/`](../ml/datasets/images/README.md) (dataset card).

1. **Map labels** from each source's vocabulary to the 8 classes, using the reviewed mapping table in the dataset card. This step uses metadata only.
   - A SCIN case is used for a class only when that class is its top-weighted dermatologist label. A tie between labels with different outcomes leaves the case out.
   - SCIN cases with no label (not gradable), or a top label outside the 7 classes, go to `unclear`. Look-alikes of a class (for example tinea versicolor, infected eczema) are left out, so `unclear` never teaches "this class look-alike cannot be judged".
   - Fitzpatrick17k only supplements the 7 classes; `unclear` comes from SCIN.
2. **Skin-tone group:** use Fitzpatrick type (SCIN: lower median of the dermatologists' estimates; Fitzpatrick17k: its label).

   | Group | Fitzpatrick types |
   |---|---|
   | `light` | I–II |
   | `medium` | III–IV |
   | `dark` | V–VI |
   | `unknown` | missing |

   Images in `unknown` are still used for training, and are reported separately.
3. **Split 70 / 15 / 15** (train / val / test) with seed 42, **from metadata only**, so dead links never change it:
   - **Grouped by case:** all images of one SCIN case land in the same split. Each Fitzpatrick17k image is its own group (atlas pages group by condition, not patient). SCIN images reused across cases are left out.
   - **Stratified by class × skin-tone group**, so every split has the same mix of classes and skin tones.
   - The **test split is frozen** once S1-NIS-5 merges. The split manifest (image ID → split, class, skin-tone group; no images) is versioned with the dataset card, pinned to the metadata checksums. Later tasks never re-split.
4. **Download** with scripts in `ml/datasets/images/` (SCIN from its public Cloud Storage bucket, Fitzpatrick17k from its CSV of source URLs). Dead links are logged and counted, not retried forever.
5. **Clean** against the frozen split, which only removes rows: drop images that fail to decode or have a side shorter than 128 px. Remove near-duplicates by perceptual hash, both within and across datasets (SCIN alone has known duplicate images); each duplicate set keeps its test copy first, then val, so test never leaks into training. Sets with conflicting labels are dropped.

---

## 5. Model choice (S1-NIS-6)

Transfer learning from an ImageNet-pretrained backbone in `timm`. The baseline trains both candidates with the same config and keeps the one with the higher validation macro-F1 that fits the budget in §7.

| Candidate | `timm` name | Params | FP32 ONNX (approx.) | Why |
|---|---|---|---|---|
| **EfficientNet-B0** (default) | `efficientnet_b0` | ~5.3 M | ~21 MB | Strong accuracy for its size on small medical datasets |
| MobileNetV3-Large | `mobilenetv3_large_100` | ~5.5 M | ~22 MB | Lower latency on CPU if B0 misses the speed budget |

Both stay under the 25 MB limit even before INT8 quantization (roughly 4× smaller after).
With 3 classes, both are about 4 M parameters (≈ 16–17 MB FP32).
`timm` downloads the ImageNet weights from the Hugging Face Hub (`timm/efficientnet_b0.ra_in1k`, `timm/mobilenetv3_large_100.ra_in1k`).

**Ready-made skin models on Hugging Face** were checked on 3 Nov 2026, to cover the merged conditions without our own data. None is used:

- **Community skin-disease classifiers** (for example `Jayanth2002/dinov2-base-finetuned-SkinDisease`, `Siraja704/DermaAI`, `*-finetuned-dermnet`) are ruled out:
  - Their training data is unstated, or is DermNet-derived (excluded in §3: no derivatives).
  - Accuracy is reported only on their own splits, with no skin-tone evaluation.
  - Several are skin-cancer models, which is out of scope.
  - The DINOv2 and ViT ones (≈ 86 M parameters) are also far over the 25 MB budget.
- **Google Derm Foundation** (`google/derm-foundation`) is ruled out:
  - It is a strong dermatology embedding model, but it is gated under the Health AI Developer Foundations terms.
  - It is about 1.5 GB (TensorFlow, BiT ResNet-101x3), so it cannot meet the 512 MB / 1 s production budget.
  - It could still be a teacher, or an offline evaluation reference, in a later version.
Larger backbones (ResNet-50, ViT) are ruled out by the memory and latency budget.

**Training setup**, from `configs/baseline.yaml`:
- 224 × 224 input; resize the short side to 256, then centre-crop; ImageNet mean and std.
- AdamW with a cosine schedule. The backbone is frozen for the first 2 epochs, then everything is fine-tuned.
- Label smoothing 0.1. Class weights from inverse square-root frequency.
- Mixed precision on GPU; fixed seed.
- **Where it runs:** Kaggle (or Colab) free GPUs. The notebook only clones the repo and runs `python ml/cv/train.py --config ...`, so the `.py` files stay the single source of truth (AI_RULES.md §4.13).
- **Tracking:** W&B project `symptom-checker-cv`, metrics and configs only, never images. `WANDB_API_KEY` lives in Kaggle secrets.

---

## 6. Metrics and targets

Measured on the frozen test set, plus each skin-tone group separately. The baseline (S1-NIS-6) only records numbers. The targets apply from v2 (S2-NIS-4) and are reviewed against the baseline.

| Metric | Why | v2 target |
|---|---|---|
| **Macro-F1** over the 8 classes | Primary metric; classes are imbalanced, so plain accuracy misleads | ≥ 0.65 |
| Per-class precision, recall + confusion matrix | Shows which conditions get confused | reported |
| **Recall for `cellulitis` and `scabies`** | These need a doctor; missing them matters most | ≥ 0.70 each |
| **Skin-tone gap**: largest macro-F1 difference between `light`, `medium` and `dark` | Fairness (NFR-07); dark skin is under-represented in most dermatology data | ≤ 0.10 |
| Expected calibration error (ECE) | The abstain threshold only works if probabilities are honest | ≤ 0.10 (temperature scaling allowed) |
| Selective accuracy vs coverage | How often we answer, and how right we are when we do | accuracy ≥ 0.80 at the chosen threshold |
| Robustness set: blurry, dark, irrelevant and edge images | Must come out `unclear`, not a confident class (S3-NIS-1) | ≥ 90% `unclear` |

If the skin-tone gap target is missed, S2-NIS-4 rebalances by skin-tone group before anything else. The model card always reports the gap, even when the target is met.

---

## 7. ONNX export, size and latency budget

| Budget | Limit | Checked in |
|---|---|---|
| Model file | ≤ **25 MB** (target ≤ 8 MB after INT8) | S2-NIS-5 |
| Inference, including preprocessing | ≤ **1 s** per image on the production CPU (Render free tier or VPS), p95 over 100 runs | S3-NIS-4 |
| Memory | Whole API process < **512 MB** RAM; the CV session ≤ 150 MB of it | S3-NIS-4 |

Export path (S2-NIS-5):
1. PyTorch → ONNX, opset 17, dynamic batch axis.
2. **INT8 static quantization** with ONNX Runtime, calibrated on 200 training images.
3. **Parity tests:**
   - ONNX FP32 vs PyTorch: top-1 agreement ≥ 99% on the test set; max probability difference ≤ 1e-3.
   - INT8 vs FP32: top-1 agreement ≥ 97%; macro-F1 drop ≤ 0.02.
   - If INT8 fails, ship FP32 (still within 25 MB).
4. Publish to Hugging Face Hub as `NT1906/skin-cv`, with a model card. The server pins it by revision (`CV_MODEL_REVISION`).

**Serving contract (S2-NIS-6):** the server must apply exactly the training preprocessing: EXIF orientation fix, RGB, resize 256, centre-crop 224, ImageNet normalisation. A parity test runs the same tiny fixture image through the training transform and the server transform and requires identical tensors. Inference runs in the threadpool, so it never blocks the event loop.

---

## 8. Risks and limitations

| Risk | Mitigation |
|---|---|
| Too few images for rare classes (scabies, chickenpox) | Fitzpatrick17k supplement; class-size rule in §2 drops a class rather than shipping a weak one |
| Atlas photos (Fitzpatrick17k) look different from phone photos | Test on SCIN phone photos; report results per dataset |
| Skin-tone bias | Stratified split, per-group metrics, gap target, rebalancing in S2-NIS-4 |
| Over-confident wrong answers | Calibration, abstain threshold, `unclear` class, robustness set; the risk engine never lowers risk from CV |
| Labels are dermatologist opinions from photos, not confirmed diagnoses | Stated in the model card; CV output only adds symptoms, never a diagnosis |
| Licence drift | Licence text and access date stored in the dataset card; re-check before each published model version |

The model is **not clinically validated** and is for an informational triage aid only (as `conditions.json` also states).

---

## 9. Task map

| Task | What it delivers from this plan |
|---|---|
| S0-NIS-2 (this) | This plan; `ml/cv/` scaffold: config, config loader, `train.py` skeleton, requirements |
| S1-NIS-5 | §3–§4: download scripts, cleaning, label mapping, frozen split, dataset card |
| S1-NIS-6 | §5: baseline training of both backbones, W&B runs, first metrics report |
| S2-NIS-4 | §6: augmentation, class and skin-tone balancing, tuning to the v2 targets |
| S2-NIS-5 | §7: ONNX export, INT8, parity tests, Hugging Face Hub + model card |
| S2-NIS-6 | §1, §7: `OnnxImageAnalyzer`, quality checks, abstain threshold, preprocessing parity |
| S3-NIS-1 / 3 / 4 | Final evaluation incl. robustness and fairness; model cards; production CPU performance |

**Kaggle notebook:** created in S1-NIS-6 ([#29](https://github.com/NT1906/AI_based_Symptom_Checker/issues/29)), when there is training code to run. Its link is added to [`ml/cv/README.md`](../ml/cv/README.md) in that PR.
