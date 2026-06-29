"""Quick z estimate using 3 train subjects (approximate)."""
import os, sys
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

class MyDataset(torch.utils.data.Dataset):
    def __init__(self, data, w=64):
        self.data, self.w = data, w
    def __len__(self):
        return len(self.data) - self.w
    def __getitem__(self, i):
        x = self.data[i:i+self.w]
        y = self.data[i+self.w:i+self.w+1]
        return x, y

def load_subject_data(sid, is_train):
    p = "train" if is_train else "test"
    return pd.read_csv(DATA_PRE / f"{p}_{sid}.csv", header=0).values.astype(np.float32)

def get_score_global(data, model, device, w=64, gamma=1, bs=16):
    model.eval()
    loader = DataLoader(MyDataset(data, w), batch_size=bs, shuffle=False)
    fs, rs = [], []
    for bx, by in loader:
        bx, by = bx.float().to(device), by.float().to(device)
        with torch.no_grad():
            _, f = model(bx)
            rx = torch.cat([bx[:, 1:, :], by], dim=1)
            r, _ = model(rx)
        fs.append(f.cpu().numpy())
        rs.append(r.cpu().numpy()[:, -1, :])
    f = np.concatenate(fs, axis=0).squeeze()
    r = np.concatenate(rs, axis=0)
    act = data[w:]
    sc = np.sqrt((f - act)**2) + gamma * np.sqrt((r - act)**2)
    return np.mean(sc, axis=1)

def main():
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    with open(SPLIT_DIR / "train_val_subjects.txt") as f:
        ids = [l.strip() for l in f if l.strip()]
    threshold = 0.34137585759162903
    w, gamma = 64, 1
    model = MTAD_GAT(n_features=load_subject_data(ids[0], True).shape[1], seq_len=w).to(device)
    model.load_state_dict(torch.load(CHECKPOINT_DIR / "global_checkpoint_iter_0.pkl", map_location=device))
    all_scores = []
    for sid in ids[:3]:
        all_scores.extend(get_score_global(load_subject_data(sid, True), model, device, w, gamma).tolist())
    all_scores = np.array(all_scores)
    mean_s, std_s = np.mean(all_scores), np.std(all_scores)
    if std_s < 1e-10:
        print("std ~ 0")
        return
    z = (threshold - mean_s) / std_s
    z_candidates = np.arange(2.5, 12, 0.5)
    best_z = z_candidates[np.argmin(np.abs(z_candidates - z))]
    print(f"Threshold_Global = {threshold:.6f}")
    print(f"Train Score_Global (3 subj approx): mean = {mean_s:.6f}, std = {std_s:.6f}")
    print(f"z (exact from formula) = (threshold - mean) / std = {z:.4f}")
    print(f"z (nearest in epsilon_threshold grid 2.5..11.5 step 0.5) = {best_z}")

if __name__ == "__main__":
    main()
