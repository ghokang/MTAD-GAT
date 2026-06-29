"""
Compute z from saved Threshold_Global and train Score_Global distribution.
Run from MTAD-GAT directory: python compute_z.py
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from model.mtad_gat import MTAD_GAT

DATA_PRE = ROOT / "data" / "DATA" / "data_pre"
SPLIT_DIR = DATA_PRE / "split_info"
CHECKPOINT_DIR = ROOT / "checkpoint"
RESULT_DIR = ROOT / "result"

# Same as train_and_infer
class MyDataset(torch.utils.data.Dataset):
    def __init__(self, data, w=64):
        self.data = data
        self.w = w
    def __len__(self):
        return len(self.data) - self.w
    def __getitem__(self, index):
        x = self.data[index : index + self.w]
        y = self.data[index + self.w : index + self.w + 1]
        return x, y

def load_subject_data(subject_id: str, is_train: bool) -> np.ndarray:
    prefix = "train" if is_train else "test"
    fpath = DATA_PRE / f"{prefix}_{subject_id}.csv"
    df = pd.read_csv(fpath, header=0)
    return df.values.astype(np.float32)

def get_score(data, model, device, w, gamma, batch_size=16):
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
    scores = np.sqrt((forecasts - actuals) ** 2) + gamma * np.sqrt((reconstructs - actuals) ** 2)
    score_global = np.mean(scores, axis=1)
    return score_global

def main():
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    with open(SPLIT_DIR / "train_val_subjects.txt") as f:
        train_val_ids = [line.strip() for line in f if line.strip()]

    # Load threshold from saved result
    sample_result = RESULT_DIR / "111514_iter_0_testresult.csv"
    if not sample_result.exists():
        print("No result file found, using threshold = 0.34137585759162903")
        threshold = 0.34137585759162903
    else:
        df = pd.read_csv(sample_result, nrows=1)
        threshold = float(df["Threshold_Global"].iloc[0])
    print(f"Threshold_Global (epsilon) = {threshold:.6f}")

    # Load model
    w = 64
    gamma = 1
    train0 = load_subject_data(train_val_ids[0], is_train=True)
    n_features = train0.shape[1]
    model = MTAD_GAT(n_features=n_features, seq_len=w).to(device)
    ckpt = CHECKPOINT_DIR / "global_checkpoint_iter_0.pkl"
    if not ckpt.exists():
        print("Checkpoint not found. Run train_and_infer.py first.")
        return
    model.load_state_dict(torch.load(ckpt, map_location=device))

    # Collect train Score_Global for all 70 subjects (same as train_and_infer)
    all_scores = []
    for sid in train_val_ids:
        data = load_subject_data(sid, is_train=True)
        sg = get_score(data, model, device, w, gamma)
        all_scores.extend(sg.tolist())
    all_scores = np.array(all_scores)
    mean_s = np.mean(all_scores)
    std_s = np.std(all_scores)
    if std_s < 1e-10:
        print("std too small, cannot compute z")
        return
    z = (threshold - mean_s) / std_s
    print(f"Train Score_Global: mean = {mean_s:.6f}, std = {std_s:.6f}")
    print(f"z = (threshold - mean) / std = ({threshold:.6f} - {mean_s:.6f}) / {std_s:.6f} = {z:.4f}")

if __name__ == "__main__":
    main()
