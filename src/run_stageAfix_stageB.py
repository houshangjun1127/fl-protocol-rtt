#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""Re-run Stage B with the Stage A selection the documented rule picks.

WHY
---
The Stage A records in `tuned_mnist_a0.1.json` store, for fedavgm / fedproxw /
fedadam, a selection that differs from the argmax the documented
stability-first rule (prefer stable, then highest late accuracy) returns when
applied to the full Stage A grid. The grid traces themselves are intact and
reproducible: a fresh re-run of the same grid reproduces every late_acc to
4 dp, and every setting in the grid is `stable` under the documented
thresholds (vol <= 0.01, drop <= 5 pt), so the rule reduces to the late_acc
argmax over the full grid. `src/tune_hp_val.py` recomputes exactly that, as
its `by_test` arm, and `src/compare_three_protocols.py` uses the re-runs
below as one of its three protocols.

WHAT THIS SCRIPT DOES
---------------------
Re-runs the six seeds at 60 rounds for the three affected methods using the
full-grid argmax hyperparameters, into an isolated directory
(`results/stageAfix/`) so the published traces in `results/rank_inv/` are
never touched. The other four methods are bit-identical to the published runs
by construction and are not re-run.

Protocol otherwise identical to published Stage B: dataset mnist, alpha 0.1,
cnn, dirichlet, 10 clients, 1 local epoch, lr 0.05, lr_decay 0.9, batch 64,
10000 train / 2000 test, seeds 0..5.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from rank_inv_runner import run_one  # noqa: E402

ROOT = os.path.dirname(HERE)
OUTDIR = os.path.join(ROOT, "results", "stageAfix")

# frozen: the full-grid argmax under the documented rule, cross-checked by
# tune_hp_val.py's by_test arm
CORRECTED = {
    "fedavgm":  {"beta": 0.7, "lr_s": 1.0},
    "fedproxw": {"rho": 0.2},
    "fedadam":  {"lr_s": 0.03, "tau": 1e-3},
}


def label_of(hp):
    return ",".join("%s=%s" % (k, v) for k, v in sorted(hp.items())) or "def"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="mnist")
    ap.add_argument("--alpha", default="0.1")
    ap.add_argument("--seeds", default="0,1,2,3,4,5")
    ap.add_argument("--methods", default=",".join(CORRECTED))
    ap.add_argument("--rounds", type=int, default=60)
    ap.add_argument("--lr", type=float, default=0.05)
    ap.add_argument("--lr-decay", type=float, default=0.9, dest="lr_decay")
    ap.add_argument("--out-dir", default=OUTDIR)
    args = ap.parse_args()

    # guard: the corrected values must not be silently edited away from under us
    pub = json.load(open(os.path.join(
        ROOT, "results", "rank_inv",
        "tuned_%s_a%s.json" % (args.dataset, args.alpha)), encoding="utf-8"))
    print("published (buggy) vs corrected selection:")
    for m, hp in CORRECTED.items():
        k = "%s|%s|%s" % (args.dataset, args.alpha, m)
        print("  %-9s published=%-24s corrected=%-24s" % (
            m, pub.get(k, {}).get("label"), label_of(hp)))

    os.makedirs(args.out_dir, exist_ok=True)
    for m in args.methods.split(","):
        hp = CORRECTED[m]
        lab = label_of(hp)
        for s in [int(x) for x in args.seeds.split(",")]:
            tag = "stageAfix_%s_a%s_%s_%s_s%d" % (
                args.dataset, args.alpha, m, lab, s)
            out = os.path.join(args.out_dir, "%s.json" % tag)
            if os.path.exists(out):
                print("skip (exists) %s" % tag, flush=True)
                continue
            cfg = dict(dataset=args.dataset, arch="cnn", skew="dirichlet",
                       alpha=float(args.alpha), n_clients=10,
                       rounds=args.rounds, local_epochs=1, lr=args.lr,
                       lr_decay=args.lr_decay, batch_size=64,
                       n_train=10000, n_test=2000, seed=s, method=m,
                       _hp=lab, tag=tag, **hp)
            print("[run] %s" % tag, flush=True)
            res = run_one(cfg)
            with open(out, "w", encoding="utf-8") as f:
                json.dump(res, f, indent=1)

    with open(os.path.join(args.out_dir, "_selection_used.json"), "w",
              encoding="utf-8") as f:
        json.dump({m: {"hp": hp, "label": label_of(hp)}
                   for m, hp in CORRECTED.items()}, f, indent=1)
    print("done -> %s" % args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
