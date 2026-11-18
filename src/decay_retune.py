#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Per-decay retuning control for the Section 3.2 decay result.

WHY
---
Section 3.2 holds every hyperparameter fixed and varies only the global
learning-rate decay, and reports that the FedAvg-SCAFFOLD gap moves by an order
of magnitude and that the leader reverses. The obvious objection is that
the hyperparameters were tuned at decay = 0.90 only, so the decay 1.00 runs may
be operating at a bad learning rate for that schedule -- in which case the
"decay effect" would partly be a tuning artefact, and the size of the reported
swing would not survive a fair per-decay comparison.

This script runs that control. For each (method, decay) it re-tunes the learning
rate from scratch under THAT decay, then runs all six seeds at 60 rounds with
the setting that tune chose. Comparing the per-decay-retuned gaps with the
published fixed-HP gaps answers whether the decay result is a property of the
schedule or of the tuning protocol.

SCOPE
-----
MNIST alpha = 0.1 only, SCAFFOLD and FedAvg only. These are the two methods the
Section 3.2 claim is about. The published SCAFFOLD and FedAvg grids are empty
(no method-specific hyperparameters), so the only knob that can be retuned per
decay is the local learning rate; three values are swept.

TUNING PROTOCOL
---------------
Deliberately the SAME as the published Stage A -- select on the test split at
the 85%-of-budget reference round, with the stability preference of
`tune_hp.py` v2 -- because the question is whether the *published* protocol's
conclusion survives, not whether a better protocol exists. Retuning on a
validation split here would confound the decay comparison with the
validation-selection comparison.

ISOLATION
---------
Output goes to `results/decayretune/`, never `results/rank_inv/`, for the same
reason as `run_valretune_stageB.py`: the analyser globs every json in the
directory it is given, and these runs must not be added to any published
statistic.

Usage
-----
    python src/decay_retune.py            # tune (40 r) then Stage B (60 r)
    python src/decay_retune.py --skip-tune
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from rank_inv_runner import run_one  # noqa: E402
from analyze_rank_inv import late_volatility, post_peak_drop  # noqa: E402

ROOT = os.path.dirname(HERE)
OUTDIR = os.path.join(ROOT, "results", "decayretune")

METHODS = ["scaffold", "fedavg"]
DECAYS = [0.90, 1.00]
LRS = [0.025, 0.05, 0.1]
VOL_MAX = 0.01
DROP_MAX = 5.0


def score(trace, vol_max=VOL_MAX, drop_max=DROP_MAX):
    a = np.array([x["acc"] for x in trace], dtype=float)
    ref = a[int(len(a) * 0.85) - 1]
    vol = late_volatility(a)
    drop = post_peak_drop(a)
    return {"late_acc": float(ref), "peak_acc": float(a.max()),
            "final_acc": float(a[-1]), "last10sd": float(vol),
            "post_peak_drop": float(drop),
            "stable": bool(vol <= vol_max and drop <= drop_max)}


def tune(args):
    path = os.path.join(OUTDIR, "_decayretune_tuning.json")
    doc = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)

    for m in METHODS:
        for dc in DECAYS:
            key = "%s|decay%.2f" % (m, dc)
            best = None
            for lr in LRS:
                label = "lr=%s" % lr
                if key in doc and any(s["label"] == label
                                      for s in doc[key].get("settings", [])):
                    continue
                cfg = dict(dataset=args.dataset, arch="cnn", skew="dirichlet",
                           alpha=float(args.alpha), n_clients=10,
                           rounds=args.tune_rounds, local_epochs=1, lr=lr,
                           lr_decay=dc, batch_size=64, n_train=10000,
                           n_test=2000, seed=args.seed, method=m,
                           _hp=label, tag="decayretune_tune_%s_dc%.2f_%s"
                                          % (m, dc, label))
                print("[tune] %s" % cfg["tag"], flush=True)
                res = run_one(cfg)
                rec = {"lr": lr, "label": label, **score(res["trace"])}
                doc.setdefault(key, {}).setdefault("settings", [])
                doc[key]["settings"] = [s for s in doc[key]["settings"]
                                        if s["label"] != label] + [rec]
                k = (rec["stable"], rec["late_acc"])
                if best is None or k > (best["stable"], best["late_acc"]):
                    best = rec
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(doc, f, indent=1)
            if best is not None:
                doc[key]["best"] = {"lr": best["lr"], "label": best["label"],
                                    **{k2: best[k2] for k2 in
                                       ("late_acc", "peak_acc", "final_acc",
                                        "stable")}}
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(doc, f, indent=1)
                print("  -> %s best %s late=%.4f stable=%s"
                      % (key, best["label"], best["late_acc"], best["stable"]),
                      flush=True)
    return doc


def stage_b(args, tuning):
    for m in METHODS:
        for dc in DECAYS:
            key = "%s|decay%.2f" % (m, dc)
            lr = tuning[key]["best"]["lr"]
            for s in args.seeds:
                # The method MUST be in the tag: scaffold and fedavg can pick
                # the same lr at the same decay (both chose 0.1 at 0.90), and
                # without it the two runs collide on one filename -- the second
                # is silently skipped by the `skip (exists)` guard, which is
                # exactly what happened on the first attempt.
                tag = "decayretune_%s_a%s_%s_dc%.2f_lr%s_s%d" % (
                    args.dataset, args.alpha, m, dc, lr, s)
                out = os.path.join(OUTDIR, "%s.json" % tag)
                if os.path.exists(out):
                    print("skip (exists) %s" % tag, flush=True)
                    continue
                cfg = dict(dataset=args.dataset, arch="cnn", skew="dirichlet",
                           alpha=float(args.alpha), n_clients=10,
                           rounds=args.rounds, local_epochs=1, lr=lr,
                           lr_decay=dc, batch_size=64, n_train=10000,
                           n_test=2000, seed=s, method=m, _hp="lr=%s" % lr,
                           tag=tag)
                print("[stageB] %s" % tag, flush=True)
                res = run_one(cfg)
                with open(out, "w", encoding="utf-8") as f:
                    json.dump(res, f, indent=1)
    with open(os.path.join(OUTDIR, "_decayretune_used.json"), "w",
              encoding="utf-8") as f:
        json.dump({k: v["best"] for k, v in tuning.items()}, f, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="mnist")
    ap.add_argument("--alpha", default="0.1")
    ap.add_argument("--seeds", type=lambda x: [int(v) for v in x.split(",")],
                    default=[0, 1, 2, 3, 4, 5])
    ap.add_argument("--tune-rounds", type=int, default=40)
    ap.add_argument("--rounds", type=int, default=60)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--skip-tune", action="store_true")
    args = ap.parse_args()

    os.makedirs(OUTDIR, exist_ok=True)
    path = os.path.join(OUTDIR, "_decayretune_tuning.json")
    if args.skip_tune and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            tuning = json.load(f)
    else:
        tuning = tune(args)
    stage_b(args, tuning)
    print("done -> %s" % OUTDIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
