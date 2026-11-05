# `ml/cv/` — Skin-Image Model (training side)

**Owner:** Nisarg · **Plan:** [docs/cv-plan.md](../../docs/cv-plan.md) · **Requirements:** NFR-07, idea §3

Training, evaluation and ONNX export code for the skin-image model. This folder is **never deployed**.
The server only loads the exported ONNX model from Hugging Face Hub (`server/app/services/image/`, S2-NIS-6).

## Layout

| Path | What it is |
|---|---|
| `configs/baseline.yaml` | Baseline config: classes, data split, backbone, training, abstain threshold, export budget |
| `train_config.py` | `load_config()` / `parse_config()`: read and validate a config into a frozen `TrainConfig` |
| `config_schema.py` | The `TrainConfig` dataclasses everything else reads |
| `config_readers.py` | Typed readers and `ConfigError` used by the loader |
| `train.py` | Training entry point. **Skeleton:** `--dry-run` works now; the training loop arrives in S1-NIS-6 (#29) |
| `requirements.txt` | Training dependencies (torch, timm, onnx, wandb, …) |
| `test_*.py` | Unit tests; they need only PyYAML (`ml/requirements-ci.txt`) |

Training data: [`ml/datasets/images/`](../datasets/images/README.md) (dataset card, frozen split manifest). Coming in later tasks: `evaluate.py` (S1-NIS-6), `export_onnx.py` (S2-NIS-5).

## Public interface

```python
from train_config import load_config

config = load_config()  # configs/baseline.yaml, raises ConfigError if invalid
config.class_names  # ('eczema', ..., 'cellulitis', 'unclear'); index = model output
config.data.image_size  # 224
config.abstain_threshold  # 0.55, below this the answer is 'unclear'
```

`unclear` is always the last class, and only `unclear` has no `condition_id`.
Every other class maps to a `visual: true` skin condition in `ml/datasets/conditions/conditions.json`. A test enforces this.

## Run

```bash
# From the repository root
python ml/cv/train.py --dry-run                                  # validate the config, print the plan
python ml/cv/train.py --config ml/cv/configs/baseline.yaml       # train (from S1-NIS-6)
```

**Kaggle / Colab:** the notebook only clones the repo, installs `ml/cv/requirements.txt` and runs `train.py`. All logic stays in `.py` files.
Put `WANDB_API_KEY` in Kaggle secrets, never in the notebook.
The notebook link is added here in S1-NIS-6 (#29).

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
