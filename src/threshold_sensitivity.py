"""Threshold sensitivity sweep for the robustness criteria of Section 3.1.

The robustness levels R1/R2/R5 of the rank-inversion analysis depend on three
author-chosen thresholds: the near-tie filter tau, the last-10-round standard
deviation bound vol_max, and the post-peak regression bound drop_max.  This
script re-runs the (training-free) analysis over a grid of those thresholds on
the released Stage B traces and records how the per-cell conclusions move.

Usage:
    python src/threshold_sensitivity.py [--outdir results/rank_inv]

Writes threshold_sensitivity.json next to the other analysis products.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ANALYZER = os.path.join(HERE, "analyze_rank_inv.py")
TRACE_DIR = os.path.join(HERE, "..", "results", "rank_inv")

# (label, extra CLI args).  The baseline is tau=2, vol_max=0.01, drop_max=5.0.
CONFIGS = [
    ("tau=1", ["--tau", "1"]),
    ("tau=2 (baseline)", ["--tau", "2"]),
    ("tau=3", ["--tau", "3"]),
    ("vol_max=0.005", ["--vol-max", "0.005"]),
    ("vol_max=0.01 (baseline)", ["--vol-max", "0.01"]),
    ("vol_max=0.02", ["--vol-max", "0.02"]),
    ("drop_max=3", ["--drop-max", "3.0"]),
    ("drop_max=5 (baseline)", ["--drop-max", "5.0"]),
    ("drop_max=10", ["--drop-max", "10.0"]),
]

CELL_ORDER = [
    "mnist|a0.05", "mnist|a0.1", "mnist|a0.3",
    "fashion|a0.05", "fashion|a0.1", "fashion|a0.3",
    "cifar10|a0.1",
]


def run_one(python, extra, tmpdir):
    out = os.path.join(tmpdir, "r_%d.json" % abs(hash(tuple(extra))))
    cmd = [python, ANALYZER, "--dir", TRACE_DIR, "--out", out] + extra
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)
    with open(out) as fh:
        return json.load(fh)


def digest(report):
    """Per-cell R1/R2/R5 verdicts plus the cross-dataset replicating pairs."""
    summ = report.get("summary", {})
    cells = {}
    for cell in CELL_ORDER:
        s = summ.get(cell, {})
        cells[cell] = {
            "n_inversions_robust_R1": s.get("n_inversions_robust_R1"),
            "n_pairs_robust_R1": s.get("n_pairs_robust_R1"),
            "R2_pass": s.get("R2_pass"),
            "n_inversions_robust_R5": s.get("n_inversions_robust_R5"),
            "n_pairs_robust_R5": s.get("n_pairs_robust_R5"),
        }
    r4 = report.get("R4_replicated_pairs") or report.get("r4_replicated_pairs")
    if r4 is None:
        # fall back: look one level down for a dict of pair -> [cells]
        for key in report:
            if "r4" in key.lower() and isinstance(report[key], dict):
                r4 = report[key]
                break
    if isinstance(r4, dict):
        r4 = sorted(k for k, v in r4.items() if v)
    return {"cells": cells, "cells_with_R1": sum(
        1 for c in cells.values() if (c["n_inversions_robust_R1"] or 0) > 0),
        "r4_pairs": r4}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=TRACE_DIR)
    ap.add_argument("--python", default=sys.executable)
    args = ap.parse_args()

    results = {}
    with tempfile.TemporaryDirectory() as tmpdir:
        for label, extra in CONFIGS:
            rep = run_one(args.python, extra, tmpdir)
            results[label] = digest(rep)
            print("%-26s cells with any robust flip: %d/7"
                  % (label, results[label]["cells_with_R1"]))

    out = os.path.join(args.outdir, "threshold_sensitivity.json")
    with open(out, "w") as fh:
        json.dump({"configs": [c[0] for c in CONFIGS],
                   "baseline": "tau=2 (baseline)",
                   "results": results}, fh, indent=2, sort_keys=False)
    print("->", out)


if __name__ == "__main__":
    main()
