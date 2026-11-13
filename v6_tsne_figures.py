"""
V6 latent 를 V4와 동일한 방식으로 PCA / t-SNE 투영한다.
  - 모든 State latent 를 쌓고 L2 정규화 (V4: full_pipeline_v4.py fig2 와 동일)
  - 좌: PCA, 우: t-SNE
덧붙여 '눈에 보이는 분리'를 수치로 환산한다 (2D 실루엣, 2D kNN 정확도).
V4 latent 에도 같은 수치를 계산해 비교한다.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.metrics import silhouette_score
from sklearn.model_selection import cross_val_score
from sklearn.neighbors import KNeighborsClassifier

ROOT = Path("/Users/mac/Desktop/code/MTAD-GAT")
V6 = ROOT / "visualization_ver6_k2_stride64"
V4 = ROOT / "visualization_ver4"
COLORS = ["#E74C3C", "#3498DB", "#2ECC71", "#F39C12", "#9B59B6", "#1ABC9C"]

for f in ("AppleGothic", "Apple SD Gothic Neo", "NanumGothic"):
    try:
        matplotlib.font_manager.findfont(f, fallback_to_default=False)
        plt.rcParams["font.family"] = f
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False


def load(d, pat, ks):
    Z, lab = [], []
    for k in ks:
        p = d / pat.format(k)
        if not p.exists():
            continue
        z = np.load(p)
        Z.append(z)
        lab.append(np.full(z.shape[0], k))
    Z = np.vstack(Z)
    return Z / (np.linalg.norm(Z, axis=1, keepdims=True) + 1e-12), np.concatenate(lab)


def scores(E, lab):
    """2D 투영에서의 분리 정도를 수치로."""
    sil = float(silhouette_score(E, lab))
    knn = float(cross_val_score(KNeighborsClassifier(10), E, lab, cv=5,
                                scoring="balanced_accuracy").mean())
    return sil, knn


out = {}

Z6, l6 = load(V6, "latents_v6_state{}.npy", range(6))
Z4, l4 = load(V4, "latents_v4_cluster{}.npy", range(6))
print(f"V6 {Z6.shape} states={sorted(set(l6.tolist()))}")
print(f"V4 {Z4.shape} states={sorted(set(l4.tolist()))}")

for tag, Z, lab in (("v6", Z6, l6), ("v4", Z4, l4)):
    p = PCA(n_components=2, random_state=42)
    P = p.fit_transform(Z)
    perp = min(30, max(5, (len(Z) - 1) // 3))
    T = TSNE(n_components=2, random_state=42, perplexity=perp,
             init="pca", max_iter=1000).fit_transform(Z)
    out[tag] = {
        "n": int(len(Z)),
        "states": {int(c): int((lab == c).sum()) for c in sorted(set(lab.tolist()))},
        "pca_evr": [float(v) for v in p.explained_variance_ratio_[:2]],
        "pca_sil": scores(P, lab)[0], "pca_knn": scores(P, lab)[1],
        "tsne_sil": scores(T, lab)[0], "tsne_knn": scores(T, lab)[1],
        "_P": P, "_T": T, "_lab": lab, "_evr": p.explained_variance_ratio_,
    }
    print(f"  {tag}: PCA sil {out[tag]['pca_sil']:+.3f} kNN {out[tag]['pca_knn']:.3f} | "
          f"t-SNE sil {out[tag]['tsne_sil']:+.3f} kNN {out[tag]['tsne_knn']:.3f}")

# ── V6 단독 그림 (V4 fig2 와 같은 구성) ────────────────────────────────────
o = out["v6"]
fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle("V6 Latent Space — Pooled (L2 정규화 후)\nState별 분리 확인 (K=2, window 64 TP)",
             fontsize=13, fontweight="bold")
for ax, E, ttl in ((axes[0], o["_P"], f"Pooled PCA (L2 norm)"),
                   (axes[1], o["_T"], "Pooled t-SNE (L2 norm)")):
    for c in sorted(set(o["_lab"].tolist())):
        m = o["_lab"] == c
        ax.scatter(E[m, 0], E[m, 1], c=COLORS[c], label=f"State {c} (n={m.sum()})",
                   s=60, alpha=0.8, edgecolors="white", linewidth=0.4)
    ax.set_title(ttl)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
axes[0].set_xlabel(f"PC1 ({o['_evr'][0]*100:.1f}%)")
axes[0].set_ylabel(f"PC2 ({o['_evr'][1]*100:.1f}%)")
axes[1].set_xlabel("t-SNE 1")
axes[1].set_ylabel("t-SNE 2")
fig.tight_layout(rect=[0, 0, 1, 0.92])
fig.savefig(V6 / "fig7_pooled_latent.png", dpi=160)
plt.close(fig)
print(f"\n저장: {V6/'fig7_pooled_latent.png'}")

# ── V4 vs V6 t-SNE 나란히 비교 ─────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(15, 6.4))
fig.suptitle("같은 방식(L2 정규화 후 t-SNE)으로 그린 V4와 V6의 latent — "
             "둘 다 State별 모델이 따로 학습된 상태",
             fontsize=13, fontweight="bold")
for ax, tag, ttl in ((axes[0], "v4", "V4 — 세그먼트 1개 = 예제 1개 (0 패딩)"),
                     (axes[1], "v6", "V6 — State concat 후 64 TP 균일 분할")):
    o = out[tag]
    for c in sorted(set(o["_lab"].tolist())):
        m = o["_lab"] == c
        ax.scatter(o["_T"][m, 0], o["_T"][m, 1], c=COLORS[c],
                   label=f"State {c} (n={m.sum()})", s=46, alpha=0.8,
                   edgecolors="white", linewidth=0.4)
    ax.set_title(f"{ttl}\n2D 실루엣 {o['tsne_sil']:+.3f} · 2D kNN 균형정확도 {o['tsne_knn']:.3f}",
                 fontsize=11, fontweight="bold")
    ax.set_xlabel("t-SNE 1")
    ax.set_ylabel("t-SNE 2")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
fig.tight_layout(rect=[0, 0, 1, 0.90])
fig.savefig(V6 / "fig8_tsne_v4_vs_v6.png", dpi=160)
plt.close(fig)
print(f"저장: {V6/'fig8_tsne_v4_vs_v6.png'}")

clean = {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")}
         for k, v in out.items()}
(V6 / "tsne_compare_summary.json").write_text(
    json.dumps(clean, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(clean, indent=2, ensure_ascii=False))
