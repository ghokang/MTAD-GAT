"""
=============================================================================
Optimal K 탐색 (leakage 방지 + 커널 크래시 방지)
=============================================================================

배경:
  - 기존 노트북들은 torch(BrainLM)와 sklearn(K-means/silhouette)을 같은
    Jupyter 커널에서 같이 돌리다가 macOS OpenMP/BLAS 충돌로 커널이 죽는
    문제가 있었음 → skip_silhouette=True로 우회하고 K=4를 그냥 하드코딩.
  - 실제로는 데이터가 작아(최대 308 x 4950) 계산량 자체는 가벼움
    (전체 K=2~10 스캔에 약 2초, 640MB). torch를 아예 로드하지 않는
    독립 프로세스로 돌리면 크래시 없이 실루엣을 계산할 수 있음.

이 스크립트는:
  1. torch 없이 순수 numpy/sklearn만 사용 (충돌 원인 자체를 제거)
  2. --subset train  : full_pipeline_v4.py와 동일한 subject-level split
     (seed=42, val=0.15, test=0.15)을 재현해 train subject만 사용
     (val/test가 클러스터 정의에 관여하지 않도록 leakage 방지)
  3. --subset full   : 27명 전체(308세그먼트, 기존 파이프라인이 실제로
     쓰는 방식)로 계산
  4. KMeans와 MiniBatchKMeans 둘 다로 실루엣을 계산해 결과가 알고리즘에
     안정적인지 함께 확인
=============================================================================
"""

from __future__ import annotations

import argparse
import os
import pickle
import sys
from pathlib import Path

# torch를 로드하지 않으므로 이 시점에 스레드 수를 고정해도 sklearn에 안전하게 적용됨
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, MiniBatchKMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from pipeline.connectivity import compute_all_cms, collect_all_cms_flat  # noqa: E402
from pipeline.visualization import plot_elbow_curve  # noqa: E402

SEGMENT_CACHE = ROOT / "checkpoint" / "brainlm_v3" / "cache" / "all_segments.pkl"
OUTPUT_DIR = ROOT / "result" / "optimal_k"

VAL_SPLIT = 0.15
TEST_SPLIT = 0.15
SEED = 42
USE_FISHER_Z = True
K_RANGE = range(2, 11)


def split_train_subjects(all_segments: dict) -> set:
    """full_pipeline_v4.py / pipeline/v3_sequences.py의 split_examples와 동일한
    subject-level 분할을 재현해 train subject 집합만 반환."""
    subjects = sorted(all_segments.keys())
    rng = np.random.default_rng(SEED)
    rng.shuffle(subjects)

    n_total = len(subjects)
    n_test = int(round(n_total * TEST_SPLIT))
    n_val = int(round(n_total * VAL_SPLIT))
    n_train = max(0, n_total - n_test - n_val)
    return set(subjects[:n_train])


def main():
    parser = argparse.ArgumentParser(description="Optimal K 탐색 (elbow + silhouette)")
    parser.add_argument("--subset", choices=["train", "full"], default="train",
                         help="train: leakage 방지용 train subject만 / full: 27명 전체")
    parser.add_argument("--k-min", type=int, default=K_RANGE.start)
    parser.add_argument("--k-max", type=int, default=K_RANGE.stop - 1)
    args = parser.parse_args()

    k_range = range(args.k_min, args.k_max + 1)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(SEGMENT_CACHE, "rb") as f:
        all_segments = pickle.load(f)
    print(f"세그먼트 캐시 로드: {SEGMENT_CACHE}  (전체 {len(all_segments)}명)")

    if args.subset == "train":
        train_subj = split_train_subjects(all_segments)
        segments = {sid: segs for sid, segs in all_segments.items() if sid in train_subj}
        print(f"[train subset] {len(segments)}명 사용 (val/test 제외, seed={SEED})")
    else:
        segments = all_segments
        print(f"[full subset] {len(segments)}명 전체 사용")

    all_cms = compute_all_cms(segments, method="pearson", min_segment_len=10, use_fisher_z=USE_FISHER_Z)
    X, cm_labels = collect_all_cms_flat(all_cms)
    print(f"X shape: {X.shape}")

    X_scaled = StandardScaler().fit_transform(X)

    rows = []
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=SEED, n_init=10)
        labels_km = km.fit_predict(X_scaled)
        sil_km = silhouette_score(X_scaled, labels_km)

        mbk = MiniBatchKMeans(n_clusters=k, random_state=SEED, n_init=4, max_iter=200, batch_size=256)
        labels_mbk = mbk.fit_predict(X_scaled)
        sil_mbk = silhouette_score(X_scaled, labels_mbk)

        sizes_km = np.bincount(labels_km)
        rows.append({
            "k": k,
            "inertia_kmeans": km.inertia_,
            "silhouette_kmeans": sil_km,
            "silhouette_minibatch": sil_mbk,
            "cluster_sizes_kmeans": sizes_km.tolist(),
            "min_cluster_size": int(sizes_km.min()),
        })
        print(f"K={k:2d}  silhouette(KMeans)={sil_km:.4f}  silhouette(MiniBatch)={sil_mbk:.4f}  "
              f"sizes={sizes_km.tolist()}")

    df = pd.DataFrame(rows)
    csv_path = OUTPUT_DIR / f"optimal_k_{args.subset}.csv"
    df.to_csv(csv_path, index=False)
    print(f"\n결과 저장: {csv_path}")

    best = df.loc[df["silhouette_kmeans"].idxmax()]
    print(f"\n>>> Silhouette 기준 최적 K = {int(best['k'])} "
          f"(silhouette={best['silhouette_kmeans']:.4f}, subset={args.subset})")

    # elbow + silhouette 플롯 저장 (pipeline/visualization.py 재사용)
    metrics = {
        "k_range": list(df["k"]),
        "inertias": list(df["inertia_kmeans"]),
        "silhouettes": list(df["silhouette_kmeans"]),
        "optimal_k": int(best["k"]),
    }
    fig_path = OUTPUT_DIR / f"elbow_silhouette_{args.subset}.png"
    plot_elbow_curve(metrics, save_path=fig_path, show=False)
    print(f"그래프 저장: {fig_path}")


if __name__ == "__main__":
    main()
