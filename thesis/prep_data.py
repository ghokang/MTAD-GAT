"""논문 그림용 데이터 준비: 세그먼트 → CM → 클러스터링(seed=42 재현) → npz 캐시."""
import os, pickle, sys, json
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import numpy as np
from pathlib import Path

ROOT = Path("/Users/mac/Desktop/code/MTAD-GAT")
sys.path.insert(0, str(ROOT))
OUT = ROOT / "thesis"

from pipeline.clustering import get_cluster_centroids, perform_clustering, compute_cluster_similarity
from pipeline.connectivity import collect_all_cms_flat, compute_all_cms
from pipeline.segmentation import get_segment_statistics

with open(ROOT / "checkpoint/brainlm_v3/cache/all_segments.pkl", "rb") as f:
    all_segments = pickle.load(f)

seg_stats = get_segment_statistics(all_segments)
print("segments:", len(seg_stats), "subjects:", len(all_segments))
print(seg_stats.columns.tolist())

all_cms = compute_all_cms(all_segments, method="pearson", min_segment_len=10, use_fisher_z=True)
X_cm, cm_labels = collect_all_cms_flat(all_cms)
n_features = next(iter(all_cms.values()))[0].n_features
print("X_cm:", X_cm.shape, "n_features:", n_features)

res = perform_clustering(X_cm, cm_labels, n_clusters=4, standardize=True, use_minibatch=True,
                         n_init=4, max_iter=200, batch_size=256, skip_silhouette=True, random_state=42)
labels = np.asarray(res.labels)
sizes = res.get_cluster_sizes()
print("cluster sizes:", sizes)

centroids = get_cluster_centroids(res, n_features=n_features)
cent = {int(k): np.asarray(v) for k, v in (centroids.items() if isinstance(centroids, dict)
                                           else enumerate(centroids))}
print("centroid shapes:", {k: v.shape for k, v in cent.items()})

# 피험자별 State 점유율
subj_ids = sorted({s for s, _ in cm_labels})
occ = np.zeros((len(subj_ids), 4))
for (sid, _), lab in zip(cm_labels, labels):
    occ[subj_ids.index(sid), int(lab)] += 1

np.savez_compressed(
    OUT / "figdata.npz",
    labels=labels,
    seg_len=seg_stats["length"].to_numpy(),
    seg_subject=np.array([str(s) for s in seg_stats.iloc[:, 0]]),
    occupancy=occ,
    subj_ids=np.array(subj_ids, dtype=str),
    **{f"centroid_{k}": v for k, v in cent.items()},
)
print("saved figdata.npz")
print("seg len: mean %.1f min %d max %d" % (seg_stats["length"].mean(),
                                            seg_stats["length"].min(), seg_stats["length"].max()))
