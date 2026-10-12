"""R6: is the oscillation attributed to a method just an aggressive hyperparameter?

Falsifiable prediction, written BEFORE CIFAR-10 was analysed
-----------------------------------------------------------
Stage A selected fdyn_alpha = 0.3 on both MNIST and FashionMNIST. At that value
FedDyn oscillates violently on FashionMNIST (last-10-round std 0.023-0.043 vs
0.0003-0.0032 for every other method) and its rank inversions vanish once R5
excludes it.

The prediction: at a MORE CONSERVATIVE fdyn_alpha the oscillation disappears.
If it does, FedDyn's inversions were a tuning artefact -- the method is fine, we
merely ran it too aggressively. If the oscillation persists across the whole grid,
then something else drives it and the "just a bad hyperparameter" reading is wrong
even if we could have tuned it away.

Either outcome is informative, which is what makes this worth running rather than
assuming the convenient branch.

Reads the Stage A sweep file, which stores the FULL trace of every setting (not
just the winner), so no retraining is needed.
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_rank_inv import late_volatility, post_peak_drop


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "results", "rank_inv"))
    ap.add_argument("--dataset", default="fashion")
    ap.add_argument("--alpha", type=float, default=0.1)
    ap.add_argument("--method", default="feddyn")
    ap.add_argument("--rounds", type=int, default=60)
    ap.add_argument("--vol-max", type=float, default=0.01)
    ap.add_argument("--drop-max", type=float, default=5.0)
    args = ap.parse_args()

    path = os.path.join(args.dir, f"tuned_{args.dataset}_a{args.alpha}.json")
    if not os.path.exists(path):
        raise SystemExit(f"missing {path}")
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    # keys look like "<dataset>|<alpha>|<method>"; each holds one entry per setting
    want = f"{args.dataset}|{args.alpha}|{args.method}"
    if want not in data:
        raise SystemExit(f"{want} not in {path}; available: {sorted(data)[:10]}")
    entry = data[want]

    # Stage A layout is:
    #   entry["best_hp"]  the selected setting
    #   entry["settings"] list of {"hp", "label", "late_acc", "peak_acc",
    #                              "final_acc", "trace", ...} for EVERY grid point
    # The full trace is stored per setting, which is what makes R6 free to run.
    settings = entry.get("settings")
    if settings is None:
        raise SystemExit(f"{want} has no 'settings' list; keys={sorted(entry)[:8]}")

    print(f"R6 mechanism check: {args.method} on {args.dataset} "
          f"(alpha={args.alpha}, budget {args.rounds} rounds)")
    print(f"selected by Stage A: {entry.get('label') or entry.get('best_hp')}")
    print(f"criterion: unstable if last10 std > {args.vol_max} "
          f"or post-peak drop > {args.drop_max} pts\n")

    print(f"{'setting':<24} {'peak':>8} {'final':>8} {'drop':>8} "
          f"{'last10sd':>10}  verdict")
    rows = []
    for rec in settings:
        label = rec.get("label") or str(rec.get("hp"))
        tr = rec.get("trace")
        if tr is None:
            print(f"  {label:<24} (no trace)")
            continue
        acc = np.array([float(t["acc"]) for t in tr], dtype=float)
        pk, fin = float(acc.max()), float(acc[-1])
        drop, vol = post_peak_drop(acc), late_volatility(acc)
        bad = vol > args.vol_max or drop > args.drop_max
        rows.append((label, pk, fin, drop, vol, bad))
        mark = "  <-- selected" if rec.get("hp") == entry.get("best_hp") else ""
        print(f"{label:<24} {pk:>8.4f} {fin:>8.4f} {drop:>7.1f}p "
              f"{vol:>10.4f}  {'UNSTABLE' if bad else 'stable'}{mark}")

    if not rows:
        raise SystemExit("no usable traces found")

    unstable = [r[0] for r in rows if r[5]]
    stable = [r[0] for r in rows if not r[5]]
    print(f"\n  stable settings   : {stable}")
    print(f"  unstable settings : {unstable}")

    if stable and unstable:
        # R6 verdict: a conservative coefficient settles the method -> the
        # inversions were a tuning artefact, not a property of the metric.
        print("\n  R6 verdict: CONFIRMED -- the oscillation is coefficient-dependent.")
        print("  A conservative setting settles the trajectory, so the inversions")
        print("  attributed to it are a tuning artefact rather than evidence about")
        print("  rounds-to-target.")
    elif unstable:
        print("\n  R6 verdict: NOT CONFIRMED -- unstable at every setting in the grid.")
        print("  Tuning alone does not remove the oscillation.")
    else:
        print("\n  R6 verdict: INCONCLUSIVE -- stable everywhere in this grid.")
        print("  Increase the grid or the budget before drawing a conclusion.")


if __name__ == "__main__":
    main()