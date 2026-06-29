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


def _safe_tsne_perplexity(n_samples: int, perplexity: float = 30) -> float:
    """sklearn TSNE requires perplexity < n_samples."""
    if n_samples < 2:
        raise ValueError(f"t-SNE needs at least 2 samples, got {n_samples}")
    return float(min(perplexity, max(1, n_samples - 1)))


def _safe_umap_n_neighbors(n_samples: int, n_neighbors: int = 15) -> int:
    """UMAP requires n_neighbors < n_samples."""
    if n_samples < 2:
        raise ValueError(f"UMAP needs at least 2 samples, got {n_samples}")
    return int(min(n_neighbors, max(1, n_samples - 1)))


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
    n_cols: Optional[int] = None,
    save_path: Optional[Path] = None,
    show: bool = True
) -> plt.Figure:
    """
    Plot cluster centroid CMs.
    
    Args:
        centroids: Dictionary mapping cluster_id to centroid CM
        figsize: Figure size
        n_cols: Subplot columns (default: 2 when n_clusters==4, else min(n_clusters, 4))
        save_path: Path to save figure
        show: Whether to show figure
        
    Returns:
        matplotlib Figure
    """
    n_clusters = len(centroids)
    if n_cols is None:
        n_cols = 2 if n_clusters == 4 else min(n_clusters, 4)
    n_rows = (n_clusters + n_cols - 1) // n_cols
    
    if figsize is None:
        if n_clusters == 4 and n_cols == 2:
            figsize = (10, 10)
        else:
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
    n_samples = latents.shape[0]
    if method == 'tsne' and n_samples < 3:
        print(
            f"t-SNE skipped: n_samples={n_samples} is too small; using PCA instead."
        )
        method = 'pca'

    if method == 'tsne':
        perp = _safe_tsne_perplexity(n_samples, perplexity)
        if perp != perplexity:
            print(f"t-SNE: adjusted perplexity {perplexity} -> {perp} (n_samples={n_samples})")
        reducer = TSNE(n_components=2, perplexity=perp, random_state=42, init="pca")
        embedded = reducer.fit_transform(latents)
    elif method == 'umap':
        if not HAS_UMAP:
            print("UMAP not available, falling back to t-SNE")
            perp = _safe_tsne_perplexity(n_samples, perplexity)
            reducer = TSNE(n_components=2, perplexity=perp, random_state=42, init="pca")
            embedded = reducer.fit_transform(latents)
        else:
            nn = _safe_umap_n_neighbors(n_samples, n_neighbors)
            if nn != n_neighbors:
                print(f"UMAP: adjusted n_neighbors {n_neighbors} -> {nn} (n_samples={n_samples})")
            reducer = umap.UMAP(n_neighbors=nn, random_state=42)
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


def plot_latent_l2_norms_by_cluster(
    cluster_latents: Dict[int, np.ndarray],
    title: str = "Latent L2 norms by CM cluster",
    figsize: Tuple[int, int] = (10, 5),
    save_path: Optional[Path] = None,
    show: bool = True,
) -> plt.Figure:
    """Box/violin of per-sample ||z||_2 for each cluster (comparable scalar summaries)."""
    fig, ax = plt.subplots(figsize=figsize)
    cids = sorted(cluster_latents.keys())
    norms = []
    positions = []
    for i, cid in enumerate(cids):
        z = np.asarray(cluster_latents[cid], dtype=np.float64)
        if z.ndim != 2 or z.shape[0] == 0:
            continue
        n = np.linalg.norm(z, axis=1)
        norms.append(n)
        positions.append(i + 1)
    if not norms:
        ax.set_title(title + " (no data)")
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
        if show:
            plt.show()
        return fig
    parts = ax.violinplot(norms, positions=positions, showmeans=True, showmedians=True)
    for b in parts["bodies"]:
        b.set_alpha(0.55)
    ax.set_xticks(positions)
    ax.set_xticklabels([f"CM cluster {cids[j-1]}" for j in positions])
    ax.set_ylabel(r"$\|z\|_2$ per sequence")
    ax.set_title(title)
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    return fig


def plot_pooled_latents_dimred(
    cluster_latents: Dict[int, np.ndarray],
    method: str = "pca",
    max_samples_per_cluster: Optional[int] = 400,
    random_state: int = 42,
    l2_normalize: bool = True,
    title: str = "Pooled latents (exploratory)",
    figsize: Tuple[int, int] = (11, 8),
    save_path: Optional[Path] = None,
    show: bool = True,
) -> plt.Figure:
    """
    Concatenate per-cluster BrainLM latents and run one 2D embedding.

    Note: each cluster uses a different encoder; this view is exploratory only
    and should not be read as a metric embedding across clusters.
    """
    rng = np.random.default_rng(random_state)
    blocks = []
    labels = []
    for cid in sorted(cluster_latents.keys()):
        z = np.asarray(cluster_latents[cid], dtype=np.float32)
        if z.ndim != 2 or z.shape[0] == 0:
            continue
        if max_samples_per_cluster is not None and z.shape[0] > max_samples_per_cluster:
            idx = rng.choice(z.shape[0], size=max_samples_per_cluster, replace=False)
            z = z[idx]
        if l2_normalize:
            denom = np.linalg.norm(z, axis=1, keepdims=True) + 1e-8
            z = z / denom
        blocks.append(z)
        labels.append(np.full((z.shape[0],), cid, dtype=np.int64))
    if not blocks:
        fig, ax = plt.subplots(figsize=figsize)
        ax.set_title(title + " (no data)")
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
        if show:
            plt.show()
        return fig
    X = np.vstack(blocks)
    y = np.concatenate(labels, axis=0)
    if method == "pca":
        emb = PCA(n_components=2, random_state=random_state).fit_transform(X)
    elif method == "tsne":
        emb = TSNE(n_components=2, perplexity=min(30, max(5, X.shape[0] // 4)), random_state=random_state).fit_transform(X)
    elif method == "umap":
        if not HAS_UMAP:
            emb = PCA(n_components=2, random_state=random_state).fit_transform(X)
            method = "pca (UMAP unavailable)"
        else:
            emb = umap.UMAP(n_neighbors=min(15, max(5, X.shape[0] // 20)), random_state=random_state).fit_transform(X)
    else:
        raise ValueError(f"Unknown method: {method}")

    fig, ax = plt.subplots(figsize=figsize)
    uniq = np.unique(y)
    colors = plt.cm.tab10(np.linspace(0, 1, max(len(uniq), 1)))
    for i, lab in enumerate(uniq):
        m = y == lab
        ax.scatter(emb[m, 0], emb[m, 1], c=[colors[i % 10]], label=f"CM cluster {lab}", alpha=0.65, s=28)
    ax.set_xlabel("Dim 1")
    ax.set_ylabel("Dim 2")
    ax.set_title(title + f" | {method}")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    return fig


def plot_per_cluster_pca_grid(
    cluster_latents: Dict[int, np.ndarray],
    n_cols: int = 2,
    figsize_per_plot: Tuple[float, float] = (5.0, 4.2),
    save_path: Optional[Path] = None,
    show: bool = True,
) -> plt.Figure:
    """Small multiples: separate PCA in each cluster's own latent space."""
    cids = [cid for cid in sorted(cluster_latents.keys()) if np.asarray(cluster_latents[cid]).ndim == 2 and cluster_latents[cid].shape[0] >= 2 and cluster_latents[cid].shape[1] >= 2]
    if not cids:
        fig, ax = plt.subplots(figsize=figsize_per_plot)
        ax.set_title("Per-cluster PCA grid (no valid latents)")
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
        if show:
            plt.show()
        return fig
    n = len(cids)
    n_rows = (n + n_cols - 1) // n_cols
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(figsize_per_plot[0] * n_cols, figsize_per_plot[1] * n_rows))
    axes = np.atleast_1d(axes).ravel()
    for ax in axes[n:]:
        ax.axis("off")
    for i, cid in enumerate(cids):
        ax = axes[i]
        z = np.asarray(cluster_latents[cid], dtype=np.float32)
        emb = PCA(n_components=2, random_state=42).fit_transform(z)
        ax.scatter(emb[:, 0], emb[:, 1], s=22, alpha=0.65, color=plt.cm.viridis(0.45))
        ax.set_title(f"PCA | BrainLM trained on CM cluster {cid}\n(n={z.shape[0]})")
        ax.set_xlabel("PC1")
        ax.set_ylabel("PC2")
    fig.suptitle("Per-cluster PCA (each panel uses only that cluster's latents)", fontsize=13, y=1.02)
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    return fig


def plot_cluster_latent_mean_cosine_heatmap(
    cluster_latents: Dict[int, np.ndarray],
    l2_normalize: bool = True,
    title: str = "Cosine similarity of mean latents (pooled-geometry heuristic)",
    figsize: Tuple[int, int] = (7, 6),
    save_path: Optional[Path] = None,
    show: bool = True,
) -> plt.Figure:
    """
    Pairwise cosine similarity between mean latent vectors (one per CM cluster).

    Different per-cluster BrainLMs occupy different representation spaces; treat
    this heatmap as a coarse summary, not a rigorous alignment metric.
    """
    cids = sorted(cluster_latents.keys())
    means = []
    valid_cids = []
    for cid in cids:
        z = np.asarray(cluster_latents[cid], dtype=np.float64)
        if z.ndim != 2 or z.shape[0] == 0:
            continue
        m = z.mean(axis=0)
        if l2_normalize:
            m = m / (np.linalg.norm(m) + 1e-12)
        means.append(m)
        valid_cids.append(cid)
    if len(means) < 2:
        fig, ax = plt.subplots(figsize=figsize)
        ax.set_title(title + " (need >=2 clusters)")
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
        if show:
            plt.show()
        return fig
    M = np.stack(means, axis=0)
    sim = M @ M.T
    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(sim, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(valid_cids)))
    ax.set_yticks(range(len(valid_cids)))
    ax.set_xticklabels([str(c) for c in valid_cids])
    ax.set_yticklabels([str(c) for c in valid_cids])
    ax.set_xlabel("CM cluster id")
    ax.set_ylabel("CM cluster id")
    ax.set_title(title)
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    return fig


def _pairwise_cosine_upper(z: np.ndarray) -> np.ndarray:
    """Off-diagonal pairwise cosine similarities for rows of z."""
    z = np.asarray(z, dtype=np.float64)
    if z.shape[0] < 2:
        return np.array([], dtype=np.float64)
    norms = np.linalg.norm(z, axis=1, keepdims=True) + 1e-12
    zn = z / norms
    sim = zn @ zn.T
    iu = np.triu_indices(sim.shape[0], k=1)
    return sim[iu]


def plot_latent_scalar_stats_bars(
    cluster_latents: Dict[int, np.ndarray],
    title: str = "Per-cluster latent summary statistics",
    figsize: Tuple[int, int] = (11, 4),
    save_path: Optional[Path] = None,
    show: bool = True,
) -> plt.Figure:
    """Bar charts: sample count, mean L2 norm, within-cluster mean pairwise cosine."""
    cids = sorted(cluster_latents.keys())
    counts, mean_norms, mean_cos = [], [], []
    for cid in cids:
        z = np.asarray(cluster_latents[cid], dtype=np.float64)
        if z.ndim != 2 or z.shape[0] == 0:
            continue
        counts.append(z.shape[0])
        mean_norms.append(float(np.linalg.norm(z, axis=1).mean()))
        pc = _pairwise_cosine_upper(z)
        mean_cos.append(float(pc.mean()) if pc.size else np.nan)

    fig, axes = plt.subplots(1, 3, figsize=figsize)
    x = np.arange(len(cids))
    labels = [str(c) for c in cids]
    axes[0].bar(x, counts, color=plt.cm.Blues(0.55))
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels)
    axes[0].set_ylabel("# test sequences")
    axes[0].set_title("Sample count")

    axes[1].bar(x, mean_norms, color=plt.cm.Greens(0.55))
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels)
    axes[1].set_ylabel(r"mean $\|z\|_2$")
    axes[1].set_title("Mean L2 norm")

    cos_vals = [0.0 if np.isnan(v) else v for v in mean_cos]
    axes[2].bar(x, cos_vals, color=plt.cm.Oranges(0.55))
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(labels)
    axes[2].set_ylim(-0.05, 1.05)
    axes[2].set_ylabel("mean pairwise cosine")
    axes[2].set_title("Within-cluster cohesion")
    fig.suptitle(title, fontsize=13)
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    return fig


def plot_latent_pairwise_cosine_violin(
    cluster_latents: Dict[int, np.ndarray],
    title: str = "Within-cluster pairwise cosine similarity",
    figsize: Tuple[int, int] = (10, 5),
    save_path: Optional[Path] = None,
    show: bool = True,
) -> plt.Figure:
    """Violin of off-diagonal cosine similarities inside each CM cluster's latents."""
    fig, ax = plt.subplots(figsize=figsize)
    cids, sims, positions = [], [], []
    for i, cid in enumerate(sorted(cluster_latents.keys())):
        z = np.asarray(cluster_latents[cid], dtype=np.float64)
        if z.ndim != 2 or z.shape[0] < 2:
            continue
        pc = _pairwise_cosine_upper(z)
        if pc.size == 0:
            continue
        cids.append(cid)
        sims.append(pc)
        positions.append(i + 1)
    if not sims:
        ax.set_title(title + " (need >=2 samples per cluster)")
    else:
        parts = ax.violinplot(sims, positions=positions, showmeans=True, showmedians=True)
        for b in parts["bodies"]:
            b.set_alpha(0.55)
        ax.set_xticks(positions)
        ax.set_xticklabels([f"CM {c}" for c in cids])
        ax.set_ylim(-1.05, 1.05)
        ax.set_ylabel("pairwise cosine")
        ax.set_title(title)
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    return fig


def plot_within_cluster_cosine_heatmaps(
    cluster_latents: Dict[int, np.ndarray],
    min_samples: int = 3,
    max_samples: int = 40,
    n_cols: int = 2,
    figsize_per_plot: Tuple[float, float] = (4.5, 4.0),
    title: str = "Within-cluster latent cosine similarity",
    save_path: Optional[Path] = None,
    show: bool = True,
) -> plt.Figure:
    """Grid of cosine similarity matrices (test latents) per CM cluster."""
    rng = np.random.default_rng(42)
    eligible = []
    for cid in sorted(cluster_latents.keys()):
        z = np.asarray(cluster_latents[cid], dtype=np.float64)
        if z.ndim == 2 and z.shape[0] >= min_samples:
            if z.shape[0] > max_samples:
                idx = rng.choice(z.shape[0], size=max_samples, replace=False)
                z = z[idx]
            eligible.append((cid, z))
    if not eligible:
        fig, ax = plt.subplots(figsize=figsize_per_plot)
        ax.set_title(title + f" (need >={min_samples} samples)")
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
        if show:
            plt.show()
        return fig

    n = len(eligible)
    n_rows = (n + n_cols - 1) // n_cols
    fig, axes = plt.subplots(
        n_rows, n_cols,
        figsize=(figsize_per_plot[0] * n_cols, figsize_per_plot[1] * n_rows),
    )
    axes = np.atleast_1d(axes).ravel()
    for ax in axes[n:]:
        ax.axis("off")
    im_last = None
    for i, (cid, z) in enumerate(eligible):
        norms = np.linalg.norm(z, axis=1, keepdims=True) + 1e-12
        sim = (z / norms) @ (z / norms).T
        im_last = axes[i].imshow(sim, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
        axes[i].set_title(f"CM cluster {cid} (n={sim.shape[0]})")
        axes[i].set_xlabel("seq idx")
        axes[i].set_ylabel("seq idx")
    if im_last is not None:
        fig.colorbar(im_last, ax=axes[:n], fraction=0.02, pad=0.02, label="cosine")
    fig.suptitle(title, fontsize=13, y=1.02)
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    return fig


def plot_latent_mean_vector_heatmap(
    cluster_latents: Dict[int, np.ndarray],
    max_dims: int = 48,
    l2_normalize: bool = True,
    title: str = "Mean latent vectors per CM cluster",
    figsize: Optional[Tuple[int, int]] = None,
    save_path: Optional[Path] = None,
    show: bool = True,
) -> plt.Figure:
    """Heatmap of mean latent (rows=clusters); columns = top-variance latent dims (pooled)."""
    cids, means = [], []
    for cid in sorted(cluster_latents.keys()):
        z = np.asarray(cluster_latents[cid], dtype=np.float64)
        if z.ndim != 2 or z.shape[0] == 0:
            continue
        m = z.mean(axis=0)
        if l2_normalize:
            m = m / (np.linalg.norm(m) + 1e-12)
        means.append(m)
        cids.append(cid)
    if not means:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.set_title(title + " (no data)")
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
        if show:
            plt.show()
        return fig

    M = np.stack(means, axis=0)
    var = M.var(axis=0)
    order = np.argsort(-var)[: min(max_dims, M.shape[1])]
    M_sub = M[:, order]

    if figsize is None:
        figsize = (max(8, M_sub.shape[1] * 0.22), max(3.5, 0.55 * len(cids)))
    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(M_sub, aspect="auto", cmap="RdBu_r")
    ax.set_yticks(range(len(cids)))
    ax.set_yticklabels([f"CM {c}" for c in cids])
    ax.set_xlabel(f"latent dim (top {len(order)} by cross-cluster variance)")
    ax.set_title(title)
    plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    return fig


def plot_pca_explained_variance_per_cluster(
    cluster_latents: Dict[int, np.ndarray],
    max_components: int = 20,
    title: str = "PCA explained variance (within each cluster)",
    figsize: Tuple[int, int] = (10, 5),
    save_path: Optional[Path] = None,
    show: bool = True,
) -> plt.Figure:
    fig, ax = plt.subplots(figsize=figsize)
    for cid in sorted(cluster_latents.keys()):
        z = np.asarray(cluster_latents[cid], dtype=np.float64)
        if z.ndim != 2 or z.shape[0] < 2 or z.shape[1] < 2:
            continue
        n_comp = min(max_components, z.shape[0], z.shape[1])
        pca = PCA(n_components=n_comp, random_state=42)
        pca.fit(z)
        ax.plot(
            np.arange(1, n_comp + 1),
            np.cumsum(pca.explained_variance_ratio_),
            marker="o",
            ms=3,
            label=f"CM {cid} (n={z.shape[0]})",
        )
    ax.set_xlabel("PC index")
    ax.set_ylabel("cumulative explained variance")
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=9)
    ax.set_title(title)
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    return fig


def plot_per_cluster_embedding_grid(
    cluster_latents: Dict[int, np.ndarray],
    method: str = "tsne",
    min_samples: int = 5,
    n_cols: int = 2,
    figsize_per_plot: Tuple[float, float] = (5.0, 4.2),
    title: Optional[str] = None,
    save_path: Optional[Path] = None,
    show: bool = True,
) -> plt.Figure:
    """2D embedding grid (PCA or t-SNE) per cluster in its own latent space."""
    eligible = []
    for cid in sorted(cluster_latents.keys()):
        z = np.asarray(cluster_latents[cid], dtype=np.float32)
        if z.ndim == 2 and z.shape[0] >= min_samples and z.shape[1] >= 2:
            eligible.append((cid, z))
    if not eligible:
        fig, ax = plt.subplots(figsize=figsize_per_plot)
        ax.set_title((title or method.upper()) + f" (need >={min_samples} samples)")
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
        if show:
            plt.show()
        return fig

    n = len(eligible)
    n_rows = (n + n_cols - 1) // n_cols
    fig, axes = plt.subplots(
        n_rows, n_cols,
        figsize=(figsize_per_plot[0] * n_cols, figsize_per_plot[1] * n_rows),
    )
    axes = np.atleast_1d(axes).ravel()
    for ax in axes[n:]:
        ax.axis("off")
    for i, (cid, z) in enumerate(eligible):
        if method == "pca":
            emb = PCA(n_components=2, random_state=42).fit_transform(z)
        elif method == "tsne":
            perp = min(30, max(5, z.shape[0] // 4))
            emb = TSNE(n_components=2, perplexity=perp, random_state=42, init="pca").fit_transform(z)
        else:
            raise ValueError(f"Unknown method: {method}")
        axes[i].scatter(emb[:, 0], emb[:, 1], s=24, alpha=0.7, color=plt.cm.tab10(cid % 10))
        axes[i].set_title(f"{method.upper()} | CM {cid} (n={z.shape[0]})")
    fig.suptitle(title or f"Per-cluster {method.upper()} (separate encoders)", fontsize=13, y=1.02)
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    return fig


def plot_single_sample_latent_profiles(
    cluster_latents: Dict[int, np.ndarray],
    max_dims: int = 64,
    title: str = "Single-sequence latent profiles (|z| per dim)",
    figsize: Tuple[int, int] = (10, 6),
    save_path: Optional[Path] = None,
    show: bool = True,
) -> plt.Figure:
    """Bar profiles for clusters with only one test latent (PCA not defined)."""
    singles = {
        cid: np.asarray(z[0], dtype=np.float64)
        for cid, z in cluster_latents.items()
        if np.asarray(z).ndim == 2 and z.shape[0] == 1
    }
    if not singles:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.set_title(title + " (none)")
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
        if show:
            plt.show()
        return fig
    n = len(singles)
    fig, axes = plt.subplots(n, 1, figsize=(figsize[0], figsize[1] * max(n, 1) * 0.35))
    if n == 1:
        axes = [axes]
    for ax, (cid, vec) in zip(axes, sorted(singles.items())):
        k = min(max_dims, vec.shape[0])
        ax.bar(np.arange(k), np.abs(vec[:k]), color=plt.cm.tab10(cid % 10), alpha=0.75)
        ax.set_title(f"CM cluster {cid} (n=1 test seq)")
        ax.set_xlabel("latent dim")
        ax.set_ylabel("|z|")
    fig.suptitle(title, fontsize=12)
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    return fig


def _pooled_latent_matrix(
    cluster_latents: Dict[int, np.ndarray],
    max_samples_per_cluster: Optional[int],
    l2_normalize: bool,
    random_state: int = 42,
) -> Tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(random_state)
    blocks, labels = [], []
    for cid in sorted(cluster_latents.keys()):
        z = np.asarray(cluster_latents[cid], dtype=np.float32)
        if z.ndim != 2 or z.shape[0] == 0:
            continue
        if max_samples_per_cluster is not None and z.shape[0] > max_samples_per_cluster:
            idx = rng.choice(z.shape[0], size=max_samples_per_cluster, replace=False)
            z = z[idx]
        if l2_normalize:
            z = z / (np.linalg.norm(z, axis=1, keepdims=True) + 1e-8)
        blocks.append(z)
        labels.append(np.full((z.shape[0],), cid, dtype=np.int64))
    if not blocks:
        return np.zeros((0, 1), dtype=np.float32), np.zeros((0,), dtype=np.int64)
    return np.vstack(blocks), np.concatenate(labels)


def plot_pooled_latents_methods_panel(
    cluster_latents: Dict[int, np.ndarray],
    methods: Tuple[str, ...] = ("pca", "tsne", "umap"),
    max_samples_per_cluster: Optional[int] = 400,
    l2_normalize: bool = True,
    title: str = "Pooled latent comparison (exploratory)",
    figsize: Tuple[int, int] = (16, 5),
    save_path: Optional[Path] = None,
    show: bool = True,
) -> plt.Figure:
    """Side-by-side pooled 2D embeddings (PCA / t-SNE / UMAP) for cross-cluster comparison."""
    X, y = _pooled_latent_matrix(cluster_latents, max_samples_per_cluster, l2_normalize)
    n_m = len(methods)
    fig, axes = plt.subplots(1, n_m, figsize=figsize)
    if n_m == 1:
        axes = [axes]
    if X.shape[0] == 0:
        for ax in axes:
            ax.set_title("no data")
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
        if show:
            plt.show()
        return fig

    for ax, method in zip(axes, methods):
        mlabel = method
        if method == "pca":
            emb = PCA(n_components=2, random_state=42).fit_transform(X)
        elif method == "tsne":
            perp = min(30, max(5, X.shape[0] // 4))
            emb = TSNE(n_components=2, perplexity=perp, random_state=42, init="pca").fit_transform(X)
        elif method == "umap":
            if HAS_UMAP:
                emb = umap.UMAP(
                    n_neighbors=min(15, max(5, X.shape[0] // 20)),
                    random_state=42,
                ).fit_transform(X)
            else:
                emb = PCA(n_components=2, random_state=42).fit_transform(X)
                mlabel = "pca (no umap)"
        else:
            raise ValueError(f"Unknown method: {method}")
        uniq = np.unique(y)
        colors = plt.cm.tab10(np.linspace(0, 1, max(len(uniq), 1)))
        for j, lab in enumerate(uniq):
            mask = y == lab
            ax.scatter(emb[mask, 0], emb[mask, 1], c=[colors[j % 10]], label=f"CM {lab}", s=22, alpha=0.65)
        ax.set_title(mlabel.upper())
        ax.legend(fontsize=8, loc="best")
    fig.suptitle(title + "\n(different BrainLM per cluster — exploratory only)", fontsize=12)
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
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
        n_samples = latents.shape[0]
        if n_samples < 3:
            print(
                f"t-SNE skipped: n_samples={n_samples} is too small; using PCA instead."
            )
            reducer = PCA(n_components=3, random_state=42)
        else:
            perp = _safe_tsne_perplexity(n_samples, 30)
            reducer = TSNE(n_components=3, perplexity=perp, random_state=42, init="pca")
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
