"""
Train MTAD-GAT on 70 subjects, infer on 27 test subjects.
Run from MTAD-GAT directory.
"""
import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import optim
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

warnings.filterwarnings("ignore")

# Add project root
ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from model.loss import JointLoss
from model.mtad_gat import MTAD_GAT
from utils.earlystop import EarlyStop
from utils.evalmethods import epsilon_threshold, pot_threshold
from utils.plot import plot_loss

# Paths
DATA_PRE = ROOT / "data" / "DATA" / "data_pre"
SPLIT_DIR = DATA_PRE / "split_info"
CHECKPOINT_DIR = ROOT / "checkpoint"
RESULT_DIR = ROOT / "result"
IMG_DIR = ROOT / "img"
CHECKPOINT_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)
IMG_DIR.mkdir(exist_ok=True)


class MyDataset(Dataset):
    """Single-subject window dataset (for inference)."""

    def __init__(self, data: np.ndarray, w: int = 64):
        self.data = data
        self.w = w

    def __getitem__(self, index):
        x = self.data[index : index + self.w]
        y = self.data[index + self.w : index + self.w + 1]
        return x, y

    def __len__(self):
        return len(self.data) - self.w


class PerSubjectWindowDataset(Dataset):
    """Generate windows per subject, then concatenate. No cross-subject windows."""

    def __init__(self, subject_arrays, w: int = 64):
        self.subject_arrays = [arr.astype(np.float32) for arr in subject_arrays]
        self.w = w
        # cumulative window count: [0, n0, n0+n1, n0+n1+n2, ...]
        window_counts = [max(0, len(s) - w) for s in self.subject_arrays]
        self.cumulative = np.cumsum([0] + window_counts)

    def __len__(self):
        return self.cumulative[-1]

    def __getitem__(self, idx):
        subj_idx = np.searchsorted(self.cumulative[1:], idx, side="right")
        local_idx = idx - self.cumulative[subj_idx]
        data = self.subject_arrays[subj_idx]
        x = data[local_idx : local_idx + self.w]
        y = data[local_idx + self.w : local_idx + self.w + 1]
        return x, y


def load_subject_data(subject_id: str, is_train: bool) -> np.ndarray:
    prefix = "train" if is_train else "test"
    fpath = DATA_PRE / f"{prefix}_{subject_id}.csv"
    df = pd.read_csv(fpath, header=0)
    return df.values.astype(np.float32)


def main():
    # Device
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Device: {device}")

    # Load split
    with open(SPLIT_DIR / "train_val_subjects.txt") as f:
        train_val_ids = [line.strip() for line in f if line.strip()]
    with open(SPLIT_DIR / "test_subjects.txt") as f:
        test_ids = [line.strip() for line in f if line.strip()]

    # Split train/valid: 56 train, 14 valid
    np.random.seed(42)
    perm = np.random.permutation(len(train_val_ids))
    train_ids = [train_val_ids[i] for i in perm[:56]]
    valid_ids = [train_val_ids[i] for i in perm[56:]]

    # Load data per subject (window generation is done per subject, then concatenated)
    train_blocks = [load_subject_data(sid, is_train=True) for sid in train_ids]
    valid_blocks = [load_subject_data(sid, is_train=True) for sid in valid_ids]

    w = 64
    trainset = PerSubjectWindowDataset(train_blocks, w=w)
    validset = PerSubjectWindowDataset(valid_blocks, w=w)
    print(f"Train: {len(trainset)} windows ({len(train_ids)} subjects), Valid: {len(validset)} windows ({len(valid_ids)} subjects)")

    # DataLoader
    batch_size = 16
    trainloader = DataLoader(trainset, batch_size=batch_size, shuffle=True)
    validloader = DataLoader(validset, batch_size=batch_size, shuffle=False)

    # Model
    n_features = train_blocks[0].shape[1]
    model = MTAD_GAT(n_features=n_features, seq_len=w).to(device)
    criterion = JointLoss()
    optimizer = optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
    earlystopping = EarlyStop(patience=3)
    check_point = CHECKPOINT_DIR / "global_checkpoint_iter_0.pkl"

    gamma = 1
    epochs = 20
    loss_history = {"train": {"forecast": [], "reconstruct": [], "total": []},
                    "valid": {"forecast": [], "reconstruct": [], "total": []}}

    # Train
    for e in range(epochs):
        model.train()
        tl_f, tl_r, tl = [], [], []
        for batch_x, batch_y in tqdm(trainloader, desc=f"Epoch {e+1}"):
            batch_x = batch_x.float().to(device)
            batch_y = batch_y.float().to(device)
            optimizer.zero_grad()
            reconstruct, forecast = model(batch_x)
            f_loss, r_loss, loss = criterion(batch_x, batch_y, reconstruct, forecast)
            loss.backward()
            optimizer.step()
            tl_f.append(f_loss.item())
            tl_r.append(r_loss.item())
            tl.append(loss.item())

        model.eval()
        vl_f, vl_r, vl = [], [], []
        for batch_x, batch_y in validloader:
            batch_x = batch_x.float().to(device)
            batch_y = batch_y.float().to(device)
            reconstruct, forecast = model(batch_x)
            f_loss, r_loss, loss = criterion(batch_x, batch_y, reconstruct, forecast)
            vl_f.append(f_loss.item())
            vl_r.append(r_loss.item())
            vl.append(loss.item())

        tl_f = np.sqrt(np.mean(np.array(tl_f) ** 2))
        tl_r = np.sqrt(np.mean(np.array(tl_r) ** 2))
        tl = np.sqrt(np.mean(np.array(tl) ** 2))
        vl_f = np.sqrt(np.mean(np.array(vl_f) ** 2))
        vl_r = np.sqrt(np.mean(np.array(vl_r) ** 2))
        vl = np.sqrt(np.mean(np.array(vl) ** 2))

        loss_history["train"]["forecast"].append(tl_f)
        loss_history["train"]["reconstruct"].append(tl_r)
        loss_history["train"]["total"].append(tl)
        loss_history["valid"]["forecast"].append(vl_f)
        loss_history["valid"]["reconstruct"].append(vl_r)
        loss_history["valid"]["total"].append(vl)

        print(f"Epoch {e+1} | Train Loss: {tl:.6f} | Valid Loss: {vl:.6f}")
        earlystopping(vl, model, str(check_point))
        if earlystopping.early_stop:
            print("Early stopping")
            break

    model.load_state_dict(torch.load(check_point))
    plot_loss(loss_history["train"]["forecast"], loss_history["train"]["reconstruct"],
              loss_history["train"]["total"], str(IMG_DIR / "global_trainloss.png"))
    plot_loss(loss_history["valid"]["forecast"], loss_history["valid"]["reconstruct"],
              loss_history["valid"]["total"], str(IMG_DIR / "global_validloss.png"))

    # Inference helper
    def get_score(data: np.ndarray, model, device, w, gamma):
        model.eval()
        loader = DataLoader(MyDataset(data, w=w), batch_size=batch_size, shuffle=False)
        forecasts, reconstructs = [], []
        for batch_x, batch_y in loader:
            batch_x = batch_x.float().to(device)
            batch_y = batch_y.float().to(device)
            with torch.no_grad():
                _, forecast = model(batch_x)
                recon_x = torch.cat((batch_x[:, 1:, :], batch_y), dim=1)
                reconstruct, _ = model(recon_x)
            forecasts.append(forecast.cpu().numpy())
            reconstructs.append(reconstruct.cpu().numpy()[:, -1, :])
        forecasts = np.concatenate(forecasts, axis=0).squeeze()
        reconstructs = np.concatenate(reconstructs, axis=0)
        actuals = data[w:]
        df = pd.DataFrame()
        scores = np.zeros_like(actuals)
        for i in range(actuals.shape[1]):
            df[f"For_{i}"] = forecasts[:, i]
            df[f"Rec_{i}"] = reconstructs[:, i]
            df[f"Act_{i}"] = actuals[:, i]
            score = np.sqrt((forecasts[:, i] - actuals[:, i]) ** 2) + gamma * np.sqrt(
                (reconstructs[:, i] - actuals[:, i]) ** 2
            )
            scores[:, i] = score
            df[f"Score_{i}"] = score
        df["Score_Global"] = np.mean(scores, axis=1)
        return df

    # Collect train scores from all 70 train subjects for threshold
    all_train_scores_global = []
    all_train_scores_per_feature = {i: [] for i in range(n_features)}
    for sid in tqdm(train_val_ids, desc="Train scores"):
        data = load_subject_data(sid, is_train=True)
        df = get_score(data, model, device, w, gamma)
        all_train_scores_global.extend(df["Score_Global"].values)
        for i in range(n_features):
            all_train_scores_per_feature[i].extend(df[f"Score_{i}"].values)
    all_train_scores_global = np.array(all_train_scores_global)
    train_scores_per_feature = {i: np.array(all_train_scores_per_feature[i]) for i in range(n_features)}
    threshold_global = epsilon_threshold(all_train_scores_global)
    print(f"Threshold_Global: {threshold_global:.6f}")

    # Infer on 27 test subjects and save
    for sid in tqdm(test_ids, desc="Test inference"):
        data = load_subject_data(sid, is_train=False)
        df = get_score(data, model, device, w, gamma)
        for i in range(n_features):
            try:
                th = pot_threshold(train_scores_per_feature[i], df[f"Score_{i}"].values)
            except ValueError:
                th = epsilon_threshold(train_scores_per_feature[i])
            df[f"Pred_{i}"] = (df[f"Score_{i}"].values > th).astype(np.int64)
            df[f"Threshold_{i}"] = th
        df["Pred_Global"] = (df["Score_Global"].values > threshold_global).astype(np.int64)
        df["Threshold_Global"] = threshold_global
        df.to_csv(RESULT_DIR / f"{sid}_iter_0_testresult.csv", index=False)

    print(f"Saved {len(test_ids)} test result files to {RESULT_DIR}")


if __name__ == "__main__":
    main()
