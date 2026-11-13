"""학위논문 그림 생성 (국문판/영문판 각각). 300 DPI, 한글 폰트 임베딩."""
import json, os, sys
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import TwoSlopeNorm
from pathlib import Path
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

ROOT = Path("/Users/mac/Desktop/code/MTAD-GAT")
SCR = ROOT / "thesis"
FIGROOT = ROOT / "thesis" / "figures"

C = ["#C0392B", "#2471A3", "#1E8449", "#B7950B"]   # State 0~3
DPI = 300

d = np.load(SCR / "figdata.npz", allow_pickle=True)
summary = json.loads((ROOT / "visualization_ver4" / "v4_summary.json").read_text())
lat = {c: np.load(ROOT / f"visualization_ver4/latents_v4_cluster{c}.npy") for c in (0, 1, 2)}
latn = {c: v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-8) for c, v in lat.items()}
# 원본 파이프라인과 동일: 원시 latent의 평균을 먼저 구한 뒤 L2 정규화 (full_pipeline_v4.py:374-379)
mean_norm = {c: lat[c].mean(0) / (np.linalg.norm(lat[c].mean(0)) + 1e-12) for c in (0, 1, 2)}
CR = {r["cluster_id"]: r for r in summary["cluster_results"]}

# ── 다국어 문자열 ─────────────────────────────────────────────────────────────
T = {
 "ko": dict(font="AppleGothic",
   state="상태", seg="세그먼트", nseg="세그먼트 수", subject="피험자", count="빈도",
   seglen="세그먼트 길이 (TR)", segdist="(a) 세그먼트 길이 분포", segper="(b) 피험자별 세그먼트 수",
   mean="평균", roi="ROI 번호", fisherz="Fisher-Z 상관계수",
   loss="MSE 손실", epochs="학습 에폭 수", trainloss="학습 손실", valloss="검증 손실",
   lossbar="(a) 상태별 최종 손실", epochbar="(b) 조기종료 시점 에폭",
   cos="코사인 유사도", cosmap="(a) 상태 간 잠재표현 코사인 유사도",
   l2v="(b) 상태별 잠재벡터 L2 노름 분포", l2="L2 노름",
   pca="(a) PCA 투영", tsne="(b) t-SNE 투영", var="설명 분산",
   prof="(a) 상태별 평균 잠재 프로파일", profx="잠재 차원 (분산 상위 30개)", profy="평균 활성값",
   cum="(b) 상태 내 PCA 누적 설명 분산", cumx="주성분 개수", cumy="누적 설명 분산",
   v3="V3 (단일 공유 모델)", v4="V4 (상태별 독립 모델)",
   v3t="(a) V3: 상태 구분 없는 단일 모델", v4t="(b) V4: 상태별 독립 모델",
   occ="상태 점유율", occt="피험자별 Brain State 점유율", ratio="비율",
   pipe=["BOLD 신호\n(100 ROI × T)", "MTAD-GAT\nConv+GAT+GRU", "임베딩 변화점\n기반 세그멘테이션",
         "기능적 연결성 행렬\n(Pearson + Fisher-Z)", "K-평균 군집화\n(K=4) → 상태 레이블",
         "상태별 독립 BrainLM\n(원시 시계열 입력)", "잠재표현 직교성 검증"],
   pipenote="연결성 행렬은 상태 레이블 부여에만 사용 · 표현학습 입력은 원시 BOLD 시계열",
   ),
 "en": dict(font="DejaVu Sans",
   state="State", seg="Segment", nseg="No. of segments", subject="Subject", count="Frequency",
   seglen="Segment length (TR)", segdist="(a) Segment length distribution",
   segper="(b) Segments per subject",
   mean="Mean", roi="ROI index", fisherz="Fisher-Z correlation",
   loss="MSE loss", epochs="Epochs trained", trainloss="Train loss", valloss="Validation loss",
   lossbar="(a) Final loss per state", epochbar="(b) Epochs at early stopping",
   cos="Cosine similarity", cosmap="(a) Cross-state latent cosine similarity",
   l2v="(b) Latent L2-norm distribution per state", l2="L2 norm",
   pca="(a) PCA projection", tsne="(b) t-SNE projection", var="explained var.",
   prof="(a) Mean latent profile per state", profx="Latent dimension (top-30 by variance)",
   profy="Mean activation",
   cum="(b) Within-state cumulative explained variance", cumx="Number of components",
   cumy="Cumulative explained variance",
   v3="V3 (single shared model)", v4="V4 (per-state models)",
   v3t="(a) V3: single model without state separation", v4t="(b) V4: per-state independent models",
   occ="State occupancy", occt="Brain state occupancy per subject", ratio="Proportion",
   pipe=["BOLD signal\n(100 ROI × T)", "MTAD-GAT\nConv+GAT+GRU", "Change-point\nsegmentation",
         "Functional connectivity\n(Pearson + Fisher-Z)", "K-means clustering\n(K=4) → state labels",
         "Per-state BrainLM\n(raw time series input)", "Latent orthogonality test"],
   pipenote="Connectivity matrices are used only for state labeling; representation learning uses raw BOLD",
   ),
}


def setfont(lang):
    plt.rcParams.update({
        "font.family": T[lang]["font"],
        "axes.unicode_minus": False,     # 한글 폰트의 마이너스 깨짐 방지
        "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
        "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
        "figure.dpi": DPI, "savefig.dpi": DPI, "savefig.bbox": "tight",
        "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.5,
        "axes.spines.top": False, "axes.spines.right": False,
    })


def save(fig, lang, name):
    out = FIGROOT / lang
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / f"{name}.png", dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  {lang}/{name}.png")


def slab(t, i):      # "상태 0" / "State 0"
    return f"{t['state']} {i}"


# ── Fig 1: 파이프라인 개요 ───────────────────────────────────────────────────
def fig1(lang):
    t = T[lang]; setfont(lang)
    fig, ax = plt.subplots(figsize=(6.0, 7.2))
    ax.set_xlim(0, 10); ax.set_ylim(0, 15.2); ax.axis("off"); ax.grid(False)
    cols = ["#5D6D7E", "#5D6D7E", "#C0392B", "#B7950B", "#B7950B", "#2471A3", "#1E8449"]
    for i, (label, col) in enumerate(zip(t["pipe"], cols)):
        y = 13.6 - i * 1.95
        ax.add_patch(mpatches.FancyBboxPatch((1.6, y - 0.62), 6.8, 1.24,
                     boxstyle="round,pad=0.08", linewidth=1.4, edgecolor=col, facecolor=col + "1A"))
        ax.text(5.0, y, label, ha="center", va="center", fontsize=9.5, color="#1B2631")
        if i < len(t["pipe"]) - 1:
            ax.annotate("", xy=(5.0, y - 1.33), xytext=(5.0, y - 0.66),
                        arrowprops=dict(arrowstyle="-|>", linewidth=1.3, color="#566573"))
    ax.text(5.0, 0.15, t["pipenote"], ha="center", va="center", fontsize=8,
            color="#566573", style="italic", wrap=True)
    save(fig, lang, "fig1_pipeline")


# ── Fig 2: 세그멘테이션 결과 ─────────────────────────────────────────────────
def fig2(lang):
    t = T[lang]; setfont(lang)
    L = d["seg_len"]; subj = d["seg_subject"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9))
    axes[0].hist(L, bins=28, color="#2471A3", edgecolor="white", linewidth=0.6)
    axes[0].axvline(L.mean(), color="#C0392B", linestyle="--", linewidth=1.4,
                    label=f"{t['mean']} = {L.mean():.1f}")
    axes[0].set_xlabel(t["seglen"]); axes[0].set_ylabel(t["count"])
    axes[0].set_title(t["segdist"]); axes[0].legend(frameon=False)
    uniq, cnt = np.unique(subj, return_counts=True)
    order = np.argsort(-cnt)
    axes[1].bar(range(len(uniq)), cnt[order], color="#5D6D7E", width=0.75)
    axes[1].axhline(cnt.mean(), color="#C0392B", linestyle="--", linewidth=1.4,
                    label=f"{t['mean']} = {cnt.mean():.1f}")
    axes[1].set_xlabel(t["subject"]); axes[1].set_ylabel(t["nseg"])
    axes[1].set_title(t["segper"]); axes[1].legend(frameon=False)
    axes[1].set_xticks([])
    fig.tight_layout()
    save(fig, lang, "fig2_segmentation")


# ── Fig 3: 상태별 CM 중심 ────────────────────────────────────────────────────
def fig3(lang):
    t = T[lang]; setfont(lang)
    fig, axes = plt.subplots(1, 4, figsize=(7.4, 2.15))
    cents = [d[f"centroid_{i}"] for i in range(4)]
    vmax = max(np.abs(c[~np.eye(100, dtype=bool)]).max() for c in cents) * 0.85
    sizes = {0: 99, 1: 121, 2: 72, 3: 16}
    for i, ax in enumerate(axes):
        c = cents[i].copy(); np.fill_diagonal(c, 0)
        im = ax.imshow(c, cmap="RdBu_r", norm=TwoSlopeNorm(0, -vmax, vmax), interpolation="nearest")
        ax.set_title(f"{slab(t,i)}  (n={sizes[i]})", fontsize=9)
        ax.set_xlabel(t["roi"], fontsize=8); ax.grid(False)
        ax.set_xticks([0, 50, 99]); ax.set_yticks([0, 50, 99] if i == 0 else [])
        if i == 0:
            ax.set_ylabel(t["roi"], fontsize=8)
    cb = fig.colorbar(im, ax=axes, fraction=0.02, pad=0.015)
    cb.set_label(t["fisherz"], fontsize=8); cb.ax.tick_params(labelsize=7)
    save(fig, lang, "fig3_cm_centroids")


# ── Fig 4: 학습 결과 ────────────────────────────────────────────────────────
def fig4(lang):
    t = T[lang]; setfont(lang)
    ids = [0, 1, 2]
    tr = [CR[i]["final_train_loss"] for i in ids]
    va = [CR[i]["final_val_loss"] for i in ids]
    ep = [CR[i]["n_epochs_trained"] for i in ids]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9))
    x = np.arange(3); w = 0.36
    axes[0].bar(x - w/2, tr, w, label=t["trainloss"], color="#5D6D7E")
    axes[0].bar(x + w/2, va, w, label=t["valloss"], color="#C0392B")
    for xi, (a, b) in enumerate(zip(tr, va)):
        axes[0].text(xi - w/2, a + 1.5, f"{a:.1f}", ha="center", fontsize=7)
        axes[0].text(xi + w/2, b + 1.5, f"{b:.1f}", ha="center", fontsize=7)
    axes[0].set_xticks(x); axes[0].set_xticklabels([slab(t, i) for i in ids])
    axes[0].set_ylabel(t["loss"]); axes[0].set_title(t["lossbar"])
    axes[0].legend(frameon=False); axes[0].set_ylim(0, 135)
    axes[1].bar(x, ep, 0.55, color=[C[i] for i in ids])
    for xi, e in enumerate(ep):
        axes[1].text(xi, e + 0.4, str(e), ha="center", fontsize=8)
    axes[1].set_xticks(x); axes[1].set_xticklabels([slab(t, i) for i in ids])
    axes[1].set_ylabel(t["epochs"]); axes[1].set_title(t["epochbar"]); axes[1].set_ylim(0, 30)
    fig.tight_layout()
    save(fig, lang, "fig4_training")


# ── Fig 5: 코사인 유사도 + L2 노름 ──────────────────────────────────────────
def fig5(lang):
    t = T[lang]; setfont(lang)
    M = np.eye(3)
    for i in range(3):
        for j in range(3):
            M[i, j] = float(mean_norm[i] @ mean_norm[j])
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))
    im = axes[0].imshow(M, cmap="RdBu_r", norm=TwoSlopeNorm(0, -1, 1))
    for i in range(3):
        for j in range(3):
            axes[0].text(j, i, f"{M[i,j]:.3f}", ha="center", va="center", fontsize=8.5,
                         color="white" if abs(M[i, j]) > 0.5 else "#1B2631")
    axes[0].set_xticks(range(3)); axes[0].set_yticks(range(3))
    axes[0].set_xticklabels([slab(t, i) for i in range(3)])
    axes[0].set_yticklabels([slab(t, i) for i in range(3)])
    axes[0].set_title(t["cosmap"]); axes[0].grid(False)
    cb = fig.colorbar(im, ax=axes[0], fraction=0.046, pad=0.04)
    cb.set_label(t["cos"], fontsize=8); cb.ax.tick_params(labelsize=7)
    norms = [np.linalg.norm(lat[c], axis=1) for c in (0, 1, 2)]
    vp = axes[1].violinplot(norms, showmeans=True, widths=0.75)
    for k, b in enumerate(vp["bodies"]):
        b.set_facecolor(C[k]); b.set_alpha(0.55); b.set_edgecolor(C[k])
    for key in ("cbars", "cmins", "cmaxes", "cmeans"):
        vp[key].set_color("#34495E"); vp[key].set_linewidth(1.1)
    axes[1].set_xticks([1, 2, 3]); axes[1].set_xticklabels([slab(t, i) for i in range(3)])
    axes[1].set_ylabel(t["l2"]); axes[1].set_title(t["l2v"])
    fig.tight_layout()
    save(fig, lang, "fig5_cosine_l2")


# ── Fig 6: PCA / t-SNE ──────────────────────────────────────────────────────
def fig6(lang):
    t = T[lang]; setfont(lang)
    X = np.vstack([latn[c] for c in (0, 1, 2)])
    y = np.concatenate([np.full(len(latn[c]), c) for c in (0, 1, 2)])
    p = PCA(n_components=2, random_state=42).fit(X)
    Z = p.transform(X)
    Y = TSNE(n_components=2, perplexity=30, init="pca", random_state=42,
             learning_rate="auto").fit_transform(X)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2))
    for c in (0, 1, 2):
        m = y == c
        axes[0].scatter(Z[m, 0], Z[m, 1], s=13, c=C[c], alpha=0.75,
                        edgecolors="white", linewidths=0.3, label=slab(t, c))
        axes[1].scatter(Y[m, 0], Y[m, 1], s=13, c=C[c], alpha=0.75,
                        edgecolors="white", linewidths=0.3, label=slab(t, c))
    axes[0].set_xlabel(f"PC1 ({p.explained_variance_ratio_[0]*100:.1f}% {t['var']})")
    axes[0].set_ylabel(f"PC2 ({p.explained_variance_ratio_[1]*100:.1f}% {t['var']})")
    axes[0].set_title(t["pca"]); axes[0].legend(frameon=False, markerscale=1.4)
    axes[1].set_xlabel("t-SNE 1"); axes[1].set_ylabel("t-SNE 2")
    axes[1].set_title(t["tsne"]); axes[1].legend(frameon=False, markerscale=1.4)
    fig.tight_layout()
    save(fig, lang, "fig6_pca_tsne")


# ── Fig 7: 잠재 프로파일 + 누적 분산 ────────────────────────────────────────
def fig7(lang):
    t = T[lang]; setfont(lang)
    means = np.vstack([lat[c].mean(0) for c in (0, 1, 2)])
    top = np.argsort(-means.var(0))[:30]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9))
    for c in (0, 1, 2):
        axes[0].plot(range(30), means[c, top], marker="o", ms=3, linewidth=1.2,
                     color=C[c], label=slab(t, c))
    axes[0].axhline(0, color="#95A5A6", linewidth=0.7)
    axes[0].set_xlabel(t["profx"]); axes[0].set_ylabel(t["profy"])
    axes[0].set_title(t["prof"]); axes[0].legend(frameon=False, ncol=3)
    for c in (0, 1, 2):
        pc = PCA(random_state=42).fit(latn[c])
        cum = np.cumsum(pc.explained_variance_ratio_)
        axes[1].plot(range(1, len(cum) + 1), cum, linewidth=1.5, color=C[c], label=slab(t, c))
    axes[1].axhline(0.9, color="#C0392B", linestyle="--", linewidth=1.0)
    axes[1].set_xlim(1, 60); axes[1].set_ylim(0, 1.02)
    axes[1].set_xlabel(t["cumx"]); axes[1].set_ylabel(t["cumy"])
    axes[1].set_title(t["cum"]); axes[1].legend(frameon=False, loc="lower right")
    fig.tight_layout()
    save(fig, lang, "fig7_latent_profile")


# ── Fig 8: V3 vs V4 ─────────────────────────────────────────────────────────
def fig8(lang):
    t = T[lang]; setfont(lang)
    v3 = np.array([[1.0, 0.960, 0.989], [0.960, 1.0, 0.974], [0.989, 0.974, 1.0]])
    v4 = np.eye(3)
    for i in range(3):
        for j in range(3):
            v4[i, j] = float(mean_norm[i] @ mean_norm[j])
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))
    for ax, M, title in zip(axes, [v3, v4], [t["v3t"], t["v4t"]]):
        im = ax.imshow(M, cmap="RdBu_r", norm=TwoSlopeNorm(0, -1, 1))
        for i in range(3):
            for j in range(3):
                ax.text(j, i, f"{M[i,j]:.3f}", ha="center", va="center", fontsize=8.5,
                        color="white" if abs(M[i, j]) > 0.5 else "#1B2631")
        ax.set_xticks(range(3)); ax.set_yticks(range(3))
        ax.set_xticklabels([slab(t, i) for i in range(3)])
        ax.set_yticklabels([slab(t, i) for i in range(3)])
        ax.set_title(title, fontsize=9.5); ax.grid(False)
        cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cb.set_label(t["cos"], fontsize=8); cb.ax.tick_params(labelsize=7)
    fig.tight_layout()
    save(fig, lang, "fig8_v3_vs_v4")


# ── Fig 9: 피험자별 State 점유율 ────────────────────────────────────────────
def fig9(lang):
    t = T[lang]; setfont(lang)
    occ = d["occupancy"]
    frac = occ / occ.sum(1, keepdims=True)
    order = np.argsort(-frac[:, 1])
    frac = frac[order]
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    bottom = np.zeros(len(frac))
    for c in range(4):
        ax.bar(range(len(frac)), frac[:, c], 0.82, bottom=bottom,
               color=C[c], label=slab(t, c), edgecolor="white", linewidth=0.3)
        bottom += frac[:, c]
    ax.set_xlim(-0.6, len(frac) - 0.4); ax.set_ylim(0, 1)
    ax.set_xlabel(t["subject"]); ax.set_ylabel(t["ratio"]); ax.set_title(t["occt"])
    ax.set_xticks([]); ax.grid(False)
    ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    fig.tight_layout()
    save(fig, lang, "fig9_occupancy")


for lang in ("ko", "en"):
    print(f"[{lang}]")
    for fn in (fig1, fig2, fig3, fig4, fig5, fig6, fig7, fig8, fig9):
        fn(lang)
print("done")
