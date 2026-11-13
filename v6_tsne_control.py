"""
대조군: t-SNE 분리가 'State 차이' 때문인가, '모델이 다르기' 때문인가?

같은 State 0 데이터로 seed 만 바꿔 두 모델을 학습하고, 각 모델이 자기 데이터에서
뽑은 latent 를 V6/V4 와 똑같은 방식(L2 정규화 → pooled t-SNE)으로 그린다.

여기서도 분리가 되면 → 분리는 State 차이가 아니라 모델이 다르다는 사실의 결과.
"""
import json
import pickle
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.metrics import silhouette_score
from sklearn.model_selection import cross_val_score
from sklearn.neighbors import KNeighborsClassifier
from torch.utils.data import DataLoader

ROOT = Path("/Users/mac/Desktop/code/MTAD-GAT")
sys.path.insert(0, str(ROOT))

from brainlm.ts_dataset import FeatureNormalizer, TSConcatDataset  # noqa: E402
from brainlm.ts_model import BrainLMTimeSeriesConfig  # noqa: E402
from brainlm.ts_train import extract_ts_latents, train_brainlm_ts  # noqa: E402
from pipeline.clustering import perform_clustering  # noqa: E402
from pipeline.connectivity import collect_all_cms_flat, compute_all_cms  # noqa: E402
from pipeline.v3_sequences import TSConcatExample, split_examples  # noqa: E402

OUT = ROOT / "visualization_ver6_k2_stride64"
WIN, STRIDE, K = 64, 64, 2
MASK_RATIO, BATCH, LR, PATIENCE, EPOCHS = 0.15, 8, 1e-4, 10, 50
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

for f in ("AppleGothic", "Apple SD Gothic Neo", "NanumGothic"):
    try:
        matplotlib.font_manager.findfont(f, fallback_to_default=False)
        plt.rcParams["font.family"] = f
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

with open(ROOT / "checkpoint" / "brainlm_v3" / "cache" / "all_segments.pkl", "rb") as f:
    all_segments = pickle.load(f)
all_cms = compute_all_cms(all_segments, method="pearson", min_segment_len=10,
                          use_fisher_z=True)
X_cm, cm_labels = collect_all_cms_flat(all_cms)
clu = perform_clustering(X_cm, cm_labels, n_clusters=K, standardize=True,
                         use_minibatch=True, n_init=4, max_iter=200, batch_size=256,
                         skip_silhouette=True, random_state=42)
seg2state = {lab: int(c) for lab, c in zip(cm_labels, clu.labels)}
subjects = sorted(all_segments)


def windows_of(cid):
    pieces = []
    for sid in subjects:
        for s in sorted(all_segments[sid], key=lambda z: z.start_idx):
            if seg2state.get((sid, s.segment_id)) == cid:
                pieces.append((sid, np.asarray(s.data, dtype=np.float32)))
    long_ts = np.concatenate([p[1] for p in pieces], axis=0)
    bounds = np.cumsum([0] + [p[1].shape[0] for p in pieces])
    owner = np.empty(long_ts.shape[0], dtype=object)
    for i, (sid, _) in enumerate(pieces):
        owner[bounds[i]:bounds[i + 1]] = sid
    exs = []
    for st in range(0, long_ts.shape[0] - WIN + 1, STRIDE):
        w = owner[st:st + WIN]
        v, c = np.unique(w.astype(str), return_counts=True)
        exs.append(TSConcatExample(subject_id=str(v[np.argmax(c)]), cluster_id=cid,
                                   segment_ids=(0,), x=long_ts[st:st + WIN]))
    return exs


def train_and_latent(exs, seed):
    torch.manual_seed(seed)
    np.random.seed(seed)
    tr, va, _ = split_examples(exs, val_split=0.15, test_split=0.15, seed=42)
    norm = FeatureNormalizer().fit(tr)
    mk = lambda ds, mr, sh: DataLoader(
        TSConcatDataset(ds, max_time_steps=WIN, mask_ratio=mr, normalizer=norm,
                        augment=False), batch_size=BATCH, shuffle=sh, num_workers=0)
    cfg = BrainLMTimeSeriesConfig(n_features=100, d_model=256, nhead=8,
                                  num_encoder_layers=4, num_decoder_layers=2,
                                  dim_feedforward=1024, dropout=0.1,
                                  max_time_steps=WIN, mask_ratio=MASK_RATIO)
    m, h = train_brainlm_ts(train_loader=mk(tr, MASK_RATIO, True),
                            val_loader=mk(va, MASK_RATIO, False), config=cfg,
                            max_epochs=EPOCHS, lr=LR, patience=PATIENCE,
                            checkpoint_dir=None, device=device)
    z, _, _ = extract_ts_latents(m, mk(exs, 0.0, False), device)
    return z, float(min(h["val_loss"]))


w0 = windows_of(0)
print(f"State 0 윈도우 {len(w0)}개 — 같은 데이터로 seed만 바꿔 두 번 학습", flush=True)

Z, lab, vls = [], [], {}
for i, seed in enumerate((111, 222)):
    z, vl = train_and_latent(w0, seed)
    vls[seed] = vl
    Z.append(z)
    lab.append(np.full(z.shape[0], i))
    print(f"  seed {seed}: best val {vl:.2f}, latent {z.shape}", flush=True)

Z = np.vstack(Z)
Z = Z / (np.linalg.norm(Z, axis=1, keepdims=True) + 1e-12)
lab = np.concatenate(lab)


def sc(E):
    return (float(silhouette_score(E, lab)),
            float(cross_val_score(KNeighborsClassifier(10), E, lab, cv=5,
                                  scoring="balanced_accuracy").mean()))


p = PCA(n_components=2, random_state=42)
P = p.fit_transform(Z)
T = TSNE(n_components=2, random_state=42, perplexity=30, init="pca",
         max_iter=1000).fit_transform(Z)
ps, pk = sc(P)
ts, tk = sc(T)

COL = ["#9B59B6", "#1ABC9C"]
NAME = ["모델 A (seed 111)", "모델 B (seed 222)"]
fig, axes = plt.subplots(1, 2, figsize=(15, 6.4))
fig.suptitle("대조군 — 같은 State 0 데이터, seed만 다른 두 모델\n"
             "State는 하나뿐인데도 투영에서 갈라지면, 분리는 모델이 다르다는 사실의 결과다",
             fontsize=13, fontweight="bold")
for ax, E, ttl, s, k in ((axes[0], P, "Pooled PCA (L2 norm)", ps, pk),
                         (axes[1], T, "Pooled t-SNE (L2 norm)", ts, tk)):
    for i in (0, 1):
        m = lab == i
        ax.scatter(E[m, 0], E[m, 1], c=COL[i], label=f"{NAME[i]} (n={m.sum()})",
                   s=50, alpha=0.8, edgecolors="white", linewidth=0.4)
    ax.set_title(f"{ttl}\n2D 실루엣 {s:+.3f} · 2D kNN 균형정확도 {k:.3f}",
                 fontsize=11, fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
axes[0].set_xlabel(f"PC1 ({p.explained_variance_ratio_[0]*100:.1f}%)")
axes[0].set_ylabel(f"PC2 ({p.explained_variance_ratio_[1]*100:.1f}%)")
axes[1].set_xlabel("t-SNE 1")
axes[1].set_ylabel("t-SNE 2")
fig.tight_layout(rect=[0, 0, 1, 0.88])
fig.savefig(OUT / "fig9_tsne_seed_control.png", dpi=160)
plt.close(fig)

res = {"n_windows": int(len(w0)), "best_val": vls,
       "pca_sil": ps, "pca_knn": pk, "tsne_sil": ts, "tsne_knn": tk,
       "pca_evr": [float(v) for v in p.explained_variance_ratio_[:2]]}
(OUT / "tsne_seed_control.json").write_text(
    json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
print("\n" + json.dumps(res, indent=2, ensure_ascii=False), flush=True)
print(f"저장: {OUT/'fig9_tsne_seed_control.png'}", flush=True)
