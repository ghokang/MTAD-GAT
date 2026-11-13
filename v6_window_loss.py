"""
V6 윈도우별 재구성 손실 분포

full_pipeline_v6.py 가 저장한 체크포인트를 불러와, 윈도우 하나하나의 masked
reconstruction 손실을 계산한다. 기존 그림(fig4)은 모델×데이터 조합당 평균 하나만
보여주지만, 여기서는 윈도우 505개의 분포를 그려 두 분포가 실제로 갈라지는지 본다.

레이블을 섞은 대조군 체크포인트가 있으면 같은 계산을 반복해 귀무분포로 겹쳐 그린다.

실행: python v6_window_loss.py [--k 2] [--n-control 5]
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
from scipy import stats
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from brainlm.ts_dataset import TSConcatDataset  # noqa: E402
from brainlm.ts_model import BrainLMTimeSeries, BrainLMTimeSeriesConfig  # noqa: E402
from pipeline.clustering import perform_clustering  # noqa: E402
from pipeline.connectivity import collect_all_cms_flat, compute_all_cms  # noqa: E402
from pipeline.v3_sequences import TSConcatExample  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--k", type=int, default=2)
ap.add_argument("--window", type=int, default=64)
ap.add_argument("--n-control", type=int, default=5, help="귀무분포에 쓸 대조군 실행 수")
args = ap.parse_args()

K, WIN = args.k, args.window
MASK_RATIO, BATCH = 0.15, 8
OUT = ROOT / f"visualization_ver6_k{K}"
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

for _f in ("AppleGothic", "Apple SD Gothic Neo", "NanumGothic", "Malgun Gothic"):
    try:
        matplotlib.font_manager.findfont(_f, fallback_to_default=False)
        plt.rcParams["font.family"] = _f
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False
CLUSTER_COLORS = ["#E74C3C", "#3498DB", "#2ECC71", "#F39C12"]

print("=" * 70)
print(f"V6 (K={K}) 윈도우별 재구성 손실 분포")
print("=" * 70)


# ── 윈도우 재구성 (파이프라인과 동일 규칙) ──────────────────────────────────
def build_windows(seg2state, all_segments, subjects, k):
    out = {}
    for cid in range(k):
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
        for i, (sid, _, _) in enumerate(pieces):
            owner[bounds[i]:bounds[i + 1]] = sid
        exs = []
        for st in range(0, long_ts.shape[0] - WIN + 1, WIN):
            w = owner[st:st + WIN]
            vals, cnts = np.unique(w.astype(str), return_counts=True)
            exs.append(TSConcatExample(subject_id=str(vals[np.argmax(cnts)]),
                                       cluster_id=cid, segment_ids=(0,),
                                       x=long_ts[st:st + WIN]))
        out[cid] = exs
    return out


print("\n세그먼트 로드 / 클러스터링 재현...")
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
windows = build_windows(seg2state, all_segments, subjects, K)
for c in windows:
    print(f"  State {c}: 윈도우 {len(windows[c])}개")


def load_model(ckpt_dir):
    cfgd = torch.load(ckpt_dir / "config.pt", weights_only=False)["config"]
    model = BrainLMTimeSeries(BrainLMTimeSeriesConfig(**cfgd))
    sd = torch.load(ckpt_dir / "best_model.pt", map_location="cpu",
                    weights_only=False)["model_state_dict"]
    model.load_state_dict(sd)
    model.eval().to(device)
    with open(ckpt_dir / "normalizer.pkl", "rb") as f:
        norm = pickle.load(f)
    return model, norm


@torch.no_grad()
def per_window_loss(model, norm, exs, seed=0):
    """윈도우 하나당 손실 하나 (학습과 동일한 masked MSE)."""
    dl = DataLoader(TSConcatDataset(exs, max_time_steps=WIN, mask_ratio=MASK_RATIO,
                                    normalizer=norm, augment=False, seed=seed),
                    batch_size=BATCH, shuffle=False, num_workers=0)
    vals = []
    for b in dl:
        x, y = b["input_x"].to(device), b["labels"].to(device)
        attn, msk = b["attention_mask"].to(device), b["mask_labels"].to(device)
        out = model(x, attention_mask=attn, mask_labels=msk)
        recon = out["reconstruction"]
        w = ((msk > 0.5).to(recon.dtype) * attn).unsqueeze(-1)
        se = (((recon - y) ** 2) * w).sum(dim=(1, 2))
        den = (w.sum(dim=(1, 2)) * y.shape[-1]).clamp_min(1.0)
        vals.append((se / den).cpu().numpy())
    return np.concatenate(vals)


# ── 실제 레이블 ─────────────────────────────────────────────────────────────
print("\n실제 레이블 — 윈도우별 손실 계산...")
states = sorted(windows)
real = {}
for m in states:
    model, norm = load_model(ROOT / "checkpoint" / f"brainlm_v6_k{K}" / f"state_{m}")
    for dcid in states:
        real[(m, dcid)] = per_window_loss(model, norm, windows[dcid])
    del model

rows = []
for m in states:
    self_v, oth_v = real[(m, m)], np.concatenate([real[(m, d)] for d in states if d != m])
    t, p = stats.ttest_ind(oth_v, self_v, equal_var=False)
    d = (oth_v.mean() - self_v.mean()) / np.sqrt((oth_v.var(ddof=1) + self_v.var(ddof=1)) / 2)
    rows.append({"model": m, "n_self": len(self_v), "n_other": len(oth_v),
                 "self_mean": self_v.mean(), "other_mean": oth_v.mean(),
                 "pct": (oth_v.mean() / self_v.mean() - 1) * 100,
                 "welch_t": float(t), "p": float(p), "cohens_d": float(d)})
    print(f"  model {m}: 자기 {self_v.mean():.2f} (n={len(self_v)}) vs "
          f"남 {oth_v.mean():.2f} (n={len(oth_v)})  "
          f"{(oth_v.mean()/self_v.mean()-1)*100:+.1f}%  "
          f"Welch t={t:.2f}, p={p:.3g}, d={d:+.2f}")
df = pd.DataFrame(rows)
df.to_csv(OUT / "tables" / "window_loss_stats.csv", index=False)

# ── 대조군 (레이블 섞기) ────────────────────────────────────────────────────
print(f"\n대조군 — 최대 {args.n_control}개 실행에서 윈도우별 손실 계산...")
ctrl_self, ctrl_other = [], []
ctrl_dirs = sorted([p for p in (ROOT / "checkpoint").glob(f"brainlm_v6_k{K}_shuffled*")
                    if (p / "state_0" / "best_model.pt").exists()])[:args.n_control]
for cdir in ctrl_dirs:
    seed = cdir.name.replace(f"brainlm_v6_k{K}_shuffled", "") or "42"
    keys, vals = list(seg2state.keys()), list(seg2state.values())
    np.random.default_rng(int(seed)).shuffle(vals)
    s2s_c = dict(zip(keys, vals))
    win_c = build_windows(s2s_c, all_segments, subjects, K)
    for m in sorted(win_c):
        mdir = cdir / f"state_{m}"
        if not (mdir / "best_model.pt").exists():
            continue
        model, norm = load_model(mdir)
        ctrl_self.append(per_window_loss(model, norm, win_c[m]))
        for dcid in sorted(win_c):
            if dcid != m:
                ctrl_other.append(per_window_loss(model, norm, win_c[dcid]))
        del model
    print(f"  {cdir.name} 완료")
ctrl_self = np.concatenate(ctrl_self) if ctrl_self else np.array([])
ctrl_other = np.concatenate(ctrl_other) if ctrl_other else np.array([])
if len(ctrl_self):
    print(f"  대조군: 자기 {ctrl_self.mean():.2f} vs 남 {ctrl_other.mean():.2f} "
          f"({(ctrl_other.mean()/ctrl_self.mean()-1)*100:+.1f}%)")

# ── 그림 ────────────────────────────────────────────────────────────────────
ncol = len(states) + 1
fig, axes = plt.subplots(1, ncol, figsize=(5.0 * ncol, 4.6))

for ax, m in zip(axes[:len(states)], states):
    data = [real[(m, d)] for d in states]
    parts = ax.violinplot(data, showmeans=False, showextrema=False, widths=0.75)
    for i, b in enumerate(parts["bodies"]):
        b.set_facecolor(CLUSTER_COLORS[states[i] % 4])
        b.set_alpha(0.35 if states[i] != m else 0.7)
        b.set_edgecolor("white")
    bp = ax.boxplot(data, widths=0.16, patch_artist=True, showfliers=False,
                    medianprops=dict(color="black", lw=1.6))
    for i, pt in enumerate(bp["boxes"]):
        pt.set_facecolor("white")
        pt.set_edgecolor(CLUSTER_COLORS[states[i] % 4])
    r = df[df.model == m].iloc[0]
    ax.set_xticks(range(1, len(states) + 1))
    ax.set_xticklabels([f"data {d}" + ("  (자기)" if d == m else "") for d in states])
    ax.set_ylabel("윈도우별 masked reconstruction MSE")
    ax.set_title(f"model {m}  —  {r['pct']:+.1f}%\n"
                 f"Welch t = {r['welch_t']:.2f}, p = {r['p']:.2g}, d = {r['cohens_d']:+.2f}",
                 fontsize=11.5, fontweight="bold")
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)

ax = axes[-1]
if len(ctrl_self):
    real_self = np.concatenate([real[(m, m)] for m in states])
    real_oth = np.concatenate([real[(m, d)] for m in states for d in states if d != m])
    pos, labels, colors = [1, 2, 3.4, 4.4], [], []
    data = [real_self, real_oth, ctrl_self, ctrl_other]
    bp = ax.boxplot(data, positions=pos, widths=0.55, patch_artist=True,
                    showfliers=False, medianprops=dict(color="black", lw=1.6))
    for pt, c in zip(bp["boxes"], ["#2E8B6F", "#E04B5A", "#BBC4D4", "#9AA5B8"]):
        pt.set_facecolor(c)
        pt.set_alpha(0.75)
    ax.set_xticks(pos)
    ax.set_xticklabels(["자기\n(실제)", "남\n(실제)", "자기\n(대조군)", "남\n(대조군)"],
                       fontsize=10)
    ax.set_ylabel("윈도우별 MSE")
    ax.set_title(f"실제 {(real_oth.mean()/real_self.mean()-1)*100:+.1f}%  vs  "
                 f"대조군 {(ctrl_other.mean()/ctrl_self.mean()-1)*100:+.1f}%\n"
                 f"(대조군 {len(ctrl_dirs)}개 실행 통합)", fontsize=11.5, fontweight="bold")
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)

fig.suptitle(f"V6 (K={K}): 윈도우별 재구성 손실 분포 — 평균이 아니라 분포로 보기",
             fontsize=13, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.91])
fig.savefig(OUT / "fig6_window_loss_dist.png", dpi=160)
plt.close(fig)
print(f"\n  저장: {OUT / 'fig6_window_loss_dist.png'}")

summary = {
    "K": K, "window": WIN, "per_model": rows,
    "n_control_runs": len(ctrl_dirs),
}
if len(ctrl_self):
    summary["control"] = {"self_mean": float(ctrl_self.mean()),
                          "other_mean": float(ctrl_other.mean()),
                          "pct": float((ctrl_other.mean() / ctrl_self.mean() - 1) * 100)}
json.dump(summary, open(OUT / "window_loss_summary.json", "w"), indent=2,
          ensure_ascii=False, default=float)
print("완료")
