# Skin-image dataset v1 (dataset card)

**Owner:** Nisarg (cv) · **Task:** S1-NIS-5 · **Requirements:** NFR-07 · **Plan:** [docs/cv-plan.md](../../../docs/cv-plan.md) §2–§4

Training, validation and test data for the skin-image model (`ml/cv/`).
**Git holds only metadata:** the split manifest (image ID → split, class, skin tone, download URL), the scripts and this card.
Images are downloaded on Kaggle or Colab into a git-ignored folder. They are never committed, shown in W&B, the app or the docs, or logged.

## 1. Intended use and limits

- **Educational, non-commercial use only.** Part of the data is CC BY-NC-SA (§2), so anything trained on it is non-commercial too.
- **The labels are opinions, not diagnoses.** They are dermatologists' calls from photos (SCIN) or atlas captions (Fitzpatrick17k), not confirmed diagnoses. The model only adds visual symptoms; it never diagnoses (cv-plan §1).
- **Never try to identify anyone in the images.** Under the SCIN licence (§3(b)), any attempt to re-identify or re-link a contributor ends all rights to the data.
- **Where SCIN comes from:** volunteers who found it through Google Search, mostly in the US. The phone photos match our users, but the people may not.

## 2. Sources and licences

Licences were checked against the source pages on 3 Nov 2026.

| Source | What we use | Licence | Pinned by |
|---|---|---|---|
| **SCIN** (Google Research), [repo](https://github.com/google-research-datasets/scin), DOI [10.5281/zenodo.10819503](https://zenodo.org/doi/10.5281/zenodo.10819503) | All 5,033 cases (≈10,400 phone photos): the mapped classes **and** every `unclear` image | **SCIN Data Use License**, full text in [`licenses/SCIN_LICENSE.txt`](licenses/SCIN_LICENSE.txt): worldwide, royalty-free; reproduce, share and adapt allowed; attribution and a licence notice required; no re-identification | SHA-256 of `scin_cases.csv` and `scin_labels.csv` (the bucket is not versioned) |
| **Fitzpatrick17k** (Groh et al., 2021), [repo](https://github.com/mattgroh/fitzpatrick17k) | Only the images of mapped classes (supplement). Images come from their original URLs (Atlas Dermatologico, DermaAmin), not from a mirror | **[CC BY-NC-SA 3.0](http://creativecommons.org/licenses/by-nc-sa/3.0/)**. Original images were collected from [Atlas Dermatologico](http://atlasdermatologico.com.br/) and [DermaAmin](https://www.dermaamin.com/site/) | Commit `9865ce9` of `fitzpatrick17k.csv`, plus its SHA-256 |
| DermNet | Not used | CC BY-NC-ND 3.0: "no derivatives" rules out the cropping and augmentation that training needs | — |

What we owe the sources, carried into the model card (S3-NIS-3) and the Hugging Face repo (S2-NIS-5):

- **Credit both datasets.** Link SCIN's licence, mark our images as modified (resized and cropped), and keep SCIN's disclaimer of warranties.
- **Release the model under share-alike, non-commercial terms,** because of the CC BY-NC-SA data.
- **Cite the Fitzpatrick17k paper:** Groh M. *et al.*, "Evaluating deep neural networks trained on clinical images in dermatology with the Fitzpatrick 17k dataset", CVPR Workshops 2021.

## 3. Label mapping (reviewed table)

The mapping lives in [`image_labels.py`](image_labels.py); change it and this table together.

| Class | SCIN `weighted_skin_condition_label` | Fitzpatrick17k `label` |
|---|---|---|
| `eczema` | Eczema | eczema |
| `fungal_infection` | Tinea | — (none in the dataset) |
| `urticaria` | Urticaria | urticaria |
| `scabies` | Scabies | scabies |
| `acne` | Acne | acne, acne vulgaris |
| `chickenpox` | Chicken pox exanthem | — |
| `cellulitis` | Cellulitis, Cellulitis of hand excluding finger | — |
| `unclear` | No label (not gradable), or a top label outside the classes | — (Fitzpatrick17k is never used for `unclear`) |

Rules:

- **SCIN uses the top-weighted label only.** A case gets a class only when that class has the highest weight. If the highest weight is tied between labels that lead to different outcomes, the case is left out.
- **Look-alikes are left out, not called `unclear`.** If they went to `unclear`, the model would learn that something that looks like a class can't be judged. The list:
  - Variants with another code: tinea versicolor (B36.0, not dermatophytosis B35); candida infections; deep fungal infection.
  - Eczema subtypes: infected, lichenified, crusted, dyshidrotic.
  - Urticarial vasculitis and PUPPP.
  - Acne keloidalis, acne urticata and acneiform eruption.
  - Erysipelas.
- **Fitzpatrick17k images reviewed as "3 Wrongly labelled" are left out.**
- **SCIN images that appear in more than one case are left out (42 images).** Otherwise one image could land in two splits or carry two labels.

## 4. Skin tone and split

- **Skin-tone groups,** from `data.skin_tone_groups` in `ml/cv/configs/baseline.yaml`:
  - `light` is Fitzpatrick I–II, `medium` III–IV, `dark` V–VI.
  - `unknown` means no estimate. Those images are still used, and reported separately.
- **Which skin type an image gets:**
  - SCIN: the lower median of the dermatologists' estimates (up to 3).
  - Fitzpatrick17k: its `fitzpatrick_scale` value.
- **Split 70 / 15 / 15, seed 42:**
  - Grouped by case, so every image of a SCIN case lands in the same split. Each Fitzpatrick17k image is its own group, because atlas pages group images by condition, not by patient.
  - Stratified by class × skin-tone group.
- **The split uses metadata only and is frozen.** Dead links and cleaning can remove rows later, but never move an image to another split. Later tasks never re-split; `build_manifest.py` refuses to run if the metadata checksums change.

## 5. Counts (manifest v1, before download and cleaning)

10,598 images in 5,754 groups. Train has 7,421, val 1,593 and test 1,584. These figures come from [`manifest/summary_v1.json`](manifest/summary_v1.json).

| Class | SCIN | Fitzpatrick17k | Train | Val | Test | Light | Medium | Dark | Unknown | Class-size rule |
|---|---|---|---|---|---|---|---|---|---|---|
| `eczema` | 826 | 204 | 719 | 157 | 154 | 494 | 410 | 96 | 30 | meets |
| `fungal_infection` | 136 | 0 | 98 | 21 | 17 | 60 | 59 | 12 | 5 | **below** |
| `urticaria` | 359 | 151 | 358 | 77 | 75 | 209 | 255 | 23 | 23 | meets |
| `scabies` | 13 | 339 | 247 | 53 | 52 | 107 | 141 | 76 | 28 | meets |
| `acne` | 88 | 517 | 425 | 90 | 90 | 368 | 188 | 47 | 2 | meets |
| `chickenpox` | 1 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | **below** |
| `cellulitis` | 19 | 0 | 12 | 4 | 3 | 12 | 7 | 0 | 0 | **below** |
| `unclear` | 7,945 | 0 | 5,561 | 1,191 | 1,193 | 2,688 | 3,411 | 617 | 1,229 | meets |

The class-size rule needs ≥ 150 train and ≥ 30 test images (cv-plan §2).

Images left out:

| Reason | Count |
|---|---|
| Fitzpatrick17k label not mapped | 15,349 |
| Fitzpatrick17k reviewed as wrongly labelled | 17 |
| SCIN tied top labels | 880 |
| SCIN class look-alike | 98 |
| SCIN image shared between cases | 42 |

## 6. Known issues

- **Three classes miss the class-size rule even before cleaning:**
  - `fungal_infection`, `chickenpox` and `cellulitis`. Neither source has enough of them, and cleaning can only lower the counts.
  - Under cv-plan §2 they are dropped from the model and their images go to `unclear`. The conditions stay reachable through text symptoms.
  - The class list in `ml/cv/configs/baseline.yaml` (and the server's `ImageLabel`) changes in S1-NIS-6 (#29), once the post-cleaning counts below are in.
- **DermaAmin links look dead.** It hosts 1,012 of the 1,211 Fitzpatrick17k images.
  - In a 3 Nov 2026 sample, 30 of 30 DermaAmin URLs failed (26 HTTP 404, 4 connection resets). All 10 Atlas Dermatologico URLs worked.
  - If DermaAmin is fully gone, `acne` (≈90 train) and `scabies` (≈106 train) also fall below the rule. That leaves `eczema`, `urticaria` and `unclear`.
  - The real numbers come from `clean_report.json` after the Kaggle run (§7).
- **Dark skin is under-represented:**
  - `urticaria`: 23 dark images. `acne`: 47.
  - The skin-tone gap metric (cv-plan §6) and the rebalancing in S2-NIS-4 handle this, and the model card reports it.
- **`unclear` is 75% of the images.** Training uses class weights (`inverse_sqrt_frequency`), and S1-NIS-6 may subsample it.
- **No non-skin photos yet.** cv-plan §2 lists a small set of non-skin photos for `unclear`; they are added with the robustness set (S3-NIS-1).

## 7. How to run

**Step 1, already done; the output is committed.** Build the manifest from metadata only (needs PyYAML):

```bash
python ml/datasets/images/build_manifest.py   # writes manifest/split_v1.csv + summary_v1.json
```

**Step 2, on Kaggle or Colab.** Download and clean the images. This needs internet on and about 15 GB of space; SCIN photos average 1.4 MB.

```bash
pip install "pillow>=11,<13" "PyYAML>=6,<7"
python ml/datasets/images/download_images.py --out /kaggle/working/images
python ml/datasets/images/clean_images.py --images /kaggle/working/images
```

The download step:
- Skips files that already exist, so a stopped run can resume.
- Retries a dead link once, then records it in `download_report.json`.
- Sends a plain project User-Agent and uses 4 parallel requests by default, to be gentle with the atlas sites.

The cleaning step:
- Drops images that are missing, fail to decode, or are smaller than 128 px on a side.
- Removes near-duplicates by 64-bit dHash (≤ 3 bits apart). In each duplicate set it keeps the test copy first, then val, then train; a set with conflicting labels is dropped.
- Writes `clean_v1.csv`, which is what training reads, and `clean_report.json`.

After the first full run, copy the `clean_report.json` counts into a new §8 here (S1-NIS-6).

## 8. Files

| Path | What it is |
|---|---|
| `manifest/split_v1.csv` | Frozen manifest: `split`, `image_id`, `source`, `group_id`, `label`, `skin_tone`, `source_label`, `reason`, `url` |
| `manifest/summary_v1.json` | Counts above, seed, fractions, and the pinned metadata URLs and SHA-256s |
| `build_manifest.py` | Step 1: fetch metadata, map labels, split, write the manifest |
| `image_labels.py` · `image_sources.py` · `image_split.py` | Label and skin-tone mapping · metadata readers · grouped stratified split |
| `download_images.py` · `clean_images.py` | Step 2 (Kaggle): download, then clean against the frozen split |
| `licenses/SCIN_LICENSE.txt` | SCIN Data Use License, verbatim |
| `test_*.py` | Unit tests (tiny fixtures, no network); run with `cd ml && pytest datasets/images` |
