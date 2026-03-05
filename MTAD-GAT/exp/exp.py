"""
Experiment class for MTAD-GAT on fMRI time series.

Key differences from the original SMD-based Exp:
  - Accepts pre-split numpy arrays (train_x, valid_x, test_x) directly.
  - No ground-truth anomaly labels required.
  - Global threshold is determined by epsilon_threshold (unsupervised).
  - Per-feature threshold falls back to pot_threshold if SPOT converges,
    otherwise also uses epsilon_threshold.
"""

import os

import numpy as np
import pandas as pd
import torch
from torch import optim
from torch.utils.data import DataLoader
from tqdm import tqdm

from data.dataset import MyDataset
from model.loss import JointLoss
from model.mtad_gat import MTAD_GAT
from utils.earlystop import EarlyStop
from utils.evalmethods import pot_threshold, epsilon_threshold
from utils.plot import plot_loss


class Exp:
    def __init__(
        self,
        iter: int,
        name: str,
        epochs: int,
        batch_size: int,
        patience: int,
        lr: float,
        train_x: np.ndarray,
        valid_x: np.ndarray,
        test_x: np.ndarray,
        w: int = 64,
        gamma: float = 1.0,
        checkpoint_dir: str = "./checkpoint",
        result_dir: str = "./result",
        img_dir: str = "./img",
    ):
        """
        Args:
            iter        : run index (for reproducibility / multiple runs)
            name        : subject ID string used for file naming
            epochs      : maximum training epochs
            batch_size  : mini-batch size
            patience    : early-stopping patience
            lr          : Adam learning rate
            train_x     : z-score normalised train split  (T_train, n_features)
            valid_x     : z-score normalised valid split  (T_valid, n_features)
            test_x      : z-score normalised test split   (T_test,  n_features)
            w           : sliding-window length
            gamma       : reconstruction-score weight  (score = for_err + gamma * rec_err)
            checkpoint_dir / result_dir / img_dir : output directories
        """
        self.iter = iter
        self.name = name
        self.epochs = epochs
        self.batch_size = batch_size
        self.patience = patience
        self.w = w
        self.gamma = gamma
        self.lr = lr

        self.train_x = train_x
        self.valid_x = valid_x
        self.test_x = test_x

        # ── device ──────────────────────────────────────────────────────────
        if torch.cuda.is_available():
            self.device = torch.device("cuda")
        elif torch.backends.mps.is_available():
            self.device = torch.device("mps")
        else:
            self.device = torch.device("cpu")

        # ── output dirs ─────────────────────────────────────────────────────
        for d in (checkpoint_dir, result_dir, img_dir):
            os.makedirs(d, exist_ok=True)

        self.checkpoint_path = os.path.join(
            checkpoint_dir, f"{self.name}_checkpoint_iter__{self.iter},pkl"
        )
        self.result_dir = result_dir
        self.img_dir = img_dir

        # ── data loaders & model ────────────────────────────────────────────
        self._build_loaders()
        self._build_model()

    # ────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ────────────────────────────────────────────────────────────────────────

    def _build_loaders(self):
        n_features = self.train_x.shape[1]

        trainset = MyDataset(self.train_x, w=self.w)
        validset = MyDataset(self.valid_x, w=self.w)
        testset  = MyDataset(self.test_x,  w=self.w)

        self.trainloader = DataLoader(trainset, batch_size=self.batch_size, shuffle=True,  drop_last=False)
        self.validloader = DataLoader(validset, batch_size=self.batch_size, shuffle=False, drop_last=False)
        self.testloader  = DataLoader(testset,  batch_size=self.batch_size, shuffle=False, drop_last=False)

        print(
            f"[{self.name}]  train={len(trainset)}  valid={len(validset)}  test={len(testset)}"
            f"  features={n_features}  window={self.w}"
        )

    def _build_model(self):
        n_features = self.train_x.shape[1]
        self.model      = MTAD_GAT(n_features=n_features, seq_len=self.w).to(self.device)
        self.criterion  = JointLoss()
        self.optimizer  = optim.Adam(self.model.parameters(), lr=self.lr, weight_decay=1e-4)
        self.earlystop  = EarlyStop(patience=self.patience)

    def _process_batch(self, batch_x, batch_y):
        batch_x = batch_x.float().to(self.device)
        batch_y = batch_y.float().to(self.device)
        reconstruct, forecast = self.model(batch_x)
        f_loss, r_loss, loss  = self.criterion(batch_x, batch_y, reconstruct, forecast)
        return f_loss, r_loss, loss

    def _epoch_loss(self, loader):
        """Compute RMSE of forecast / reconstruct / total loss over a loader (no grad)."""
        f_list, r_list, t_list = [], [], []
        for batch_x, batch_y in loader:
            fl, rl, tl = self._process_batch(batch_x, batch_y)
            f_list.append(fl.item())
            r_list.append(rl.item())
            t_list.append(tl.item())
        f = float(np.sqrt(np.mean(np.array(f_list) ** 2)))
        r = float(np.sqrt(np.mean(np.array(r_list) ** 2)))
        t = float(np.sqrt(np.mean(np.array(t_list) ** 2)))
        return f, r, t

    # ────────────────────────────────────────────────────────────────────────
    # Training
    # ────────────────────────────────────────────────────────────────────────

    def fit(self):
        """Train MTAD-GAT with early stopping."""
        history = {
            "train": {"forecast": [], "reconstruct": [], "total": []},
            "valid": {"forecast": [], "reconstruct": [], "total": []},
        }

        # initial loss (before any training step)
        self.model.eval()
        with torch.no_grad():
            tfl, trl, ttl = self._epoch_loss(self.trainloader)
            vfl, vrl, vtl = self._epoch_loss(self.validloader)
        print(
            f"[{self.name}] Init  | total: train={ttl:.4f} val={vtl:.4f}"
            f"  | for: {tfl:.4f}/{vfl:.4f}  | rec: {trl:.4f}/{vrl:.4f}"
        )

        for epoch in range(1, self.epochs + 1):
            # ── train ────────────────────────────────────────────────────
            self.model.train()
            f_losses, r_losses, t_losses = [], [], []
            for batch_x, batch_y in tqdm(self.trainloader, desc=f"  Epoch {epoch}", leave=False):
                self.optimizer.zero_grad()
                fl, rl, loss = self._process_batch(batch_x, batch_y)
                loss.backward()
                self.optimizer.step()
                f_losses.append(fl.item())
                r_losses.append(rl.item())
                t_losses.append(loss.item())

            tfl = float(np.sqrt(np.mean(np.array(f_losses) ** 2)))
            trl = float(np.sqrt(np.mean(np.array(r_losses) ** 2)))
            ttl = float(np.sqrt(np.mean(np.array(t_losses) ** 2)))

            # ── validation ───────────────────────────────────────────────
            self.model.eval()
            with torch.no_grad():
                vfl, vrl, vtl = self._epoch_loss(self.validloader)

            history["train"]["forecast"].append(tfl)
            history["train"]["reconstruct"].append(trl)
            history["train"]["total"].append(ttl)
            history["valid"]["forecast"].append(vfl)
            history["valid"]["reconstruct"].append(vrl)
            history["valid"]["total"].append(vtl)

            print(
                f"[{self.name}] Epoch {epoch:03d}  | total: train={ttl:.4f} val={vtl:.4f}"
                f"  | for: {tfl:.4f}/{vfl:.4f}  | rec: {trl:.4f}/{vrl:.4f}"
            )

            self.earlystop(vtl, self.model, self.checkpoint_path)
            if self.earlystop.early_stop:
                print(f"[{self.name}] Early stopping at epoch {epoch}.")
                break

        # reload best weights
        self.model.load_state_dict(torch.load(self.checkpoint_path))

        # save loss curves
        prefix = os.path.join(self.img_dir, f"{self.name}_iter{self.iter}")
        plot_loss(
            history["train"]["forecast"], history["train"]["reconstruct"], history["train"]["total"],
            prefix + "_trainloss.png",
        )
        plot_loss(
            history["valid"]["forecast"], history["valid"]["reconstruct"], history["valid"]["total"],
            prefix + "_validloss.png",
        )

    # ────────────────────────────────────────────────────────────────────────
    # Inference & anomaly scoring
    # ────────────────────────────────────────────────────────────────────────

    def _get_scores(self, data: np.ndarray, loader: DataLoader) -> pd.DataFrame:
        """
        Run model inference and compute per-feature + global anomaly scores.

        Score_i      = |forecast_i - actual_i| + gamma * |reconstruct_i - actual_i|
        Score_Global = mean(Score_i  for all i)
        """
        self.model.eval()
        forecasts, reconstructs = [], []

        with torch.no_grad():
            for batch_x, batch_y in tqdm(loader, desc="  scoring", leave=False):
                batch_x = batch_x.float().to(self.device)
                batch_y = batch_y.float().to(self.device)

                # forecast: model sees x[0..w-1], predicts x[w]
                _, forecast = self.model(batch_x)
                forecasts.append(forecast.cpu().numpy())

                # reconstruction: shift window right by 1, get reconstruction of last step
                recon_x = torch.cat([batch_x[:, 1:, :], batch_y], dim=1)
                reconstruct, _ = self.model(recon_x)
                reconstructs.append(reconstruct.cpu().numpy()[:, -1, :])

        forecasts    = np.concatenate(forecasts,    axis=0).squeeze(axis=1)  # (N, n_features)
        reconstructs = np.concatenate(reconstructs, axis=0)                  # (N, n_features)
        actuals      = data[self.w:]                                          # (N, n_features)

        n_features = actuals.shape[1]
        df = pd.DataFrame()
        per_feature_scores = np.zeros_like(actuals)

        for i in range(n_features):
            for_err = np.sqrt((forecasts[:, i]    - actuals[:, i]) ** 2)
            rec_err = np.sqrt((reconstructs[:, i] - actuals[:, i]) ** 2)
            score   = for_err + self.gamma * rec_err

            df[f"For_{i}"]   = forecasts[:, i]
            df[f"Rec_{i}"]   = reconstructs[:, i]
            df[f"Act_{i}"]   = actuals[:, i]
            df[f"Score_{i}"] = score
            per_feature_scores[:, i] = score

        df["Score_Global"] = per_feature_scores.mean(axis=1)
        return df

    # ────────────────────────────────────────────────────────────────────────

    def predict(self, model_load: bool = False):
        """
        Compute anomaly scores and apply unsupervised thresholding.

        Threshold strategy (no ground-truth labels):
          - Per-feature : pot_threshold  (SPOT, uses train+test score distribution)
          - Global      : epsilon_threshold  (fitted on train score only)

        Outputs:
          {result_dir}/{name}_iter_{iter}_trainresult.csv
          {result_dir}/{name}_iter_{iter}_testresult.csv

        Returns:
          (trainresult DataFrame, testresult DataFrame, test_score array)
        """
        if model_load:
            self.model.load_state_dict(torch.load(self.checkpoint_path))

        # reference distribution = train + validation (what the model was trained on)
        train_valid_x = np.vstack([self.train_x, self.valid_x])
        tv_dataset    = MyDataset(train_valid_x, w=self.w)
        tv_loader     = DataLoader(tv_dataset, batch_size=self.batch_size, shuffle=False)

        trainresult = self._get_scores(train_valid_x, tv_loader)
        testresult  = self._get_scores(self.test_x, self.testloader)

        n_features = self.train_x.shape[1]

        # ── per-feature threshold (POT, no labels needed) ────────────────
        for i in range(n_features):
            tr_score = trainresult[f"Score_{i}"].values
            te_score = testresult[f"Score_{i}"].values
            try:
                thr = pot_threshold(tr_score, te_score)
            except Exception:
                thr = epsilon_threshold(tr_score)

            trainresult[f"Pred_{i}"]      = (tr_score > thr).astype(np.int64)
            trainresult[f"Threshold_{i}"] = thr
            testresult[f"Pred_{i}"]       = (te_score > thr).astype(np.int64)
            testresult[f"Threshold_{i}"]  = thr

        # ── global threshold (epsilon, fitted on train-only score) ───────
        tr_global  = trainresult["Score_Global"].values
        te_global  = testresult["Score_Global"].values
        thr_global = epsilon_threshold(tr_global)

        trainresult["Pred_Global"]      = (tr_global > thr_global).astype(np.int64)
        trainresult["Threshold_Global"] = thr_global
        testresult["Pred_Global"]       = (te_global > thr_global).astype(np.int64)
        testresult["Threshold_Global"]  = thr_global

        # ── save ─────────────────────────────────────────────────────────
        base = os.path.join(self.result_dir, f"{self.name}_iter_{self.iter}")
        trainresult.to_csv(base + "_trainresult.csv", index=False)
        testresult.to_csv(base  + "_testresult.csv",  index=False)

        n_anomaly = int(testresult["Pred_Global"].sum())
        pct       = 100.0 * n_anomaly / max(len(testresult), 1)
        print(
            f"[{self.name}] threshold={thr_global:.6f}  "
            f"anomaly_points={n_anomaly}/{len(testresult)} ({pct:.1f}%)"
        )

        return trainresult, testresult, te_global
