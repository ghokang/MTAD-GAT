"""
Segmentation Evaluation Module

Compares three segmentation methods:
1. Embedding change-based: dt = ||zt - zt-1||, smooth, find_peaks top-k, midpoint
2. Anomaly score peak + length constraint (existing)
3. Anomaly score peak + length constraint + smoothing
"""

import os
import sys
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
import torch
from scipy.signal import find_peaks
from torch.utils.data import DataLoader
from tqdm import tqdm

# Add project root
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model.mtad_gat import MTAD_GAT
from pipeline.segmentation import (
    Segment,
    load_anomaly_results,
    load_original_timeseries,
    load_test_subject_ids,
    segment_by_anomaly,
    _merge_short_segments,
)


# Paths
DATA_PRE = ROOT / "data" / "DATA" / "data_pre"
SPLIT_DIR = DATA_PRE / "split_info"
RESULT_DIR = ROOT / "result"
CHECKPOINT_DIR = ROOT / "checkpoint"
EVAL_OUTPUT_DIR = ROOT / "pipeline" / "segmentation_eval_output"
EVAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class WindowDataset:
    def __init__(self, data: np.ndarray, w: int = 64):
        self.data = data.astype(np.float32)
        self.w = w

    def __len__(self):
        return len(self.data) - self.w

    def __getitem__(self, idx):
        return self.data[idx : idx + self.w]


def load_test_data(subject_id: str) -> np.ndarray:
    fpath = DATA_PRE / f"test_{subject_id}.csv"
    if not fpath.exists():
        raise FileNotFoundError(f"Test data not found: {fpath}")
    df = pd.read_csv(fpath, header=0)
    return df.values.astype(np.float32)


def extract_embeddings(model, data: np.ndarray, device, w: int = 64, batch_size: int = 32):
    """Extract GRU h_last for each window."""
    model.eval()
    dataset = WindowDataset(data, w=w)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
    embeddings = []
    with torch.no_grad():
        for batch in loader:
            x = batch.float().to(device)
            h = model.get_embedding(x)  # (1, batch, hid_dim)
            h = h.squeeze(0).cpu().numpy()  # (batch, hid_dim)
            embeddings.append(h)
    return np.concatenate(embeddings, axis=0)


# ---------------------------------------------------------------------------
# Method 1: Embedding change-based segmentation
# ---------------------------------------------------------------------------
def segment_by_embedding_change(
    timeseries: np.ndarray,
    embeddings: np.ndarray,
    subject_id: str,
    window_size: int = 64,
    min_segment_len: int = 30,
    top_k: int = 20,
    smooth_window: int = 5,
) -> List[Segment]:
    """
    Segment by peaks in dt = ||zt - zt-1||.
    - dt smoothing
    - find_peaks, top-k
    - midpoint of peak as boundary
    """
    n_windows = len(embeddings)
    if n_windows < 2:
        if len(timeseries) >= min_segment_len:
            return [
                Segment(
                    subject_id=subject_id,
                    segment_id=0,
                    start_idx=0,
                    end_idx=len(timeseries),
                    data=timeseries.copy(),
                    is_anomaly=False,
                )
            ]
        return []

    # dt = ||zt - zt-1||
    dt = np.linalg.norm(embeddings[1:] - embeddings[:-1], axis=1)

    # Smooth dt
    if smooth_window > 1:
        kernel = np.ones(smooth_window) / smooth_window
        dt = np.convolve(dt, kernel, mode="same")

    # find_peaks, top-k
    peaks, properties = find_peaks(dt, height=0)
    if len(peaks) == 0:
        if len(timeseries) >= min_segment_len:
            return [
                Segment(
                    subject_id=subject_id,
                    segment_id=0,
                    start_idx=0,
                    end_idx=len(timeseries),
                    data=timeseries.copy(),
                    is_anomaly=False,
                )
            ]
        return []

    peak_heights = properties["peak_heights"]
    top_indices = np.argsort(peak_heights)[-top_k:]
    peak_positions = np.sort(peaks[top_indices])

    # Midpoint: boundary at window_size + peak_idx (start of second window in pair)
    # dt[i] = ||z[i+1]-z[i]||, so peak at i means change between window i and i+1
    # Boundary at index: window_size + peak_idx + 1 (start of window i+1 in time series)
    boundaries = [0]
    for p in peak_positions:
        b = window_size + p + 1  # start of window (p+1) in time series
        if b > boundaries[-1] + min_segment_len and b < len(timeseries) - min_segment_len:
            boundaries.append(b)
    boundaries.append(len(timeseries))

    segments = []
    for i, (s, e) in enumerate(zip(boundaries[:-1], boundaries[1:])):
        if e - s >= min_segment_len:
            segments.append(
                Segment(
                    subject_id=subject_id,
                    segment_id=len(segments),
                    start_idx=s,
                    end_idx=e,
                    data=timeseries[s:e].copy(),
                    is_anomaly=False,
                )
            )

    segments = _merge_short_segments(segments, timeseries, min_segment_len)
    return segments


# ---------------------------------------------------------------------------
# Method 2: Anomaly score peak + length constraint (existing)
# ---------------------------------------------------------------------------
def segment_by_anomaly_length(
    timeseries: np.ndarray,
    pred_global: np.ndarray,
    subject_id: str,
    window_size: int = 64,
    min_segment_len: int = 30,
) -> List[Segment]:
    """Existing method: anomaly peak + min_segment_len."""
    return segment_by_anomaly(
        timeseries=timeseries,
        pred_global=pred_global,
        min_segment_len=min_segment_len,
        subject_id=subject_id,
        window_size=window_size,
    )


# ---------------------------------------------------------------------------
# Method 3: Anomaly score peak + length constraint + smoothing
# ---------------------------------------------------------------------------
def smooth_prediction(pred: np.ndarray, window: int = 5, threshold: float = 0.5) -> np.ndarray:
    """Smooth binary prediction with rolling mean and re-threshold."""
    if window <= 1:
        return pred
    kernel = np.ones(window) / window
    smoothed = np.convolve(pred.astype(float), kernel, mode="same")
    return (smoothed >= threshold).astype(np.int64)


def segment_by_anomaly_length_smooth(
    timeseries: np.ndarray,
    pred_global: np.ndarray,
    subject_id: str,
    window_size: int = 64,
    min_segment_len: int = 30,
    smooth_window: int = 5,
) -> List[Segment]:
    """Anomaly peak + min_segment_len + smoothing on pred_global."""
    pred_smooth = smooth_prediction(pred_global, window=smooth_window)
    return segment_by_anomaly(
        timeseries=timeseries,
        pred_global=pred_smooth,
        min_segment_len=min_segment_len,
        subject_id=subject_id,
        window_size=window_size,
    )


# ---------------------------------------------------------------------------
# segment_all_subjects_embedding - for use in full_pipeline
# ---------------------------------------------------------------------------
def segment_all_subjects_embedding(
    data_path: Path,
    checkpoint_path: Path,
    min_segment_len: int = 30,
    window_size: int = 64,
    subject_ids: List[str] = None,
    split_dir: Path = None,
    top_k: int = 20,
    smooth_window: int = 5,
    device=None,
    data_pre_path: Path = None,
    verbose: bool = True,
) -> dict:
    """
    Segment all subjects using embedding change-based method.
    Returns Dict[subject_id, List[Segment]] compatible with segment_all_subjects.
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
    
    if subject_ids is None:
        if split_dir is None:
            split_dir = data_path.parent / "data_pre" / "split_info"
        subject_ids = load_test_subject_ids(split_dir)
        if subject_ids is None:
            base = data_pre_path or data_path
            subject_ids = [f.stem.replace("test_", "").replace("train_", "") for f in sorted(base.glob("*.csv"))]
    
    def _load_data(sid: str) -> np.ndarray:
        if data_pre_path:
            f = data_pre_path / f"test_{sid}.csv"
            if f.exists():
                return pd.read_csv(f, header=0).values.astype(np.float32)
        return load_original_timeseries(data_path, sid)
    
    checkpoint_path = Path(checkpoint_path)
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
    
    sample = _load_data(subject_ids[0])
    n_features = sample.shape[1]
    model = MTAD_GAT(n_features=n_features, seq_len=window_size).to(device)
    model.load_state_dict(torch.load(checkpoint_path, map_location=device))
    model.eval()
    
    all_segments = {}
    for sid in tqdm(subject_ids, desc="Embedding segmentation", disable=not verbose):
        try:
            data = _load_data(sid)
            embeddings = extract_embeddings(model, data, device, w=window_size)
            segs = segment_by_embedding_change(
                timeseries=data,
                embeddings=embeddings,
                subject_id=sid,
                window_size=window_size,
                min_segment_len=min_segment_len,
                top_k=top_k,
                smooth_window=smooth_window,
            )
            all_segments[sid] = segs
            if verbose:
                print(f"Subject {sid}: {len(segs)} segments")
        except Exception as e:
            if verbose:
                print(f"Error processing subject {sid}: {e}")
            continue
    return all_segments


# ---------------------------------------------------------------------------
# Evaluation & run
# ---------------------------------------------------------------------------
def get_segment_stats(segments: List[Segment]) -> dict:
    if not segments:
        return {"n_segments": 0, "mean_len": 0, "std_len": 0, "min_len": 0, "max_len": 0}
    lengths = [s.length for s in segments]
    return {
        "n_segments": len(segments),
        "mean_len": np.mean(lengths),
        "std_len": np.std(lengths),
        "min_len": np.min(lengths),
        "max_len": np.max(lengths),
    }


def run_evaluation(
    top_k: int = 20,
    smooth_window_emb: int = 5,
    smooth_window_pred: int = 5,
    min_segment_len: int = 30,
    window_size: int = 64,
):
    device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Device: {device}")

    test_ids = load_test_subject_ids(SPLIT_DIR)
    if not test_ids:
        test_ids = [f.stem.replace("test_", "") for f in sorted(DATA_PRE.glob("test_*.csv"))]
    print(f"Test subjects: {len(test_ids)}")

    # Load model
    checkpoint_path = CHECKPOINT_DIR / "global_checkpoint_iter_0.pkl"
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
    sample_data = load_test_data(test_ids[0])
    n_features = sample_data.shape[1]
    model = MTAD_GAT(n_features=n_features, seq_len=window_size).to(device)
    model.load_state_dict(torch.load(checkpoint_path, map_location=device))
    model.eval()

    results = {
        "method1_embedding": {},
        "method2_anomaly_length": {},
        "method3_anomaly_length_smooth": {},
    }
    stats_summary = {k: [] for k in results}

    for sid in tqdm(test_ids, desc="Evaluating"):
        try:
            data = load_test_data(sid)
            df_result, pred_global = load_anomaly_results(Path(RESULT_DIR), sid)

            # Method 1: Embedding-based
            embeddings = extract_embeddings(model, data, device, w=window_size)
            seg1 = segment_by_embedding_change(
                timeseries=data,
                embeddings=embeddings,
                subject_id=sid,
                window_size=window_size,
                min_segment_len=min_segment_len,
                top_k=top_k,
                smooth_window=smooth_window_emb,
            )
            results["method1_embedding"][sid] = seg1
            stats_summary["method1_embedding"].append(get_segment_stats(seg1))

            # Method 2: Anomaly + length
            seg2 = segment_by_anomaly_length(
                timeseries=data,
                pred_global=pred_global,
                subject_id=sid,
                window_size=window_size,
                min_segment_len=min_segment_len,
            )
            results["method2_anomaly_length"][sid] = seg2
            stats_summary["method2_anomaly_length"].append(get_segment_stats(seg2))

            # Method 3: Anomaly + length + smooth
            seg3 = segment_by_anomaly_length_smooth(
                timeseries=data,
                pred_global=pred_global,
                subject_id=sid,
                window_size=window_size,
                min_segment_len=min_segment_len,
                smooth_window=smooth_window_pred,
            )
            results["method3_anomaly_length_smooth"][sid] = seg3
            stats_summary["method3_anomaly_length_smooth"].append(get_segment_stats(seg3))

        except Exception as e:
            print(f"Error {sid}: {e}")

    # Aggregate stats
    summary_rows = []
    for method_name, stat_list in stats_summary.items():
        if not stat_list:
            continue
        n_seg = [s["n_segments"] for s in stat_list]
        mean_len = [s["mean_len"] for s in stat_list if s["n_segments"] > 0]
        summary_rows.append({
            "method": method_name,
            "mean_n_segments_per_subject": np.mean(n_seg),
            "std_n_segments": np.std(n_seg),
            "mean_segment_length": np.mean(mean_len) if mean_len else 0,
            "total_segments": sum(n_seg),
        })

    summary_df = pd.DataFrame(summary_rows)
    output_path = EVAL_OUTPUT_DIR / "segmentation_comparison.csv"
    summary_df.to_csv(output_path, index=False)
    print(f"\nSaved comparison to {output_path}")
    print("\n" + summary_df.to_string(index=False))

    # Save per-subject stats
    for method_name, seg_dict in results.items():
        rows = []
        for sid, segs in seg_dict.items():
            s = get_segment_stats(segs)
            s["subject_id"] = sid
            rows.append(s)
        pd.DataFrame(rows).to_csv(EVAL_OUTPUT_DIR / f"{method_name}_per_subject.csv", index=False)

    return results, summary_df


if __name__ == "__main__":
    run_evaluation(
        top_k=20,
        smooth_window_emb=5,
        smooth_window_pred=5,
        min_segment_len=30,
        window_size=64,
    )
