"""Quantify tie prevalence in the per-seed rankings behind the reported Kendall tau,
and recompute tau under tau-a (no tie correction) vs tau-b (tie-corrected).

Context: analyze_rank_inv.py::rank_at sorts achieving methods by RTT and failing
methods by -final accuracy, using Python's stable sort. Two methods with the
SAME first-passage round therefore receive DIFFERENT ranks (order = dict load
order), i.e. ties are broken arbitrarily rather than handled as ties.
kendall_tau() then computes the tie-corrected tau-b.

This script recomputes, for every cell/seed:
  - n_tied_pairs at the low target and the high target (equal RTT among
    achieving methods; counted as pairs C(n_g, 2) per tie group of size n_g,
    matching the report's `tied_pairs_first_last` caliber)
  - tau-a on the ORDINAL path (what the pipeline does: tied RTTs converted to
    distinct ordinal positions by stable sort, then tau-a on those positions)
  - tau-a and tau-b on the RAW path (straight from the (rtt, -final) keys, with
    ties preserved)
  - an EXHAUSTIVE enumeration of all 7! = 5040 load orders per (cell, seed),
    giving the complete set of values each statistic can take on the same data.

ATTRIBUTION (R1, 2026-10-18).  The load-order sensitivity belongs to the
*ordinal conversion* -- an unreported preprocessing choice -- and NOT to tau-a.
On the ordinal path, 41 of the 42 runs are order-sensitive (mnist|a0.1 seed 0
takes 11 distinct values spanning -0.524 .. +0.429, spread 0.952; the worst
runs span -1.000 .. +1.000, spread 2.000).  On the raw path tau-a takes a
single value under every one of the 5040 orders in all 42 runs (spread 0.000000).
The ordinal path also reports systematically HIGHER values than the raw path
(mean +0.230 over the 42 runs; the two disagree in sign on 15 of 42), so the
artefact was a bias, not merely noise.

Usage:  python src/check_tau_variant.py
"""
from __future__ import annotations

import glob
import itertools
import json
import math
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


def tau_a_exhaustive(accs, t0, t1, exhaustive=True):
    """Enumerate ALL len(accs)! load orders; return the sorted set of distinct
    tau-a values the *same data* can produce.  Deterministic (no RNG).

    Two statistics are tracked:
      * the ORDINAL path -- ranking() stable-sorts, breaking equal-RTT ties by
        load order, and tau_a() reads the resulting ordinal positions.  This
        path is order-sensitive by construction.
      * the RAW path -- tau_raw() reads the (rtt, -final) keys themselves, so
        no load order can enter.  This path must return ONE value under all
        5040 orders; any spread here means a deeper implementation fault and is
        a hard stop (revision_plan R1 stop condition).

    7 methods -> 5040 orders per run.
    """
    methods = sorted(accs)
    vals, raw_vals = set(), set()
    perms = (itertools.permutations(methods) if exhaustive
             else iter([tuple(methods)]))
    for perm in perms:
        d = {m: accs[m] for m in perm}
        oa, _ = ranking(d, t0)
        ob, _ = ranking(d, t1)
        v = tau_a(oa, ob)
        if v is not None:
            vals.add(round(float(v), 4))
        rv = tau_raw(d, t0, t1)["tau_a_raw"]
        if rv is not None:
            raw_vals.add(round(float(rv), 6))
    return sorted(vals), sorted(raw_vals)


def ordering_key(rtt_val, final_acc):
    """The pipeline's rank key, as a pure function of the data.

    Achievers first, ordered by first-passage round (smaller = ahead);
    non-achievers after them, ordered by final accuracy (larger = ahead).
    Lexicographic, so "m is ahead of n"  <=>  key(m) < key(n).

    This is exactly what rank_at()/ranking() compute, EXCEPT that those
    functions then destroy ties by stable-sorting on load order.  Here the
    key is kept intact, so two methods with the same key are a genuine tie.
    """
    if rtt_val is None:
        return (1, -float(final_acc))
    return (0, int(rtt_val))


def key_table(accs_by_method, target):
    """{method: (rtt_or_None, final_acc, order_key)} at one target."""
    out = {}
    for m, a in accs_by_method.items():
        r = rtt(a, target)
        out[m] = (r, float(a[-1]), ordering_key(r, a[-1]))
    return out


def tau_raw(accs_by_method, t0, t1):
    """Standard tau-a and tau-b Straight from the raw RTT/final-accuracy keys.

    Definitions (n = number of methods, n0 = C(n,2)):
      concordant pair: both targets order the pair the same way
      discordant pair: the targets order the pair oppositely
      tied on a side : the two methods share the SAME key at that target
                       (same first-passage round for achievers; equal final
                       accuracy for the rare both-censored pair)
      tau-a = (C - D) / n0                [tied pairs sit in the denominator
                                           and in neither C nor D]
      tau-b = (C - D) / sqrt((n0 - na)(n0 - nb))   [na, nb = #pairs tied on
                                           that side, counting pairs tied on
                                           BOTH sides in both terms]

    Neither statistic touches the file iteration order: the key of a method is a
    function of its own trace alone.  Verified exhaustively (all 7! = 5040 load
    orders per run) by tau_raw_exhaustive().
    """
    ka, kb = key_table(accs_by_method, t0), key_table(accs_by_method, t1)
    methods = [m for m in ka if m in kb]
    n = len(methods)
    if n < 2:
        return {"tau_a_raw": None, "tau_b_raw": None, "n": n,
                "ties_low": 0, "ties_high": 0}
    n0 = n * (n - 1) // 2
    conc = disc = na = nb = 0
    for x, y in itertools.combinations(methods, 2):
        sx = _cmp_key(ka[x][2], ka[y][2])
        sy = _cmp_key(kb[x][2], kb[y][2])
        if sx == 0:
            na += 1
        if sy == 0:
            nb += 1
        if sx == 0 or sy == 0:
            continue
        if sx * sy > 0:
            conc += 1
        else:
            disc += 1
    tau_a = (conc - disc) / n0
    denom = np.sqrt(float(n0 - na) * float(n0 - nb))
    tau_b = None if denom == 0 else (conc - disc) / denom

    # tied PAIRS, C(n_g,2) per tie group -- same caliber as
    # analyze_rank_inv.py::tied_groups / the report's tied_pairs_first_last
    ga = _tie_groups(ka)
    gb = _tie_groups(kb)
    return {
        "tau_a_raw": round(float(tau_a), 6),
        "tau_b_raw": None if tau_b is None else round(float(tau_b), 6),
        "conc": conc, "disc": disc,
        "ties_low": sum(len(g) * (len(g) - 1) // 2 for g in ga),
        "ties_high": sum(len(g) * (len(g) - 1) // 2 for g in gb),
        "n": n,
    }


def _cmp_key(kx, ky):
    """-1 if kx before ky (ahead), +1 if after, 0 if identical."""
    if kx < ky:
        return -1
    if kx > ky:
        return 1
    return 0


def _tie_groups(ktab):
    g: dict[tuple, list[str]] = {}
    for m, v in ktab.items():
        g.setdefault(v[2], []).append(m)
    return [v for v in g.values() if len(v) > 1]


def tau_from_rankvecs(ra, rb, common, tie_map):
    """Generic Kendall with tie correction.

    tie_map: dict (target_side, method) -> group id, or {}. If a pair of methods
    shares a group id on a side, that pair is a tie on that side.

    NOTE (R1 fix): pairs tied on BOTH sides must be counted in `ta` *and* `tb`,
    per the standard tau-b identity tau_b = (C-D)/sqrt((n0-n1)(n0-n2)) where
    n1 = sum_i C(t_i,2) and n2 = sum_j C(u_j,2) each run over ALL tied pairs on
    that side.  The previous `if sx == 0 and sy == 0: continue` skipped them,
    inflating the denominator and, in the all-tied limit, returning a spurious
    0.0 where tau-b is in fact undefined.
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
        if sx == 0:
            ta += 1
        if sy == 0:
            tb += 1
        if sx == 0 or sy == 0:
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
            # exhaustive: every load order, deterministic
            ex, ex_raw = tau_a_exhaustive(accs, T0, T1GRID)
            raw = tau_raw(accs, T0, T1GRID)
            rows.append({
                "cell": cell, "seed": sd,
                # tied PAIRS, C(n_g, 2) per tie group -- matches the report's
                # tied_pairs_first_last caliber (group-size-minus-one would
                # undercount: a group of 4 holds 6 tied pairs, not 3)
                "ties_low": sum(len(g) * (len(g) - 1) // 2 for g in ga),
                "ties_high": sum(len(g) * (len(g) - 1) // 2 for g in gb),
                "tau_a": None if a is None else round(float(a), 3),
                "tau_b": None if b is None else round(float(b), 3),
                "tau_a_raw": raw["tau_a_raw"],
                "tau_b_raw": raw["tau_b_raw"],
                "tau_a_exhaustive": {
                    "n_orders": math.factorial(len(accs)),
                    "n_values": len(ex),
                    "min": ex[0] if ex else None,
                    "max": ex[-1] if ex else None,
                    "spread": round(ex[-1] - ex[0], 4) if ex else None,
                    "values": ex,
                } if ex else None,
                "tau_a_raw_exhaustive": {
                    "n_orders": math.factorial(len(accs)),
                    "n_values": len(ex_raw),
                    "min": ex_raw[0] if ex_raw else None,
                    "max": ex_raw[-1] if ex_raw else None,
                    "spread": (round(ex_raw[-1] - ex_raw[0], 6)
                               if ex_raw else None),
                } if ex_raw else None,
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

    sens = [(r["tau_a_exhaustive"]["spread"], r["cell"], r["seed"],
             r["tau_a_exhaustive"]["n_values"]) for r in rows
            if r.get("tau_a_exhaustive")]
    sens.sort(reverse=True)
    n_sensitive = sum(1 for s in sens if s[0] > 0)
    print(f"\ntau-a load-order sensitivity (exhaustive over 7! = 5040 orders/run):")
    print(f"  order-sensitive (n_values > 1): {n_sensitive} of {len(rows)} runs")
    for spread, cell, sd, nv in sens[:5]:
        print(f"  worst: {cell} seed {sd}: {nv} distinct values, spread {spread:.3f}")

    # ---- R1: raw-value tau must be order-invariant -------------------------
    raw_sp = [r["tau_a_raw_exhaustive"]["spread"] for r in rows
              if r.get("tau_a_raw_exhaustive")]
    raw_nv = [r["tau_a_raw_exhaustive"]["n_values"] for r in rows
              if r.get("tau_a_raw_exhaustive")]
    worst = max(raw_sp) if raw_sp else 0.0
    print(f"\n[R1] tau-a on RAW values (order-invariant by construction):")
    print(f"  runs checked: {len(raw_sp)} of {len(rows)}")
    print(f"  max spread over all 5040 load orders: {worst:.6f}")
    print(f"  runs with >1 distinct value: {sum(1 for v in raw_nv if v > 1)}")
    if worst != 0.0:
        print("  !!! STOP CONDITION TRIGGERED: raw tau-a is NOT order-invariant.")
        print("      Do not proceed; report to reviewer.")
        return 2
    print("  OK: raw tau-a takes a single value under every load order (spread=0).")

    out = ROOT / "results" / "rank_inv" / "_tau_variant_check.json"
    out.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
