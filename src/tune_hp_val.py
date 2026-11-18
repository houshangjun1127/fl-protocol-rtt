"""Validation-split control: does Stage A's selection metric change the chosen
hyperparameters?

Why this script exists
----------------------
The Stage A sweep selects hyperparameters on the *test* split, so the test set
participates in tuning; this is disclosed in the manuscript. This script
measures how much it actually matters, which is a separate question from
whether it is disclosed.

Design
------
Run the SAME Stage A grid once, with a validation split evaluated alongside the
test split (see `data.load_dataset_with_val`: train/test subsamples are
bit-identical to the published runs). Then compute the Stage A selection twice
from those same runs -- once scoring on validation accuracy, once on test
accuracy -- using the identical selection rule in both cases.

Because both selections are read off one set of runs, any difference between
them is attributable to the selection metric alone: not to seed noise, not to
a different grid, not to a different budget.

The same-grid trick matters here. Running two separate sweeps would confound
the comparison with run-to-run nondeterminism, which is exactly the sort of
protocol artefact this paper is about.

Selection rule: identical to `tune_hp.py` v2 -- prefer a *stable* setting even
at slightly lower late-round accuracy, keyed on (stable, late_acc), where
`stable` means last-10-round std <= vol_max AND post-peak drop <= drop_max.
Only the accuracy source changes.

Writes results/rank_inv/tunedval_<dataset>_a<alpha>.json
"""
import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rank_inv_runner import run_one
from analyze_rank_inv import late_volatility, post_peak_drop

# Identical to tune_hp.GRID. Deliberately restated rather than imported so that
# a later edit to the Stage A grid cannot silently change the comparison this
# script makes; if they diverge, `check_grid_parity` below fails.
GRID = {
    "fedavg":   [{}],
    "uniform":  [{}],
    "fedavgm":  [{"beta": b, "lr_s": 1.0} for b in (0.5, 0.7, 0.9, 0.95)],
    "fedproxw": [{"rho": r} for r in (0.2, 0.5, 0.8)],
    "fedadam":  [{"lr_s": x, "tau": 1e-3} for x in (0.005, 0.01, 0.03, 0.1)],
    "scaffold": [{}],
    "feddyn":   [{"fdyn_alpha": a} for a in (0.01, 0.05, 0.1, 0.3)],
}


def check_grid_parity():
    """Fail loudly if this grid has drifted from the one Stage A actually used."""
    import tune_hp
    if tune_hp.GRID != GRID:
        raise SystemExit(
            "tune_hp_val.GRID != tune_hp.GRID. This comparison is only "
            "valid if both sweeps use the same grid. Reconcile before running.")


def series(trace, key):
    return np.array([t[key] for t in trace], dtype=float)


def score(trace, key, vol_max, drop_max):
    """Apply the Stage A selection rule to one accuracy series."""
    a = series(trace, key)
    ref = a[int(len(a) * 0.85) - 1]
    vol = late_volatility(a)
    drop = post_peak_drop(a)
    return {
        "late_acc": float(ref),
        "peak_acc": float(a.max()),
        "final_acc": float(a[-1]),
        "last10sd": float(vol),
        "post_peak_drop": float(drop),
        "stable": bool(vol <= vol_max and drop <= drop_max),
    }


def pick(records, key):
    """Stage A rule v2: (stable, late_acc) lexicographic max."""
    if not records:
        return None
    return max(records, key=lambda r: (r[key]["stable"], r[key]["late_acc"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", default="mnist")
    ap.add_argument("--alphas", default="0.1")
    ap.add_argument("--rounds", type=int, default=40)
    ap.add_argument("--lr", type=float, default=0.05)
    ap.add_argument("--lr-decay", type=float, default=0.9, dest="lr_decay")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n-val", type=int, default=1000)
    ap.add_argument("--vol-max", type=float, default=0.01)
    ap.add_argument("--drop-max", type=float, default=5.0)
    ap.add_argument("--out-dir", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "results", "rank_inv"))
    args = ap.parse_args()

    check_grid_parity()
    os.makedirs(args.out_dir, exist_ok=True)
    t0 = time.time()
    n_run = 0

    for ds in args.datasets.split(","):
        for al in [float(x) for x in args.alphas.split(",")]:
            out_path = os.path.join(args.out_dir, f"tunedval_{ds}_a{al}.json")
            doc = {}
            if os.path.exists(out_path):
                with open(out_path, "r", encoding="utf-8") as f:
                    doc = json.load(f)

            for m, hps in GRID.items():
                settings = []
                for hp in hps:
                    label = ",".join(f"{k}={v}" for k, v in sorted(hp.items())) \
                        or "def"
                    cfg = dict(dataset=ds, arch="cnn", skew="dirichlet", alpha=al,
                               n_clients=10, rounds=args.rounds, local_epochs=1,
                               lr=args.lr, lr_decay=args.lr_decay, batch_size=64,
                               n_train=10000, n_test=2000, n_val=args.n_val,
                               seed=args.seed, method=m, _hp=label, **hp)
                    cfg["tag"] = f"valtune_{ds}_a{al}_{m}_{label}"
                    n_run += 1
                    print(f"[{n_run}] {cfg['tag']}", flush=True)
                    res = run_one(cfg)
                    tr = res["trace"]
                    rec = {
                        "hp": hp, "label": label,
                        "test": score(tr, "acc", args.vol_max, args.drop_max),
                        "val": score(tr, "val_acc", args.vol_max, args.drop_max),
                        "trace": tr,
                    }
                    settings.append(rec)
                    doc.setdefault("settings", {}).setdefault(m, [])
                    doc["settings"][m] = [s for s in doc["settings"].get(m, [])
                                          if s["label"] != label] + [rec]
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(doc, f, indent=1)

                best_test = pick(settings, "test")
                best_val = pick(settings, "val")
                doc.setdefault("selection", {})[m] = {
                    "by_test": {"hp": best_test["hp"], "label": best_test["label"],
                                **best_test["test"]},
                    "by_val": {"hp": best_val["hp"], "label": best_val["label"],
                               **best_val["val"]},
                    "agree": best_test["label"] == best_val["label"],
                    "n_settings": len(settings),
                }
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(doc, f, indent=1)
                print("  -> %-9s test=%-22s val=%-22s agree=%s"
                      % (m, best_test["label"], best_val["label"],
                         best_test["label"] == best_val["label"]), flush=True)

    print("\nDONE %d runs in %.1f min" % (n_run, (time.time() - t0) / 60.0))


if __name__ == "__main__":
    main()
