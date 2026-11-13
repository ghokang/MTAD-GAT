"""
V6 대조군 집계: 실제 State 레이블 vs 레이블을 섞은 대조군

full_pipeline_v6.py --shuffle-control 을 여러 seed로 돌린 결과를 모아
"cross-state 재구성 손실 증가율"의 귀무분포를 만들고 실제값과 비교한다.

실행: python v6_control_summary.py [--k 2]
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("--k", type=int, default=2)
args = ap.parse_args()
K = args.k

for _f in ("AppleGothic", "Apple SD Gothic Neo", "NanumGothic", "Malgun Gothic"):
    try:
        matplotlib.font_manager.findfont(_f, fallback_to_default=False)
        plt.rcParams["font.family"] = _f
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

real_path = ROOT / f"visualization_ver6_k{K}" / f"v6_k{K}_summary.json"
real = json.loads(real_path.read_text())
R = real["recon_pct_increase"]

rows = []
for f in sorted(glob.glob(str(ROOT / f"visualization_ver6_k{K}_shuffled*" / "v6_*_summary.json"))):
    d = json.loads(Path(f).read_text())
    rows.append({
        "seed": d.get("shuffle_seed", 42),
        "self": d["recon_self_mean"],
        "cross": d["recon_cross_mean"],
        "pct": d["recon_pct_increase"],
        "cos_offdiag": d["offdiag_mean"],
    })
df = pd.DataFrame(rows).sort_values("seed").reset_index(drop=True)
v = df["pct"].to_numpy()

n = len(v)
ge = int((v >= R).sum())
p_perm = (1 + ge) / (1 + n)
z = (R - v.mean()) / v.std(ddof=1) if n > 1 else np.nan

print("=" * 66)
print(f"V6 (K={K}) cross-state 재구성 손실 증가율 — 실제 vs 레이블 섞기 대조군")
print("=" * 66)
print(f"  실제 레이블 : {R:+.2f}%   (자기 {real['recon_self_mean']:.2f} / "
      f"남 {real['recon_cross_mean']:.2f})")
print(f"  대조군 {n}회 : 평균 {v.mean():+.2f}%, SD {v.std(ddof=1):.2f}, "
      f"범위 [{v.min():+.2f}, {v.max():+.2f}]")
print(f"  z = {z:+.2f},  대조군 중 실제값 이상 {ge}/{n}  →  permutation p = {p_perm:.4f}")
print()
print(df.round(3).to_string(index=False))

out_dir = ROOT / f"visualization_ver6_k{K}"
df.to_csv(out_dir / "tables" / "shuffle_control.csv", index=False)

fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
ax = axes[0]
ax.hist(v, bins=min(12, max(4, n // 2)), color="#B0BEC5", edgecolor="white",
        label=f"레이블 섞기 대조군 (n={n})")
ax.axvline(R, color="#E74C3C", lw=2.6, label=f"실제 레이블 ({R:+.2f}%)")
ax.axvline(v.mean(), color="#546E7A", lw=1.3, ls="--", label=f"대조군 평균 ({v.mean():+.2f}%)")
ax.set_xlabel("cross-state 재구성 손실 증가율 [%]   (클수록 State가 구별됨)")
ax.set_ylabel("빈도")
ax.set_title(f"귀무분포 대비 실제값\nz = {z:+.2f},  permutation p = {p_perm:.3f}",
             fontsize=12, fontweight="bold")
ax.legend(fontsize=9)
ax.grid(axis="y", alpha=0.3)
ax.set_axisbelow(True)

ax = axes[1]
xs = np.arange(n + 1)
vals = np.concatenate([[R], v])
cols = ["#E74C3C"] + ["#B0BEC5"] * n
ax.bar(xs, vals, color=cols, edgecolor="white")
ax.axhline(v.mean(), color="#546E7A", ls="--", lw=1.2)
ax.set_xticks(xs)
ax.set_xticklabels(["실제"] + [str(s) for s in df["seed"]], fontsize=8, rotation=90)
ax.set_xlabel("실제 / 대조군 seed")
ax.set_ylabel("손실 증가율 [%]")
ax.set_title("개별 실행값 비교", fontsize=12, fontweight="bold")
ax.grid(axis="y", alpha=0.3)
ax.set_axisbelow(True)

fig.suptitle(f"V6 (K={K}): State 레이블이 BrainLM 표현에 실제로 반영되는가",
             fontsize=13, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.91])
fig.savefig(out_dir / "fig5_shuffle_control.png", dpi=160)
plt.close(fig)
print(f"\n  저장: {out_dir / 'fig5_shuffle_control.png'}")

json.dump({
    "K": K, "real_pct": R, "n_control": n,
    "control_mean": float(v.mean()), "control_sd": float(v.std(ddof=1)),
    "control_min": float(v.min()), "control_max": float(v.max()),
    "z": float(z), "n_ge": ge, "p_perm": float(p_perm),
    "controls": df.to_dict("records"),
}, open(out_dir / "shuffle_control_summary.json", "w"), indent=2, ensure_ascii=False)
