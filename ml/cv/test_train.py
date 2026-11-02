"""Tests for the ``train.py`` command line (skeleton).

Covers the dry run used before every Kaggle session, the exit code for a bad
config, and the guard that stops a real run until S1-NIS-6 adds training.

Owner: Nisarg (cv) · Task: S0-NIS-2 · Requirements: NFR-07
"""

import logging
from pathlib import Path

import pytest
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


def test_dry_run_validates_config_and_logs_plan(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="cv.train"):
        code = main(["--dry-run"])

    assert code == EXIT_OK
    assert "dry_run_complete: config is valid" in caplog.messages
    assert any(m.startswith("classes (8): eczema") for m in caplog.messages)


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


def test_real_run_is_blocked_until_training_exists() -> None:
    with pytest.raises(NotImplementedError, match="S1-NIS-6"):
        main([])
