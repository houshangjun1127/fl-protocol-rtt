#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Validation-split control: compare the published MNIST alpha=0.1 ranking with
the val-retuned one.

The published Stage B used hyperparameters selected on the test split. The
control re-ran Stage A selecting on a disjoint validation split; three of seven
methods
changed their selected setting. This script re-runs the analysis on the
val-retuned traces and reports whether any *conclusion* moves.

WHAT IS COMPARED
----------------
Per seed, per target, the first-passage RTT of all seven methods: four of them
(fedavg, uniform, fedadam, scaffold) are the published traces, because their
selection did not change and re-running them would measure only nondeterminism.
The three whose selection changed (fedavgm, fedproxw, feddyn) are the val-retuned
traces from results/valretune/.

Reported, per target:
  * the first-ranked method under each protocol, and whether they agree;
  * the Kendall tau-b between the two orderings;
  * the FedDyn mean RTT, since FedDyn is the method whose change is largest
    (alpha 0.3 -> 0.1) and it is the method Section 3.1's crossing story is
    about.
Plus the location of the FedAvg-FedDyn crossing under each protocol, because the
abstract quotes it.

Note on what can and cannot be concluded: this is one cell, one seed budget, and
a tuning protocol that still selects on a single split (now a validation split).
It bounds the effect of the selection metric on this cell. It does not say
anything about the other six cells, and it is not a claim that validation-split
selection is the right protocol -- only that the published numbers are not an
artefact of having used the test split for selection. That framing is what goes
into Section 6.

Usage
-----
    python src/compare_valretune.py
"""

from __future__ import annotations

import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MAIN = os.path.join(ROOT, "results", "rank_inv")
VAL = os.path.join(ROOT, "results", "valretune")
DS, ALPHA = "mnist", "0.1"
SEEDS = [0, 1, 2, 3, 4, 5]
METHODS = ["fedavg", "uniform", "fedavgm", "fedproxw", "fedadam", "scaffold",
           "feddyn"]
CHANGED = {"fedavgm", "fedproxw", "feddyn"}
TGRID = [round(0.30 + 0.01 * i, 2) for i in range(61)]
INF = float("inf")


def load(d, m, s, prefix=""):
    pat = os.path.join(d, "%s%s_a%s_%s_*_s%d.json" % (prefix, DS, ALPHA, m, s))
    hits = sorted(glob.glob(pat), key=len)
    if not hits:
        return None
    with open(hits[0], encoding="utf-8") as f:
        return json.load(f)


def acc(r):
    return [float(x["acc"]) for x in sorted(r["trace"],
                                            key=lambda z: z["round"])]


def rtt(a, t):
    for i, v in enumerate(a):
        if v >= t:
            return i + 1
    return INF


def tau_b(x, y):
    """Kendall tau-b between two equal-length vectors, both tie sets handled.

    tau_b = (C - D) / sqrt((n0 - nx)(n0 - ny)), with n0 = n(n-1)/2 and nx/ny
    the number of pairs tied in x / in y. This is the standard definition and
    is used instead of a library call so the diagnostic has no dependency.
    """
    n = len(x)
    n0 = n * (n - 1) / 2.0
    if n < 2 or n0 == 0:
        return None
    c = d = nx = ny = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = x[i] - x[j]
            dy = y[i] - y[j]
            if dx == 0:
                nx += 1
            if dy == 0:
                ny += 1
            if dx == 0 or dy == 0:
                continue
            if (dx > 0) == (dy > 0):
                c += 1
            else:
                d += 1
    den = ((n0 - nx) * (n0 - ny)) ** 0.5
    if den == 0:
        return None
    return (c - d) / den


def crossing(fedavg_accs, feddyn_accs, grid=TGRID):
    """First grid target where mean FedDyn RTT < mean FedAvg RTT."""
    for t in grid:
        fa = [rtt(a, t) for a in fedavg_accs if rtt(a, t) < INF]
        fd = [rtt(a, t) for a in feddyn_accs if rtt(a, t) < INF]
        if len(fa) < 4 or len(fd) < 4:
            continue
        if sum(fd) / len(fd) < sum(fa) / len(fa):
            return t
    return None


def main():
    pub, val = {}, {}
    for s in SEEDS:
        for m in METHODS:
            r = load(MAIN, m, s)
            if r is not None:
                pub[(m, s)] = acc(r)
            rv = load(VAL, m, s, prefix="valretune_") if m in CHANGED else None
            if rv is not None:
                val[(m, s)] = acc(rv)

    missing = [k for k in ((m, s) for m in CHANGED for s in SEEDS)
               if k not in val]
    if missing:
        print("MISSING val-retuned traces: %s" % missing)
        print("run src/run_valretune_stageB.py to completion first")
        return 1

    print("protocol comparison, %s alpha=%s (published vs validation-retuned)"
          % (DS, ALPHA))
    print("%-6s %-22s %-22s %-6s %s" % ("target", "leader(published)",
                                        "leader(val-retuned)", "agree",
                                        "tau_b"))
    agree = tot = 0
    rows = []
    for t in TGRID:
        lp, lv, tp = [], [], []
        for m in METHODS:
            rp = [rtt(pub[(m, s)], t) for s in SEEDS]
            # The four methods whose selection did not change have no
            # val-retuned traces BY CONSTRUCTION: re-running them would measure
            # only nondeterminism. Their val-protocol trace is therefore the
            # published one. Getting this wrong silently drops the method from
            # the val ranking -- the first version of this script did exactly
            # that and reported 28/61 disagreements that do not exist.
            rv = [rtt(val.get((m, s), pub[(m, s)]), t) for s in SEEDS]
            mp = sum(rp) / len(rp) if rp else INF
            mv = sum(rv) / len(rv) if rv else INF
            lp.append((mp, m))
            lv.append((mv, m))
            tp.append((mp, mv))
        lead_p = min(lp)[1]
        lead_v = min(lv)[1]
        tb = tau_b([x[0] for x in lp], [x[0] for x in lv])
        ok = lead_p == lead_v
        tot += 1
        agree += ok
        rows.append((t, lead_p, lead_v, ok, tb))
        if t * 100 % 10 == 0:      # print every 0.10
            print("%-6.2f %-22s %-22s %-6s %s"
                  % (t, lead_p, lead_v, "yes" if ok else "NO",
                     "-" if tb is None else "%.3f" % tb))
    print("\ntargets where the leader agrees: %d / %d" % (agree, tot))

    fa_p = [pub[("fedavg", s)] for s in SEEDS]
    fd_p = [pub[("feddyn", s)] for s in SEEDS]
    # fedavg did not change its selection, so its val-protocol traces ARE the
    # published ones; only feddyn was re-run.
    fa_v = [val.get(("fedavg", s), pub[("fedavg", s)]) for s in SEEDS]
    fd_v = [val[("feddyn", s)] for s in SEEDS]
    cp = crossing(fa_p, fd_p)
    cv = crossing(fa_v, fd_v)
    print("FedAvg-FedDyn crossing: published t=%s  val-retuned t=%s"
          % (cp, cv))

    with open(os.path.join(VAL, "_comparison.json"), "w",
              encoding="utf-8") as f:
        json.dump({"rows": rows, "agree": agree, "n_targets": tot,
                   "crossing_published": cp, "crossing_valretuned": cv},
                  f, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
