"""
Brain Signal Analysis Pipeline

Modules:
- segmentation: Anomaly-based time series segmentation
- connectivity: Connectivity Matrix (CM) generation
- clustering: K-means clustering with Elbow method
- tokenizer: CM tokenization for BrainLM
- visualization: Latent space visualization
"""

from .segmentation import segment_by_anomaly, load_anomaly_results, load_test_subject_ids
from .connectivity import compute_connectivity_matrix, compute_all_cms
from .clustering import (
    flatten_cm, find_optimal_k, perform_clustering, 
    compute_cluster_similarity, get_cluster_centroids
)
from .tokenizer import CMTokenizer
from .visualization import visualize_latents, plot_cm_heatmap, plot_similarity_matrix

__all__ = [
    'segment_by_anomaly',
    'load_anomaly_results',
    'load_test_subject_ids',
    'compute_connectivity_matrix',
    'compute_all_cms',
    'flatten_cm',
    'find_optimal_k',
    'perform_clustering',
    'compute_cluster_similarity',
    'get_cluster_centroids',
    'CMTokenizer',
    'visualize_latents',
    'plot_cm_heatmap',
    'plot_similarity_matrix',
]
