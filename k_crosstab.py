"""K=2/3/4 클러스터 레이블의 교차표 — 희소 state가 K를 낮추면 흡수되는가?"""
import pickle, sys
from pathlib import Path
import numpy as np

ROOT = Path("/Users/mac/Desktop/code/MTAD-GAT")
sys.path.insert(0, str(ROOT))
from pipeline.clustering import perform_clustering
from pipeline.connectivity import collect_all_cms_flat, compute_all_cms

with open(ROOT / "checkpoint/brainlm_v3/cache/all_segments.pkl", "rb") as f:
    all_segments = pickle.load(f)
all_cms = compute_all_cms(all_segments, method="pearson", min_segment_len=10,
                          use_fisher_z=True)
X, labs = collect_all_cms_flat(all_cms)
len_of = {(sid, s.segment_id): int(np.asarray(s.data).shape[0])
          for sid in all_segments for s in all_segments[sid]}
TP = np.array([len_of[l] for l in labs])

lab = {}
for K in (2, 3, 4):
    clu = perform_clustering(X, labs, n_clusters=K, standardize=True,
                             use_minibatch=True, n_init=4, max_iter=200,
                             batch_size=256, skip_silhouette=True, random_state=42)
    lab[K] = np.asarray(clu.labels)
    print(f"\nK={K}  state별 (세그먼트 수, 총 TP)")
    for c in range(K):
        m = lab[K] == c
        print(f"   S{c}: {m.sum():3d}개, {TP[m].sum():6d} TP")

for a, b in ((4, 3), (3, 2)):
    print(f"\n교차표 — 행 K={a}, 열 K={b} (총 TP)")
    hdr = "        " + "".join(f"K{b}-S{j}".rjust(10) for j in range(b))
    print(hdr)
    for i in range(a):
        row = "".join(f"{TP[(lab[a]==i)&(lab[b]==j)].sum():10d}" for j in range(b))
        print(f"  K{a}-S{i}" + row)
