"""
RSA / CKA 를 제대로 다시 계산한다.

기존 오류: 모델 A에는 State A 데이터를, 모델 B에는 State B 데이터를 넣고 비교했다.
          입력이 다르면 '모델 차이'와 '입력 차이'가 섞인다.
수정:     두 모델에 **같은 입력 집합**을 통과시켜 표현 구조를 비교한다.

비교 두 가지
  (기준선) 같은 State 0 데이터로 seed만 바꿔 학습한 두 모델
  (관심)   State 0 모델 vs State 1 모델

기준선과 관심값이 비슷하면 → RSA/CKA도 State 차이를 감지하지 못한다는 뜻
기준선이 훨씬 높으면       → 관심값의 낮음이 '표현 내용이 다르다'의 증거가 된다
"""
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
from brainlm.ts_train import extract_ts_latents, train_brainlm_ts  # noqa: E402
from pipeline.clustering import perform_clustering  # noqa: E402
from pipeline.connectivity import collect_all_cms_flat, compute_all_cms  # noqa: E402
from pipeline.v3_sequences import TSConcatExample, split_examples  # noqa: E402

WIN, STRIDE, K = 64, 64, 2
MASK_RATIO, BATCH, LR, PATIENCE, EPOCHS = 0.15, 8, 1e-4, 10, 50
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

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


def train_model(exs, seed):
    torch.manual_seed(seed); np.random.seed(seed)
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
    return m, norm, min(h["val_loss"])


def latents_on(model, norm, exs):
    """지정한 입력 집합을 이 모델에 통과시켜 latent를 얻는다."""
    dl = DataLoader(TSConcatDataset(exs, max_time_steps=WIN, mask_ratio=0.0,
                                    normalizer=norm, augment=False),
                    batch_size=BATCH, shuffle=False, num_workers=0)
    z, _, _ = extract_ts_latents(model, dl, device)
    return z


def rdm(Z):
    Zn = Z / (np.linalg.norm(Z, axis=1, keepdims=True) + 1e-12)
    return 1.0 - Zn @ Zn.T


def rsa(Za, Zb):
    ra, rb = rdm(Za), rdm(Zb)
    iu = np.triu_indices(Za.shape[0], 1)
    return float(np.corrcoef(ra[iu], rb[iu])[0, 1])


def cka(A, B):
    A = A - A.mean(0); B = B - B.mean(0)
    hsic = np.linalg.norm(B.T @ A, "fro") ** 2
    return float(hsic / (np.linalg.norm(A.T @ A, "fro") *
                         np.linalg.norm(B.T @ B, "fro") + 1e-12))


import json

w0, w1 = windows_of(0), windows_of(1)
common = w0 + w1                      # 두 모델에 똑같이 넣을 공통 입력
print(f"공통 입력 집합: {len(common)}개 윈도우 (State0 {len(w0)} + State1 {len(w1)})\n",
      flush=True)

SEED_PAIRS = [(111, 222), (333, 444), (555, 666)]
rows = []
for sa, sb in SEED_PAIRS:
    print(f"--- seed 쌍 ({sa}, {sb}) ---", flush=True)
    m0a, n0a, v0a = train_model(w0, sa)   # State 0 데이터
    m0b, n0b, v0b = train_model(w0, sb)   # State 0 데이터, 다른 seed ← 기준선 짝
    m1, n1, v1 = train_model(w1, sa)      # State 1 데이터
    print(f"  val: S0/{sa} {v0a:.2f}  S0/{sb} {v0b:.2f}  S1/{sa} {v1:.2f}", flush=True)
    Z0a = latents_on(m0a, n0a, common)
    Z0b = latents_on(m0b, n0b, common)
    Z1 = latents_on(m1, n1, common)
    r = {"seeds": [sa, sb],
         "base_rsa": rsa(Z0a, Z0b), "base_cka": cka(Z0a, Z0b),
         "test_rsa": rsa(Z0a, Z1), "test_cka": cka(Z0a, Z1)}
    rows.append(r)
    print("  기준선 RSA %.4f CKA %.4f | 관심 RSA %.4f CKA %.4f"
          % (r["base_rsa"], r["base_cka"], r["test_rsa"], r["test_cka"]), flush=True)

agg = {k: [float(r[k]) for r in rows]
       for k in ("base_rsa", "base_cka", "test_rsa", "test_cka")}
summary = {"n_repeats": len(rows), "n_common_windows": len(common), "runs": rows,
           "mean": {k: float(np.mean(v)) for k, v in agg.items()},
           "sd": {k: float(np.std(v, ddof=1)) for k, v in agg.items()},
           "delta_rsa": [float(r["base_rsa"] - r["test_rsa"]) for r in rows],
           "delta_cka": [float(r["base_cka"] - r["test_cka"]) for r in rows]}
out = ROOT / "visualization_ver6_k2_stride64" / "rsa_cka_repeats.json"
out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

print("\n" + "=" * 74)
print("%-44s %14s %14s" % ("비교 (n=%d 반복)" % len(rows), "RSA 평균±SD", "CKA 평균±SD"))
print("-" * 74)
print("%-44s %6.4f ± %.4f %6.4f ± %.4f"
      % ("(기준선) 같은 State0 데이터, seed만 다름",
         summary["mean"]["base_rsa"], summary["sd"]["base_rsa"],
         summary["mean"]["base_cka"], summary["sd"]["base_cka"]))
print("%-44s %6.4f ± %.4f %6.4f ± %.4f"
      % ("(관심)   State0 모델 vs State1 모델",
         summary["mean"]["test_rsa"], summary["sd"]["test_rsa"],
         summary["mean"]["test_cka"], summary["sd"]["test_cka"]))
print("=" * 74)
print("기준선 − 관심  RSA %s  CKA %s"
      % ([round(d, 4) for d in summary["delta_rsa"]],
         [round(d, 4) for d in summary["delta_cka"]]))
print(f"저장: {out}")
