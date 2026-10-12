"""Stage A: coarse hyperparameter sweep.

Purpose
-------
Rule out the cheapest alternative explanation for any rank inversion we later
observe: that a method was simply mis-tuned. For each (dataset, alpha, method)
we evaluate a small grid and record the FULL accuracy trace of every setting,
not just its best value, because rounds-to-target curves depend on the whole
trajectory.

Selection rule
--------------
Pick the setting with the highest accuracy at a LATE reference round (85% of
the budget), not the best peak. Peak accuracy systematically favours settings
that spike and then collapse -- exactly the pathology this study is about, and
we saw it in the alpha=0.05 probe (94.70% -> 55.25%). Selecting on the peak
would hand the win to unstable methods.

Writes results/rank_inv/tuned_<dataset>_a<alpha>.json
"""
import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import methods as MS
from rank_inv_runner import run_one
from analyze_rank_inv import late_volatility, post_peak_drop

# Coarse but deliberately wide: enough to be fair, small enough for CPU.
GRID = {
    "fedavg":   [{}],
    "uniform":  [{}],
    "fedavgm":  [{"beta": b, "lr_s": 1.0} for b in (0.5, 0.7, 0.9, 0.95)],
    "fedproxw": [{"rho": r} for r in (0.2, 0.5, 0.8)],
    "fedadam":  [{"lr_s": x, "tau": 1e-3} for x in (0.005, 0.01, 0.03, 0.1)],
    "scaffold": [{}],
    "feddyn":   [{"fdyn_alpha": a} for a in (0.01, 0.05, 0.1, 0.3)],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", default="mnist,fashion")
    ap.add_argument("--alphas", default="0.1")
    ap.add_argument("--rounds", type=int, default=40)
    ap.add_argument("--lr", type=float, default=0.05)
    ap.add_argument("--lr-decay", type=float, default=0.9)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--vol-max", type=float, default=0.01,
                    help="a hyperparameter setting counts as settled below this "
                         "last-10-round std")
    ap.add_argument("--drop-max", type=float, default=5.0,
                    help="... and below this post-peak accuracy loss, in points")
    ap.add_argument("--out-dir", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "results", "rank_inv"))
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    t0 = time.time()
    total = 0

    for ds in args.datasets.split(","):
        for al in [float(x) for x in args.alphas.split(",")]:
            out_path = os.path.join(args.out_dir, f"tuned_{ds}_a{al}.json")
            tuned = {}
            if os.path.exists(out_path):
                with open(out_path, "r", encoding="utf-8") as f:
                    tuned = json.load(f)

            for m, hps in GRID.items():
                best = None
                for hp in hps:
                    key = f"{ds}|{al}|{m}"
                    label = ",".join(f"{k}={v}" for k, v in sorted(hp.items())) or "def"
                    if key in tuned and tuned[key].get("label") == label:
                        continue
                    cfg = dict(dataset=ds, arch="cnn", skew="dirichlet", alpha=al,
                               n_clients=10, rounds=args.rounds, local_epochs=1,
                               lr=args.lr, lr_decay=args.lr_decay, batch_size=64,
                               n_train=10000, n_test=2000, seed=args.seed,
                               method=m, _hp=label, **hp)
                    cfg["tag"] = f"tune_{ds}_a{al}_{m}_{label}"
                    total += 1
                    print(f"[{total}] {cfg['tag']}", flush=True)
                    res = run_one(cfg)
                    tr = res["trace"]
                    ref = tr[int(len(tr) * 0.85) - 1]["acc"]
                    acc = np.array([x["acc"] for x in tr], dtype=float)
                    vol = late_volatility(acc)
                    drop = post_peak_drop(acc)
                    stable = vol <= args.vol_max and drop <= args.drop_max
                    rec = {"hp": hp, "label": label, "late_acc": ref,
                           "peak_acc": max(x["acc"] for x in tr),
                           "final_acc": tr[-1]["acc"], "trace": tr,
                           "last10sd": vol, "post_peak_drop": drop,
                           "stable": stable}
                    # Selection rule v2: prefer a STABLE setting even if its
                    # late-round accuracy is slightly lower. The old rule picked
                    # the raw max of a single late sample, and that single sample
                    # can be a lucky phase of an oscillating run -- we proved this
                    # the hard way: Stage A chose feddyn fdyn_alpha=0.3 (late
                    # 0.6915) although its FINAL accuracy (0.6670) was worse than
                    # fdyn_alpha=0.05 (0.7300), because 0.3 merely happened to be
                    # at a high point of its oscillation when sampled.
                    # A single-sample score shares the exact defect this whole
                    # study is about, so the tuner must not repeat it.
                    key_of = lambda r: (r["stable"], r["late_acc"])
                    if best is None or key_of(rec) > key_of(best):
                        best = rec
                    tuned.setdefault(key, {})["settings"] = \
                        tuned.get(key, {}).get("settings", []) + [rec]
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(tuned, f, indent=1)

                if best is not None:
                    tuned[f"{ds}|{al}|{m}"] = {
                        "best_hp": best["hp"], "label": best["label"],
                        "late_acc": best["late_acc"],
                        "peak_acc": best["peak_acc"],
                        "final_acc": best["final_acc"],
                        "settings": tuned.get(f"{ds}|{al}|{m}", {}).get("settings", []),
                    }
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(tuned, f, indent=1)
                    print(f"  -> {m}: {best['label']}  late={best['late_acc']*100:.2f}%  "
                          f"peak={best['peak_acc']*100:.2f}%  "
                          f"final={best['final_acc']*100:.2f}%", flush=True)

    print(f"\nDONE {total} runs in {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
