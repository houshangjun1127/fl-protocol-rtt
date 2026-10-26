#!/usr/bin/env python
"""Exact sign test over seeds for every rank-inversion claim (task A-3).

WHY THIS EXISTS
---------------
execution_plan_20261011.md section 1.1 argument A: the paper's central claim is
that a ranking inversion is *seed-replicated*. With n=4 seeds, even perfect 4/4
agreement gives a two-sided exact sign test p = 0.125, which cannot clear
alpha = 0.05. With n=6, 6/6 gives p = 0.031. So the number of seeds decides
whether the paper's own headline claim is statistically statable at all.

This script therefore does NOT re-derive what analyse_cell() already reports.
It takes the same inversion definition and asks, for every (cell, method pair,
target pair) that shows an inversion, **on how many of the 6 seeds** it shows
it, and attaches the exact two-sided binomial sign-test p-value.

INVERSION DEFINITION -- copied from analyze_rank_inv.analyse_cell(), NOT
re-invented:
    both RTTs finite at t1 and t2; |rtt_a - rtt_b| >= tau (default 2) at BOTH
    targets; a strictly faster at t1 and strictly slower at t2.

THE TEST
--------
For a claim "this inversion occurs", each seed is a Bernoulli trial. Under
H0 the direction is a coin flip, p = 0.5. Two-sided exact binomial:
    p = 2 * min(P(X >= k), P(X <= k)), clipped to 1.0
with X ~ Binomial(n_seeds, 0.5). Computed with math.comb, never by hand.

NOTE ON WHAT COUNTS AS A CLAIM
------------------------------
A pair is only "seed-replicated" in the strong sense if the SAME (t1, t2)
inversion reproduces on all 6 seeds. A pair that inverts on 3 seeds at one
target pair and 3 different seeds at another is NOT replicated, even though
the pair-level count looks like 6. Both granularities are reported so the
difference cannot be hidden.

USAGE
-----
    python sign_test_seeds.py --dir ../results/rank_inv \
        --out ../results/rank_inv/sign_test_seeds.json
"""
import argparse
import itertools
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_rank_inv import acc_trace, rtt  # reuse, do not redefine


def sign_test_p(k, n):
    """Two-sided exact binomial sign test, p=0.5. Returns (p, tail)."""
    if n == 0:
        return None, None
    tail_hi = sum(math.comb(n, i) for i in range(k, n + 1)) / (2.0 ** n)
    tail_lo = sum(math.comb(n, i) for i in range(0, k + 1)) / (2.0 ** n)
    p = 2.0 * min(tail_hi, tail_lo)
    return min(p, 1.0), ("upper" if tail_hi <= tail_lo else "lower")


def load_stage_b(d):
    """Load Stage B runs only: skip probes, tuned files, reports."""
    out = []
    for f in sorted(os.listdir(d)):
        if not f.endswith(".json"):
            continue
        if "_decay_" in f or "tuned" in f or "report" in f or "sign_test" in f:
            continue
        try:
            with open(os.path.join(d, f), encoding="utf-8") as fh:
                r = json.load(fh)
        except Exception:
            continue
        c = r.get("cfg") if isinstance(r, dict) else None
        if not isinstance(c, dict):
            continue
        if "method" not in c or "seed" not in c:
            continue
        out.append(r)
    return out


def settle_flags(accs, vol_max=0.01, drop_max=5.0):
    """R5-style settledness: last-10 sd below vol_max AND post-peak drop small."""
    tail = accs[-10:] if len(accs) >= 10 else accs
    vol = float(np.std(tail))
    pk = float(accs.max())
    i = int(accs.argmax())
    drop = 100.0 * (pk - float(accs[i:].min()))
    return vol, drop, (vol <= vol_max and drop <= drop_max)


def main():
    ap = argparse.ArgumentParser()
    # Anchored to this file rather than the working directory; see make_ci.py.
    _root = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".."))
    ap.add_argument("--dir", default=os.path.join(_root, "results", "rank_inv"))
    ap.add_argument("--out", default=os.path.join(
        _root, "results", "rank_inv", "sign_test_seeds.json"))
    ap.add_argument("--tau", type=int, default=2)
    ap.add_argument("--target-lo", type=float, default=0.30)
    ap.add_argument("--target-hi", type=float, default=0.95)
    ap.add_argument("--target-step", type=float, default=0.01)
    ap.add_argument("--vol-max", type=float, default=0.01)
    ap.add_argument("--drop-max", type=float, default=5.0)
    args = ap.parse_args()

    n_t = int(round((args.target_hi - args.target_lo) / args.target_step)) + 1
    targets = [round(args.target_lo + i * args.target_step, 4) for i in range(n_t)]

    runs = load_stage_b(args.dir)
    cells = {}
    for r in runs:
        c = r["cfg"]
        cells.setdefault((c["dataset"], c["alpha"]), {}).setdefault(c["seed"], {})[
            c["method"]] = acc_trace(r)

    report = {}
    for (ds, al), by_seed in sorted(cells.items()):
        seeds = sorted(by_seed)
        n = len(seeds)
        methods = sorted(set().union(*[set(v) for v in by_seed.values()]))

        # per (pair, t1, t2): which seeds show the inversion
        support = {}
        for sd in seeds:
            accs = by_seed[sd]
            present = [m for m in methods if m in accs]
            tabs = {}
            for t in targets:
                tabs[t] = {m: rtt(accs[m], t) for m in present}
            settled = {m: settle_flags(accs[m], args.vol_max, args.drop_max)[2]
                       for m in present}
            for a, b in itertools.combinations(present, 2):
                for t1, t2 in itertools.combinations(targets, 2):
                    ra1, rb1 = tabs[t1][a], tabs[t1][b]
                    ra2, rb2 = tabs[t2][a], tabs[t2][b]
                    if None in (ra1, rb1, ra2, rb2):
                        continue
                    if abs(ra1 - rb1) < args.tau or abs(ra2 - rb2) < args.tau:
                        continue
                    if ra1 < rb1 and ra2 > rb2:
                        key = ("%s|%s" % (a, b), round(t1, 4), round(t2, 4))
                        support.setdefault(key, {"seeds": [], "settled": 0})
                        support[key]["seeds"].append(sd)
                        if settled[a] and settled[b]:
                            support[key]["settled"] += 1

        rows = []
        for (pair, t1, t2), v in sorted(support.items()):
            k = len(v["seeds"])
            p, tail = sign_test_p(k, n)
            ks = v["settled"]
            ps, _ = sign_test_p(ks, n)
            rows.append({
                "pair": pair, "t1": t1, "t2": t2,
                "k_seeds": k, "n_seeds": n, "seed_list": v["seeds"],
                "p_two_sided": p, "tail": tail,
                "k_settled": ks, "p_two_sided_settled": ps,
            })

        # pair-level: best (largest k) single crossing, and the union of seeds
        by_pair = {}
        for r in rows:
            d2 = by_pair.setdefault(r["pair"], {"best_k": 0, "best_rows": [],
                                                "union_seeds": set()})
            d2["union_seeds"].update(r["seed_list"])
            if r["k_seeds"] > d2["best_k"]:
                d2["best_k"] = r["k_seeds"]
                d2["best_rows"] = [r]
            elif r["k_seeds"] == d2["best_k"]:
                d2["best_rows"].append(r)
        pair_summary = {}
        for pair, d2 in sorted(by_pair.items()):
            best = d2["best_rows"][0]
            p, _ = sign_test_p(d2["best_k"], n)
            cov = len(d2["union_seeds"])
            pcov, _ = sign_test_p(cov, n)
            pair_summary[pair] = {
                # --- STRICT reading: the SAME (t1,t2) crossing reproduces.
                "best_k": d2["best_k"], "n_seeds": n,
                "best_p_two_sided": p,
                "best_t1_t2": [best["t1"], best["t2"]],
                # --- BROAD reading: the pair inverts on how many seeds AT ALL,
                # wherever the crossing lands. The crossing point itself moves
                # with the seed, so this is the reading that matches the claim
                # "the inversion phenomenon replicates across seeds".
                "seed_coverage": cov,
                "seed_coverage_list": sorted(d2["union_seeds"]),
                "p_coverage_two_sided": pcov,
                "n_crossings_observed": len([r for r in rows if r["pair"] == pair]),
            }

        report["%s|a%s" % (ds, al)] = {
            "n_seeds": n, "seeds": seeds, "methods": methods,
            "n_crossing_points": len(rows),
            "per_crossing": rows,
            "per_pair": pair_summary,
            "n_pairs_full_support": len([1 for v in pair_summary.values()
                                         if v["best_k"] == n]),
            "n_crossings_full_support": len([r for r in rows
                                             if r["k_seeds"] == n]),
        }

    out = {
        "tau": args.tau,
        "targets": "%s..%s step %s" % (args.target_lo, args.target_hi,
                                       args.target_step),
        "vol_max": args.vol_max, "drop_max": args.drop_max,
        "sign_test": "two-sided exact binomial, p=0.5, 2*min(P(X>=k),P(X<=k))",
        "cells": report,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)

    # console summary
    print("exact sign test over %d seeds per cell" %
          (next(iter(report.values()))["n_seeds"] if report else 0))
    print("=" * 78)
    for cell, v in report.items():
        full_pair = v["n_pairs_full_support"]
        full_cross = v["n_crossings_full_support"]
        print("\n%s   seeds=%s  crossings=%d" %
              (cell, v["seeds"], v["n_crossing_points"]))
        print("  STRICT same (t1,t2) 6/6 : pairs=%d crossings=%d" %
              (full_pair, full_cross))
        n_cov = len([1 for ps in v["per_pair"].values()
                     if ps["seed_coverage"] == n])
        print("  BROAD  pair inverts on all %d seeds : %d" % (n, n_cov))
        print("    %-22s %-28s %s" % ("pair", "STRICT best k (same t1,t2)",
                                      "BROAD coverage (any t1,t2)"))
        for pair, ps in sorted(v["per_pair"].items(),
                               key=lambda x: -x[1]["seed_coverage"]):
            flag = "  <-- p<0.05" if ps["p_coverage_two_sided"] is not None \
                and ps["p_coverage_two_sided"] < 0.05 else ""
            print("    %-22s k=%d/%d p=%.4f (t %s->%s)   cov=%d/%d p=%.4f%s" % (
                pair, ps["best_k"], ps["n_seeds"], ps["best_p_two_sided"],
                ps["best_t1_t2"][0], ps["best_t1_t2"][1],
                ps["seed_coverage"], ps["n_seeds"],
                ps["p_coverage_two_sided"], flag))
    print("\n-> %s" % args.out)


if __name__ == "__main__":
    main()
