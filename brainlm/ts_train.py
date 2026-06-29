"""
Training utilities for the time-series BrainLM (v3).
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
from torch.optim import AdamW
from torch.optim.lr_scheduler import LambdaLR, OneCycleLR
from tqdm import tqdm

from .ts_model import BrainLMTimeSeries, BrainLMTimeSeriesConfig


def _make_scheduler(optimizer, max_epochs: int, train_loader_len: int, lr: float):
    total_steps = int(max_epochs) * int(train_loader_len)
    if total_steps < 10:
        return LambdaLR(optimizer, lr_lambda=lambda _: 1.0)
    try:
        return OneCycleLR(optimizer, max_lr=lr, total_steps=total_steps, pct_start=0.1)
    except ZeroDivisionError:
        return LambdaLR(optimizer, lr_lambda=lambda _: 1.0)


def train_brainlm_ts(
    train_loader,
    val_loader,
    config: BrainLMTimeSeriesConfig,
    max_epochs: int = 50,
    lr: float = 1e-4,
    patience: int = 10,
    checkpoint_dir: Optional[Path] = None,
    device: Optional[torch.device] = None,
) -> Tuple[BrainLMTimeSeries, Dict[str, List[float]]]:
    # These reduce the chance of low-level thread / BLAS issues on macOS,
    # especially when mixing numpy/sklearn + torch in one process.
    try:
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
    except Exception:
        pass

    if device is None:
        if torch.cuda.is_available():
            device = torch.device("cuda")
        elif torch.backends.mps.is_available():
            device = torch.device("mps")
        else:
            device = torch.device("cpu")

    model = BrainLMTimeSeries(config).to(device)
    optimizer = AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    scheduler = _make_scheduler(optimizer, max_epochs=max_epochs, train_loader_len=len(train_loader), lr=lr)

    history: Dict[str, List[float]] = {"train_loss": [], "val_loss": [], "lr": []}
    best_val = float("inf")
    bad = 0

    if checkpoint_dir is not None:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        torch.save({"config": asdict(config)}, checkpoint_dir / "config.pt")

    for epoch in range(int(max_epochs)):
        model.train()
        total = 0.0
        n = 0
        pbar = tqdm(train_loader, desc=f"Epoch {epoch+1}")
        for batch in pbar:
            input_x = batch["input_x"].to(device)
            labels = batch["labels"].to(device)
            attn = batch["attention_mask"].to(device)
            mask = batch["mask_labels"].to(device)

            optimizer.zero_grad(set_to_none=True)
            out = model.compute_loss(input_x=input_x, labels=labels, attention_mask=attn, mask_labels=mask)
            loss = out["loss"]
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            scheduler.step()

            total += float(loss.item())
            n += 1
            pbar.set_postfix({"loss": f"{loss.item():.4f}"})

        train_loss = total / max(n, 1)

        model.eval()
        with torch.no_grad():
            vtotal = 0.0
            vn = 0
            for batch in val_loader:
                input_x = batch["input_x"].to(device)
                labels = batch["labels"].to(device)
                attn = batch["attention_mask"].to(device)
                mask = batch["mask_labels"].to(device)
                out = model.compute_loss(input_x=input_x, labels=labels, attention_mask=attn, mask_labels=mask)
                vtotal += float(out["loss"].item())
                vn += 1
            val_loss = vtotal / max(vn, 1)

        cur_lr = scheduler.get_last_lr()[0] if hasattr(scheduler, "get_last_lr") else lr
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["lr"].append(cur_lr)

        if checkpoint_dir is not None:
            # save last
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "scheduler_state_dict": scheduler.state_dict(),
                    "history": history,
                    "best_val_loss": best_val,
                    "config": asdict(config),
                },
                checkpoint_dir / "last_model.pt",
            )

        if val_loss < best_val:
            best_val = val_loss
            bad = 0
            if checkpoint_dir is not None:
                torch.save({"model_state_dict": model.state_dict(), "config": asdict(config)}, checkpoint_dir / "best_model.pt")
        else:
            bad += 1
            if bad >= int(patience):
                break

    # restore best if available
    if checkpoint_dir is not None and (checkpoint_dir / "best_model.pt").exists():
        ckpt = torch.load(checkpoint_dir / "best_model.pt", map_location=device)
        model.load_state_dict(ckpt["model_state_dict"])

    return model, history


@torch.no_grad()
def extract_ts_latents(model: BrainLMTimeSeries, dataloader, device: torch.device):
    model.eval()
    model = model.to(device)
    zs: List[np.ndarray] = []
    cids: List[np.ndarray] = []
    subjects: List[str] = []

    for batch in tqdm(dataloader, desc="Extracting latents"):
        input_x = batch["input_x"].to(device)
        attn = batch["attention_mask"].to(device)
        out = model.forward(input_x=input_x, attention_mask=attn, mask_labels=None, return_latent=False)
        z = out["cls_representation"].detach().cpu().numpy()
        zs.append(z)
        cids.append(batch["cluster_id"].cpu().numpy())
        # subject_id is a list of strings in default collate
        if "subject_id" in batch:
            subjects.extend(list(batch["subject_id"]))

    latents = np.concatenate(zs, axis=0) if zs else np.zeros((0, model.config.d_model), dtype=np.float32)
    cluster_ids = np.concatenate(cids, axis=0) if cids else np.zeros((0,), dtype=np.int64)
    return latents, cluster_ids, subjects

