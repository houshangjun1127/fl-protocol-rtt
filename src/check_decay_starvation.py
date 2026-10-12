"""Does SCAFFOLD's collapse on CIFAR-10 come from lr_decay=1.0 rather than the method?

Background
----------
Stage A on CIFAR-10 used lr_decay=1.0 because that maximised FedAvg's late
accuracy (0.4975 vs 0.3765 at 0.9). But SCAFFOLD is the one method whose late
stability depended on decay in the MNIST pilot (constant lr peaked at 78.95%,
decayed lr reached 91.30%). Under decay=1.0 it scored a final 0.2005 on CIFAR-10
-- worse than half of FedAvg -- which looks like decay starvation, not a genuine
method failure.

If SCAFFOLD recovers at a moderate decay, then the CIFAR-10 test of the
`fedavg|scaffold` pair (the cleanest robust inversion from MNIST) is INVALID
rather than negative, and lr_decay has to move into the tuned grid.

This script answers that with one seed per decay value. It deliberately does not
pick a winner outright -- a single seed is not enough to choose a schedule, only
enough to decide whether the method is alive at all.
"""

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rank_inv_runner import run_one                      # noqa: E402


def score(acc):
    acc = np.asarray(acc, dtype=float)
    vol = float(acc[-10:].std())
    drop = 100.0 * float(acc.max() - acc[acc.argmax():].min())
    # numpy comparisons hand back np.bool_, which json.dump rejects outright --
    # it fails only at serialisation time, after every run is already finished,
    # which silently throws away the whole experiment.
    return dict(late=float(acc[int(len(acc) * 0.85) - 1]),
                peak=float(acc.max()), final=float(acc[-1]),
                drop=drop, vol=vol,
                stable=bool(vol <= 0.01 and drop <= 5.0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="cifar10")
    ap.add_argument("--alpha", default="0.1")
    ap.add_argument("--rounds", type=int, default=60)
    ap.add_argument("--lr", type=float, default=0.05)
    ap.add_argument("--decays", default="0.9,0.95,0.98,1.0")
    ap.add_argument("--methods", default="scaffold,fedavg")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="../results/rank_inv/_decay_starve.json")
    args = ap.parse_args()

    decays = [float(x) for x in args.decays.split(",")]
    methods = args.methods.split(",")
    lines = ["%s scaffold-decay probe (seed %d, %d rounds, lr=%s)" % (
                 args.dataset, args.seed, args.rounds, args.lr),
             "hypothesis: SCAFFOLD's collapse is caused by lr_decay=1.0, "
             "not by the method", ""]
    store = {}
    for meth in methods:
        lines.append("=== %s" % meth)
        store[meth] = {}
        for dec in decays:
            cfg = dict(dataset=args.dataset, arch="cnn", skew="dirichlet",
                       alpha=float(args.alpha), n_clients=10,
                       rounds=args.rounds, local_epochs=1, lr=args.lr,
                       batch_size=64, n_train=10000, n_test=2000,
                       seed=args.seed, method=meth, lr_decay=dec)
            r = run_one(cfg)
            acc = [t["acc"] for t in r["trace"]]
            s = score(acc)
            store[meth][str(dec)] = s
            # Flush after EVERY run. The first version of this script dumped the
            # whole store only at the end, and a serialisation error (np.bool_)
            # threw away all eight completed runs. An experiment that costs ~25
            # minutes must not be all-or-nothing.
            json.dump(store, open(args.out, "w"), indent=1, default=str)
            lines.append("  decay=%-5.2f late=%.4f final=%.4f peak=%.4f "
                         "drop=%.1fp last10sd=%.4f  %s"
                         % (dec, s["late"], s["final"], s["peak"], s["drop"],
                            s["vol"], "STABLE" if s["stable"] else "unstable"))
            open(args.out.replace(".json", ".txt"), "w",
                 encoding="utf-8").write("\n".join(lines))
            print("  %s decay=%.2f final=%.4f %s" % (
                meth, dec, s["final"], "STABLE" if s["stable"] else "unstable"),
                flush=True)
        lines.append("")

    for meth, rows in store.items():
        st = [(float(k), v) for k, v in rows.items() if v["stable"]]
        un = [(float(k), v) for k, v in rows.items() if not v["stable"]]
        lines.append("--- %s: %d/%d decay values stable" % (
            meth, len(st), len(rows)))
        if st:
            bstd = max(st, key=lambda kv: kv[1]["late"])
            lines.append("    best STABLE  decay=%.2f late=%.4f final=%.4f"
                         % (bstd[0], bstd[1]["late"], bstd[1]["final"]))
        if un:
            bstu = max(un, key=lambda kv: kv[1]["late"])
            lines.append("    best overall decay=%.2f late=%.4f final=%.4f "
                         "(unstable, vol=%.4f drop=%.1fp)"
                         % (bstu[0], bstu[1]["late"], bstu[1]["final"],
                            bstu[1]["vol"], bstu[1]["drop"]))
        # spread = how much the SAME knob moves this method's own score
        spreads = sorted(((float(k), v["late"]) for k, v in rows.items()),
                         key=lambda kv: kv[0])
        lines.append("    spread of late acc across knob: %.4f - %.4f = %.4f"
                     % (min(v for _, v in spreads), max(v for _, v in spreads),
                        max(v for _, v in spreads) - min(v for _, v in spreads)))
    lines.append("")
    lines.append("NOTE: this deliberately does NOT reduce the result to one")
    lines.append("verdict word. 'Collapses everywhere' and 'merely loses accuracy'")
    lines.append("are different claims, and an arbitrary aliveness threshold")
    lines.append("(the first version used late > 0.35) would have declared a")
    lines.append("STABLE 0.3475 run dead. Read the rows, not the verdict.")

    json.dump(store, open(args.out, "w"), indent=1, default=str)
    txt = args.out.replace(".json", ".txt")
    open(txt, "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
