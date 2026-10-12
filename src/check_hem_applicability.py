"""Can our CIFAR-10 traces be checked against HEM's own setup at all?

Why this exists
---------------
The first plan for the case study was to rerun HEM's fixed-80% rule "under our
protocol". A check of the original paper killed that idea: HEM evaluates on
CIFAR-10 with 100 clients, 5-of-10 classes per client, 1000 rounds, and reports
client accuracies of 0.84-0.89. Our CIFAR-10 protocol tops out at 0.523.

So the honest question is not "do we reproduce HEM" but "for which datasets is
HEM's 80% even *defined*". This script answers exactly that, and nothing more --
it does not pretend the two setups are comparable.

It also computes the headroom of each setup relative to its own reachable
ceiling, which is the quantity HEM never reports and the one that makes the 80%
number mean four different things.
"""

import glob
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.normpath(os.path.join(HERE, "..", "results", "rank_inv"))
OUT = os.path.normpath(os.path.join(HERE, "..", "results", "_hem_applicability.txt"))

HEM_TARGET = 0.80
SEEDS = [0, 1, 2, 3]

# Published numbers, each with its source. HEM's come from its Table III; the
# "ours" rows are recomputed from stored traces on disk.
PUBLISHED = [
    ("HEM (published) CIFAR-10, 100 clients, 1000 rounds",
     {"FedAvg": 0.84, "FedDyn": 0.85, "SCAFFOLD": 0.86}, "TST 10.26599/TST.2025.9010175"),
]


def ours(dataset):
    """max reachable accuracy per method, over all seeds, from stored traces."""
    best = {}
    for path in glob.glob(os.path.join(RES, "%s_a0.1_*_s*.json" % dataset)):
        base = os.path.basename(path)
        if base.startswith("tuned_") or base.startswith("_"):
            continue
        method = base.split("_")[2]
        try:
            with open(path) as fh:
                d = json.load(fh)
        except (json.JSONDecodeError, KeyError):
            continue
        acc = [row["acc"] for row in d["trace"]]
        if not acc:
            continue
        best[method] = max(best.get(method, 0.0), float(max(acc)))
    return best


def main():
    lines = ["Is HEM's fixed 80%% target even DEFINED under each protocol?",
             "target = %.2f  (HEM's published value)" % HEM_TARGET, ""]

    setups = []
    for name, methods, src in PUBLISHED:
        setups.append((name, methods, src))
    for ds, label in (("mnist", "ours MNIST (10 clients, Dirichlet a=0.1, 60 rounds)"),
                      ("fashion", "ours Fashion-MNIST (same)"),
                      ("cifar10", "ours CIFAR-10 (same)")):
        m = ours(ds)
        if m:
            setups.append((label, m, "recomputed from results/rank_inv"))

    lines.append("%-56s %8s %8s %10s   %s" % (
        "setup", "ceiling", "target", "headroom", "verdict"))
    lines.append("-" * 104)

    rows = []
    for name, methods, src in setups:
        ceiling = max(methods.values())
        lo = min(methods.values())
        reachable = ceiling >= HEM_TARGET
        head = 100.0 * (ceiling - HEM_TARGET)
        verdict = ("defined  (ceiling-target = %+.1f pt)" % head if reachable
                   else "UNDEFINED (ceiling %.3f < target)" % ceiling)
        lines.append("%-56s %8.3f %8.2f %9s   %s" % (
            name[:56], ceiling, HEM_TARGET,
            "%+.1f pt" % head if reachable else "--", verdict))
        rows.append(dict(name=name, ceiling=ceiling, floor=lo, src=src,
                         reachable=bool(reachable), headroom_pts=head))
    lines.append("")

    lines.append("Per-method ceilings and how close each sits to HEM's 80%:")
    lines.append("")
    for name, methods, src in setups:
        lines.append("  %s" % name)
        for m in sorted(methods, key=lambda k: -methods[k]):
            v = methods[m]
            if v >= HEM_TARGET:
                note = "reachable, headroom %+.1f pt" % (100 * (v - HEM_TARGET))
            else:
                note = "SHORT by %.1f pt" % (100 * (HEM_TARGET - v))
            lines.append("    %-10s %.3f  %s" % (m, v, note))
        lines.append("    source: %s" % src)
        lines.append("")

    lines.append("=" * 104)
    lines.append("READING (this is the point of the exercise):")
    lines.append("")
    lines.append("  1. HEM reports client accuracies of 0.84-0.89 on CIFAR-10 with")
    lines.append("     100 clients. Its 80%% target therefore leaves FedAvg just")
    lines.append("     4.0 accuracy points of headroom -- and the Convergence index,")
    lines.append("     which feeds directly into the HEM score, is a measurement of")
    lines.append("     how fast an algorithm climbs through that last few points.")
    lines.append("")
    lines.append("  2. The same nominal 80%% means completely different things across")
    lines.append("     setups: a generous target on MNIST, an impossible one on our")
    lines.append("     CIFAR-10 protocol. The number carries no transferable meaning")
    lines.append("     without the ceiling it is measured against.")
    lines.append("")
    lines.append("  3. This is NOT a reproduction of HEM. Our CIFAR-10 protocol is far")
    lines.append("     smaller (10 clients vs 100, 60 rounds vs 1000) and is not")
    lines.append("     comparable to theirs. Any paper text must say so explicitly;")
    lines.append("     claiming a rerun here would be unsupportable.")
    lines.append("")
    lines.append("  4. Consequence for the design: the case study must be framed as a")
    lines.append("     SENSITIVITY ANALYSIS OF THE RULE (fix a target, move it, watch")
    lines.append("     the ranking move), run on a dataset where the target is")
    lines.append("     reachable -- i.e. MNIST -- with the dataset mismatch declared")
    lines.append("     as a limitation.")

    txt = "\n".join(lines)
    open(OUT, "w", encoding="utf-8").write(txt)
    print(txt)
    with open(OUT.replace(".txt", ".json"), "w") as fh:
        json.dump({"hem_target": HEM_TARGET, "setups": rows}, fh, indent=1,
                  default=str)


if __name__ == "__main__":
    main()
