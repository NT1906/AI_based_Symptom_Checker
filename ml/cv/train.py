"""Train the baseline skin-image model (run on a Kaggle or Colab GPU).

Responsibilities:
    - Parse the command line and load a validated config (``train_config``).
    - ``--dry-run`` checks the config and the plan without torch, so CI runs it.
    - Train: seed, load the cleaned manifest, freeze the backbone for the
      first epochs, then fine-tune with AdamW + cosine schedule, class-weighted
      label-smoothed loss and mixed precision (docs/cv-plan.md §5).
    - Keep the checkpoint with the best validation macro-F1, then evaluate it
      on val and the frozen test split; write ``metrics.json`` + ``report.md``.
    - Log metrics and the config to W&B with ``--wandb`` (never images).

Checkpoints and reports go to ``--output-dir`` (default ``ml/checkpoints/``,
git-ignored). Run from the repository root:
    python ml/cv/train.py --manifest /kaggle/working/images/clean_v1.csv \
        --images /kaggle/working/images --output-dir /kaggle/working/runs/b0
    python ml/cv/train.py --dry-run

Owner: Nisarg (cv) · Task: S0-NIS-2, S1-NIS-6 · Requirements: NFR-07
"""

import argparse
import json
import logging
import sys
import time
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from config_readers import ConfigError
from config_schema import TrainConfig
from cv_data import SPLITS, Sample, class_counts, class_weights, read_splits
from cv_metrics import evaluate, format_report
from train_config import BACKBONES, DEFAULT_CONFIG_PATH, load_config

log = logging.getLogger("cv.train")

EXIT_OK = 0
EXIT_CONFIG_ERROR = 2
ML_DIR = Path(__file__).resolve().parents[1]
DEFAULT_IMAGES = ML_DIR / "data" / "images"
DEFAULT_OUTPUT = ML_DIR / "checkpoints"

TRAINING_STEPS = (
    "seed every random generator from config.seed",
    "load the cleaned split manifest (clean_v1.csv) from S1-NIS-5",
    "preload train/val/test images with the shared preprocessing",
    "create the timm backbone (ImageNet weights from Hugging Face Hub)",
    "train the head with the backbone frozen",
    "fine-tune the whole network with AdamW and a cosine schedule",
    "log metrics and config to W&B (never images)",
    "keep the best checkpoint by validation macro-F1 outside git",
    "evaluate it on val and test; write metrics.json and report.md",
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Arguments without the program name. ``None`` reads ``sys.argv``.

    Returns:
        The parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Train the skin-image model.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument(
        "--manifest", type=Path, default=DEFAULT_IMAGES / "clean_v1.csv"
    )
    parser.add_argument("--images", type=Path, default=DEFAULT_IMAGES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache-dir", type=Path, help="resized-PNG cache (optional)")
    parser.add_argument("--backbone", choices=sorted(BACKBONES), help="override config")
    parser.add_argument("--epochs", type=int, help="override config (smoke runs)")
    parser.add_argument("--limit", type=int, help="max images per split (smoke runs)")
    parser.add_argument("--workers", type=int, default=2, help="DataLoader workers")
    parser.add_argument("--no-pretrained", action="store_true", help="random init")
    parser.add_argument("--wandb", action="store_true", help="log to W&B")
    parser.add_argument(
        "--dry-run", action="store_true", help="validate the config, then exit"
    )
    return parser.parse_args(argv)


def describe_plan(config: TrainConfig) -> list[str]:
    """Summarise what a training run with this config would do.

    Args:
        config: A validated config.

    Returns:
        Human-readable lines: model, classes, data, then the training steps.
    """
    training = config.training
    merged = ", ".join(config.data.merged_into_unclear) or "none"
    lines = [
        f"backbone: {config.model.backbone} (pretrained={config.model.pretrained})",
        f"classes ({len(config.classes)}): {', '.join(config.class_names)}",
        f"merged into unclear: {merged}",
        f"data: {', '.join(config.data.sources)} at {config.data.image_size}px",
        f"epochs: {training.epochs} ({training.freeze_backbone_epochs} frozen)",
    ]
    lines.extend(f"step {i}: {step}" for i, step in enumerate(TRAINING_STEPS, 1))
    return lines


def run_training(config: TrainConfig, args: argparse.Namespace) -> dict[str, Any]:
    """Train, evaluate and save one model.

    Args:
        config: A validated config.
        args: Parsed command line (paths and overrides).

    Returns:
        Split name -> metrics for the best checkpoint (val and test).
    """
    # Why: torch is imported here so --dry-run and CI never need it.
    import torch
    from cv_model import build_model, seed_everything

    seed_everything(config.seed)
    started = time.monotonic()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    splits = read_splits(args.manifest, args.images, config, args.limit)
    loaders = _loaders(config, args, splits)
    backbone = args.backbone or config.model.backbone
    model = build_model(config, backbone, pretrained=not args.no_pretrained)
    run = _fit(config, args, model.to(device), loaders, splits, device, backbone)

    checkpoint = torch.load(
        args.output_dir / "best.pt", map_location=device, weights_only=True
    )
    model.load_state_dict(checkpoint["state_dict"])
    metrics = {
        s: _evaluate_split(config, model, loaders, splits, s, device)
        for s in ("val", "test")
    }
    run["minutes"] = round((time.monotonic() - started) / 60, 1)
    report = {"run": run, "metrics": metrics}
    (args.output_dir / "metrics.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    (args.output_dir / "report.md").write_text(
        format_report(run, metrics), encoding="utf-8"
    )
    log.info(
        "done: test macro-F1 %.4f -> %s", metrics["test"]["macro_f1"], args.output_dir
    )
    return metrics


def _loaders(
    config: TrainConfig, args: argparse.Namespace, splits: dict[str, list[Sample]]
) -> dict[str, Any]:  # Any: torch DataLoader, imported lazily
    """Preload every split and wrap it in a DataLoader."""
    from cv_model import ImageDataset
    from torch.utils.data import DataLoader

    started = time.monotonic()
    loaders = {}
    for split in SPLITS:
        dataset = ImageDataset(
            splits[split], config, train=split == "train", cache_dir=args.cache_dir
        )
        loaders[split] = DataLoader(
            dataset,
            batch_size=config.training.batch_size,
            shuffle=split == "train",
            num_workers=args.workers,
        )
    sizes = {s: len(splits[s]) for s in SPLITS}
    log.info("images_loaded: %s in %.0fs", sizes, time.monotonic() - started)
    return loaders


def _fit(
    config: TrainConfig,
    args: argparse.Namespace,
    model: Any,  # Any: torch module, imported lazily
    loaders: dict[str, Any],
    splits: dict[str, list[Sample]],
    device: Any,
    backbone: str,
) -> dict[str, Any]:
    """Train for the configured epochs; save the best checkpoint by val macro-F1."""
    import torch
    from cv_model import set_backbone_trainable, train_one_epoch

    epochs = args.epochs or config.training.epochs
    frozen = min(config.training.freeze_backbone_epochs, epochs - 1)
    amp = config.training.mixed_precision and device.type == "cuda"
    counts = class_counts(splits["train"], len(config.classes))
    weights = class_weights(counts, config.training.class_weighting)
    loss_fn = torch.nn.CrossEntropyLoss(
        weight=torch.tensor(weights, device=device),
        label_smoothing=config.training.label_smoothing,
    )
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config.training.learning_rate,
        weight_decay=config.training.weight_decay,
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    scaler = torch.amp.GradScaler(device.type, enabled=amp)
    tracker = _start_wandb(config, backbone, epochs) if args.wandb else None
    best_f1, best_epoch = -1.0, 0
    for epoch in range(1, epochs + 1):
        set_backbone_trainable(model, trainable=epoch > frozen)
        loss = train_one_epoch(
            model, loaders["train"], loss_fn, optimizer, scaler, device
        )
        scheduler.step()
        val = _evaluate_split(config, model, loaders, splits, "val", device)
        log.info(
            "epoch %d/%d loss=%.4f val_macro_f1=%.4f",
            epoch,
            epochs,
            loss,
            val["macro_f1"],
        )
        if tracker is not None:
            tracker.log(
                {
                    "epoch": epoch,
                    "train_loss": loss,
                    "val_macro_f1": val["macro_f1"],
                    "val_ece": val["ece"],
                }
            )
        if val["macro_f1"] > best_f1:
            best_f1, best_epoch = val["macro_f1"], epoch
            _save_checkpoint(
                args.output_dir / "best.pt", model, config, backbone, epoch, best_f1
            )
    if tracker is not None:
        tracker.summary["best_val_macro_f1"] = best_f1
        tracker.finish()
    return {
        "backbone": backbone,
        "pretrained": not args.no_pretrained,
        "epochs": epochs,
        "frozen_epochs": frozen,
        "best_epoch": best_epoch,
        "train_images_per_class": dict(zip(config.class_names, counts, strict=True)),
        "class_weights": [round(w, 3) for w in weights],
        "device": device.type,
    }


def _evaluate_split(
    config: TrainConfig,
    model: Any,  # Any: torch module, imported lazily
    loaders: dict[str, Any],
    splits: dict[str, list[Sample]],
    split: str,
    device: Any,
) -> dict[str, Any]:
    """Predict one split and compute its metrics."""
    from cv_model import predict

    amp = config.training.mixed_precision and device.type == "cuda"
    return evaluate(
        predict(model, loaders[split], device, amp),
        [s.label for s in splits[split]],
        [s.skin_tone for s in splits[split]],
        config.class_names,
        config.abstain_threshold,
    )


def _save_checkpoint(
    path: Path, model: Any, config: TrainConfig, backbone: str, epoch: int, f1: float
) -> None:  # Any: torch module, imported lazily
    """Save weights plus what the exporter needs to rebuild the model."""
    import torch

    torch.save(
        {
            "state_dict": model.state_dict(),
            "backbone": backbone,
            "class_names": list(config.class_names),
            "epoch": epoch,
            "val_macro_f1": f1,
            "resize_size": config.data.resize_size,
            "image_size": config.data.image_size,
            "mean": list(config.data.mean),
            "std": list(config.data.std),
        },
        path,
    )


def _start_wandb(
    config: TrainConfig, backbone: str, epochs: int
) -> Any:  # Any: wandb Run
    """Start a W&B run with the config only (never images)."""
    import wandb

    return wandb.init(
        project=config.wandb_project,
        name=f"baseline-{backbone}",
        config={**asdict(config), "backbone": backbone, "epochs": epochs},
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line.

    Args:
        argv: Arguments without the program name. ``None`` reads ``sys.argv``.

    Returns:
        ``EXIT_OK`` on success, ``EXIT_CONFIG_ERROR`` if the config is invalid.
    """
    args = parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        log.error("config_invalid: %s", exc)
        return EXIT_CONFIG_ERROR
    for line in describe_plan(config):
        log.info(line)
    if args.dry_run:
        log.info("dry_run_complete: config is valid")
        return EXIT_OK
    run_training(config, args)
    return EXIT_OK


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sys.exit(main())
