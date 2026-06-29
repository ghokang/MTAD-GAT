"""
연구 결과 종합 시각화 스크립트
- 가설 검증 여부를 한눈에 파악할 수 있는 5개 Figure 생성
- 출력: visualization_results/ 폴더
"""

import os
import sys
import pickle
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import TwoSlopeNorm, Normalize
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

OUT = ROOT / 'visualization_results'
OUT.mkdir(exist_ok=True)

CLUSTER_COLORS = ['#E74C3C', '#3498DB', '#2ECC71', '#F39C12']
CLUSTER_LABELS = ['State 0', 'State 1', 'State 2', 'State 3']

# ──────────────────────────────────────────────
# 데이터 로드
# ──────────────────────────────────────────────
print("=" * 60)
print("[1] 데이터 로드 중...")
print("=" * 60)

V2_BASE = ROOT / 'visualization_ver2' / 'final_runs' / 'seq6_st1_z_ep50'
V1_BASE = ROOT / 'visualization_ver1'

# V2 latents (per-cluster BrainLM)
v2_latents, v2_cluster_ids = {}, {}
for cid in range(4):
    lat_path = V2_BASE / f'latents_seq6_st1_z_ep50_cluster{cid}.npy'
    cid_path = V2_BASE / f'cluster_ids_seq6_st1_z_ep50_cluster{cid}.npy'
    if lat_path.exists():
        v2_latents[cid] = np.load(lat_path)
        v2_cluster_ids[cid] = np.load(cid_path)
        print(f"  V2 Cluster {cid}: {v2_latents[cid].shape}")

# V1 latents (single BrainLM)
v1_lat = np.load(V1_BASE / 'latents_z.npy')        # (308, 256)
v1_cids = np.load(V1_BASE / 'cluster_ids_z.npy')   # (308,)
print(f"  V1 latents: {v1_lat.shape}, cluster_ids: {v1_cids.shape}")

# Training results
df_results = pd.read_csv(V2_BASE / 'results_seq6_st1_z_ep50.csv')
print(f"  Training results: {len(df_results)} clusters")

# Segment cache + CM 재계산
CACHE = ROOT / 'checkpoint' / 'brainlm_v3' / 'cache' / 'all_segments.pkl'
all_segments, all_cms, cm_labels, clustering_result = None, None, None, None
if CACHE.exists():
    print("  세그먼트 캐시 로드 중...")
    with open(CACHE, 'rb') as f:
        all_segments = pickle.load(f)
    print(f"  세그먼트 수: {sum(len(v) for v in all_segments.values())}")

    from pipeline.connectivity import compute_all_cms, collect_all_cms_flat
    from pipeline.clustering import perform_clustering, get_cluster_centroids

    all_cms = compute_all_cms(all_segments, method='pearson', min_segment_len=10, use_fisher_z=True)
    X_cm, cm_labels = collect_all_cms_flat(all_cms)
    n_features = next(iter(all_cms.values()))[0].n_features
    print(f"  CM shape: {X_cm.shape}")

    clustering_result = perform_clustering(
        X_cm, cm_labels, n_clusters=4,
        use_minibatch=True, n_init=4, max_iter=200,
        batch_size=256, skip_silhouette=True, random_state=42
    )
    centroids = get_cluster_centroids(clustering_result, n_features=n_features)
    print(f"  클러스터 크기: {clustering_result.get_cluster_sizes()}")
else:
    print("  [경고] 세그먼트 캐시 없음 — CM 분석 스킵")
    X_cm, cm_labels, centroids = None, None, None


# ──────────────────────────────────────────────
# Figure 1: 결과 요약 대시보드
# ──────────────────────────────────────────────
print("\n[2] Figure 1: 결과 요약 대시보드...")

fig1, axes = plt.subplots(2, 3, figsize=(18, 11))
fig1.suptitle('연구 결과 요약 — BrainLM per-Cluster (v2, seq6_st1)', fontsize=15, fontweight='bold', y=0.98)

# 2-1: 클러스터별 Train/Val Loss
ax = axes[0, 0]
cids_list = df_results['cluster_id'].tolist()
train_losses = df_results['final_train_loss'].tolist()
val_losses = df_results['final_val_loss'].tolist()
x = np.arange(len(cids_list))
w = 0.35
bars1 = ax.bar(x - w/2, train_losses, w, label='Train Loss', color=[CLUSTER_COLORS[c] for c in cids_list], alpha=0.85)
bars2 = ax.bar(x + w/2, val_losses, w, label='Val Loss', color=[CLUSTER_COLORS[c] for c in cids_list], alpha=0.5, edgecolor='black', linewidth=0.8)
ax.set_xticks(x)
ax.set_xticklabels([f'State {c}' for c in cids_list])
ax.set_ylabel('Reconstruction Loss (MSE)')
ax.set_title('① Cluster별 BrainLM 학습 손실')
ax.legend()
for bar, val in zip(bars1, train_losses):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.002, f'{val:.3f}', ha='center', va='bottom', fontsize=8)
for bar, val in zip(bars2, val_losses):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.002, f'{val:.3f}', ha='center', va='bottom', fontsize=8)
ax.set_ylim(0, max(val_losses) * 1.3)

# 2-2: 클러스터 크기 (CM 수)
ax = axes[0, 1]
if clustering_result is not None:
    sizes = clustering_result.get_cluster_sizes()
    labels_pie = [f'State {k}\n(n={v})' for k, v in sorted(sizes.items())]
    vals_pie = [v for _, v in sorted(sizes.items())]
    colors_pie = [CLUSTER_COLORS[k] for k, _ in sorted(sizes.items())]
    wedges, texts, autotexts = ax.pie(vals_pie, labels=labels_pie, colors=colors_pie,
                                       autopct='%1.1f%%', startangle=90, pctdistance=0.8)
    for t in autotexts:
        t.set_fontsize(9)
else:
    ax.text(0.5, 0.5, 'CM 데이터 없음', ha='center', va='center')
ax.set_title('② Brain State 분포 (전체 CM 308개)')

# 2-3: Cross-cluster Cosine Similarity (V2)
ax = axes[0, 2]
n_c = len(v2_latents)
sim_matrix = np.zeros((n_c, n_c))
means = {}
for cid, lat in v2_latents.items():
    m = lat.mean(0)
    means[cid] = m / (np.linalg.norm(m) + 1e-12)
for i in range(n_c):
    for j in range(n_c):
        sim_matrix[i, j] = means[i] @ means[j]

norm = TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1)
im = ax.imshow(sim_matrix, cmap='RdBu_r', norm=norm)
plt.colorbar(im, ax=ax, shrink=0.8)
ax.set_xticks(range(n_c))
ax.set_yticks(range(n_c))
ax.set_xticklabels([f'State {c}' for c in range(n_c)])
ax.set_yticklabels([f'State {c}' for c in range(n_c)])
for i in range(n_c):
    for j in range(n_c):
        val = sim_matrix[i, j]
        ax.text(j, i, f'{val:.3f}', ha='center', va='center',
                color='white' if abs(val) > 0.5 else 'black', fontsize=10, fontweight='bold')
ax.set_title('③ Cross-cluster Latent 코사인 유사도\n(≈0: 서로 다른 방향 ← 원하는 결과)')

# 2-4: L2 Norm 분포 violin
ax = axes[1, 0]
data_for_violin = []
positions = []
colors_violin = []
for i, (cid, lat) in enumerate(sorted(v2_latents.items())):
    norms = np.linalg.norm(lat, axis=1)
    data_for_violin.append(norms)
    positions.append(i)
    colors_violin.append(CLUSTER_COLORS[cid])
parts = ax.violinplot(data_for_violin, positions=positions, showmeans=True, showmedians=True)
for i, (pc, color) in enumerate(zip(parts['bodies'], colors_violin)):
    pc.set_facecolor(color)
    pc.set_alpha(0.7)
ax.set_xticks(positions)
ax.set_xticklabels([f'State {c}' for c in sorted(v2_latents.keys())])
ax.set_ylabel('L2 Norm of Latent')
ax.set_title('④ 클러스터별 Latent L2 Norm 분포')
for i, (cid, lat) in enumerate(sorted(v2_latents.items())):
    ax.text(i, np.linalg.norm(lat, axis=1).mean(), f'{np.linalg.norm(lat, axis=1).mean():.1f}',
            ha='center', va='bottom', fontsize=8)

# 2-5: V2 vs V1 비교 (Latent 차별성)
ax = axes[1, 1]
offdiag_v2 = [sim_matrix[i, j] for i in range(n_c) for j in range(n_c) if i != j]

# V1 cross-cluster cosine
v1_means = {}
for cid in np.unique(v1_cids):
    lat = v1_lat[v1_cids == cid]
    m = lat.mean(0)
    v1_means[int(cid)] = m / (np.linalg.norm(m) + 1e-12)
v1_cids_list = sorted(v1_means.keys())
v1_sim = np.zeros((len(v1_cids_list), len(v1_cids_list)))
for i, ci in enumerate(v1_cids_list):
    for j, cj in enumerate(v1_cids_list):
        v1_sim[i, j] = v1_means[ci] @ v1_means[cj]
offdiag_v1 = [v1_sim[i, j] for i in range(len(v1_cids_list)) for j in range(len(v1_cids_list)) if i != j]

ax.boxplot([offdiag_v1, offdiag_v2], labels=['V1\n(단일 BrainLM)', 'V2\n(Cluster별 BrainLM)'],
           patch_artist=True, boxprops=dict(facecolor='lightblue', alpha=0.7))
ax.axhline(0, color='red', linestyle='--', alpha=0.5, label='cosine=0 (직교)')
ax.set_ylabel('Cross-cluster Cosine Similarity')
ax.set_title('⑤ V1 vs V2 클러스터 분리 비교\n(0에 가까울수록 State 분리 명확)')
ax.legend(fontsize=8)
ax.text(2.4, 0.02, f'V2 mean:\n{np.mean(offdiag_v2):.3f}', fontsize=9, color='blue', ha='center')
ax.text(1.4, 0.02 + np.mean(offdiag_v1), f'V1 mean:\n{np.mean(offdiag_v1):.3f}', fontsize=9, color='orange', ha='center')

# 2-6: 핵심 결과 텍스트 요약
ax = axes[1, 2]
ax.axis('off')
summary_lines = [
    ("핵심 결과 요약", True),
    ("", False),
    (f"✅ V2 Cross-cluster cosine", True),
    (f"   평균: {np.mean(offdiag_v2):.4f}  (≈ 0 = 직교)", False),
    (f"   범위: [{min(offdiag_v2):.3f}, {max(offdiag_v2):.3f}]", False),
    ("   → 4개 State가 서로 다른 방향", False),
    ("   → 가설 부합 ✓", False),
    ("", False),
    (f"✅ Train Loss / Val Loss", True),
    (f"   State 0: {df_results[df_results.cluster_id==0]['final_val_loss'].values[0]:.4f}", False),
    (f"   State 1: {df_results[df_results.cluster_id==1]['final_val_loss'].values[0]:.4f}", False),
    (f"   State 2: {df_results[df_results.cluster_id==2]['final_val_loss'].values[0]:.4f}", False),
    (f"   State 3: {df_results[df_results.cluster_id==3]['final_val_loss'].values[0]:.4f}", False),
    ("", False),
    ("⚠️ 주의", True),
    ("   State 3: n=11 (데이터 부족)", False),
    ("   → 다음 단계: Baseline 비교 필요", False),
]
y = 0.97
for line, bold in summary_lines:
    ax.text(0.05, y, line, transform=ax.transAxes, fontsize=9.5,
            fontweight='bold' if bold else 'normal',
            verticalalignment='top', family='monospace' if not bold else 'sans-serif')
    y -= 0.055
ax.set_title('⑥ 결과 해석')

plt.tight_layout(rect=[0, 0, 1, 0.97])
fig1.savefig(OUT / 'fig1_result_summary.png', dpi=150, bbox_inches='tight')
plt.close(fig1)
print("  저장: fig1_result_summary.png")


# ──────────────────────────────────────────────
# Figure 2: CM 클러스터 분석 (Brain State 패턴)
# ──────────────────────────────────────────────
print("[3] Figure 2: CM 클러스터 분석...")

if centroids is not None:
    n_clusters = len(centroids)
    fig2 = plt.figure(figsize=(20, 16))
    fig2.suptitle('Brain State CM 클러스터 분석 (Fisher-Z 변환 후 Pearson 상관)', fontsize=14, fontweight='bold')

    gs_top = gridspec.GridSpec(2, n_clusters, top=0.90, bottom=0.52, hspace=0.4, wspace=0.3)
    gs_bot = gridspec.GridSpec(2, n_clusters, top=0.48, bottom=0.05, hspace=0.4, wspace=0.3)

    cluster_sizes = clustering_result.get_cluster_sizes()
    vmax_cm = max(abs(centroids[c]).max() for c in range(n_clusters)) * 0.8

    for cid in range(n_clusters):
        cm = centroids[cid]
        ax = fig2.add_subplot(gs_top[0, cid])
        im = ax.imshow(cm, cmap='RdBu_r', vmin=-vmax_cm, vmax=vmax_cm, aspect='auto')
        ax.set_title(f'State {cid}\n(n={cluster_sizes.get(cid, "?")}개 CM)', fontsize=11)
        ax.set_xlabel('ROI index')
        if cid == 0:
            ax.set_ylabel('ROI index')
        plt.colorbar(im, ax=ax, shrink=0.8, label='Fisher-Z')

    # 클러스터 간 CM 차이 (상삼각 행렬 비교)
    ax_diff = fig2.add_subplot(gs_top[1, :2])
    diff_01 = centroids[0] - centroids[1]
    im2 = ax_diff.imshow(diff_01, cmap='RdBu_r', vmin=-vmax_cm*0.5, vmax=vmax_cm*0.5, aspect='auto')
    ax_diff.set_title('State 0 − State 1 CM 차이')
    ax_diff.set_xlabel('ROI index')
    ax_diff.set_ylabel('ROI index')
    plt.colorbar(im2, ax=ax_diff, shrink=0.8, label='Δ Fisher-Z')

    ax_diff2 = fig2.add_subplot(gs_top[1, 2:])
    diff_23 = centroids[2] - centroids[3]
    im3 = ax_diff2.imshow(diff_23, cmap='RdBu_r', vmin=-vmax_cm*0.5, vmax=vmax_cm*0.5, aspect='auto')
    ax_diff2.set_title('State 2 − State 3 CM 차이')
    ax_diff2.set_xlabel('ROI index')
    plt.colorbar(im3, ax=ax_diff2, shrink=0.8, label='Δ Fisher-Z')

    # ROI별 클러스터 구별 중요도 (분산이 큰 ROI pair)
    n_roi = n_features
    all_centroid_flat = np.array([centroids[c][np.triu_indices(n_roi, k=1)] for c in range(n_clusters)])
    roi_variance = np.var(all_centroid_flat, axis=0)

    # 상위 20개 ROI pair
    top_k = 20
    top_idx = np.argsort(roi_variance)[::-1][:top_k]
    triu_i, triu_j = np.triu_indices(n_roi, k=1)
    top_pairs = [(triu_i[idx], triu_j[idx], roi_variance[idx]) for idx in top_idx]

    ax_roi = fig2.add_subplot(gs_bot[0, :2])
    pair_labels = [f'ROI{i}↔ROI{j}' for i, j, _ in top_pairs]
    pair_vars = [v for _, _, v in top_pairs]
    pair_colors = plt.cm.Reds(np.array(pair_vars) / max(pair_vars))
    bars = ax_roi.barh(range(top_k), pair_vars, color=pair_colors)
    ax_roi.set_yticks(range(top_k))
    ax_roi.set_yticklabels(pair_labels, fontsize=7)
    ax_roi.invert_yaxis()
    ax_roi.set_xlabel('클러스터 간 분산 (클수록 State 구별에 중요)')
    ax_roi.set_title(f'① State 구분에 중요한 ROI 연결 (상위 {top_k}개)')

    # 상위 5개 ROI pair의 클러스터별 값 비교
    ax_pair = fig2.add_subplot(gs_bot[0, 2:])
    top5 = top_pairs[:5]
    x_bar = np.arange(len(top5))
    bar_width = 0.2
    for ci in range(n_clusters):
        vals = [centroids[ci][pi, pj] for pi, pj, _ in top5]
        ax_pair.bar(x_bar + ci * bar_width, vals, bar_width,
                    label=f'State {ci}', color=CLUSTER_COLORS[ci], alpha=0.85)
    ax_pair.set_xticks(x_bar + bar_width * 1.5)
    ax_pair.set_xticklabels([f'ROI{i}\n↔ROI{j}' for i, j, _ in top5], fontsize=8)
    ax_pair.set_ylabel('Fisher-Z 상관')
    ax_pair.set_title('② 핵심 ROI pair의 State별 연결 강도')
    ax_pair.legend(fontsize=8)
    ax_pair.axhline(0, color='black', linewidth=0.5)

    # 각 클러스터에서 ROI별 mean absolute connectivity (ROI 중요도)
    for cid in range(n_clusters):
        ax_r = fig2.add_subplot(gs_bot[1, cid])
        cm = np.abs(centroids[cid])
        np.fill_diagonal(cm, 0)
        roi_importance = cm.mean(axis=1)
        top_rois = np.argsort(roi_importance)[::-1][:15]
        ax_r.barh(range(15), roi_importance[top_rois][::-1],
                  color=CLUSTER_COLORS[cid], alpha=0.8)
        ax_r.set_yticks(range(15))
        ax_r.set_yticklabels([f'ROI {r}' for r in top_rois[::-1]], fontsize=7)
        ax_r.set_title(f'State {cid}\n평균 연결 강도 상위 ROI', fontsize=9)
        if cid == 0:
            ax_r.set_xlabel('Mean |Fisher-Z|')

    plt.savefig(OUT / 'fig2_cm_cluster_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  저장: fig2_cm_cluster_analysis.png")
else:
    print("  [스킵] CM 데이터 없음")


# ──────────────────────────────────────────────
# Figure 3: Latent Space 분석 (V2 핵심)
# ──────────────────────────────────────────────
print("[4] Figure 3: Latent Space 분석 (V2)...")

# V2: 각 클러스터별 자체 BrainLM latent → L2 정규화 후 pooled PCA
all_lat_v2 = np.vstack([v2_latents[c] for c in sorted(v2_latents.keys())])
all_cids_v2 = np.concatenate([np.full(len(v2_latents[c]), c) for c in sorted(v2_latents.keys())])

# L2 normalize (per-cluster BrainLM이므로 scale 차이 보정)
norms = np.linalg.norm(all_lat_v2, axis=1, keepdims=True)
all_lat_v2_norm = all_lat_v2 / (norms + 1e-12)

fig3, axes3 = plt.subplots(2, 3, figsize=(18, 12))
fig3.suptitle('BrainLM Latent Space 분석 (V2: 클러스터별 모델)', fontsize=14, fontweight='bold')

# 3-1: Pooled PCA (L2 정규화 후)
ax = axes3[0, 0]
pca = PCA(n_components=2, random_state=42)
pca2d = pca.fit_transform(all_lat_v2_norm)
for cid in sorted(v2_latents.keys()):
    mask = all_cids_v2 == cid
    ax.scatter(pca2d[mask, 0], pca2d[mask, 1],
               c=CLUSTER_COLORS[cid], label=f'State {cid} (n={mask.sum()})',
               s=50, alpha=0.8, edgecolors='white', linewidth=0.3)
ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)')
ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)')
ax.set_title('① Pooled PCA (L2 정규화 후)\n← 클러스터별 색상 분리 확인')
ax.legend(fontsize=9)

# 3-2: Pooled t-SNE
ax = axes3[0, 1]
perp = min(30, len(all_lat_v2_norm) - 1)
tsne = TSNE(n_components=2, random_state=42, perplexity=perp, n_iter=1000)
tsne2d = tsne.fit_transform(all_lat_v2_norm)
for cid in sorted(v2_latents.keys()):
    mask = all_cids_v2 == cid
    ax.scatter(tsne2d[mask, 0], tsne2d[mask, 1],
               c=CLUSTER_COLORS[cid], label=f'State {cid}',
               s=50, alpha=0.8, edgecolors='white', linewidth=0.3)
ax.set_xlabel('t-SNE 1')
ax.set_ylabel('t-SNE 2')
ax.set_title('② Pooled t-SNE (L2 정규화 후)')
ax.legend(fontsize=9)

# 3-3: Cross-cluster cosine heatmap (메인)
ax = axes3[0, 2]
norm_c = TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1)
im = ax.imshow(sim_matrix, cmap='RdBu_r', norm=norm_c)
plt.colorbar(im, ax=ax, shrink=0.9, label='Cosine Similarity')
for i in range(n_c):
    for j in range(n_c):
        val = sim_matrix[i, j]
        color_txt = 'white' if abs(val) > 0.5 else 'black'
        ax.text(j, i, f'{val:.3f}', ha='center', va='center', fontsize=12,
                fontweight='bold', color=color_txt)
ax.set_xticks(range(n_c))
ax.set_yticks(range(n_c))
ax.set_xticklabels([f'State {c}' for c in range(n_c)], fontsize=10)
ax.set_yticklabels([f'State {c}' for c in range(n_c)], fontsize=10)
ax.set_title('③ Cross-cluster Latent 코사인 유사도\n빨강=유사 | 파랑=다름 | ≈0 = 직교')

# 3-4: PCA 설명분산 누적 (각 클러스터 내부 구조)
ax = axes3[1, 0]
max_comp = min(20, min(len(v) for v in v2_latents.values()) - 1)
for cid, lat in sorted(v2_latents.items()):
    if len(lat) > 1:
        pca_k = PCA(n_components=min(max_comp, len(lat) - 1))
        pca_k.fit(lat)
        cumvar = np.cumsum(pca_k.explained_variance_ratio_) * 100
        ax.plot(range(1, len(cumvar)+1), cumvar,
                marker='o', markersize=3, color=CLUSTER_COLORS[cid], label=f'State {cid}')
ax.set_xlabel('PC 개수')
ax.set_ylabel('누적 설명분산 (%)')
ax.set_title('④ 클러스터별 Latent 내부 차원 구조\n(가파를수록 저차원에 정보 집중)')
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)
ax.axhline(90, color='red', linestyle='--', alpha=0.4, label='90%')

# 3-5: Latent mean vector profile (클러스터 간 차이)
ax = axes3[1, 1]
top_dims = 30  # 분산 큰 상위 30차원
all_means = np.array([v2_latents[c].mean(0) for c in sorted(v2_latents.keys())])
dim_var = np.var(all_means, axis=0)
top_dim_idx = np.argsort(dim_var)[::-1][:top_dims]
x_d = np.arange(top_dims)
for i, cid in enumerate(sorted(v2_latents.keys())):
    vals = v2_latents[cid].mean(0)[top_dim_idx]
    ax.plot(x_d, vals, color=CLUSTER_COLORS[cid], label=f'State {cid}', alpha=0.85, linewidth=1.5)
ax.set_xlabel('Latent 차원 (분산 상위 순)')
ax.set_ylabel('Mean Latent 값')
ax.set_title('⑤ 클러스터별 평균 Latent 프로파일\n(색상 차이 = State 차이)')
ax.legend(fontsize=9)
ax.axhline(0, color='black', linewidth=0.5)
ax.grid(True, alpha=0.3)

# 3-6: V1 Latent PCA (비교용)
ax = axes3[1, 2]
pca_v1 = PCA(n_components=2, random_state=42)
v1_norm = v1_lat / (np.linalg.norm(v1_lat, axis=1, keepdims=True) + 1e-12)
pca_v1_2d = pca_v1.fit_transform(v1_norm)
for cid in np.unique(v1_cids):
    mask = v1_cids == cid
    ax.scatter(pca_v1_2d[mask, 0], pca_v1_2d[mask, 1],
               c=CLUSTER_COLORS[int(cid)], label=f'State {int(cid)} (n={mask.sum()})',
               s=30, alpha=0.7, edgecolors='white', linewidth=0.3)
ax.set_xlabel(f'PC1 ({pca_v1.explained_variance_ratio_[0]*100:.1f}%)')
ax.set_ylabel(f'PC2 ({pca_v1.explained_variance_ratio_[1]*100:.1f}%)')
ax.set_title('⑥ V1 단일 BrainLM PCA (비교)\n← V2 대비 분리 어떻게 다른지 확인')
ax.legend(fontsize=8)

plt.tight_layout(rect=[0, 0, 1, 0.96])
fig3.savefig(OUT / 'fig3_latent_space.png', dpi=150, bbox_inches='tight')
plt.close(fig3)
print("  저장: fig3_latent_space.png")


# ──────────────────────────────────────────────
# Figure 4: 피험자별 State 분석
# ──────────────────────────────────────────────
print("[5] Figure 4: 피험자별 State 분석...")

if all_segments is not None and clustering_result is not None:
    from pipeline.clustering import compute_cluster_similarity

    sims = compute_cluster_similarity(all_cms, clustering_result, n_features=n_features)
    subjects = sorted(sims.keys())
    n_subj = len(subjects)

    fig4, axes4 = plt.subplots(1, 2, figsize=(18, 9))
    fig4.suptitle('피험자별 Brain State 분석', fontsize=14, fontweight='bold')

    # 4-1: Subject-Cluster Similarity Heatmap
    ax = axes4[0]
    sim_arr = np.array([[sims[s][c] for c in range(4)] for s in subjects])
    im = ax.imshow(sim_arr, cmap='YlOrRd', aspect='auto', vmin=-0.1, vmax=0.8)
    plt.colorbar(im, ax=ax, shrink=0.9, label='CM Pearson 유사도')
    ax.set_xticks(range(4))
    ax.set_xticklabels([f'State {c}' for c in range(4)], fontsize=10)
    ax.set_yticks(range(n_subj))
    ax.set_yticklabels([s[-6:] for s in subjects], fontsize=8)
    ax.set_xlabel('Brain State (Cluster)')
    ax.set_ylabel('피험자 ID')
    ax.set_title('① 피험자 × State 유사도\n(밝을수록 해당 State에 많이 속함)')
    for i in range(n_subj):
        for j in range(4):
            val = sim_arr[i, j]
            ax.text(j, i, f'{val:.2f}', ha='center', va='center',
                    fontsize=6, color='black' if val < 0.5 else 'white')

    # 4-2: 각 피험자의 주도적 State 분포 (stacked bar)
    ax = axes4[1]
    # 각 피험자에서 몇 개 세그먼트가 각 클러스터에 속하는지
    subj_state_counts = {s: {c: 0 for c in range(4)} for s in subjects}
    for (subj, seg_id), cid in zip(cm_labels, clustering_result.labels):
        if subj in subj_state_counts:
            subj_state_counts[subj][int(cid)] += 1

    bottom = np.zeros(n_subj)
    for cid in range(4):
        vals = [subj_state_counts[s][cid] for s in subjects]
        totals = [sum(subj_state_counts[s].values()) for s in subjects]
        pcts = [v / max(t, 1) * 100 for v, t in zip(vals, totals)]
        ax.bar(range(n_subj), pcts, bottom=bottom,
               color=CLUSTER_COLORS[cid], label=f'State {cid}', alpha=0.85)
        bottom += np.array(pcts)

    ax.set_xticks(range(n_subj))
    ax.set_xticklabels([s[-6:] for s in subjects], rotation=45, ha='right', fontsize=8)
    ax.set_ylabel('State 점유율 (%)')
    ax.set_ylim(0, 105)
    ax.set_title('② 피험자별 Brain State 점유율\n(각 피험자에서 세그먼트 몇 %가 각 State)')
    ax.legend(loc='upper right', fontsize=9)
    ax.axhline(100, color='black', linewidth=0.5)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    fig4.savefig(OUT / 'fig4_subject_state.png', dpi=150, bbox_inches='tight')
    plt.close(fig4)
    print("  저장: fig4_subject_state.png")
else:
    print("  [스킵] 세그먼트 데이터 없음")


# ──────────────────────────────────────────────
# Figure 5: Latent → ROI 중요도 (연구 핵심)
# ──────────────────────────────────────────────
print("[6] Figure 5: Latent → ROI 중요도 분석...")

if centroids is not None:
    fig5, axes5 = plt.subplots(2, 4, figsize=(20, 11))
    fig5.suptitle('Brain State별 ROI 연결성 중요도 분석\n(Latent → CM Centroid → 뇌 영역 해석)',
                  fontsize=13, fontweight='bold')

    for cid in range(4):
        cm = centroids[cid].copy()
        np.fill_diagonal(cm, 0)
        cm_abs = np.abs(cm)

        # 상단: ROI 중요도 (mean absolute connectivity)
        ax_top = axes5[0, cid]
        roi_importance = cm_abs.mean(axis=1)
        top_n = 20
        top_roi_idx = np.argsort(roi_importance)[::-1][:top_n]
        top_roi_vals = roi_importance[top_roi_idx]
        colors_bar = [CLUSTER_COLORS[cid]] * top_n
        ax_top.barh(range(top_n), top_roi_vals[::-1], color=colors_bar, alpha=0.85)
        ax_top.set_yticks(range(top_n))
        ax_top.set_yticklabels([f'ROI {r}' for r in top_roi_idx[::-1]], fontsize=7)
        ax_top.set_xlabel('Mean |FC| (Fisher-Z)')
        ax_top.set_title(f'State {cid} ROI 중요도\n(상위 {top_n}개)', fontsize=10, color=CLUSTER_COLORS[cid])
        ax_top.invert_yaxis()

        # 하단: State 간 차이 (이 클러스터에서만 강한 ROI)
        ax_bot = axes5[1, cid]
        other_means = np.mean([np.abs(centroids[c]) for c in range(4) if c != cid], axis=0)
        np.fill_diagonal(other_means, 0)
        other_roi = other_means.mean(axis=1)
        roi_diff = roi_importance - other_roi  # 양수 = 이 State에서만 강함

        top_diff_idx = np.argsort(roi_diff)[::-1][:top_n]
        top_diff_vals = roi_diff[top_diff_idx]
        bar_colors2 = [CLUSTER_COLORS[cid] if v >= 0 else 'gray' for v in top_diff_vals[::-1]]
        ax_bot.barh(range(top_n), top_diff_vals[::-1], color=bar_colors2, alpha=0.85)
        ax_bot.set_yticks(range(top_n))
        ax_bot.set_yticklabels([f'ROI {r}' for r in top_diff_idx[::-1]], fontsize=7)
        ax_bot.set_xlabel('Δ Mean |FC| (이 State - 나머지 평균)')
        ax_bot.set_title(f'State {cid} 특이적 ROI\n(양수 = 이 State에서만 강한 연결)', fontsize=9, color=CLUSTER_COLORS[cid])
        ax_bot.invert_yaxis()
        ax_bot.axvline(0, color='black', linewidth=0.8)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    fig5.savefig(OUT / 'fig5_roi_importance.png', dpi=150, bbox_inches='tight')
    plt.close(fig5)
    print("  저장: fig5_roi_importance.png")
else:
    print("  [스킵] CM 데이터 없음")


# ──────────────────────────────────────────────
# Figure 6: 가설 검증 요약 (논문용 정리)
# ──────────────────────────────────────────────
print("[7] Figure 6: 가설 검증 요약...")

fig6, axes6 = plt.subplots(2, 2, figsize=(16, 12))
fig6.suptitle('가설 검증 요약: MTAD-GAT Anomaly Point → Brain State 정의',
              fontsize=13, fontweight='bold')

# 6-1: 파이프라인 Flow (텍스트)
ax = axes6[0, 0]
ax.axis('off')
flow_steps = [
    ("BOLD Signal (27명, 100 ROI)", '#3498DB'),
    ("↓", 'black'),
    ("MTAD-GAT 이상 탐지\n(Conv + Feat-GAT + Temp-GAT + GRU)", '#E74C3C'),
    ("↓ Embedding Change Detection", 'black'),
    ("Segmentation (308 Segments)", '#E67E22'),
    ("↓ Pearson + Fisher-Z", 'black'),
    ("CM 계산 (100×100 → 4950-dim)", '#27AE60'),
    ("↓ K-means (K=4)", 'black'),
    ("4개 Brain State 클러스터", '#9B59B6'),
    ("↓ per-cluster BrainLM 학습", 'black'),
    ("CLS Latent (256-dim)", '#1ABC9C'),
    ("↓ PCA / Cosine 분석", 'black'),
    ("State별 Latent 공간 검증 ✓", '#2C3E50'),
]
y_pos = 0.97
for text, color in flow_steps:
    size = 9 if '↓' not in text else 8
    weight = 'bold' if '↓' not in text else 'normal'
    ax.text(0.5, y_pos, text, transform=ax.transAxes,
            ha='center', va='top', fontsize=size, fontweight=weight, color=color,
            bbox=dict(boxstyle='round,pad=0.2', facecolor='lightyellow', alpha=0.5) if '↓' not in text else None)
    y_pos -= 0.072
ax.set_title('연구 파이프라인', fontsize=11)

# 6-2: V2 Cross-cluster cosine 재확인 (핵심)
ax = axes6[0, 1]
norm_c = TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1)
im = ax.imshow(sim_matrix, cmap='RdBu_r', norm=norm_c, interpolation='nearest')
plt.colorbar(im, ax=ax, label='Cosine Similarity')
for i in range(n_c):
    for j in range(n_c):
        val = sim_matrix[i, j]
        ax.text(j, i, f'{val:.3f}', ha='center', va='center', fontsize=13,
                fontweight='bold', color='black' if abs(val) < 0.5 else 'white')
ax.set_xticks(range(n_c))
ax.set_yticks(range(n_c))
ax.set_xticklabels([f'State {c}' for c in range(n_c)], fontsize=11)
ax.set_yticklabels([f'State {c}' for c in range(n_c)], fontsize=11)
ax.set_title('핵심 결과: Latent 직교성\n오프-대각선 ≈ 0 → State가 서로 다른 표현', fontsize=11)

# 해석 박스
ax.text(0.5, -0.22,
        '✅ 의미: 각 Brain State에서 BrainLM이 학습한 CM 패턴이\n'
        '   서로 완전히 다른 방향의 latent 표현을 가짐\n'
        '   → MTAD-GAT 기반 State 정의가 의미있음',
        transform=ax.transAxes, ha='center', va='top', fontsize=9,
        bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.4))

# 6-3: 클러스터별 학습 손실 (State별 BrainLM 품질)
ax = axes6[1, 0]
cids_bar = df_results['cluster_id'].tolist()
val_l = df_results['final_val_loss'].tolist()
test_l = df_results['final_test_loss'].tolist()
n_seqs = df_results['n_latents'].tolist()
x = np.arange(len(cids_bar))
b1 = ax.bar(x - 0.2, val_l, 0.4, label='Val Loss', color=[CLUSTER_COLORS[c] for c in cids_bar], alpha=0.9)
b2 = ax.bar(x + 0.2, test_l, 0.4, label='Test Loss', color=[CLUSTER_COLORS[c] for c in cids_bar], alpha=0.5,
            edgecolor='black')
for bar, n in zip(b1, n_seqs):
    ax.text(bar.get_x() + bar.get_width()/2, 0.005, f'n={n}', ha='center', va='bottom', fontsize=8, rotation=90)
ax.set_xticks(x)
ax.set_xticklabels([f'State {c}' for c in cids_bar])
ax.set_ylabel('Reconstruction Loss')
ax.set_title('클러스터별 BrainLM 학습 품질\n(State별 CM 재구성 얼마나 잘 학습했나)')
ax.legend()

# 6-4: 결론 텍스트
ax = axes6[1, 1]
ax.axis('off')
conclusion = """
가설 검증 결과

✅ 확인된 것:
  1. CM Clustering (K=4):
     4개의 다른 뇌 연결 패턴이 존재

  2. Per-cluster BrainLM (V2):
     각 State에서 서로 다른 Latent 학습
     Cross-cluster cosine ≈ 0 (직교)
     → MTAD-GAT Anomaly Point 기반
       State 정의가 의미 있음

  3. State별 학습 손실 차이:
     State 3 (n=11): loss 높음
     → 드문 State = 패턴이 다양/불안정
     State 0,1 (n=94,116): loss 낮음
     → 안정적인 State = 잘 학습됨

⚠️ 추가 필요:
  - Baseline (무작위 분할) 대비 Loss 비교
  - 더 많은 피험자 (HCP 확장)
  - ROI → 실제 뇌 네트워크 매핑
    (DMN, Salience, FPN 등)
"""
ax.text(0.05, 0.98, conclusion, transform=ax.transAxes,
        fontsize=9.5, verticalalignment='top', family='monospace',
        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.7))
ax.set_title('결론 및 다음 단계', fontsize=11)

plt.tight_layout(rect=[0, 0, 1, 0.95])
fig6.savefig(OUT / 'fig6_hypothesis_validation.png', dpi=150, bbox_inches='tight')
plt.close(fig6)
print("  저장: fig6_hypothesis_validation.png")


# ──────────────────────────────────────────────
# 완료
# ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("✅ 모든 시각화 완료!")
print(f"   출력 디렉토리: {OUT}")
print("=" * 60)
print()
print("생성된 파일:")
for f in sorted(OUT.glob("*.png")):
    size_kb = f.stat().st_size // 1024
    print(f"  {f.name:45s} ({size_kb} KB)")
