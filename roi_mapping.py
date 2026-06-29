"""
ROI 번호 → 해부학적 뇌 영역 매핑 및 시각화
============================================

데이터: HCP REST1_LR, Schaefer100 (7 Networks, cortex only)
ROI 인덱스 0~99  ↔  Schaefer 100 Parcels 레이블 1~100

레이블 형식: 7Networks_{반구}_{네트워크}_{번호}
  반구: LH (좌뇌) / RH (우뇌)
  네트워크: Vis / SomMot / DorsAttn / SalVentAttn / Limbic / Cont / Default

이 스크립트가 하는 일:
  1. ROI → 레이블 테이블 생성 및 CSV 저장
  2. 각 Brain State(V4 클러스터)의 State-specific ROI를 해부학적 이름으로 시각화
  3. 네트워크 수준 중요도 비교 (State별)
  4. LH/RH 비대칭성 분석
  5. 결과를 visualization_ver4/roi_mapping/ 에 저장
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from nilearn.datasets import fetch_atlas_schaefer_2018

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

OUT = ROOT / "visualization_ver4" / "roi_mapping"
OUT.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────
# 1. Schaefer 100 레이블 로드 및 파싱
# ─────────────────────────────────────────────────────────────────────
print("Schaefer 100 atlas 레이블 로드 중...")
atlas = fetch_atlas_schaefer_2018(n_rois=100, yeo_networks=7, resolution_mm=2, verbose=0)

# nilearn은 0번=Background 포함하여 101개 반환 → 인덱스 1~100이 실제 ROI
raw_labels = atlas["labels"]
raw_labels = [l.decode() if isinstance(l, bytes) else l for l in raw_labels]

# Background 제거 → 100개 ROI 레이블
roi_labels_full = [l for l in raw_labels if l != "Background"]
assert len(roi_labels_full) == 100, f"레이블 수 오류: {len(roi_labels_full)}"

# 레이블 파싱: "7Networks_LH_Vis_1" → (hemisphere, network, region_num, short_name)
def parse_label(label: str) -> dict:
    """'7Networks_LH_DorsAttn_Post_1' 같은 레이블을 분해."""
    parts = label.replace("7Networks_", "").split("_")
    hemisphere = parts[0]  # LH 또는 RH
    network = parts[1]     # Vis, SomMot, DorsAttn, SalVentAttn, Limbic, Cont, Default
    region_parts = parts[2:]  # 나머지 (서브영역 이름 + 번호)
    region_str = "_".join(region_parts)
    short = f"{hemisphere}-{network}-{region_str}"
    return {
        "hemisphere": hemisphere,
        "network": network,
        "region": region_str,
        "short_name": short,
        "full_label": label,
    }

roi_info = []
for idx, label in enumerate(roi_labels_full):
    info = parse_label(label)
    info["roi_index"] = idx      # 0-based (데이터 컬럼 인덱스)
    info["roi_number"] = idx + 1 # 1-based (Schaefer 번호)
    roi_info.append(info)

df_roi = pd.DataFrame(roi_info)
df_roi.to_csv(OUT / "schaefer100_roi_table.csv", index=False)
print(f"ROI 테이블 저장: {OUT / 'schaefer100_roi_table.csv'}")
print(df_roi.groupby("network")["roi_index"].count().rename("ROI 수"))

# 네트워크별 색상 (Yeo 7 Networks 표준 색상)
NETWORK_COLORS = {
    "Vis":         "#781286",   # 보라 — Visual
    "SomMot":      "#4682B4",   # 파랑 — Somatomotor
    "DorsAttn":    "#00760E",   # 초록 — Dorsal Attention
    "SalVentAttn": "#C43AFA",   # 분홍 — Salience/Ventral Attention
    "Limbic":      "#DCF8A4",   # 연두 — Limbic
    "Cont":        "#E69422",   # 주황 — Control (Frontoparietal)
    "Default":     "#CD3E4E",   # 빨강 — Default Mode
}
NETWORK_FULLNAME = {
    "Vis":         "Visual",
    "SomMot":      "Somatomotor",
    "DorsAttn":    "Dorsal Attention",
    "SalVentAttn": "Salience/Ventral Attn",
    "Limbic":      "Limbic",
    "Cont":        "Frontoparietal (Control)",
    "Default":     "Default Mode (DMN)",
}

# ROI 인덱스 → 네트워크 빠른 조회용
roi_to_network = {row["roi_index"]: row["network"] for _, row in df_roi.iterrows()}
roi_to_hemi    = {row["roi_index"]: row["hemisphere"] for _, row in df_roi.iterrows()}
roi_to_short   = {row["roi_index"]: row["short_name"] for _, row in df_roi.iterrows()}
roi_to_full    = {row["roi_index"]: row["full_label"] for _, row in df_roi.iterrows()}


# ─────────────────────────────────────────────────────────────────────
# 2. V4 클러스터링 결과 로드 (CM 중심값 + latent)
# ─────────────────────────────────────────────────────────────────────
from pipeline.clustering import (
    get_cluster_centroids,
    perform_clustering,
    compute_cluster_similarity,
)
from pipeline.connectivity import collect_all_cms_flat, compute_all_cms
from pipeline.segmentation import get_segment_statistics
import pickle

SEGMENT_CACHE = ROOT / "checkpoint" / "brainlm_v3" / "cache" / "all_segments.pkl"
K = 4
N_FEATURES = 100

print("\n세그먼트 캐시 로드 중...")
with open(SEGMENT_CACHE, "rb") as f:
    all_segments = pickle.load(f)

print("CM 계산 + 클러스터링 중...")
all_cms = compute_all_cms(all_segments, method="pearson", min_segment_len=10, use_fisher_z=True)
X_cm, cm_labels = collect_all_cms_flat(all_cms)

clustering_result = perform_clustering(
    X_cm, cm_labels, n_clusters=K,
    standardize=True, use_minibatch=True,
    n_init=4, max_iter=200, batch_size=256,
    skip_silhouette=True, random_state=42,
)
cluster_sizes = clustering_result.get_cluster_sizes()
centroids = get_cluster_centroids(clustering_result, n_features=N_FEATURES)
print(f"클러스터 크기: {cluster_sizes}")


# ─────────────────────────────────────────────────────────────────────
# 3. State별 ROI 중요도 계산 (CM 기반)
# ─────────────────────────────────────────────────────────────────────
def roi_importance_from_cm(centroid: np.ndarray) -> np.ndarray:
    """
    CM에서 각 ROI의 평균 |FC| 강도를 계산.
    대각선(자기 자신) 제외.
    반환: (100,) 배열
    """
    cm = np.abs(centroid.copy())
    np.fill_diagonal(cm, 0)
    return cm.mean(axis=1)

def state_specific_roi(cid: int, centroids: dict) -> np.ndarray:
    """
    해당 State에서 다른 State들 대비 특이적으로 강한 ROI 중요도 차이.
    반환: (100,) 배열 (양수 = 이 State에서만 강함)
    """
    own = roi_importance_from_cm(centroids[cid])
    others_list = [roi_importance_from_cm(centroids[c]) for c in centroids if c != cid]
    other_avg = np.mean(others_list, axis=0)
    return own - other_avg  # delta: 이 State에서 두드러지는 ROI

# 네트워크 수준 집계 함수
def network_importance(roi_scores: np.ndarray) -> pd.Series:
    """ROI 점수를 네트워크별로 평균."""
    net_scores: Dict[str, List[float]] = {}
    for roi_idx, score in enumerate(roi_scores):
        net = roi_to_network[roi_idx]
        net_scores.setdefault(net, []).append(score)
    return pd.Series({net: np.mean(vals) for net, vals in net_scores.items()})


# ─────────────────────────────────────────────────────────────────────
# Figure 1: 전체 100 ROI → 해부학적 분류 파이차트 + 막대
# ─────────────────────────────────────────────────────────────────────
print("\n[Figure 1] Schaefer100 구성 개요...")

fig1, axes = plt.subplots(1, 2, figsize=(16, 7))
fig1.suptitle("Schaefer 100 Parcels 구성\n(HCP REST1_LR 데이터 ROI 분류)", fontsize=13, fontweight="bold")

# 파이차트: 네트워크별 ROI 수
net_counts = df_roi.groupby("network")["roi_index"].count()
net_order = [n for n in NETWORK_COLORS if n in net_counts]
sizes = [net_counts[n] for n in net_order]
colors_pie = [NETWORK_COLORS[n] for n in net_order]
labels_pie = [f"{NETWORK_FULLNAME[n]}\n(n={net_counts[n]})" for n in net_order]
axes[0].pie(sizes, labels=labels_pie, colors=colors_pie, autopct="%1.0f%%",
            startangle=140, textprops={"fontsize": 9})
axes[0].set_title("네트워크별 ROI 구성 비율")

# 막대: LH/RH 반구별 네트워크 분포
lh_counts = df_roi[df_roi.hemisphere=="LH"].groupby("network")["roi_index"].count()
rh_counts = df_roi[df_roi.hemisphere=="RH"].groupby("network")["roi_index"].count()
x = np.arange(len(net_order))
w = 0.38
b1 = axes[1].bar(x - w/2, [lh_counts.get(n, 0) for n in net_order], w,
                 color=[NETWORK_COLORS[n] for n in net_order], alpha=0.9, label="LH (좌뇌)")
b2 = axes[1].bar(x + w/2, [rh_counts.get(n, 0) for n in net_order], w,
                 color=[NETWORK_COLORS[n] for n in net_order], alpha=0.5, edgecolor="black", label="RH (우뇌)")
axes[1].set_xticks(x)
axes[1].set_xticklabels([NETWORK_FULLNAME[n].replace(" ", "\n") for n in net_order], fontsize=8)
axes[1].set_ylabel("ROI 수")
axes[1].set_title("네트워크별 LH/RH 분포")
axes[1].legend()
axes[1].grid(axis="y", alpha=0.3)

plt.tight_layout(rect=[0, 0, 1, 0.94])
p = OUT / "fig1_schaefer100_overview.png"
fig1.savefig(p, dpi=150, bbox_inches="tight")
plt.close(fig1)
print(f"  저장: {p.name}")


# ─────────────────────────────────────────────────────────────────────
# Figure 2: State별 네트워크 수준 중요도 레이더 차트
# ─────────────────────────────────────────────────────────────────────
print("[Figure 2] 네트워크 수준 레이더 차트...")

CLUSTER_COLORS = ["#E74C3C", "#3498DB", "#2ECC71", "#F39C12"]
networks_ordered = list(NETWORK_COLORS.keys())  # 7개
N = len(networks_ordered)
angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
angles += angles[:1]  # 닫기

fig2, axes2 = plt.subplots(2, 2, figsize=(14, 12), subplot_kw=dict(polar=True))
fig2.suptitle("Brain State별 네트워크 수준 FC 중요도 (레이더 차트)\n"
              "각 꼭짓점 = 해당 네트워크 ROI들의 평균 |FC| 강도",
              fontsize=12, fontweight="bold")

for idx, cid in enumerate(range(K)):
    ax = axes2.flatten()[idx]
    if cid not in centroids:
        ax.set_title(f"State {cid}\n(스킵)")
        continue

    roi_scores = roi_importance_from_cm(centroids[cid])
    net_scores = network_importance(roi_scores)
    vals = [float(net_scores.get(n, 0)) for n in networks_ordered]
    vals += vals[:1]

    ax.plot(angles, vals, color=CLUSTER_COLORS[cid], linewidth=2, linestyle="solid")
    ax.fill(angles, vals, color=CLUSTER_COLORS[cid], alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([NETWORK_FULLNAME[n].replace(" ", "\n") for n in networks_ordered], fontsize=8)
    ax.set_title(f"State {cid}  (n={cluster_sizes.get(cid, '?')} 세그먼트)",
                 fontsize=11, color=CLUSTER_COLORS[cid], pad=15)
    ax.grid(True, alpha=0.3)

plt.tight_layout(rect=[0, 0, 1, 0.94])
p = OUT / "fig2_network_radar.png"
fig2.savefig(p, dpi=150, bbox_inches="tight")
plt.close(fig2)
print(f"  저장: {p.name}")


# ─────────────────────────────────────────────────────────────────────
# Figure 3: State별 State-specific ROI Top 20 (해부학적 이름 포함)
# ─────────────────────────────────────────────────────────────────────
print("[Figure 3] State-specific ROI 해부학적 이름 시각화...")

fig3, axes3 = plt.subplots(2, 2, figsize=(20, 18))
fig3.suptitle("Brain State별 특이적 ROI Top 20 (해부학적 영역명)\n"
              "기타 State 대비 연결 강도가 두드러지게 높은 ROI",
              fontsize=13, fontweight="bold")

for idx, cid in enumerate(range(K)):
    ax = axes3.flatten()[idx]
    if cid not in centroids:
        ax.text(0.5, 0.5, f"State {cid}\n데이터 없음",
                ha="center", va="center", transform=ax.transAxes, fontsize=14)
        ax.axis("off")
        continue

    delta = state_specific_roi(cid, centroids)
    top20_idx = np.argsort(delta)[::-1][:20]

    # 레이블, 색, 값 준비
    bar_labels = []
    bar_colors = []
    for roi_idx in top20_idx:
        net = roi_to_network[roi_idx]
        hemi = roi_to_hemi[roi_idx]
        full = roi_to_full[roi_idx]
        # 레이블: "ROI 7 | LH-Vis-7\n7Networks_LH_Vis_7"
        bar_labels.append(f"ROI{roi_idx:>3d} | {roi_to_short[roi_idx]}")
        bar_colors.append(NETWORK_COLORS.get(net, "#999999"))

    y = np.arange(len(top20_idx))
    ax.barh(y, delta[top20_idx][::-1] if False else delta[top20_idx],
            color=bar_colors, alpha=0.85, edgecolor="white", linewidth=0.5)

    # y축을 역순으로 (top ROI가 맨 위)
    ax.set_yticks(y)
    ax.set_yticklabels(bar_labels, fontsize=8, family="monospace")
    ax.invert_yaxis()
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Δ Mean |FC| (이 State − 다른 State 평균)")
    ax.set_title(f"State {cid}  |  n={cluster_sizes.get(cid, '?')} 세그먼트",
                 fontsize=12, color=CLUSTER_COLORS[cid], fontweight="bold")
    ax.grid(axis="x", alpha=0.3)

    # 네트워크 색상 범례
    legend_handles = [
        mpatches.Patch(color=NETWORK_COLORS[n], label=NETWORK_FULLNAME[n])
        for n in NETWORK_COLORS if n in [roi_to_network[r] for r in top20_idx]
    ]
    ax.legend(handles=legend_handles, fontsize=7, loc="lower right", framealpha=0.8)

plt.tight_layout(rect=[0, 0, 1, 0.95])
p = OUT / "fig3_state_specific_roi_anatomical.png"
fig3.savefig(p, dpi=150, bbox_inches="tight")
plt.close(fig3)
print(f"  저장: {p.name}")


# ─────────────────────────────────────────────────────────────────────
# Figure 4: 네트워크 수준 중요도 비교 막대 (4개 State 나란히)
# ─────────────────────────────────────────────────────────────────────
print("[Figure 4] State 간 네트워크 중요도 비교...")

fig4, ax4 = plt.subplots(figsize=(16, 7))
fig4.suptitle("Brain State별 네트워크 수준 FC 중요도 비교\n"
              "(각 State의 CM에서 해당 네트워크 ROI들의 평균 |FC|)",
              fontsize=12, fontweight="bold")

x = np.arange(len(networks_ordered))
bar_w = 0.18
trained_cids = [c for c in range(K) if c in centroids]

for i, cid in enumerate(trained_cids):
    roi_scores = roi_importance_from_cm(centroids[cid])
    net_scores = network_importance(roi_scores)
    vals = [float(net_scores.get(n, 0)) for n in networks_ordered]
    bars = ax4.bar(x + i * bar_w - bar_w * len(trained_cids) / 2,
                   vals, bar_w, label=f"State {cid} (n={cluster_sizes.get(cid,'?')})",
                   color=CLUSTER_COLORS[cid], alpha=0.85, edgecolor="white")

ax4.set_xticks(x)
ax4.set_xticklabels([f"{NETWORK_FULLNAME[n]}\n({net_counts.get(n, 0)} ROIs)"
                     for n in networks_ordered], fontsize=9)
ax4.set_ylabel("평균 |FC| 강도 (Fisher-Z)")
ax4.set_title("네트워크별 State 차이 — 막대가 높을수록 해당 State에서 그 네트워크가 강하게 활성화")
ax4.legend(fontsize=10)
ax4.grid(axis="y", alpha=0.3)

# 네트워크 컬러 배경 띠
for i, net in enumerate(networks_ordered):
    ax4.axvspan(i - 0.45, i + 0.45, color=NETWORK_COLORS[net], alpha=0.07, zorder=0)

plt.tight_layout(rect=[0, 0, 1, 0.93])
p = OUT / "fig4_network_comparison_bar.png"
fig4.savefig(p, dpi=150, bbox_inches="tight")
plt.close(fig4)
print(f"  저장: {p.name}")


# ─────────────────────────────────────────────────────────────────────
# Figure 5: LH/RH 비대칭성 분석 (State별)
# ─────────────────────────────────────────────────────────────────────
print("[Figure 5] LH/RH 비대칭성...")

fig5, axes5 = plt.subplots(1, 2, figsize=(16, 7))
fig5.suptitle("Brain State별 좌뇌(LH) / 우뇌(RH) FC 비대칭성\n"
              "양수 = LH 우세, 음수 = RH 우세",
              fontsize=12, fontweight="bold")

# 네트워크별 LH/RH 비대칭 (이 State에서)
lh_rois = df_roi[df_roi.hemisphere == "LH"]["roi_index"].values
rh_rois = df_roi[df_roi.hemisphere == "RH"]["roi_index"].values

for i, cid in enumerate(trained_cids):
    roi_scores = roi_importance_from_cm(centroids[cid])

    # 각 네트워크의 LH 평균 - RH 평균
    asym_net = {}
    for net in networks_ordered:
        lh_net = df_roi[(df_roi.hemisphere=="LH") & (df_roi.network==net)]["roi_index"].values
        rh_net = df_roi[(df_roi.hemisphere=="RH") & (df_roi.network==net)]["roi_index"].values
        lh_mean = roi_scores[lh_net].mean() if len(lh_net) > 0 else 0
        rh_mean = roi_scores[rh_net].mean() if len(rh_net) > 0 else 0
        asym_net[net] = lh_mean - rh_mean  # 양수 = LH 우세

    # 좌측 subplot: State별 비대칭 선 그래프
    ax = axes5[0]
    asym_vals = [asym_net[n] for n in networks_ordered]
    ax.plot(range(len(networks_ordered)), asym_vals,
            marker="o", label=f"State {cid}", color=CLUSTER_COLORS[cid], linewidth=2)

axes5[0].axhline(0, color="black", linewidth=0.8, linestyle="--")
axes5[0].fill_between(range(len(networks_ordered)), 0, 0, alpha=0)
axes5[0].set_xticks(range(len(networks_ordered)))
axes5[0].set_xticklabels([n for n in networks_ordered], rotation=30, ha="right", fontsize=9)
axes5[0].set_ylabel("LH − RH 평균 |FC|")
axes5[0].set_title("네트워크별 반구 비대칭성\n(위 = 좌뇌 우세, 아래 = 우뇌 우세)")
axes5[0].legend(fontsize=10)
axes5[0].grid(alpha=0.3)

# 우측: 전체 LH vs RH 산점도 (State 0 vs State 1 예시)
ax2 = axes5[1]
if len(trained_cids) >= 2:
    c0, c1 = trained_cids[0], trained_cids[1]
    s0 = roi_importance_from_cm(centroids[c0])
    s1 = roi_importance_from_cm(centroids[c1])
    for roi_idx in range(N_FEATURES):
        net = roi_to_network[roi_idx]
        hemi = roi_to_hemi[roi_idx]
        marker = "o" if hemi == "LH" else "^"
        ax2.scatter(s0[roi_idx], s1[roi_idx],
                    c=NETWORK_COLORS.get(net, "#aaa"), marker=marker,
                    s=60, alpha=0.75, edgecolors="white", linewidth=0.3)
    # 기준선 (x=y)
    lims = [min(s0.min(), s1.min()), max(s0.max(), s1.max())]
    ax2.plot(lims, lims, "k--", alpha=0.4, linewidth=1)
    ax2.set_xlabel(f"State {c0} ROI 중요도")
    ax2.set_ylabel(f"State {c1} ROI 중요도")
    ax2.set_title(f"State {c0} vs State {c1} ROI 중요도 산점도\n○ = LH, △ = RH")
    # 네트워크 범례
    net_patches = [mpatches.Patch(color=NETWORK_COLORS[n], label=NETWORK_FULLNAME[n])
                   for n in NETWORK_COLORS]
    lh_marker = plt.Line2D([0], [0], marker="o", color="gray", label="LH", linestyle="None")
    rh_marker = plt.Line2D([0], [0], marker="^", color="gray", label="RH", linestyle="None")
    ax2.legend(handles=net_patches + [lh_marker, rh_marker], fontsize=7,
               loc="upper left", framealpha=0.8, ncol=2)
    ax2.grid(alpha=0.3)

plt.tight_layout(rect=[0, 0, 1, 0.93])
p = OUT / "fig5_lh_rh_asymmetry.png"
fig5.savefig(p, dpi=150, bbox_inches="tight")
plt.close(fig5)
print(f"  저장: {p.name}")


# ─────────────────────────────────────────────────────────────────────
# Figure 6: CM Heatmap에 네트워크 경계선 추가 (해부학적 해석용)
# ─────────────────────────────────────────────────────────────────────
print("[Figure 6] 네트워크 경계선 포함 CM 히트맵...")

# 네트워크별 ROI 구간 (연속 블록이 됨 — Schaefer는 네트워크 순서대로 정렬)
net_boundaries = []
prev_net = None
start = 0
for idx in range(N_FEATURES):
    net = roi_to_network[idx]
    if net != prev_net:
        if prev_net is not None:
            net_boundaries.append((prev_net, start, idx - 1))
        start = idx
        prev_net = net
net_boundaries.append((prev_net, start, N_FEATURES - 1))

fig6, axes6 = plt.subplots(2, 2, figsize=(20, 18))
fig6.suptitle("Brain State별 CM (네트워크 경계선 포함)\n"
              "색 블록 = 네트워크 내부 연결 / 블록 사이 = 네트워크 간 연결",
              fontsize=12, fontweight="bold")

from matplotlib.colors import TwoSlopeNorm
vmax = max(np.abs(centroids[c]).max() for c in range(K) if c in centroids) * 0.7

for idx, cid in enumerate(range(K)):
    ax = axes6.flatten()[idx]
    if cid not in centroids:
        ax.text(0.5, 0.5, f"State {cid}\n데이터 없음", ha="center", va="center",
                transform=ax.transAxes, fontsize=14)
        ax.axis("off")
        continue

    cm = centroids[cid]
    im = ax.imshow(cm, cmap="RdBu_r", norm=TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax),
                   aspect="auto")
    plt.colorbar(im, ax=ax, shrink=0.75, label="Fisher-Z")

    # 네트워크 경계선 그리기
    for net_name, s, e in net_boundaries:
        mid = (s + e) / 2
        # 수직/수평 경계선
        if s > 0:
            ax.axhline(s - 0.5, color="white", linewidth=1.5, alpha=0.9)
            ax.axvline(s - 0.5, color="white", linewidth=1.5, alpha=0.9)
        # 네트워크 이름 레이블 (대각선 위)
        ax.text(mid, -2.5, net_name, ha="center", va="bottom", fontsize=6.5,
                color=NETWORK_COLORS.get(net_name, "black"), fontweight="bold",
                rotation=45, clip_on=False)
        ax.text(-3, mid, net_name, ha="right", va="center", fontsize=6.5,
                color=NETWORK_COLORS.get(net_name, "black"), fontweight="bold",
                clip_on=False)

    ax.set_title(f"State {cid}  (n={cluster_sizes.get(cid, '?')} 세그먼트)",
                 fontsize=11, color=CLUSTER_COLORS[cid], fontweight="bold")
    ax.set_xlabel("ROI (Schaefer100 순서)")
    ax.set_ylabel("ROI (Schaefer100 순서)")

plt.tight_layout(rect=[0, 0, 1, 0.95])
p = OUT / "fig6_cm_network_annotated.png"
fig6.savefig(p, dpi=150, bbox_inches="tight")
plt.close(fig6)
print(f"  저장: {p.name}")


# ─────────────────────────────────────────────────────────────────────
# ROI 매핑 테이블 요약 출력
# ─────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("ROI 매핑 완료 요약")
print("="*60)
print(df_roi[["roi_index", "hemisphere", "network", "short_name"]].head(15).to_string(index=False))
print(f"\n... 총 {len(df_roi)} ROI")
print(f"\n결과 저장 위치: {OUT}")
for f in sorted(OUT.glob("*.png")):
    print(f"  {f.name:45s} ({f.stat().st_size//1024} KB)")
print(f"  {'schaefer100_roi_table.csv':45s} ({(OUT/'schaefer100_roi_table.csv').stat().st_size//1024} KB)")
