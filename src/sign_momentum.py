"""Sign test: is the late phase noise-dominated?

The probe showed, on plain FedAvg and across four configurations:
  - cancel_ratio rises monotonically (0.25-0.42 -> 0.63-0.80)
  - round_cos falls, and becomes NEGATIVE late in training on FashionMNIST
i.e. late-round global updates are mutually cancelling and inter-round
directions are unstable. If that reading is right, then server-side momentum
-- which averages recent global directions -- should make the LATE phase WORSE,
not better. That is the opposite of the "conservative early, aggressive late"
schedule that FedCAda / FedaGrac / FLASH all hand-design.

This script runs server momentum with a beta sweep and records the accuracy
trajectory, split into early/mid/late thirds. It is a SIGN test, not a method:
we are checking whether the predicted failure appears, before proposing
anything to fix it.

beta = 0 reduces exactly to FedAvg (invariant check, must pass).
"""
import argparse
import json
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data import load_dataset, dirichlet_partition, loader
from models import build_model
from fedcore import evaluate, local_train
import aggregate as A


def run(cfg):
    torch.manual_seed(cfg["seed"])
    np.random.seed(cfg["seed"])

    train_ds, test_ds, ch, size = load_dataset(
        cfg["dataset"], cfg["n_train"], cfg["n_test"], seed=cfg["seed"])
    labels = np.array(train_ds.tensors[1])
    n_classes = int(labels.max()) + 1
    parts = dirichlet_partition(labels, cfg["n_clients"], cfg["alpha"], seed=cfg["seed"])

    model = build_model(cfg["arch"], ch, size, n_classes)
    gmodel = build_model(cfg["arch"], ch, size, n_classes)
    gmodel.load_state_dict(model.state_dict())
    nk = [len(p) for p in parts]

    beta = cfg["beta"]
    mom = None
    hist = []

    for rnd in range(cfg["rounds"]):
        deltas = []
        for k, idx in enumerate(parts):
            model.load_state_dict(gmodel.state_dict())
            d, l, n = local_train(
                model, train_ds, idx, cfg["local_epochs"], cfg["lr"],
                cfg["batch_size"], mu=0.0,
                global_flat=None, seed=cfg["seed"] * 1000 + rnd * 100 + k)
            deltas.append(d)

        S = A._norm(torch.tensor(nk, dtype=torch.float)) @ torch.stack(deltas)

        # server momentum on the global direction
        if mom is None:
            mom = S.clone()
        else:
            mom = beta * mom + S
        step = mom if beta > 0 else S

        flat = torch.cat([p.detach().reshape(-1) for p in gmodel.parameters()])
        new_flat = flat + step
        i = 0
        sd = {}
        for k, v in gmodel.state_dict().items():
            if v.dtype.is_floating_point and k in dict(gmodel.named_parameters()):
                sd[k] = new_flat[i:i + v.numel()].view_as(v)
                i += v.numel()
            else:
                sd[k] = v
        gmodel.load_state_dict(sd)

        acc, tl = evaluate(gmodel, test_ds)
        hist.append({"round": rnd + 1, "test_acc": acc, "test_loss": tl,
                     "step_norm": float(step.norm())})
        print(f"  [b={beta:.2f}] r{rnd+1:3d} acc={acc*100:5.2f}% "
              f"|step|={float(step.norm()):.4f}", flush=True)

    return {"cfg": cfg, "history": hist}


def thirds(hist):
    """mean / max accuracy in each third of training."""
    n = len(hist)
    a = np.array([h["test_acc"] for h in hist])
    seg = []
    for i in range(3):
        lo, hi = i * n // 3, (i + 1) * n // 3
        seg.append({"mean": float(a[lo:hi].mean()),
                    "max": float(a[lo:hi].max()),
                    "final": float(a[hi - 1])})
    return seg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="fashion")
    ap.add_argument("--alpha", type=float, default=0.1)
    ap.add_argument("--rounds", type=int, default=30)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--betas", default="0.0,0.5,0.9")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    out = args.out or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "results",
        f"momentum_sign_{args.dataset}_a{args.alpha}_s{args.seed}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    results = []
    for b in [float(x) for x in args.betas.split(",")]:
        cfg = dict(dataset=args.dataset, arch="cnn", skew="dirichlet",
                   alpha=args.alpha, n_clients=10, rounds=args.rounds,
                   local_epochs=1, lr=0.05, batch_size=64, n_train=10000,
                   n_test=2000, seed=args.seed, mu=0.0, beta=b)
        cfg["tag"] = f"mom_b{b}_{args.dataset}_a{args.alpha}_s{args.seed}"
        print(f"== beta={b} ==", flush=True)
        res = run(cfg)
        res["segments"] = thirds(res["history"])
        results.append(res)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=1)
        s = res["segments"]
        print(f"   beta={b:.2f}  early {s[0]['mean']*100:.2f}  "
              f"mid {s[1]['mean']*100:.2f}  late {s[2]['mean']*100:.2f}  "
              f"final {res['history'][-1]['test_acc']*100:.2f}", flush=True)

    print(f"\nDONE -> {out}")


if __name__ == "__main__":
    main()
