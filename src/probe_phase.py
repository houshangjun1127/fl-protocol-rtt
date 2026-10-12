"""Diagnostic probe for the 'aggressiveness schedule' direction.

WHAT THIS DOES NOT DO
---------------------
It does not propose a method. It measures, on a plain FedAvg run, whether the
structural premise behind every 'early = conservative, late = aggressive'
schedule actually holds, and records which server-observable signals track it.

WHY
---
Three independent papers state that the optimal amount of server-side
aggressiveness should be LOW early and HIGH late:
  - FedCAda   : damping 1+beta^t, large early (conservative), decaying late
  - FedaGrac  : "increasing lambda schedule, low calibration first"
  - FLASH     : clients needing MORE local epochs signals drift
All three hand-design the schedule. FedaGrac explicitly leaves "how to determine
the optimal schedule" open. So the premise is claimed but never *measured*.

If the premise is false here, the direction dies before any method is designed.
That is the cheapest possible kill, so we try it first.

SIGNALS RECORDED PER ROUND (all computable server-side, no extra comms)
---------------------------------------------------------------------
consensus_cos   mean_k cos(d_k, S_t)          : directional agreement
cancel_ratio    1 - ||sum w_k d_k|| / sum w_k||d_k||  : how much averaging
                                                  cancels vs reinforces
norm_ratio      ||S_t|| / mean_k||d_k||      : shrinkage under averaging
round_cos       cos(S_t, S_{t-1})             : inter-round direction stability
majority_share  corr path: not recorded here (needs label histograms)
top1_cos        cos of the largest-norm client with the consensus
                 : is the consensus driven by one dominant client?
drift_proxy     ||S_t||^2 / sum_k w_k||d_k||^2 : 1-cancel_ratio, for reference

Local diagnostics: mean local loss already logged by fedcore.
"""
import argparse
import json
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data import load_dataset, dirichlet_partition, quantity_skew_partition, loader
from models import build_model
from fedcore import evaluate, local_train
import aggregate as A


def probe(cfg):
    torch.manual_seed(cfg["seed"])
    np.random.seed(cfg["seed"])

    train_ds, test_ds, ch, size = load_dataset(
        cfg["dataset"], cfg["n_train"], cfg["n_test"], seed=cfg["seed"])
    labels = np.array(train_ds.tensors[1])
    n_classes = int(labels.max()) + 1

    if cfg["skew"] == "dirichlet":
        parts = dirichlet_partition(labels, cfg["n_clients"], cfg["alpha"], seed=cfg["seed"])
    elif cfg["skew"] == "quantity":
        parts = quantity_skew_partition(labels, cfg["n_clients"], seed=cfg["seed"])
    else:
        rng = np.random.RandomState(cfg["seed"])
        parts = [np.sort(p) for p in np.split(rng.permutation(len(labels)), cfg["n_clients"])]

    model = build_model(cfg["arch"], ch, size, n_classes)
    gmodel = build_model(cfg["arch"], ch, size, n_classes)
    gmodel.load_state_dict(model.state_dict())
    nk = [len(p) for p in parts]

    hist = []
    prev_S = None

    for rnd in range(cfg["rounds"]):
        deltas, lls = [], []
        for k, idx in enumerate(parts):
            model.load_state_dict(gmodel.state_dict())
            d, l, n = local_train(
                model, train_ds, idx, cfg["local_epochs"], cfg["lr"],
                cfg["batch_size"], mu=0.0,
                global_flat=None, seed=cfg["seed"] * 1000 + rnd * 100 + k)
            deltas.append(d)
            lls.append(l)

        D = torch.stack(deltas)                    # [K,d]
        w = A._norm(torch.tensor(nk, dtype=torch.float))
        S = w @ D                                  # [d] FedAvg direction

        norms = D.norm(dim=1)                      # [K]
        sum_w_norm = float((w * norms).sum())
        S_norm = float(S.norm())

        cosk = torch.nn.functional.cosine_similarity(D, S.unsqueeze(0), dim=1)
        j = int(torch.argmax(norms))
        row = {
            "round": rnd + 1,
            "consensus_cos": float(cosk.mean()),
            "cos_std": float(cosk.std()),
            "cos_min": float(cosk.min()),
            "frac_cos_neg": float((cosk < 0).float().mean()),
            "cancel_ratio": 1.0 - (S_norm / (sum_w_norm + 1e-12)),
            "norm_ratio": S_norm / (sum_w_norm + 1e-12),
            "round_cos": (float(torch.nn.functional.cosine_similarity(
                S.unsqueeze(0), prev_S.unsqueeze(0), dim=1)[0])
                if prev_S is not None else None),
            "top1_cos": float(cosk[j]),
            "top1_norm_share": float(w[j] * norms[j] / (sum_w_norm + 1e-12)),
            "mean_local_loss": float(np.mean(lls)),
        }

        flat = torch.cat([p.detach().reshape(-1) for p in gmodel.parameters()])
        new_flat = flat + S
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
        row["test_acc"] = acc
        hist.append(row)
        prev_S = S.clone()

        print(f"  r{rnd+1:3d} acc={acc*100:5.2f}%  cos={row['consensus_cos']:+.4f}  "
              f"neg={row['frac_cos_neg']:.2f}  cancel={row['cancel_ratio']:.4f}  "
              f"rcos={('%.4f' % row['round_cos']) if row['round_cos'] is not None else '  na  '}  "
              f"top1cos={row['top1_cos']:+.3f}", flush=True)

    return {"cfg": cfg, "history": hist}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="mnist")
    ap.add_argument("--alpha", type=float, default=0.1)
    ap.add_argument("--skew", default="dirichlet")
    ap.add_argument("--rounds", type=int, default=30)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n-clients", type=int, default=10)
    ap.add_argument("--lr", type=float, default=0.05)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cfg = dict(dataset=args.dataset, arch="cnn", skew=args.skew, alpha=args.alpha,
               n_clients=args.n_clients, rounds=args.rounds, local_epochs=1,
               lr=args.lr, batch_size=64, n_train=10000, n_test=2000,
               seed=args.seed, mu=0.0)
    cfg["tag"] = (f"probe_{cfg['dataset']}_a{cfg['alpha']}_{cfg['skew']}"
                  f"_s{cfg['seed']}_r{cfg['rounds']}")
    print(f"== probe {cfg['tag']} ==", flush=True)
    res = probe(cfg)

    out = args.out or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "results",
        f"probe_{cfg['dataset']}_a{cfg['alpha']}_{cfg['skew']}_s{cfg['seed']}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(f"DONE -> {out}")


if __name__ == "__main__":
    main()
