"""
Anomaly-based Time Series Segmentation Module

This module segments brain signal time series based on detected anomaly points.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass


@dataclass
class Segment:
    """Represents a time series segment"""
    subject_id: str
    segment_id: int
    start_idx: int
    end_idx: int
    data: np.ndarray
    is_anomaly: bool = False
    
    @property
    def length(self) -> int:
        return self.end_idx - self.start_idx
    
    def __repr__(self):
        return f"Segment(subject={self.subject_id}, id={self.segment_id}, len={self.length}, anomaly={self.is_anomaly})"


def load_anomaly_results(result_path: Path, subject_id: str) -> Tuple[pd.DataFrame, np.ndarray]:
    """
    Load anomaly detection results for a subject.
    
    Args:
        result_path: Path to result directory
        subject_id: Subject identifier
        
    Returns:
        Tuple of (result_df, pred_global array)
    """
    test_result_file = result_path / f"{subject_id}_iter_0_testresult.csv"
    
    if not test_result_file.exists():
        raise FileNotFoundError(f"Result file not found: {test_result_file}")
    
    df = pd.read_csv(test_result_file)
    
    if 'Pred_Global' not in df.columns:
        raise ValueError(f"Pred_Global column not found in {test_result_file}")
    
    pred_global = df['Pred_Global'].values
    return df, pred_global


def load_original_timeseries(data_path: Path, subject_id: str) -> np.ndarray:
    """
    Load original time series data for a subject.
    
    Args:
        data_path: Path to data directory
        subject_id: Subject identifier
        
    Returns:
        Time series array of shape (T, n_features)
    """
    data_file = data_path / f"{subject_id}.csv"
    
    if not data_file.exists():
        raise FileNotFoundError(f"Data file not found: {data_file}")
    
    df = pd.read_csv(data_file, header=None)
    return df.values.astype(np.float32)


def segment_by_anomaly(
    timeseries: np.ndarray,
    pred_global: np.ndarray,
    min_segment_len: int = 30,
    subject_id: str = "unknown",
    window_size: int = 64
) -> List[Segment]:
    """
    Segment time series based on anomaly detection points.
    
    The time series is divided at points where anomalies are detected (pred_global == 1).
    Continuous normal regions (pred_global == 0) form individual segments.
    Segments shorter than min_segment_len are merged with adjacent segments.
    
    Args:
        timeseries: Original time series of shape (T, n_features)
        pred_global: Binary anomaly predictions of shape (T - window_size,)
        min_segment_len: Minimum segment length (shorter segments are merged)
        subject_id: Subject identifier for tracking
        window_size: Window size used in MTAD-GAT (default 64)
        
    Returns:
        List of Segment objects
    """
    T, n_features = timeseries.shape
    
    full_pred = np.zeros(T, dtype=np.int32)
    
    expected_pred_len = T - window_size
    actual_pred_len = len(pred_global)
    
    if actual_pred_len != expected_pred_len:
        copy_len = min(actual_pred_len, expected_pred_len)
        full_pred[window_size:window_size + copy_len] = pred_global[:copy_len]
    else:
        full_pred[window_size:window_size + len(pred_global)] = pred_global
    
    segments = []
    current_start = 0
    segment_id = 0
    
    i = 0
    while i < T:
        if full_pred[i] == 0:
            start = i
            while i < T and full_pred[i] == 0:
                i += 1
            end = i
            
            if end - start >= min_segment_len:
                seg = Segment(
                    subject_id=subject_id,
                    segment_id=segment_id,
                    start_idx=start,
                    end_idx=end,
                    data=timeseries[start:end].copy(),
                    is_anomaly=False
                )
                segments.append(seg)
                segment_id += 1
        else:
            anomaly_start = i
            while i < T and full_pred[i] == 1:
                i += 1
            anomaly_end = i
    
    if len(segments) == 0 and T >= min_segment_len:
        segments.append(Segment(
            subject_id=subject_id,
            segment_id=0,
            start_idx=0,
            end_idx=T,
            data=timeseries.copy(),
            is_anomaly=False
        ))
    
    segments = _merge_short_segments(segments, timeseries, min_segment_len)
    
    return segments


def _merge_short_segments(
    segments: List[Segment],
    timeseries: np.ndarray,
    min_segment_len: int
) -> List[Segment]:
    """
    Merge segments that are shorter than minimum length.
    
    Args:
        segments: List of segments
        timeseries: Original time series
        min_segment_len: Minimum segment length
        
    Returns:
        List of merged segments
    """
    if len(segments) <= 1:
        return segments
    
    merged = []
    i = 0
    
    while i < len(segments):
        current = segments[i]
        
        while current.length < min_segment_len and i + 1 < len(segments):
            next_seg = segments[i + 1]
            new_start = current.start_idx
            new_end = next_seg.end_idx
            current = Segment(
                subject_id=current.subject_id,
                segment_id=len(merged),
                start_idx=new_start,
                end_idx=new_end,
                data=timeseries[new_start:new_end].copy(),
                is_anomaly=False
            )
            i += 1
        
        current.segment_id = len(merged)
        merged.append(current)
        i += 1
    
    return merged


def load_test_subject_ids(split_dir: Path) -> Optional[List[str]]:
    """
    Load test subject IDs from split_info/test_subjects.txt. Returns None if not found.
    """
    test_file = Path(split_dir) / "test_subjects.txt"
    if not test_file.exists():
        return None
    with open(test_file) as f:
        return [line.strip() for line in f if line.strip()]


def segment_all_subjects(
    data_path: Path,
    result_path: Path,
    min_segment_len: int = 30,
    window_size: int = 64,
    subject_ids: Optional[List[str]] = None,
    split_dir: Optional[Path] = None,
) -> Dict[str, List[Segment]]:
    """
    Segment time series for subjects.
    
    Args:
        data_path: Path to data directory containing CSV files
        result_path: Path to result directory containing anomaly detection results
        min_segment_len: Minimum segment length
        window_size: Window size used in MTAD-GAT
        subject_ids: If provided, only process these subjects. If None and split_dir
                     has test_subjects.txt, use test subjects only.
        split_dir: Path to split_info dir (for loading test_subjects.txt)
        
    Returns:
        Dictionary mapping subject_id to list of segments
    """
    all_segments = {}
    
    if subject_ids is not None:
        ids_to_process = subject_ids
    else:
        if split_dir is None:
            split_dir = data_path.parent / "data_pre" / "split_info"
        test_ids = load_test_subject_ids(split_dir)
        if test_ids is not None:
            ids_to_process = test_ids
        else:
            ids_to_process = [f.stem for f in sorted(data_path.glob("*.csv"))]
    
    for subject_id in ids_to_process:
        try:
            timeseries = load_original_timeseries(data_path, subject_id)
            _, pred_global = load_anomaly_results(result_path, subject_id)
            
            segments = segment_by_anomaly(
                timeseries=timeseries,
                pred_global=pred_global,
                min_segment_len=min_segment_len,
                subject_id=subject_id,
                window_size=window_size
            )
            
            all_segments[subject_id] = segments
            print(f"Subject {subject_id}: {len(segments)} segments")
            
        except Exception as e:
            print(f"Error processing subject {subject_id}: {e}")
            continue
    
    return all_segments


def get_segment_statistics(all_segments: Dict[str, List[Segment]]) -> pd.DataFrame:
    """
    Get statistics about segments across all subjects.
    
    Args:
        all_segments: Dictionary mapping subject_id to list of segments
        
    Returns:
        DataFrame with segment statistics
    """
    stats = []
    
    for subject_id, segments in all_segments.items():
        for seg in segments:
            stats.append({
                'subject_id': subject_id,
                'segment_id': seg.segment_id,
                'start_idx': seg.start_idx,
                'end_idx': seg.end_idx,
                'length': seg.length,
                'is_anomaly': seg.is_anomaly
            })
    
    return pd.DataFrame(stats)


if __name__ == "__main__":
    from pathlib import Path
    
    data_path = Path("data/DATA")
    result_path = Path("result")
    
    all_segments = segment_all_subjects(data_path, result_path, min_segment_len=30)
    
    stats = get_segment_statistics(all_segments)
    print(f"\nTotal segments: {len(stats)}")
    print(f"Average segment length: {stats['length'].mean():.2f}")
    print(f"Segments per subject: {stats.groupby('subject_id').size().mean():.2f}")
