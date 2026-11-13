"""
=============================================================================
V5: 무작위 분할 대조군 (Random Segmentation Control)
=============================================================================

핵심 가설 검정:
    "MTAD-GAT 임베딩 변화점은 단순한 잡음이 아니라 뇌 기능 상태가 전환되는
     의미 있는 경계다."

지금까지의 V1~V4 분석은 MTAD-GAT 경계로 자른 결과만 보여줬을 뿐, **비교 대상이
없었다**. 시계열을 아무 데서나 잘라도 세그먼트마다 FC는 다르고 K-means는 무조건
무언가로 묶어준다. 따라서 "묶였다"는 사실 자체는 가설의 증거가 되지 못한다.

이 스크립트는 귀무 모형(null model)을 만든다.
    · 피험자별 세그먼트 **개수**와 **길이 분포**는 실제와 동일하게 유지
    · **경계 위치만** 무작위로 재배치 (피험자 내에서 길이 순서를 섞음)
    · 이것을 N_PERM회 반복하여 각 지표의 귀무분포를 얻는다
    · MTAD-GAT 경계의 값이 그 분포에서 상위 몇 %인지로 permutation p-value 계산

검정 지표 (4가지)
  (1) 세그먼트 내부 동질성  — 세그먼트를 전/후반으로 쪼갠 두 CM의 상관
       경계가 진짜 상태 전환점이면 세그먼트 **안**은 균질해야 한다 (↑ 좋음)
  (2) 경계 대비            — 경계 양쪽 윈도우(W TP)의 CM 상관
       진짜 전환점이라면 경계를 사이에 두고 FC가 **달라져야** 한다 (↓ 좋음)
  (3) 클러스터링 품질      — 세그먼트 CM의 silhouette (K=2,3,4)
       경계가 의미 있으면 세그먼트들이 상태로 더 잘 뭉쳐야 한다 (↑ 좋음)
  (4) 전역강도 축 지배성   — PC1 설명분산, PC1과 평균 FC 강도의 상관
       V4 add 분석에서 드러난 "전역 연결강도 단일 축" 구조가 분할 방식과
       무관하게 나타나는지 확인 (가설 검정이 아니라 해석용)

이 대조군은 **세그먼테이션 단계**를 직접 검정한다. BrainLM 재학습(상태별 트랜스포머
×100회)은 계산량 때문에 포함하지 않았다 — 애초에 세그먼트 경계가 무작위와
구별되지 않으면 그 뒤 단계는 검정할 의미가 없다.

실행:
    python full_pipeline_v5.py                 # 기본 100회 반복
    python full_pipeline_v5.py --n-perm 1000   # 반복 수 변경
    python full_pipeline_v5.py --window 40     # 경계 대비 윈도우 크기
=============================================================================
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

parser = argparse.ArgumentParser(description="V5 무작위 분할 대조군")
parser.add_argument("--n-perm", type=int, default=100, help="무작위 분할 반복 수 (기본 100)")
parser.add_argument("--window", type=int, default=30,
                    help="경계 대비 계산용 윈도우 크기 [TP] (기본 30)")
parser.add_argument("--seed", type=int, default=42, help="난수 seed")
args = parser.parse_args()

N_PERM = args.n_perm
WIN = args.window
SEED = args.seed
K_LIST = (2, 3, 4)
TR = 0.72                # dwell time 환산 (V4 add-on과 동일)
MIN_HALF = 10          # 전/후반 CM을 계산할 수 있는 최소 TP 수

SEGMENT_CACHE = ROOT / "checkpoint" / "brainlm_v3" / "cache" / "all_segments.pkl"
OUTPUT_PATH = ROOT / "visualization_ver5"
CSV_PATH = OUTPUT_PATH / "tables"
for p in (OUTPUT_PATH, CSV_PATH):
    p.mkdir(parents=True, exist_ok=True)
REPORT_PATH = ROOT / "v5_report.md"

for _f in ("AppleGothic", "Apple SD Gothic Neo", "NanumGothic", "Malgun Gothic"):
    try:
        matplotlib.font_manager.findfont(_f, fallback_to_default=False)
        plt.rcParams["font.family"] = _f
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

print("=" * 70)
print("V5: 무작위 분할 대조군 (Random Segmentation Control)")
print("=" * 70)
print(f"  무작위 반복 수   : {N_PERM}")
print(f"  경계 대비 윈도우 : {WIN} TP")
print(f"  출력 경로        : {OUTPUT_PATH}")


# =============================================================================
# 유틸 — CM 계산 (pipeline/connectivity.py와 동일한 규칙)
# =============================================================================
TRIU = np.triu_indices(100, k=1)


def cm_flat(ts: np.ndarray) -> np.ndarray:
    """(T, 100) 시계열 → Fisher-Z CM의 상삼각 4950차원 벡터."""
    if ts.shape[0] < 2:
        return np.zeros(len(TRIU[0]), dtype=np.float64)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cm = np.corrcoef(ts.T)
    cm = np.nan_to_num(cm, nan=0.0)
    np.fill_diagonal(cm, 1.0)
    cm = np.arctanh(np.clip(cm, -0.9999, 0.9999))   # Fisher-Z (파이프라인과 동일)
    return cm[TRIU]


def corr(a: np.ndarray, b: np.ndarray) -> float:
    """두 벡터의 Pearson 상관 (분산 0이면 nan)."""
    if a.std() == 0 or b.std() == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


# =============================================================================
# STAGE 1: 실제 세그먼트 로드 + 전체 시계열 복원
# =============================================================================
print("\n" + "=" * 70)
print("STAGE 1: 세그먼트 로드 / 전체 시계열 복원")
print("=" * 70)

if not SEGMENT_CACHE.exists():
    raise FileNotFoundError(f"세그먼트 캐시가 없습니다: {SEGMENT_CACHE}")
with open(SEGMENT_CACHE, "rb") as f:
    all_segments = pickle.load(f)

subjects = sorted(all_segments)
ts_of: Dict[str, np.ndarray] = {}        # subject → (T, 100) 전체 시계열
real_lengths: Dict[str, List[int]] = {}  # subject → 실제 세그먼트 길이 목록

for sid in subjects:
    segs = sorted(all_segments[sid], key=lambda s: s.start_idx)
    # 세그먼트가 스캔 전체를 빈틈없이 덮는지 확인 (복원 가능 조건)
    assert all(segs[i].end_idx == segs[i + 1].start_idx for i in range(len(segs) - 1)), \
        f"{sid}: 세그먼트가 연속적이지 않습니다"
    ts_of[sid] = np.concatenate([s.data for s in segs], axis=0).astype(np.float64)
    real_lengths[sid] = [int(s.length) for s in segs]

n_seg_total = sum(len(v) for v in real_lengths.values())
scan_len = {sid: ts_of[sid].shape[0] for sid in subjects}
print(f"  피험자 수: {len(subjects)}, 총 세그먼트 수: {n_seg_total}")
print(f"  스캔 길이: {sorted(set(scan_len.values()))} TP")
print(f"  세그먼트 길이: min={min(min(v) for v in real_lengths.values())}, "
      f"max={max(max(v) for v in real_lengths.values())}, "
      f"mean={np.mean([l for v in real_lengths.values() for l in v]):.1f}")


# =============================================================================
# STAGE 2: 분할(segmentation) → 지표 계산
# =============================================================================
def boundaries_from_lengths(lengths: List[int]) -> List[Tuple[int, int]]:
    """길이 목록 → [(start, end), ...] 구간 목록."""
    out, pos = [], 0
    for L in lengths:
        out.append((pos, pos + L))
        pos += L
    return out


def dwell_anova(labels: np.ndarray, owner: List[str], lengths: List[int]) -> Dict[str, float]:
    """state별 dwell time을 구하고 one-way ANOVA.

    V4 add-on(`full_pipeline_v4_add.py` ANALYSIS (6))과 동일한 두 정의를 쓴다.
      (A) 총 점유 시간   : 그 state 세그먼트 길이의 총합 x TR
      (B) 방문당 체류 시간: 같은 state가 연속된 구간(bout) 길이의 피험자별 평균 x TR
    관측 단위는 (subject, state) 쌍.

    반환: 두 정의 각각의 ANOVA F / p / eta^2
    """
    occ: Dict[Tuple[str, int], float] = {}
    bout: Dict[Tuple[str, int], float] = {}

    i = 0
    while i < len(owner):
        sid = owner[i]
        j = i
        while j < len(owner) and owner[j] == sid:
            j += 1
        seq = [(int(labels[t]), lengths[t]) for t in range(i, j)]   # 시간 순서

        for st, L in seq:                       # (A)
            occ[(sid, st)] = occ.get((sid, st), 0.0) + L * TR

        bouts: Dict[int, List[int]] = {}        # (B)
        cur_state, cur_len = None, 0
        for st, L in seq:
            if st == cur_state:
                cur_len += L
            else:
                if cur_state is not None:
                    bouts.setdefault(cur_state, []).append(cur_len)
                cur_state, cur_len = st, L
        if cur_state is not None:
            bouts.setdefault(cur_state, []).append(cur_len)
        for st, lens in bouts.items():
            bout[(sid, st)] = float(np.mean(lens)) * TR

        i = j

    out: Dict[str, float] = {}
    for tag, d in (("dwell_occ", occ), ("dwell_bout", bout)):
        states = sorted({c for (_, c) in d})
        groups = [np.array([v for (s, cc), v in d.items() if cc == c]) for c in states]
        groups = [g for g in groups if len(g) >= 2]
        if len(groups) < 2:
            out[f"{tag}_F"] = out[f"{tag}_p"] = out[f"{tag}_eta2"] = float("nan")
            continue
        F, p = stats.f_oneway(*groups)
        allv = np.concatenate(groups)
        gm = allv.mean()
        ssb = sum(len(g) * (g.mean() - gm) ** 2 for g in groups)
        sst = ((allv - gm) ** 2).sum()
        out[f"{tag}_F"] = float(F)
        out[f"{tag}_p"] = float(p)
        out[f"{tag}_eta2"] = float(ssb / sst) if sst > 0 else float("nan")
    return out


def evaluate_segmentation(lengths_of: Dict[str, List[int]]) -> Dict[str, float]:
    """한 가지 분할 방식에 대해 모든 지표를 계산한다."""
    feats, homo, bcontrast = [], [], []
    seg_owner: List[str] = []      # 각 세그먼트의 피험자 (dwell time 계산용)
    seg_len: List[int] = []        # 각 세그먼트의 길이 [TP] (시간 순서 유지)

    for sid in subjects:
        ts = ts_of[sid]
        spans = boundaries_from_lengths(lengths_of[sid])

        for (s, e) in spans:
            seg_owner.append(sid)
            seg_len.append(e - s)
            seg = ts[s:e]
            feats.append(cm_flat(seg))

            # (1) 세그먼트 내부 동질성 — 전/후반 CM 상관
            half = (e - s) // 2
            if half >= MIN_HALF:
                c = corr(cm_flat(ts[s:s + half]), cm_flat(ts[s + half:e]))
                if np.isfinite(c):
                    homo.append(c)

        # (2) 경계 대비 — 경계 양쪽 WIN TP의 CM 상관
        for (s, e) in spans[:-1]:
            b = e                                  # 경계 위치
            if b - WIN < 0 or b + WIN > ts.shape[0]:
                continue
            c = corr(cm_flat(ts[b - WIN:b]), cm_flat(ts[b:b + WIN]))
            if np.isfinite(c):
                bcontrast.append(c)

    X = np.vstack(feats)
    Xs = StandardScaler().fit_transform(X)

    res = {
        "within_segment_homogeneity": float(np.mean(homo)),
        "boundary_contrast": float(np.mean(bcontrast)),
        "n_segments": X.shape[0],
        "n_homo_pairs": len(homo),
        "n_boundaries": len(bcontrast),
    }

    # (3) 클러스터링 품질 — silhouette
    # (5) dwell time — 같은 군집 레이블로 state별 체류 시간을 계산해 ANOVA
    for K in K_LIST:
        km = KMeans(n_clusters=K, n_init=10, max_iter=300, random_state=SEED)
        lab = km.fit_predict(Xs)
        res[f"silhouette_K{K}"] = float(silhouette_score(Xs, lab))
        for name, val in dwell_anova(lab, seg_owner, seg_len).items():
            res[f"{name}_K{K}"] = val

    # (4) 전역강도 축 지배성 — PC1 설명분산 / PC1과 평균 FC 강도의 상관
    Xc = Xs - Xs.mean(0)
    # 공분산 고유값 대신 SVD (4950차원이지만 n=308이라 경제적)
    U, S, _ = np.linalg.svd(Xc, full_matrices=False)
    var = S ** 2
    res["pc1_explained_var"] = float(var[0] / var.sum())
    pc1 = U[:, 0] * S[0]
    strength = X.mean(1)                      # 세그먼트별 평균 FC 강도
    res["pc1_vs_global_strength_r"] = float(abs(corr(pc1, strength)))
    return res


print("\n" + "=" * 70)
print("STAGE 2: 실제 분할(MTAD-GAT) 지표 계산")
print("=" * 70)
real = evaluate_segmentation(real_lengths)
for k, v in real.items():
    print(f"  {k:<32s} {v:.4f}" if isinstance(v, float) else f"  {k:<32s} {v}")


# =============================================================================
# STAGE 3: 무작위 분할 귀무분포
# =============================================================================
# 피험자 내에서 실제 세그먼트 길이의 **순서만** 섞는다.
#   → 세그먼트 개수와 길이 분포는 실제와 완전히 동일
#   → 경계 위치만 달라짐
print("\n" + "=" * 70)
print(f"STAGE 3: 무작위 분할 {N_PERM}회 반복")
print("=" * 70)

rng = np.random.default_rng(SEED)
null_rows = []
for it in range(N_PERM):
    shuffled = {sid: list(rng.permutation(real_lengths[sid])) for sid in subjects}
    r = evaluate_segmentation(shuffled)
    r["iter"] = it
    null_rows.append(r)
    if (it + 1) % 10 == 0 or it == 0:
        print(f"  [{it + 1:>4d}/{N_PERM}] "
              f"homo={r['within_segment_homogeneity']:.4f} "
              f"bcon={r['boundary_contrast']:.4f} "
              f"sil(K=2)={r['silhouette_K2']:.4f}")

df_null = pd.DataFrame(null_rows)
df_null.to_csv(CSV_PATH / "null_distribution.csv", index=False)
print(f"  저장: {CSV_PATH / 'null_distribution.csv'}")


# =============================================================================
# STAGE 4: permutation p-value
# =============================================================================
# 방향: higher=True  → 실제값이 클수록 가설에 유리
#       higher=False → 실제값이 작을수록 가설에 유리 (경계 대비)
METRICS = [
    ("within_segment_homogeneity", "세그먼트 내부 동질성", True,
     "세그먼트 전/후반 CM 상관 — 경계가 맞으면 세그먼트 안은 균질해야 함"),
    ("boundary_contrast", "경계 대비", False,
     "경계 양쪽 윈도우 CM 상관 — 진짜 전환점이면 양쪽이 달라야 함"),
    ("silhouette_K2", "클러스터링 품질 (K=2)", True, "세그먼트 CM 군집의 silhouette"),
    ("silhouette_K3", "클러스터링 품질 (K=3)", True, "세그먼트 CM 군집의 silhouette"),
    ("silhouette_K4", "클러스터링 품질 (K=4)", True, "세그먼트 CM 군집의 silhouette"),
    ("dwell_occ_eta2_K4", "Dwell time: 총 점유 시간 (K=4)", True,
     "state별 총 점유 시간 차이의 효과크기 eta^2 — state가 진짜면 더 크게 갈려야 함"),
    ("dwell_bout_eta2_K4", "Dwell time: 방문당 체류 시간 (K=4)", True,
     "state별 방문당 체류 시간 차이의 효과크기 eta^2"),
]

print("\n" + "=" * 70)
print("STAGE 4: Permutation 검정 결과")
print("=" * 70)

rows = []
for key, label, higher, desc in METRICS:
    obs = real[key]
    null = df_null[key].to_numpy()
    # 단측 permutation p-value (관측값 포함)
    if higher:
        p = (1 + int(np.sum(null >= obs))) / (1 + len(null))
    else:
        p = (1 + int(np.sum(null <= obs))) / (1 + len(null))
    z = (obs - null.mean()) / null.std(ddof=1) if null.std(ddof=1) > 0 else np.nan
    pct = float((null < obs).mean() * 100)
    rows.append({
        "metric": key, "label": label, "방향": "클수록 유리" if higher else "작을수록 유리",
        "observed": obs, "null_mean": float(null.mean()), "null_sd": float(null.std(ddof=1)),
        "null_min": float(null.min()), "null_max": float(null.max()),
        "z": float(z), "percentile": pct, "p_perm": p,
        "significant": bool(p < 0.05), "desc": desc,
    })
    verdict = "✅ 유의" if p < 0.05 else "❌ 무작위와 구별 안 됨"
    print(f"\n  [{label}]  {desc}")
    print(f"    관측값(MTAD-GAT) = {obs:.4f}")
    print(f"    무작위 분포      = {null.mean():.4f} ± {null.std(ddof=1):.4f} "
          f"[{null.min():.4f}, {null.max():.4f}]")
    print(f"    z = {z:+.2f}, 백분위 = {pct:.1f}%, permutation p = {p:.4f}  {verdict}")

df_test = pd.DataFrame(rows)
df_test.to_csv(CSV_PATH / "permutation_test.csv", index=False)

# (4) 전역강도 축 — 가설 검정이 아니라 해석용
print("\n  [참고] 전역강도 축 지배성 (가설 검정 아님)")
print(f"    PC1 설명분산        : 실제 {real['pc1_explained_var']:.3f} vs "
      f"무작위 {df_null['pc1_explained_var'].mean():.3f} ± {df_null['pc1_explained_var'].std(ddof=1):.3f}")
print(f"    |corr(PC1, 평균 FC)| : 실제 {real['pc1_vs_global_strength_r']:.3f} vs "
      f"무작위 {df_null['pc1_vs_global_strength_r'].mean():.3f} ± "
      f"{df_null['pc1_vs_global_strength_r'].std(ddof=1):.3f}")

pd.DataFrame([real]).to_csv(CSV_PATH / "observed_metrics.csv", index=False)


# =============================================================================
# STAGE 5: 그림
# =============================================================================
print("\n" + "=" * 70)
print("STAGE 5: 그림 생성")
print("=" * 70)

n_panel = len(METRICS) + 1          # 지표 + 전역강도 참고 패널
ncol = 4
nrow = int(np.ceil(n_panel / ncol))
fig, axes = plt.subplots(nrow, ncol, figsize=(5.4 * ncol, 4.3 * nrow))
axes = axes.ravel()
for ax, (key, label, higher, desc) in zip(axes, METRICS):
    null = df_null[key].to_numpy()
    obs = real[key]
    r = df_test[df_test.metric == key].iloc[0]
    ax.hist(null, bins=20, color="#B0BEC5", edgecolor="white", label=f"무작위 분할 (n={N_PERM})")
    ax.axvline(obs, color="#E74C3C", lw=2.4, label="MTAD-GAT 분할")
    ax.axvline(null.mean(), color="#546E7A", lw=1.2, ls="--", label="무작위 평균")
    ax.set_title(f"{label}\nz = {r['z']:+.2f}, p = {r['p_perm']:.3f} "
                 f"({'유의' if r['significant'] else 'n.s.'})",
                 fontsize=11, fontweight="bold")
    ax.set_xlabel("클수록 유리 →" if higher else "← 작을수록 유리")
    ax.set_ylabel("빈도")
    ax.legend(fontsize=7.5)
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)

# 참고 패널: 전역강도 축
ax = axes[len(METRICS)]
ax.hist(df_null["pc1_vs_global_strength_r"], bins=20, color="#B0BEC5",
        edgecolor="white", label=f"무작위 분할 (n={N_PERM})")
ax.axvline(real["pc1_vs_global_strength_r"], color="#E74C3C", lw=2.4, label="MTAD-GAT 분할")
ax.set_title("[참고] PC1과 평균 FC 강도의 상관\n(분할 방식과 무관하게 1에 가까움)",
             fontsize=11, fontweight="bold")
ax.set_xlabel("|corr(PC1, 평균 FC 강도)|")
ax.set_ylabel("빈도")
ax.legend(fontsize=7.5)
ax.grid(axis="y", alpha=0.3)
ax.set_axisbelow(True)

for k_ in range(len(METRICS) + 1, len(axes)):
    axes[k_].axis("off")

fig.suptitle("V5: MTAD-GAT 분할 vs 무작위 분할 대조군 — permutation 검정",
             fontsize=13, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.94])
fig.savefig(OUTPUT_PATH / "fig1_permutation_null.png", dpi=160)
plt.close(fig)
print(f"  저장: {OUTPUT_PATH / 'fig1_permutation_null.png'}")

# 요약 그림: z-score 막대
fig, ax = plt.subplots(figsize=(9, 4.4))
labels = [r["label"] for _, r in df_test.iterrows()]
zs = [r["z"] if r["방향"] == "클수록 유리" else -r["z"] for _, r in df_test.iterrows()]
colors = ["#2ECC71" if r["significant"] else "#BDC3C7" for _, r in df_test.iterrows()]
ax.barh(labels, zs, color=colors, edgecolor="white")
ax.axvline(0, color="k", lw=1)
ax.axvline(1.645, color="#E74C3C", ls="--", lw=1.2, label="단측 p=0.05 기준 (z≈1.65)")
ax.set_xlabel("가설에 유리한 방향의 z-score  (무작위 분포 대비)")
ax.set_title("MTAD-GAT 경계는 무작위 경계보다 나은가?", fontsize=12, fontweight="bold")
ax.legend(fontsize=9)
ax.grid(axis="x", alpha=0.3)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(OUTPUT_PATH / "fig2_zscore_summary.png", dpi=160)
plt.close(fig)
print(f"  저장: {OUTPUT_PATH / 'fig2_zscore_summary.png'}")


# =============================================================================
# STAGE 6: 리포트
# =============================================================================
def md_table(df: pd.DataFrame, cols: List[str], fmt: Dict[str, str] = None) -> str:
    fmt = fmt or {}
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
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


n_sig = int(df_test.significant.sum())
L: List[str] = []
A = L.append

A("# V5: 무작위 분할 대조군 — 핵심 가설 검정\n")
A("- 생성 스크립트: `full_pipeline_v5.py`")
A(f"- 무작위 분할 반복 수: **{N_PERM}회**, 경계 대비 윈도우: **{WIN} TP**, seed: {SEED}")
A(f"- 피험자 **{len(subjects)}명**, 세그먼트 **{n_seg_total}개**, "
  f"스캔 길이 {sorted(set(scan_len.values()))[0]} TP")
A("- 귀무 모형: 피험자별 세그먼트 **개수와 길이 분포는 그대로 두고 경계 위치만 무작위 재배치**\n")

A("---\n")
A("## 검정 대상 가설\n")
A("> MTAD-GAT가 탐지한 임베딩 변화점은 단순한 잡음이 아니라, "
  "뇌 기능 상태가 전환되는 의미 있는 경계다.\n")
A("이 가설이 참이라면 MTAD-GAT 경계로 자른 세그먼트는 **무작위로 자른 세그먼트보다** "
  "(a) 내부가 균질하고 (b) 경계를 사이에 두고 FC가 뚜렷이 달라지며 "
  "(c) 상태로 더 잘 군집화되어야 한다. 지금까지의 V1~V4 분석에는 이 비교 대상이 없었다.\n")

A("---\n")
A("## 결론 요약\n")
if n_sig == 0:
    A(f"**{len(df_test)}개 지표 중 단 하나도** MTAD-GAT 분할이 무작위 분할보다 "
      f"유의하게 낫지 않았다 (모두 permutation p ≥ 0.05). "
      f"**핵심 가설은 현재 데이터에서 지지되지 않는다.**\n")
else:
    _fc_ns = int((~df_test.significant & ~df_test.metric.str.startswith("dwell")).sum())
    _fc_tot = int((~df_test.metric.str.startswith("dwell")).sum())
    A(f"{len(df_test)}개 지표 중 **{n_sig}개**에서만 MTAD-GAT 분할이 무작위 분할보다 "
      f"유의하게 나았다 (permutation p < 0.05).\n")
    A(f"- **FC 구조 지표 {_fc_tot}개(세그먼트 내부 동질성·경계 대비·군집 품질)는 "
      f"{_fc_ns}개 모두 무작위와 구별되지 않았다.**")
    A(f"- **유의한 것은 dwell time 지표뿐이다.** 다만 무작위 분할에서도 "
      f"state별 dwell time 차이가 크게 나오므로(η² 평균 "
      f"{df_null['dwell_bout_eta2_K4'].mean():.3f}), V4에서 보고한 dwell time "
      f"ANOVA 자체가 아니라 **무작위 대비 초과분**만이 증거다.\n")
for _, r in df_test.iterrows():
    mark = "**유의**" if r["significant"] else "무작위와 구별 안 됨"
    A(f"- **{r['label']}**: 관측 {r['observed']:.4f} vs 무작위 "
      f"{r['null_mean']:.4f} ± {r['null_sd']:.4f} → z = {r['z']:+.2f}, "
      f"p = {r['p_perm']:.4f} ({mark})")
A("")

A("---\n")
A("## 방법\n")
A("### 귀무 모형 (무작위 분할)\n")
A("```")
A("실제 분할 : 피험자 A의 세그먼트 길이 = [70, 33, 252, 87, ...]  (MTAD-GAT 경계)")
A("무작위 분할: 같은 길이 목록을 무작위로 섞어 배치 = [252, 87, 70, 33, ...]")
A("            → 세그먼트 개수 동일, 길이 분포 동일, 경계 위치만 다름")
A("```\n")
A("길이 분포를 그대로 유지하는 이유: 세그먼트가 짧을수록 CM 추정이 불안정해져 "
  "지표가 달라지므로, 길이를 맞추지 않으면 \"경계 위치의 효과\"와 \"길이의 효과\"가 "
  "뒤섞인다.\n")
A("### 검정 지표\n")
A(md_table(df_test, ["label", "방향", "desc"]).replace("| label | 방향 | desc |",
                                                       "| 지표 | 방향 | 정의 |"))
A("")
A(f"- 모든 CM은 본 파이프라인과 동일하게 Pearson 상관 + Fisher-Z 변환 후 "
  f"상삼각 4,950차원으로 평탄화했다.")
A(f"- silhouette은 표준화된 4,950차원 특징에 KMeans(n_init=10)를 적용해 계산했다.")
A(f"- permutation p-value = (1 + 무작위 중 관측값 이상인 횟수) / (1 + {N_PERM}), 단측.\n")

A("---\n")
A("## 결과\n")
A("### Permutation 검정\n")
_t = df_test.copy()
_t["관측값"] = _t["observed"].map(lambda v: f"{v:.4f}")
_t["무작위 (평균 ± SD)"] = [f"{r.null_mean:.4f} ± {r.null_sd:.4f}" for _, r in _t.iterrows()]
_t["무작위 범위"] = [f"[{r.null_min:.4f}, {r.null_max:.4f}]" for _, r in _t.iterrows()]
_t["백분위"] = _t["percentile"].map(lambda v: f"{v:.1f}%")
_t["판정"] = _t["significant"].map(lambda b: "유의" if b else "n.s.")
A(md_table(_t, ["label", "방향", "관측값", "무작위 (평균 ± SD)", "무작위 범위",
                "z", "백분위", "p_perm", "판정"],
           {"z": "{:+.2f}", "p_perm": "{:.4f}"}).replace("| label |", "| 지표 |"))
A("")
A(f"![permutation null](./{OUTPUT_PATH.name}/fig1_permutation_null.png)\n")
A("*Figure 1. 각 지표의 무작위 분할 귀무분포(회색)와 MTAD-GAT 분할의 관측값(빨간 선). "
  "관측값이 분포 한가운데 있으면 무작위와 구별되지 않는다는 뜻이다.*\n")
A(f"![z-score 요약](./{OUTPUT_PATH.name}/fig2_zscore_summary.png)\n")
A("*Figure 2. 가설에 유리한 방향으로 정렬한 z-score. 점선(z≈1.65)을 넘어야 "
  "단측 p < 0.05다.*\n")

A("### [참고] 전역강도 축은 분할 방식과 무관하게 나타난다\n")
A(f"- PC1 설명분산: MTAD-GAT {real['pc1_explained_var']:.3f} vs "
  f"무작위 {df_null['pc1_explained_var'].mean():.3f} ± "
  f"{df_null['pc1_explained_var'].std(ddof=1):.3f}")
A(f"- |corr(PC1, 세그먼트 평균 FC 강도)|: MTAD-GAT "
  f"{real['pc1_vs_global_strength_r']:.3f} vs 무작위 "
  f"{df_null['pc1_vs_global_strength_r'].mean():.3f} ± "
  f"{df_null['pc1_vs_global_strength_r'].std(ddof=1):.3f}\n")
A("V4 add-on 분석에서 \"K-means가 찾은 축은 사실상 전역 연결강도 하나\"라는 결과가 "
  "나왔는데, 무작위로 잘라도 같은 축이 똑같이 지배적으로 나타난다. "
  "즉 그 축은 MTAD-GAT 분할이 찾아낸 구조가 아니라, **세그먼트 FC 데이터 자체의 "
  "일반적 성질**이다.\n")

A("---\n")
A("## 해석\n")
if n_sig == 0:
    A("1. **핵심 가설이 지지되지 않는다.** MTAD-GAT 임베딩 변화점으로 자른 세그먼트는 "
      "내부 동질성·경계 대비·군집 품질 어느 쪽에서도 무작위 경계와 구별되지 않았다. "
      "지금까지 V1~V4에서 관찰된 \"상태 구조\"는 경계의 품질 때문이 아니라, "
      "시계열을 토막내 FC를 계산하면 **어떻게 자르든** 생기는 구조로 보인다.")
    A("2. **V4의 직교성 결과와 종합하면**, 현재 파이프라인에는 "
      "\"MTAD-GAT 경계가 의미 있다\"를 뒷받침하는 증거가 남아 있지 않다. "
      "(cross-cluster 코사인 역시 서로 다른 모델의 좌표계를 비교한 값이라 "
      "무작위 벡터의 기대값과 구별되지 않는다.)")
    A("3. **논문 프레이밍 전환이 필요하다.** \"새로운 상태 정의 방법 제안\"에서 "
      "\"흔히 쓰이는 분할·군집 관행이 무작위 분할과 구별되지 않는다는 "
      "방법론적 경고\"로 바꾸는 편이 현재 결과로 방어 가능하다.\n")
else:
    _sig = df_test[df_test.significant]
    _ns = df_test[~df_test.significant]
    _bonf = 0.05 / len(df_test)
    _sig_bonf = df_test[df_test.p_perm < _bonf]
    A(f"1. **FC 구조 지표는 전부 무작위와 구별되지 않았다.** "
      + ", ".join(f"{r['label']}(p = {r['p_perm']:.3f})" for _, r in _ns.iterrows())
      + " 모두 유의하지 않았다. 경계가 진짜 상태 전환점이라면 가장 먼저 "
      "드러나야 할 세그먼트 내부 동질성과 경계 대비에서 방향조차 유리하지 않았다는 "
      "점이 특히 중요하다.")
    A(f"2. **유일하게 살아남은 것은 dwell time이다.** "
      + ", ".join(f"{r['label']}: 관측 {r['observed']:.4f} vs 무작위 "
                  f"{r['null_mean']:.4f} ± {r['null_sd']:.4f} (p = {r['p_perm']:.4f})"
                  for _, r in _sig.iterrows())
      + ". 즉 MTAD-GAT 경계로 자르면 state별 체류 시간이 무작위로 자를 때보다 "
      "더 크게 갈린다.")
    A(f"3. **다중비교를 감안하면 더 좁혀야 한다.** {len(df_test)}개 지표를 검정했으므로 "
      f"Bonferroni 기준은 p < {_bonf:.4f}다. 이 기준을 넘는 지표는 "
      + (", ".join(f"**{r['label']}**" for _, r in _sig_bonf.iterrows())
         if len(_sig_bonf) else "**없다**")
      + f"({len(_sig_bonf)}개).")
    A("4. **그래도 과대해석은 금물이다.** 무작위 분할의 dwell time η² 평균이 "
      f"{df_null['dwell_bout_eta2_K4'].mean():.3f}나 된다는 점에 주목해야 한다. "
      "즉 **아무렇게나 잘라도** state별 체류 시간 차이는 크게 나오며, 실제로 "
      "무작위 분할의 상당수가 통계적으로 유의한 ANOVA 결과를 낸다. 따라서 V4 "
      "리포트의 dwell time ANOVA(p < 0.001) 자체는 증거가 되지 못하고, "
      "**무작위 대비 초과분**만이 증거다.")
    A("5. **대안 설명을 배제하지 못했다.** 세그먼트가 길수록 더 긴 시간을 평균하므로 "
      "FC 크기가 낮게 추정되는 경향이 있다. 이 길이↔FC강도 결합은 귀무 모형에도 "
      "존재하지만(그래서 무작위 η²도 0이 아니다), 실제 분할에서 더 강하게 나타났을 "
      "수 있다. 또한 방문당 체류 시간은 인접 세그먼트가 같은 state로 묶이는 정도에 "
      "민감한데, 이는 \"경계가 정확하다\"는 뜻일 수도 있고 반대로 "
      "\"한 상태를 불필요하게 여러 번 잘랐다(과분할)\"는 뜻일 수도 있다. "
      "두 해석을 가르려면 경계 수를 바꿔가며 재검정해야 한다.")
    A("6. **종합하면**, \"MTAD-GAT 경계가 FC 구조상 의미 있는 상태 전환점\"이라는 "
      "원래 가설은 지지되지 않는다. 지지되는 것은 그보다 훨씬 약한 주장 — "
      "\"MTAD-GAT 경계는 state 체류 시간의 분포에 무작위가 아닌 영향을 준다\" — "
      "뿐이며, 이것도 대안 설명이 남아 있다.\n")

A("---\n")
A("## 이 검정의 한계\n")
A("1. **BrainLM 재학습은 포함하지 않았다.** 상태별 트랜스포머를 무작위 분할마다 "
  "다시 학습하는 것은 계산량이 과도하다. 다만 세그먼트 경계 자체가 무작위와 "
  "구별되지 않는다면 그 뒤 표현학습 단계를 검정할 의미가 적다.")
A("2. **귀무 모형은 길이 분포를 보존하는 한 가지 방식만 사용했다.** "
  "피험자 내 길이 순서를 섞는 방식이므로, 가능한 경계 배치의 일부만 탐색한다. "
  "더 엄격하게 하려면 최소 길이 제약 하에서 경계를 균등 무작위로 뽑는 변형도 "
  "함께 보고하는 것이 좋다.")
A("3. **지표는 FC 기반이다.** MTAD-GAT 경계가 FC가 아닌 다른 측면(예: 신호 진폭, "
  "주파수 구성)에서 의미 있는 전환점일 가능성은 이 검정으로 배제되지 않는다.")
A(f"4. **표본이 {len(subjects)}명으로 작다.** 효과가 작다면 검정력 부족으로 "
  f"놓쳤을 수 있다.\n")

A("---\n")
A("## 산출물\n")
A(f"- 그림: `{OUTPUT_PATH.name}/fig1_permutation_null.png`, "
  f"`{OUTPUT_PATH.name}/fig2_zscore_summary.png`")
A(f"- 표(CSV): `{OUTPUT_PATH.name}/tables/`")
A("  - `observed_metrics.csv` — MTAD-GAT 분할의 지표값")
A(f"  - `null_distribution.csv` — 무작위 분할 {N_PERM}회의 지표값")
A("  - `permutation_test.csv` — permutation 검정 결과 (z, p)")

REPORT_PATH.write_text("\n".join(L), encoding="utf-8")
print(f"\n  리포트 저장: {REPORT_PATH}")

summary = {
    "n_perm": N_PERM, "window": WIN, "seed": SEED,
    "n_subjects": len(subjects), "n_segments": n_seg_total,
    "observed": real,
    "permutation_test": df_test.drop(columns=["desc"]).to_dict("records"),
    "n_significant": n_sig,
}
with open(OUTPUT_PATH / "v5_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

print("\n" + "=" * 70)
print("완료")
print("=" * 70)
print(f"  리포트 : {REPORT_PATH}")
print(f"  그림/표: {OUTPUT_PATH}")
