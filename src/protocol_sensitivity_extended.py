#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Extended protocol-sensitivity checks on the released 294 traces.

No model is trained.  Two quantities are computed:

1. Sustained-attainment sensitivity for k = 3, 5, 10.  The timestamp is the
   onset of the first k-round run at or above the target.  Winner-change rates
   use the same common-reacher set and two-round pair filter as Section 3.3.
2. Single-target selection loss.  Within each cell, retain targets at which all
   seven methods reach on all six seeds under first passage.  For every ordered
   pair (reference target, evaluation target), select the method with the lowest
   six-seed mean RTT at the reference target and measure its additional mean
   rounds at the evaluation target relative to the best method there.  Thus the
   same seven methods and six seeds enter both ends; censoring cannot create a
   loss.  Lexicographic method order breaks an exact reference-target tie.

Usage:
    python src/protocol_sensitivity_extended.py
    python src/protocol_sensitivity_extended.py \
        --out results/protocol_sensitivity_extended.json
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from rtt_statistic_compare import (  # noqa: E402
    ALPHAS, DATASETS, METHODS, SEEDS, TGRID, build, load_trace,
)
from sustained_attainment import flips, sustained  # noqa: E402

INF = float("inf")


def percentile_nearest(values, q):
    """Nearest-rank percentile, with a deterministic definition for the JSON."""
    if not values:
        return None
    ordered = sorted(values)
    pos = max(0, min(len(ordered) - 1,
                     int((len(ordered) - 1) * q + 0.5)))
    return ordered[pos]


def summarise(values):
    if not values:
        return {"n": 0, "median": None, "p95": None, "max": None}
    return {
        "n": len(values),
        "median": round(statistics.median(values), 4),
        "p95": round(percentile_nearest(values, 0.95), 4),
        "max": round(max(values), 4),
        "mean": round(statistics.mean(values), 4),
    }


def selection_loss(data):
    out = {}
    pooled_losses = []
    pooled_changed_losses = []
    pooled_pairs = pooled_changes = 0
    for ds in DATASETS:
        for alpha in ALPHAS[ds]:
            cell = "%s|a%s" % (ds, alpha)
            seeds = [s for s in SEEDS if (ds, alpha, s) in data]
            # Mean RTT is defined at t only when every method reaches on every
            # seed.  This is deliberately stricter than a per-method reach set.
            means = {}
            for t in TGRID:
                per_method = {}
                valid = True
                for m in METHODS:
                    vals = [data[(ds, alpha, s)][m]["first"][t]
                            for s in seeds]
                    if not vals or any(v == INF for v in vals):
                        valid = False
                        break
                    per_method[m] = sum(vals) / float(len(vals))
                if valid:
                    means[t] = per_method
            losses = []
            changed_losses = []
            examples = []
            n_pairs = n_changes = 0
            for ref in sorted(means):
                ref_order = sorted(METHODS, key=lambda m: (means[ref][m], m))
                chosen = ref_order[0]
                for ev in sorted(means):
                    if ev == ref:
                        continue
                    best = min(means[ev].values())
                    loss = means[ev][chosen] - best
                    # Guard only against floating-point noise; all inputs are
                    # means of integer round numbers.
                    loss = round(loss, 10)
                    losses.append(loss)
                    n_pairs += 1
                    ev_order = sorted(METHODS,
                                      key=lambda m: (means[ev][m], m))
                    if chosen != ev_order[0]:
                        n_changes += 1
                        changed_losses.append(loss)
                        examples.append({
                            "reference": ref, "evaluation": ev,
                            "selected": chosen, "best": ev_order[0],
                            "reference_margin_rounds": round(
                                means[ref][ref_order[1]] - means[ref][chosen], 4),
                            "loss_rounds": round(loss, 4),
                        })
            examples.sort(key=lambda e: (-e["loss_rounds"],
                                         e["reference"], e["evaluation"]))
            out[cell] = {
                "eligible_targets": [round(t, 2) for t in sorted(means)],
                "n_ordered_target_pairs": n_pairs,
                "n_selection_changes": n_changes,
                "all_ordered_pairs": summarise(losses),
                "changed_selections": summarise(changed_losses),
                "changes_with_loss_gt_2": sum(v > 2 for v in changed_losses),
                "largest_examples": examples[:5],
            }
            pooled_losses.extend(losses)
            pooled_changed_losses.extend(changed_losses)
            pooled_pairs += n_pairs
            pooled_changes += n_changes
    out["_pooled"] = {
        "n_ordered_target_pairs": pooled_pairs,
        "n_selection_changes": pooled_changes,
        "all_ordered_pairs": summarise(pooled_losses),
        "changed_selections": summarise(pooled_changed_losses),
        "changes_with_loss_gt_2": sum(v > 2 for v in pooled_changed_losses),
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(
        ROOT, "results", "protocol_sensitivity_extended.json"))
    args = ap.parse_args()

    data, srcmap, missing = build()
    if missing or len(data) != 42 or sum(len(v) for v in data.values()) != 294:
        raise RuntimeError("Expected 42 cell-seed groups and 294 traces; "
                           "missing=%r" % (missing,))
    # Add all three sustained rules after one second pass over the raw traces.
    for ds in DATASETS:
        for alpha in ALPHAS[ds]:
            for m in METHODS:
                for seed in SEEDS:
                    got = load_trace(ds, alpha, m, seed)
                    if got is None:
                        raise RuntimeError("Missing trace: %r" %
                                           ((ds, alpha, m, seed),))
                    acc = got[0]
                    tbl = data[(ds, alpha, seed)][m]
                    for k in (3, 5, 10):
                        tbl["sust%d" % k] = {
                            t: sustained(acc, t, k=k) for t in TGRID
                        }

    sustained_out = {}
    for k in (3, 5, 10):
        f = flips(data, "first", "sust%d" % k)
        sustained_out["k%d" % k] = f
        print("first passage vs sustained-%d: %d/%d = %.1f%%" %
              (k, f["winner_flips"], f["units"], 100 * f["rate"]))

    loss = selection_loss(data)
    print("\nSingle-target selection loss (strict all-method/all-seed set):")
    for cell, row in loss.items():
        print("%-16s changes=%d/%d changed-loss median=%s max=%s >2 rounds=%d" %
              (cell, row["n_selection_changes"],
               row["n_ordered_target_pairs"],
               row["changed_selections"]["median"],
               row["changed_selections"]["max"],
               row["changes_with_loss_gt_2"]))

    result = {
        "source": "294 released Stage-B traces; no training",
        "target_grid": [TGRID[0], TGRID[-1], 0.01],
        "near_tie_rounds": 2,
        "sustained": sustained_out,
        "selection_loss": loss,
        "selection_loss_definition": (
            "Ordered target pairs within each cell; all seven methods reach "
            "on all six seeds at both targets. Select by six-seed mean RTT at "
            "the reference target; loss is additional mean rounds at the "
            "evaluation target relative to its best method."),
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1)
    print("\nwrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
