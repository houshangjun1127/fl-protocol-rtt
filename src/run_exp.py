"""Experiment driver: run the benchmark grid and dump results to JSON."""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fedcore import run_federated

BASE = dict(
    dataset="mnist", arch="cnn", skew="dirichlet", alpha=0.1,
    n_clients=10, rounds=30, local_epochs=1, lr=0.05, batch_size=64,
    n_train=10000, n_test=2000, seed=0, mu=0.0,
    gamma=2.0, lam=0.5, rho=0.5, eval_every=5,
)

METHODS = {
    "fedavg":     dict(method="fedavg"),
    "uniform":    dict(method="uniform"),
    "fedproxw":   dict(method="fedproxw", rho=0.5),
    "cfa":        dict(method="cfa", variant="full"),
    "cfa_align":  dict(method="cfa", variant="align"),
    "cfa_proj":   dict(method="cfa", variant="proj"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="smoke")
    ap.add_argument("--out", default=None)
    ap.add_argument("--methods", default="all")
    args = ap.parse_args()

    if args.methods == "all":
        methods = list(METHODS)
    else:
        methods = args.methods.split(",")

    if args.suite == "smoke":
        grid = [dict(dataset="mnist", alpha=0.1, rounds=10, seed=0, eval_every=5)]
    elif args.suite == "main":
        grid = []
        for ds in ["mnist", "fashion"]:
            for alpha in [0.05, 0.1, 0.3, 1.0]:
                for seed in [0, 1, 2]:
                    grid.append(dict(dataset=ds, alpha=alpha, seed=seed, rounds=30))
    elif args.suite == "skew":
        grid = [dict(dataset="mnist", skew="iid", rounds=30, seed=0),
                dict(dataset="mnist", skew="quantity", rounds=30, seed=0),
                dict(dataset="mnist", skew="dirichlet", alpha=0.05, rounds=30, seed=0),
                dict(dataset="mnist", skew="dirichlet", alpha=0.3, rounds=30, seed=0),
                dict(dataset="mnist", skew="dirichlet", alpha=1.0, rounds=30, seed=0)]
    else:
        raise SystemExit(f"unknown suite {args.suite}")

    out_path = args.out or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "results", f"{args.suite}.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    results = []
    if os.path.exists(out_path):
        with open(out_path, "r", encoding="utf-8") as f:
            results = json.load(f)

    done = {(r["cfg"]["tag"]) for r in results}
    t0 = time.time()
    for g in grid:
        for m in methods:
            cfg = dict(BASE)
            cfg.update(g)
            cfg.update(METHODS[m])
            tag = f"{cfg['dataset']}_a{cfg.get('alpha')}_{cfg['skew']}_{m}_s{cfg['seed']}_r{cfg['rounds']}"
            cfg["tag"] = tag
            if tag in done:
                print(f"skip {tag}", flush=True)
                continue
            print(f"== run {tag} ==", flush=True)
            res = run_federated(cfg)
            res["method_key"] = m
            results.append(res)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=1)
            print(f"   -> acc {res['final_acc']*100:.2f}%  "
                  f"worst-class {res['worst_class_acc']*100:.2f}%  "
                  f"({res['wall_time']:.0f}s, total {time.time()-t0:.0f}s)", flush=True)

    print(f"\nDONE -> {out_path}")


if __name__ == "__main__":
    main()