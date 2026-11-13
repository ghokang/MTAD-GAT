"""
교차 재구성 손실 행렬을 이중 중심화(double-centering)해서 본다.

행 기준 "자기 vs 남" 비율은 교란이 있다. 어떤 state의 데이터는 모든 모델에게
어렵고(열 효과), 어떤 모델은 모든 데이터에서 손실이 낮다(행 효과).
L[i,j] = mu + row_i + col_j + resid 로 보고, 대각 잔차가 음수여야
"자기 데이터에 특화되었다"는 뜻이 된다.
"""
import json
from pathlib import Path
import numpy as np

ROOT = Path("/Users/mac/Desktop/code/MTAD-GAT")


def report(name, M, labels):
    M = np.asarray(M, dtype=float)
    k = M.shape[0]
    R = M - M.mean(1, keepdims=True) - M.mean(0, keepdims=True) + M.mean()
    diag = np.diag(R)
    off = R[~np.eye(k, dtype=bool)]
    print(f"\n{'='*70}\n{name}")
    print(f"{'':>8}" + "".join(f"data{l}".rjust(11) for l in labels) + "   행 기준 자기vs남")
    for i, a in enumerate(labels):
        self_l = M[i, i]
        other = np.delete(M[i], i).mean()
        print(f"model{a:<3}" + "".join(f"{M[i,j]:11.2f}" for j in range(k))
              + f"{(other-self_l)/self_l*100:+15.1f}%")
    print(f"\n  이중 중심화 잔차 (음수 = 기대보다 잘 복원):")
    for i, a in enumerate(labels):
        mark = "  ✓" if diag[i] < 0 else "  ✗"
        print(f"    대각 State {a}: {diag[i]:+8.3f}{mark}")
    print(f"    대각 평균 {diag.mean():+.3f}  vs  비대각 평균 {off.mean():+.3f}"
          f"   (차 {diag.mean()-off.mean():+.3f})")
    print(f"  열 효과 (데이터 난이도, 전체 평균 대비): "
          + "  ".join(f"S{l} {M.mean(0)[i]-M.mean():+.1f}" for i, l in enumerate(labels)))
    print(f"  행 효과 (모델 전반 손실,  전체 평균 대비): "
          + "  ".join(f"S{l} {M.mean(1)[i]-M.mean():+.1f}" for i, l in enumerate(labels)))
    return diag, off


v4 = json.loads((ROOT / "visualization_ver4_crossrecon/v4_cross_recon.json").read_text())
report("V4 방식 (세그먼트=예제, 0 패딩, K=4, 공통 max_T=264)",
       v4["matrix"], v4["states_trained"])

import csv
def load_csv(p):
    rows = list(csv.reader(open(p)))
    lab = [int(h.replace("data", "")) for h in rows[0][1:]]
    return [[float(x) for x in r[1:]] for r in rows[1:]], lab

M, lab = load_csv(ROOT / "visualization_ver6_k4/tables/cross_state_recon_loss.csv")
report("V6 방식 (concat → 균일 64 TP, K=4, stride 64)", M, lab)

M, lab = load_csv(ROOT / "visualization_ver6_k3/tables/cross_state_recon_loss.csv")
report("V6 방식 (concat → 균일 64 TP, K=3, stride 32)", M, lab)

M, lab = load_csv(ROOT / "visualization_ver6_k2_stride64/tables/cross_state_recon_loss.csv")
report("V6 방식 (concat → 균일 64 TP, K=2, stride 64)  ← 대조군 검증본", M, lab)
