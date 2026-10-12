"""Render the Phase-2 knob table in paper-ready markdown.

Separated from check_phase2_gate.py on purpose:

  * check_phase2_gate.py answers "does the claim survive?" (one decision, may
    legitimately close a line of work).
  * this script answers "what exactly do we print?" (no decisions, no verdicts).

Keeping them apart means a change in presentation taste can never silently
change the gate outcome, and vice versa.
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.normpath(os.path.join(HERE, "..", "results", "rank_inv"))
OUT = os.path.normpath(os.path.join(HERE, "..", "results", "table_knob.md"))

SEEDS = [0, 1, 2]


def load(dataset, seed):
    stem = "cifar" if dataset == "cifar10" else "mnist"
    if dataset == "cifar10" and seed == 0:
        paths = [os.path.join(RES, "_decay_starve.json"),
                 os.path.join(RES, "_decay_starve_fedavg.json")]
    else:
        paths = [os.path.join(RES, "_decay_%s_s%d.json" % (stem, seed))]
    merged = {}
    for p in paths:
        if not os.path.exists(p):
            continue
        try:
            with open(p) as fh:
                blob = json.load(fh)
        except json.JSONDecodeError:
            continue
        if any(isinstance(v, dict) and "final" not in v for v in blob.values()):
            for meth, rows in blob.items():
                merged.setdefault(meth, {}).update(rows)
        elif "fedavg" in p:
            merged.setdefault("fedavg", {}).update(blob)
        else:
            merged.setdefault("scaffold", {}).update(blob)
    return merged or None


def row_for(store, dec):
    fa = store.get("fedavg", {}).get(dec)
    sc = store.get("scaffold", {}).get(dec)
    if fa is None or sc is None:
        return None
    return fa, sc


def main():
    L = ["# Table 2. The global learning-rate schedule is not neutral across methods",
         "",
         "Same data, same budget, same every-other-hyperparameter; only the global",
         "`lr_decay` knob moves. FedAvg stays stable throughout; SCAFFOLD's verdict",
         "flips from converged to non-converged, and the FedAvg-SCAFFOLD gap grows",
         "by roughly an order of magnitude -- decided by a knob that is normally",
         "not reported at all.",
         ""]

    for dataset, dsname in (("cifar10", "CIFAR-10"), ("mnist", "MNIST")):
        L.append("## %s" % dsname)
        L.append("")
        L.append("| seed | lr_decay | FedAvg final | SCAFFOLD final | gap (pts) | "
                 "FedAvg stable | SCAFFOLD stable | ratio vs smallest decay |")
        L.append("|---|---|---|---|---|---|---|---|")
        for seed in SEEDS:
            store = load(dataset, seed)
            if not store:
                L.append("| %d | — | not run | not run | — | — | — | — |" % seed)
                continue
            decs = sorted(set(store.get("fedavg", {})) & set(store.get("scaffold", {})),
                          key=float)
            if not decs:
                L.append("| %d | — | incomplete | incomplete | — | — | — | — |" % seed)
                continue
            base = None
            for dec in decs:
                r = row_for(store, dec)
                if r is None:
                    continue
                fa, sc = r
                gap = 100.0 * (fa["final"] - sc["final"])
                if base is None:
                    base = gap
                    ratio = "1.00x (ref)"
                else:
                    ratio = ("%.2fx" % (gap / base)) if base > 0 else "n/a"
                L.append("| %d | %.2f | %.4f | %.4f | %+.2f | %s | %s | %s |"
                         % (seed, float(dec), fa["final"], sc["final"], gap,
                            "yes" if fa["stable"] else "**no**",
                            "yes" if sc["stable"] else "**no**", ratio))
            L.append("")

    L += [
        "## How to read the ratio column",
        "",
        "The ratio is the gap at each decay divided by the gap at the smallest decay",
        "for the same seed. It is a within-seed quantity: each seed is its own",
        "baseline, so seed-to-seed variation in absolute accuracy does not leak into",
        "it. A ratio of 1.00x would mean the knob is neutral for this pair.",
        "",
        "Two caveats that belong in the caption:",
        "",
        "1. Some rows compare against a run flagged unstable. Its `final` accuracy is",
        "   a snapshot at round 60 rather than a settled level, so the gap partly",
        "   reflects where the run happened to be when the budget ended. The stability",
        "   columns are printed alongside for exactly this reason.",
        "2. `lr_decay=1.0` is a constant learning rate, i.e. the *absence* of a",
        "   schedule. The fact that the no-schedule default happens to be the most",
        "   favourable setting for one method and the worst for another is the point:",
        "   the default is a choice, and it is a consequential one.",
        "",
    ]

    txt = "\n".join(L)
    open(OUT, "w", encoding="utf-8").write(txt)
    print(txt)


if __name__ == "__main__":
    main()
