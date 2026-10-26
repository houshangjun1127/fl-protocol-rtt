#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R7 / M4: how much of the "winner changes" rate is censoring, not the rule?

WHY THIS SCRIPT EXISTS
----------------------
Every RTT in this paper is a first-passage time observed inside a 60-round
budget. A run that never touches the target has no RTT at that target and we do
not impute one, so a seed-averaged RTT is a *conditional* mean whose conditioning
set shrinks as the target rises. The reviewer's point (M4) is that any quantity
built on that mean -- the ranking, and therefore the "winner changes" rate of
Section 3.3 -- is partly a statement about who was still eligible rather than
only about who was faster.

This script measures it. For every (cell, seed, target) unit in which the
first-ranked method changes between two decision statistics, it asks whether the
set of methods that reached the target is the same under both statistics:

  RULE EFFECT        identical reach sets: the two statistics ranked the same
                     candidates and disagreed only about their order;
  ELIGIBILITY EFFECT the reach sets differ: a method was excluded from one
                     ranking purely because it was censored under the other
                     statistic, so the change can be produced by who remained
                     rather than by the statistic itself.

The two shares sum to 100% by construction. Separately it recomputes every
pairwise comparison on the seeds where *both* methods reach the target (paired
both-reach), which is free of the artefact.

CONVENTIONS (stated because each is a choice, not a default)
------------------------------------------------------------
  T            first-passage round in {1..60}; T = inf if never reached.
  mean RTT     E[T | T <= 60] over the seeds that reach t -- a CONDITIONAL
               mean, not E[T]. `n_valid` records the contributing seeds.
  reach rate   P(T <= 60) = n_reach / n_seeds.
  RMTT         restricted mean time-to-target,
                   RMTT = E[min(T, 61)] = (1/n) * sum_i min(T_i, 61),
               i.e. a censored seed contributes 61 rounds -- the standard
               "+1" convention for a discrete horizon. Identical to the area
               under the survival curve, sum_{r=1}^{61} P(T >= r); the min(T,61)
               form is used because it makes the censoring penalty explicit.
               RMTT is NOT an estimate of E[T]: it is a bounded summary of the
               observable window, and it is defined even where the conditional
               mean is not.

No model is trained; everything is recomputed from the released traces.

Usage
-----
    python src/censoring_analysis.py
    python src/censoring_analysis.py --out results/rank_inv/_censoring.json
"""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from itertools import combinations

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# Reuse WP-11's statistic definitions and trace loader verbatim, so the
# decomposition cannot drift from the numbers already in the paper.
from rtt_statistic_compare import (  # noqa: E402
    ALPHAS, DATASETS, METHODS, SEEDS, STATS, STAT_LABEL, TGRID, WIN,
    load_trace, smooth,
)

HORIZON = 60
CENSOR_VALUE = HORIZON + 1          # 61 -- the "+1" convention above
INF = float("inf")

CELLS = [(ds, a) for ds in DATASETS for a in ALPHAS[ds]]
# The compact supplementary table reports every tenth grid point; the full
# grid is in the JSON next to it.
REPORT_TARGETS = [t for i, t in enumerate(TGRID) if i % 10 == 0]


# ------------------------------------------------------------------- statistics
def rtt_one(acc, stat, t):
    ser = acc if stat == "first" else smooth(acc, WIN[stat])
    for r in range(1, len(ser)):
        v = ser[r]
        if v is not None and v >= t:
            return r
    return INF


def rank_at(rt, common):
    """First-ranked method among `common`, ordered by RTT then name.

    Identical to src/rtt_statistic_compare.py::rank_at restricted to the
    commonly-reaching set, which is what produced the 366 / 423 counts already
    reported in Section 3.3. Keeping the definition byte-identical is what lets
    the decomposition below be checked against those published numbers.
    """
    return sorted(common, key=lambda m: (rt[m], m))[0]


# -------------------------------------------------------------------------- io
def build():
    """(ds, alpha, seed) -> method -> 1-based accuracy list."""
    data = defaultdict(dict)
    for ds in DATASETS:
        for a in ALPHAS[ds]:
            for seed in SEEDS:
                for m in METHODS:
                    got = load_trace(ds, a, m, seed)
                    if got is not None:
                        data[(ds, a, seed)][m] = got[0]
    return data


# ------------------------------------------------------------------- analyses
def table_reach(data):
    """Per (cell, target): how many methods fully/partially/never reach, plus
    the conditional-mean and RMTT spread across the seven methods.

    The per-method breakdown behind each row is kept in the JSON so that a
    reader can audit any single entry without a 3,000-row table in the text.
    """
    rows = []
    for (ds, a) in CELLS:
        seeds = [s for s in SEEDS if (ds, a, s) in data]
        for t in TGRID:
            full = part = zero = 0
            conds = []
            rmtts = []
            per_method = {}
            for m in METHODS:
                vals = [rtt_one(data[(ds, a, s)][m], "first", t) for s in seeds]
                fin = [v for v in vals if v < INF]
                cens = [CENSOR_VALUE if v == INF else v for v in vals]
                rr = len(fin) / float(len(seeds))
                cond = round(float(np.mean(fin)), 2) if fin else None
                rm = round(float(np.mean(cens)), 2)
                per_method[m] = {"n_reach": len(fin), "n_seeds": len(seeds),
                                 "reach_rate": round(rr, 3),
                                 "mean_rtt_cond": cond, "rmtt": rm}
                if rr == 1.0:
                    full += 1
                elif len(fin) == 0:
                    zero += 1
                else:
                    part += 1
                if cond is not None:
                    conds.append(cond)
                rmtts.append(rm)
            rows.append({
                "cell": f"{ds}|a{a}", "target": round(t, 2),
                "n_full": full, "n_partial": part, "n_zero": zero,
                "cond_min": min(conds) if conds else None,
                "cond_max": max(conds) if conds else None,
                "rmtt_min": min(rmtts), "rmtt_max": max(rmtts),
                "per_method": per_method,
            })
    return rows


def table_decomposition(data, tau):
    """Split the winner-change count into rule effect and eligibility effect.

    Reproduces the Section 3.3 comparison exactly (same grid, same comparable
    set, same tie-break) and adds one label per changed unit.
    """
    out = {}
    for s1, s2 in combinations(STATS, 2):
        key = f"{s1}_vs_{s2}"
        per_cell = {}
        tot = chg = rule = elig = 0
        for (ds, a) in CELLS:
            seeds = [s for s in SEEDS if (ds, a, s) in data]
            c_u = c_w = c_r = c_e = 0
            for seed in seeds:
                for t in TGRID:
                    r1 = {m: rtt_one(data[(ds, a, seed)][m], s1, t)
                          for m in METHODS}
                    r2 = {m: rtt_one(data[(ds, a, seed)][m], s2, t)
                          for m in METHODS}
                    common = [m for m in METHODS
                              if r1[m] < INF and r2[m] < INF]
                    if len(common) < 2:
                        continue
                    c_u += 1
                    w1 = rank_at(r1, common)
                    w2 = rank_at(r2, common)
                    if w1 != w2:
                        c_w += 1
                        reach1 = frozenset(m for m in METHODS if r1[m] < INF)
                        reach2 = frozenset(m for m in METHODS if r2[m] < INF)
                        if reach1 == reach2:
                            c_r += 1
                        else:
                            c_e += 1
            per_cell[f"{ds}|a{a}"] = {"units": c_u, "winner_changes": c_w,
                                       "rule_effect": c_r,
                                       "eligibility_effect": c_e}
            tot += c_u; chg += c_w; rule += c_r; elig += c_e
        out[key] = {
            "per_cell": per_cell,
            "units": tot,
            "winner_changes": chg,
            "rate": round(chg / tot, 4) if tot else None,
            "rule_effect": rule,
            "eligibility_effect": elig,
            "share_rule_effect": round(rule / chg, 4) if chg else None,
            "share_eligibility_effect": round(elig / chg, 4) if chg else None,
        }
    return out


def table_paired(data, tau):
    """Per (cell, method pair): both-reach comparison vs. conditional means.

    For each target we take the seeds on which BOTH methods reach t and compare
    their mean RTT there (paired). We then ask whether that comparison agrees
    in sign with the comparison implied by each method's own conditional mean
        E[T | T <= 60] taken over *all* seeds -- the quantity the paper plots.
    Sign disagreement means the conditional mean is comparing different seed
    sets, which is exactly the censoring artefact the reviewer flagged.
    """
    out = {}
    for (ds, a) in CELLS:
        seeds = [s for s in SEEDS if (ds, a, s) in data]
        ent = {}
        for x, y in combinations(METHODS, 2):
            agree = disagree = 0
            n_t = 0
            diffs = []
            for t in TGRID:
                px, py = [], []          # paired, both reach
                ax, ay = [], []          # all seeds, conditional
                for s in seeds:
                    vx = rtt_one(data[(ds, a, s)][x], "first", t)
                    vy = rtt_one(data[(ds, a, s)][y], "first", t)
                    if vx < INF:
                        ax.append(vx)
                    if vy < INF:
                        ay.append(vy)
                    if vx < INF and vy < INF:
                        px.append(vx)
                        py.append(vy)
                if len(px) < 1 or not ax or not ay:
                    continue
                n_t += 1
                d_pair = float(np.mean(px)) - float(np.mean(py))
                d_cond = float(np.mean(ax)) - float(np.mean(ay))
                diffs.append(d_pair)
                if abs(d_pair) < tau or abs(d_cond) < tau:
                    continue        # near tie: not evidence of disagreement
                if (d_pair > 0) == (d_cond > 0):
                    agree += 1
                else:
                    disagree += 1
            ent[f"{x}|{y}"] = {
                "n_targets_with_common_seed": n_t,
                "sign_agree": agree,
                "sign_disagree": disagree,
                "disagree_rate": (round(disagree / float(agree + disagree), 4)
                                  if (agree + disagree) else None),
                "mean_paired_diff_rounds": (round(float(np.mean(diffs)), 2)
                                            if diffs else None),
            }
        out[f"{ds}|a{a}"] = ent
    return out


# ----------------------------------------------------------------- rendering
def md_reach(rows):
    sel = [r for r in rows
           if int(round(r["target"] * 100)) % 10 == 0]
    out = ["**Table S2. Reach and the two means, per (cell, target).** "
           "`full` = methods of the seven that reach the target on all six "
           "seeds; `partial` = methods that reach it on some seeds but not "
           "all; `none` = methods that never reach it inside the budget. "
           "`cond` is E[T | T <= 60], taken over the reaching seeds only, and "
           "is undefined for a method with reach = 0; the `cond` min-max "
           "therefore skips such methods, while the `rmtt` min-max does not "
           "(a censored method contributes 61). That asymmetry is the whole "
           "reason the two columns can disagree. Per-method values behind every "
           "row are in `_censoring.json`.", "",
           "| cell | target | full | partial | none | cond min-max (rounds) | "
           "rmtt min-max (rounds) |", "|---|---|---|---|---|---|---|"]
    for r in sorted(sel, key=lambda z: (z["cell"], z["target"])):
        cm = ("-" if r["cond_min"] is None
              else "%.2f-%.2f" % (r["cond_min"], r["cond_max"]))
        out.append("| %s | %.2f | %d | %d | %d | %s | %.2f-%.2f |"
                % (r["cell"], r["target"], r["n_full"], r["n_partial"],
                   r["n_zero"], cm, r["rmtt_min"], r["rmtt_max"]))
    out.append("")
    return "\n".join(out)


def md_decomp(dec):
    out = ["**Table S3. Decomposition of the Section 3.3 winner-change rate.** "
           "For every comparable (cell, seed, target) unit in which the "
           "first-ranked method differs between the two statistics, the unit "
           "is labelled *rule* when the set of methods reaching the target is "
           "identical under both statistics, and *eligibility* when it is not. "
           "The two shares sum to 100% by construction.", "",
           "| statistic pair | comparable units | winner changes | rate | "
           "rule effect | eligibility effect | share rule | share eligibility |",
           "|---|---|---|---|---|---|---|---|"]
    for k, v in dec.items():
        out.append("| %s | %d | %d | %.1f%% | %d | %d | %.1f%% | %.1f%% |" % (
            STAT_LABEL[k.split("_vs_")[0]] + " vs " +
            STAT_LABEL[k.split("_vs_")[1]],
            v["units"], v["winner_changes"], 100.0 * (v["rate"] or 0),
            v["rule_effect"], v["eligibility_effect"],
            100.0 * (v["share_rule_effect"] or 0),
            100.0 * (v["share_eligibility_effect"] or 0)))
    out.append("")
    return "\n".join(out)


def md_paired(paired):
    """One summary row per cell, then only the pairs that ever disagree.

    The full 7 cells x 21 pairs x 61 targets grid is in the JSON; printing it
    here would add 147 rows for a quantity that is zero in all but a handful.
    """
    out = ["**Table S4. Paired both-reach comparison, summarised per cell.** "
           "For each (cell, method pair) and each target we restrict to the "
           "seeds on which BOTH methods reach the target and compare mean RTT "
           "there (paired), then ask whether the sign agrees with the sign "
           "implied by each method's own conditional mean E[T | T <= 60] taken "
           "over all six seeds. Disagreement identifies the artefact "
           "precisely: the two conditional means were computed over different "
           "seed sets. Comparisons closer than the 2-round near-tie threshold "
           "are excluded from the agree/disagree counts.", "",
           "| cell | pairs compared | sign agree | sign disagree | "
           "disagree rate | pairs with any disagreement |",
           "|---|---|---|---|---|---|"]
    for cell in sorted(paired):
        ag = dg = 0
        bad = []
        for pk, v in sorted(paired[cell].items()):
            ag += v["sign_agree"]
            dg += v["sign_disagree"]
            if v["sign_disagree"]:
                bad.append("%s (%d/%d targets)"
                           % (pk, v["sign_disagree"],
                              v["sign_disagree"] + v["sign_agree"]))
        rate = "-" if (ag + dg) == 0 else "%.1f%%" % (100.0 * dg / (ag + dg))
        out.append("| %s | %d | %d | %d | %s | %s |"
                   % (cell, len(paired[cell]), ag, dg, rate,
                      "; ".join(bad) if bad else "none"))
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(
        ROOT, "results", "rank_inv", "_censoring.json"))
    ap.add_argument("--md", default=os.path.join(
        ROOT, "results", "_censoring_tables.md"))
    ap.add_argument("--tau", type=float, default=2.0,
                    help="near-tie filter in rounds (same as the main analyzer)")
    args = ap.parse_args()

    data = build()
    reach_rows = table_reach(data)
    decomp = table_decomposition(data, args.tau)
    paired = table_paired(data, args.tau)

    out = {
        "conventions": {
            "horizon_rounds": HORIZON,
            "censored_value_rmtt": CENSOR_VALUE,
            "mean_rtt": "E[T | T <= 60] over reaching seeds; n_valid reported",
            "rmtt": "E[min(T, 61)], equal to sum_{r=1}^{61} P(T >= r)",
            "tgrid": [TGRID[0], TGRID[-1], 0.01],
            "tau_rounds": args.tau,
            "statistics": {s: STAT_LABEL[s] for s in STATS},
        },
        "n_traces": sum(len(v) for v in data.values()),
        "per_cell_target": reach_rows,
        "winner_change_decomposition": decomp,
        "paired_both_reach": paired,
    }

    md = "\n".join([md_reach(reach_rows), md_decomp(decomp), md_paired(paired)])

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    with open(args.md, "w", encoding="utf-8") as fh:
        fh.write(md + "\n")
    print(md)
    print("wrote %s" % args.out)
    print("wrote %s" % args.md)


if __name__ == "__main__":
    main()
