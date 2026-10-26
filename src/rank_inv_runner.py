"""Rank-inversion study: does "rounds-to-target-accuracy" depend on the target?

DESIGN
------
The observation that triggered this study (results/negative_results.md 3.5):
on FashionMNIST a0.1, beta=0.5 reached 75% in 13 rounds and beta=0.9 in 15;
but at 80% the order flipped to 26 vs 21. A single data point. Before claiming
a construction defect in the metric we must rule out the cheap explanations:

  (a) BAD HYPERPARAMETERS -- an inversion could just mean beta=0.5 was
      mis-tuned. -> Stage A does a coarse sweep first and uses the tuned value.
  (b) NOISE / SINGLE SEED -- -> Stage B uses 4 seeds and reports the
      fraction of (dataset, seed) cells that invert.
  (c) COARSE TARGET GRID -- -> accuracy is recorded EVERY round and targets are
      swept on a dense grid, not evaluated at two hand-picked thresholds.
  (d) NEAR-TIE AMBIGUITY -- a 13-vs-15 gap could be within noise. -> we report
      Kendall tau and the size of every inversion, and mark near-ties.

Only if inversions survive (a)-(d) is the metric claim warranted.

WHY IT MATTERS
--------------
"Fewer rounds to reach accuracy X" is the headline efficiency claim across the
federated learning literature. If the ranking of methods changes with X, then
the reported ordering is partly an artifact of an under-specified metric, and
cross-paper comparison of efficiency claims is unsound.

OUTPUT
------
results/rank_inv/<tag>.json  with the full per-round accuracy trace, so any
target grid can be recomputed without re-running training.
"""
import argparse
import itertools
import json
import os
import sys
import time

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data import (load_dataset, load_dataset_with_val, dirichlet_partition,
                  loader)
from models import build_model
from fedcore import evaluate
import methods as MS

torch.set_num_threads(int(os.getenv("FL_THREADS", "2")))
# NOTE: the original hard-coded 2 assumed many configs ran in parallel. Our
# queues run SEQUENTIALLY, so one job owns the whole 8C/16T CPU and 2 threads
# wastes ~85% of it. Default kept at 2 for backward compatibility with the 112
# already-completed Stage B runs; verify numerical equivalence before raising.


def local_train_ext(model, ds, idx, epochs, lr, batch_size,
                    c_glob=None, c_i=None, h_i=None, alpha=0.0, seed=0):
    """Local training with optional SCAFFOLD control variate / FedDyn h.

    All three flat tensors (c_glob, c_i, h_i, w, grad) are laid out in
    `model.parameters()` order -- the same order used by fedcore's
    get_flat_grad and by the delta vector in run_one. Mixing named_parameters()
    ordering with parameters() ordering silently misaligns the slices.

    Returns (flat_update, mean_loss).
      SCAFFOLD: grad <- grad - c_i + c
      FedDyn  : grad <- grad - h_i + alpha*(w - w_t)
    """
    g = torch.Generator().manual_seed(seed)
    model.train()
    w0 = [p.detach().clone() for p in model.parameters()]
    plist = list(model.parameters())
    use_scaf = c_i is not None
    use_dyn = h_i is not None

    def flat_grad():
        return torch.cat([(p.grad if p.grad is not None
                           else torch.zeros_like(p)).reshape(-1) for p in plist])

    opt = torch.optim.SGD(plist, lr=lr, momentum=0.0)
    losses = []
    for _ in range(epochs):
        for x, y in loader(ds, idx, batch_size, shuffle=True, gen=g):
            opt.zero_grad()
            loss = torch.nn.functional.cross_entropy(model(x), y)
            loss.backward()

            if use_scaf or use_dyn:
                cur = torch.cat([p.detach().reshape(-1) for p in plist])
                gc = flat_grad()
                if use_scaf:
                    gc = gc - c_i + c_glob
                if use_dyn:
                    gc = gc - h_i + alpha * (cur - w0_cat(plist, w0))
                off = 0
                for p in plist:
                    num = p.numel()
                    p.grad.copy_(gc[off:off + num].view_as(p))
                    off += num

            opt.step()
            losses.append(loss.item())

    delta = torch.cat([(p.detach() - w0[k]).reshape(-1)
                       for k, p in enumerate(plist)])
    return delta, float(np.mean(losses)) if losses else 0.0


def w0_cat(plist, w0):
    return torch.cat([t.reshape(-1) for t in w0])


def run_one(cfg):
    """Train one (dataset, alpha, seed, method) combo, record acc EVERY round.

    Learning-rate schedule applies IDENTICALLY to every method. SCAFFOLD needs
    a decaying lr to stay stable late in training (verified: const-lr peaks at
    78.95% then oscillates 58-79%; exp decay reaches 91.30%). Giving only
    SCAFFOLD a decay would be an unfair comparison, so it is global.
    """
    torch.manual_seed(cfg["seed"])
    np.random.seed(cfg["seed"])

    # R10 (second-round review). When n_val > 0 we additionally build a
    # validation split and evaluate on it every round, recording `val_acc`
    # alongside `acc`. The train/test subsamples are bit-identical to the
    # published runs (asserted in data.load_dataset_with_val), so existing
    # numbers are untouched and the extra key is purely additive.
    n_val = int(cfg.get("n_val", 0) or 0)
    if n_val > 0:
        train_ds, val_ds, test_ds, ch, size = load_dataset_with_val(
            cfg["dataset"], cfg.get("n_train", 10000), cfg.get("n_test", 2000),
            n_val, seed=cfg["seed"])
    else:
        val_ds = None
        train_ds, test_ds, ch, size = load_dataset(
            cfg["dataset"], cfg.get("n_train", 10000), cfg.get("n_test", 2000),
            seed=cfg["seed"])
    labels = np.array(train_ds.tensors[1])
    n_classes = int(labels.max()) + 1
    parts = dirichlet_partition(labels, cfg["n_clients"], cfg["alpha"],
                                seed=cfg["seed"])
    nk = [len(p) for p in parts]

    model = build_model(cfg["arch"], ch, size, n_classes)
    gmodel = build_model(cfg["arch"], ch, size, n_classes)
    gmodel.load_state_dict(model.state_dict())
    d = sum(p.numel() for p in gmodel.parameters())

    spec = MS.METHODS[cfg["method"]]
    kw = {k: v for k, v in cfg.items()
          if k in ("beta", "lr_s", "rho", "beta1", "beta2", "tau", "fdyn_alpha")}
    state = None
    ci = None
    if cfg["method"] in ("scaffold", "feddyn"):
        state = torch.zeros(d)
        ci = [torch.zeros(d) for _ in parts]

    lr_decay = float(cfg.get("lr_decay", 0.9))
    trace = []
    t0 = time.time()

    for rnd in range(cfg["rounds"]):
        lr_t = cfg["lr"] * (lr_decay ** rnd)
        deltas, lls = [], []
        for k, idx in enumerate(parts):
            model.load_state_dict(gmodel.state_dict())
            dvec, l = local_train_ext(
                model, train_ds, idx, cfg["local_epochs"], lr_t,
                cfg["batch_size"],
                c_glob=state if cfg["method"] == "scaffold" else None,
                c_i=ci[k] if cfg["method"] == "scaffold" else None,
                h_i=ci[k] if cfg["method"] == "feddyn" else None,
                alpha=cfg.get("fdyn_alpha", 0.1) if cfg["method"] == "feddyn" else 0.0,
                seed=cfg["seed"] * 1000 + rnd * 100 + k)
            # ---- per-client state updates
            if cfg["method"] == "scaffold":
                # SCAFFOLD (option II): c_i^+ = c_i - c + (w_t - w_i)/(K*eta).
                # K is the TOTAL local SGD steps in the round, not local_epochs.
                # Using local_epochs inflates c ~15x on MNIST -> NaN by round 3.
                Kk = max(1, -(-len(idx) // cfg["batch_size"])) * cfg["local_epochs"]
                ci[k] = ci[k] - state - dvec / max(lr_t * Kk, 1e-8)
            elif cfg["method"] == "feddyn":
                ci[k] = ci[k] - cfg.get("fdyn_alpha", 0.1) * dvec
            deltas.append(dvec)
            lls.append(l)

        if cfg["method"] == "scaffold":
            w = MS._norm(torch.tensor(nk, dtype=torch.float))
            avg_ci = sum(ci) / len(ci)
            state = avg_ci                       # c_new = mean of c_i
            step = w @ torch.stack(deltas)       # step along pseudo-gradient
        elif cfg["method"] == "feddyn":
            w = MS._norm(torch.tensor(nk, dtype=torch.float))
            state = w @ torch.stack(ci)          # sum_k p_k h_k
            step = -state / cfg.get("fdyn_alpha", 0.1)
        else:
            step, state = spec["fn"](state, deltas, nk, rnd, **kw)

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
        rec = {"round": rnd + 1, "acc": acc, "loss": tl,
               "local_loss": float(np.mean(lls))}
        if val_ds is not None:
            vacc, _v = evaluate(gmodel, val_ds)
            rec["val_acc"] = vacc
        trace.append(rec)

    return {"cfg": cfg, "trace": trace, "wall": time.time() - t0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", default="mnist,fashion")
    ap.add_argument("--alphas", default="0.1")
    ap.add_argument("--seeds", default="0,1,2,3")
    ap.add_argument("--methods", default="")
    ap.add_argument("--rounds", type=int, default=60)
    ap.add_argument("--lr", type=float, default=0.05)
    # Kept explicit rather than relying on cfg.get("lr_decay", 0.9) inside
    # run_one(). Default is unchanged (0.9) so all previously produced results
    # stay valid; the point of the flag is that Stage B's decay must not depend
    # on an invisible default in a study about invisible protocol choices.
    ap.add_argument("--lr-decay", type=float, default=0.9, dest="lr_decay")
    ap.add_argument("--out-dir", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "results", "rank_inv"))
    ap.add_argument("--stage", default="main")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    datasets = args.datasets.split(",")
    alphas = [float(x) for x in args.alphas.split(",")]
    seeds = [int(x) for x in args.seeds.split(",")]

    if args.methods:
        methods = args.methods.split(",")
    elif args.stage == "tune":
        methods = ["fedavg", "fedavgm", "fedproxw", "fedadam", "scaffold", "feddyn"]
    else:
        methods = ["fedavg", "uniform", "fedavgm", "fedproxw", "fedadam",
                   "scaffold", "feddyn"]

    grid = list(itertools.product(datasets, alphas, seeds, methods))
    print(f"stage={args.stage}  {len(grid)} configs", flush=True)

    # Resume index: collect the tag of every run already present on disk.
    #
    # BUGFIX (2026-10-09). The previous version did `for r in json.load(fh)`.
    # Files written by THIS script are objects ({cfg, trace, wall}), and the
    # tuned_*.json files are objects too, so `for r in <dict>` iterated over
    # *string keys*; `r["cfg"]` then raised TypeError, which the bare
    # `except Exception: pass` swallowed. Result: `done` was ALWAYS empty and
    # nothing was ever skipped -- the resume feature silently never worked.
    # Now each file is normalised to a list of candidate records and only
    # records that actually carry a cfg are indexed, so unparseable or foreign
    # files no longer mask real ones.
    done = set()
    n_scanned = 0
    for f in os.listdir(args.out_dir):
        if not f.endswith(".json"):
            continue
        try:
            with open(os.path.join(args.out_dir, f), "r", encoding="utf-8") as fh:
                doc = json.load(fh)
        except Exception:
            continue
        cands = doc if isinstance(doc, list) else [doc]
        for r in cands:
            c = r.get("cfg") if isinstance(r, dict) else None
            if not isinstance(c, dict):
                continue
            try:
                done.add(f"{c['dataset']}_a{c['alpha']}_{c['method']}"
                         f"_{c.get('_hp', 'def')}_s{c['seed']}")
                n_scanned += 1
            except KeyError:
                continue
    if done:
        print(f"resume: {n_scanned} existing runs indexed "
              f"({len(done)} unique tags)", flush=True)
    t0 = time.time()
    for i, (ds, al, sd, m) in enumerate(grid):
        hp = MS.METHODS[m]
        cfg = dict(dataset=ds, arch="cnn", skew="dirichlet", alpha=al,
                   n_clients=10, rounds=args.rounds, local_epochs=1,
                   lr=args.lr, lr_decay=args.lr_decay, batch_size=64,
                   n_train=10000, n_test=2000,
                   seed=sd, method=m)
        # tuned coefficients come from the sweep file if it exists
        tuned = os.path.join(args.out_dir, f"tuned_{ds}_a{al}.json")
        if os.path.exists(tuned):
            with open(tuned, "r", encoding="utf-8") as fh:
                tun = json.load(fh)
            key = f"{ds}|{al}|{m}"
            if key in tun:
                for k, v in tun[key]["best_hp"].items():
                    cfg[k] = v
                cfg["_hp"] = tun[key]["label"]
        tag = (f"{ds}_a{al}_{m}_{cfg.get('_hp','def')}_s{sd}")
        if tag in done:
            print(f"skip {tag}", flush=True)
            continue
        print(f"[{i+1}/{len(grid)}] {tag}", flush=True)
        res = run_one(cfg)
        with open(os.path.join(args.out_dir, tag + ".json"), "w",
                  encoding="utf-8") as fh:
            json.dump(res, fh, indent=1)
        best = max(t["acc"] for t in res["trace"])
        print(f"   final {res['trace'][-1]['acc']*100:.2f}%  "
              f"best {best*100:.2f}%  ({res['wall']:.0f}s, "
              f"total {(time.time()-t0)/60:.1f}min)", flush=True)

    print(f"\nDONE in {(time.time()-t0)/60:.1f} min -> {args.out_dir}")


if __name__ == "__main__":
    main()
