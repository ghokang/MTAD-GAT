"""
=============================================================================
V4 Pipeline: per-cluster BrainLM with raw timeseries input
=============================================================================

핵심 아이디어:
  - V2의 '클러스터별 별도 BrainLM' 구조 유지
  - V3의 '원시 BOLD timeseries 입력' 방식 채택
  → CM은 오직 클러스터링(State 레이블 부여)에만 사용
  → BrainLM 학습에는 raw BOLD timeseries를 직접 입력

왜 timeseries를 넣어야 하는가 (교수님 피드백):
  CM = Pearson 상관 → 시간 축 정보(순서, 동역학)가 모두 소실
  Raw TS → BrainLM이 어떤 시간 패턴이 State를 구분하는지 직접 학습 가능
=============================================================================
"""

from __future__ import annotations

import json
import os
import pickle
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")  # GUI 없는 환경에서 PNG 저장용

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from matplotlib.colors import TwoSlopeNorm
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from torch.utils.data import DataLoader
from tqdm import tqdm

# ── 프로젝트 루트를 sys.path에 추가 ──────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# macOS에서 sklearn + torch 혼용 시 스레드 충돌 방지
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

from brainlm.ts_dataset import FeatureNormalizer, TSConcatDataset
from brainlm.ts_model import BrainLMTimeSeries, BrainLMTimeSeriesConfig
from brainlm.ts_train import extract_ts_latents, train_brainlm_ts
from pipeline.clustering import (
    get_cluster_centroids,       # 클러스터 중심 CM 추출
    perform_clustering,          # K-means 클러스터링
    compute_cluster_similarity,  # 피험자별 State 유사도
)
from pipeline.connectivity import (
    collect_all_cms_flat,   # 클러스터링용 flattened CM 수집 (상삼각 평탄화)
    compute_all_cms,        # 세그먼트 → CM 계산 (Pearson + Fisher-Z)
)
from pipeline.segmentation import get_segment_statistics
from pipeline.v3_sequences import (
    TSConcatExample,
    build_ts_concat_sequences,  # 클러스터별 TS 시퀀스 생성 (v3에서 재사용)
    count_by_cluster,
    split_examples,             # subject 단위 train/val/test 분할
    suggest_max_time_steps,
)

# ─────────────────────────────────────────────────────────────────────────────
# 설정값 (하이퍼파라미터)
# ─────────────────────────────────────────────────────────────────────────────
K = 4            # Brain State 클러스터 수 (CM K-means)
SEQ_LEN = 1      # 한 학습 예제에 사용할 세그먼트 수
                 # SEQ_LEN=1: 각 세그먼트(=CM 1개에 대응하는 raw TS)를 그대로 사용
                 # → 교수님 피드백의 핵심: "CM 만들 때 쓴 timeseries 자체를 입력"
                 # → 308 세그먼트 전체 활용 (SEQ_LEN=4면 소수 클러스터 데이터 부족)
STRIDE = 1       # 슬라이딩 윈도우 보폭 (SEQ_LEN=1이면 stride는 무관)
VAL_SPLIT = 0.15 # 검증 세트 비율 (subject 단위)
TEST_SPLIT = 0.15 # 테스트 세트 비율
MASK_RATIO = 0.15  # Masked Autoencoder 마스킹 비율 (15%)
MAX_EPOCHS = 50    # 최대 학습 에폭 수
PATIENCE = 10      # Early stopping 인내 횟수
BATCH_SIZE = 8     # 배치 크기
LR = 1e-4          # 학습률
USE_FISHER_Z = True  # CM에 Fisher-Z 변환 적용 여부 (클러스터링 품질 향상)

# 경로 설정
DATA_PATH = ROOT / "data" / "DATA"
RESULT_PATH = ROOT / "result"
SPLIT_DIR = DATA_PATH / "data_pre" / "split_info"
OUTPUT_PATH = ROOT / "visualization_ver4"
CHECKPOINT_PATH = ROOT / "checkpoint" / "brainlm_v4"
SEGMENT_CACHE = ROOT / "checkpoint" / "brainlm_v3" / "cache" / "all_segments.pkl"

OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
CHECKPOINT_PATH.mkdir(parents=True, exist_ok=True)

# 클러스터별 색상 (시각화 일관성)
CLUSTER_COLORS = ["#E74C3C", "#3498DB", "#2ECC71", "#F39C12"]

# 디바이스 선택 (GPU/MPS/CPU)
if torch.cuda.is_available():
    device = torch.device("cuda")
elif torch.backends.mps.is_available():
    device = torch.device("mps")
else:
    device = torch.device("cpu")

try:
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
except Exception:
    pass

print(f"device: {device}")
print(f"ROOT: {ROOT}")


# =============================================================================
# STAGE 1: 세그먼트 로드
# =============================================================================
# 이미 v3에서 MTAD-GAT embedding 변화 기반으로 세그먼트화된 결과를 재사용
# → 불필요한 재계산 없이 동일한 State 경계를 사용함
print("\n" + "="*60)
print("STAGE 1: 세그먼트 로드")
print("="*60)

if SEGMENT_CACHE.exists():
    print(f"  캐시에서 로드: {SEGMENT_CACHE}")
    with open(SEGMENT_CACHE, "rb") as f:
        all_segments = pickle.load(f)
else:
    # 캐시가 없으면 직접 세그먼테이션 실행 (시간 소요)
    print("  캐시 없음 → embedding 기반 세그먼테이션 실행...")
    from pipeline.segmentation_evaluation import segment_all_subjects_embedding
    MTAD_GAT_CHECKPOINT = ROOT / "checkpoint" / "global_checkpoint_iter_0.pkl"
    all_segments = segment_all_subjects_embedding(
        data_path=DATA_PATH,
        checkpoint_path=MTAD_GAT_CHECKPOINT,
        min_segment_len=30,
        window_size=64,
        split_dir=SPLIT_DIR,
        top_k=20,
        smooth_window=5,
        device=device,
        data_pre_path=SPLIT_DIR.parent,
        verbose=True,
    )

seg_stats = get_segment_statistics(all_segments)
n_subjects = len(all_segments)
n_segments = len(seg_stats)
print(f"  피험자 수: {n_subjects}, 총 세그먼트 수: {n_segments}")
print(f"  세그먼트 길이 분포: mean={seg_stats['length'].mean():.1f}, "
      f"min={seg_stats['length'].min()}, max={seg_stats['length'].max()}")


# =============================================================================
# STAGE 2: CM 계산 + K-means 클러스터링 (State 레이블 부여)
# =============================================================================
# CM은 BrainLM 입력이 아님!
# 오직 각 세그먼트가 어떤 Brain State에 해당하는지 레이블을 달기 위한 목적
print("\n" + "="*60)
print("STAGE 2: CM 계산 + Brain State 클러스터링")
print("="*60)

print("  Pearson 상관 CM 계산 중 (Fisher-Z 변환 적용)...")
all_cms = compute_all_cms(
    all_segments,
    method="pearson",
    min_segment_len=10,
    use_fisher_z=USE_FISHER_Z,  # Fisher-Z: 정규분포에 가깝게 변환 → KMeans 안정화
)

# CM을 (n_segments, 4950) 행렬로 평탄화 (상삼각 추출)
X_cm, cm_labels = collect_all_cms_flat(all_cms)
n_features = next(iter(all_cms.values()))[0].n_features  # = 100 (ROI 수)
print(f"  CM shape: {X_cm.shape}  (n_cms × 4950-dim flat)")

# K-means 클러스터링: 4개 Brain State 정의
print(f"  K-means 클러스터링 (K={K})...")
clustering_result = perform_clustering(
    X_cm,
    cm_labels,
    n_clusters=K,
    standardize=True,      # 클러스터링 전 표준화
    use_minibatch=True,    # 메모리 절약
    n_init=4,
    max_iter=200,
    batch_size=256,
    skip_silhouette=True,
    random_state=42,
)
cluster_sizes = clustering_result.get_cluster_sizes()
print(f"  클러스터 크기: {cluster_sizes}")

# CM 클러스터 중심 (각 State의 평균 FC 패턴)
centroids = get_cluster_centroids(clustering_result, n_features=n_features)


# =============================================================================
# STAGE 3: 클러스터별 Raw Timeseries 시퀀스 생성
# =============================================================================
# 핵심 차이점 (V2 vs V4):
#   V2: CM 시퀀스 → BrainLM 입력
#   V4: 같은 클러스터에 속하는 연속 세그먼트의 raw BOLD TS를 이어붙임
#
# 예시: Cluster 1에 속하는 Subject A의 세그먼트 [2, 3, 4, 5]가
#       모두 State 1이면 → 4개 raw TS concat → 하나의 학습 예제
print("\n" + "="*60)
print("STAGE 3: 클러스터별 Raw Timeseries 시퀀스 생성")
print("="*60)
print(f"  SEQ_LEN={SEQ_LEN} (세그먼트 {SEQ_LEN}개 이어붙임), STRIDE={STRIDE}")

# build_ts_concat_sequences: v3_sequences.py에 구현된 함수 재사용
# 같은 클러스터 내 연속 세그먼트 슬라이딩 윈도우 → TSConcatExample 목록 반환
all_ts_examples = build_ts_concat_sequences(
    all_segments=all_segments,
    cm_labels_list=cm_labels,                  # (subject_id, segment_id) → cluster 매핑
    cluster_labels_flat=clustering_result.labels,  # 각 CM의 클러스터 ID
    seq_len=SEQ_LEN,
    stride=STRIDE,
)
print(f"  전체 TS 예제 수: {len(all_ts_examples)}")
print(f"  클러스터별 예제 수: {count_by_cluster(all_ts_examples)}")

# subject 단위로 train/val/test 분할 (data leakage 방지)
# 같은 피험자의 데이터가 train/test에 동시에 들어가지 않도록
all_train_ex, all_val_ex, all_test_ex = split_examples(
    all_ts_examples,
    val_split=VAL_SPLIT,
    test_split=TEST_SPLIT,
    seed=42,
)
print(f"  전체 Train/Val/Test: {len(all_train_ex)}/{len(all_val_ex)}/{len(all_test_ex)}")


# =============================================================================
# STAGE 4: 클러스터별 BrainLM TS 학습
# =============================================================================
# V4의 핵심: 각 Brain State(클러스터)에 대해 독립적인 BrainLM을 학습
# → 각 State의 BOLD 시계열 동역학을 특화 학습
# → 클러스터별 latent 공간이 독립적으로 형성됨
print("\n" + "="*60)
print("STAGE 4: 클러스터별 BrainLM (Raw TS) 학습")
print("="*60)

# 결과 저장용 딕셔너리
v4_latents: Dict[int, np.ndarray] = {}    # {cluster_id: latent array}
v4_histories: Dict[int, dict] = {}        # {cluster_id: training history}
v4_results: List[dict] = []               # 학습 결과 요약

for cid in range(K):
    print(f"\n── Cluster {cid} (State {cid}) ──")

    # 이 클러스터에 해당하는 예제만 필터링
    train_c = [ex for ex in all_train_ex if ex.cluster_id == cid]
    val_c   = [ex for ex in all_val_ex   if ex.cluster_id == cid]
    test_c  = [ex for ex in all_test_ex  if ex.cluster_id == cid]

    print(f"  Train/Val/Test: {len(train_c)}/{len(val_c)}/{len(test_c)}")

    # 데이터가 너무 적으면 스킵 (정상적인 학습 불가)
    if len(train_c) < 2 or len(val_c) < 1:
        print(f"  [SKIP] 데이터 부족")
        v4_results.append({
            "cluster_id": cid, "status": "skipped",
            "n_train": len(train_c), "n_val": len(val_c), "n_test": len(test_c),
        })
        continue

    # 이 클러스터 전용 Normalizer: train 데이터의 mean/std로 정규화
    # → 각 State가 가진 BOLD 신호의 스케일 차이를 제거
    normalizer_c = FeatureNormalizer().fit(train_c)

    # 이 클러스터의 시계열 길이 분포에 맞는 max_time_steps 결정
    # (95th percentile, 최대 2048로 cap)
    max_T = suggest_max_time_steps(train_c, percentile=95.0, absolute_cap=2048)
    print(f"  max_time_steps: {max_T}")

    # DataLoader 생성 (mask_ratio=0은 latent 추출용, 학습에는 MASK_RATIO 사용)
    train_loader = DataLoader(
        TSConcatDataset(train_c, max_time_steps=max_T, mask_ratio=MASK_RATIO,
                        normalizer=normalizer_c, augment=True),
        batch_size=BATCH_SIZE, shuffle=True, num_workers=0,
    )
    val_loader = DataLoader(
        TSConcatDataset(val_c, max_time_steps=max_T, mask_ratio=MASK_RATIO,
                        normalizer=normalizer_c, augment=False),
        batch_size=BATCH_SIZE, shuffle=False, num_workers=0,
    )

    # BrainLM TS 모델 설정
    # 입력: (B, T, 100) — B개 배치, T 타임스텝, 100개 ROI
    # CLS 토큰 latent: 256-dim → 이것이 Brain State의 표현 벡터
    config_c = BrainLMTimeSeriesConfig(
        n_features=n_features,    # 100 ROI
        d_model=256,              # Transformer 내부 차원
        nhead=8,                  # Multi-head attention 헤드 수
        num_encoder_layers=4,     # Encoder layer 수
        num_decoder_layers=2,     # Decoder layer 수 (가벼운 decoder)
        dim_feedforward=1024,     # FFN 차원
        dropout=0.1,              # Dropout 비율
        max_time_steps=max_T,     # Positional encoding 최대 길이
        mask_ratio=MASK_RATIO,    # 마스킹 비율 (학습용)
    )

    ckpt_dir = CHECKPOINT_PATH / f"cluster_{cid}"

    # 학습 실행 (Early stopping: val_loss가 PATIENCE 에폭 동안 개선 없으면 중단)
    model_c, history_c = train_brainlm_ts(
        train_loader=train_loader,
        val_loader=val_loader,
        config=config_c,
        max_epochs=MAX_EPOCHS,
        lr=LR,
        patience=PATIENCE,
        checkpoint_dir=ckpt_dir,
        device=device,
    )
    v4_histories[cid] = history_c

    # Latent 추출: train + val + test 전체 (마스킹 없이)
    # → 시각화/분석용으로 모든 예제의 latent를 뽑음
    all_c = train_c + val_c + test_c
    extract_loader = DataLoader(
        TSConcatDataset(all_c, max_time_steps=max_T, mask_ratio=0.0,
                        normalizer=normalizer_c, augment=False),
        batch_size=BATCH_SIZE, shuffle=False, num_workers=0,
    )
    latents_c, _, _ = extract_ts_latents(model_c, extract_loader, device)
    v4_latents[cid] = latents_c
    print(f"  Latent shape: {latents_c.shape}")

    # 결과 저장
    v4_results.append({
        "cluster_id": cid,
        "status": "ok",
        "n_train": len(train_c),
        "n_val": len(val_c),
        "n_test": len(test_c),
        "n_latents": len(all_c),
        "max_time_steps": max_T,
        "final_train_loss": history_c["train_loss"][-1],
        "final_val_loss": history_c["val_loss"][-1],
        "n_epochs_trained": len(history_c["train_loss"]),
    })

    # 클러스터별 latent numpy 저장
    np.save(OUTPUT_PATH / f"latents_v4_cluster{cid}.npy", latents_c)
    with open(ckpt_dir / "normalizer.pkl", "wb") as f:
        pickle.dump(normalizer_c, f)

# 결과 DataFrame
df_results = pd.DataFrame(v4_results)
df_results.to_csv(OUTPUT_PATH / "v4_results.csv", index=False)
print(f"\n결과 요약:\n{df_results[['cluster_id','status','n_train','n_val','n_latents','final_train_loss','final_val_loss']].to_string()}")

# 학습된 클러스터만 추출
trained_cids = sorted([r["cluster_id"] for r in v4_results if r["status"] == "ok"])


# =============================================================================
# STAGE 5: Cross-cluster 분석
# =============================================================================
# 각 클러스터 latent의 평균 벡터가 서로 얼마나 다른 방향인지 측정
# 코사인 유사도 ≈ 0 → 직교 (완전히 다른 State 표현) ← 원하는 결과
print("\n" + "="*60)
print("STAGE 5: Cross-cluster 분석")
print("="*60)

# 평균 latent 벡터를 L2 정규화하여 방향만 비교
means_norm = {}
for cid in trained_cids:
    lat = v4_latents[cid]
    m = lat.mean(0)
    means_norm[cid] = m / (np.linalg.norm(m) + 1e-12)

n_trained = len(trained_cids)
sim_matrix = np.zeros((n_trained, n_trained))
for i, ci in enumerate(trained_cids):
    for j, cj in enumerate(trained_cids):
        sim_matrix[i, j] = float(means_norm[ci] @ means_norm[cj])

print("  Cross-cluster cosine similarity:")
df_sim = pd.DataFrame(
    sim_matrix,
    index=[f"State{c}" for c in trained_cids],
    columns=[f"State{c}" for c in trained_cids],
)
print(df_sim.round(4))
df_sim.to_csv(OUTPUT_PATH / "v4_cross_cluster_cosine.csv")

offdiag = [sim_matrix[i, j] for i in range(n_trained) for j in range(n_trained) if i != j]
if offdiag:
    print(f"\n  오프-대각 평균: {np.mean(offdiag):.4f}  (≈0 = 직교 = 원하는 결과)")
    print(f"  오프-대각 범위: [{min(offdiag):.4f}, {max(offdiag):.4f}]")
else:
    print(f"\n  [INFO] 학습된 클러스터가 1개 → 클러스터 간 비교 불가")


# =============================================================================
# STAGE 6: 종합 시각화 생성
# =============================================================================
print("\n" + "="*60)
print("STAGE 6: 시각화 생성")
print("="*60)


# ── 헬퍼: Figure 저장 ──────────────────────────────────────────────────────
def save_fig(fig: plt.Figure, name: str) -> Path:
    p = OUTPUT_PATH / name
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  저장: {p.name}")
    return p


# ────────────────────────────────────────────────────────────────────────────
# Figure 1: 학습 곡선 (클러스터별)
# → 각 State별 BrainLM이 raw TS를 얼마나 잘 학습했는지 확인
# ────────────────────────────────────────────────────────────────────────────
print("\n  [Figure 1] 학습 곡선...")
n_rows = (len(trained_cids) + 1) // 2
fig1, axes = plt.subplots(n_rows, 2, figsize=(14, 5 * n_rows))
axes = np.array(axes).flatten()
fig1.suptitle("V4: 클러스터별 BrainLM 학습 곡선 (Raw Timeseries 입력)", fontsize=14, fontweight="bold")

for i, cid in enumerate(trained_cids):
    ax = axes[i]
    h = v4_histories[cid]
    ep = range(1, len(h["train_loss"]) + 1)
    ax.plot(ep, h["train_loss"], label="Train Loss", color=CLUSTER_COLORS[cid], linewidth=2)
    ax.plot(ep, h["val_loss"], label="Val Loss", color=CLUSTER_COLORS[cid],
            linewidth=2, linestyle="--", alpha=0.8)
    best_ep = int(np.argmin(h["val_loss"])) + 1
    ax.axvline(best_ep, color="gray", linestyle=":", alpha=0.6, label=f"Best ep={best_ep}")
    ax.set_title(f"State {cid}  |  n_train={df_results[df_results.cluster_id==cid]['n_train'].values[0]}", fontsize=11)
    ax.set_xlabel("Epoch")
    ax.set_ylabel("MSE Loss")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    r = df_results[df_results.cluster_id == cid].iloc[0]
    ax.text(0.98, 0.95, f"best_val={min(h['val_loss']):.4f}",
            transform=ax.transAxes, ha="right", va="top", fontsize=9,
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.7))

# 빈 subplot 숨기기
for j in range(len(trained_cids), len(axes)):
    axes[j].axis("off")

plt.tight_layout(rect=[0, 0, 1, 0.96])
save_fig(fig1, "fig1_training_curves.png")


# ────────────────────────────────────────────────────────────────────────────
# Figure 2: Pooled PCA + t-SNE (L2 정규화 후)
# → V4 latent 공간에서 4개 State가 얼마나 분리되는지 시각화
# 핵심: per-cluster 모델이라 각자 다른 L2 norm을 가질 수 있음
#       → L2 정규화로 크기 차이를 제거하고 '방향'만 비교
# ────────────────────────────────────────────────────────────────────────────
print("  [Figure 2] Pooled PCA / t-SNE...")

# 모든 클러스터 latent를 합치고 L2 정규화
all_lat = np.vstack([v4_latents[c] for c in trained_cids])
all_cid_arr = np.concatenate([np.full(len(v4_latents[c]), c) for c in trained_cids])
norms = np.linalg.norm(all_lat, axis=1, keepdims=True)
all_lat_norm = all_lat / (norms + 1e-12)

fig2, axes2 = plt.subplots(1, 2, figsize=(16, 7))
fig2.suptitle("V4 Latent Space — Pooled (L2 정규화 후)\n클러스터별 분리 확인", fontsize=13, fontweight="bold")

# PCA: 선형 분리 확인
pca = PCA(n_components=2, random_state=42)
pca2d = pca.fit_transform(all_lat_norm)
ax = axes2[0]
for cid in trained_cids:
    m = all_cid_arr == cid
    ax.scatter(pca2d[m, 0], pca2d[m, 1], c=CLUSTER_COLORS[cid],
               label=f"State {cid} (n={m.sum()})", s=60, alpha=0.8,
               edgecolors="white", linewidth=0.4)
ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)")
ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)")
ax.set_title("Pooled PCA (L2 norm)")
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)

# t-SNE: 비선형 분리 확인
perp = min(30, len(all_lat_norm) - 1)
tsne = TSNE(n_components=2, random_state=42, perplexity=perp, n_iter=1000)
tsne2d = tsne.fit_transform(all_lat_norm)
ax = axes2[1]
for cid in trained_cids:
    m = all_cid_arr == cid
    ax.scatter(tsne2d[m, 0], tsne2d[m, 1], c=CLUSTER_COLORS[cid],
               label=f"State {cid}", s=60, alpha=0.8,
               edgecolors="white", linewidth=0.4)
ax.set_xlabel("t-SNE 1")
ax.set_ylabel("t-SNE 2")
ax.set_title("Pooled t-SNE (L2 norm)")
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)

plt.tight_layout(rect=[0, 0, 1, 0.94])
save_fig(fig2, "fig2_pooled_latent.png")


# ────────────────────────────────────────────────────────────────────────────
# Figure 3: Cross-cluster Cosine Heatmap + L2 Norm Violin
# → 핵심 가설 검증 지표
#   - Heatmap 오프-대각 ≈ 0 → State들이 완전히 다른 latent 방향
#   - L2 norm이 State마다 다름 → 각 State의 BOLD 신호 강도가 다름
# ────────────────────────────────────────────────────────────────────────────
print("  [Figure 3] Cosine 히트맵 + L2 Norm 분포...")

fig3, axes3 = plt.subplots(1, 2, figsize=(15, 6))
fig3.suptitle("V4 핵심 결과: Latent 직교성 및 크기 분포", fontsize=13, fontweight="bold")

# Cosine Heatmap
ax = axes3[0]
norm_c = TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1)
im = ax.imshow(sim_matrix, cmap="RdBu_r", norm=norm_c)
plt.colorbar(im, ax=ax, label="Cosine Similarity")
ax.set_xticks(range(n_trained))
ax.set_yticks(range(n_trained))
ax.set_xticklabels([f"State {c}" for c in trained_cids], fontsize=11)
ax.set_yticklabels([f"State {c}" for c in trained_cids], fontsize=11)
for i in range(n_trained):
    for j in range(n_trained):
        v = sim_matrix[i, j]
        ax.text(j, i, f"{v:.3f}", ha="center", va="center", fontsize=12,
                fontweight="bold", color="white" if abs(v) > 0.5 else "black")
mean_od = np.mean(offdiag)
ax.set_title(f"Cross-cluster Cosine (오프-대각 평균={mean_od:.4f})\n"
             f"{'✅ 직교 (≈0) — State 분리 성공' if abs(mean_od) < 0.3 else '⚠️ 분리 부족'}")

# L2 Norm Violin
ax = axes3[1]
data_violin = [np.linalg.norm(v4_latents[c], axis=1) for c in trained_cids]
parts = ax.violinplot(data_violin, positions=range(len(trained_cids)),
                      showmeans=True, showmedians=True)
for i, (pc, cid) in enumerate(zip(parts["bodies"], trained_cids)):
    pc.set_facecolor(CLUSTER_COLORS[cid])
    pc.set_alpha(0.75)
for i, (cid, nrm) in enumerate(zip(trained_cids, data_violin)):
    ax.text(i, nrm.mean(), f"{nrm.mean():.1f}", ha="center", va="bottom", fontsize=9)
ax.set_xticks(range(len(trained_cids)))
ax.set_xticklabels([f"State {c}" for c in trained_cids])
ax.set_ylabel("L2 Norm of Latent Vector")
ax.set_title("클러스터별 Latent L2 Norm 분포\n(State마다 표현 크기가 다른지 확인)")
ax.grid(True, alpha=0.3)

plt.tight_layout(rect=[0, 0, 1, 0.93])
save_fig(fig3, "fig3_cosine_and_l2.png")


# ────────────────────────────────────────────────────────────────────────────
# Figure 4: 평균 Latent 프로파일 + PCA 누적 분산
# → 각 State의 BrainLM이 어떤 차원에서 차별화된 표현을 만드는지
# ────────────────────────────────────────────────────────────────────────────
print("  [Figure 4] Latent 프로파일...")

fig4, axes4 = plt.subplots(1, 2, figsize=(16, 6))
fig4.suptitle("V4 Latent 구조 분석", fontsize=13, fontweight="bold")

# 평균 latent 프로파일 (분산 높은 차원 상위 30개)
ax = axes4[0]
all_means_arr = np.array([v4_latents[c].mean(0) for c in trained_cids])
dim_var = np.var(all_means_arr, axis=0)
top30 = np.argsort(dim_var)[::-1][:30]
for cid in trained_cids:
    vals = v4_latents[cid].mean(0)[top30]
    ax.plot(range(30), vals, color=CLUSTER_COLORS[cid],
            label=f"State {cid}", linewidth=2, alpha=0.85)
ax.set_xlabel("Latent 차원 (클러스터 간 분산 상위 30개)")
ax.set_ylabel("Mean Latent 값")
ax.set_title("State별 평균 Latent 프로파일\n색이 다를수록 State 표현이 다름")
ax.legend(fontsize=10)
ax.axhline(0, color="black", linewidth=0.5)
ax.grid(True, alpha=0.3)

# PCA 누적 설명분산 (각 State 내부 구조의 복잡도)
ax = axes4[1]
max_comp = min(15, min(len(v4_latents[c]) - 1 for c in trained_cids if len(v4_latents[c]) > 1))
for cid in trained_cids:
    lat = v4_latents[cid]
    if len(lat) < 2:
        continue
    pca_k = PCA(n_components=min(max_comp, len(lat) - 1))
    pca_k.fit(lat)
    cumvar = np.cumsum(pca_k.explained_variance_ratio_) * 100
    ax.plot(range(1, len(cumvar) + 1), cumvar,
            marker="o", markersize=4, color=CLUSTER_COLORS[cid], label=f"State {cid}")
ax.axhline(90, color="red", linestyle="--", alpha=0.4, label="90%")
ax.set_xlabel("PC 수")
ax.set_ylabel("누적 설명분산 (%)")
ax.set_title("클러스터 내부 PCA 누적 분산\n(가파를수록 저차원으로 표현 가능 = 일관된 State)")
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)

plt.tight_layout(rect=[0, 0, 1, 0.93])
save_fig(fig4, "fig4_latent_profile.png")


# ────────────────────────────────────────────────────────────────────────────
# Figure 5: CM Centroid 비교 (Brain State별 FC 패턴)
# → 각 State의 CM이 어떻게 다른지 시각화
#   이것이 BrainLM latent 차이의 원인
# ────────────────────────────────────────────────────────────────────────────
print("  [Figure 5] CM Centroid 비교...")

fig5, axes5 = plt.subplots(2, K, figsize=(20, 12))
fig5.suptitle("Brain State별 Connectivity Matrix (CM) 패턴\n"
              "각 State의 FC 구조 차이 → BrainLM latent 차이의 원인",
              fontsize=13, fontweight="bold")

vmax = max(np.abs(centroids[c]).max() for c in range(K)) * 0.8

for cid in range(K):
    cm = centroids[cid]

    # 상단: CM 히트맵
    ax = axes5[0, cid]
    im = ax.imshow(cm, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
    n = cluster_sizes.get(cid, "?")
    ax.set_title(f"State {cid}  (n={n}개 CM)", fontsize=11, color=CLUSTER_COLORS[cid])
    ax.set_xlabel("ROI index")
    if cid == 0:
        ax.set_ylabel("ROI index")
    plt.colorbar(im, ax=ax, shrink=0.8, label="Fisher-Z")

    # 하단: 이 State에서 특이적으로 강한 ROI (다른 State 대비)
    ax = axes5[1, cid]
    cm_abs = np.abs(cm.copy())
    np.fill_diagonal(cm_abs, 0)
    roi_importance = cm_abs.mean(axis=1)  # 100-dim: 각 ROI의 평균 연결 강도
    # 다른 State들의 평균 ROI 중요도
    others = [np.abs(centroids[c].copy()) for c in range(K) if c != cid]
    for o in others:
        np.fill_diagonal(o, 0)
    other_avg = np.mean([o.mean(axis=1) for o in others], axis=0)
    roi_diff = roi_importance - other_avg  # 양수 = 이 State에서만 강함

    top_rois = np.argsort(roi_diff)[::-1][:15]
    ax.barh(range(15), roi_diff[top_rois][::-1], color=CLUSTER_COLORS[cid], alpha=0.85)
    ax.set_yticks(range(15))
    ax.set_yticklabels([f"ROI {r}" for r in top_rois[::-1]], fontsize=8)
    ax.invert_yaxis()
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Δ Mean |FC|")
    ax.set_title(f"State {cid} 특이적 ROI\n(이 State에서만 강한 연결)", fontsize=9, color=CLUSTER_COLORS[cid])

plt.tight_layout(rect=[0, 0, 1, 0.96])
save_fig(fig5, "fig5_cm_centroids.png")


# ────────────────────────────────────────────────────────────────────────────
# Figure 6: 피험자별 State 점유율
# → 각 피험자가 scan 시간 동안 어떤 State에 얼마나 머물렀는지
# ────────────────────────────────────────────────────────────────────────────
print("  [Figure 6] 피험자별 State 분석...")

sims = compute_cluster_similarity(all_cms, clustering_result, n_features=n_features)
subjects = sorted(sims.keys())
n_subj = len(subjects)

# 각 피험자별 클러스터 점유 세그먼트 수 계산
subj_counts = {s: {c: 0 for c in range(K)} for s in subjects}
for (subj, seg_id), cid in zip(cm_labels, clustering_result.labels):
    if subj in subj_counts:
        subj_counts[subj][int(cid)] += 1

fig6, axes6 = plt.subplots(1, 2, figsize=(20, 8))
fig6.suptitle("피험자별 Brain State 분석", fontsize=13, fontweight="bold")

# Similarity heatmap
ax = axes6[0]
sim_arr = np.array([[sims[s][c] for c in range(K)] for s in subjects])
im = ax.imshow(sim_arr, cmap="YlOrRd", aspect="auto", vmin=-0.1, vmax=0.8)
plt.colorbar(im, ax=ax, label="CM Pearson 유사도")
ax.set_xticks(range(K))
ax.set_xticklabels([f"State {c}" for c in range(K)])
ax.set_yticks(range(n_subj))
ax.set_yticklabels([s[-6:] for s in subjects], fontsize=8)
ax.set_title("① 피험자 × State 유사도\n밝을수록 해당 State에 주로 속함")
for i in range(n_subj):
    for j in range(K):
        ax.text(j, i, f"{sim_arr[i,j]:.2f}", ha="center", va="center",
                fontsize=6, color="black" if sim_arr[i,j] < 0.5 else "white")

# Stacked bar: 피험자별 State 점유율
ax = axes6[1]
bottom = np.zeros(n_subj)
for cid in range(K):
    pcts = [subj_counts[s][cid] / max(sum(subj_counts[s].values()), 1) * 100 for s in subjects]
    ax.bar(range(n_subj), pcts, bottom=bottom, color=CLUSTER_COLORS[cid],
           label=f"State {cid}", alpha=0.85)
    bottom += np.array(pcts)
ax.set_xticks(range(n_subj))
ax.set_xticklabels([s[-6:] for s in subjects], rotation=45, ha="right", fontsize=8)
ax.set_ylabel("State 점유율 (%)")
ax.set_ylim(0, 105)
ax.set_title("② 피험자별 Brain State 점유율\n(각 피험자에서 State 비중)")
ax.legend(loc="upper right", fontsize=9)

plt.tight_layout(rect=[0, 0, 1, 0.94])
save_fig(fig6, "fig6_subject_state.png")


# ────────────────────────────────────────────────────────────────────────────
# Figure 7: V2 vs V4 비교 대시보드 (핵심 비교)
# → raw TS 입력이 CM 입력보다 더 나은지 확인
# ────────────────────────────────────────────────────────────────────────────
print("  [Figure 7] V2 vs V4 비교...")

V2_BASE = ROOT / "visualization_ver2" / "final_runs" / "seq6_st1_z_ep50"
v2_latents_loaded = {}
for cid in range(K):
    p = V2_BASE / f"latents_seq6_st1_z_ep50_cluster{cid}.npy"
    if p.exists():
        v2_latents_loaded[cid] = np.load(p)

fig7, axes7 = plt.subplots(2, 3, figsize=(18, 12))
fig7.suptitle("V2 (CM 입력) vs V4 (Raw TS 입력) 비교\n교수님 피드백 반영 전/후", fontsize=13, fontweight="bold")

# V2 Cosine
if v2_latents_loaded:
    v2_means_norm = {}
    for cid, lat in v2_latents_loaded.items():
        m = lat.mean(0)
        v2_means_norm[cid] = m / (np.linalg.norm(m) + 1e-12)
    v2_cids = sorted(v2_latents_loaded.keys())
    v2_sim = np.zeros((len(v2_cids), len(v2_cids)))
    for i, ci in enumerate(v2_cids):
        for j, cj in enumerate(v2_cids):
            v2_sim[i, j] = float(v2_means_norm[ci] @ v2_means_norm[cj])
    v2_offdiag = [v2_sim[i, j] for i in range(len(v2_cids)) for j in range(len(v2_cids)) if i != j]

    ax = axes7[0, 0]
    im2 = ax.imshow(v2_sim, cmap="RdBu_r", norm=TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1))
    plt.colorbar(im2, ax=ax, shrink=0.8)
    for i in range(len(v2_cids)):
        for j in range(len(v2_cids)):
            ax.text(j, i, f"{v2_sim[i,j]:.3f}", ha="center", va="center", fontsize=9, fontweight="bold",
                    color="black" if abs(v2_sim[i,j]) < 0.5 else "white")
    ax.set_xticks(range(len(v2_cids)))
    ax.set_yticks(range(len(v2_cids)))
    ax.set_xticklabels([f"S{c}" for c in v2_cids])
    ax.set_yticklabels([f"S{c}" for c in v2_cids])
    ax.set_title(f"V2 (CM 입력)\n오프대각 평균={np.mean(v2_offdiag):.4f}")

# V4 Cosine
ax = axes7[0, 1]
im4 = ax.imshow(sim_matrix, cmap="RdBu_r", norm=TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1))
plt.colorbar(im4, ax=ax, shrink=0.8)
for i in range(n_trained):
    for j in range(n_trained):
        ax.text(j, i, f"{sim_matrix[i,j]:.3f}", ha="center", va="center", fontsize=9, fontweight="bold",
                color="black" if abs(sim_matrix[i,j]) < 0.5 else "white")
ax.set_xticks(range(n_trained))
ax.set_yticks(range(n_trained))
ax.set_xticklabels([f"S{c}" for c in trained_cids])
ax.set_yticklabels([f"S{c}" for c in trained_cids])
ax.set_title(f"V4 (Raw TS 입력)\n오프대각 평균={np.mean(offdiag):.4f}")

# Boxplot 비교
ax = axes7[0, 2]
box_data = []
box_labels = []
if v2_latents_loaded:
    box_data.append(v2_offdiag)
    box_labels.append(f"V2\n(CM)\nmean={np.mean(v2_offdiag):.3f}")
box_data.append(offdiag)
box_labels.append(f"V4\n(Raw TS)\nmean={np.mean(offdiag):.3f}")
bplot = ax.boxplot(box_data, labels=box_labels, patch_artist=True)
colors_box = ["#3498DB", "#E74C3C"]
for patch, color in zip(bplot["boxes"], colors_box[-len(box_data):]):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)
ax.axhline(0, color="red", linestyle="--", alpha=0.5, label="0 (직교)")
ax.set_ylabel("Cross-cluster Cosine Similarity")
ax.set_title("V2 vs V4 클러스터 분리 비교\n(0에 가까울수록 State 분리 명확)")
ax.legend(fontsize=9)

# V4 PCA
ax = axes7[1, 0]
for cid in trained_cids:
    m = all_cid_arr == cid
    ax.scatter(pca2d[m, 0], pca2d[m, 1], c=CLUSTER_COLORS[cid],
               label=f"State {cid}", s=50, alpha=0.8, edgecolors="white", linewidth=0.3)
ax.set_title("V4 Pooled PCA (L2 norm)")
ax.legend(fontsize=9)
ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)")
ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)")

# V2 PCA 비교
if v2_latents_loaded:
    ax = axes7[1, 1]
    v2_all = np.vstack([v2_latents_loaded[c] for c in sorted(v2_latents_loaded.keys())])
    v2_cid_arr = np.concatenate([np.full(len(v2_latents_loaded[c]), c) for c in sorted(v2_latents_loaded.keys())])
    v2_all_norm = v2_all / (np.linalg.norm(v2_all, axis=1, keepdims=True) + 1e-12)
    pca_v2 = PCA(n_components=2, random_state=42)
    v2_pca2d = pca_v2.fit_transform(v2_all_norm)
    for cid in sorted(v2_latents_loaded.keys()):
        m = v2_cid_arr == cid
        ax.scatter(v2_pca2d[m, 0], v2_pca2d[m, 1], c=CLUSTER_COLORS[cid],
                   label=f"State {cid}", s=50, alpha=0.8, edgecolors="white", linewidth=0.3)
    ax.set_title("V2 Pooled PCA (L2 norm)")
    ax.legend(fontsize=9)
    ax.set_xlabel(f"PC1 ({pca_v2.explained_variance_ratio_[0]*100:.1f}%)")
    ax.set_ylabel(f"PC2 ({pca_v2.explained_variance_ratio_[1]*100:.1f}%)")

# V4 t-SNE
ax = axes7[1, 2]
for cid in trained_cids:
    m = all_cid_arr == cid
    ax.scatter(tsne2d[m, 0], tsne2d[m, 1], c=CLUSTER_COLORS[cid],
               label=f"State {cid}", s=50, alpha=0.8, edgecolors="white", linewidth=0.3)
ax.set_title("V4 Pooled t-SNE (L2 norm)")
ax.legend(fontsize=9)

plt.tight_layout(rect=[0, 0, 1, 0.95])
save_fig(fig7, "fig7_v2_vs_v4.png")


# ────────────────────────────────────────────────────────────────────────────
# Figure 8: 종합 요약 대시보드
# ────────────────────────────────────────────────────────────────────────────
print("  [Figure 8] 종합 요약 대시보드...")

fig8 = plt.figure(figsize=(20, 14))
fig8.suptitle("V4 종합 결과 요약: per-cluster BrainLM + Raw Timeseries",
              fontsize=14, fontweight="bold")

gs = gridspec.GridSpec(3, 4, figure=fig8, hspace=0.45, wspace=0.35)

# 1) Cross-cluster cosine
ax1 = fig8.add_subplot(gs[0, :2])
im = ax1.imshow(sim_matrix, cmap="RdBu_r", norm=TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1))
plt.colorbar(im, ax=ax1, shrink=0.8)
for i in range(n_trained):
    for j in range(n_trained):
        v = sim_matrix[i, j]
        ax1.text(j, i, f"{v:.3f}", ha="center", va="center", fontsize=11,
                 fontweight="bold", color="black" if abs(v) < 0.5 else "white")
ax1.set_xticks(range(n_trained))
ax1.set_yticks(range(n_trained))
ax1.set_xticklabels([f"State {c}" for c in trained_cids])
ax1.set_yticklabels([f"State {c}" for c in trained_cids])
sign = "✅" if abs(mean_od) < 0.3 else "⚠️"
ax1.set_title(f"{sign} Latent 직교성 | 오프대각 평균={mean_od:.4f}")

# 2) Train/Val loss 요약
ax2 = fig8.add_subplot(gs[0, 2:])
ok_df = df_results[df_results.status == "ok"]
x_bar = np.arange(len(ok_df))
w = 0.35
b1 = ax2.bar(x_bar - w/2, ok_df["final_train_loss"], w, label="Train",
             color=[CLUSTER_COLORS[c] for c in ok_df["cluster_id"]], alpha=0.9)
b2 = ax2.bar(x_bar + w/2, ok_df["final_val_loss"], w, label="Val",
             color=[CLUSTER_COLORS[c] for c in ok_df["cluster_id"]], alpha=0.5, edgecolor="black")
for bar, val in zip(b1, ok_df["final_train_loss"]):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.001,
             f"{val:.3f}", ha="center", fontsize=8)
ax2.set_xticks(x_bar)
ax2.set_xticklabels([f"State {c}" for c in ok_df["cluster_id"]])
ax2.set_ylabel("Reconstruction Loss (MSE)")
ax2.set_title("클러스터별 BrainLM 학습 손실 (Raw TS)")
ax2.legend()

# 3) PCA
ax3 = fig8.add_subplot(gs[1, :2])
for cid in trained_cids:
    m = all_cid_arr == cid
    ax3.scatter(pca2d[m, 0], pca2d[m, 1], c=CLUSTER_COLORS[cid],
                label=f"State {cid} (n={m.sum()})", s=50, alpha=0.85,
                edgecolors="white", linewidth=0.3)
ax3.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)")
ax3.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)")
ax3.set_title("Pooled PCA (L2 정규화)")
ax3.legend(fontsize=9)

# 4) t-SNE
ax4 = fig8.add_subplot(gs[1, 2:])
for cid in trained_cids:
    m = all_cid_arr == cid
    ax4.scatter(tsne2d[m, 0], tsne2d[m, 1], c=CLUSTER_COLORS[cid],
                label=f"State {cid}", s=50, alpha=0.85,
                edgecolors="white", linewidth=0.3)
ax4.set_xlabel("t-SNE 1")
ax4.set_ylabel("t-SNE 2")
ax4.set_title("Pooled t-SNE (L2 정규화)")
ax4.legend(fontsize=9)

# 5) CM centroid 2개 (대표)
for k2, cid in enumerate(trained_cids[:min(2, len(trained_cids))]):
    ax5 = fig8.add_subplot(gs[2, k2])
    cm = centroids[cid]
    vmax_c = np.abs(cm).max() * 0.8
    im5 = ax5.imshow(cm, cmap="RdBu_r", vmin=-vmax_c, vmax=vmax_c, aspect="auto")
    ax5.set_title(f"State {cid} CM\n(n={cluster_sizes.get(cid,'?')})", fontsize=10)
    plt.colorbar(im5, ax=ax5, shrink=0.7)

# 6) 결론 텍스트
ax6 = fig8.add_subplot(gs[2, 2:])
ax6.axis("off")
v4_mean = np.mean(offdiag)
v2_mean = np.mean(v2_offdiag) if v2_latents_loaded else float("nan")
result_text = f"""
V4 결과 요약

구조: per-cluster BrainLM + Raw BOLD TS 입력
     (CM은 클러스터링에만 사용)

◆ Cross-cluster cosine (V4)
   오프대각 평균 = {v4_mean:.4f}
   {'✅ ≈0 : State latent 직교 (가설 부합)' if abs(v4_mean) < 0.3 else '⚠️ 아직 분리 부족'}

◆ V2 비교 (CM 입력)
   V2 오프대각 평균 = {v2_mean:.4f}
   V4 오프대각 평균 = {v4_mean:.4f}

◆ 학습 손실
""" + "\n".join([
    f"   State {r['cluster_id']}: val={r['final_val_loss']:.4f}  (n={r['n_latents']})"
    for _, r in ok_df.iterrows()
]) + f"""

◆ 다음 단계
   - Baseline (무작위 분할 TS) 대비 비교
   - ROI → 뇌 네트워크 매핑 (DMN, FPN 등)
   - 더 많은 피험자로 확장
"""
ax6.text(0.05, 0.95, result_text, transform=ax6.transAxes,
         fontsize=9, verticalalignment="top", family="monospace",
         bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8))
ax6.set_title("결론 및 해석")

save_fig(fig8, "fig8_summary_dashboard.png")


# =============================================================================
# 최종 결과 저장
# =============================================================================
summary = {
    "version": "v4",
    "description": "per-cluster BrainLM + Raw Timeseries input",
    "K": K,
    "SEQ_LEN": SEQ_LEN,
    "STRIDE": STRIDE,
    "n_subjects": n_subjects,
    "n_segments": n_segments,
    "n_ts_examples_total": len(all_ts_examples),
    "trained_clusters": trained_cids,
    "cross_cluster_cosine_mean": float(np.mean(offdiag)),
    "cross_cluster_cosine_min": float(min(offdiag)),
    "cross_cluster_cosine_max": float(max(offdiag)),
    "cluster_results": v4_results,
}
with open(OUTPUT_PATH / "v4_summary.json", "w") as f:
    json.dump(summary, f, indent=2)

print("\n" + "="*60)
print("✅ V4 파이프라인 완료!")
print(f"   출력: {OUTPUT_PATH}")
print("="*60)
for p in sorted(OUTPUT_PATH.glob("*.png")):
    print(f"  {p.name:40s} ({p.stat().st_size//1024} KB)")
