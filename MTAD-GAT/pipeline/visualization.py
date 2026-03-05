"""
Visualization Module

Visualization utilities for connectivity matrices, clustering results,
and BrainLM latent representations.
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA

try:
    import umap
    HAS_UMAP = True
except ImportError:
    HAS_UMAP = False

from .connectivity import ConnectivityMatrix
from .clustering import ClusteringResult


def set_style():
    """Set matplotlib style for publication-quality figures"""
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.rcParams.update({
        'font.size': 12,
        'axes.labelsize': 14,
        'axes.titlesize': 16,
        'xtick.labelsize': 12,
        'ytick.labelsize': 12,
        'legend.fontsize': 12,
        'figure.figsize': (10, 8),
        'figure.dpi': 100
    })


def plot_cm_heatmap(
    cm: Union[np.ndarray, ConnectivityMatrix],
    title: str = "Connectivity Matrix",
    cmap: str = "RdBu_r",
    vmin: float = -1.0,
    vmax: float = 1.0,
    figsize: Tuple[int, int] = (10, 8),
    save_path: Optional[Path] = None,
    show: bool = True
) -> plt.Figure:
    """
    Plot connectivity matrix as heatmap.
    
    Args:
        cm: Connectivity matrix or ConnectivityMatrix object
        title: Plot title
        cmap: Colormap
        vmin, vmax: Color scale limits
        figsize: Figure size
        save_path: Path to save figure
        show: Whether to show figure
        
    Returns:
        matplotlib Figure
    """
    if isinstance(cm, ConnectivityMatrix):
        matrix = cm.matrix
        title = f"{title} (Subject: {cm.subject_id}, Segment: {cm.segment_id})"
    else:
        matrix = cm
    
    fig, ax = plt.subplots(figsize=figsize)
    
    im = ax.imshow(matrix, cmap=cmap, vmin=vmin, vmax=vmax, aspect='auto')
    
    plt.colorbar(im, ax=ax, label='Correlation')
    
    ax.set_title(title)
    ax.set_xlabel('Brain Region')
    ax.set_ylabel('Brain Region')
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    
    if show:
        plt.show()
    
    return fig


def plot_multiple_cms(
    cms: List[Union[np.ndarray, ConnectivityMatrix]],
    titles: Optional[List[str]] = None,
    n_cols: int = 3,
    figsize: Optional[Tuple[int, int]] = None,
    save_path: Optional[Path] = None,
    show: bool = True
) -> plt.Figure:
    """
    Plot multiple connectivity matrices in a grid.
    
    Args:
        cms: List of connectivity matrices
        titles: List of titles
        n_cols: Number of columns
        figsize: Figure size
        save_path: Path to save figure
        show: Whether to show figure
        
    Returns:
        matplotlib Figure
    """
    n_cms = len(cms)
    n_rows = (n_cms + n_cols - 1) // n_cols
    
    if figsize is None:
        figsize = (4 * n_cols, 3.5 * n_rows)
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
    axes = np.array(axes).flatten()
    
    for i, cm in enumerate(cms):
        ax = axes[i]
        
        if isinstance(cm, ConnectivityMatrix):
            matrix = cm.matrix
            default_title = f"Subj {cm.subject_id}, Seg {cm.segment_id}"
        else:
            matrix = cm
            default_title = f"CM {i+1}"
        
        title = titles[i] if titles and i < len(titles) else default_title
        
        im = ax.imshow(matrix, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')
        ax.set_title(title, fontsize=10)
        ax.set_xticks([])
        ax.set_yticks([])
    
    for i in range(n_cms, len(axes)):
        axes[i].axis('off')
    
    fig.colorbar(im, ax=axes, shrink=0.6, label='Correlation')
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    
    if show:
        plt.show()
    
    return fig


def plot_cluster_centroids(
    centroids: Dict[int, np.ndarray],
    figsize: Optional[Tuple[int, int]] = None,
    save_path: Optional[Path] = None,
    show: bool = True
) -> plt.Figure:
    """
    Plot cluster centroid CMs.
    
    Args:
        centroids: Dictionary mapping cluster_id to centroid CM
        figsize: Figure size
        save_path: Path to save figure
        show: Whether to show figure
        
    Returns:
        matplotlib Figure
    """
    n_clusters = len(centroids)
    n_cols = min(n_clusters, 4)
    n_rows = (n_clusters + n_cols - 1) // n_cols
    
    if figsize is None:
        figsize = (4 * n_cols, 3.5 * n_rows)
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
    if n_clusters == 1:
        axes = [axes]
    else:
        axes = np.array(axes).flatten()
    
    for i, (cluster_id, centroid) in enumerate(sorted(centroids.items())):
        ax = axes[i]
        im = ax.imshow(centroid, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')
        ax.set_title(f'Cluster {cluster_id}', fontsize=12)
        ax.set_xticks([])
        ax.set_yticks([])
    
    for i in range(n_clusters, len(axes)):
        axes[i].axis('off')
    
    fig.colorbar(im, ax=axes, shrink=0.6, label='Correlation')
    fig.suptitle('Cluster Centroid Connectivity Matrices', fontsize=14)
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    
    if show:
        plt.show()
    
    return fig


def plot_elbow_curve(
    metrics: Dict,
    save_path: Optional[Path] = None,
    show: bool = True
) -> plt.Figure:
    """
    Plot elbow curve for K-means clustering.
    
    Args:
        metrics: Dictionary with 'k_range', 'inertias', 'silhouettes', 'optimal_k'
        save_path: Path to save figure
        show: Whether to show figure
        
    Returns:
        matplotlib Figure
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    k_range = metrics['k_range']
    inertias = metrics['inertias']
    silhouettes = metrics['silhouettes']
    optimal_k = metrics['optimal_k']
    
    ax1.plot(k_range, inertias, 'b-o', linewidth=2, markersize=8)
    ax1.axvline(x=optimal_k, color='r', linestyle='--', label=f'Optimal K={optimal_k}')
    ax1.set_xlabel('Number of Clusters (K)')
    ax1.set_ylabel('Inertia')
    ax1.set_title('Elbow Method')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    ax2.plot(k_range, silhouettes, 'g-o', linewidth=2, markersize=8)
    ax2.axvline(x=optimal_k, color='r', linestyle='--', label=f'Optimal K={optimal_k}')
    ax2.set_xlabel('Number of Clusters (K)')
    ax2.set_ylabel('Silhouette Score')
    ax2.set_title('Silhouette Analysis')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    
    if show:
        plt.show()
    
    return fig


def plot_similarity_matrix(
    similarities: Dict[str, Dict[int, float]],
    figsize: Tuple[int, int] = (12, 10),
    save_path: Optional[Path] = None,
    show: bool = True
) -> plt.Figure:
    """
    Plot similarity matrix between subjects and clusters.
    
    Args:
        similarities: Dictionary mapping subject_id to {cluster_id: similarity}
        figsize: Figure size
        save_path: Path to save figure
        show: Whether to show figure
        
    Returns:
        matplotlib Figure
    """
    subjects = sorted(similarities.keys())
    clusters = sorted(list(similarities[subjects[0]].keys()))
    
    matrix = np.zeros((len(subjects), len(clusters)))
    for i, subject in enumerate(subjects):
        for j, cluster in enumerate(clusters):
            matrix[i, j] = similarities[subject][cluster]
    
    fig, ax = plt.subplots(figsize=figsize)
    
    im = ax.imshow(matrix, cmap='YlOrRd', aspect='auto')
    
    ax.set_xticks(range(len(clusters)))
    ax.set_xticklabels([f'Cluster {c}' for c in clusters])
    
    if len(subjects) <= 20:
        ax.set_yticks(range(len(subjects)))
        ax.set_yticklabels(subjects)
    else:
        step = len(subjects) // 10
        ax.set_yticks(range(0, len(subjects), step))
        ax.set_yticklabels([subjects[i] for i in range(0, len(subjects), step)])
    
    plt.colorbar(im, ax=ax, label='Similarity')
    ax.set_xlabel('Cluster')
    ax.set_ylabel('Subject')
    ax.set_title('Subject-Cluster Similarity Matrix')
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    
    if show:
        plt.show()
    
    return fig


def visualize_latents(
    latents: np.ndarray,
    labels: np.ndarray,
    method: str = 'tsne',
    perplexity: int = 30,
    n_neighbors: int = 15,
    figsize: Tuple[int, int] = (12, 10),
    title: str = "Latent Space Visualization",
    save_path: Optional[Path] = None,
    show: bool = True
) -> plt.Figure:
    """
    Visualize latent representations using dimensionality reduction.
    
    Args:
        latents: Latent representations of shape (n_samples, d_model)
        labels: Cluster or class labels
        method: 'tsne', 'umap', or 'pca'
        perplexity: Perplexity for t-SNE
        n_neighbors: Number of neighbors for UMAP
        figsize: Figure size
        title: Plot title
        save_path: Path to save figure
        show: Whether to show figure
        
    Returns:
        matplotlib Figure
    """
    if method == 'tsne':
        reducer = TSNE(n_components=2, perplexity=perplexity, random_state=42)
        embedded = reducer.fit_transform(latents)
    elif method == 'umap':
        if not HAS_UMAP:
            print("UMAP not available, falling back to t-SNE")
            reducer = TSNE(n_components=2, perplexity=perplexity, random_state=42)
            embedded = reducer.fit_transform(latents)
        else:
            reducer = umap.UMAP(n_neighbors=n_neighbors, random_state=42)
            embedded = reducer.fit_transform(latents)
    elif method == 'pca':
        reducer = PCA(n_components=2, random_state=42)
        embedded = reducer.fit_transform(latents)
    else:
        raise ValueError(f"Unknown method: {method}")
    
    fig, ax = plt.subplots(figsize=figsize)
    
    unique_labels = np.unique(labels)
    colors = plt.cm.tab10(np.linspace(0, 1, len(unique_labels)))
    
    for i, label in enumerate(unique_labels):
        mask = labels == label
        ax.scatter(
            embedded[mask, 0],
            embedded[mask, 1],
            c=[colors[i]],
            label=f'Cluster {label}' if label >= 0 else 'Unknown',
            alpha=0.7,
            s=50
        )
    
    ax.set_xlabel(f'{method.upper()} Dimension 1')
    ax.set_ylabel(f'{method.upper()} Dimension 2')
    ax.set_title(title)
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    
    if show:
        plt.show()
    
    return fig


def visualize_latents_3d(
    latents: np.ndarray,
    labels: np.ndarray,
    method: str = 'pca',
    title: str = "3D Latent Space",
    figsize: Tuple[int, int] = (12, 10),
    save_path: Optional[Path] = None,
    show: bool = True
) -> plt.Figure:
    """
    3D visualization of latent representations.
    
    Args:
        latents: Latent representations
        labels: Cluster labels
        method: Dimensionality reduction method
        title: Plot title
        figsize: Figure size
        save_path: Path to save
        show: Whether to show
        
    Returns:
        matplotlib Figure
    """
    if method == 'pca':
        reducer = PCA(n_components=3, random_state=42)
        embedded = reducer.fit_transform(latents)
    elif method == 'tsne':
        reducer = TSNE(n_components=3, perplexity=30, random_state=42)
        embedded = reducer.fit_transform(latents)
    else:
        raise ValueError(f"Unknown method: {method}")
    
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection='3d')
    
    unique_labels = np.unique(labels)
    colors = plt.cm.tab10(np.linspace(0, 1, len(unique_labels)))
    
    for i, label in enumerate(unique_labels):
        mask = labels == label
        ax.scatter(
            embedded[mask, 0],
            embedded[mask, 1],
            embedded[mask, 2],
            c=[colors[i]],
            label=f'Cluster {label}',
            alpha=0.7,
            s=50
        )
    
    ax.set_xlabel('Dim 1')
    ax.set_ylabel('Dim 2')
    ax.set_zlabel('Dim 3')
    ax.set_title(title)
    ax.legend()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    
    if show:
        plt.show()
    
    return fig


def plot_training_history(
    history: Dict[str, List[float]],
    figsize: Tuple[int, int] = (14, 5),
    save_path: Optional[Path] = None,
    show: bool = True
) -> plt.Figure:
    """
    Plot training history.
    
    Args:
        history: Training history dictionary
        figsize: Figure size
        save_path: Path to save
        show: Whether to show
        
    Returns:
        matplotlib Figure
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
    
    epochs = range(1, len(history['train_loss']) + 1)
    
    ax1.plot(epochs, history['train_loss'], 'b-', label='Train Loss', linewidth=2)
    if 'val_loss' in history:
        ax1.plot(epochs, history['val_loss'], 'r-', label='Val Loss', linewidth=2)
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Loss')
    ax1.set_title('Training and Validation Loss')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    if 'lr' in history:
        ax2.plot(epochs, history['lr'], 'g-', linewidth=2)
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('Learning Rate')
        ax2.set_title('Learning Rate Schedule')
        ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    
    if show:
        plt.show()
    
    return fig


def plot_cluster_distribution(
    result: ClusteringResult,
    figsize: Tuple[int, int] = (10, 6),
    save_path: Optional[Path] = None,
    show: bool = True
) -> plt.Figure:
    """
    Plot distribution of samples across clusters.
    
    Args:
        result: ClusteringResult object
        figsize: Figure size
        save_path: Path to save
        show: Whether to show
        
    Returns:
        matplotlib Figure
    """
    cluster_sizes = result.get_cluster_sizes()
    
    fig, ax = plt.subplots(figsize=figsize)
    
    clusters = list(cluster_sizes.keys())
    sizes = list(cluster_sizes.values())
    
    bars = ax.bar(clusters, sizes, color=plt.cm.tab10(np.linspace(0, 1, len(clusters))))
    
    for bar, size in zip(bars, sizes):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                str(size), ha='center', va='bottom', fontsize=12)
    
    ax.set_xlabel('Cluster ID')
    ax.set_ylabel('Number of Samples')
    ax.set_title(f'Cluster Distribution (Total: {sum(sizes)}, Silhouette: {result.silhouette:.3f})')
    ax.set_xticks(clusters)
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    
    if show:
        plt.show()
    
    return fig


if __name__ == "__main__":
    np.random.seed(42)
    
    cm = np.random.randn(100, 100)
    cm = (cm + cm.T) / 2
    np.fill_diagonal(cm, 1.0)
    
    plot_cm_heatmap(cm, title="Example CM", show=True)
    
    latents = np.random.randn(200, 64)
    labels = np.random.randint(0, 5, 200)
    
    visualize_latents(latents, labels, method='tsne', title="Example Latent Space")
