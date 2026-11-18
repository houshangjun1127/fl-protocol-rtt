#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""Decay-retune control: does the Section 3.2 decay effect survive per-decay
learning-rate retuning?

The published decay probe holds every hyperparameter fixed -- including the
global learning rate 0.05 inherited from Stage A -- and varies only `lr_decay`.
That is the right design for isolating the knob, but it means a method observed
at an unfavourable decay may simply be at a bad learning rate for that schedule.
This is the control: retune lr per (method, decay) and re-measure.

  published:  lr = 0.05 for both methods at every decay
  retuned:    lr = argmax over {0.025, 0.05, 0.1} of the Stage A rule
              (stable-first, then late accuracy at 85% of a 40-round budget),
              fitted separately at each decay, at seed 0

Metric is the paper's: **late accuracy** = mean test accuracy over the final ten
rounds. Scope is MNIST alpha=0.1, SCAFFOLD and FedAvg, decay in {0.90, 1.00}
-- the two endpoints of the published sweep. The published headline decay
number in the paper is Table 3 (CIFAR-10); this control does NOT cover it, and
the write-up must say so.
"""

from __future__ import annotations

import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

DS, ALPHA = "mnist", "0.1"
SEEDS = [0, 1, 2, 3, 4, 5]
DECAYS = ["0.90", "1.00"]
METHODS = ["fedavg", "scaffold"]

RETUNE = os.path.join(ROOT, "results", "decayretune")
PUB = os.path.join(ROOT, "results", "rank_inv")


def late_from_trace(r):
    a = [float(x["acc"]) for x in sorted(r["trace"], key=lambda z: z["round"])]
    return sum(a[-10:]) / len(a[-10:])


def load_retuned(m, dc, s):
    # method is part of the tag: the first attempt omitted it and scaffold /
    # fedavg collided at decay 0.90 (both selected lr=0.1)
    pat = os.path.join(RETUNE, "decayretune_%s_a%s_%s_dc%s_lr*_s%d.json"
                       % (DS, ALPHA, m, dc, s))
    hits = sorted(glob.glob(pat))
    if not hits:
        return None
    with open(hits[0], encoding="utf-8") as f:
        d = json.load(f)
    assert d["cfg"]["method"] == m, (hits[0], d["cfg"]["method"])
    assert abs(d["cfg"]["lr_decay"] - float(dc)) < 1e-9, (hits[0], dc)
    assert d["cfg"]["seed"] == s, (hits[0], s)
    return late_from_trace(d)


def load_pub(m, dc, s):
    """Published probe stores only summary stats, not traces."""
    p = os.path.join(PUB, "_decay_%s_s%d.json" % (DS, s))
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding="utf-8"))
    # the published probe files key decays as "0.9"/"0.95"/"0.98"/"1.0"
    f = float(dc)
    for k in d[m]:
        if abs(float(k) - f) < 1e-9:
            return d[m][k]["late"]
    raise KeyError("no decay %s in %s" % (dc, p))


def main():
    used = json.load(open(os.path.join(RETUNE, "_decayretune_used.json"),
                          encoding="utf-8"))
    print("per-decay retuned learning rates (Stage A rule, seed 0, 40 rounds):")
    for k in sorted(used):
        print("  %-20s lr=%s   late=%.4f  stable=%s"
              % (k, used[k]["lr"], used[k]["late_acc"], used[k]["stable"]))
    print()

    pub = {(m, dc, s): load_pub(m, dc, s)
           for m in METHODS for dc in DECAYS for s in SEEDS}
    ret = {(m, dc, s): load_retuned(m, dc, s)
           for m in METHODS for dc in DECAYS for s in SEEDS}

    miss = [k for k, v in ret.items() if v is None]
    if miss:
        print("MISSING %d retuned traces: %s" % (len(miss), miss[:6]))
        print("run src/decay_retune.py to completion first")
        return 1

    print("late accuracy (mean of final ten rounds), percent")
    print("%-6s | %-22s | %-22s" % ("seed", "PUBLISHED lr=0.05", "RETUNED per decay"))
    print("%-6s | %-10s %-10s | %-10s %-10s" %
          ("", "d0.90", "d1.00", "d0.90", "d1.00"))
    for s in SEEDS:
        print("%-6d | %-10.2f %-10.2f | %-10.2f %-10.2f" % (
            s,
            pub[("scaffold", "0.90", s)] * 100,
            pub[("scaffold", "1.00", s)] * 100,
            ret[("scaffold", "0.90", s)] * 100,
            ret[("scaffold", "1.00", s)] * 100))
        print("%-6s | %-10.2f %-10.2f | %-10.2f %-10.2f" % (
            "  fedavg",
            pub[("fedavg", "0.90", s)] * 100,
            pub[("fedavg", "1.00", s)] * 100,
            ret[("fedavg", "0.90", s)] * 100,
            ret[("fedavg", "1.00", s)] * 100))
    print()

    def gap(P, dc, s):
        return (P[("fedavg", dc, s)] - P[("scaffold", dc, s)]) * 100

    print("FedAvg minus SCAFFOLD late gap, points")
    print("%-6s | %-10s %-10s | %-10s %-10s" %
          ("seed", "PUB 0.90", "PUB 1.00", "RET 0.90", "RET 1.00"))
    g = {}
    for s in SEEDS:
        g[("pub", "0.90", s)] = gap(pub, "0.90", s)
        g[("pub", "1.00", s)] = gap(pub, "1.00", s)
        g[("ret", "0.90", s)] = gap(ret, "0.90", s)
        g[("ret", "1.00", s)] = gap(ret, "1.00", s)
        print("%-6d | %-10.2f %-10.2f | %-10.2f %-10.2f" % (
            s, g[("pub", "0.90", s)], g[("pub", "1.00", s)],
            g[("ret", "0.90", s)], g[("ret", "1.00", s)]))

    def mv(tag, dc):
        return sum(g[(tag, dc, s)] for s in SEEDS) / len(SEEDS)

    print("\nmean gap  0.90 -> 1.00")
    for tag, name in (("pub", "published lr=0.05"), ("ret", "retuned per decay")):
        a, b = mv(tag, "0.90"), mv(tag, "1.00")
        print("  %-22s %+7.2f -> %+7.2f   absolute change %+.2f" % (name, a, b, b - a))

    for tag, name in (("pub", "published"), ("ret", "retuned")):
        flips = sum(1 for s in SEEDS
                    if g[(tag, "0.90", s)] * g[(tag, "1.00", s)] < 0)
        lead9 = sum(1 for s in SEEDS if g[(tag, "0.90", s)] < 0)
        lead1 = sum(1 for s in SEEDS if g[(tag, "1.00", s)] > 0)
        print("  %-10s leader flips 0.90->1.00: %d/6   "
              "(SCAFFOLD leads at 0.90 on %d/6, FedAvg leads at 1.00 on %d/6)"
              % (name, flips, lead9, lead1))

    print("\nSCAFFOLD late accuracy at decay 1.00 (the collapse):")
    for tag, P, name in (("pub", pub, "published lr=0.05"),
                         ("ret", ret, "retuned lr=0.025")):
        v = [P[("scaffold", "1.00", s)] * 100 for s in SEEDS]
        print("  %-22s %.2f - %.2f  (mean %.2f)" % (name, min(v), max(v),
                                                    sum(v) / len(v)))

    out = {
        "retuned_lr": {k: v["lr"] for k, v in used.items()},
        "published_gap_mean": {"0.90": mv("pub", "0.90"),
                               "1.00": mv("pub", "1.00")},
        "retuned_gap_mean": {"0.90": mv("ret", "0.90"),
                             "1.00": mv("ret", "1.00")},
        "per_seed": {"%s|%s|%d" % k: v for k, v in g.items()},
    }
    with open(os.path.join(RETUNE, "_comparison.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
