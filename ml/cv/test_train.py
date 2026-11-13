"""Tests for the ``train.py`` command line and a tiny end-to-end training run.

Covers:
    - The dry run used before every Kaggle session, and the exit code for a
      bad config (no torch needed; runs in CI).
    - With torch + timm installed (skipped in CI): a 2-epoch CPU run on
      generated images writes a checkpoint, metrics and a report, and the
      dataset's eval crop matches ``cv_preprocess`` exactly.

Owner: Nisarg (cv) · Task: S0-NIS-2, S1-NIS-6 · Requirements: NFR-07
"""

import csv
import json
import logging
from pathlib import Path

import pytest
from PIL import Image
from train import (
    EXIT_CONFIG_ERROR,
    EXIT_OK,
    TRAINING_STEPS,
    describe_plan,
    main,
    parse_args,
)
from train_config import DEFAULT_CONFIG_PATH, load_config


def test_parse_args_defaults_to_baseline_config() -> None:
    args = parse_args([])

    assert args.config == DEFAULT_CONFIG_PATH
    assert args.dry_run is False
    assert args.wandb is False


def test_dry_run_validates_config_and_logs_plan(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="cv.train"):
        code = main(["--dry-run"])

    assert code == EXIT_OK
    assert "dry_run_complete: config is valid" in caplog.messages
    assert "classes (3): eczema, urticaria, unclear" in caplog.messages
    assert any(
        m.startswith("merged into unclear: fungal_infection") for m in caplog.messages
    )


def test_describe_plan_lists_every_class_and_step() -> None:
    lines = describe_plan(load_config())
    text = "\n".join(lines)

    assert all(name in text for name in load_config().class_names)
    assert sum(line.startswith("step ") for line in lines) == len(TRAINING_STEPS)


def test_invalid_config_returns_config_error_exit_code(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("version: 1\n", encoding="utf-8")

    with caplog.at_level(logging.ERROR, logger="cv.train"):
        code = main(["--config", str(bad), "--dry-run"])

    assert code == EXIT_CONFIG_ERROR
    assert any(m.startswith("config_invalid:") for m in caplog.messages)


def _tiny_dataset(root: Path) -> Path:
    """Write 4 images per label per split, each label a different colour."""
    colours = {
        "eczema": (200, 40, 40),
        "urticaria": (40, 200, 40),
        "acne": (40, 40, 200),
    }
    root.mkdir(parents=True, exist_ok=True)
    manifest = root / "clean_v1.csv"
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("split", "image_id", "source", "label", "skin_tone", "url"))
        for split in ("train", "val", "test"):
            for label, colour in colours.items():
                for i in range(4):
                    image_id = f"{split}-{label}-{i}"
                    path = root / "scin" / f"{image_id}.png"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    Image.new("RGB", (300 + 10 * i, 260), colour).save(path)
                    tone = ("light", "dark")[i % 2]
                    writer.writerow(
                        (split, image_id, "scin", label, tone, f"u/{image_id}.png")
                    )
    return manifest


def test_tiny_training_run_writes_checkpoint_metrics_and_report(tmp_path: Path) -> None:
    pytest.importorskip("torch")
    pytest.importorskip("timm")
    manifest = _tiny_dataset(tmp_path / "images")
    out = tmp_path / "run"

    code = main(
        [
            "--manifest", str(manifest),
            "--images", str(tmp_path / "images"),
            "--output-dir", str(out),
            "--cache-dir", str(tmp_path / "cache"),
            "--backbone", "mobilenetv3_large_100",
            "--epochs", "2",
            "--workers", "0",
            "--no-pretrained",
        ]
    )  # fmt: skip

    assert code == EXIT_OK
    assert (out / "best.pt").exists()
    report = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    assert set(report["metrics"]) == {"val", "test"}
    assert report["metrics"]["test"]["images"] == 12
    # acne is merged into unclear, so unclear has 4 training images.
    assert report["run"]["train_images_per_class"] == {
        "eczema": 4,
        "urticaria": 4,
        "unclear": 4,
    }
    assert (out / "report.md").read_text(encoding="utf-8").startswith("# CV baseline")
    assert len(list((tmp_path / "cache").glob("*.png"))) == 36


def test_eval_crop_matches_shared_preprocessing(tmp_path: Path) -> None:
    torch = pytest.importorskip("torch")
    from cv_data import read_splits
    from cv_model import ImageDataset
    from cv_preprocess import center_crop, load_rgb, resize_short_side

    config = load_config()
    manifest = _tiny_dataset(tmp_path / "images")
    sample = read_splits(manifest, tmp_path / "images", config)["test"][1]
    dataset = ImageDataset([sample], config, train=False)

    tensor, _ = dataset[0]
    expected = center_crop(resize_short_side(load_rgb(sample.path), 256), 224)
    pixels = torch.tensor(list(expected.getdata()), dtype=torch.float32)
    expected_tensor = pixels.view(224, 224, 3).permute(2, 0, 1) / 255.0
    mean = torch.tensor(config.data.mean).view(3, 1, 1)
    std = torch.tensor(config.data.std).view(3, 1, 1)
    assert torch.allclose(tensor, (expected_tensor - mean) / std, atol=1e-6)
