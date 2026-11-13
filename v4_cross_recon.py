"""
V4 방식(세그먼트 1개 = 예제 1개, 0 패딩)으로 state별 BrainLM을 다시 학습하고
교차 재구성 손실을 계산한다.

V4 원본은 cross-cluster 코사인만 계산했는데, 독립 학습 모델의 코사인은 좌표계가
달라 해석할 수 없다. 좌표계 문제가 없는 지표는 교차 재구성 손실뿐이다.
원본은 모델 가중치를 저장하지 않았고(normalizer.pkl만 있음), 클러스터마다
max_time_steps가 달라(252/292/237) 서로의 데이터를 넣을 수도 없다.
따라서 모든 state에 **공통 max_time_steps**를 적용해 다시 학습한다.

State 3은 세그먼트 16개(train 12, val 0)라 원본에서도 학습되지 않았다 → 제외.
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

from brainlm.ts_dataset import FeatureNormalizer, TSConcatDataset  # noqa: E402
from brainlm.ts_model import BrainLMTimeSeriesConfig  # noqa: E402
from brainlm.ts_train import train_brainlm_ts  # noqa: E402
from pipeline.clustering import perform_clustering  # noqa: E402
from pipeline.connectivity import collect_all_cms_flat, compute_all_cms  # noqa: E402
from pipeline.v3_sequences import TSConcatExample, split_examples  # noqa: E402

K = 4
VAL_SPLIT, TEST_SPLIT = 0.15, 0.15
MASK_RATIO, BATCH, LR, PATIENCE, EPOCHS = 0.15, 8, 1e-4, 10, 50
RANDOM_STATE = 42
OUT = ROOT / "visualization_ver4_crossrecon"
OUT.mkdir(exist_ok=True)
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

with open(ROOT / "checkpoint/brainlm_v3/cache/all_segments.pkl", "rb") as f:
    segs = pickle.load(f)
all_cms = compute_all_cms(segs, method="pearson", min_segment_len=10, use_fisher_z=True)
X, labs = collect_all_cms_flat(all_cms)
clu = perform_clustering(X, labs, n_clusters=K, standardize=True, use_minibatch=True,
                         n_init=4, max_iter=200, batch_size=256, skip_silhouette=True,
                         random_state=RANDOM_STATE)
seg2state = {l: int(c) for l, c in zip(labs, clu.labels)}

# ── V4 방식 예제 구성: 세그먼트 하나 = 예제 하나 ───────────────────────────
by_state = {c: [] for c in range(K)}
for sid in sorted(segs):
    for s in sorted(segs[sid], key=lambda z: z.start_idx):
        c = seg2state.get((sid, s.segment_id))
        if c is None:
            continue
        by_state[c].append(TSConcatExample(subject_id=sid, cluster_id=c,
                                           segment_ids=(s.segment_id,),
                                           x=np.asarray(s.data, dtype=np.float32)))

lens = np.array([e.x.shape[0] for c in by_state for e in by_state[c]])
MAX_T = int(np.percentile(lens, 95))     # 모든 state 공통 (원본은 state별로 따로)
print(f"공통 max_time_steps = {MAX_T} (전체 {len(lens)}개 세그먼트의 95 퍼센타일)", flush=True)
for c in range(K):
    L = np.array([e.x.shape[0] for e in by_state[c]])
    print(f"  State {c}: 세그먼트 {len(L):3d}개, 길이 {L.min()}~{L.max()} "
          f"(평균 {L.mean():.1f}), 패딩 비율 "
          f"{(1 - np.minimum(L, MAX_T).mean() / MAX_T) * 100:.1f}%", flush=True)

models, norms, info, heldout, allex = {}, {}, [], {}, {}
for c in range(K):
    exs = by_state[c]
    tr, va, te = split_examples(exs, val_split=VAL_SPLIT, test_split=TEST_SPLIT,
                                seed=RANDOM_STATE)
    if len(tr) < 4 or len(va) < 1:
        print(f"\nState {c}: train={len(tr)} val={len(va)} → 학습 불가, 제외", flush=True)
        info.append({"state": c, "status": "skipped", "n": len(exs),
                     "n_train": len(tr), "n_val": len(va)})
        continue
    print(f"\n── State {c}: train {len(tr)} / val {len(va)} / test {len(te)}", flush=True)
    norm = FeatureNormalizer().fit(tr)
    mk = lambda ds, mr, sh: DataLoader(
        TSConcatDataset(ds, max_time_steps=MAX_T, mask_ratio=mr, normalizer=norm,
                        augment=False), batch_size=BATCH, shuffle=sh, num_workers=0)
    cfg = BrainLMTimeSeriesConfig(n_features=100, d_model=256, nhead=8,
                                  num_encoder_layers=4, num_decoder_layers=2,
                                  dim_feedforward=1024, dropout=0.1,
                                  max_time_steps=MAX_T, mask_ratio=MASK_RATIO)
    m, h = train_brainlm_ts(train_loader=mk(tr, MASK_RATIO, True),
                            val_loader=mk(va, MASK_RATIO, False), config=cfg,
                            max_epochs=EPOCHS, lr=LR, patience=PATIENCE,
                            checkpoint_dir=None, device=device)
    models[c], norms[c] = m, norm
    heldout[c] = va + te          # 이 모델이 학습에 쓰지 않은 예제
    allex[c] = exs
    info.append({"state": c, "status": "ok", "n": len(exs), "n_train": len(tr),
                 "n_val": len(va), "n_test": len(te),
                 "best_val_loss": float(min(h["val_loss"])),
                 "n_epochs": len(h["train_loss"])})
    print(f"   best val {min(h['val_loss']):.3f} ({len(h['train_loss'])} epochs)", flush=True)

ok = sorted(models)


@torch.no_grad()
def recon(c_model, exs, c_norm, seed=0):
    """모델 c_model 에 exs 를 넣었을 때의 재구성 손실 (마스킹된 유효 위치에서만 계산)."""
    m = models[c_model].eval().to(device)
    torch.manual_seed(seed)
    dl = DataLoader(TSConcatDataset(exs, max_time_steps=MAX_T, mask_ratio=MASK_RATIO,
                                    normalizer=norms[c_norm], augment=False),
                    batch_size=BATCH, shuffle=False, num_workers=0)
    tot, n = 0.0, 0
    for b in dl:
        out = m.compute_loss(input_x=b["input_x"].to(device),
                             labels=b["labels"].to(device),
                             attention_mask=b["attention_mask"].to(device),
                             mask_labels=b["mask_labels"].to(device))
        tot += float(out["loss"].item()); n += 1
    return tot / max(n, 1)


def build(pool, tag):
    """pool[b] = 열 b 에 쓸 예제 목록. 모든 모델을 같은 예제에 적용한다."""
    M = np.array([[recon(a, pool[b], a) for b in ok] for a in ok])
    R = M - M.mean(1, keepdims=True) - M.mean(0, keepdims=True) + M.mean()
    rows = []
    for i, a in enumerate(ok):
        other = np.delete(M[i], i).mean()
        rows.append({"state": a, "n_eval": len(pool[a]), "self": float(M[i, i]),
                     "other_mean": float(other),
                     "pct_increase": float((other - M[i, i]) / M[i, i] * 100),
                     "centered_diag": float(R[i, i])})
    off = R[~np.eye(len(ok), dtype=bool)]
    out = {"matrix": M.tolist(), "per_state": rows,
           "centered_diag_mean": float(np.diag(R).mean()),
           "centered_off_mean": float(off.mean()),
           "centered_gap": float(np.diag(R).mean() - off.mean()),
           "recon_self_mean": float(np.mean(np.diag(M))),
           "recon_cross_mean": float(M[~np.eye(len(ok), dtype=bool)].mean())}
    out["recon_pct_increase"] = ((out["recon_cross_mean"] - out["recon_self_mean"])
                                 / out["recon_self_mean"] * 100)
    print("\n" + "=" * 72)
    print(f"[{tag}]  평가 예제 수: "
          + ", ".join(f"S{a} {len(pool[a])}개" for a in ok))
    print("      " + "".join(f"data{b}".rjust(12) for b in ok)
          + "   행 기준   중심화 잔차")
    for i, a in enumerate(ok):
        print(f"model{a}" + "".join(f"{M[i, j]:12.3f}" for j in range(len(ok)))
              + f"{rows[i]['pct_increase']:+10.1f}%{R[i, i]:+13.3f}")
    print(f"  전체: 자기 {out['recon_self_mean']:.3f} vs 남 "
          f"{out['recon_cross_mean']:.3f} = {out['recon_pct_increase']:+.1f}%")
    print(f"  중심화 대각 평균 {out['centered_diag_mean']:+.3f} vs 비대각 "
          f"{out['centered_off_mean']:+.3f}  (차 {out['centered_gap']:+.3f})")
    return out


print("\n교차 재구성 손실 계산 중 (행 = 모델, 열 = 데이터)...", flush=True)
res = {"method": "V4 방식 (세그먼트 1개 = 예제 1개, 0 패딩)", "K": K,
       "max_time_steps": MAX_T, "states_trained": ok, "training": info,
       "all_examples": build(allex, "모든 예제 — 대각선에 학습 데이터 포함 (누수 있음)"),
       "held_out": build(heldout, "미학습 예제만 (val + test) — 누수 없음")}
(OUT / "v4_cross_recon.json").write_text(json.dumps(res, indent=2, ensure_ascii=False),
                                         encoding="utf-8")
print(f"\n저장: {OUT / 'v4_cross_recon.json'}")
