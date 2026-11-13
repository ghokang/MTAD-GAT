"""
V7: 공유 BrainLM 하나로 학습 → latent를 같은 공간에서 비교

V6와의 관계
-----------
V6는 State별로 모델을 따로 학습한다(교수님 요청 방식). V7은 같은 윈도우
데이터를 쓰되 모델을 하나만 학습해, latent를 같은 좌표계에서 비교할 수 있게 한다.

문제의식
--------
State별로 모델을 따로 학습하면 각 모델의 latent 좌표계가 공유되지 않는다.
따라서 cross-state 코사인도, 여러 모델의 latent를 한 평면에 겹쳐 그린 PCA/t-SNE도
State 분리의 증거가 되지 못한다(무작위 벡터와 구별되지 않음).

해결
----
모든 State 데이터로 BrainLM "하나"를 학습하면 모든 윈도우의 latent가 같은 공간에
놓인다. 그러면 다음 질문이 well-posed 해진다.

  (1) latent를 t-SNE / PCA로 그렸을 때 State가 갈리는가  → 정당한 시각화
  (2) 처음 보는 피험자에서 latent로 State를 맞힐 수 있는가 → 분류 정확도
  (3) 그 정확도가 우연보다 높은가                         → 레이블 치환 귀무분포

귀무 모형은 세그먼트 단위로 레이블을 치환한다. 같은 세그먼트에서 나온 윈도우들은
서로 강하게 상관되므로, 윈도우 단위로 섞으면 귀무분포가 지나치게 느슨해진다.

실행: python full_pipeline_v7.py --k 2 --window 64 --stride 32 --n-perm 20
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.manifold import TSNE
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from brainlm.ts_dataset import FeatureNormalizer, TSConcatDataset  # noqa: E402
from brainlm.ts_model import BrainLMTimeSeriesConfig  # noqa: E402
from brainlm.ts_train import extract_ts_latents, train_brainlm_ts  # noqa: E402
from pipeline.clustering import perform_clustering  # noqa: E402
from pipeline.connectivity import collect_all_cms_flat, compute_all_cms  # noqa: E402
from pipeline.v3_sequences import TSConcatExample, split_examples  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--k", type=int, default=2)
ap.add_argument("--window", type=int, default=64)
ap.add_argument("--stride", type=int, default=32)
ap.add_argument("--n-perm", type=int, default=20)
ap.add_argument("--max-epochs", type=int, default=50)
args = ap.parse_args()

K, WIN, STRIDE, NPERM = args.k, args.window, args.stride, args.n_perm
MASK_RATIO, BATCH, LR, PATIENCE = 0.15, 8, 1e-4, 10
SEED = 42
OUT = ROOT / f"visualization_ver7_k{K}"
(OUT / "tables").mkdir(parents=True, exist_ok=True)
CKPT = ROOT / "checkpoint" / f"brainlm_v7_k{K}"
CKPT.mkdir(parents=True, exist_ok=True)
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

for _f in ("AppleGothic", "Apple SD Gothic Neo", "NanumGothic", "Malgun Gothic"):
    try:
        matplotlib.font_manager.findfont(_f, fallback_to_default=False)
        plt.rcParams["font.family"] = _f
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False
COLORS = ["#E74C3C", "#3498DB", "#2ECC71", "#F39C12"]

print("=" * 72)
print(f"V7 (K={K}): 공유 BrainLM 하나로 학습 → 같은 공간에서 latent 비교")
print(f"  윈도우 {WIN} TP ({WIN*0.72:.1f}초), 보폭 {STRIDE}, device {device}")
print("=" * 72)

# ── STAGE 1: 세그먼트 → CM → 클러스터링 ────────────────────────────────────
with open(ROOT / "checkpoint" / "brainlm_v3" / "cache" / "all_segments.pkl", "rb") as f:
    all_segments = pickle.load(f)
all_cms = compute_all_cms(all_segments, method="pearson", min_segment_len=10,
                          use_fisher_z=True)
X_cm, cm_labels = collect_all_cms_flat(all_cms)
clu = perform_clustering(X_cm, cm_labels, n_clusters=K, standardize=True,
                         use_minibatch=True, n_init=4, max_iter=200, batch_size=256,
                         skip_silhouette=True, random_state=SEED)
seg2state = {lab: int(c) for lab, c in zip(cm_labels, clu.labels)}
subjects = sorted(all_segments)

# ── STAGE 2: 윈도우 생성 (모든 State를 한 데 모음) ──────────────────────────
# 핵심 차이: State별로 나누지 않고 전체를 하나의 학습 집합으로 쓴다.
exs, w_state, w_subject, w_segkey = [], [], [], []
for cid in range(K):
    pieces = []
    for sid in subjects:
        for s in sorted(all_segments[sid], key=lambda z: z.start_idx):
            if seg2state.get((sid, s.segment_id)) == cid:
                pieces.append((sid, int(s.segment_id),
                               np.asarray(s.data, dtype=np.float32)))
    if not pieces:
        continue
    long_ts = np.concatenate([p[2] for p in pieces], axis=0)
    bounds = np.cumsum([0] + [p[2].shape[0] for p in pieces])
    owner = np.empty(long_ts.shape[0], dtype=object)
    segk = np.empty(long_ts.shape[0], dtype=object)
    for i, (sid, segid, _) in enumerate(pieces):
        owner[bounds[i]:bounds[i + 1]] = sid
        segk[bounds[i]:bounds[i + 1]] = f"{sid}_{segid}"
    for st in range(0, long_ts.shape[0] - WIN + 1, STRIDE):
        w = owner[st:st + WIN]
        vals, cnts = np.unique(w.astype(str), return_counts=True)
        major = str(vals[np.argmax(cnts)])
        sv, sc = np.unique(segk[st:st + WIN].astype(str), return_counts=True)
        exs.append(TSConcatExample(subject_id=major, cluster_id=cid,
                                   segment_ids=(0,), x=long_ts[st:st + WIN]))
        w_state.append(cid)
        w_subject.append(major)
        w_segkey.append(str(sv[np.argmax(sc)]))

w_state = np.array(w_state)
w_subject = np.array(w_subject)
w_segkey = np.array(w_segkey)
print(f"\n윈도우 {len(exs)}개  (State별: "
      f"{ {int(c): int((w_state == c).sum()) for c in range(K)} })")

# ── STAGE 3: 공유 모델 1개 학습 ────────────────────────────────────────────
print("\n공유 BrainLM 학습 (모든 State 데이터 사용)...")
tr, va, te = split_examples(exs, val_split=0.15, test_split=0.15, seed=SEED)
print(f"  train {len(tr)} / val {len(va)} / test {len(te)} 윈도우")
norm = FeatureNormalizer().fit(tr)
mk = lambda ds, mr, sh: DataLoader(
    TSConcatDataset(ds, max_time_steps=WIN, mask_ratio=mr, normalizer=norm,
                    augment=False),
    batch_size=BATCH, shuffle=sh, num_workers=0)
cfg = BrainLMTimeSeriesConfig(n_features=100, d_model=256, nhead=8,
                              num_encoder_layers=4, num_decoder_layers=2,
                              dim_feedforward=1024, dropout=0.1,
                              max_time_steps=WIN, mask_ratio=MASK_RATIO)
model, hist = train_brainlm_ts(train_loader=mk(tr, MASK_RATIO, True),
                               val_loader=mk(va, MASK_RATIO, False), config=cfg,
                               max_epochs=args.max_epochs, lr=LR, patience=PATIENCE,
                               checkpoint_dir=CKPT, device=device)
print(f"  best val loss = {min(hist['val_loss']):.3f} ({len(hist['train_loss'])} epochs)")

Z, _, _ = extract_ts_latents(model, mk(exs, 0.0, False), device)
np.save(OUT / "shared_latents.npy", Z)
print(f"  latent {Z.shape}  ← 모든 윈도우가 같은 공간")

# ── STAGE 4: 분류 — 처음 보는 피험자에서 State를 맞힐 수 있는가 ────────────
Zs = StandardScaler().fit_transform(Z)
gkf = GroupKFold(n_splits=5)


def cv_balanced_acc(y):
    accs = []
    for tr_i, te_i in gkf.split(Zs, y, groups=w_subject):
        if len(np.unique(y[tr_i])) < 2:
            continue
        clf = LogisticRegression(max_iter=2000, C=1.0)
        clf.fit(Zs[tr_i], y[tr_i])
        accs.append(balanced_accuracy_score(y[te_i], clf.predict(Zs[te_i])))
    return float(np.mean(accs)), accs


obs_acc, fold_accs = cv_balanced_acc(w_state)
chance = 1.0 / K
print(f"\n분류 (피험자 단위 5-fold, 균형정확도): {obs_acc:.4f}  (우연 수준 {chance:.3f})")
print("  fold별:", np.round(fold_accs, 3))

# 귀무분포: 세그먼트 단위로 레이블 치환
print(f"\n귀무분포 — 세그먼트 단위 레이블 치환 {NPERM}회...")
seg_keys = np.unique(w_segkey)
seg_label = {s: w_state[w_segkey == s][0] for s in seg_keys}
rng = np.random.default_rng(SEED)
null_accs = []
for it in range(NPERM):
    vals = np.array([seg_label[s] for s in seg_keys])
    rng.shuffle(vals)
    perm = dict(zip(seg_keys, vals))
    y_perm = np.array([perm[s] for s in w_segkey])
    a, _ = cv_balanced_acc(y_perm)
    null_accs.append(a)
null_accs = np.array(null_accs)
ge = int((null_accs >= obs_acc).sum())
p_perm = (1 + ge) / (1 + NPERM)
z = (obs_acc - null_accs.mean()) / null_accs.std(ddof=1)
print(f"  귀무 평균 {null_accs.mean():.4f} ± {null_accs.std(ddof=1):.4f} "
      f"[{null_accs.min():.4f}, {null_accs.max():.4f}]")
print(f"  z = {z:+.2f}, 치환 중 관측값 이상 {ge}/{NPERM} → permutation p = {p_perm:.4f}")

# ── STAGE 5: 시각화 ────────────────────────────────────────────────────────
Zl = Z / (np.linalg.norm(Z, axis=1, keepdims=True) + 1e-12)
fig, axes = plt.subplots(1, 3, figsize=(16.5, 4.8))

p2 = PCA(n_components=2).fit(Zl)
P = p2.transform(Zl)
for c in range(K):
    m = w_state == c
    axes[0].scatter(P[m, 0], P[m, 1], s=13, alpha=0.6, color=COLORS[c % 4],
                    label=f"State {c} (n={m.sum()})", edgecolor="none")
axes[0].set_title(f"PCA  (설명분산 {p2.explained_variance_ratio_[:2].sum()*100:.1f}%)",
                  fontsize=12, fontweight="bold")
axes[0].set_xlabel("PC1"); axes[0].set_ylabel("PC2")
axes[0].legend(fontsize=9, markerscale=1.6); axes[0].grid(alpha=0.3)

T = TSNE(n_components=2, perplexity=30, init="pca", random_state=0).fit_transform(Zl)
for c in range(K):
    m = w_state == c
    axes[1].scatter(T[m, 0], T[m, 1], s=13, alpha=0.6, color=COLORS[c % 4],
                    label=f"State {c}", edgecolor="none")
axes[1].set_title("t-SNE", fontsize=12, fontweight="bold")
axes[1].legend(fontsize=9, markerscale=1.6); axes[1].grid(alpha=0.3)

axes[2].hist(null_accs, bins=min(12, max(4, NPERM // 2)), color="#B0BEC5",
             edgecolor="white", label=f"레이블 치환 ({NPERM}회)")
axes[2].axvline(obs_acc, color="#E74C3C", lw=2.6, label=f"실제 ({obs_acc:.3f})")
axes[2].axvline(chance, color="#546E7A", lw=1.3, ls=":", label=f"우연 ({chance:.2f})")
axes[2].set_xlabel("균형정확도 (피험자 단위 5-fold)")
axes[2].set_ylabel("빈도")
axes[2].set_title(f"latent로 State를 맞힐 수 있는가\nz = {z:+.2f},  p = {p_perm:.3f}",
                  fontsize=12, fontweight="bold")
axes[2].legend(fontsize=8.5); axes[2].grid(axis="y", alpha=0.3)
axes[2].set_axisbelow(True)

fig.suptitle(f"V7 (K={K}): 공유 모델 하나로 학습한 latent — 같은 공간에서의 정당한 비교",
             fontsize=13, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.91])
fig.savefig(OUT / "fig1_shared_latent.png", dpi=160)
plt.close(fig)
print(f"\n  저장: {OUT / 'fig1_shared_latent.png'}")

pd.DataFrame({"fold_balanced_acc": fold_accs}).to_csv(
    OUT / "tables" / "cv_folds.csv", index=False)
pd.DataFrame({"null_balanced_acc": null_accs}).to_csv(
    OUT / "tables" / "null_accs.csv", index=False)
json.dump({
    "K": K, "window": WIN, "stride": STRIDE, "n_windows": int(len(exs)),
    "per_state": {int(c): int((w_state == c).sum()) for c in range(K)},
    "best_val_loss": float(min(hist["val_loss"])),
    "observed_balanced_acc": obs_acc, "chance": chance,
    "null_mean": float(null_accs.mean()), "null_sd": float(null_accs.std(ddof=1)),
    "z": float(z), "n_perm": NPERM, "p_perm": float(p_perm),
}, open(OUT / f"v7_k{K}_summary.json", "w"), indent=2, ensure_ascii=False,
    default=float)
print("완료")
