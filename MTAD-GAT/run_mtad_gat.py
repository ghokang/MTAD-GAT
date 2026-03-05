"""
run_mtad_gat.py
===============
Run MTAD-GAT anomaly detection on all fMRI subjects.

Pipeline per subject
--------------------
1. Load raw CSV  (T x n_features, no header)
2. Split chronologically : 70% train | 15% val | 15% test
3. Z-score normalise      (fit on train, apply to val/test)
4. Train MTAD-GAT         (early stopping on validation loss)
5. Score                  (forecast + reconstruction error)
6. Threshold              (epsilon / POT — fully unsupervised)
7. Save results           →  result/{subject_id}_iter_0_[train|test]result.csv

Usage
-----
    cd MTAD-GAT
    python run_mtad_gat.py                        # all subjects
    python run_mtad_gat.py --subjects 100206 101309   # specific subjects
    python run_mtad_gat.py --skip_existing            # skip already-computed results
    python run_mtad_gat.py --epochs 30 --lr 0.001
"""

import argparse
import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

# ── allow imports from project root ─────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from exp.exp import Exp

warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────────────────────────────────────
# Data helpers
# ─────────────────────────────────────────────────────────────────────────────

def load_subject(csv_path: Path) -> np.ndarray:
    """
    Load a subject CSV file.

    Expected format: T rows x n_features columns, no header row.
    Returns float32 array of shape (T, n_features).
    """
    df = pd.read_csv(csv_path, header=None)
    X  = df.values.astype(np.float32)
    # guard against NaN / Inf (rare but possible after preprocessing)
    if not np.isfinite(X).all():
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    return X


def split_and_normalise(
    X: np.ndarray,
    train_ratio: float = 0.70,
    val_ratio:   float = 0.15,
) -> tuple:
    """
    Chronological split + z-score normalisation.

    Normalisation is fitted on train only and applied to val/test.
    Returns (train_x, valid_x, test_x).
    """
    T = len(X)
    train_end = int(T * train_ratio)
    val_end   = int(T * (train_ratio + val_ratio))

    train_x = X[:train_end].copy()
    valid_x = X[train_end:val_end].copy()
    test_x  = X[val_end:].copy()

    # z-score: fit on train
    mu    = train_x.mean(axis=0)
    sigma = train_x.std(axis=0) + 1e-8

    train_x = (train_x - mu) / sigma
    valid_x = (valid_x - mu) / sigma
    test_x  = (test_x  - mu) / sigma

    return train_x, valid_x, test_x


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="MTAD-GAT fMRI anomaly detection")

    p.add_argument("--data_dir",      type=str, default="data/DATA",
                   help="Directory containing per-subject CSV files")
    p.add_argument("--result_dir",    type=str, default="result",
                   help="Output directory for result CSVs")
    p.add_argument("--checkpoint_dir",type=str, default="checkpoint",
                   help="Output directory for model checkpoints")
    p.add_argument("--img_dir",       type=str, default="img",
                   help="Output directory for loss-curve images")

    p.add_argument("--subjects",      nargs="*", default=None,
                   help="Specific subject IDs to process (default: all)")
    p.add_argument("--skip_existing", action="store_true",
                   help="Skip subjects whose test result file already exists")

    # training hyper-parameters
    p.add_argument("--epochs",     type=int,   default=50)
    p.add_argument("--batch_size", type=int,   default=16)
    p.add_argument("--patience",   type=int,   default=5,
                   help="Early-stopping patience (epochs)")
    p.add_argument("--lr",         type=float, default=1e-3)
    p.add_argument("--window",     type=int,   default=64,
                   help="Sliding-window length (seq_len for MTAD-GAT)")
    p.add_argument("--gamma",      type=float, default=1.0,
                   help="Weight on reconstruction error in anomaly score")

    p.add_argument("--iter",       type=int,   default=0,
                   help="Run index appended to output file names")

    # data split
    p.add_argument("--train_ratio", type=float, default=0.70)
    p.add_argument("--val_ratio",   type=float, default=0.15)

    return p.parse_args()


def run_subject(subject_id: str, csv_path: Path, args) -> bool:
    """Train + predict for a single subject. Returns True on success."""
    print(f"\n{'=' * 60}")
    print(f"Subject: {subject_id}")
    print(f"{'=' * 60}")

    # ── load & split ─────────────────────────────────────────────────────
    X = load_subject(csv_path)
    print(f"  Raw data: {X.shape}  (T={X.shape[0]}, features={X.shape[1]})")

    train_x, valid_x, test_x = split_and_normalise(
        X,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
    )

    # sanity check: windows must fit
    min_len = args.window + 1
    if min(len(train_x), len(valid_x), len(test_x)) < min_len:
        print(f"  [SKIP] split too short for window={args.window}")
        return False

    # ── train ────────────────────────────────────────────────────────────
    exp = Exp(
        iter          = args.iter,
        name          = subject_id,
        epochs        = args.epochs,
        batch_size    = args.batch_size,
        patience      = args.patience,
        lr            = args.lr,
        train_x       = train_x,
        valid_x       = valid_x,
        test_x        = test_x,
        w             = args.window,
        gamma         = args.gamma,
        checkpoint_dir= args.checkpoint_dir,
        result_dir    = args.result_dir,
        img_dir       = args.img_dir,
    )
    exp.fit()

    # ── score & threshold ────────────────────────────────────────────────
    exp.predict()

    return True


def main():
    args = parse_args()

    data_dir   = Path(args.data_dir)
    result_dir = Path(args.result_dir)

    if not data_dir.exists():
        print(f"[ERROR] data_dir not found: {data_dir}")
        sys.exit(1)

    # collect subject CSV files
    csv_files = sorted(data_dir.glob("*.csv"))
    if not csv_files:
        print(f"[ERROR] No CSV files found in {data_dir}")
        sys.exit(1)

    # filter by subject list if provided
    if args.subjects:
        csv_files = [f for f in csv_files if f.stem in args.subjects]
        if not csv_files:
            print(f"[ERROR] None of the requested subjects found: {args.subjects}")
            sys.exit(1)

    print(f"Found {len(csv_files)} subject(s) to process.")
    print(f"Hyper-params: epochs={args.epochs}  bs={args.batch_size}  patience={args.patience}"
          f"  lr={args.lr}  window={args.window}  gamma={args.gamma}")

    success, skipped, failed = [], [], []

    for csv_path in csv_files:
        subject_id = csv_path.stem

        # skip if result already exists
        if args.skip_existing:
            test_result_file = result_dir / f"{subject_id}_iter_{args.iter}_testresult.csv"
            if test_result_file.exists():
                print(f"[SKIP] {subject_id} — result already exists.")
                skipped.append(subject_id)
                continue

        try:
            ok = run_subject(subject_id, csv_path, args)
            if ok:
                success.append(subject_id)
            else:
                failed.append(subject_id)
        except Exception as exc:
            print(f"[ERROR] {subject_id}: {exc}")
            import traceback; traceback.print_exc()
            failed.append(subject_id)

    # ── summary ──────────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print(f"Done.  success={len(success)}  skipped={len(skipped)}  failed={len(failed)}")
    if failed:
        print(f"Failed subjects: {failed}")
    print(f"Results saved to: {result_dir}/")


if __name__ == "__main__":
    main()
