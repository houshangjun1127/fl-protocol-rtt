"""Emit the two-panel Table S1 (R1 by tau; R5 by vol_max x drop_max grid).

No training.  Reads results/rank_inv/threshold_sensitivity.json and prints
markdown to stdout, ready to paste into results/supplementary_material.md.

Usage:  python src/make_table_s1.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "rank_inv" / "threshold_sensitivity.json"

CELLS = [
    ("mnist|a0.05", "MNIST 0.05"),
    ("mnist|a0.1", "MNIST 0.1"),
    ("mnist|a0.3", "MNIST 0.3"),
    ("fashion|a0.05", "Fashion 0.05"),
    ("fashion|a0.1", "Fashion 0.1"),
    ("fashion|a0.3", "Fashion 0.3"),
    ("cifar10|a0.1", "CIFAR-10 0.1"),
]

TAU = ["tau=1", "tau=2 (baseline)", "tau=3"]
VOL = ["vol_max=0.005", "vol_max=0.01 (baseline)", "vol_max=0.02"]
DROP = ["drop_max=3", "drop_max=5 (baseline)", "drop_max=10"]


def cell_str(node):
    if not node:
        return "–"
    n = node.get("n_inversions_robust_R1")
    p = node.get("n_pairs_robust_R1")
    if n is None:
        return "–"
    return "%d (%d)" % (n, p)


def r5_str(node):
    if not node:
        return "–"
    n = node.get("n_inversions_robust_R5")
    p = node.get("n_pairs_robust_R5")
    if n is None:
        return "–"
    return "%d (%d)" % (n, p)


def main() -> int:
    data = json.loads(SRC.read_text(encoding="utf-8"))["results"]
    print("**(a) seed-replicated flips (R1), by near-tie filter τ**\n")
    print("| τ | cells non-empty | " + " | ".join(l for _, l in CELLS) + " |")
    print("|---|---|" + "---|" * len(CELLS))
    for cfg in TAU:
        r = data[cfg]["cells"]
        nz = sum(1 for c, _ in CELLS if r.get(c, {}).get("n_inversions_robust_R1", 0) > 0)
        mark = " *(used)*" if "baseline" in cfg else ""
        print("| %s%s | %d / 7 | " % (cfg.split(" ")[0], mark, nz)
              + " | ".join(cell_str(r.get(c)) for c, _ in CELLS) + " |")
    # The sweep varies ONE threshold at a time off the baseline, so the configs
    # are single-knob entries ("vol_max=0.005", "drop_max=3", ...), not
    # (vol_max, drop_max) pairs.  Rendering them as a grid was a bug that left
    # this panel empty; each config is one row.
    print("\n**(b) stability-screened flips (R5), one threshold varied at a "
          "time off the baseline**\n")
    print("| varied threshold | cells non-empty (R5) | "
          + " | ".join(l for _, l in CELLS) + " |")
    print("|---|---|" + "---|" * len(CELLS))
    for cfg in VOL + DROP:
        if cfg not in data:
            continue
        r = data[cfg]["cells"]
        nz = sum(1 for c, _ in CELLS
                 if (r.get(c, {}).get("n_inversions_robust_R5") or 0) > 0)
        mark = " *(used)*" if "baseline" in cfg else ""
        print("| %s%s | %d / 7 | " % (cfg, mark, nz)
              + " | ".join(r5_str(r.get(c)) for c, _ in CELLS) + " |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
