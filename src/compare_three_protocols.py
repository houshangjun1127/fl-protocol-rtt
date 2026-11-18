#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""Compare three Stage A protocols on MNIST alpha=0.1.

  P0  "as published"  -- fedavgm beta=0.5, fedproxw rho=0.5, fedadam lr_s=0.01,
                         feddyn alpha=0.3. Three of these are the resume-bug
                         artifacts diagnosed by audit_stageA_resume_bug.py.
  P1  "rule, test"    -- the documented Stage A rule (v2: stable-first, then
                         late_acc) applied to the full grid on the TEST metric:
                         0.7 / 0.2 / 0.03 / 0.3. This is what Stage A should
                         have handed to Stage B.
  P2  "rule, val"     -- the same rule on a disjoint VALIDATION split:
                         0.9 / 0.5 / 0.03 / 0.1.

P1 and P2 differ from P0 only in the method hyperparameter: same seeds, same
10k/2k split, same lr, same decay, same code. Any difference below is therefore
attributable to the hyper-parameter selection, nothing else.

Trace sources
-------------
  results/rank_inv/     P0, and the four methods whose HP is unchanged in P1/P2
  results/stageAfix/    fedavgm 0.7, fedproxw 0.2, fedadam 0.03
  results/valretune/    fedavgm 0.9, fedproxw 0.5, feddyn 0.1

fedadam is 0.03 in BOTH P1 and P2 (test and val agree), so the stageAfix
fedadam traces serve both -- results/valretune/ has no fedadam run by
construction, and borrowing published fedadam 0.01 for P2 would be wrong.
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
METHODS = ["fedavg", "fedavgm", "fedadam", "fedproxw", "feddyn",
           "scaffold", "uniform"]
TGRID = [round(0.30 + 0.01 * i, 2) for i in range(61)]
INF = float("inf")

MAIN = os.path.join(ROOT, "results", "rank_inv")
FIX = os.path.join(ROOT, "results", "stageAfix")
VAL = os.path.join(ROOT, "results", "valretune")

# method -> {protocol: hp label fragment as it appears in the filename}
OVERLAY = {
    "fedavgm":  {"P1": ("stageAfix",  "beta=0.7,lr_s=1.0"),
                 "P2": ("valretune",  "beta=0.9,lr_s=1.0")},
    "fedproxw": {"P1": ("stageAfix",  "rho=0.2"),
                 "P2": ("valretune",  "rho=0.5")},
    "fedadam":  {"P1": ("stageAfix",  "lr_s=0.03,tau=0.001"),
                 "P2": ("stageAfix",  "lr_s=0.03,tau=0.001")},
    "feddyn":   {"P2": ("valretune",  "fdyn_alpha=0.1")},
}


def load(d, m, s, prefix="", hp=None):
    if hp:
        pat = os.path.join(d, "%s%s_a%s_%s_%s_s%d.json" % (prefix, DS, ALPHA, m, hp, s))
    else:
        pat = os.path.join(d, "%s%s_a%s_%s_*_s%d.json" % (prefix, DS, ALPHA, m, s))
    hits = sorted(glob.glob(pat), key=len)
    if not hits:
        return None
    with open(hits[0], encoding="utf-8") as f:
        return json.load(f)


def acc(r):
    return [float(x["acc"]) for x in sorted(r["trace"], key=lambda z: z["round"])]


def rtt(a, t):
    for i, v in enumerate(a):
        if v >= t:
            return i + 1
    return INF


def tau_b(x, y):
    n = len(x)
    n0 = n * (n - 1) / 2.0
    if n < 2 or n0 == 0:
        return None
    c = d = nx = ny = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx, dy = x[i] - x[j], y[i] - y[j]
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


def build():
    out = {"P0": {}, "P1": {}, "P2": {}}
    for s in SEEDS:
        for m in METHODS:
            base = load(MAIN, m, s)
            if base is None:
                print("MISSING published trace %s s%d" % (m, s))
                return None
            a = acc(base)
            out["P0"][(m, s)] = a
            out["P1"][(m, s)] = a
            out["P2"][(m, s)] = a
            for p, (d, hp) in OVERLAY.get(m, {}).items():
                r = load(os.path.join(ROOT, "results", d), m, s,
                         prefix=(d + "_"), hp=hp)
                if r is None:
                    print("MISSING %s trace %s %s s%d" % (p, d, m, s))
                    return None
                out[p][(m, s)] = acc(r)
    return out


def leaders(P, t, strict=False):
    """method -> mean RTT over the six seeds.

    strict=True drops any method that fails to reach t on every seed, so the
    compared set is identical across protocols. strict=False keeps the
    as-published convention, where a censored seed contributes +inf to the mean.
    """
    res = {}
    for m in METHODS:
        rs = [rtt(P[(m, s)], t) for s in SEEDS]
        if strict and any(v == INF for v in rs):
            continue
        res[m] = sum(rs) / len(rs)
    return res


def crossing(P, a="fedavg", b="feddyn", min_reach=4):
    for t in TGRID:
        ra = [rtt(P[(a, s)], t) for s in SEEDS if rtt(P[(a, s)], t) < INF]
        rb = [rtt(P[(b, s)], t) for s in SEEDS if rtt(P[(b, s)], t) < INF]
        if len(ra) < min_reach or len(rb) < min_reach:
            continue
        if sum(rb) / len(rb) < sum(ra) / len(ra):
            return t
    return None


def main():
    P = build()
    if P is None:
        return 1

    names = ["P0", "P1", "P2"]
    print("three-protocol comparison, %s alpha=%s" % (DS, ALPHA))
    print("  P0 = as published (3 HP are resume-bug artifacts)")
    print("  P1 = documented rule on the test split   (0.7 / 0.2 / 0.03 / 0.3)")
    print("  P2 = documented rule on a held-out val   (0.9 / 0.5 / 0.03 / 0.1)")
    print()

    for strict in (False, True):
        tag = "strict (all 6 seeds must reach)" if strict else \
              "as-published (censored seeds enter the mean as +inf)"
        print("=== leader agreement, %s ===" % tag)
        pairs = [("P0", "P1"), ("P0", "P2"), ("P1", "P2")]
        agree = {p: 0 for p in pairs}
        tot = 0
        tb = {p: [] for p in pairs}
        rows = []
        for t in TGRID:
            L = {n: leaders(P[n], t, strict=strict) for n in names}
            lead = {}
            for n in names:
                if not L[n]:
                    lead[n] = None
                    continue
                lead[n] = min(L[n].items(), key=lambda kv: (kv[1], kv[0]))[0]
            if any(v is None for v in lead.values()):
                continue
            tot += 1
            for p in pairs:
                agree[p] += int(lead[p[0]] == lead[p[1]])
            # tau_b over the vector of mean RTTs, aligned on the shared methods
            for p in pairs:
                shared = sorted(set(L[p[0]]) & set(L[p[1]]))
                if len(shared) < 2:
                    continue
                v = tau_b([L[p[0]][m] for m in shared],
                          [L[p[1]][m] for m in shared])
                if v is not None:
                    tb[p].append(v)
            rows.append((t, lead["P0"], lead["P1"], lead["P2"]))
            if abs(t * 100 - round(t * 100)) < 1e-9 and round(t * 100) % 10 == 0:
                print("  t=%.2f  P0=%-9s P1=%-9s P2=%-9s" %
                      (t, lead["P0"], lead["P1"], lead["P2"]))
        print("  comparable targets: %d" % tot)
        for p in pairs:
            rng = ("%.3f - %.3f" % (min(tb[p]), max(tb[p]))) if tb[p] else "-"
            print("  %s vs %s: leader agrees %d/%d   tau_b %s"
                  % (p[0], p[1], agree[p], tot, rng))
        print()

    print("=== FedAvg-FedDyn crossing (first grid t with mean FedDyn < FedAvg) ===")
    for n in names:
        print("  %s: t=%s" % (n, crossing(P[n])))

    print("\n=== FedAvg vs FedAvgM: mean RTT gap at a few targets ===")
    for t in (0.50, 0.60, 0.67, 0.70, 0.80, 0.90):
        line = "  t=%.2f" % t
        for n in names:
            fa = [rtt(P[n][("fedavg", s)], t) for s in SEEDS]
            fm = [rtt(P[n][("fedavgm", s)], t) for s in SEEDS]
            if any(v == INF for v in fa) or any(v == INF for v in fm):
                line += "   %s=censored" % n
            else:
                line += "   %s: fedavg %.1f  fedavgm %.1f  (%+.1f)" % (
                    n, sum(fa) / 6, sum(fm) / 6, sum(fa) / 6 - sum(fm) / 6)
        print(line)

    with open(os.path.join(ROOT, "results", "stageAfix",
                           "_three_protocol.json"), "w", encoding="utf-8") as f:
        json.dump({"rows": rows}, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
