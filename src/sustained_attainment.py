#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Sustained attainment, as a fourth decision statistic.

WHY THIS SCRIPT EXISTS
----------------------
Section 3.3 compares three decision statistics for "reached the target" --
first passage, 5-round trailing mean, 10-round trailing mean -- and reports that
they disagree about the winner on 17.0% of comparable units. All three are
still *first-crossing* rules: each returns the first round at which some
smoothed series touches the target, so all three can be satisfied by a
transient spike. The paper's oscillation argument therefore calls for a
statistic that cannot be satisfied by a spike.

This adds one: SUSTAINED attainment.

DEFINITION
----------
  sust_k(t) = min { r : acc[r] >= t for every round r, r+1, ..., r+k-1 }

i.e. the first round of a k-consecutive run at or above t. We use k = 5. It is
censored (INF) if no such run fits inside the 60-round budget, so the largest
value it can take is 60 - k + 1 = 56.

Two properties worth stating because they are the whole point:
  * sust_k(t) >= first(t) always. The gap is the "spike premium": how much later
    a method *holds* the target than it *touches* it.
  * sust_k can be censored where first passage is not. That is exactly the case
    the oscillation argument is about -- a method that touches t once on an
    upward swing and never holds it -- and this script counts it.

CONSISTENCY CHECK
-----------------
The script recomputes the first/ma5, first/ma10 and ma5/ma10 winner-flip counts
with the published definitions (src/rtt_statistic_compare.py, tau = 2) and
prints them against the numbers in the paper. If they drift, the new statistic
is being compared against a different baseline and nothing here can be quoted.

No model is trained; everything is recomputed from the released traces.

Usage
-----
    python src/sustained_attainment.py
    python src/sustained_attainment.py --out results/rank_inv/_sustained.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from itertools import combinations

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from rtt_statistic_compare import (  # noqa: E402
    ALPHAS, DATASETS, METHODS, SEEDS, STATS, STAT_LABEL, TGRID, WIN,
    load_trace, smooth,
)

INF = float("inf")
K = 5
SUST = "sust%d" % K
ALL_STATS = STATS + [SUST]
LABEL = dict(STAT_LABEL)
LABEL[SUST] = "sustained-%d" % K
TAU = 2


def sustained(acc, t, k=K):
    """First round starting a k-consecutive run at or above t, else INF."""
    n = len(acc) - 1                      # acc is 1-based
    run = 0
    for r in range(1, n + 1):
        v = acc[r]
        if v is not None and v >= t:
            run += 1
            if run >= k:
                return r - k + 1
        else:
            run = 0
    return INF


def build():
    """(ds, alpha, seed) -> method -> {stat: {t: rtt}}"""
    data = defaultdict(lambda: defaultdict(dict))
    for ds in DATASETS:
        for a in ALPHAS[ds]:
            for m in METHODS:
                for s in SEEDS:
                    got = load_trace(ds, a, m, s)
                    if got is None:
                        continue
                    acc = got[0]
                    tbl = {}
                    for st_ in STATS:
                        ser = acc if st_ == "first" else smooth(acc, WIN[st_])
                        row = {}
                        for t in TGRID:
                            hit = INF
                            for r in range(1, len(ser)):
                                v = ser[r]
                                if v is not None and v >= t:
                                    hit = r
                                    break
                            row[t] = hit
                        tbl[st_] = row
                    tbl[SUST] = {t: sustained(acc, t) for t in TGRID}
                    data[(ds, a, s)][m] = tbl
    return data


def flips(data, s1, s2):
    """Winner-flip rate between two statistics, published definitions, tau=2."""
    tot = winflip = pair_tot = pair_flip = 0
    per_cell = {}
    for (ds, a) in [(d, x) for d in DATASETS for x in ALPHAS[d]]:
        seeds = [s for s in SEEDS if (ds, a, s) in data]
        c_u = c_w = c_p = c_pf = 0
        for seed in seeds:
            for t in TGRID:
                r1 = {m: data[(ds, a, seed)][m][s1][t] for m in METHODS}
                r2 = {m: data[(ds, a, seed)][m][s2][t] for m in METHODS}
                common = [m for m in METHODS if r1[m] < INF and r2[m] < INF]
                if len(common) < 2:
                    continue
                c_u += 1
                o1 = sorted(common, key=lambda m: (r1[m], m))
                o2 = sorted(common, key=lambda m: (r2[m], m))
                if o1[0] != o2[0]:
                    c_w += 1
                for x, y in combinations(common, 2):
                    d1, d2 = r1[x] - r1[y], r2[x] - r2[y]
                    if abs(d1) < TAU or abs(d2) < TAU:
                        continue
                    c_p += 1
                    if (d1 > 0) != (d2 > 0):
                        c_pf += 1
        per_cell[f"{ds}|a{a}"] = {"units": c_u, "winner_flips": c_w,
                                  "rate": round(c_w / c_u, 4) if c_u else None,
                                  "pairs": c_p, "pair_flips": c_pf}
        tot += c_u
        winflip += c_w
        pair_tot += c_p
        pair_flip += c_pf
    return {"units": tot, "winner_flips": winflip,
            "rate": round(winflip / tot, 4) if tot else None,
            "pairs": pair_tot, "pair_flips": pair_flip,
            "pair_rate": round(pair_flip / pair_tot, 4) if pair_tot else None,
            "per_cell": per_cell}


def spike_premium(data):
    """(cell, method): sust_k minus first, and the touch-but-never-hold rate."""
    out = {}
    for (ds, a) in [(d, x) for d in DATASETS for x in ALPHAS[d]]:
        seeds = [s for s in SEEDS if (ds, a, s) in data]
        ent = {}
        for m in METHODS:
            gaps, touch_only, both, censored_both = [], 0, 0, 0
            for s in seeds:
                for t in TGRID:
                    v1 = data[(ds, a, s)][m]["first"][t]
                    vk = data[(ds, a, s)][m][SUST][t]
                    if v1 < INF and vk < INF:
                        gaps.append(vk - v1)
                        both += 1
                    elif v1 < INF and vk == INF:
                        touch_only += 1          # touched t, never held it k rounds
                    elif v1 == INF:
                        censored_both += 1
            ent[m] = {
                "n_both": both,
                "n_touch_only": touch_only,
                "touch_only_rate": (round(touch_only / float(both + touch_only), 4)
                                    if (both + touch_only) else None),
                "gap_median": (sorted(gaps)[len(gaps) // 2] if gaps else None),
                "gap_mean": (round(sum(gaps) / float(len(gaps)), 2) if gaps
                             else None),
                "gap_max": (max(gaps) if gaps else None),
            }
        out[f"{ds}|a{a}"] = ent
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(
        HERE, "..", "results", "rank_inv", "_sustained.json"))
    args = ap.parse_args()

    data = build()
    res = {"conventions": {
        "definition": "sust_%d(t) = first round of a %d-consecutive run with "
                      "acc >= t" % (K, K),
        "max_value": 60 - K + 1,
        "tau_rounds": TAU,
        "censoring": "INF (no imputation), same as every other statistic",
    }, "n_traces": sum(len(v) for v in data.values())}

    res["flips"] = {}
    print("winner-flip rate between statistic pairs (tau = 2)")
    print("%-22s %8s %8s %8s" % ("pair", "units", "flips", "rate"))
    for s1, s2 in combinations(ALL_STATS, 2):
        f = flips(data, s1, s2)
        res["flips"][f"{s1}_vs_{s2}"] = f
        print("%-22s %8d %8d %8.3f" % (
            "%s vs %s" % (LABEL[s1], LABEL[s2]), f["units"],
            f["winner_flips"], f["rate"] or 0), flush=True)

    res["spike_premium"] = spike_premium(data)
    print("\ntouch-but-never-hold rate (first passage reached, sust_%d did not)" % K)
    for cell, ent in res["spike_premium"].items():
        vals = [(m, e["touch_only_rate"]) for m, e in ent.items()
                if e["touch_only_rate"] is not None]
        if not vals:
            continue
        hi = max(vals, key=lambda z: z[1])
        print("  %-14s worst: %-9s %.3f   median gap (rounds) %s" % (
            cell, hi[0], hi[1],
            ", ".join("%s=%s" % (m, e["gap_median"])
                      for m, e in sorted(ent.items()))))

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print("\nwrote", args.out)

    # consistency check against the published numbers
    print("\nconsistency with published Section 3.3 counts:")
    for key, expect in (("first_vs_ma5", 366), ("first_vs_ma10", 423),
                        ("ma5_vs_ma10", 203)):
        got = res["flips"][key]["winner_flips"]
        print("  %-16s published=%d  recomputed=%d  %s"
              % (key, expect, got, "OK" if got == expect else "MISMATCH"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
