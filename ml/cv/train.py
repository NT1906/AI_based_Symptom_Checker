"""Training entry point for the skin-image model (skeleton).

Responsibilities:
    - Parse the command line and load a validated config (``train_config``).
    - ``--dry-run`` checks the config and prints the plan without touching a
      GPU or the training dependencies, so it also runs in CI.
    - Lay out the training steps that S1-NIS-6 fills in, in order.

Run it on Kaggle/Colab from the repository root:
    python ml/cv/train.py --config ml/cv/configs/baseline.yaml
    python ml/cv/train.py --dry-run

Owner: Nisarg (cv) · Task: S0-NIS-2 · Requirements: NFR-07
"""

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from config_readers import ConfigError
from config_schema import TrainConfig
from train_config import DEFAULT_CONFIG_PATH, load_config

log = logging.getLogger("cv.train")

EXIT_OK = 0
EXIT_CONFIG_ERROR = 2

# The steps S1-NIS-6 implements, in order (docs/cv-plan.md §5).
TRAINING_STEPS = (
    "seed every random generator from config.seed",
    "load the frozen split manifest from S1-NIS-5",
    "build train/val loaders with the shared preprocessing",
    "create the timm backbone with a new classification head",
    "train the head with the backbone frozen",
    "fine-tune the whole network with AdamW and a cosine schedule",
    "log metrics and config to W&B (never images)",
    "save the best checkpoint by validation macro-F1 outside git",
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Arguments without the program name. ``None`` reads ``sys.argv``.

    Returns:
        Namespace with ``config`` (Path) and ``dry_run`` (bool).
    """
    parser = argparse.ArgumentParser(description="Train the skin-image model.")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="YAML config (default: ml/cv/configs/baseline.yaml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate the config and print the plan, then exit",
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
    lines = [
        f"backbone: {config.model.backbone} (pretrained={config.model.pretrained})",
        f"classes ({len(config.classes)}): {', '.join(config.class_names)}",
        f"data: {', '.join(config.data.sources)} at {config.data.image_size}px",
        f"epochs: {training.epochs} ({training.freeze_backbone_epochs} frozen)",
    ]
    lines.extend(f"step {i}: {step}" for i, step in enumerate(TRAINING_STEPS, 1))
    return lines


def run_training(config: TrainConfig) -> None:
    """Train the model described by ``config``.

    Args:
        config: A validated config.

    Raises:
        NotImplementedError: Always, until S1-NIS-6 adds the training loop.
    """
    # TODO(#29): implement TRAINING_STEPS (S1-NIS-6, baseline CV model).
    raise NotImplementedError(
        "Training is added in S1-NIS-6 (#29). Use --dry-run to check a config."
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line.

    Args:
        argv: Arguments without the program name. ``None`` reads ``sys.argv``.

    Returns:
        ``EXIT_OK`` on success, ``EXIT_CONFIG_ERROR`` if the config is invalid.

    Raises:
        NotImplementedError: Without ``--dry-run``, until S1-NIS-6.
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
    run_training(config)
    return EXIT_OK


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sys.exit(main())
