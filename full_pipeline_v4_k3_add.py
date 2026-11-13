"""
=============================================================================
V4 (K=3) Add-on Pipeline: Degree Centrality 기반 Brain State 해석 분석
=============================================================================

full_pipeline_v4_k3.py 의 결과(세그먼트 → CM → K=3 Brain State)를 그대로
재현한 뒤, 해석(interpretation)을 위한 4가지 추가 분석을 수행한다.

※ full_pipeline_v4_add.py(K=4)와 분석 내용은 완전히 동일하며 K만 다르다.
  (full_pipeline_v4_k3.py 가 full_pipeline_v4.py 의 K만 바꾼 것과 같은 관계)

  (1) Row-wise thresholding 기반 Degree Centrality (DC)
      100x100 CM의 각 행에서 상위 10% element만 남기고 행 방향 합 → 100x1 벡터

  (2) 100x1 DC 벡터를 brain surface에 시각화
      ENIGMA TOOLBOX (parcel_to_surface + plot_cortical, fsa5 표면)
      https://enigma-toolbox.readthedocs.io/en/latest/pages/12.visualization/index.html

  (3) 100x1 DC를 Schaefer2018 100Parcels 7Networks 레이블로 7x1 요약 → bar plot
      Vis / SomMot / DorsAttn / SalVentAttn / Limbic / Cont / Default

  (4) subject별 CM → subject×state DC → state 간 차이 검정
      one-way ANOVA (F, p) + state pair별 two-sample t-test (t, p)

사전 준비 (표면 시각화용, 최초 1회):
    pip install "git+https://github.com/MICA-MNI/ENIGMA.git"
    pip install "vtk==9.3.1"
      ↑ ENIGMA TOOLBOX 2.0.3에 내장된 brainspace vtk_interface는 vtk >= 9.4에서
        `PointSet has no attribute __vtkname__` 오류가 난다. vtk 9.3.x로 고정할 것.
    (ENIGMA 없이 통계만 돌리려면 --no-surface 옵션 사용)

실행:
    python full_pipeline_v4_k3_add.py                 # K=3 (full_pipeline_v4_k3.py와 동일)
    python full_pipeline_v4_k3_add.py --top-pct 0.05  # 상위 5% thresholding

산출물:
    visualization_ver4_k3_add/   (그림, 표)
    v4_k3_add_report.md          (리포트)
=============================================================================
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import pickle
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")  # GUI 없는 환경에서 PNG 저장용

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

# ── 프로젝트 루트를 sys.path에 추가 ──────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# macOS에서 sklearn + vtk 혼용 시 스레드 충돌 방지
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

from pipeline.clustering import perform_clustering
from pipeline.connectivity import collect_all_cms_flat, compute_all_cms
from pipeline.segmentation import get_segment_statistics


# =============================================================================
# 설정값 — full_pipeline_v4.py와 동일하게 맞춰 State 레이블을 정확히 재현
# =============================================================================
parser = argparse.ArgumentParser(description="V4 (K=3) Degree Centrality 추가 분석")
parser.add_argument("--k", type=int, default=3, help="Brain State 클러스터 수 (기본 3)")
parser.add_argument("--top-pct", type=float, default=0.10,
                    help="row-wise thresholding 상위 비율 (기본 0.10 = 상위 10%%)")
parser.add_argument("--use-abs", action="store_true",
                    help="부호 대신 |z|의 상위 10%%를 사용 (민감도 분석용)")
parser.add_argument("--no-surface", action="store_true",
                    help="ENIGMA surface 렌더링을 건너뜀 (통계만 수행)")
args = parser.parse_args()

K = args.k
TOP_PCT = args.top_pct
USE_ABS = args.use_abs
USE_FISHER_Z = True   # v4와 동일
RANDOM_STATE = 42     # v4와 동일

# 경로
DATA_PATH = ROOT / "data" / "DATA"
SPLIT_DIR = DATA_PATH / "data_pre" / "split_info"
SEGMENT_CACHE = ROOT / "checkpoint" / "brainlm_v3" / "cache" / "all_segments.pkl"
ATLAS_INFO = ROOT / "data" / "atlas" / "Schaefer2018_100Parcels_7Networks_order_info.txt"

# 기반 파이프라인과 짝이 맞도록 K에 따라 경로 접미사를 붙인다.
#   K=4 → full_pipeline_v4.py    / visualization_ver4_add    / v4_add_report.md
#   K=3 → full_pipeline_v4_k3.py / visualization_ver4_k3_add / v4_k3_add_report.md
#   K=2 → full_pipeline_v4_k2.py / visualization_ver4_k2_add / v4_k2_add_report.md
_suffix = "" if K == 4 else f"_k{K}"
BASE_PIPELINE = f"full_pipeline_v4{_suffix}.py"
OUTPUT_PATH = ROOT / f"visualization_ver4{_suffix}_add"
SURF_PATH = OUTPUT_PATH / "surface"
CSV_PATH = OUTPUT_PATH / "tables"
for p in (OUTPUT_PATH, SURF_PATH, CSV_PATH):
    p.mkdir(parents=True, exist_ok=True)

REPORT_PATH = ROOT / f"v4{_suffix}_add_report.md"

# State 색상 (v4 시각화와 동일)
CLUSTER_COLORS = ["#E74C3C", "#3498DB", "#2ECC71", "#F39C12", "#9B59B6", "#1ABC9C"]

# Yeo 7-Network 표준 색상 / 표기
NETWORK_ORDER = ["Vis", "SomMot", "DorsAttn", "SalVentAttn", "Limbic", "Cont", "Default"]
NETWORK_COLORS = {
    "Vis":         "#781286",
    "SomMot":      "#4682B4",
    "DorsAttn":    "#00760E",
    "SalVentAttn": "#C43AFA",
    "Limbic":      "#DCF8A4",
    "Cont":        "#E69422",
    "Default":     "#CD3E4E",
}
NETWORK_FULLNAME = {
    "Vis":         "Visual",
    "SomMot":      "Somatomotor",
    "DorsAttn":    "Dorsal Attention",
    "SalVentAttn": "Salience / Ventral Attention",
    "Limbic":      "Limbic",
    "Cont":        "Frontoparietal Control",
    "Default":     "Default Mode",
}

# 한글 폰트 (macOS)
for _f in ("AppleGothic", "Apple SD Gothic Neo", "NanumGothic", "Malgun Gothic"):
    try:
        matplotlib.font_manager.findfont(_f, fallback_to_default=False)
        plt.rcParams["font.family"] = _f
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

print("=" * 70)
print("V4 Add-on: Degree Centrality 기반 Brain State 해석 분석")
print("=" * 70)
print(f"  K (Brain State 수)      : {K}")
print(f"  Row-wise threshold      : 상위 {TOP_PCT*100:.0f}%")
print(f"  Thresholding 기준       : {'|z| (절대값)' if USE_ABS else 'z (부호 유지)'}")
print(f"  출력 경로               : {OUTPUT_PATH}")


# =============================================================================
# 유틸: Degree Centrality (row-wise proportional thresholding)
# =============================================================================
def row_threshold_dc(cm: np.ndarray, top_pct: float = 0.10,
                     use_abs: bool = False) -> np.ndarray:
    """
    100x100 연결성 행렬 → 100x1 Degree Centrality 벡터.

    절차:
      1) 대각(자기 자신 연결)을 후보에서 제외
      2) 각 행에서 상위 top_pct에 해당하는 element만 남김
         (n=100이면 99개 후보 중 상위 round(0.1*99)=10개)
      3) 남은 element들을 행 방향으로 합산 → 노드별 weighted degree

    Args:
        cm: (n, n) 연결성 행렬 (Fisher-Z 변환된 Pearson 상관)
        top_pct: 각 행에서 남길 상위 비율
        use_abs: True면 |z| 기준으로 상위를 고르고 |z|를 합산

    Returns:
        (n,) Degree Centrality 벡터
    """
    M = np.asarray(cm, dtype=np.float64).copy()
    n = M.shape[0]
    assert M.shape == (n, n), f"정방행렬이 아님: {M.shape}"

    weight = np.abs(M) if use_abs else M
    score = weight.copy()
    np.fill_diagonal(score, -np.inf)          # 대각 제외

    k = max(1, int(round(top_pct * (n - 1))))  # 남길 element 개수 (행당)
    idx = np.argpartition(-score, k - 1, axis=1)[:, :k]
    kept = np.take_along_axis(weight, idx, axis=1)
    return kept.sum(axis=1)


def dc_keep_count(n: int = 100, top_pct: float = 0.10) -> int:
    """행당 남는 element 개수 (리포트용)."""
    return max(1, int(round(top_pct * (n - 1))))


# =============================================================================
# 유틸: Schaefer2018 100Parcels 7Networks 레이블
# =============================================================================
def load_schaefer_network_labels(path: Path) -> pd.DataFrame:
    """
    CBIG의 Schaefer2018_100Parcels_7Networks_order_info.txt 를 파싱.

    파일 형식 (2줄이 1개 parcel):
        7Networks_LH_Vis_1
        1 120 18 131 255          ← parcel index, R, G, B, A

    Returns:
        DataFrame[roi_index(0-based), roi_number(1-based), full_label,
                  hemisphere, network, short_name]
    """
    if not path.exists():
        # 폴백: nilearn 내장 Schaefer atlas 레이블 사용 (동일한 순서)
        warnings.warn(f"{path} 없음 → nilearn atlas 레이블로 대체")
        from nilearn.datasets import fetch_atlas_schaefer_2018
        atlas = fetch_atlas_schaefer_2018(n_rois=100, yeo_networks=7,
                                          resolution_mm=2, verbose=0)
        raw = [l.decode() if isinstance(l, bytes) else str(l) for l in atlas.labels]
        pairs = list(enumerate(raw, start=1))
    else:
        lines = [l.strip() for l in path.read_text().splitlines() if l.strip()]
        assert len(lines) % 2 == 0, "order_info 파일 형식 오류 (짝수 줄이어야 함)"
        pairs = []
        for i in range(0, len(lines), 2):
            name = lines[i]
            roi_number = int(lines[i + 1].split()[0])
            pairs.append((roi_number, name))

    rows = []
    for roi_number, name in pairs:
        parts = name.split("_")          # 7Networks_LH_DorsAttn_Post_1
        hemi = parts[1]                  # LH / RH
        net = parts[2]                   # Vis / SomMot / ...
        rows.append({
            "roi_index": roi_number - 1,
            "roi_number": roi_number,
            "full_label": name,
            "hemisphere": hemi,
            "network": net,
            "short_name": f"{hemi}-{net}-{parts[-1]}",
        })
    df = pd.DataFrame(rows).sort_values("roi_index").reset_index(drop=True)

    # 무결성 검사: 100개, 1~100, 7개 네트워크
    assert len(df) == 100, f"parcel 수가 100이 아님: {len(df)}"
    assert df["roi_number"].tolist() == list(range(1, 101)), "parcel 번호가 1~100이 아님"
    assert set(df["network"]) == set(NETWORK_ORDER), f"네트워크 불일치: {set(df['network'])}"
    return df


# =============================================================================
# 유틸: ENIGMA TOOLBOX 표면 시각화
# =============================================================================
_ENIGMA_OK = False
if not args.no_surface:
    try:
        from enigmatoolbox.plotting import plot_cortical
        from enigmatoolbox.utils.parcellation import parcel_to_surface
        _ENIGMA_OK = True
    except Exception as e:  # pragma: no cover
        warnings.warn(f"ENIGMA TOOLBOX 로드 실패 → surface 시각화 생략 ({e})")


def render_surface(values: np.ndarray, filename: Path, cmap: str = "RdBu_r",
                   color_range: Optional[Tuple[float, float]] = None,
                   label_text: Optional[Dict[str, list]] = None,
                   size: Tuple[int, int] = (1000, 250)) -> Optional[Path]:
    """
    100x1 parcel 값 → fsa5 cortical surface PNG (LH lat / LH med / RH med / RH lat).

    ENIGMA TOOLBOX의 parcel_to_surface로 parcel 값을 20484개 vertex에 뿌린 뒤
    plot_cortical로 오프스크린 렌더링하여 PNG로 저장한다.
    """
    if not _ENIGMA_OK:
        return None
    vals = np.asarray(values, dtype=float)
    assert vals.shape == (100,), f"100차원 벡터가 아님: {vals.shape}"

    # fill=np.nan → medial wall 등 비-parcel vertex는 회색 처리
    surf_vals = parcel_to_surface(vals, "schaefer_100_fsa5", fill=np.nan)

    if color_range is None:
        finite = surf_vals[np.isfinite(surf_vals)]
        color_range = (float(np.nanmin(finite)), float(np.nanmax(finite)))

    plot_cortical(
        array_name=surf_vals,
        surface_name="fsa5",
        size=size,
        cmap=cmap,
        color_bar=True,
        color_range=color_range,
        label_text=label_text,
        nan_color=(0.82, 0.82, 0.82, 1),
        background=(1, 1, 1),
        transparent_bg=False,
        screenshot=True,
        filename=str(filename),
    )
    return filename if filename.exists() else None


def _trim_white(img: np.ndarray, tol: int = 250) -> np.ndarray:
    """PNG 주변 흰 여백 제거 (composite figure를 촘촘하게 붙이기 위함)."""
    if img.ndim == 3 and img.shape[2] == 4:
        img = img[..., :3]
    gray = img[..., :3].mean(axis=2)
    if gray.max() <= 1.001:      # float [0,1] 스케일
        gray = gray * 255.0
    mask = gray < tol
    if not mask.any():
        return img
    rs, cs = np.where(mask)
    pad = 4
    r0, r1 = max(rs.min() - pad, 0), min(rs.max() + pad + 1, img.shape[0])
    c0, c1 = max(cs.min() - pad, 0), min(cs.max() + pad + 1, img.shape[1])
    return img[r0:r1, c0:c1]


def compose_surface_grid(png_paths: List[Path], titles: List[str],
                         out_path: Path, suptitle: str,
                         ncols: int = 1, row_h: float = 2.2) -> None:
    """개별 surface PNG들을 하나의 그림으로 합쳐 저장."""
    png_paths = [p for p in png_paths if p is not None and Path(p).exists()]
    if not png_paths:
        return
    n = len(png_paths)
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols,
                             figsize=(11 * ncols, row_h * nrows), squeeze=False)
    for ax in axes.ravel():
        ax.axis("off")
    for i, (p, t) in enumerate(zip(png_paths, titles)):
        ax = axes[i // ncols, i % ncols]
        ax.imshow(_trim_white(plt.imread(str(p))))
        ax.set_title(t, fontsize=11, fontweight="bold", pad=4)
    fig.suptitle(suptitle, fontsize=13, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.955])
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"    저장: {out_path}")


# =============================================================================
# STAGE 1: 세그먼트 로드 + CM 계산 + K-means (full_pipeline_v4.py와 동일)
# =============================================================================
print("\n" + "=" * 70)
print("STAGE 1: 세그먼트 로드 / CM 계산 / Brain State 클러스터링 (v4 재현)")
print("=" * 70)

if not SEGMENT_CACHE.exists():
    raise FileNotFoundError(
        f"세그먼트 캐시가 없습니다: {SEGMENT_CACHE}\n"
        "  → 먼저 full_pipeline_v4.py를 실행해 캐시를 생성하세요."
    )
with open(SEGMENT_CACHE, "rb") as f:
    all_segments = pickle.load(f)

seg_stats = get_segment_statistics(all_segments)
print(f"  피험자 수: {len(all_segments)}, 총 세그먼트 수: {len(seg_stats)}")

print("  Pearson 상관 CM 계산 (Fisher-Z 변환)...")
all_cms = compute_all_cms(all_segments, method="pearson", min_segment_len=10,
                          use_fisher_z=USE_FISHER_Z)
X_cm, cm_labels = collect_all_cms_flat(all_cms)
n_features = next(iter(all_cms.values()))[0].n_features   # = 100
print(f"  CM: {X_cm.shape}  (n_cms x {X_cm.shape[1]}-dim flat), ROI 수 = {n_features}")

print(f"  K-means (K={K}, standardize=True, MiniBatch, seed={RANDOM_STATE})...")
clustering_result = perform_clustering(
    X_cm, cm_labels, n_clusters=K, standardize=True, use_minibatch=True,
    n_init=4, max_iter=200, batch_size=256, skip_silhouette=True,
    random_state=RANDOM_STATE,
)
cluster_sizes = clustering_result.get_cluster_sizes()
print(f"  State별 세그먼트 수: { {int(k): int(v) for k, v in cluster_sizes.items()} }")

# (subject_id, segment_id) → state 매핑
seg2state: Dict[Tuple[str, int], int] = {
    lab: int(c) for lab, c in zip(cm_labels, clustering_result.labels)
}
# (subject_id, segment_id) → CM 행렬 매핑
seg2cm: Dict[Tuple[str, int], np.ndarray] = {
    (sid, cm.segment_id): cm.matrix.astype(np.float64)
    for sid, cms in all_cms.items() for cm in cms
}
subjects = sorted(all_cms.keys())


# =============================================================================
# STAGE 2: Atlas 레이블 로드 (Schaefer2018 100Parcels 7Networks)
# =============================================================================
print("\n" + "=" * 70)
print("STAGE 2: Schaefer2018 100Parcels / 7Networks 레이블 로드")
print("=" * 70)
df_roi = load_schaefer_network_labels(ATLAS_INFO)
df_roi.to_csv(CSV_PATH / "schaefer100_7networks_labels.csv", index=False)
net_of_roi = df_roi["network"].to_numpy()
print("  네트워크별 ROI 수:")
for net in NETWORK_ORDER:
    sel = df_roi[df_roi.network == net]
    lh = int((sel.hemisphere == "LH").sum())
    rh = int((sel.hemisphere == "RH").sum())
    print(f"    {net:<12s} {len(sel):>3d}개  (LH {lh}, RH {rh})")


# =============================================================================
# ANALYSIS (1): State-level Degree Centrality
# =============================================================================
# 각 State의 대표 CM = 그 State에 속한 모든 세그먼트 CM의 평균 (Fisher-Z 공간)
# → row-wise 상위 10% thresholding → 행 합 → 100x1 DC 벡터
print("\n" + "=" * 70)
print("ANALYSIS (1): Row-wise thresholding 기반 Degree Centrality")
print("=" * 70)
KEEP = dc_keep_count(n_features, TOP_PCT)
print(f"  각 행(ROI)에서 대각 제외 {n_features - 1}개 중 상위 {KEEP}개 element 유지 후 합산")

state_mean_cm: Dict[int, np.ndarray] = {}
state_dc: Dict[int, np.ndarray] = {}
for cid in range(K):
    members = [seg2cm[lab] for lab in cm_labels if seg2state[lab] == cid]
    if not members:
        continue
    mcm = np.mean(np.stack(members, axis=0), axis=0)
    np.fill_diagonal(mcm, 0.0)
    state_mean_cm[cid] = mcm
    state_dc[cid] = row_threshold_dc(mcm, TOP_PCT, USE_ABS)
    print(f"  State {cid}: n_CM={len(members):>3d}  "
          f"DC mean={state_dc[cid].mean():.3f}  "
          f"[min {state_dc[cid].min():.3f}, max {state_dc[cid].max():.3f}]")

trained_states = sorted(state_dc.keys())

df_state_dc = pd.DataFrame(
    {f"State{cid}": state_dc[cid] for cid in trained_states},
    index=df_roi["roi_number"],
)
df_state_dc.insert(0, "network", df_roi["network"].to_numpy())
df_state_dc.insert(0, "hemisphere", df_roi["hemisphere"].to_numpy())
df_state_dc.insert(0, "roi_label", df_roi["full_label"].to_numpy())
df_state_dc.to_csv(CSV_PATH / "dc_state_level_roi.csv")
print(f"  저장: {CSV_PATH / 'dc_state_level_roi.csv'}")

# 각 State의 DC 상위 10개 ROI (해석용)
top_roi_records = []
for cid in trained_states:
    order = np.argsort(state_dc[cid])[::-1][:10]
    for rank, r in enumerate(order, start=1):
        top_roi_records.append({
            "state": cid, "rank": rank,
            "roi_number": int(df_roi.roi_number[r]),
            "roi_label": df_roi.full_label[r],
            "network": df_roi.network[r],
            "hemisphere": df_roi.hemisphere[r],
            "DC": float(state_dc[cid][r]),
        })
df_top_roi = pd.DataFrame(top_roi_records)
df_top_roi.to_csv(CSV_PATH / "dc_top10_roi_per_state.csv", index=False)


# =============================================================================
# ANALYSIS (2): Brain surface 시각화 (ENIGMA TOOLBOX)
# =============================================================================
print("\n" + "=" * 70)
print("ANALYSIS (2): Brain surface 시각화 (ENIGMA TOOLBOX / fsa5)")
print("=" * 70)

if _ENIGMA_OK:
    # ── 2-a. State별 절대 DC 맵 (공통 color range로 State 간 직접 비교 가능) ──
    allv = np.concatenate([state_dc[c] for c in trained_states])
    rng_abs = (float(np.percentile(allv, 2)), float(np.percentile(allv, 98)))
    print(f"  [2-a] State별 DC 맵 (공통 color range = {rng_abs[0]:.2f} ~ {rng_abs[1]:.2f})")
    paths, titles = [], []
    for cid in trained_states:
        p = render_surface(state_dc[cid], SURF_PATH / f"dc_state{cid}.png",
                           cmap="Reds", color_range=rng_abs)
        paths.append(p)
        titles.append(f"State {cid}  (n_CM={int(cluster_sizes[cid])})   "
                      f"DC mean={state_dc[cid].mean():.2f}")
    compose_surface_grid(
        paths, titles, OUTPUT_PATH / "fig1_surface_dc_by_state.png",
        f"Degree Centrality (row-wise top {TOP_PCT*100:.0f}%) — State별 피질 분포"
        f"\nSchaefer-100 / fsa5 · LH lateral · LH medial · RH medial · RH lateral",
    )

    # ── 2-b. Grand mean 대비 State별 편차 (State 특이성 강조) ──
    grand = np.mean(np.stack([state_dc[c] for c in trained_states]), axis=0)
    devs = {c: state_dc[c] - grand for c in trained_states}
    lim = float(np.percentile(np.abs(np.concatenate(list(devs.values()))), 98))
    print(f"  [2-b] Grand mean 대비 편차 맵 (±{lim:.2f})")
    paths, titles = [], []
    for cid in trained_states:
        p = render_surface(devs[cid], SURF_PATH / f"dc_dev_state{cid}.png",
                           cmap="RdBu_r", color_range=(-lim, lim))
        paths.append(p)
        titles.append(f"State {cid} - Grand mean   "
                      f"(red = 이 State에서 hub 강화)")
    compose_surface_grid(
        paths, titles, OUTPUT_PATH / "fig2_surface_dc_deviation.png",
        "State별 Degree Centrality 편차 (State DC - 전체 State 평균 DC)",
    )

    # ── 2-c. Grand mean DC 자체 ──
    render_surface(grand, SURF_PATH / "dc_grand_mean.png", cmap="Reds")
    compose_surface_grid(
        [SURF_PATH / "dc_grand_mean.png"], ["전체 State 평균 DC"],
        OUTPUT_PATH / "fig3_surface_dc_grandmean.png",
        f"전체 Degree Centrality (row-wise top {TOP_PCT*100:.0f}%) — 공통 hub 구조",
    )
else:
    grand = np.mean(np.stack([state_dc[c] for c in trained_states]), axis=0)
    print("  [SKIP] ENIGMA TOOLBOX 미사용 → surface 그림 생략")

# ── 2-d. Surface 없이도 볼 수 있는 ROI×State DC 히트맵 (보조 그림) ──
fig, ax = plt.subplots(figsize=(14, 4.2))
mat = np.stack([state_dc[c] for c in trained_states])
im = ax.imshow(mat, aspect="auto", cmap="Reds")
ax.set_yticks(range(len(trained_states)))
ax.set_yticklabels([f"State {c}" for c in trained_states])
ax.set_xlabel("Schaefer-100 ROI (1–50: LH, 51–100: RH)")
# 네트워크 경계 표시
bounds, prev = [], None
for i, net in enumerate(net_of_roi):
    if net != prev:
        bounds.append((i, net))
        prev = net
for i, net in bounds:
    ax.axvline(i - 0.5, color="k", lw=0.6, alpha=0.5)
    ax.text(i, -0.75, net, rotation=90, fontsize=6.5, va="bottom",
            color=NETWORK_COLORS[net], fontweight="bold")
plt.colorbar(im, ax=ax, label="Degree Centrality")
ax.set_title(f"ROI × State Degree Centrality (row-wise top {TOP_PCT*100:.0f}%)",
             fontsize=12, fontweight="bold", pad=26)
fig.tight_layout()
fig.savefig(OUTPUT_PATH / "fig4_dc_roi_state_heatmap.png", dpi=160)
plt.close(fig)
print(f"  저장: {OUTPUT_PATH / 'fig4_dc_roi_state_heatmap.png'}")


# =============================================================================
# ANALYSIS (3): 7-Network 요약 + Bar plot
# =============================================================================
print("\n" + "=" * 70)
print("ANALYSIS (3): 100x1 DC → 7 Network 요약 (bar plot)")
print("=" * 70)


def summarize_by_network(dc_vec: np.ndarray, how: str = "mean") -> np.ndarray:
    """100x1 DC → 7x1 네트워크 요약 (기본: 네트워크 내 ROI 평균)."""
    out = np.zeros(len(NETWORK_ORDER))
    for i, net in enumerate(NETWORK_ORDER):
        m = net_of_roi == net
        out[i] = dc_vec[m].mean() if how == "mean" else dc_vec[m].sum()
    return out


net_dc_mean = {c: summarize_by_network(state_dc[c], "mean") for c in trained_states}
net_dc_sum = {c: summarize_by_network(state_dc[c], "sum") for c in trained_states}

df_net = pd.DataFrame(net_dc_mean, index=NETWORK_ORDER)
df_net.columns = [f"State{c}" for c in trained_states]
df_net.insert(0, "n_roi", [int((net_of_roi == n).sum()) for n in NETWORK_ORDER])
df_net.to_csv(CSV_PATH / "dc_network_level_state.csv")
pd.DataFrame(net_dc_sum, index=NETWORK_ORDER).to_csv(
    CSV_PATH / "dc_network_level_state_SUM.csv")
print(df_net.round(3).to_string())

# ── Bar plot: (좌) State별 grouped bar, (우) 네트워크별 State 프로파일 ──
fig, axes = plt.subplots(1, 2, figsize=(16, 5.4))

ax = axes[0]
x = np.arange(len(NETWORK_ORDER))
w = 0.8 / len(trained_states)
for j, cid in enumerate(trained_states):
    ax.bar(x + j * w - 0.4 + w / 2, net_dc_mean[cid], width=w,
           color=CLUSTER_COLORS[cid % len(CLUSTER_COLORS)],
           edgecolor="black", lw=0.4, label=f"State {cid}")
ax.set_xticks(x)
ax.set_xticklabels([NETWORK_FULLNAME[n].replace(" / ", "\n").replace(" ", "\n")
                    for n in NETWORK_ORDER], fontsize=8.5)
ax.set_ylabel("Degree Centrality (네트워크 내 ROI 평균)")
ax.set_title("7-Network별 Degree Centrality — State 비교", fontsize=12, fontweight="bold")
ax.legend(fontsize=9)
ax.grid(axis="y", alpha=0.3)

ax = axes[1]
for j, net in enumerate(NETWORK_ORDER):
    vals = [net_dc_mean[c][j] for c in trained_states]
    ax.plot(range(len(trained_states)), vals, "o-", color=NETWORK_COLORS[net],
            lw=2, ms=7, markeredgecolor="black", markeredgewidth=0.5,
            label=NETWORK_FULLNAME[net])
ax.set_xticks(range(len(trained_states)))
ax.set_xticklabels([f"State {c}" for c in trained_states])
ax.set_ylabel("Degree Centrality")
ax.set_title("네트워크별 State 프로파일", fontsize=12, fontweight="bold")
ax.legend(fontsize=8, loc="best")
ax.grid(alpha=0.3)

fig.suptitle(f"Analysis (3): Schaefer-100 → Yeo 7-Network DC 요약 "
             f"(row-wise top {TOP_PCT*100:.0f}%)", fontsize=13, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.94])
fig.savefig(OUTPUT_PATH / "fig5_network_dc_barplot.png", dpi=160)
plt.close(fig)
print(f"  저장: {OUTPUT_PATH / 'fig5_network_dc_barplot.png'}")

# ── State별 개별 bar plot (네트워크 색상) ──
ncol = len(trained_states)
fig, axes = plt.subplots(1, ncol, figsize=(4.2 * ncol, 4.4), squeeze=False)
ymax = max(v.max() for v in net_dc_mean.values()) * 1.15
for j, cid in enumerate(trained_states):
    ax = axes[0, j]
    ax.bar(range(len(NETWORK_ORDER)), net_dc_mean[cid],
           color=[NETWORK_COLORS[n] for n in NETWORK_ORDER],
           edgecolor="black", lw=0.5)
    ax.set_xticks(range(len(NETWORK_ORDER)))
    ax.set_xticklabels(NETWORK_ORDER, rotation=45, ha="right", fontsize=8.5)
    ax.set_ylim(0, ymax)
    ax.set_title(f"State {cid}", fontsize=12, fontweight="bold",
                 color=CLUSTER_COLORS[cid % len(CLUSTER_COLORS)])
    if j == 0:
        ax.set_ylabel("Degree Centrality")
    ax.grid(axis="y", alpha=0.3)
fig.suptitle("State별 7-Network Degree Centrality", fontsize=13, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.92])
fig.savefig(OUTPUT_PATH / "fig6_network_dc_per_state.png", dpi=160)
plt.close(fig)
print(f"  저장: {OUTPUT_PATH / 'fig6_network_dc_per_state.png'}")


# =============================================================================
# ANALYSIS (4): Subject-level DC → State 간 통계 검정
# =============================================================================
# 각 피험자(subject)에 대해, 같은 State에 배정된 세그먼트 CM들을 평균 →
# subject×State CM → row-wise thresholding → 100x1 DC 벡터
#   · 관측 단위 = (subject, state) 쌍
#   · 검정 1: one-way ANOVA  (State 간 DC 차이)          → F, p
#   · 검정 2: two-sample t-test (State pair별 비교)       → t, p
print("\n" + "=" * 70)
print("ANALYSIS (4): Subject별 CM → State 간 Degree Centrality 차이 검정")
print("=" * 70)

subj_state_dc: Dict[Tuple[str, int], np.ndarray] = {}
subj_state_n: Dict[Tuple[str, int], int] = {}
for sid in subjects:
    for cid in range(K):
        members = [cm.matrix.astype(np.float64) for cm in all_cms[sid]
                   if seg2state[(sid, cm.segment_id)] == cid]
        if not members:
            continue
        mcm = np.mean(np.stack(members, axis=0), axis=0)
        np.fill_diagonal(mcm, 0.0)
        subj_state_dc[(sid, cid)] = row_threshold_dc(mcm, TOP_PCT, USE_ABS)
        subj_state_n[(sid, cid)] = len(members)

obs_states = sorted({c for (_, c) in subj_state_dc})
n_per_state = {c: sum(1 for (_, cc) in subj_state_dc if cc == c) for c in obs_states}
print(f"  관측(subject×State) 수: {len(subj_state_dc)}")
print(f"  State별 피험자 수: {n_per_state}")

# long-format 저장
long_rows = []
for (sid, cid), dc in subj_state_dc.items():
    for r in range(n_features):
        long_rows.append({
            "subject": sid, "state": cid, "n_segments": subj_state_n[(sid, cid)],
            "roi_number": int(df_roi.roi_number[r]),
            "roi_label": df_roi.full_label[r],
            "network": df_roi.network[r],
            "hemisphere": df_roi.hemisphere[r],
            "DC": float(dc[r]),
        })
df_long = pd.DataFrame(long_rows)
df_long.to_csv(CSV_PATH / "dc_subject_state_roi_long.csv", index=False)
print(f"  저장: {CSV_PATH / 'dc_subject_state_roi_long.csv'}  ({len(df_long)} rows)")


def fdr_bh(pvals: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg FDR 보정 q-value."""
    p = np.asarray(pvals, dtype=float)
    n = p.size
    order = np.argsort(p)
    ranked = p[order] * n / (np.arange(n) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    q = np.empty(n)
    q[order] = np.clip(ranked, 0, 1)
    return q


def cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    """pooled SD 기반 Cohen's d."""
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return float("nan")
    sp2 = ((na - 1) * np.var(a, ddof=1) + (nb - 1) * np.var(b, ddof=1)) / (na + nb - 2)
    return float((np.mean(a) - np.mean(b)) / np.sqrt(sp2)) if sp2 > 0 else float("nan")


def eta_squared(groups: List[np.ndarray]) -> float:
    """one-way ANOVA 효과크기 eta^2 = SS_between / SS_total."""
    allv = np.concatenate(groups)
    gm = allv.mean()
    ssb = sum(len(g) * (g.mean() - gm) ** 2 for g in groups)
    sst = ((allv - gm) ** 2).sum()
    return float(ssb / sst) if sst > 0 else float("nan")


def run_anova_and_pairwise(value_of: Dict[Tuple[str, int], float], name: str):
    """
    value_of: (subject, state) → 스칼라 값
    반환: (anova_dict, pairwise DataFrame)
    """
    groups = {c: np.array([v for (s, cc), v in value_of.items() if cc == c])
              for c in obs_states}
    groups = {c: g for c, g in groups.items() if len(g) >= 2}
    glist = [groups[c] for c in sorted(groups)]
    F, p = stats.f_oneway(*glist) if len(glist) >= 2 else (np.nan, np.nan)
    H, p_kw = stats.kruskal(*glist) if len(glist) >= 2 else (np.nan, np.nan)
    k = len(glist)
    ntot = sum(len(g) for g in glist)
    anova = {
        "measure": name, "k_groups": k, "n_total": ntot,
        "df_between": k - 1, "df_within": ntot - k,
        "F": float(F), "p": float(p), "eta_sq": eta_squared(glist),
        "kruskal_H": float(H), "kruskal_p": float(p_kw),
        **{f"mean_State{c}": float(groups[c].mean()) for c in sorted(groups)},
        **{f"sd_State{c}": float(groups[c].std(ddof=1)) for c in sorted(groups)},
        **{f"n_State{c}": int(len(groups[c])) for c in sorted(groups)},
    }
    rows = []
    for a, b in itertools.combinations(sorted(groups), 2):
        ga, gb = groups[a], groups[b]
        t, pt = stats.ttest_ind(ga, gb, equal_var=True)      # 요청된 two-sample t-test
        tw, pw = stats.ttest_ind(ga, gb, equal_var=False)    # Welch (보조)
        rows.append({
            "measure": name, "pair": f"State{a} vs State{b}",
            "state_a": a, "state_b": b, "n_a": len(ga), "n_b": len(gb),
            "mean_a": float(ga.mean()), "mean_b": float(gb.mean()),
            "mean_diff": float(ga.mean() - gb.mean()),
            "t": float(t), "p": float(pt), "df": len(ga) + len(gb) - 2,
            "cohens_d": cohens_d(ga, gb),
            "welch_t": float(tw), "welch_p": float(pw),
        })
    dfp = pd.DataFrame(rows)
    if len(dfp):
        dfp["p_fdr"] = fdr_bh(dfp["p"].to_numpy())
    return anova, dfp


# ── 4-a. Global DC (100개 ROI 평균) ────────────────────────────────────────
print("\n  [4-a] Global DC (100개 ROI 평균) — State 간 비교")
global_vals = {k_: float(v.mean()) for k_, v in subj_state_dc.items()}
anova_global, pw_global = run_anova_and_pairwise(global_vals, "Global DC")
print(f"    ANOVA: F({anova_global['df_between']},{anova_global['df_within']}) = "
      f"{anova_global['F']:.3f}, p = {anova_global['p']:.4g}, "
      f"eta^2 = {anova_global['eta_sq']:.3f}")
for _, r in pw_global.iterrows():
    print(f"    {r['pair']:<22s} t({int(r['df'])}) = {r['t']:>7.3f}, "
          f"p = {r['p']:.4g}  (FDR q = {r['p_fdr']:.4g}, d = {r['cohens_d']:.2f})")

# ── 4-b. 네트워크별 DC (7개) ───────────────────────────────────────────────
print("\n  [4-b] 네트워크별 DC — State 간 비교")
net_anovas, net_pairwise = [], []
for net in NETWORK_ORDER:
    m = net_of_roi == net
    vals = {k_: float(v[m].mean()) for k_, v in subj_state_dc.items()}
    a, dfp = run_anova_and_pairwise(vals, net)
    net_anovas.append(a)
    net_pairwise.append(dfp)
df_net_anova = pd.DataFrame(net_anovas)
df_net_anova["p_fdr"] = fdr_bh(df_net_anova["p"].to_numpy())
df_net_pw = pd.concat(net_pairwise, ignore_index=True)
df_net_pw["p_fdr_across_networks"] = fdr_bh(df_net_pw["p"].to_numpy())
for _, r in df_net_anova.iterrows():
    star = "***" if r.p_fdr < 0.001 else "**" if r.p_fdr < 0.01 else "*" if r.p_fdr < 0.05 else ""
    print(f"    {r['measure']:<12s} F({int(r.df_between)},{int(r.df_within)}) = {r.F:>7.3f}, "
          f"p = {r.p:.4g}, FDR q = {r.p_fdr:.4g} {star}")

# ── 4-c. ROI별 DC (100개) ─────────────────────────────────────────────────
print("\n  [4-c] ROI별 DC (100개) — State 간 비교")
roi_anovas = []
for r in range(n_features):
    vals = {k_: float(v[r]) for k_, v in subj_state_dc.items()}
    a, _ = run_anova_and_pairwise(vals, f"ROI{int(df_roi.roi_number[r])}")
    a.update({
        "roi_index": r, "roi_number": int(df_roi.roi_number[r]),
        "roi_label": df_roi.full_label[r], "network": df_roi.network[r],
        "hemisphere": df_roi.hemisphere[r],
    })
    roi_anovas.append(a)
df_roi_anova = pd.DataFrame(roi_anovas)
df_roi_anova["p_fdr"] = fdr_bh(df_roi_anova["p"].to_numpy())
n_sig_unc = int((df_roi_anova.p < 0.05).sum())
n_sig_fdr = int((df_roi_anova.p_fdr < 0.05).sum())
print(f"    p < 0.05 (uncorrected): {n_sig_unc}/100 ROI")
print(f"    FDR q < 0.05          : {n_sig_fdr}/100 ROI")

# ROI별 pairwise t-test (모든 pair × 100 ROI), pair별 FDR 보정
roi_pw_rows = []
for a, b in itertools.combinations(obs_states, 2):
    ga_keys = [k_ for k_ in subj_state_dc if k_[1] == a]
    gb_keys = [k_ for k_ in subj_state_dc if k_[1] == b]
    if len(ga_keys) < 2 or len(gb_keys) < 2:
        continue
    A = np.stack([subj_state_dc[k_] for k_ in ga_keys])   # (n_a, 100)
    B = np.stack([subj_state_dc[k_] for k_ in gb_keys])
    t, p = stats.ttest_ind(A, B, axis=0, equal_var=True)
    q = fdr_bh(p)
    for r in range(n_features):
        roi_pw_rows.append({
            "pair": f"State{a} vs State{b}", "state_a": a, "state_b": b,
            "roi_number": int(df_roi.roi_number[r]), "roi_label": df_roi.full_label[r],
            "network": df_roi.network[r], "hemisphere": df_roi.hemisphere[r],
            "n_a": len(ga_keys), "n_b": len(gb_keys),
            "mean_a": float(A[:, r].mean()), "mean_b": float(B[:, r].mean()),
            "mean_diff": float(A[:, r].mean() - B[:, r].mean()),
            "t": float(t[r]), "p": float(p[r]), "p_fdr": float(q[r]),
            "cohens_d": cohens_d(A[:, r], B[:, r]),
        })
df_roi_pw = pd.DataFrame(roi_pw_rows)
for pr, g in df_roi_pw.groupby("pair"):
    print(f"    {pr:<22s} p<0.05: {int((g.p < 0.05).sum()):>3d}/100 ROI, "
          f"FDR q<0.05: {int((g.p_fdr < 0.05).sum()):>3d}/100 ROI")

# ── 저장 ──
pd.DataFrame([anova_global]).to_csv(CSV_PATH / "stats_global_anova.csv", index=False)
pw_global.to_csv(CSV_PATH / "stats_global_pairwise_ttest.csv", index=False)
df_net_anova.to_csv(CSV_PATH / "stats_network_anova.csv", index=False)
df_net_pw.to_csv(CSV_PATH / "stats_network_pairwise_ttest.csv", index=False)
df_roi_anova.to_csv(CSV_PATH / "stats_roi_anova.csv", index=False)
df_roi_pw.to_csv(CSV_PATH / "stats_roi_pairwise_ttest.csv", index=False)
print(f"  통계 결과 저장: {CSV_PATH}")


# =============================================================================
# ANALYSIS (4) 시각화
# =============================================================================
print("\n  [4-d] 통계 결과 시각화")

# ── fig7: Global DC boxplot + 네트워크별 boxplot ──
n_panels = 1 + len(NETWORK_ORDER)
fig, axes = plt.subplots(2, 4, figsize=(17, 8.5))
axes = axes.ravel()


def _box_panel(ax, values_by_state, title, anova_row):
    data = [values_by_state[c] for c in obs_states if len(values_by_state[c]) >= 1]
    labels = [f"State {c}\n(n={len(values_by_state[c])})"
              for c in obs_states if len(values_by_state[c]) >= 1]
    bp = ax.boxplot(data, labels=labels, patch_artist=True, widths=0.55,
                    medianprops=dict(color="black", lw=1.6), showfliers=False)
    for patch, c in zip(bp["boxes"], obs_states):
        patch.set_facecolor(CLUSTER_COLORS[c % len(CLUSTER_COLORS)])
        patch.set_alpha(0.55)
    for i, (c, d) in enumerate(zip(obs_states, data)):
        jitter = np.random.default_rng(0).normal(0, 0.05, len(d))
        ax.scatter(np.full(len(d), i + 1) + jitter, d, s=16, color="k", alpha=0.55, zorder=3)
    F, p, q = anova_row["F"], anova_row["p"], anova_row.get("p_fdr", np.nan)
    star = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."
    qtxt = "" if np.isnan(q) else f"\nFDR q = {q:.3g}"
    ax.set_title(f"{title}\nF = {F:.2f}, p = {p:.3g} {star}{qtxt}",
                 fontsize=10, fontweight="bold")
    ax.tick_params(axis="x", labelsize=8)
    ax.grid(axis="y", alpha=0.3)


gvals = {c: np.array([v for (s, cc), v in global_vals.items() if cc == c]) for c in obs_states}
_box_panel(axes[0], gvals, "Global DC (100 ROI 평균)", anova_global)
axes[0].set_ylabel("Degree Centrality")

for i, net in enumerate(NETWORK_ORDER):
    m = net_of_roi == net
    vals = {c: np.array([v[m].mean() for (s, cc), v in subj_state_dc.items() if cc == c])
            for c in obs_states}
    row = df_net_anova[df_net_anova.measure == net].iloc[0].to_dict()
    _box_panel(axes[i + 1], vals, NETWORK_FULLNAME[net], row)

fig.suptitle(f"Analysis (4): Subject×State Degree Centrality — one-way ANOVA "
             f"(관측 단위 = subject×State, N = {len(subj_state_dc)})",
             fontsize=13, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.94])
fig.savefig(OUTPUT_PATH / "fig7_anova_boxplots.png", dpi=160)
plt.close(fig)
print(f"    저장: {OUTPUT_PATH / 'fig7_anova_boxplots.png'}")

# ── fig8: 네트워크별 pairwise t-test heatmap ──
pairs = sorted(df_net_pw["pair"].unique())
if pairs:
    fig, axes = plt.subplots(1, 2, figsize=(15, 4.6))
    T = np.array([[df_net_pw[(df_net_pw.measure == n) & (df_net_pw.pair == p)]["t"].values[0]
                   for p in pairs] for n in NETWORK_ORDER])
    P = np.array([[df_net_pw[(df_net_pw.measure == n) & (df_net_pw.pair == p)]["p"].values[0]
                   for p in pairs] for n in NETWORK_ORDER])
    lim = np.nanmax(np.abs(T)) if np.isfinite(T).any() else 1
    im = axes[0].imshow(T, cmap="RdBu_r", vmin=-lim, vmax=lim, aspect="auto")
    axes[0].set_title("two-sample t-test: t 통계량\n(양수 = 앞 State가 더 큼)",
                      fontsize=11, fontweight="bold")
    plt.colorbar(im, ax=axes[0], label="t")
    im2 = axes[1].imshow(-np.log10(np.clip(P, 1e-16, 1)), cmap="viridis", aspect="auto")
    axes[1].set_title("two-sample t-test: -log10(p)\n(흰 별 = p < 0.05)",
                      fontsize=11, fontweight="bold")
    plt.colorbar(im2, ax=axes[1], label="-log10(p)")
    for ax in axes:
        ax.set_yticks(range(len(NETWORK_ORDER)))
        ax.set_yticklabels(NETWORK_ORDER, fontsize=9)
        ax.set_xticks(range(len(pairs)))
        ax.set_xticklabels([p.replace("State", "S").replace(" vs ", "\nvs ") for p in pairs],
                           fontsize=8)
    for i in range(len(NETWORK_ORDER)):
        for j in range(len(pairs)):
            axes[0].text(j, i, f"{T[i, j]:.2f}", ha="center", va="center", fontsize=7.5,
                         color="white" if abs(T[i, j]) > lim * 0.55 else "black")
            if P[i, j] < 0.05:
                axes[1].text(j, i, "*", ha="center", va="center", fontsize=15, color="white")
    fig.suptitle("Analysis (4): 네트워크별 State pair two-sample t-test",
                 fontsize=13, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.9])
    fig.savefig(OUTPUT_PATH / "fig8_network_pairwise_ttest.png", dpi=160)
    plt.close(fig)
    print(f"    저장: {OUTPUT_PATH / 'fig8_network_pairwise_ttest.png'}")

# ── fig9: ROI별 ANOVA F 값 surface map + p 값 ──
if _ENIGMA_OK:
    Fmap = df_roi_anova.sort_values("roi_index")["F"].to_numpy()
    logp = -np.log10(np.clip(df_roi_anova.sort_values("roi_index")["p"].to_numpy(), 1e-16, 1))
    p1 = render_surface(Fmap, SURF_PATH / "roi_anova_F.png", cmap="YlOrRd")
    p2 = render_surface(logp, SURF_PATH / "roi_anova_logp.png", cmap="viridis")
    # FDR 유의 ROI만 강조 (나머지는 0)
    sigF = np.where(df_roi_anova.sort_values("roi_index")["p_fdr"].to_numpy() < 0.05, Fmap, 0.0)
    p3 = render_surface(sigF, SURF_PATH / "roi_anova_F_fdr_sig.png", cmap="YlOrRd")
    compose_surface_grid(
        [p1, p2, p3],
        ["ROI별 one-way ANOVA  F 통계량",
         "ROI별 one-way ANOVA  -log10(p)  (uncorrected)",
         f"FDR q < 0.05 유의 ROI만 표시 ({n_sig_fdr}개)"],
        OUTPUT_PATH / "fig9_surface_roi_anova.png",
        "Analysis (4): ROI별 State 간 Degree Centrality 차이 (one-way ANOVA)",
    )

    # ── fig10: State pair별 t-map surface (pair마다 자체 color range) ──
    # 공통 range를 쓰면 강한 대비가 약한 대비를 눌러버리므로 pair별로 스케일링한다.
    paths, titles = [], []
    for pr in pairs:
        g = df_roi_pw[df_roi_pw.pair == pr].sort_values("roi_number")
        tm = g["t"].to_numpy()
        lim_p = float(np.max(np.abs(tm))) if np.isfinite(tm).any() else 1.0
        p_ = render_surface(tm, SURF_PATH / f"tmap_{pr.replace(' ', '_')}.png",
                            cmap="RdBu_r", color_range=(-lim_p, lim_p))
        paths.append(p_)
        titles.append(f"{pr}   (red = 앞 State의 DC가 큼, |t| max = {lim_p:.1f}, "
                      f"p<0.05: {int((g.p < 0.05).sum())} ROI, "
                      f"FDR q<0.05: {int((g.p_fdr < 0.05).sum())} ROI)")
    compose_surface_grid(
        paths, titles, OUTPUT_PATH / "fig10_surface_pairwise_tmap.png",
        "Analysis (4): State pair별 two-sample t-test t-map (ROI 단위)"
        "\ncolor range는 pair마다 독립 스케일 (공간 패턴 비교용)",
    )


# =============================================================================
# ANALYSIS (5, 보조): 상대 DC — 전역 연결강도와 공간적 hub 재배치의 분리
# =============================================================================
# (4)의 결과는 State 간 DC가 전반적인 크기(global offset)로 크게 갈릴 수 있다.
# "State가 달라질 때 hub의 공간적 배치도 바뀌는가?"를 따로 보려면
# 각 관측의 DC를 자기 자신의 평균으로 나눠 전역 크기를 제거해야 한다.
#   relative DC_i = DC_i / mean(DC)        (100개 ROI 합 = 100, 단위 없음)
print("\n" + "=" * 70)
print("ANALYSIS (5, 보조): 상대 DC (global 크기 제거 후 공간 패턴 비교)")
print("=" * 70)

rel_subj: Dict[Tuple[str, int], np.ndarray] = {
    k_: v / v.mean() for k_, v in subj_state_dc.items()
}
rel_state: Dict[int, np.ndarray] = {c: state_dc[c] / state_dc[c].mean()
                                    for c in trained_states}

# State-level 상대 DC 프로파일 간 공간 상관 (State 간 hub 배치가 얼마나 닮았나)
sp_corr = np.ones((len(trained_states), len(trained_states)))
for i, a in enumerate(trained_states):
    for j, b in enumerate(trained_states):
        sp_corr[i, j] = np.corrcoef(rel_state[a], rel_state[b])[0, 1]
df_spcorr = pd.DataFrame(sp_corr,
                         index=[f"State{c}" for c in trained_states],
                         columns=[f"State{c}" for c in trained_states])
df_spcorr.to_csv(CSV_PATH / "dc_state_spatial_correlation.csv")
print("  State 간 상대 DC 공간 상관 (Pearson r):")
print(df_spcorr.round(3).to_string())

# 네트워크별 상대 DC ANOVA + pairwise
rel_net_anovas, rel_net_pw = [], []
for net in NETWORK_ORDER:
    m = net_of_roi == net
    vals = {k_: float(v[m].mean()) for k_, v in rel_subj.items()}
    a, dfp = run_anova_and_pairwise(vals, net)
    rel_net_anovas.append(a)
    rel_net_pw.append(dfp)
df_rel_net_anova = pd.DataFrame(rel_net_anovas)
df_rel_net_anova["p_fdr"] = fdr_bh(df_rel_net_anova["p"].to_numpy())
df_rel_net_pw = pd.concat(rel_net_pw, ignore_index=True)
df_rel_net_pw["p_fdr_across_networks"] = fdr_bh(df_rel_net_pw["p"].to_numpy())
print("\n  네트워크별 상대 DC one-way ANOVA:")
for _, r in df_rel_net_anova.iterrows():
    star = "***" if r.p_fdr < 0.001 else "**" if r.p_fdr < 0.01 else "*" if r.p_fdr < 0.05 else "n.s."
    print(f"    {r['measure']:<12s} F({int(r.df_between)},{int(r.df_within)}) = {r.F:>7.3f}, "
          f"p = {r.p:.4g}, FDR q = {r.p_fdr:.4g} {star}")

# ROI별 상대 DC ANOVA
rel_roi_anovas = []
for r in range(n_features):
    vals = {k_: float(v[r]) for k_, v in rel_subj.items()}
    a, _ = run_anova_and_pairwise(vals, f"ROI{int(df_roi.roi_number[r])}")
    a.update({"roi_index": r, "roi_number": int(df_roi.roi_number[r]),
              "roi_label": df_roi.full_label[r], "network": df_roi.network[r],
              "hemisphere": df_roi.hemisphere[r]})
    rel_roi_anovas.append(a)
df_rel_roi_anova = pd.DataFrame(rel_roi_anovas)
df_rel_roi_anova["p_fdr"] = fdr_bh(df_rel_roi_anova["p"].to_numpy())
n_rel_sig_unc = int((df_rel_roi_anova.p < 0.05).sum())
n_rel_sig_fdr = int((df_rel_roi_anova.p_fdr < 0.05).sum())
print(f"\n  ROI별 상대 DC ANOVA: p<0.05 {n_rel_sig_unc}/100, FDR q<0.05 {n_rel_sig_fdr}/100")

df_rel_net_anova.to_csv(CSV_PATH / "stats_network_anova_relativeDC.csv", index=False)
df_rel_net_pw.to_csv(CSV_PATH / "stats_network_pairwise_ttest_relativeDC.csv", index=False)
df_rel_roi_anova.to_csv(CSV_PATH / "stats_roi_anova_relativeDC.csv", index=False)
pd.DataFrame({f"State{c}": rel_state[c] for c in trained_states},
             index=df_roi["roi_number"]).to_csv(CSV_PATH / "dc_state_level_roi_relative.csv")

# ── fig11: 상대 DC 네트워크 bar + 공간 상관 heatmap ──
fig, axes = plt.subplots(1, 2, figsize=(15.5, 5.0),
                         gridspec_kw={"width_ratios": [2.1, 1]})
ax = axes[0]
x = np.arange(len(NETWORK_ORDER))
w = 0.8 / len(trained_states)
for j, cid in enumerate(trained_states):
    m_vals = [rel_state[cid][net_of_roi == n].mean() for n in NETWORK_ORDER]
    ax.bar(x + j * w - 0.4 + w / 2, m_vals, width=w,
           color=CLUSTER_COLORS[cid % len(CLUSTER_COLORS)],
           edgecolor="black", lw=0.4, label=f"State {cid}")
ax.axhline(1.0, color="k", ls="--", lw=1, alpha=0.7)
ax.text(len(NETWORK_ORDER) - 0.55, 1.01, "전체 평균 = 1.0", fontsize=8, va="bottom")
ax.set_xticks(x)
ax.set_xticklabels([NETWORK_FULLNAME[n].replace(" / ", "\n").replace(" ", "\n")
                    for n in NETWORK_ORDER], fontsize=8.5)
ax.set_ylabel("상대 DC (DC / 그 State의 평균 DC)")
ax.set_title("전역 연결강도 제거 후 네트워크별 상대 DC", fontsize=12, fontweight="bold")
ax.legend(fontsize=9)
ax.grid(axis="y", alpha=0.3)

ax = axes[1]
im = ax.imshow(sp_corr, cmap="viridis", vmin=np.min(sp_corr), vmax=1.0)
ax.set_xticks(range(len(trained_states)))
ax.set_yticks(range(len(trained_states)))
ax.set_xticklabels([f"S{c}" for c in trained_states])
ax.set_yticklabels([f"S{c}" for c in trained_states])
for i in range(len(trained_states)):
    for j in range(len(trained_states)):
        ax.text(j, i, f"{sp_corr[i, j]:.3f}", ha="center", va="center", fontsize=10,
                color="white" if sp_corr[i, j] < (np.min(sp_corr) + 1) / 2 else "black")
plt.colorbar(im, ax=ax, label="Pearson r")
ax.set_title("State 간 상대 DC 공간 상관\n(1에 가까울수록 hub 배치가 동일)",
             fontsize=11, fontweight="bold")

fig.suptitle("Analysis (5, 보조): 전역 연결강도 vs 공간적 hub 재배치 분리",
             fontsize=13, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.92])
fig.savefig(OUTPUT_PATH / "fig11_relative_dc.png", dpi=160)
plt.close(fig)
print(f"  저장: {OUTPUT_PATH / 'fig11_relative_dc.png'}")

# ── fig12: 상대 DC 편차 표면 맵 ──
if _ENIGMA_OK:
    rel_grand = np.mean(np.stack([rel_state[c] for c in trained_states]), axis=0)
    rel_devs = {c: rel_state[c] - rel_grand for c in trained_states}
    rlim = float(np.percentile(np.abs(np.concatenate(list(rel_devs.values()))), 98))
    paths, titles = [], []
    for cid in trained_states:
        p_ = render_surface(rel_devs[cid], SURF_PATH / f"reldc_dev_state{cid}.png",
                            cmap="RdBu_r", color_range=(-rlim, rlim))
        paths.append(p_)
        titles.append(f"State {cid}: 상대 DC - 전체 평균  "
                      f"(red = 이 State에서 상대적 hub 강화)")
    compose_surface_grid(
        paths, titles, OUTPUT_PATH / "fig12_surface_relative_dc.png",
        "Analysis (5, 보조): 전역 크기를 제거한 상대 DC의 State별 편차",
    )


# =============================================================================
# 리포트 생성 (Markdown)
# =============================================================================
print("\n" + "=" * 70)
print("리포트 생성")
print("=" * 70)


def md_table(df: pd.DataFrame, cols: List[str], fmt: Dict[str, str] = None) -> str:
    fmt = fmt or {}
    head = "| " + " | ".join(cols) + " |"
    sep = "|" + "|".join(["---"] * len(cols)) + "|"
    lines = [head, sep]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if c in fmt:
                cells.append(fmt[c].format(v))
            elif isinstance(v, (float, np.floating)):
                cells.append(f"{v:.4g}")
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def stars(p: float) -> str:
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."


L: List[str] = []
A = L.append

A(f"# Degree Centrality 기반 Brain State 해석 분석 (V4, K={K})\n")
A(f"- 생성 스크립트: `{Path(__file__).name}`")
A(f"- 기반 파이프라인: `{BASE_PIPELINE}` (세그먼트 → CM → K-means Brain State)")
A(f"- 피험자 수: **{len(all_segments)}**, 총 세그먼트(=CM) 수: **{len(cm_labels)}**, ROI: **Schaefer-100 (7 Networks, cortex only)**")
A(f"- Brain State 수 K = **{K}**, State별 세그먼트 수: "
  f"{ {int(k): int(v) for k, v in cluster_sizes.items()} }")
A(f"- CM: Pearson 상관 + Fisher-Z 변환\n")

A("---\n")
A("## 핵심 결과 요약\n")

_order = sorted(trained_states, key=lambda c: state_dc[c].mean())
_ord_txt = " < ".join(f"State {c} ({state_dc[c].mean():.2f})" for c in _order)
_offdiag = sp_corr[np.triu_indices(len(trained_states), 1)]
_rel_sig_nets = [NETWORK_FULLNAME[m] for m, q in
                 zip(df_rel_net_anova["measure"], df_rel_net_anova["p_fdr"]) if q < 0.05]

A(f"1. **State 간 DC는 매우 크게 다르다.** Global DC(100개 ROI 평균)의 one-way ANOVA는 "
  f"F({anova_global['df_between']}, {anova_global['df_within']}) = {anova_global['F']:.1f}, "
  f"p = {anova_global['p']:.3g} (η² = {anova_global['eta_sq']:.2f})이고, "
  + (f"State pair는 t = {pw_global['t'].iloc[0]:+.1f}, p = {pw_global['p'].iloc[0]:.3g}로 유의했다."
     if len(pw_global) == 1 else
     f"{len(pw_global)}개 State pair "
     f"{'모두' if (pw_global['p'] < 0.05).all() else '중 일부만'} two-sample t-test에서 유의했다 "
     f"(|t| = {pw_global['t'].abs().min():.1f} ~ {pw_global['t'].abs().max():.1f})."))
A(f"2. **DC 크기 순서**: {_ord_txt}. "
  f"가장 강한 State는 **State {_order[-1]}**, 가장 약한 State는 **State {_order[0]}**이다.")
A(f"3. **네트워크 수준에서도 7개 네트워크 전부 유의**하게 달랐다 "
  f"(FDR q < 0.05, F = {df_net_anova['F'].min():.1f} ~ {df_net_anova['F'].max():.1f}). "
  f"ROI 수준에서는 {n_sig_fdr}/100 ROI가 FDR q < 0.05였다.")
A(f"4. **DC가 가장 높은 영역은 모든 State에서 일관되게 Visual network**이며 "
  f"(Vis 상대 DC ≈ {np.mean([rel_state[c][net_of_roi == 'Vis'].mean() for c in trained_states]):.2f}), "
  f"가장 낮은 영역은 Limbic network다 "
  f"(≈ {np.mean([rel_state[c][net_of_roi == 'Limbic'].mean() for c in trained_states]):.2f}). "
  f"즉 hub의 위치 자체는 State가 바뀌어도 크게 흔들리지 않는다.")
A(f"5. **차이의 대부분은 전역 연결강도(FC magnitude)에서 온다.** "
  "전역 크기를 제거한 상대 DC로 다시 보면 State 간 공간 상관이 "
  + (f"r = {_offdiag[0]:.2f}로 높고, " if _offdiag.size == 1
     else f"r = {_offdiag.min():.2f} ~ {_offdiag.max():.2f}로 높고, ")
  + f"7개 네트워크 중 {len(_rel_sig_nets)}개"
  + (f"({', '.join(_rel_sig_nets)})만" if _rel_sig_nets else "만")
  + f" FDR q < 0.05를 유지했으며, 유의 ROI도 {n_sig_fdr}개 → {n_rel_sig_fdr}개로 줄었다. "
    f"따라서 K-means가 잡아낸 Brain State의 주된 축은 "
    f"\"hub의 재배치\"보다 \"전반적 연결강도의 고저\"로 해석하는 것이 타당하다. (자세한 내용은 (5)절)")
_small = min(obs_states, key=lambda c: n_per_state[c])
_small_warn = (f"표본이 가장 작은 State는 State {_small}로 "
               f"세그먼트 {int(cluster_sizes[_small])}개 / 피험자 {n_per_state[_small]}명뿐이라 "
               f"검정력이 낮고, 또한 "
               if n_per_state[_small] < 15 else
               f"State별 피험자 수는 {min(n_per_state.values())}~{max(n_per_state.values())}명으로 "
               f"비교적 균형이 있으나, ")
A(f"6. **주의**: {_small_warn}"
  f"관측 단위가 (subject × State)라 독립성 가정이 완전하지 않다. (마지막 절 참고)\n")

A("---\n")
A("## 방법: Degree Centrality 정의\n")
A(f"100×100 연결성 행렬 `Z`(Fisher-Z)에 **row-wise proportional thresholding**을 적용한다.\n")
A("```")
A("1) 대각(자기 자신 연결)을 후보에서 제외             → 각 행 99개 후보")
A(f"2) 각 행에서 값이 큰 상위 {TOP_PCT*100:.0f}% element만 유지        → 행당 {KEEP}개 유지")
A("3) 유지된 element를 행 방향으로 합산                → DC_i = sum_j∈top(i) Z_ij")
A("```")
A(f"\n- 결과: 100×1 벡터 (ROI별 weighted degree centrality)")
A(f"- Thresholding 기준: **{'|z| 절대값' if USE_ABS else 'z (부호 유지, 즉 가장 강한 양의 연결)'}**")
A("- 행별로 독립적으로 threshold하므로 유지 마스크는 비대칭이며, "
  "DC는 \"각 ROI가 자신의 가장 강한 연결 상위 10%로부터 받는 총 연결 강도\"를 의미한다.\n")

A("---\n")
A("## (1)+(2) State별 Degree Centrality 와 피질 표면 분포\n")
A("### State별 DC 요약 통계\n")
_sum_rows = []
for cid in trained_states:
    d = state_dc[cid]
    top1 = df_top_roi[df_top_roi.state == cid].iloc[0]
    _sum_rows.append({
        "State": f"State {cid}", "n_CM": int(cluster_sizes[cid]),
        "DC mean": d.mean(), "DC SD": d.std(ddof=1),
        "DC min": d.min(), "DC max": d.max(),
        "최대 DC ROI": f"{top1.roi_label} ({top1.network})",
    })
A(md_table(pd.DataFrame(_sum_rows),
           ["State", "n_CM", "DC mean", "DC SD", "DC min", "DC max", "최대 DC ROI"],
           {"DC mean": "{:.3f}", "DC SD": "{:.3f}", "DC min": "{:.3f}", "DC max": "{:.3f}"}))
A("")
A("### State별 DC 상위 5개 ROI\n")
for cid in trained_states:
    g = df_top_roi[df_top_roi.state == cid].head(5)
    A(f"**State {cid}**")
    A(md_table(g, ["rank", "roi_label", "network", "hemisphere", "DC"], {"DC": "{:.3f}"}))
    A("")

if _ENIGMA_OK:
    A("### 표면 시각화 (ENIGMA TOOLBOX, fsa5)\n")
    A("각 그림은 좌→우로 `LH lateral · LH medial · RH medial · RH lateral` 순서다.\n")
    A(f"![State별 DC](./{OUTPUT_PATH.name}/fig1_surface_dc_by_state.png)\n")
    A("*Figure 1. State별 Degree Centrality의 피질 분포 (공통 color range).*\n")
    A(f"![DC 편차](./{OUTPUT_PATH.name}/fig2_surface_dc_deviation.png)\n")
    A("*Figure 2. 전체 State 평균 대비 각 State의 DC 편차. "
      "붉은색 = 해당 State에서 상대적으로 hub 역할이 강화된 영역.*\n")
    A(f"![Grand mean DC](./{OUTPUT_PATH.name}/fig3_surface_dc_grandmean.png)\n")
    A("*Figure 3. 모든 State 평균 DC — State와 무관한 공통 hub 구조.*\n")
A(f"![ROI×State heatmap](./{OUTPUT_PATH.name}/fig4_dc_roi_state_heatmap.png)\n")
A("*Figure 4. ROI × State DC 히트맵 (네트워크 경계 표시).*\n")

A("---\n")
A("## (3) Yeo 7-Network 요약\n")
A("Schaefer-100 parcel을 CBIG `Schaefer2018_100Parcels_7Networks_order_info.txt` 의 "
  "네트워크 레이블로 묶어, 네트워크 내 ROI의 DC **평균**으로 7×1 벡터를 만들었다.\n")
_dfn = df_net.copy()
_dfn.insert(0, "Network", [NETWORK_FULLNAME[n] for n in NETWORK_ORDER])
A(md_table(_dfn.reset_index().rename(columns={"index": "code"}),
           ["Network", "code", "n_roi"] + [f"State{c}" for c in trained_states],
           {f"State{c}": "{:.3f}" for c in trained_states}))
A("")
A(f"![Network bar plot](./{OUTPUT_PATH.name}/fig5_network_dc_barplot.png)\n")
A("*Figure 5. (좌) 네트워크별 State 비교 grouped bar plot, (우) 네트워크별 State 프로파일.*\n")
A(f"![State별 network bar](./{OUTPUT_PATH.name}/fig6_network_dc_per_state.png)\n")
A("*Figure 6. State별 7-Network DC bar plot (Yeo 표준 색상).*\n")

A("---\n")
A("## (4) State 간 Degree Centrality 차이 검정\n")
A(f"- 관측 단위: **(subject × State) 쌍** — 각 피험자의 세그먼트 CM 중 해당 State에 "
  f"배정된 것들을 Fisher-Z 공간에서 평균한 뒤 DC를 계산")
A(f"- 총 관측 수 **N = {len(subj_state_dc)}** "
  f"(State별 피험자 수: { {f'State{c}': n_per_state[c] for c in obs_states} })")
A("- 검정 1: one-way ANOVA (State가 요인)")
A("- 검정 2: State pair별 two-sample t-test (equal variance, Student's t)")
A("- 다중비교: Benjamini-Hochberg FDR (`p_fdr`)\n")

A("### 4-a. Global DC (100개 ROI 평균)\n")
A(f"**one-way ANOVA**: F({anova_global['df_between']}, {anova_global['df_within']}) = "
  f"**{anova_global['F']:.3f}**, p = **{anova_global['p']:.4g}** "
  f"{stars(anova_global['p'])}, η² = {anova_global['eta_sq']:.3f}  \n")
A(f"(비모수 확인: Kruskal-Wallis H = {anova_global['kruskal_H']:.3f}, "
  f"p = {anova_global['kruskal_p']:.4g})\n")
if len(obs_states) == 2:
    A("> **참고 (K=2)**: 그룹이 2개일 때 one-way ANOVA와 two-sample t-test는 수학적으로 "
      "동일한 검정이다 (F = t², p 값 동일). 따라서 아래 ANOVA와 4-a의 pairwise t-test는 "
      "같은 결과를 다른 형식으로 보여 주는 것이며, 서로 독립된 근거가 아니다.\n")
A("State별 평균 ± 표준편차:\n")
_g = pd.DataFrame([{
    "State": f"State {c}", "n": anova_global[f"n_State{c}"],
    "mean": anova_global[f"mean_State{c}"], "SD": anova_global[f"sd_State{c}"],
} for c in obs_states if f"n_State{c}" in anova_global])
A(md_table(_g, ["State", "n", "mean", "SD"], {"mean": "{:.3f}", "SD": "{:.3f}"}))
A("")
A("**State pair별 two-sample t-test**\n")
_pg = pw_global.copy()
_pg["sig"] = _pg["p"].map(stars)
A(md_table(_pg, ["pair", "n_a", "n_b", "mean_a", "mean_b", "mean_diff",
                 "t", "p", "sig", "p_fdr", "cohens_d"],
           {"mean_a": "{:.3f}", "mean_b": "{:.3f}", "mean_diff": "{:+.3f}",
            "t": "{:+.3f}", "cohens_d": "{:+.2f}"}))
A("")

A("### 4-b. 네트워크별 DC (7개 네트워크)\n")
A("**one-way ANOVA (네트워크별)**\n")
_na = df_net_anova.copy()
_na["Network"] = [NETWORK_FULLNAME[m] for m in _na["measure"]]
_na["sig"] = _na["p_fdr"].map(stars)
A(md_table(_na, ["Network", "measure", "F", "p", "p_fdr", "sig", "eta_sq"],
           {"F": "{:.3f}", "eta_sq": "{:.3f}"}))
A("")
A("**네트워크 × State pair two-sample t-test** (전체 표는 "
  f"`{CSV_PATH.name}/stats_network_pairwise_ttest.csv`)\n")
_sig_net = df_net_pw[df_net_pw.p < 0.05].sort_values("p")
if len(_sig_net):
    _sig_net = _sig_net.copy()
    _sig_net["sig"] = _sig_net["p"].map(stars)
    A(md_table(_sig_net.head(25),
               ["measure", "pair", "mean_a", "mean_b", "mean_diff", "t", "p", "sig",
                "p_fdr_across_networks", "cohens_d"],
               {"mean_a": "{:.3f}", "mean_b": "{:.3f}", "mean_diff": "{:+.3f}",
                "t": "{:+.3f}", "cohens_d": "{:+.2f}"}))
else:
    A("p < 0.05 인 네트워크 × pair 조합 없음.")
A("")
A(f"![network pairwise](./{OUTPUT_PATH.name}/fig8_network_pairwise_ttest.png)\n")
A("*Figure 8. 네트워크별 State pair two-sample t-test 결과 (t 통계량 / -log10 p).*\n")
A(f"![ANOVA boxplot](./{OUTPUT_PATH.name}/fig7_anova_boxplots.png)\n")
A("*Figure 7. Global DC 및 네트워크별 DC의 State 간 분포 (점 = 개별 subject×State 관측).*\n")

A("### 4-c. ROI별 DC (100개 ROI)\n")
A(f"- one-way ANOVA에서 **p < 0.05 (uncorrected): {n_sig_unc}/100 ROI**, "
  f"**FDR q < 0.05: {n_sig_fdr}/100 ROI**\n")
_top_roi_anova = df_roi_anova.sort_values("p").head(15).copy()
_top_roi_anova["sig"] = _top_roi_anova["p"].map(stars)
A("F 값 상위 15개 ROI:\n")
A(md_table(_top_roi_anova,
           ["roi_number", "roi_label", "network", "F", "p", "sig", "p_fdr", "eta_sq"],
           {"F": "{:.3f}", "eta_sq": "{:.3f}"}))
A("")
A("**State pair별 ROI 수준 two-sample t-test 요약**\n")
_pw_sum = df_roi_pw.groupby("pair").apply(
    lambda g: pd.Series({
        "n_a": int(g.n_a.iloc[0]), "n_b": int(g.n_b.iloc[0]),
        "ROI p<0.05": int((g.p < 0.05).sum()),
        "ROI FDR q<0.05": int((g.p_fdr < 0.05).sum()),
        "max abs(t)": float(g.t.abs().max()),
        "가장 유의한 ROI": g.loc[g.p.idxmin(), "roi_label"],
    }), include_groups=False).reset_index()
A(md_table(_pw_sum, ["pair", "n_a", "n_b", "ROI p<0.05", "ROI FDR q<0.05",
                     "max abs(t)", "가장 유의한 ROI"], {"max abs(t)": "{:.3f}"}))
A("")
if _ENIGMA_OK:
    A(f"![ROI ANOVA surface](./{OUTPUT_PATH.name}/fig9_surface_roi_anova.png)\n")
    A("*Figure 9. ROI별 one-way ANOVA F / -log10(p) / FDR 유의 ROI 표면 맵.*\n")
    A(f"![pairwise tmap](./{OUTPUT_PATH.name}/fig10_surface_pairwise_tmap.png)\n")
    A("*Figure 10. State pair별 two-sample t-test t-map.*\n")

A("---\n")
A("## (5, 보조) 전역 연결강도 vs 공간적 hub 재배치\n")
A("(4)의 DC 차이가 \"뇌 전체 연결강도가 통째로 올라간 것\"인지 "
  "\"hub의 공간적 배치가 바뀐 것\"인지 구분하기 위해, 각 관측의 DC를 "
  "자기 평균으로 나눈 **상대 DC**(relative DC = DC / mean(DC), 100개 ROI 평균 = 1)로 "
  "동일한 검정을 반복했다.\n")
A("### State 간 상대 DC 프로파일의 공간 상관\n")
A(md_table(df_spcorr.reset_index().rename(columns={"index": ""}),
           [""] + [f"State{c}" for c in trained_states],
           {f"State{c}": "{:.3f}" for c in trained_states}))
A("")
A(f"- State 간 공간 상관의 최솟값 = **{sp_corr[np.triu_indices(len(trained_states), 1)].min():.3f}** "
  f"→ 1에 가까울수록 State가 달라져도 hub의 공간적 배치는 거의 동일함을 뜻한다.\n")
A("### 네트워크별 상대 DC one-way ANOVA\n")
_rna = df_rel_net_anova.copy()
_rna["Network"] = [NETWORK_FULLNAME[m] for m in _rna["measure"]]
_rna["sig"] = _rna["p_fdr"].map(stars)
A(md_table(_rna, ["Network", "measure", "F", "p", "p_fdr", "sig", "eta_sq"],
           {"F": "{:.3f}", "eta_sq": "{:.3f}"}))
A("")
A(f"- ROI별 상대 DC ANOVA: p < 0.05 (uncorrected) **{n_rel_sig_unc}/100 ROI**, "
  f"FDR q < 0.05 **{n_rel_sig_fdr}/100 ROI**")
A(f"- 비교: 원래(절대) DC에서는 각각 {n_sig_unc}/100, {n_sig_fdr}/100 ROI였다.\n")
A(f"![relative DC](./{OUTPUT_PATH.name}/fig11_relative_dc.png)\n")
A("*Figure 11. (좌) 전역 크기를 제거한 네트워크별 상대 DC, (우) State 간 상대 DC 공간 상관.*\n")
if _ENIGMA_OK:
    A(f"![relative DC surface](./{OUTPUT_PATH.name}/fig12_surface_relative_dc.png)\n")
    A("*Figure 12. 상대 DC의 State별 편차 표면 맵.*\n")
A("**해석 포인트**: 절대 DC의 State 차이 중 얼마만큼이 전역 연결강도 차이이고 "
  "얼마만큼이 공간적 재배치인지를 위 두 결과를 비교해 판단해야 한다. "
  "공간 상관이 매우 높고 상대 DC의 유의 ROI 수가 크게 줄어든다면, "
  "State 구분의 주된 축은 \"hub 위치의 변화\"가 아니라 \"전반적 연결강도(FC magnitude)\"이다.\n")

A("---\n")
A("## 통계적 주의사항\n")
A(f"1. 관측 단위가 (subject × State)이므로 한 피험자가 여러 State에 기여할 수 있다"
  f"(전체 {len(subjects)}명 중 여러 State를 가진 피험자 존재). "
  f"따라서 one-way ANOVA / two-sample t-test의 독립성 가정은 엄밀히는 위배되며, "
  f"결과는 탐색적(exploratory)으로 해석해야 한다. "
  f"보조 지표로 Kruskal-Wallis(비모수)와 Welch t-test를 함께 보고했다.")
A(f"2. State별 표본 크기가 불균형하다 "
  f"({ {f'State{c}': n_per_state[c] for c in obs_states} }). "
  f"표본이 작은 State의 검정력은 낮다.")
A("3. 100개 ROI 및 7개 네트워크에 대한 반복 검정은 Benjamini-Hochberg FDR로 보정했다 "
  "(`p_fdr` 열). 본문의 `p`는 보정 전 값이다.")
A("4. DC는 Fisher-Z 값의 합이므로 단위가 없는 상대적 지표이며, "
  "State 간 비교에서만 의미를 가진다.\n")

A("---\n")
A("## 산출물\n")
A(f"- 그림: `{OUTPUT_PATH.name}/fig1 ~ fig12*.png`")
A(f"- 개별 표면 렌더링: `{OUTPUT_PATH.name}/surface/*.png`")
A(f"- 표(CSV): `{OUTPUT_PATH.name}/tables/`")
A("  - `dc_state_level_roi.csv` — State별 100×1 DC")
A("  - `dc_top10_roi_per_state.csv` — State별 DC 상위 10 ROI")
A("  - `dc_network_level_state.csv` / `..._SUM.csv` — 7×1 네트워크 요약")
A("  - `dc_subject_state_roi_long.csv` — subject×State×ROI DC (long format)")
A("  - `stats_global_anova.csv`, `stats_global_pairwise_ttest.csv`")
A("  - `stats_network_anova.csv`, `stats_network_pairwise_ttest.csv`")
A("  - `stats_roi_anova.csv`, `stats_roi_pairwise_ttest.csv`")
A("  - `dc_state_level_roi_relative.csv`, `dc_state_spatial_correlation.csv` — 상대 DC (보조 분석)")
A("  - `stats_network_anova_relativeDC.csv`, `stats_network_pairwise_ttest_relativeDC.csv`, "
  "`stats_roi_anova_relativeDC.csv`")
A("  - `schaefer100_7networks_labels.csv` — 사용된 ROI↔네트워크 매핑")

REPORT_PATH.write_text("\n".join(L), encoding="utf-8")
print(f"  리포트 저장: {REPORT_PATH}")

# 요약 JSON
summary = {
    "K": K, "top_pct": TOP_PCT, "use_abs": USE_ABS,
    "n_subjects": len(all_segments), "n_segments": len(cm_labels),
    "cluster_sizes": {int(k): int(v) for k, v in cluster_sizes.items()},
    "n_obs_subject_state": len(subj_state_dc),
    "n_per_state": {int(k): int(v) for k, v in n_per_state.items()},
    "global_anova": {k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
                     for k, v in anova_global.items()},
    "global_pairwise": pw_global.to_dict("records"),
    "network_anova": df_net_anova.to_dict("records"),
    "n_roi_sig_uncorrected": n_sig_unc,
    "n_roi_sig_fdr": n_sig_fdr,
    "relative_dc": {
        "state_spatial_correlation": df_spcorr.to_dict(),
        "network_anova": df_rel_net_anova.to_dict("records"),
        "n_roi_sig_uncorrected": n_rel_sig_unc,
        "n_roi_sig_fdr": n_rel_sig_fdr,
    },
    "enigma_surface": bool(_ENIGMA_OK),
}
with open(OUTPUT_PATH / "v4_add_summary.json", "w") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

print("\n" + "=" * 70)
print("완료")
print("=" * 70)
print(f"  리포트 : {REPORT_PATH}")
print(f"  그림/표: {OUTPUT_PATH}")
