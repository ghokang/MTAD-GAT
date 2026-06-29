"""
V3 utilities: CM-cluster → concatenated time-series windows.

Design (used by notebooks/full_pipeline_v3.ipynb):
- CM is computed per Segment, then clustered.
- For each subject, map (subject_id, segment_id) -> cm_cluster_id.
- Build examples by taking sliding windows of length `seq_len` over segments
  *within the same CM cluster* (all segments in the window share the same cluster id),
  and concatenating raw segment time series along time axis.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np

from .segmentation import Segment


@dataclass(frozen=True)
class TSConcatExample:
    """One concatenated time-series training example."""

    subject_id: str
    cluster_id: int
    segment_ids: Tuple[int, ...]
    x: np.ndarray  # shape (T_total, n_features)


def _build_cluster_lookup(
    cm_labels_list: Sequence[Tuple[str, int]],
    cluster_labels_flat: Sequence[int],
) -> Dict[Tuple[str, int], int]:
    if len(cm_labels_list) != len(cluster_labels_flat):
        raise ValueError(
            f"cm_labels_list and cluster_labels_flat must align: "
            f"{len(cm_labels_list)} != {len(cluster_labels_flat)}"
        )
    lookup: Dict[Tuple[str, int], int] = {}
    for k, cid in zip(cm_labels_list, cluster_labels_flat):
        lookup[(str(k[0]), int(k[1]))] = int(cid)
    return lookup


def build_ts_concat_sequences(
    all_segments: Dict[str, List[Segment]],
    cm_labels_list: Sequence[Tuple[str, int]],
    cluster_labels_flat: Sequence[int],
    seq_len: int,
    stride: int,
) -> List[TSConcatExample]:
    """
    Build concatenated time-series examples.

    Args:
        all_segments: {subject_id: [Segment,...]} in temporal order (segment_id order)
        cm_labels_list: list of (subject_id, segment_id) aligned with clustering input
        cluster_labels_flat: cluster id per CM sample (same order as cm_labels_list)
        seq_len: number of consecutive segments per window
        stride: stride over segment index (not time)

    Returns:
        List of TSConcatExample. Each example has x of shape (sum(T_i), n_features).
    """
    if seq_len <= 0:
        raise ValueError("seq_len must be positive")
    if stride <= 0:
        raise ValueError("stride must be positive")

    cluster_lookup = _build_cluster_lookup(cm_labels_list, cluster_labels_flat)
    examples: List[TSConcatExample] = []

    for subject_id, segments in all_segments.items():
        if not segments:
            continue

        # Ensure stable temporal order
        segments_sorted = sorted(segments, key=lambda s: int(s.segment_id))

        # Keep only segments that have a CM/cluster assignment.
        segs_with_cluster: List[Tuple[Segment, int]] = []
        for seg in segments_sorted:
            key = (str(subject_id), int(seg.segment_id))
            if key in cluster_lookup:
                segs_with_cluster.append((seg, cluster_lookup[key]))

        if len(segs_with_cluster) < seq_len:
            continue

        for start in range(0, len(segs_with_cluster) - seq_len + 1, stride):
            window = segs_with_cluster[start : start + seq_len]
            cids = [cid for (_, cid) in window]
            # Only allow windows fully within one cluster.
            if len(set(cids)) != 1:
                continue

            seg_ids = tuple(int(seg.segment_id) for (seg, _) in window)
            xs = [np.asarray(seg.data, dtype=np.float32) for (seg, _) in window]
            # Defensive: all segments should share n_features
            n_features = xs[0].shape[1]
            if any(x.ndim != 2 or x.shape[1] != n_features for x in xs):
                raise ValueError(f"Inconsistent feature dims for subject {subject_id} window {seg_ids}")

            x_cat = np.concatenate(xs, axis=0)  # (T_total, n_features)
            examples.append(
                TSConcatExample(
                    subject_id=str(subject_id),
                    cluster_id=int(cids[0]),
                    segment_ids=seg_ids,
                    x=x_cat,
                )
            )

    return examples


def count_by_cluster(examples: Sequence[TSConcatExample]) -> Dict[int, int]:
    counts: Dict[int, int] = {}
    for ex in examples:
        counts[int(ex.cluster_id)] = counts.get(int(ex.cluster_id), 0) + 1
    return counts


def split_examples(
    examples: Sequence[TSConcatExample],
    val_split: float = 0.1,
    test_split: float = 0.1,
    seed: int = 42,
) -> Tuple[List[TSConcatExample], List[TSConcatExample], List[TSConcatExample]]:
    """
    Subject-level split to avoid leakage: subjects are partitioned first, then
    all examples from each subject are assigned to that partition.
    """
    if not (0.0 <= val_split < 1.0 and 0.0 <= test_split < 1.0 and (val_split + test_split) < 1.0):
        raise ValueError("val_split and test_split must be in [0,1) and sum < 1")

    # Group examples by subject
    by_subj: Dict[str, List[TSConcatExample]] = {}
    for ex in examples:
        by_subj.setdefault(str(ex.subject_id), []).append(ex)

    subjects = sorted(by_subj.keys())
    rng = np.random.default_rng(seed)
    rng.shuffle(subjects)

    n_total = len(subjects)
    n_test = int(round(n_total * test_split))
    n_val = int(round(n_total * val_split))
    n_train = max(0, n_total - n_test - n_val)

    train_subj = set(subjects[:n_train])
    val_subj = set(subjects[n_train : n_train + n_val])
    test_subj = set(subjects[n_train + n_val :])

    train: List[TSConcatExample] = []
    val: List[TSConcatExample] = []
    test: List[TSConcatExample] = []
    for sid, exs in by_subj.items():
        if sid in train_subj:
            train.extend(exs)
        elif sid in val_subj:
            val.extend(exs)
        else:
            test.extend(exs)

    return train, val, test


def suggest_max_time_steps(
    examples: Sequence[TSConcatExample],
    percentile: float = 95.0,
    absolute_cap: int = 2048,
) -> int:
    """
    Pick a padding/truncation length from a percentile of observed lengths.
    """
    if not examples:
        return min(256, int(absolute_cap))
    lengths = np.array([int(ex.x.shape[0]) for ex in examples], dtype=np.int32)
    p = float(np.percentile(lengths, percentile))
    p = int(max(1, round(p)))
    return int(min(p, int(absolute_cap)))

