"""Quantify tie prevalence in the per-seed rankings behind the reported Kendall tau,
and recompute tau under tau-a (no tie correction) vs tau-b (tie-corrected).

Context: analyze_rank_inv.py::rank_at sorts achieving methods by RTT and failing
methods by -final accuracy, using Python's stable sort. Two methods with the
SAME first-passage round therefore receive DIFFERENT ranks (order = dict load
order), i.e. ties are broken arbitrarily rather than handled as ties.
kendall_tau() then computes (conc-disc)/(conc+disc), which is tau-a.

This script recomputes, for every cell/seed:
  - n_tied_pairs at the low target and the high target (equal RTT among
    achieving methods)
  - tau-a as currently implemented (arbitrary tie-breaking)
  - tau-b on the *proper* tied ranking (ties shared rank, tau-b denominator)

Usage:  python src/check_tau_variant.py
"""
from __future__ import annotations

import glob
import itertools
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TRACES = ROOT / "results" / "rank_inv"

CELLS = [
    "mnist|a0.05", "mnist|a0.1", "mnist|a0.3",
    "fashion|a0.05", "fashion|a0.1", "fashion|a0.3",
    "cifar10|a0.1",
]
T0, T1GRID = 0.30, 0.95


def load_cell(cell: str):
    """cell -> {method: [per-seed acc list]}"""
    ds, a = cell.split("|")
    out: dict[str, list] = {}
    for p in sorted(glob.glob(str(TRACES / f"{ds}_{a}_*_s*.json"))):
        base = os.path.basename(p)
        if "decay" in base or "probe" in base or "momentum" in base:
            continue
        # method is the middle token(s)
        core = base[len(f"{ds}_{a}_"):]
        method = core.rsplit("_s", 1)[0]
        seed = int(core.rsplit("_s", 1)[1].split(".")[0])
        d = json.load(open(p))
        acc = [r["acc"] for r in d["trace"]]
        out.setdefault(method, {})[seed] = acc
    return out


def rtt(accs, target):
    hit = np.nonzero(np.asarray(accs) >= target)[0]
    return int(hit[0]) + 1 if len(hit) else None


def ranking(accs_by_method, target):
    """Return (order_list, rtt_map). Stable sort by RTT then -final."""
    tab = {m: (rtt(a, target), float(a[-1])) for m, a in accs_by_method.items()}
    ach = sorted([m for m in tab if tab[m][0] is not None], key=lambda m: tab[m][0])
    fail = sorted([m for m in tab if tab[m][0] is None], key=lambda m: -tab[m][1])
    return ach + fail, tab


def tied_groups(order, rtt_map):
    """Among methods that ACHIEVED the target, group by equal RTT."""
    g: dict[int, list[str]] = {}
    for m in order:
        v = rtt_map[m][0]
        if v is not None:
            g.setdefault(v, []).append(m)
    return [v for v in g.values() if len(v) > 1]


def tau_a(order_a, order_b):
    ia = {m: i for i, m in enumerate(order_a)}
    ib = {m: i for i, m in enumerate(order_b)}
    common = [m for m in order_a if m in order_b]
    if len(common) < 2:
        return None
    conc = disc = 0
    for x, y in itertools.combinations(common, 2):
        s = np.sign(ia[x] - ia[y]) * np.sign(ib[x] - ib[y])
        if s > 0:
            conc += 1
        elif s < 0:
            disc += 1
    return (conc - disc) / (conc + disc)


def tau_b(order_a, order_b):
    """tau-b with explicit tie handling: build rank vectors with shared ranks."""
    common = [m for m in order_a if m in order_b]
    if len(common) < 2:
        return None

    def ranks(order):
        # assign 0..n-1 but collapse explicit ties flagged by caller
        return {m: i for i, m in enumerate(order)}

    return tau_from_rankvecs(ranks(order_a), ranks(order_b), common, {})


def tau_from_rankvecs(ra, rb, common, tie_map):
    """Generic Kendall with tie correction.

    tie_map: dict (target_side, method) -> group id, or {}. If a pair of methods
    shares a group id on a side, that pair is a tie on that side.
    """
    n = len(common)
    n0 = n * (n - 1) // 2
    conc = disc = 0
    ta = tb = 0
    for x, y in itertools.combinations(common, 2):
        sx = np.sign(ra[x] - ra[y])
        sy = np.sign(rb[x] - rb[y])
        # tie overrides
        if ("a", x) in tie_map and tie_map[("a", x)] == tie_map.get(("a", y)):
            sx = 0
        if ("b", x) in tie_map and tie_map[("b", x)] == tie_map.get(("b", y)):
            sy = 0
        if sx == 0 and sy == 0:
            continue
        if sx == 0:
            ta += 1
            continue
        if sy == 0:
            tb += 1
            continue
        if sx * sy > 0:
            conc += 1
        else:
            disc += 1
    denom = np.sqrt((n0 - ta) * (n0 - tb))
    return None if denom == 0 else (conc - disc) / denom


def main() -> int:
    rows = []
    for cell in CELLS:
        bym = load_cell(cell)
        if not bym:
            print(f"!! no traces for {cell}")
            continue
        seeds = sorted({s for d in bym.values() for s in d})
        for sd in seeds:
            accs = {m: d[sd] for m, d in bym.items() if sd in d}
            if len(accs) < 2:
                continue
            oa, taba = ranking(accs, T0)
            ob, tabb = ranking(accs, T1GRID)
            ga = tied_groups(oa, taba)
            gb = tied_groups(ob, tabb)
            # tie map keyed by RTT value per side
            tm = {}
            for g in ga:
                for m in g:
                    tm[("a", m)] = ("a", taba[m][0])
            for g in gb:
                for m in g:
                    tm[("b", m)] = ("b", tabb[m][0])
            ra = {m: i for i, m in enumerate(oa)}
            rb = {m: i for i, m in enumerate(ob)}
            common = [m for m in oa if m in ob]
            a = tau_a(oa, ob)
            b = tau_from_rankvecs(ra, rb, common, tm)
            rows.append({
                "cell": cell, "seed": sd,
                "ties_low": sum(len(g) - 1 for g in ga),
                "ties_high": sum(len(g) - 1 for g in gb),
                "tau_a": None if a is None else round(float(a), 3),
                "tau_b": None if b is None else round(float(b), 3),
            })

    print(f"{'cell':<14}{'seed':<5}{'ties@0.30':>10}{'ties@0.95':>10}"
          f"{'tau_a':>9}{'tau_b':>9}{'diff':>8}")
    for r in rows:
        d = "" if (r["tau_a"] is None or r["tau_b"] is None) else f"{r['tau_a']-r['tau_b']:+.3f}"
        print(f"{r['cell']:<14}{r['seed']:<5}{r['ties_low']:>10}{r['ties_high']:>10}"
              f"{str(r['tau_a']):>9}{str(r['tau_b']):>9}{d:>8}")

    a_vals = [r["tau_a"] for r in rows if r["tau_a"] is not None]
    b_vals = [r["tau_b"] for r in rows if r["tau_b"] is not None]
    print(f"\ntau_a range [{min(a_vals):.2f}, {max(a_vals):.2f}]  n={len(a_vals)}")
    print(f"tau_b range [{min(b_vals):.2f}, {max(b_vals):.2f}]  n={len(b_vals)}")
    print(f"max |tau_a - tau_b| = {max(abs(x-y) for x,y in zip(a_vals,b_vals)):.3f}")
    print(f"total tied pairs @0.30 = {sum(r['ties_low'] for r in rows)}, "
          f"@0.95 = {sum(r['ties_high'] for r in rows)}")

    out = ROOT / "results" / "rank_inv" / "_tau_variant_check.json"
    out.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
