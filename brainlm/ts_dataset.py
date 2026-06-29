"""
Time-series dataset utilities for BrainLM v3 (segment-concat time series).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset


@dataclass
class FeatureNormalizer:
    """
    Per-feature standardization (mean/std) fit across all timepoints in train examples.
    """

    mean_: Optional[np.ndarray] = None  # shape (n_features,)
    std_: Optional[np.ndarray] = None   # shape (n_features,)
    eps: float = 1e-6

    def fit(self, examples: Sequence) -> "FeatureNormalizer":
        if not examples:
            raise ValueError("Cannot fit normalizer on empty examples")
        xs = [np.asarray(ex.x, dtype=np.float32) for ex in examples]
        x_all = np.concatenate(xs, axis=0)  # (sum_T, F)
        self.mean_ = x_all.mean(axis=0)
        self.std_ = x_all.std(axis=0)
        self.std_ = np.maximum(self.std_, self.eps)
        return self

    def transform(self, x: np.ndarray) -> np.ndarray:
        if self.mean_ is None or self.std_ is None:
            raise ValueError("Normalizer is not fit yet")
        x = np.asarray(x, dtype=np.float32)
        return (x - self.mean_) / self.std_


class TSConcatDataset(Dataset):
    """
    Dataset of variable-length time series, padded/truncated to max_time_steps.

    Each item returns:
      - input_x: masked input (T, F)
      - labels: original normalized x (T, F)
      - attention_mask: 1 for valid time steps (T,)
      - mask_labels: 1 for masked time steps (T,)
      - cluster_id: int
    """

    def __init__(
        self,
        examples: Sequence,
        max_time_steps: int,
        mask_ratio: float = 0.15,
        normalizer: Optional[FeatureNormalizer] = None,
        augment: bool = False,
        seed: int = 0,
    ):
        self.examples = list(examples)
        self.max_time_steps = int(max_time_steps)
        self.mask_ratio = float(mask_ratio)
        self.normalizer = normalizer
        self.augment = bool(augment)
        self.rng = np.random.default_rng(int(seed))

        if self.max_time_steps <= 0:
            raise ValueError("max_time_steps must be positive")

    def __len__(self) -> int:
        return len(self.examples)

    def _pad_truncate(self, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Returns (x_fixed, attn_mask) with shape (T_max, F) and (T_max,).
        """
        x = np.asarray(x, dtype=np.float32)
        T, F = x.shape
        Tm = self.max_time_steps
        if T >= Tm:
            x_fixed = x[:Tm]
            mask = np.ones(Tm, dtype=np.float32)
        else:
            pad = np.zeros((Tm - T, F), dtype=np.float32)
            x_fixed = np.concatenate([x, pad], axis=0)
            mask = np.zeros(Tm, dtype=np.float32)
            mask[:T] = 1.0
        return x_fixed, mask

    def __getitem__(self, idx: int):
        ex = self.examples[idx]
        x = np.asarray(ex.x, dtype=np.float32)

        if self.normalizer is not None:
            x = self.normalizer.transform(x)

        x_fixed, attn = self._pad_truncate(x)
        labels = x_fixed.copy()

        # Build time-step mask. Only mask valid (non-padding) positions.
        valid_idx = np.where(attn > 0.5)[0]
        mask_labels = np.zeros((self.max_time_steps,), dtype=np.float32)
        input_x = x_fixed.copy()

        if len(valid_idx) > 0 and self.mask_ratio > 0:
            n_mask = max(1, int(round(len(valid_idx) * self.mask_ratio)))
            chosen = self.rng.choice(valid_idx, size=min(n_mask, len(valid_idx)), replace=False)
            mask_labels[chosen] = 1.0
            # Replace masked steps with noise (like MAE-style corruption)
            noise = self.rng.standard_normal(size=(len(chosen), x_fixed.shape[1])).astype(np.float32) * 0.1
            input_x[chosen] = noise

        if self.augment and len(valid_idx) > 0:
            # light Gaussian noise on all valid steps
            if self.rng.random() < 0.3:
                input_x[valid_idx] = input_x[valid_idx] + (
                    self.rng.standard_normal(size=(len(valid_idx), x_fixed.shape[1])).astype(np.float32) * 0.01
                )

        return {
            "input_x": torch.from_numpy(input_x).float(),              # (T, F)
            "labels": torch.from_numpy(labels).float(),               # (T, F)
            "attention_mask": torch.from_numpy(attn).float(),         # (T,)
            "mask_labels": torch.from_numpy(mask_labels).float(),     # (T,)
            "cluster_id": torch.tensor(int(ex.cluster_id), dtype=torch.long),
            "subject_id": str(ex.subject_id),
        }


def create_ts_dataloaders(
    train_ex: Sequence,
    val_ex: Sequence,
    test_ex: Sequence,
    max_time_steps: int,
    batch_size: int = 8,
    mask_ratio: float = 0.15,
    normalizer: Optional[FeatureNormalizer] = None,
    num_workers: int = 0,
) -> Tuple[DataLoader, DataLoader, DataLoader]:
    train_ds = TSConcatDataset(
        train_ex,
        max_time_steps=max_time_steps,
        mask_ratio=mask_ratio,
        normalizer=normalizer,
        augment=True,
        seed=0,
    )
    val_ds = TSConcatDataset(
        val_ex,
        max_time_steps=max_time_steps,
        mask_ratio=mask_ratio,
        normalizer=normalizer,
        augment=False,
        seed=1,
    )
    test_ds = TSConcatDataset(
        test_ex,
        max_time_steps=max_time_steps,
        mask_ratio=mask_ratio,
        normalizer=normalizer,
        augment=False,
        seed=2,
    )

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)
    return train_loader, val_loader, test_loader

