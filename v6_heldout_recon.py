"""
V6 (K=2, stride 64) 교차 재구성 손실을 **미학습 예제에서만** 다시 계산한다.

원 파이프라인은 각 state의 전체 윈도우에서 손실을 쟀다. 그러면 대각선(자기 데이터)에는
그 모델의 학습 윈도우가 섞여 있어 '자기 데이터를 더 잘 복원한다'가 과대평가된다.
저장된 체크포인트를 그대로 불러와 val+test 윈도우에서만 다시 잰다.
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

ROOT = Path("/Users/mac/Desktop/code/MTAD-GAT")
sys.path.insert(0, str(ROOT))

from brainlm.ts_dataset import TSConcatDataset  # noqa: E402
from brainlm.ts_model import BrainLMTimeSeries, BrainLMTimeSeriesConfig  # noqa: E402
from pipeline.clustering import perform_clustering  # noqa: E402
from pipeline.connectivity import collect_all_cms_flat, compute_all_cms  # noqa: E402
from pipeline.v3_sequences import TSConcatExample, split_examples  # noqa: E402

K = int(sys.argv[1]) if len(sys.argv) > 1 else 2
WIN = 64
STRIDE = int(sys.argv[3]) if len(sys.argv) > 3 else 64
MASK_RATIO, BATCH, RANDOM_STATE = 0.15, 8, 42
CKPT = ROOT / (sys.argv[2] if len(sys.argv) > 2 else "checkpoint/brainlm_v6_k2_stride64")
OUT = ROOT / (sys.argv[4] if len(sys.argv) > 4 else "visualization_ver6_k2_stride64")
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

with open(ROOT / "checkpoint/brainlm_v3/cache/all_segments.pkl", "rb") as f:
    segs = pickle.load(f)
all_cms = compute_all_cms(segs, method="pearson", min_segment_len=10, use_fisher_z=True)
X, labs = collect_all_cms_flat(all_cms)
clu = perform_clustering(X, labs, n_clusters=K, standardize=True, use_minibatch=True,
                         n_init=4, max_iter=200, batch_size=256, skip_silhouette=True,
                         random_state=RANDOM_STATE)
seg2state = {l: int(c) for l, c in zip(labs, clu.labels)}
subjects = sorted(segs)


def windows_of(cid):
    pieces = []
    for sid in subjects:
        for s in sorted(segs[sid], key=lambda z: z.start_idx):
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


models, norms, allex, heldout = {}, {}, {}, {}
for c in range(K):
    exs = windows_of(c)
    tr, va, te = split_examples(exs, val_split=0.15, test_split=0.15, seed=RANDOM_STATE)
    allex[c], heldout[c] = exs, va + te
    with open(CKPT / f"state_{c}" / "normalizer.pkl", "rb") as f:
        norms[c] = pickle.load(f)
    cfg = torch.load(CKPT / f"state_{c}" / "config.pt", weights_only=False)
    if isinstance(cfg, dict):
        cfg = BrainLMTimeSeriesConfig(**cfg.get("config", cfg))
    m = BrainLMTimeSeries(cfg)
    sd = torch.load(CKPT / f"state_{c}" / "best_model.pt", map_location="cpu",
                    weights_only=False)
    if isinstance(sd, dict) and "model_state_dict" in sd:
        sd = sd["model_state_dict"]
    m.load_state_dict(sd)
    models[c] = m.eval().to(device)
    print(f"State {c}: 전체 {len(exs)} 윈도우 (train {len(tr)} / val {len(va)} / "
          f"test {len(te)}) → 미학습 {len(heldout[c])}개", flush=True)


@torch.no_grad()
def recon(a, exs, seed=0):
    torch.manual_seed(seed)
    dl = DataLoader(TSConcatDataset(exs, max_time_steps=WIN, mask_ratio=MASK_RATIO,
                                    normalizer=norms[a], augment=False),
                    batch_size=BATCH, shuffle=False, num_workers=0)
    tot, n = 0.0, 0
    for b in dl:
        out = models[a].compute_loss(input_x=b["input_x"].to(device),
                                     labels=b["labels"].to(device),
                                     attention_mask=b["attention_mask"].to(device),
                                     mask_labels=b["mask_labels"].to(device))
        tot += float(out["loss"].item()); n += 1
    return tot / max(n, 1)


def build(pool, tag):
    M = np.array([[recon(a, pool[b]) for b in range(K)] for a in range(K)])
    rows = []
    for i in range(K):
        other = np.delete(M[i], i).mean()
        rows.append({"state": i, "n_eval": len(pool[i]), "self": float(M[i, i]),
                     "other_mean": float(other),
                     "pct_increase": float((other - M[i, i]) / M[i, i] * 100)})
    sm = float(np.mean(np.diag(M)))
    cm = float(M[~np.eye(K, dtype=bool)].mean())
    print(f"\n[{tag}]  평가: " + ", ".join(f"S{i} {len(pool[i])}개" for i in range(K)))
    print("      " + "".join(f"data{b}".rjust(12) for b in range(K)) + "    행 기준")
    for i in range(K):
        print(f"model{i}" + "".join(f"{M[i, j]:12.3f}" for j in range(K))
              + f"{rows[i]['pct_increase']:+11.1f}%")
    print(f"  전체: 자기 {sm:.3f} vs 남 {cm:.3f} = {(cm - sm) / sm * 100:+.1f}%")
    return {"matrix": M.tolist(), "per_state": rows, "recon_self_mean": sm,
            "recon_cross_mean": cm, "recon_pct_increase": (cm - sm) / sm * 100}


res = {"K": K, "window": WIN, "stride": STRIDE,
       "all_examples": build(allex, "모든 윈도우 — 대각선에 학습 데이터 포함 (원 파이프라인)"),
       "held_out": build(heldout, "미학습 윈도우만 (val + test)")}
(OUT / "heldout_recon.json").write_text(json.dumps(res, indent=2, ensure_ascii=False),
                                        encoding="utf-8")
print(f"\n저장: {OUT / 'heldout_recon.json'}")
