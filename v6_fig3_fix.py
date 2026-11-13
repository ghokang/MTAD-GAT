"""
fig3_latent_comparison 의 우측 패널(RSA/CKA)을 바로잡은 그림.

기존 그림은 모델 A에 State A 데이터를, 모델 B에 State B 데이터를 넣고 계산한
RSA 0.004 / CKA 0.026 을 그리고 있었다. 입력이 달라 무효인 값이다.
여기서는 공통 입력 505 윈도우로 다시 계산한 값과, 같은 데이터로 seed만 바꿔
학습한 두 모델의 기준선을 나란히 그린다.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path("/Users/mac/Desktop/code/MTAD-GAT")
OUT = ROOT / "visualization_ver6_k2_stride64"
for f in ("AppleGothic", "Apple SD Gothic Neo", "NanumGothic"):
    try:
        matplotlib.font_manager.findfont(f, fallback_to_default=False)
        plt.rcParams["font.family"] = f
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

summ = json.loads((OUT / "v6_k2_summary.json").read_text(encoding="utf-8"))
rep = json.loads((OUT / "rsa_cka_repeats.json").read_text(encoding="utf-8"))

states = sorted(int(k.replace("State", "")) for k in summ["cross_state_cosine"])
cos = np.array([[summ["cross_state_cosine"][f"State{a}"][f"State{b}"]
                 for b in states] for a in states])
lo, hi = summ["null_95ci"]
offdiag = summ["offdiag_mean"]
COS_SEED = 0.1531   # 같은 State 0 데이터, seed 111 vs 222 (v6_tsne_control / seed_test)

fig, axes = plt.subplots(1, 3, figsize=(16, 4.4))

im = axes[0].imshow(cos, cmap="RdBu_r", vmin=-1, vmax=1)
axes[0].set_xticks(range(len(states))); axes[0].set_yticks(range(len(states)))
axes[0].set_xticklabels([f"S{c}" for c in states])
axes[0].set_yticklabels([f"S{c}" for c in states])
for i in range(len(states)):
    for j in range(len(states)):
        axes[0].text(j, i, f"{cos[i, j]:.3f}", ha="center", va="center",
                     fontsize=11, color="white" if abs(cos[i, j]) > 0.5 else "black")
axes[0].set_title("cross-state 코사인", fontsize=12, fontweight="bold")
fig.colorbar(im, ax=axes[0], fraction=0.046)

rng = np.random.default_rng(0)
R = rng.normal(size=(20000, 256))
R /= np.linalg.norm(R, axis=1, keepdims=True)
null = np.einsum("ij,ij->i", R[:10000], R[10000:])
axes[1].hist(null, bins=60, color="#B8C4DE", edgecolor="white")
axes[1].axvline(lo, color="#5A6BA8", ls="--", lw=1.2)
axes[1].axvline(hi, color="#5A6BA8", ls="--", lw=1.2, label="무작위 95% 구간")
axes[1].axvline(offdiag, color="#E04B5A", lw=2.2,
                label=f"State0 vs State1  {offdiag:+.3f}")
axes[1].axvline(COS_SEED, color="#2E8B6F", lw=2.2,
                label=f"같은 State0, seed만 다름  {COS_SEED:+.3f}")
axes[1].set_title("무작위 256차원 벡터의 귀무분포 대비", fontsize=12, fontweight="bold")
axes[1].set_xlabel("코사인")
axes[1].legend(fontsize=8.5, loc="upper left")

labels = ["RSA (r)", "CKA"]
base = [rep["mean"]["base_rsa"], rep["mean"]["base_cka"]]
base_sd = [rep["sd"]["base_rsa"], rep["sd"]["base_cka"]]
test = [rep["mean"]["test_rsa"], rep["mean"]["test_cka"]]
test_sd = [rep["sd"]["test_rsa"], rep["sd"]["test_cka"]]
xp = np.arange(2)
axes[2].bar(xp - 0.2, base, width=0.4, yerr=base_sd, capsize=4, color="#1C7293",
            label="기준선 — 같은 State0, seed만 다름")
axes[2].bar(xp + 0.2, test, width=0.4, yerr=test_sd, capsize=4, color="#E8A33D",
            label="관심 — State0 vs State1")
for x, v in zip(xp - 0.2, base):
    axes[2].text(x, v + 0.03, f"{v:.3f}", ha="center", fontsize=9.5)
for x, v in zip(xp + 0.2, test):
    axes[2].text(x, v + 0.03, f"{v:.3f}", ha="center", fontsize=9.5)
axes[2].set_xticks(xp); axes[2].set_xticklabels(labels)
axes[2].set_ylim(0, 1.12)
axes[2].set_title("좌표 회전에 불변한 지표 (공통 입력 505 윈도우, seed 쌍 3회)",
                  fontsize=11.5, fontweight="bold")
axes[2].legend(fontsize=8.5, loc="lower left")
axes[2].grid(axis="y", alpha=0.3)

fig.tight_layout()
fig.savefig(OUT / "fig3_latent_comparison_fixed.png", dpi=160)
plt.close(fig)
print("저장:", OUT / "fig3_latent_comparison_fixed.png")
