"""Torch parts of training: dataset, model, and the train/predict loops.

Responsibilities:
    - ``ImageDataset``: load each photo once with ``cv_preprocess`` (resize
      short side to 256), keep it in memory, and optionally cache it as a
      lossless PNG so the second backbone run skips decoding.
    - Train-time crop + flip; eval-time centre crop; ImageNet normalisation.
    - Build the ``timm`` backbone with a new head. Pretrained ImageNet weights
      are downloaded from the Hugging Face Hub by ``timm``.
    - One training epoch with optional mixed precision; batched prediction.

Needs torch and timm (``ml/cv/requirements.txt``); never imported in CI.
Images stay in memory or the git-ignored cache; they are never logged.

Owner: Nisarg (cv) · Task: S1-NIS-6 · Requirements: NFR-07
"""

import random
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import timm
import torch
from config_schema import TrainConfig
from cv_data import Sample
from cv_preprocess import load_rgb, resize_short_side
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset


def seed_everything(seed: int) -> None:
    """Seed Python, NumPy and torch (CPU and GPU)."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def _load_resized(sample: Sample, resize: int, cache_dir: Path | None) -> torch.Tensor:
    """Load one photo resized to ``resize`` on its short side, as uint8 CHW."""
    cached = cache_dir / f"{sample.image_id}.png" if cache_dir else None
    if cached is not None and cached.exists():
        with Image.open(cached) as opened:
            image = opened.convert("RGB")
    else:
        image = resize_short_side(load_rgb(sample.path), resize)
        if cached is not None:
            image.save(cached)  # PNG is lossless, so cached tensors are identical
    return torch.from_numpy(np.asarray(image, dtype=np.uint8).copy()).permute(2, 0, 1)


class ImageDataset(Dataset[tuple[torch.Tensor, int]]):
    """Preloaded, preprocessed images with their labels."""

    def __init__(
        self,
        samples: Sequence[Sample],
        config: TrainConfig,
        train: bool,
        cache_dir: Path | None = None,
        threads: int = 8,
    ) -> None:
        """Load every image once.

        Args:
            samples: Images of one split.
            config: Training config (sizes, mean, std).
            train: Random crop + flip if true, centre crop otherwise.
            cache_dir: Optional folder for resized PNGs (outside git).
            threads: Parallel image loads.
        """
        self.samples = list(samples)
        self.train = train
        self.crop = config.data.image_size
        self.mean = torch.tensor(config.data.mean).view(3, 1, 1)
        self.std = torch.tensor(config.data.std).view(3, 1, 1)
        if cache_dir is not None:
            cache_dir.mkdir(parents=True, exist_ok=True)
        resize = config.data.resize_size
        with ThreadPoolExecutor(max_workers=threads) as pool:
            self.images = list(
                pool.map(lambda s: _load_resized(s, resize, cache_dir), self.samples)
            )

    def __len__(self) -> int:
        """Number of images."""
        return len(self.samples)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, int]:
        """Cropped, normalised image tensor and its label."""
        image = self.images[index]
        _, height, width = image.shape
        if self.train:
            top = random.randint(0, height - self.crop)
            left = random.randint(0, width - self.crop)
        else:
            # Same rounding as cv_preprocess.center_crop.
            top = (height - self.crop) // 2
            left = (width - self.crop) // 2
        patch = image[:, top : top + self.crop, left : left + self.crop]
        if self.train and random.random() < 0.5:
            patch = patch.flip(-1)
        tensor = (patch.float() / 255.0 - self.mean) / self.std
        return tensor, self.samples[index].label


def build_model(config: TrainConfig, backbone: str, pretrained: bool) -> nn.Module:
    """Create the backbone with a new head for the config's classes.

    Pretrained weights come from the Hugging Face Hub (``timm/<backbone>``).
    """
    model: nn.Module = timm.create_model(
        backbone,
        pretrained=pretrained,
        num_classes=len(config.classes),
        drop_rate=config.model.dropout,
    )
    return model


def set_backbone_trainable(model: nn.Module, trainable: bool) -> None:
    """Freeze or unfreeze everything except the classification head."""
    for parameter in model.parameters():
        parameter.requires_grad = trainable
    head: nn.Module = model.get_classifier()
    for parameter in head.parameters():
        parameter.requires_grad = True


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader[tuple[torch.Tensor, int]],
    loss_fn: nn.Module,
    optimizer: torch.optim.Optimizer,
    scaler: torch.amp.GradScaler,
    device: torch.device,
) -> float:
    """Run one epoch; return the mean training loss."""
    model.train()
    total, count = 0.0, 0
    amp = scaler.is_enabled()
    for images, labels in loader:
        images, labels = images.to(device), labels.to(device)
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(device.type, dtype=torch.float16, enabled=amp):
            loss = loss_fn(model(images), labels)
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        total += loss.item() * len(labels)
        count += len(labels)
    return total / max(count, 1)


@torch.no_grad()
def predict(
    model: nn.Module,
    loader: DataLoader[tuple[torch.Tensor, int]],
    device: torch.device,
    amp: bool,
) -> list[list[float]]:
    """Softmax probabilities for every image, in loader order."""
    model.eval()
    probabilities: list[list[float]] = []
    for images, _ in loader:
        with torch.autocast(device.type, dtype=torch.float16, enabled=amp):
            logits = model(images.to(device))
        probabilities.extend(torch.softmax(logits.float(), dim=1).cpu().tolist())
    return probabilities
