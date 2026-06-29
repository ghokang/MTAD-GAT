"""
K-means Clustering Module with Elbow Method

This module performs clustering on connectivity matrices
and computes similarity between individual and cluster CMs.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from sklearn.cluster import KMeans, MiniBatchKMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from dataclasses import dataclass
import warnings

from .connectivity import ConnectivityMatrix


@dataclass
class ClusteringResult:
    """Results from clustering analysis"""
    n_clusters: int
    labels: np.ndarray
    centroids: np.ndarray
    inertia: float
    silhouette: float
    cm_labels: List[Tuple[str, int]]
    
    def get_cluster_members(self, cluster_id: int) -> List[Tuple[str, int]]:
        """Get (subject_id, segment_id) pairs for a cluster"""
        indices = np.where(self.labels == cluster_id)[0]
        return [self.cm_labels[i] for i in indices]
    
    def get_cluster_sizes(self) -> Dict[int, int]:
        """Get size of each cluster"""
        unique, counts = np.unique(self.labels, return_counts=True)
        return dict(zip(unique, counts))


def flatten_cm(cm: np.ndarray) -> np.ndarray:
    """
    Flatten connectivity matrix to 1D vector (upper triangle only).
    
    Args:
        cm: Connectivity matrix of shape (n, n)
        
    Returns:
        1D array of upper triangle values
    """
    n = cm.shape[0]
    indices = np.triu_indices(n, k=1)
    return cm[indices]


def unflatten_cm(flat_cm: np.ndarray, n: int = 100) -> np.ndarray:
    """
    Reconstruct connectivity matrix from flattened vector.
    
    Args:
        flat_cm: Flattened CM vector
        n: Number of features (brain regions)
        
    Returns:
        Reconstructed symmetric CM
    """
    cm = np.zeros((n, n), dtype=np.float32)
    indices = np.triu_indices(n, k=1)
    cm[indices] = flat_cm
    cm = cm + cm.T
    np.fill_diagonal(cm, 1.0)
    return cm


def find_optimal_k(
    X: np.ndarray,
    k_range: range = range(2, 15),
    method: str = 'elbow',
    random_state: int = 42,
    n_init: int = 3,
    skip_silhouette: bool = False,
    silhouette_sample_size: Optional[int] = 500,
    use_minibatch: bool = False,
) -> Tuple[int, Dict]:
    """
    Find optimal number of clusters using Elbow method.
    
    Args:
        X: Data matrix of shape (n_samples, n_features)
        k_range: Range of k values to try
        method: Method for finding optimal k ('elbow' or 'silhouette')
        random_state: Random seed
        n_init: KMeans runs per k (lower = faster, use 1 if kernel crashes)
        skip_silhouette: Skip silhouette computation (recommended if kernel crashes)
        silhouette_sample_size: Subsample size for silhouette. None=full data.
        use_minibatch: Use MiniBatchKMeans (less memory, kernel crash 방지)
        
    Returns:
        Tuple of (optimal_k, metrics_dict)
    """
    inertias = []
    silhouettes = []
    k_list = list(k_range)
    km_cls = MiniBatchKMeans if use_minibatch else KMeans
    
    for k in k_list:
        km = km_cls(n_clusters=k, random_state=random_state, n_init=n_init)
        labels = km.fit_predict(X)
        inertias.append(km.inertia_)
        
        if k >= 2 and not skip_silhouette:
            try:
                ss = min(silhouette_sample_size, len(X)) if silhouette_sample_size else None
                sil = silhouette_score(
                    X, labels,
                    sample_size=ss,
                    random_state=random_state if ss else None,
                )
                silhouettes.append(sil)
            except (MemoryError, Exception):
                silhouettes.append(0.0)
        else:
            silhouettes.append(0.0)
    
    if method == 'elbow':
        optimal_k = _detect_elbow(k_list, inertias)
    elif silhouettes and any(s > 0 for s in silhouettes):
        optimal_k = k_list[np.argmax(silhouettes)]
    else:
        optimal_k = _detect_elbow(k_list, inertias)
    
    metrics = {
        'k_range': k_list,
        'inertias': inertias,
        'silhouettes': silhouettes,
        'optimal_k': optimal_k
    }
    
    return optimal_k, metrics


def _detect_elbow(k_values: List[int], inertias: List[float]) -> int:
    """
    Detect elbow point using the maximum curvature method.
    
    Args:
        k_values: List of k values
        inertias: Corresponding inertia values
        
    Returns:
        Optimal k at elbow point
    """
    if len(k_values) < 3:
        return k_values[0]
    
    k_arr = np.array(k_values)
    inertia_arr = np.array(inertias)
    
    k_norm = (k_arr - k_arr.min()) / (k_arr.max() - k_arr.min() + 1e-10)
    inertia_norm = (inertia_arr - inertia_arr.min()) / (inertia_arr.max() - inertia_arr.min() + 1e-10)
    
    p1 = np.array([k_norm[0], inertia_norm[0]])
    p2 = np.array([k_norm[-1], inertia_norm[-1]])
    
    distances = []
    for i in range(len(k_values)):
        p = np.array([k_norm[i], inertia_norm[i]])
        d = np.abs(np.cross(p2 - p1, p1 - p)) / (np.linalg.norm(p2 - p1) + 1e-10)
        distances.append(d)
    
    elbow_idx = np.argmax(distances)
    return k_values[elbow_idx]


def perform_clustering(
    X: np.ndarray,
    cm_labels: List[Tuple[str, int]],
    n_clusters: Optional[int] = None,
    k_range: range = range(2, 15),
    standardize: bool = True,
    use_minibatch: bool = False,
    random_state: int = 42,
    n_init: int = 10,
    max_iter: int = 300,
    batch_size: int = 1024,
    skip_silhouette: bool = False,
    silhouette_sample_size: Optional[int] = 500,
) -> ClusteringResult:
    """
    Perform K-means clustering on CM data.
    
    Args:
        X: Data matrix of shape (n_samples, n_features)
        cm_labels: List of (subject_id, segment_id) tuples
        n_clusters: Number of clusters (if None, use Elbow method)
        k_range: Range of k values for Elbow method
        standardize: Whether to standardize features
        use_minibatch: Use MiniBatchKMeans (less memory, kernel crash 방지)
        random_state: Random seed
        n_init: KMeans runs (lower if kernel crashes)
        max_iter: Maximum iterations for (MiniBatch)KMeans
        batch_size: MiniBatchKMeans batch size (ignored if use_minibatch=False)
        skip_silhouette: Skip silhouette computation (recommended if kernel crashes)
        silhouette_sample_size: Subsample for silhouette; None=full. Ignored if skip_silhouette.
        
    Returns:
        ClusteringResult object
    """
    # Ensure numeric array (sklearn may upcast; keep input compact when possible)
    X_in = np.asarray(X)
    if standardize:
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_in)
    else:
        X_scaled = X_in
    
    if n_clusters is None:
        n_clusters, metrics = find_optimal_k(X_scaled, k_range, random_state=random_state)
        print(f"Optimal K determined by Elbow method: {n_clusters}")
    
    km_cls = MiniBatchKMeans if use_minibatch else KMeans
    try:
        if use_minibatch:
            kmeans = km_cls(
                n_clusters=n_clusters,
                random_state=random_state,
                n_init=n_init,
                max_iter=max_iter,
                batch_size=batch_size,
            )
        else:
            kmeans = km_cls(
                n_clusters=n_clusters,
                random_state=random_state,
                n_init=n_init,
                max_iter=max_iter,
            )
        labels = kmeans.fit_predict(X_scaled)
    except Exception:
        # Fallback: if full KMeans triggers a native crash/MemoryError upstream,
        # try MiniBatchKMeans as a safer alternative.
        kmeans = MiniBatchKMeans(
            n_clusters=n_clusters,
            random_state=random_state,
            n_init=max(1, n_init),
            max_iter=max_iter,
            batch_size=batch_size,
        )
        labels = kmeans.fit_predict(X_scaled)
    
    if n_clusters > 1 and not skip_silhouette:
        try:
            ss = min(silhouette_sample_size, len(X_scaled)) if silhouette_sample_size else None
            sil = silhouette_score(X_scaled, labels, sample_size=ss, random_state=random_state if ss else None)
        except (MemoryError, Exception):
            sil = 0.0
    else:
        sil = 0.0
    
    return ClusteringResult(
        n_clusters=n_clusters,
        labels=labels,
        centroids=kmeans.cluster_centers_,
        inertia=kmeans.inertia_,
        silhouette=sil,
        cm_labels=cm_labels
    )


def get_cluster_centroids(
    result: ClusteringResult,
    n_features: int = 100
) -> Dict[int, np.ndarray]:
    """
    Get cluster centroid CMs.
    
    Args:
        result: ClusteringResult object
        n_features: Number of features (brain regions)
        
    Returns:
        Dictionary mapping cluster_id to centroid CM
    """
    centroids = {}
    
    for i in range(result.n_clusters):
        flat_centroid = result.centroids[i]
        cm = unflatten_cm(flat_centroid, n_features)
        centroids[i] = cm
    
    return centroids


def compute_cluster_similarity(
    all_cms: Dict[str, List[ConnectivityMatrix]],
    result: ClusteringResult,
    n_features: int = 100
) -> Dict[str, Dict[int, float]]:
    """
    Compute similarity between individual CMs and cluster centroids.
    
    Args:
        all_cms: Dictionary mapping subject_id to list of CMs
        result: ClusteringResult object
        n_features: Number of features
        
    Returns:
        Dictionary mapping subject_id to dict of {cluster_id: similarity}
    """
    centroids = get_cluster_centroids(result, n_features)
    
    similarities = {}
    
    for subject_id, cms in all_cms.items():
        subject_similarities = {}
        
        for cluster_id, centroid in centroids.items():
            sims = []
            for cm in cms:
                sim = _cm_similarity(cm.matrix, centroid)
                sims.append(sim)
            subject_similarities[cluster_id] = np.mean(sims) if sims else 0.0
        
        similarities[subject_id] = subject_similarities
    
    return similarities


def _cm_similarity(cm1: np.ndarray, cm2: np.ndarray) -> float:
    """
    Compute similarity between two CMs using Pearson correlation.
    
    Args:
        cm1: First CM
        cm2: Second CM
        
    Returns:
        Similarity score
    """
    n = cm1.shape[0]
    indices = np.triu_indices(n, k=1)
    
    flat1 = cm1[indices]
    flat2 = cm2[indices]
    
    corr = np.corrcoef(flat1, flat2)[0, 1]
    return corr if not np.isnan(corr) else 0.0


def compute_within_cluster_similarity(
    X: np.ndarray,
    result: ClusteringResult
) -> Dict[int, float]:
    """
    Compute average within-cluster similarity.
    
    Args:
        X: Data matrix
        result: ClusteringResult object
        
    Returns:
        Dictionary mapping cluster_id to average similarity
    """
    within_sims = {}
    
    for cluster_id in range(result.n_clusters):
        indices = np.where(result.labels == cluster_id)[0]
        
        if len(indices) < 2:
            within_sims[cluster_id] = 1.0
            continue
        
        cluster_data = X[indices]
        n = len(indices)
        
        sims = []
        for i in range(n):
            for j in range(i + 1, n):
                sim = np.corrcoef(cluster_data[i], cluster_data[j])[0, 1]
                if not np.isnan(sim):
                    sims.append(sim)
        
        within_sims[cluster_id] = np.mean(sims) if sims else 0.0
    
    return within_sims


def compute_between_cluster_similarity(
    result: ClusteringResult,
    n_features: int = 100
) -> np.ndarray:
    """
    Compute similarity between cluster centroids.
    
    Args:
        result: ClusteringResult object
        n_features: Number of features
        
    Returns:
        Similarity matrix of shape (n_clusters, n_clusters)
    """
    centroids = get_cluster_centroids(result, n_features)
    n_clusters = result.n_clusters
    
    sim_matrix = np.eye(n_clusters)
    
    for i in range(n_clusters):
        for j in range(i + 1, n_clusters):
            sim = _cm_similarity(centroids[i], centroids[j])
            sim_matrix[i, j] = sim
            sim_matrix[j, i] = sim
    
    return sim_matrix


def assign_new_cm_to_cluster(
    cm: np.ndarray,
    result: ClusteringResult,
    n_features: int = 100
) -> Tuple[int, np.ndarray]:
    """
    Assign a new CM to the nearest cluster.
    
    Args:
        cm: New connectivity matrix
        result: ClusteringResult from training
        n_features: Number of features
        
    Returns:
        Tuple of (assigned_cluster_id, distances_to_all_centroids)
    """
    flat_cm = flatten_cm(cm)
    
    centroids = result.centroids
    distances = []
    
    for centroid in centroids:
        dist = np.linalg.norm(flat_cm - centroid)
        distances.append(dist)
    
    assigned_cluster = np.argmin(distances)
    return assigned_cluster, np.array(distances)


if __name__ == "__main__":
    np.random.seed(42)
    n_samples = 100
    n_features = 100
    flat_size = n_features * (n_features - 1) // 2
    
    X = np.random.randn(n_samples, flat_size).astype(np.float32)
    cm_labels = [(f"subj_{i//10}", i % 10) for i in range(n_samples)]
    
    optimal_k, metrics = find_optimal_k(X, k_range=range(2, 10))
    print(f"Optimal K: {optimal_k}")
    
    result = perform_clustering(X, cm_labels, n_clusters=optimal_k)
    print(f"Cluster sizes: {result.get_cluster_sizes()}")
    print(f"Silhouette score: {result.silhouette:.4f}")
