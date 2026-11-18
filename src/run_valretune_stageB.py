#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Validation-split Stage B: re-run the six seeds with VALIDATION-selected
hyperparameters.

WHY
---
Stage A selected hyperparameters on the test split (disclosed in Section 3.0).
`src/tune_hp_val.py` re-ran the same Stage A grid with a disjoint validation
split evaluated alongside, and read the selection off both metrics from one set
of runs. Three of the seven methods pick a different setting under validation
(fedavgm beta 0.7 -> 0.9, fedproxw rho 0.2 -> 0.5, feddyn alpha 0.3 -> 0.1).

That changes the selection. Whether it changes any *conclusion* is a separate
question, and this script answers it: re-run Stage B with the validation-chosen
settings and compare the resulting rankings against the published ones.

ISOLATION
---------
Output goes to `results/valretune/`, NOT `results/rank_inv/`. This matters:
`analyze_rank_inv.load_results` globs every non-`tuned_*` json in the directory
it is handed, so dropping these traces next to the published ones would silently
add a second run of the same (cell, seed, method) to every downstream statistic.
A separate directory is the only safe place for them.

Only the methods whose selection actually changed need re-running; the other
four are bit-identical to the published runs by construction.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from rank_inv_runner import run_one  # noqa: E402
import methods as MS  # noqa: E402

ROOT = os.path.dirname(HERE)
OUTDIR = os.path.join(ROOT, "results", "valretune")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="mnist")
    ap.add_argument("--alpha", default="0.1")
    ap.add_argument("--seeds", default="0,1,2,3,4,5")
    ap.add_argument("--methods", default="")
    ap.add_argument("--rounds", type=int, default=60)
    ap.add_argument("--lr", type=float, default=0.05)
    ap.add_argument("--lr-decay", type=float, default=0.9, dest="lr_decay")
    ap.add_argument("--tuned", default=os.path.join(
        ROOT, "results", "rank_inv", "tunedval_mnist_a0.1.json"))
    ap.add_argument("--out-dir", default=OUTDIR)
    ap.add_argument("--all", action="store_true",
                    help="run every method, not only those whose selection "
                         "differs between the two metrics")
    args = ap.parse_args()

    with open(args.tuned, encoding="utf-8") as f:
        tun = json.load(f)
    sel = tun.get("selection", {})

    if args.methods:
        methods = args.methods.split(",")
    elif args.all:
        methods = [m for m in MS.METHODS]
    else:
        methods = [m for m, v in sel.items() if not v.get("agree", True)]

    os.makedirs(args.out_dir, exist_ok=True)
    print("methods to re-run (selection changed): %s" % ", ".join(methods))
    for m in methods:
        v = sel.get(m, {})
        print("  %-9s test=%-22s -> val=%s" % (
            m, v.get("by_test", {}).get("label", "?"),
            v.get("by_val", {}).get("label", "?")))

    for m in methods:
        hp = sel[m]["by_val"]["hp"]
        for s in [int(x) for x in args.seeds.split(",")]:
            tag = "valretune_%s_a%s_%s_%s_s%d" % (
                args.dataset, args.alpha, m,
                sel[m]["by_val"]["label"] or "def", s)
            out = os.path.join(args.out_dir, "%s.json" % tag)
            if os.path.exists(out):
                print("skip (exists) %s" % tag, flush=True)
                continue
            cfg = dict(dataset=args.dataset, arch="cnn", skew="dirichlet",
                       alpha=float(args.alpha), n_clients=10,
                       rounds=args.rounds, local_epochs=1, lr=args.lr,
                       lr_decay=args.lr_decay, batch_size=64,
                       n_train=10000, n_test=2000, seed=s, method=m,
                       _hp=sel[m]["by_val"]["label"], tag=tag, **hp)
            print("run %s" % tag, flush=True)
            res = run_one(cfg)
            with open(out, "w", encoding="utf-8") as f:
                json.dump(res, f, indent=1)

    with open(os.path.join(args.out_dir, "_selection_used.json"), "w",
              encoding="utf-8") as f:
        json.dump({m: sel[m]["by_val"] for m in methods}, f, indent=1)
    print("done -> %s" % args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
