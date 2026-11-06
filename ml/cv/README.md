# `ml/cv/` — Skin-Image Model (training side)

**Owner:** Nisarg · **Plan:** [docs/cv-plan.md](../../docs/cv-plan.md) · **Requirements:** NFR-07, idea §3

Training, evaluation and ONNX export code for the skin-image model. This folder is **never deployed**.
The server only loads the exported ONNX model from Hugging Face Hub (`server/app/services/image/`, S2-NIS-6).

## Layout

| Path | What it is |
|---|---|
| `configs/baseline.yaml` | Baseline config: classes, merged labels, data split, backbone, training, abstain threshold, export budget |
| `train_config.py` · `config_schema.py` · `config_readers.py` | `load_config()` → validated, frozen `TrainConfig` (`ConfigError` names the bad key) |
| `train.py` | Training entry point: `--dry-run`, then train → best checkpoint → val/test metrics + report |
| `cv_data.py` | Cleaned manifest → samples per split; merged labels → `unclear`; class weights |
| `cv_preprocess.py` | Pillow preprocessing shared with the server (EXIF fix, RGB, resize short side, centre crop) |
| `cv_model.py` | Torch parts: preloaded dataset (+ PNG cache), `timm` model, train/predict loops |
| `cv_metrics.py` | Macro-F1, per-class scores, confusion matrix, per-skin-tone gap, ECE, abstain coverage; Markdown report |
| `requirements.txt` | Training dependencies (torch, timm, onnx, wandb, …) |
| `test_*.py` | Unit tests. Torch tests (a 2-epoch CPU run, crop parity) are skipped when torch is missing, as in CI |

Training data: [`ml/datasets/images/`](../datasets/images/README.md) (dataset card, frozen split manifest). Coming in later tasks: `export_onnx.py` (S2-NIS-5).

## Public interface

```python
from train_config import load_config

config = load_config()  # configs/baseline.yaml, raises ConfigError if invalid
config.class_names  # ('eczema', 'urticaria', 'unclear'); index = model output
config.data.image_size  # 224
config.abstain_threshold  # 0.55, below this the answer is 'unclear'
```

`unclear` is always the last class, and only `unclear` has no `condition_id`.
Every other class maps to a `visual: true` skin condition in `ml/datasets/conditions/conditions.json`.
Every remaining one is listed in `data.merged_into_unclear` (too few photos; trained as `unclear`). A test enforces this.

## Train on Kaggle

Training is not in CI, and runs on a Kaggle (or Colab) GPU. Each step:
- **Notebook:** create a **private** notebook with **GPU T4 or P100** and **Internet on**.
- **Images:** add the committed version of the image download notebook (`ml/datasets/images/README.md` §7) under **Add Input → Notebook output**. Its images are under `/kaggle/input/<that-notebook>/images`.
- **W&B (optional):** put `WANDB_API_KEY` in **Add-ons → Secrets**, never in the notebook.

```python
!git clone -b develop https://github.com/NT1906/AI_based_Symptom_Checker.git
%cd AI_based_Symptom_Checker
!pip install -q "timm>=1.0,<2" "PyYAML>=6,<7" wandb

import os
from kaggle_secrets import UserSecretsClient
os.environ["WANDB_API_KEY"] = UserSecretsClient().get_secret("WANDB_API_KEY")

IMAGES = "/kaggle/input/<that-notebook>/images"
for backbone in ["efficientnet_b0", "mobilenetv3_large_100"]:
    !python ml/cv/train.py --manifest {IMAGES}/clean_v1.csv --images {IMAGES} --cache-dir /kaggle/working/cache --backbone {backbone} --output-dir /kaggle/working/runs/{backbone} --wandb
```

- **Run time:** the first run decodes about 9,200 photos once (several minutes). It caches them at 256 px, so the second backbone starts fast.
- **Outputs per backbone:** `runs/<backbone>/` holds `best.pt` (best validation macro-F1), `metrics.json` and `report.md` (val + frozen test).
- **Picking the baseline:** keep the backbone with the higher **validation** macro-F1 (§5 of the plan). The test numbers are reported and never used to choose.
- **Without W&B:** leave out `--wandb` and the secrets lines.

Other commands:

```bash
python ml/cv/train.py --dry-run                     # validate the config, print the plan (CI runs this)
python ml/cv/train.py --limit 32 --epochs 1 ...     # quick smoke run on a few images
```

## Test

```bash
cd ml
pip install ruff pytest -r requirements-ci.txt
ruff check . && pytest
```

## Rules

- Datasets, checkpoints, `.onnx` and `.pt` files are **never committed** (they are git-ignored). Data lives in Kaggle or Drive, models on Hugging Face Hub.
- Never log or display training images (W&B gets metrics and configs only). Never try to re-identify anyone (SCIN licence).
- Changing a class, the split or the budget means updating `docs/cv-plan.md` in the same PR.
