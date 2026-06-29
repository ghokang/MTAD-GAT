#!/usr/bin/env python3
"""Run full_pipeline_v2 cells required before final BrainLM training."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB_PATH = ROOT / "notebooks" / "full_pipeline_v2.ipynb"

# Code cell indices (skip markdown, viz, scan/grid if results exist)
ALWAYS = [2, 3, 4, 5, 6, 10]  # setup, seg, cm, cluster, sequence helpers
RANK = 14
FINAL = 15
LATENT_VIZ = 16


def _load_notebook():
    return json.loads(NB_PATH.read_text(encoding="utf-8"))


def _cell_code(nb, idx: int) -> str:
    return "".join(nb["cells"][idx].get("source", []))


def _run_cells(indices: list[int], skip_grid_if_exists: bool = True) -> None:
    nb = _load_notebook()
    g = {"__name__": "__main__"}
    grid_csv = ROOT / "visualization_ver2" / "grid_seq_len_stride" / "grid_results_z.csv"

    for idx in indices:
        if skip_grid_if_exists and idx == 13 and grid_csv.exists() and grid_csv.stat().st_size > 100:
            print(f"[skip] cell {idx}: grid_results_z.csv already populated")
            continue
        code = _cell_code(nb, idx)
        if not code.strip():
            continue
        print(f"\n{'=' * 60}\nExecuting cell {idx}\n{'=' * 60}")
        exec(compile(code, f"{NB_PATH}:cell{idx}", "exec"), g, g)


def main() -> None:
    import os

    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
    print("Working directory:", Path.cwd())

    to_run = list(ALWAYS)
    grid_csv = ROOT / "visualization_ver2" / "grid_seq_len_stride" / "grid_results_z.csv"
    if not (grid_csv.exists() and grid_csv.stat().st_size > 100):
        to_run.extend([12, 13])
    else:
        print("[info] Using existing grid_results; skipping cells 12-13")
    to_run.extend([RANK, FINAL, LATENT_VIZ])

    _run_cells(to_run, skip_grid_if_exists=True)
    print("\nDone.")


if __name__ == "__main__":
    main()
