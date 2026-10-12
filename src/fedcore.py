"""Federated training loop (CPU). Server-side aggregation is pluggable."""
import json
import os
import time
import copy
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from data import load_dataset, dirichlet_partition, quantity_skew_partition, loader, TensorSubset
from models import build_model, param_blocks, get_flat_grad
from aggregate import build_block_index
import aggregate as A

torch.set_num_threads(max(1, (os.cpu_count() or 4) - 1))


def evaluate(model, test_ds, batch_size=256):
    model.eval()
    correct = tot = 0
    loss_sum = 0.0
    with torch.no_grad():
        for x, y in loader(test_ds, np.arange(len(test_ds)), batch_size, shuffle=False):
            out = model(x)
            loss_sum += F.cross_entropy(out, y, reduction="sum").item()
            correct += (out.argmax(1) == y).sum().item()
            tot += y.numel()
    return correct / tot, loss_sum / tot


def per_class_accuracy(model, test_ds, n_classes, batch_size=256):
    model.eval()
    correct = np.zeros(n_classes)
    total = np.zeros(n_classes)
    with torch.no_grad():
        for x, y in loader(test_ds, np.arange(len(test_ds)), batch_size, shuffle=False):
            pred = model(x).argmax(1)
            for c in range(n_classes):
                m = (y == c)
                total[c] += m.sum().item()
                correct[c] += ((pred == c) & m).sum().item()
    return np.divide(correct, np.maximum(total, 1))


def local_train(model, ds, idx, epochs, lr, batch_size, mu=0.0, global_flat=None, seed=0):
    """Return (flat update, mean local loss, n_k)."""
    g = torch.Generator().manual_seed(seed)
    model.train()
    n_k = len(idx)
    w0 = {k: v.detach().clone() for k, v in model.named_parameters()}
    opt = torch.optim.SGD(model.parameters(), lr=lr, momentum=0.0)
    losses = []
    for _ in range(epochs):
        for x, y in loader(ds, idx, batch_size, shuffle=True, gen=g):
            opt.zero_grad()
            loss = F.cross_entropy(model(x), y)
            if mu > 0 and global_flat is not None:
                cur = get_flat_grad(model)
                prox = 0.5 * mu * (cur - global_flat).pow(2).sum()
                loss = loss + prox
            loss.backward()
            opt.step()
            losses.append(loss.item())
    delta = torch.cat([
        (p.detach() - w0[n]).reshape(-1) for n, p in model.named_parameters()
    ])
    return delta, float(np.mean(losses)) if losses else 0.0, n_k


def run_federated(cfg):
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
    blocks = param_blocks(model)
    bidx = build_block_index(dict(model.named_parameters()), blocks)
    gmodel = build_model(cfg["arch"], ch, size, n_classes)
    gmodel.load_state_dict(model.state_dict())

    nk = [len(p) for p in parts]
    method = cfg["method"]
    hist = []
    t0 = time.time()

    # --- PriorGap setup: client label histograms (C floats per client, sent once) ---
    tau_cal = float(cfg.get("tau_cal", 0.0))
    H = None
    if method == "priorcal" or cfg.get("calibrate", False):
        from prior_calib import class_histogram, prior_gap
        H = np.stack([class_histogram(labels, p, n_classes) for p in parts])
        gap = prior_gap(H, nk, n_classes)

    for rnd in range(cfg["rounds"]):
        deltas, lls = [], []
        for k, idx in enumerate(parts):
            model.load_state_dict(gmodel.state_dict())
            d, l, n = local_train(
                model, train_ds, idx, cfg["local_epochs"], cfg["lr"],
                cfg["batch_size"], mu=cfg.get("mu", 0.0),
                global_flat=None, seed=cfg["seed"] * 1000 + rnd * 100 + k)
            deltas.append(d)
            lls.append(l)

        if method == "priorcal":
            agg = A.agg_fedavg(deltas, nk, blocks, bidx)
        elif method in A.REGISTRY:
            kw = dict(blocks=blocks, bidx=bidx)
            if method == "cfa":
                kw.update(gamma=cfg.get("gamma", 2.0), lam=cfg.get("lam", 0.5),
                          variant=cfg.get("variant", "full"),
                          warmup=cfg.get("warmup", 0), rnd=rnd)
            if method == "fedproxw":
                kw.update(rho=cfg.get("rho", 0.5))
            agg = A.REGISTRY[method](deltas, nk, **kw)
        else:
            raise ValueError(method)

        # w_{t+1} = w_t + agg
        flat = torch.cat([p.detach().reshape(-1) for p in gmodel.parameters()])
        new_flat = flat + agg
        i = 0
        sd = {}
        for k, v in gmodel.state_dict().items():
            if v.dtype.is_floating_point and k in dict(gmodel.named_parameters()):
                sd[k] = new_flat[i:i + v.numel()].view_as(v)
                i += v.numel()
            else:
                sd[k] = v
        gmodel.load_state_dict(sd)

        # --- PriorGap: re-centre the head on the true global prior ---
        if H is not None and tau_cal > 0:
            from prior_calib import apply_bias_correction
            # Recomputed each round: client partitions are static here, so the
            # gap is constant, but we re-derive it to stay correct if the
            # partition changes (e.g. per-round client sampling).
            gap_t = prior_gap(H, nk, n_classes)
            apply_bias_correction(gmodel, gap_t, tau_cal)

        if (rnd + 1) % cfg["eval_every"] == 0 or rnd == cfg["rounds"] - 1:
            acc, tl = evaluate(gmodel, test_ds)
            hist.append({"round": rnd + 1, "test_acc": acc, "test_loss": tl,
                         "mean_local_loss": float(np.mean(lls)),
                         "elapsed": time.time() - t0})
            print(f"  [{cfg['tag']}] round {rnd+1:3d}  acc={acc*100:.2f}%  "
                  f"loss={tl:.4f}  local={np.mean(lls):.4f}  "
                  f"({time.time()-t0:.0f}s)", flush=True)

    final_pca = per_class_accuracy(gmodel, test_ds, n_classes)
    return {"cfg": cfg, "history": hist, "final_acc": hist[-1]["test_acc"],
            "worst_class_acc": float(final_pca.min()), "pca": final_pca.tolist(),
            "n_classes": n_classes, "wall_time": time.time() - t0}