"""
Connectivity Matrix (CM) Generation Module

This module computes Pearson correlation-based connectivity matrices
from segmented brain signal time series.
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import warnings

from .segmentation import Segment


@dataclass
class ConnectivityMatrix:
    """Represents a connectivity matrix for a segment"""
    subject_id: str
    segment_id: int
    matrix: np.ndarray
    n_features: int
    segment_length: int
    
    def __repr__(self):
        return f"CM(subject={self.subject_id}, segment={self.segment_id}, shape={self.matrix.shape})"
    
    def flatten_upper_triangle(self) -> np.ndarray:
        """Extract upper triangle (excluding diagonal) as 1D vector"""
        indices = np.triu_indices(self.n_features, k=1)
        return self.matrix[indices]
    
    @property
    def flat_size(self) -> int:
        """Size of flattened upper triangle"""
        return self.n_features * (self.n_features - 1) // 2


def compute_connectivity_matrix(
    segment: Segment,
    method: str = 'pearson'
) -> ConnectivityMatrix:
    """
    Compute connectivity matrix for a segment.
    
    Args:
        segment: Segment object containing time series data
        method: Correlation method ('pearson' supported)
        
    Returns:
        ConnectivityMatrix object
    """
    data = segment.data
    T, n_features = data.shape
    
    if T < 2:
        warnings.warn(f"Segment too short for correlation: T={T}")
        cm = np.eye(n_features)
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            cm = np.corrcoef(data.T)
        
        cm = np.nan_to_num(cm, nan=0.0)
        np.fill_diagonal(cm, 1.0)
    
    return ConnectivityMatrix(
        subject_id=segment.subject_id,
        segment_id=segment.segment_id,
        matrix=cm.astype(np.float32),
        n_features=n_features,
        segment_length=T
    )


def compute_all_cms(
    all_segments: Dict[str, List[Segment]],
    method: str = 'pearson',
    min_segment_len: int = 10
) -> Dict[str, List[ConnectivityMatrix]]:
    """
    Compute connectivity matrices for all segments across all subjects.
    
    Args:
        all_segments: Dictionary mapping subject_id to list of segments
        method: Correlation method
        min_segment_len: Minimum segment length for CM computation
        
    Returns:
        Dictionary mapping subject_id to list of ConnectivityMatrix objects
    """
    all_cms = {}
    
    for subject_id, segments in all_segments.items():
        cms = []
        for segment in segments:
            if segment.length >= min_segment_len:
                cm = compute_connectivity_matrix(segment, method=method)
                cms.append(cm)
        
        if cms:
            all_cms[subject_id] = cms
            print(f"Subject {subject_id}: {len(cms)} CMs computed")
    
    return all_cms


def collect_all_cms_flat(
    all_cms: Dict[str, List[ConnectivityMatrix]]
) -> Tuple[np.ndarray, List[Tuple[str, int]]]:
    """
    Collect all CMs into a single matrix for clustering.
    
    Args:
        all_cms: Dictionary mapping subject_id to list of ConnectivityMatrix
        
    Returns:
        Tuple of:
        - X: Matrix of shape (n_samples, n_features) where each row is flattened CM
        - labels: List of (subject_id, segment_id) tuples
    """
    flat_cms = []
    labels = []
    
    for subject_id, cms in all_cms.items():
        for cm in cms:
            flat_cm = cm.flatten_upper_triangle()
            flat_cms.append(flat_cm)
            labels.append((subject_id, cm.segment_id))
    
    X = np.array(flat_cms, dtype=np.float32)
    return X, labels


def compute_average_cm(cms: List[ConnectivityMatrix]) -> np.ndarray:
    """
    Compute average connectivity matrix from a list of CMs.
    
    Args:
        cms: List of ConnectivityMatrix objects
        
    Returns:
        Average CM as numpy array
    """
    if not cms:
        raise ValueError("Empty CM list")
    
    matrices = [cm.matrix for cm in cms]
    return np.mean(matrices, axis=0)


def compute_cm_similarity(cm1: np.ndarray, cm2: np.ndarray) -> float:
    """
    Compute similarity between two connectivity matrices.
    Uses Pearson correlation of flattened upper triangles.
    
    Args:
        cm1: First connectivity matrix
        cm2: Second connectivity matrix
        
    Returns:
        Similarity score (Pearson correlation)
    """
    n = cm1.shape[0]
    indices = np.triu_indices(n, k=1)
    
    flat1 = cm1[indices]
    flat2 = cm2[indices]
    
    correlation = np.corrcoef(flat1, flat2)[0, 1]
    return correlation if not np.isnan(correlation) else 0.0


def compute_subject_average_cm(
    all_cms: Dict[str, List[ConnectivityMatrix]]
) -> Dict[str, np.ndarray]:
    """
    Compute average CM for each subject.
    
    Args:
        all_cms: Dictionary mapping subject_id to list of ConnectivityMatrix
        
    Returns:
        Dictionary mapping subject_id to average CM
    """
    subject_avg_cms = {}
    
    for subject_id, cms in all_cms.items():
        if cms:
            subject_avg_cms[subject_id] = compute_average_cm(cms)
    
    return subject_avg_cms


def fisher_z_transform(cm: np.ndarray) -> np.ndarray:
    """
    Apply Fisher z-transformation to correlation matrix.
    This is useful for statistical comparisons.
    
    Args:
        cm: Connectivity matrix with values in [-1, 1]
        
    Returns:
        Fisher z-transformed matrix
    """
    cm_clipped = np.clip(cm, -0.9999, 0.9999)
    z = np.arctanh(cm_clipped)
    np.fill_diagonal(z, 0)
    return z


def inverse_fisher_z(z: np.ndarray) -> np.ndarray:
    """
    Apply inverse Fisher z-transformation.
    
    Args:
        z: Fisher z-transformed matrix
        
    Returns:
        Original correlation matrix
    """
    cm = np.tanh(z)
    np.fill_diagonal(cm, 1.0)
    return cm


if __name__ == "__main__":
    from pathlib import Path
    from .segmentation import segment_all_subjects
    
    data_path = Path("data/DATA")
    result_path = Path("result")
    
    all_segments = segment_all_subjects(data_path, result_path)
    all_cms = compute_all_cms(all_segments)
    
    X, labels = collect_all_cms_flat(all_cms)
    print(f"\nTotal CMs: {len(labels)}")
    print(f"Feature dimension: {X.shape[1]}")
