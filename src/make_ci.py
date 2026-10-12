#!/usr/bin/env python
"""Seed-level bootstrap CIs + full distribution tables (task A-4).

Absorbs WP-6a (bootstrap CI and effect size) and WP-7 (report the full
distribution, not only the extremes), recomputed on the 6-seed data.

WHAT IS BOOTSTRAPPED
--------------------
The resampling unit is the SEED, not the round and not the client. That is the
only unit that is plausibly exchangeable here: six independent training runs
per (dataset, alpha, method) cell. With n=6 the bootstrap is coarse -- it is
reported as a description of seed-to-seed spread, NOT as a claim of asymptotic
coverage. That caveat is printed in the output on purpose.

    statistic  -> resample the 6 seeds with replacement, 10,000 times,
                  take the 2.5th and 97.5th percentile.

COVERAGE
--------
1. late accuracy per (cell, method)
2. top-2 gap per cell: mean(best) - mean(second best)
3. spread per cell: max - min over methods (the section 3.3 quantity)
4. decay-probe gap (FedAvg - SCAFFOLD) per (dataset, decay) -- the Table 2 gap
5. swing of that gap from decay=0.90 to decay=1.00
6. per-seed Kendall tau, all seeds listed individually
7. the complete distribution: every seed x cell x method late accuracy, so no
   reader has to take an extreme value on trust

USAGE
-----
    python make_ci.py --dir ../results/rank_inv --out ../results/rank_inv/bootstrap_ci.json \
        --md ../results/bootstrap_ci.md --n-boot 10000
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_rank_inv import acc_trace

N_BOOT_DEFAULT = 10000


def late_acc(a, tail=10):
    return 100.0 * float(np.mean(a[-tail:]))


def boot_ci(vals, n_boot, rng, stat=np.mean):
    """Percentile bootstrap CI over the seed axis."""
    v = np.asarray(vals, dtype=float)
    if len(v) < 2:
        return None, None, None
    idx = rng.integers(0, len(v), size=(n_boot, len(v)))
    draws = stat(v[idx], axis=1)
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return float(stat(v)), float(lo), float(hi)


def load_stage_b(d):
    cells = {}
    for f in sorted(os.listdir(d)):
        if not f.endswith(".json"):
            continue
        if "_decay_" in f or "tuned" in f or "report" in f or "sign_test" in f \
                or "bootstrap" in f:
            continue
        try:
            r = json.load(open(os.path.join(d, f), encoding="utf-8"))
        except Exception:
            continue
        c = r.get("cfg") if isinstance(r, dict) else None
        if not isinstance(c, dict) or "method" not in c or "seed" not in c:
            continue
        cells.setdefault((c["dataset"], c["alpha"]), {}).setdefault(c["seed"], {})[
            c["method"]] = late_acc(acc_trace(r))
    return cells


def load_decay(d):
    """decay probe -> {(dataset, seed): {decay: {method: {'late':..,'stable':..}}}}"""
    out = {}
    for f in sorted(os.listdir(d)):
        if not f.startswith("_decay_") or not f.endswith(".json"):
            continue
        if "_starve" in f:
            continue
        base = f[len("_decay_"):-len(".json")]
        if "_s" not in base:
            continue
        tag, _, s = base.rpartition("_s")
        if not s.isdigit():
            continue
        try:
            doc = json.load(open(os.path.join(d, f), encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue
        for meth, by_decay in doc.items():
            if not isinstance(by_decay, dict):
                continue
            for dk, rec in by_decay.items():
                if not isinstance(rec, dict) or "late" not in rec:
                    continue
                out.setdefault((tag, int(s)), {}).setdefault(
                    float(dk), {})[meth] = {
                        "late": 100.0 * float(rec["late"]),
                        "stable": bool(rec.get("stable", False))}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="../results/rank_inv")
    ap.add_argument("--out", default="../results/rank_inv/bootstrap_ci.json")
    ap.add_argument("--md", default="../results/bootstrap_ci.md")
    ap.add_argument("--n-boot", type=int, default=N_BOOT_DEFAULT)
    ap.add_argument("--seed", type=int, default=20261012)
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    cells = load_stage_b(args.dir)
    decay = load_decay(args.dir)

    res = {"n_boot": args.n_boot, "bootstrap_unit": "seed",
           "rng_seed": args.seed,
           "caveat": "n=6 seeds; percentile bootstrap describes observed "
                     "seed-to-seed spread, it is not an asymptotic coverage claim",
           "cells": {}, "decay_probe": {}, "distribution": []}

    # ---------- 1-3: Stage B ----------
    for (ds, al), by_seed in sorted(cells.items()):
        seeds = sorted(by_seed)
        methods = sorted(set().union(*[set(v) for v in by_seed.values()]))
        per_method = {}
        for m in methods:
            v = [by_seed[s][m] for s in seeds if m in by_seed[s]]
            mean, lo, hi = boot_ci(v, args.n_boot, rng)
            per_method[m] = {"seeds": {str(s): round(by_seed[s][m], 4)
                                       for s in seeds if m in by_seed[s]},
                             "mean": mean, "ci_lo": lo, "ci_hi": hi,
                             "sd": float(np.std(v, ddof=1)) if len(v) > 1 else 0.0}

        def pair_gap(m1, m2):
            d = [by_seed[s][m1] - by_seed[s][m2]
                 for s in seeds if m1 in by_seed[s] and m2 in by_seed[s]]
            return d

        means = {m: per_method[m]["mean"] for m in methods}
        order = sorted(methods, key=lambda m: -means[m])
        top2 = (order[0], order[1]) if len(order) >= 2 else (None, None)
        gap_vals = pair_gap(*top2) if top2[0] else []
        g_mean, g_lo, g_hi = boot_ci(gap_vals, args.n_boot, rng) if gap_vals \
            else (None, None, None)

        spread_vals = []
        for s in seeds:
            vs = [by_seed[s][m] for m in methods if m in by_seed[s]]
            spread_vals.append(max(vs) - min(vs))
        sp_mean, sp_lo, sp_hi = boot_ci(spread_vals, args.n_boot, rng)

        res["cells"]["%s|a%s" % (ds, al)] = {
            "seeds": seeds, "methods": methods,
            "per_method": per_method,
            "top2": list(top2),
            "top2_gap": {"mean": g_mean, "ci_lo": g_lo, "ci_hi": g_hi,
                         "per_seed": [round(x, 4) for x in gap_vals]},
            "spread": {"mean": sp_mean, "ci_lo": sp_lo, "ci_hi": sp_hi,
                       "per_seed": [round(x, 4) for x in spread_vals]},
        }
        for s in seeds:
            for m in methods:
                if m in by_seed[s]:
                    res["distribution"].append({
                        "cell": "%s|a%s" % (ds, al), "seed": s, "method": m,
                        "late_acc": round(by_seed[s][m], 4)})

    # ---------- 4-5: decay probe ----------
    by_ds = {}
    for (tag, s), by_decay in decay.items():
        by_ds.setdefault(tag, {}).setdefault(s, {}).update(by_decay)
    for tag, by_seed in sorted(by_ds.items()):
        seeds = sorted(by_seed)
        decays = sorted(set().union(*[set(v) for v in by_seed.values()]))
        per_decay = {}
        for dk in decays:
            gaps = []
            n_stable = {"fedavg": 0, "scaffold": 0}
            n_tot = {"fedavg": 0, "scaffold": 0}
            for s in seeds:
                rec = by_seed[s].get(dk, {})
                if "fedavg" in rec and "scaffold" in rec:
                    gaps.append(rec["fedavg"]["late"] - rec["scaffold"]["late"])
                for m in ("fedavg", "scaffold"):
                    if m in rec:
                        n_tot[m] += 1
                        n_stable[m] += int(rec[m]["stable"])
            g_mean, g_lo, g_hi = boot_ci(gaps, args.n_boot, rng) if gaps \
                else (None, None, None)
            per_decay[str(dk)] = {
                "gap_mean": g_mean, "gap_ci_lo": g_lo, "gap_ci_hi": g_hi,
                "gap_per_seed": [round(x, 4) for x in gaps],
                "fedavg_stable": "%d/%d" % (n_stable["fedavg"], n_tot["fedavg"]),
                "scaffold_stable": "%d/%d" % (n_stable["scaffold"], n_tot["scaffold"]),
            }
        lo_key, hi_key = str(decays[0]), str(decays[-1])
        swing = None
        if per_decay.get(lo_key, {}).get("gap_mean") is not None and \
                per_decay.get(hi_key, {}).get("gap_mean") is not None:
            swing = per_decay[hi_key]["gap_mean"] - per_decay[lo_key]["gap_mean"]
        res["decay_probe"][tag] = {
            "seeds": seeds, "decays": decays, "per_decay": per_decay,
            "swing_gap_lo_to_hi_decay": swing,
        }

    # ---------- 6: per-seed Kendall tau ----------
    rep = os.path.join(args.dir, "rank_inv_report_alpha_sweep.json")
    if os.path.exists(rep):
        tau = json.load(open(rep, encoding="utf-8"))["summary"]
        res["kendall_tau_per_seed"] = {
            cell: v.get("kendall_tau_first_vs_last")
            for cell, v in tau.items()}

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)

    # ---------- markdown ----------
    L = []
    L.append("# Bootstrap CIs and full distributions (6 seeds)\n")
    L.append("Seed-level percentile bootstrap, %d resamples, rng seed %d.\n"
             % (args.n_boot, args.seed))
    L.append("> **Caveat.** n = 6 seeds per cell. The bootstrap below describes "
             "the observed seed-to-seed spread; it is **not** an asymptotic "
             "coverage claim. Read the per-seed columns alongside the CI.\n")
    L.append("\n## 1. Late accuracy per method, with 95% CI\n")
    L.append("| cell | method | mean | 95% CI | sd | per-seed values |")
    L.append("|---|---|---|---|---|---|")
    for cell, v in res["cells"].items():
        for m in v["methods"]:
            pm = v["per_method"][m]
            L.append("| %s | %s | %.2f | [%.2f, %.2f] | %.2f | %s |" % (
                cell, m, pm["mean"], pm["ci_lo"], pm["ci_hi"], pm["sd"],
                ", ".join("%.2f" % x for x in pm["seeds"].values())))
    L.append("\n## 2. Top-2 gap and spread per cell\n")
    L.append("| cell | top-2 | gap mean | gap 95% CI | gap per-seed | "
             "spread mean | spread 95% CI |")
    L.append("|---|---|---|---|---|---|---|")
    for cell, v in res["cells"].items():
        g, sp = v["top2_gap"], v["spread"]
        L.append("| %s | %s | %.2f | [%.2f, %.2f] | %s | %.2f | [%.2f, %.2f] |" % (
            cell, " vs ".join(v["top2"]), g["mean"], g["ci_lo"], g["ci_hi"],
            ", ".join("%.2f" % x for x in g["per_seed"]),
            sp["mean"], sp["ci_lo"], sp["ci_hi"]))
    L.append("\n## 3. Decay probe: FedAvg - SCAFFOLD gap (pts), with 95% CI\n")
    L.append("| dataset | lr_decay | gap mean | 95% CI | per-seed gaps | "
             "FedAvg stable | SCAFFOLD stable |")
    L.append("|---|---|---|---|---|---|---|")
    for tag, v in res["decay_probe"].items():
        for dk, pd in v["per_decay"].items():
            if pd["gap_mean"] is None:
                continue
            L.append("| %s | %s | %+.2f | [%.2f, %.2f] | %s | %s | %s |" % (
                tag, dk, pd["gap_mean"], pd["gap_ci_lo"], pd["gap_ci_hi"],
                ", ".join("%+.2f" % x for x in pd["gap_per_seed"]),
                pd["fedavg_stable"], pd["scaffold_stable"]))
        L.append("")
        L.append("*%s: gap swing from decay %s to %s = %s pts*\n" % (
            tag, v["decays"][0], v["decays"][-1],
            ("%+.2f" % v["swing_gap_lo_to_hi_decay"])
            if v["swing_gap_lo_to_hi_decay"] is not None else "n/a"))
    if "kendall_tau_per_seed" in res:
        L.append("\n## 4. Kendall tau (lowest vs highest target), per seed\n")
        L.append("| cell | " + " | ".join(
            "s%d" % s for s in range(6)) + " |")
        L.append("|---|" + "---|" * 6)
        for cell, tv in res["kendall_tau_per_seed"].items():
            tv = tv or {}
            row = [("%.2f" % tv[str(s)] if str(s) in tv else "-")
                   for s in range(6)]
            L.append("| %s | %s |" % (cell, " | ".join(row)))
    L.append("\n## 5. Full distribution: every seed x cell x method\n")
    L.append("%d rows. (`results/rank_inv/bootstrap_ci.json` -> `distribution`)\n"
             % len(res["distribution"]))
    with open(args.md, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")

    print("cells: %d   distribution rows: %d   decay datasets: %d"
          % (len(res["cells"]), len(res["distribution"]), len(res["decay_probe"])))
    print("-> %s" % args.out)
    print("-> %s" % args.md)


if __name__ == "__main__":
    main()
