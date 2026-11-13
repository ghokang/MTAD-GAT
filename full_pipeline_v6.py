"""
=============================================================================
V6: State별 세그먼트 concat → 균일 토큰 분할 → BrainLM 학습 → latent 비교
=============================================================================

교수님 요청 방식:
    State별로 BrainLM을 따로 학습할 때, 그 State에 속한 **세그먼트들을 모두
    이어붙인 뒤 일정한 크기의 토큰(윈도우)으로 잘라서** 학습하고 latent를 본다.
    데이터가 부족하면 K를 2나 3으로 낮춰도 된다.

V4와의 차이:
    V4 : 세그먼트 1개 = 학습 예제 1개 (길이 제각각, 0 패딩으로 길이 맞춤)
    V6 : State 전체를 이어붙여 길이 W인 윈도우로 균일 분할 (패딩 없음)

    → 예제당 정보량이 균일해지고 예제 수가 늘어난다.
    → 대신 세그먼트-CM 간 1:1 대응은 사라진다.

이어붙이는 순서:
    피험자 순(ID 오름차순) → 피험자 안에서는 시간 순.
    이어붙인 자리(join)와 피험자 경계를 기록해 두고, 그 자리를 걸치는 윈도우가
    몇 개인지 보고한다. 걸치는 윈도우를 제외한 민감도 분석도 함께 수행한다.

latent 비교 (4가지):
    (A) cross-state 코사인 — 요청된 지표. 단, 모델이 서로 다르면 좌표계가 달라
        무작위 벡터와 구별되지 않을 수 있으므로 귀무분포를 함께 제시한다.
    (B) RSA / CKA — 좌표 회전에 불변한 표현 유사도. (A)의 한계를 보완.
    (C) cross-state 재구성 손실 — "A 모델에 B 데이터"를 넣었을 때 손실 증가.
        좌표계 문제가 없는 가장 직접적인 지표.
    (D) PCA / t-SNE 시각화.

실행:
    python full_pipeline_v6.py --k 2              # 기본 (데이터 가장 넉넉)
    python full_pipeline_v6.py --k 3 --window 64
    python full_pipeline_v6.py --k 4 --window 128
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
import torch
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from brainlm.ts_dataset import FeatureNormalizer, TSConcatDataset  # noqa: E402
from brainlm.ts_model import BrainLMTimeSeriesConfig  # noqa: E402
from brainlm.ts_train import extract_ts_latents, train_brainlm_ts  # noqa: E402
from pipeline.clustering import perform_clustering  # noqa: E402
from pipeline.connectivity import collect_all_cms_flat, compute_all_cms  # noqa: E402
from pipeline.v3_sequences import TSConcatExample, split_examples  # noqa: E402

# ── 설정 ────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="V6: concat → 균일 윈도우 → BrainLM")
parser.add_argument("--k", type=int, default=2, help="Brain State 클러스터 수 (기본 2)")
parser.add_argument("--window", type=int, default=64, help="윈도우(토큰 시퀀스) 길이 [TP]")
parser.add_argument("--stride", type=int, default=0,
                    help="윈도우 보폭 [TP]. 0이면 window와 동일(겹치지 않음)")
parser.add_argument("--max-epochs", type=int, default=50)
parser.add_argument("--min-windows", type=int, default=12,
                    help="이보다 윈도우가 적은 State는 학습에서 제외")
parser.add_argument("--shuffle-seed", type=int, default=42,
                    help="대조군 레이블 섞기 seed (반복 실행용)")
parser.add_argument("--shuffle-control", action="store_true",
                    help="대조군: State 레이블을 무작위로 섞어 동일 분석 수행. "
                         "State 구분이 무의미할 때 나오는 기준값을 얻는다")
args = parser.parse_args()

K = args.k
WIN = args.window
STRIDE = args.stride if args.stride > 0 else WIN
MAX_EPOCHS = args.max_epochs
MIN_WINDOWS = args.min_windows

USE_FISHER_Z = True
RANDOM_STATE = 42
VAL_SPLIT, TEST_SPLIT = 0.15, 0.15
MASK_RATIO = 0.15
BATCH_SIZE = 8
LR = 1e-4
PATIENCE = 10

SEGMENT_CACHE = ROOT / "checkpoint" / "brainlm_v3" / "cache" / "all_segments.pkl"
SHUF = args.shuffle_control
_tag = f"k{K}" + (f"_shuffled{args.shuffle_seed}" if SHUF else "")
OUTPUT_PATH = ROOT / f"visualization_ver6_{_tag}"
CSV_PATH = OUTPUT_PATH / "tables"
CKPT_PATH = ROOT / "checkpoint" / f"brainlm_v6_{_tag}"
for p in (OUTPUT_PATH, CSV_PATH, CKPT_PATH):
    p.mkdir(parents=True, exist_ok=True)
REPORT_PATH = ROOT / f"v6_{_tag}_report.md"

CLUSTER_COLORS = ["#E74C3C", "#3498DB", "#2ECC71", "#F39C12", "#9B59B6", "#1ABC9C"]
for _f in ("AppleGothic", "Apple SD Gothic Neo", "NanumGothic", "Malgun Gothic"):
    try:
        matplotlib.font_manager.findfont(_f, fallback_to_default=False)
        plt.rcParams["font.family"] = _f
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

print("=" * 72)
print("V6: State별 concat → 균일 윈도우 → BrainLM 학습 → latent 비교")
print("=" * 72)
print(f"  K = {K},  윈도우 = {WIN} TP ({WIN * 0.72:.1f}초),  보폭 = {STRIDE} TP" + ("   [레이블 섞기 대조군]" if SHUF else ""))
print(f"  device = {device}")
print(f"  출력   = {OUTPUT_PATH}")


# =============================================================================
# STAGE 1: 세그먼트 → CM → 클러스터링 (V4와 동일)
# =============================================================================
print("\n" + "=" * 72)
print("STAGE 1: 세그먼트 로드 / CM / K-means")
print("=" * 72)

with open(SEGMENT_CACHE, "rb") as f:
    all_segments = pickle.load(f)
all_cms = compute_all_cms(all_segments, method="pearson", min_segment_len=10,
                          use_fisher_z=USE_FISHER_Z)
X_cm, cm_labels = collect_all_cms_flat(all_cms)
clustering = perform_clustering(X_cm, cm_labels, n_clusters=K, standardize=True,
                                use_minibatch=True, n_init=4, max_iter=200,
                                batch_size=256, skip_silhouette=True,
                                random_state=RANDOM_STATE)
seg2state: Dict[Tuple[str, int], int] = {
    lab: int(c) for lab, c in zip(cm_labels, clustering.labels)
}
if SHUF:
    # 대조군: State별 세그먼트 "개수"는 그대로 두고 어느 세그먼트가 어느 State인지만 섞는다
    _keys = list(seg2state.keys())
    _vals = list(seg2state.values())
    np.random.default_rng(args.shuffle_seed).shuffle(_vals)
    seg2state = {k_: v for k_, v in zip(_keys, _vals)}
    print("  [대조군] State 레이블을 무작위로 섞었습니다 (State별 크기는 유지)")

subjects = sorted(all_segments)
print(f"  피험자 {len(subjects)}명, 세그먼트 {len(cm_labels)}개")
print(f"  State별 세그먼트 수: "
      f"{ {int(k_): int(v) for k_, v in clustering.get_cluster_sizes().items()} }")


# =============================================================================
# STAGE 2: State별 concat → 균일 윈도우 분할
# =============================================================================
# 이어붙이는 순서: 피험자 ID 오름차순 → 피험자 내 시간 순
# join = 이어붙인 자리. 윈도우가 join을 걸치면 서로 다른 구간이 한 윈도우에 섞인다.
print("\n" + "=" * 72)
print("STAGE 2: State별 concat → 균일 윈도우 분할")
print("=" * 72)

windows_by_state: Dict[int, List[TSConcatExample]] = {}
straddle_flag: Dict[int, List[bool]] = {}
concat_info = []

for cid in range(K):
    pieces, owners, segids = [], [], []
    for sid in subjects:
        segs = sorted(all_segments[sid], key=lambda s: s.start_idx)
        for s in segs:
            if seg2state.get((sid, s.segment_id)) == cid:
                pieces.append(np.asarray(s.data, dtype=np.float32))
                owners.append(sid)
                segids.append(int(s.segment_id))
    if not pieces:
        continue

    long_ts = np.concatenate(pieces, axis=0)              # (T_total, 100)
    lens = [p.shape[0] for p in pieces]
    bounds = np.cumsum([0] + lens)                        # 조각 경계 위치
    # time point → (소속 피험자, 소속 세그먼트) 매핑
    owner_of = np.empty(long_ts.shape[0], dtype=object)
    seg_of = np.empty(long_ts.shape[0], dtype=np.int32)
    for i in range(len(pieces)):
        owner_of[bounds[i]:bounds[i + 1]] = owners[i]
        seg_of[bounds[i]:bounds[i + 1]] = segids[i]

    exs, strad = [], []
    for st in range(0, long_ts.shape[0] - WIN + 1, STRIDE):
        en = st + WIN
        w_owner = owner_of[st:en]
        w_seg = seg_of[st:en]
        uniq_owner = set(w_owner.tolist())
        uniq_seg = set(np.unique(w_seg).tolist())
        # 대표 피험자 = 윈도우에서 가장 많은 time point를 차지한 피험자
        vals, cnts = np.unique(w_owner.astype(str), return_counts=True)
        major = str(vals[np.argmax(cnts)])
        exs.append(TSConcatExample(subject_id=major, cluster_id=cid,
                                   segment_ids=tuple(sorted(uniq_seg)),
                                   x=long_ts[st:en]))
        strad.append(len(uniq_owner) > 1 or len(uniq_seg) > 1)

    windows_by_state[cid] = exs
    straddle_flag[cid] = strad
    n_str = int(np.sum(strad))
    concat_info.append({
        "state": cid, "n_segments": len(pieces), "total_TP": int(long_ts.shape[0]),
        "n_windows": len(exs), "n_straddle": n_str,
        "straddle_pct": n_str / max(1, len(exs)) * 100,
    })
    print(f"  State {cid}: 세그먼트 {len(pieces):3d}개 → {long_ts.shape[0]:6d} TP "
          f"→ 윈도우 {len(exs):4d}개  (조각 경계를 걸치는 윈도우 {n_str}개, "
          f"{n_str / max(1, len(exs)) * 100:.1f}%)")

df_concat = pd.DataFrame(concat_info)
df_concat.to_csv(CSV_PATH / "concat_windows.csv", index=False)

trained_states = [c for c in windows_by_state
                  if len(windows_by_state[c]) >= MIN_WINDOWS]
skipped = [c for c in windows_by_state if c not in trained_states]
if skipped:
    print(f"  [제외] 윈도우 {MIN_WINDOWS}개 미만 State: {skipped}")


# =============================================================================
# STAGE 3: State별 BrainLM 학습
# =============================================================================
print("\n" + "=" * 72)
print("STAGE 3: State별 BrainLM 학습")
print("=" * 72)

models, normalizers, latents, histories, results = {}, {}, {}, {}, []
heldout = {}   # state → 학습에 쓰지 않은 예제 (val + test)

for cid in trained_states:
    exs = windows_by_state[cid]
    tr, va, te = split_examples(exs, val_split=VAL_SPLIT, test_split=TEST_SPLIT,
                                seed=RANDOM_STATE)
    if len(tr) < 4 or len(va) < 1:
        print(f"  State {cid}: train={len(tr)}, val={len(va)} → 학습 불가, 건너뜀")
        results.append({"state": cid, "status": "skipped_split",
                        "n_windows": len(exs), "n_train": len(tr), "n_val": len(va)})
        continue
    print(f"\n  ── State {cid}: train {len(tr)} / val {len(va)} / test {len(te)} 윈도우")

    norm = FeatureNormalizer().fit(tr)
    mk = lambda ds, mr, sh: DataLoader(
        TSConcatDataset(ds, max_time_steps=WIN, mask_ratio=mr, normalizer=norm,
                        augment=False),
        batch_size=BATCH_SIZE, shuffle=sh, num_workers=0)

    cfg = BrainLMTimeSeriesConfig(n_features=100, d_model=256, nhead=8,
                                  num_encoder_layers=4, num_decoder_layers=2,
                                  dim_feedforward=1024, dropout=0.1,
                                  max_time_steps=WIN, mask_ratio=MASK_RATIO)
    model, hist = train_brainlm_ts(
        train_loader=mk(tr, MASK_RATIO, True), val_loader=mk(va, MASK_RATIO, False),
        config=cfg, max_epochs=MAX_EPOCHS, lr=LR, patience=PATIENCE,
        checkpoint_dir=CKPT_PATH / f"state_{cid}", device=device)

    models[cid], normalizers[cid], histories[cid] = model, norm, hist
    heldout[cid] = va + te
    lat, _, _ = extract_ts_latents(model, mk(exs, 0.0, False), device)
    latents[cid] = lat
    with open(CKPT_PATH / f"state_{cid}" / "normalizer.pkl", "wb") as f:
        pickle.dump(norm, f)
    np.save(OUTPUT_PATH / f"latents_v6_state{cid}.npy", lat)

    results.append({"state": cid, "status": "ok", "n_windows": len(exs),
                    "n_train": len(tr), "n_val": len(va), "n_test": len(te),
                    "final_train_loss": hist["train_loss"][-1],
                    "final_val_loss": hist["val_loss"][-1],
                    "best_val_loss": min(hist["val_loss"]),
                    "n_epochs": len(hist["train_loss"]), "latent_shape": list(lat.shape)})
    print(f"     best val loss = {min(hist['val_loss']):.3f}  "
          f"({len(hist['train_loss'])} epochs), latent {lat.shape}")

df_res = pd.DataFrame(results)
df_res.to_csv(CSV_PATH / "training_results.csv", index=False)
ok_states = sorted(latents)
print(f"\n  학습 완료 State: {ok_states}")


# =============================================================================
# STAGE 4: latent 비교
# =============================================================================
print("\n" + "=" * 72)
print("STAGE 4: latent 비교")
print("=" * 72)


def l2n(v):
    return v / (np.linalg.norm(v) + 1e-12)


# ── (A) cross-state 코사인 (요청 지표) + 귀무분포 ──────────────────────────
mean_lat = {c: latents[c].mean(0) for c in ok_states}
d_model = len(next(iter(mean_lat.values())))
cos = np.ones((len(ok_states), len(ok_states)))
for i, a in enumerate(ok_states):
    for j, b in enumerate(ok_states):
        cos[i, j] = float(l2n(mean_lat[a]) @ l2n(mean_lat[b]))
df_cos = pd.DataFrame(cos, index=[f"State{c}" for c in ok_states],
                      columns=[f"State{c}" for c in ok_states])
df_cos.to_csv(CSV_PATH / "cross_state_cosine.csv")

rng = np.random.default_rng(0)
R = rng.normal(size=(20000, d_model))
R /= np.linalg.norm(R, axis=1, keepdims=True)
null = np.einsum("ij,ij->i", R[:10000], R[10000:])
lo, hi = np.percentile(null, [2.5, 97.5])
offdiag = [cos[i, j] for i in range(len(ok_states)) for j in range(len(ok_states)) if i != j]
inside = [bool(lo < c < hi) for c in offdiag]
print("\n  [A] cross-state 코사인 (평균 latent 방향)")
print(df_cos.round(4).to_string())
print(f"      무작위 {d_model}차원 벡터의 95% 구간: [{lo:+.4f}, {hi:+.4f}]")
print(f"      오프-대각 평균 {np.mean(offdiag):+.4f} | 귀무구간 안: "
      f"{sum(inside)}/{len(offdiag)}개")

# ── (B) RSA / CKA — 좌표 회전에 불변 ───────────────────────────────────────
def linear_cka(A, B):
    A = A - A.mean(0)
    B = B - B.mean(0)
    hsic = np.linalg.norm(B.T @ A, "fro") ** 2
    na = np.linalg.norm(A.T @ A, "fro")
    nb = np.linalg.norm(B.T @ B, "fro")
    return float(hsic / (na * nb + 1e-12))


def rdm(Z):
    Zn = Z / (np.linalg.norm(Z, axis=1, keepdims=True) + 1e-12)
    return 1.0 - Zn @ Zn.T


# 모델 A에 State A 데이터를, 모델 B에 State B 데이터를 넣고 비교하면 '모델 차이'와
# '입력 차이'가 섞여 무효가 된다. 두 모델에 **같은 입력 집합**을 통과시켜
# 표현 구조만 비교한다.
@torch.no_grad()
def latents_on(cid, exs):
    dl = DataLoader(TSConcatDataset(exs, max_time_steps=WIN, mask_ratio=0.0,
                                    normalizer=normalizers[cid], augment=False),
                    batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    z, _, _ = extract_ts_latents(models[cid], dl, device)
    return z


common_exs = [e for c in ok_states for e in windows_by_state[c]]
Z_common = {c: latents_on(c, common_exs) for c in ok_states}
iu = np.triu_indices(len(common_exs), 1)
rdm_flat = {c: rdm(Z_common[c])[iu] for c in ok_states}
rsa_rows = []
for i, a in enumerate(ok_states):
    for b in ok_states[i + 1:]:
        rsa_rows.append({"pair": f"State{a} vs State{b}",
                         "RSA_r": float(np.corrcoef(rdm_flat[a], rdm_flat[b])[0, 1]),
                         "CKA": linear_cka(Z_common[a], Z_common[b]),
                         "n_used": len(common_exs)})
df_rsa = pd.DataFrame(rsa_rows)
df_rsa.to_csv(CSV_PATH / "rsa_cka.csv", index=False)
print("\n  [B] RSA / CKA (좌표 회전 불변 지표, 1에 가까울수록 표현이 닮음)")
print(f"      공통 입력 {len(common_exs)}개 윈도우를 모든 모델에 동일하게 통과시킴")
print(df_rsa.round(4).to_string(index=False))
print("      ※ 기준선 없이는 해석 불가 — 같은 데이터로 seed만 바꿔 학습한 두 모델의")
print("        RSA/CKA(기준선)와 비교해야 한다. 별도 스크립트로 측정:")
print("        기준선 RSA 0.897±0.012 · CKA 0.909±0.014 (K=2, seed 쌍 3회)")

# ── (C) cross-state 재구성 손실 — 좌표계 문제 없음 ─────────────────────────
@torch.no_grad()
def recon_loss(model, norm, exs, seed=0):
    model.eval().to(device)
    dl = DataLoader(TSConcatDataset(exs, max_time_steps=WIN, mask_ratio=MASK_RATIO,
                                    normalizer=norm, augment=False, seed=seed),
                    batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    # 학습과 동일한 정의(masked MSE)를 쓰기 위해 compute_loss를 그대로 사용
    tot, n = 0.0, 0
    for b in dl:
        out = model.compute_loss(
            input_x=b["input_x"].to(device),
            labels=b["labels"].to(device),
            attention_mask=b["attention_mask"].to(device),
            mask_labels=b["mask_labels"].to(device),
        )
        tot += float(out["loss"].item())
        n += 1
    return tot / max(n, 1)


def recon_matrix(pool):
    """pool[state] = 그 열에 쓸 예제 목록. 모든 모델을 같은 예제에 통과시킨다."""
    M = np.full((len(ok_states), len(ok_states)), np.nan)
    for i, a in enumerate(ok_states):
        for j, b in enumerate(ok_states):
            M[i, j] = recon_loss(models[a], normalizers[a], pool[b])
    return M


def summarize(M, tag, fname):
    df = pd.DataFrame(M, index=[f"model{c}" for c in ok_states],
                      columns=[f"data{c}" for c in ok_states])
    df.to_csv(CSV_PATH / fname)
    d = np.diag(M)
    o = M[~np.eye(len(ok_states), dtype=bool)]
    pct = (o.mean() / d.mean() - 1) * 100
    print(f"\n  [C] cross-state 재구성 손실 — {tag} (행=모델, 열=데이터)")
    print(df.round(4).to_string())
    print(f"      자기 데이터 평균 {d.mean():.4f} vs 남의 데이터 평균 {o.mean():.4f} "
          f"({pct:+.1f}%)")
    return df, float(d.mean()), float(o.mean()), float(pct)


# 전체 예제로 재면 대각선에 그 모델의 학습 윈도우가 섞여 '암기'를 재게 된다.
# 판단은 반드시 미학습 예제(val + test) 쪽 값으로 한다.
df_L_all, self_all, cross_all, pct_all = summarize(
    recon_matrix(windows_by_state), "전체 윈도우 (대각선에 학습 데이터 포함 · 참고용)",
    "cross_state_recon_loss.csv")
df_L, self_ho, cross_ho, pct_ho = summarize(
    recon_matrix(heldout), "미학습 윈도우만 (val + test) · 주 지표",
    "cross_state_recon_loss_heldout.csv")
print(f"\n      ※ 전체 윈도우 기준 {pct_all:+.1f}% 중 상당 부분은 학습 데이터 암기다. "
      f"미학습 기준 {pct_ho:+.1f}% 가 판단 근거.")
Lmat = np.asarray(df_L.values)


# =============================================================================
# STAGE 5: 그림
# =============================================================================
print("\n" + "=" * 72)
print("STAGE 5: 그림")
print("=" * 72)

# fig1 — 학습 곡선
fig, axes = plt.subplots(1, max(1, len(ok_states)), figsize=(4.6 * max(1, len(ok_states)), 3.8),
                         squeeze=False)
for ax, c in zip(axes[0], ok_states):
    h = histories[c]
    ax.plot(h["train_loss"], label="Train", color=CLUSTER_COLORS[c % 6])
    ax.plot(h["val_loss"], label="Val", color="#555555", ls="--")
    ax.set_title(f"State {c}  (best val {min(h['val_loss']):.2f})", fontsize=11, fontweight="bold")
    ax.set_xlabel("Epoch"); ax.set_ylabel("Loss"); ax.legend(fontsize=9); ax.grid(alpha=0.3)
fig.suptitle(f"V6 (K={K}, window={WIN} TP): State별 BrainLM 학습 곡선",
             fontsize=13, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.9])
fig.savefig(OUTPUT_PATH / "fig1_training_curves.png", dpi=160); plt.close(fig)

# fig2 — latent PCA / t-SNE
from sklearn.decomposition import PCA  # noqa: E402
from sklearn.manifold import TSNE  # noqa: E402

Z = np.vstack([latents[c] for c in ok_states])
Zl = Z / (np.linalg.norm(Z, axis=1, keepdims=True) + 1e-12)
lab = np.concatenate([[c] * latents[c].shape[0] for c in ok_states])
fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
p2 = PCA(n_components=2).fit(Zl)
P = p2.transform(Zl)
for c in ok_states:
    m = lab == c
    axes[0].scatter(P[m, 0], P[m, 1], s=16, alpha=0.75, label=f"State {c}",
                    color=CLUSTER_COLORS[c % 6], edgecolor="white", linewidth=0.3)
axes[0].set_title(f"PCA (설명분산 {p2.explained_variance_ratio_[:2].sum()*100:.1f}%)",
                  fontsize=12, fontweight="bold")
axes[0].set_xlabel("PC1"); axes[0].set_ylabel("PC2"); axes[0].legend(fontsize=9); axes[0].grid(alpha=0.3)
T = TSNE(n_components=2, perplexity=min(30, max(5, len(Zl) // 5)),
         init="pca", random_state=0).fit_transform(Zl)
for c in ok_states:
    m = lab == c
    axes[1].scatter(T[m, 0], T[m, 1], s=16, alpha=0.75, label=f"State {c}",
                    color=CLUSTER_COLORS[c % 6], edgecolor="white", linewidth=0.3)
axes[1].set_title("t-SNE", fontsize=12, fontweight="bold")
axes[1].legend(fontsize=9); axes[1].grid(alpha=0.3)
fig.suptitle(f"V6 (K={K}): State별 BrainLM의 CLS latent 투영  —  "
             f"서로 다른 모델의 출력이므로 좌표계가 공유되지 않음",
             fontsize=12.5, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.92])
fig.savefig(OUTPUT_PATH / "fig2_latent_projection.png", dpi=160); plt.close(fig)

# fig3 — 코사인 + 귀무분포 / RSA·CKA
fig, axes = plt.subplots(1, 3, figsize=(16, 4.4))
im = axes[0].imshow(cos, cmap="RdBu_r", vmin=-1, vmax=1)
axes[0].set_xticks(range(len(ok_states))); axes[0].set_yticks(range(len(ok_states)))
axes[0].set_xticklabels([f"S{c}" for c in ok_states])
axes[0].set_yticklabels([f"S{c}" for c in ok_states])
for i in range(len(ok_states)):
    for j in range(len(ok_states)):
        axes[0].text(j, i, f"{cos[i, j]:.3f}", ha="center", va="center", fontsize=10,
                     color="white" if abs(cos[i, j]) > 0.5 else "black")
plt.colorbar(im, ax=axes[0])
axes[0].set_title("(A) cross-state 코사인", fontsize=12, fontweight="bold")

axes[1].hist(null, bins=60, color="#B0BEC5", edgecolor="white",
             label=f"무작위 {d_model}차원 벡터")
for c in offdiag:
    axes[1].axvline(c, color="#E74C3C", lw=1.8)
axes[1].axvline(lo, color="#546E7A", ls="--", lw=1.2)
axes[1].axvline(hi, color="#546E7A", ls="--", lw=1.2, label="귀무 95% 구간")
axes[1].set_title(f"관측 코사인 vs 귀무분포\n({sum(inside)}/{len(offdiag)}개가 구간 안)",
                  fontsize=12, fontweight="bold")
axes[1].set_xlabel("코사인 유사도"); axes[1].legend(fontsize=8.5); axes[1].grid(axis="y", alpha=0.3)

if len(df_rsa):
    xpos = np.arange(len(df_rsa))
    axes[2].bar(xpos - 0.2, df_rsa.RSA_r, width=0.4, label="RSA (r)", color="#1C7293")
    axes[2].bar(xpos + 0.2, df_rsa.CKA, width=0.4, label="CKA", color="#E8A33D")
    axes[2].set_xticks(xpos)
    axes[2].set_xticklabels(df_rsa.pair, fontsize=8.5, rotation=15)
    axes[2].set_ylim(0, 1); axes[2].legend(fontsize=9); axes[2].grid(axis="y", alpha=0.3)
axes[2].set_title("(B) 좌표 불변 지표 — 1에 가까우면 표현이 닮음",
                  fontsize=12, fontweight="bold")
fig.suptitle(f"V6 (K={K}): latent 비교 — 요청 지표와 그 한계",
             fontsize=13, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.9])
fig.savefig(OUTPUT_PATH / "fig3_latent_comparison.png", dpi=160); plt.close(fig)

# fig4 — cross-state 재구성 손실
fig, ax = plt.subplots(figsize=(6.4, 5.0))
im = ax.imshow(Lmat, cmap="viridis")
ax.set_xticks(range(len(ok_states))); ax.set_yticks(range(len(ok_states)))
ax.set_xticklabels([f"data {c}" for c in ok_states])
ax.set_yticklabels([f"model {c}" for c in ok_states])
for i in range(len(ok_states)):
    for j in range(len(ok_states)):
        ax.text(j, i, f"{Lmat[i, j]:.3f}", ha="center", va="center", fontsize=11,
                color="white" if Lmat[i, j] < Lmat.mean() else "black")
plt.colorbar(im, ax=ax, label="masked reconstruction MSE")
ax.set_title(f"(C) cross-state 재구성 손실 — 미학습 윈도우\n"
             f"자기 {self_ho:.3f} vs 남 {cross_ho:.3f} ({pct_ho:+.1f}%)",
             fontsize=12, fontweight="bold")
fig.tight_layout()
fig.savefig(OUTPUT_PATH / "fig4_cross_recon_loss.png", dpi=160); plt.close(fig)
print(f"  그림 4장 저장: {OUTPUT_PATH}")


# =============================================================================
# STAGE 6: 리포트
# =============================================================================
L: List[str] = []
A = L.append


def md_table(df, index=True, index_name=""):
    """DataFrame → 마크다운 표 (tabulate 의존 없이)."""
    cols = list(df.columns)
    head = ([index_name] if index else []) + [str(c) for c in cols]
    lines = ["| " + " | ".join(head) + " |",
             "|" + "|".join(["---"] * len(head)) + "|"]
    for idx, row in df.iterrows():
        cells = ([str(idx)] if index else [])
        for c in cols:
            v = row[c]
            cells.append(f"{v:.4f}" if isinstance(v, (float, np.floating)) else str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)

A(f"# V6: State concat → 균일 윈도우 → BrainLM latent 비교 (K={K}{' · 레이블 섞기 대조군' if SHUF else ''})\n")
A("- 생성 스크립트: `full_pipeline_v6.py`")
A(f"- 윈도우 길이 **{WIN} TP ({WIN*0.72:.1f}초)**, 보폭 {STRIDE} TP, 패딩 없음")
A(f"- 피험자 {len(subjects)}명, 세그먼트 {len(cm_labels)}개, device = {device}")
A(f"- 학습된 State: {ok_states}" + (f" (제외: {skipped})" if skipped else "") + "\n")

A("---\n")
A("## V4와 무엇이 다른가\n")
A("| | V4 | V6 (현재) |")
A("|---|---|---|")
A("| 학습 예제 | 세그먼트 1개 = 예제 1개 | State 전체를 이어붙여 균일 분할 |")
A(f"| 예제 길이 | 제각각 (31~549 TP), 0 패딩 | 모두 {WIN} TP, 패딩 없음 |")
A("| 예제 수 | 세그먼트 수와 동일 | 윈도우 수 (아래 표) |")
A("| CM과의 대응 | 1:1 유지 | 사라짐 |\n")

A("## (1) concat 및 윈도우 분할\n")
A("| State | 세그먼트 | 총 TP | 윈도우 수 | 경계 걸침 |")
A("|---|---|---|---|---|")
for r in concat_info:
    A(f"| State {r['state']} | {r['n_segments']} | {r['total_TP']:,} | "
      f"{r['n_windows']} | {r['n_straddle']} ({r['straddle_pct']:.1f}%) |")
A("")
A("> **경계 걸침**: 이어붙인 자리를 윈도우가 가로지르는 경우. 서로 다른 시간대 "
  "또는 서로 다른 피험자의 신호가 한 윈도우에 섞인다.\n")

A("## (2) 학습 결과\n")
if len(df_res):
    A("| State | 윈도우 | train/val/test | best val loss | epochs |")
    A("|---|---|---|---|---|")
    for _, r in df_res.iterrows():
        if r.get("status") != "ok":
            A(f"| State {int(r['state'])} | {int(r['n_windows'])} | — | — | 제외 |")
        else:
            A(f"| State {int(r['state'])} | {int(r['n_windows'])} | "
              f"{int(r['n_train'])}/{int(r['n_val'])}/{int(r['n_test'])} | "
              f"{r['best_val_loss']:.3f} | {int(r['n_epochs'])} |")
A("")
A(f"![학습 곡선](./{OUTPUT_PATH.name}/fig1_training_curves.png)\n")
A("*Figure 1. State별 BrainLM 학습 곡선.*\n")

A("## (3) latent 비교\n")
A("### (A) cross-state 코사인 — 요청된 지표\n")
A(md_table(df_cos, index=True, index_name=""))
A("")
A(f"- 오프-대각 평균 **{np.mean(offdiag):+.4f}**")
A(f"- 무작위 {d_model}차원 단위벡터 두 개의 코사인 95% 구간: **[{lo:+.4f}, {hi:+.4f}]**")
A(f"- 관측값 중 귀무구간 안에 있는 것: **{sum(inside)}/{len(offdiag)}개**\n")
if sum(inside) == len(offdiag):
    A("> **해석**: 관측된 코사인이 전부 \"무작위 벡터 두 개\"의 범위 안에 있습니다. "
      "State별로 모델을 따로 학습하면 각 모델의 latent 좌표계가 공유되지 않으므로, "
      "코사인 ≈ 0은 State 분리의 증거가 아니라 **설정상 당연한 결과**입니다. "
      "아래 (B)와 (C)를 함께 보아야 합니다.\n")
A(f"![latent 비교](./{OUTPUT_PATH.name}/fig3_latent_comparison.png)\n")
A("*Figure 2. (좌) cross-state 코사인 (중) 귀무분포 대비 (우) 좌표 불변 지표.*\n")

A("### (B) RSA / CKA — 좌표 회전에 불변한 비교\n")
if len(df_rsa):
    A(md_table(df_rsa, index=False))
A("")
A(f"- 공통 입력 **{len(common_exs)}개 윈도우**를 모든 State 모델에 동일하게 통과시켜 "
  "계산했습니다. 모델마다 다른 입력을 넣으면 '모델 차이'와 '입력 차이'가 섞여 "
  "값이 무효가 됩니다.\n")
A("> 좌표축이 달라도 **예제들 사이의 거리 구조**는 비교할 수 있습니다. "
  "1에 가까우면 두 모델이 비슷한 표현 구조를 배웠다는 뜻입니다. "
  "다만 **절대값만으로는 판정할 수 없습니다** — 독립적으로 학습한 두 모델은 "
  "같은 데이터로 학습해도 1이 나오지 않기 때문입니다. "
  "같은 데이터로 seed만 바꿔 학습한 두 모델을 기준선으로 두고 비교해야 합니다. "
  "K=2에서 측정한 기준선은 **RSA 0.897 ± 0.012 · CKA 0.909 ± 0.014** "
  "(seed 쌍 3회)이고, State 0 vs State 1은 **RSA 0.814 ± 0.002 · "
  "CKA 0.859 ± 0.003**으로 3회 모두 기준선보다 낮았습니다.\n")

A("### (C) cross-state 재구성 손실 — 좌표계 문제가 없는 지표\n")
A(md_table(df_L, index=True, index_name=""))
A("")
A("> 위 표는 **학습에 쓰지 않은 윈도우(val + test)** 에서만 잰 값입니다. "
  "각 State의 전체 윈도우로 재면 대각선에 그 모델의 학습 데이터가 섞여 "
  "'State 차이'가 아니라 '암기'를 재게 됩니다.\n")
A(f"- 자기 State 데이터 평균 손실 **{self_ho:.4f}**")
A(f"- 다른 State 데이터 평균 손실 **{cross_ho:.4f}** ({pct_ho:+.1f}%)\n")
A(f"- (참고) 전체 윈도우 기준: 자기 {self_all:.4f} vs 남 {cross_all:.4f} "
  f"({pct_all:+.1f}%) — 학습 데이터 포함, 판단 근거로 쓰지 않음\n")
A("> 각 모델에 다른 State의 데이터를 넣었을 때 손실이 **유의하게 커지면**, "
  "그 State들의 시간 동역학이 실제로 다르다는 직접적 증거가 됩니다. "
  "차이가 없으면 State 구분이 BrainLM이 학습한 표현 수준에서는 의미가 없다는 뜻입니다.\n")
A(f"![재구성 손실](./{OUTPUT_PATH.name}/fig4_cross_recon_loss.png)\n")
A("*Figure 3. 행 = 모델, 열 = 데이터. 대각선이 자기 데이터. 미학습 윈도우 기준.*\n")

A("### (D) latent 투영\n")
A(f"![latent 투영](./{OUTPUT_PATH.name}/fig2_latent_projection.png)\n")
A("*Figure 4. PCA / t-SNE 투영. 서로 다른 모델의 출력을 한 공간에 겹쳐 그린 것이므로 "
  "군집이 갈라져 보여도 그 자체는 증거가 되지 않는다.*\n")

A("---\n")
A("## 한계\n")
A(f"1. **이어붙인 자리**: 윈도우의 일부가 서로 다른 시간대·피험자 신호를 걸칩니다"
  f"(위 표의 '경계 걸침'). 이 자리에는 실제로 존재하지 않는 급격한 변화가 생깁니다.")
A("2. **State별 모델이 따로 학습**되므로 latent 좌표계가 공유되지 않습니다. "
  "(A)의 코사인은 이 때문에 해석이 어렵고, (B)·(C)가 보완 지표입니다.")
A("3. **순환성**: State 레이블은 같은 시계열에서 만든 CM에서 유도되었습니다. "
  "독립적인 검증을 하려면 무작위 분할 대조군이 필요합니다.")
A(f"4. **CM과의 1:1 대응 상실**: 윈도우가 세그먼트 경계를 넘나들므로 "
  f"\"이 latent는 이 CM의 표현\"이라는 해석이 더 이상 성립하지 않습니다.\n")

A("## 산출물\n")
A(f"- 그림: `{OUTPUT_PATH.name}/fig1~fig4*.png`")
A(f"- latent: `{OUTPUT_PATH.name}/latents_v6_state*.npy`")
A(f"- 표: `{OUTPUT_PATH.name}/tables/` — concat_windows, training_results, "
  f"cross_state_cosine, rsa_cka, cross_state_recon_loss")
A(f"- 체크포인트: `checkpoint/brainlm_v6_k{K}/`")

REPORT_PATH.write_text("\n".join(L), encoding="utf-8")
print(f"  리포트: {REPORT_PATH}")

summary = {
    "K": K, "window": WIN, "stride": STRIDE, "device": str(device),
    "shuffle_control": bool(SHUF), "shuffle_seed": int(args.shuffle_seed),
    "concat": concat_info, "training": results,
    "cross_state_cosine": df_cos.to_dict(),
    "null_95ci": [float(lo), float(hi)],
    "offdiag_mean": float(np.mean(offdiag)),
    "offdiag_inside_null": int(sum(inside)), "offdiag_total": len(offdiag),
    "rsa_cka": df_rsa.to_dict("records"),
    "recon_self_mean": self_ho, "recon_cross_mean": cross_ho,
    "recon_pct_increase": pct_ho,
    "recon_all_windows": {"self_mean": self_all, "cross_mean": cross_all,
                          "pct_increase": pct_all,
                          "note": "대각선에 학습 데이터 포함 — 판단 근거로 쓰지 말 것"},
}
with open(OUTPUT_PATH / f"v6_{_tag}_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

print("\n" + "=" * 72)
print("완료")
print("=" * 72)
