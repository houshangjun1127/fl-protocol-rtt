"""Render Table 4 (MNIST late accuracy at the two extreme decay settings, plus
each method's swing across all four settings) directly from the decay-probe
JSON files.

Why this script exists. `make_table_knob.py` was written for an earlier draft:
it tabulated `final` accuracy (a single end-of-run sample) over three seeds.
The published table reports *late* accuracy (mean test accuracy over the final
ten rounds) over six seeds, because a single end-of-run sample is exactly the
kind of point estimate Section 3.2 argues against. Rather than mutate the old
script, this one computes the published quantity and says so.

Table 3 (the CIFAR-10 gap matrix with bootstrap CIs) is NOT produced here; it
is produced by `make_ci.py`, whose `decay_probe` block already contains the
per-seed gaps and the seed-level percentile intervals.
"""

import argparse
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RES_DEFAULT = os.path.normpath(os.path.join(HERE, "..", "results", "rank_inv"))

METHODS = ("fedavg", "scaffold")
EXTREMES = (0.90, 1.00)


def load(dirpath, tag, seed):
    """-> {method: {decay: {'late': float, 'stable': bool}}} or None"""
    p = os.path.join(dirpath, "_decay_%s_s%d.json" % (tag, seed))
    if not os.path.exists(p):
        return None
    try:
        doc = json.load(open(p, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    out = {}
    for m in METHODS:
        if m not in doc:
            continue
        out[m] = {}
        for dk, rec in doc[m].items():
            if isinstance(rec, dict) and "late" in rec:
                out[m][float(dk)] = {"late": float(rec["late"]),
                                     "stable": bool(rec.get("stable", False))}
    return out or None


def swing(rec, m):
    vals = [v["late"] for v in rec[m].values()]
    return max(vals) - min(vals) if vals else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=RES_DEFAULT)
    ap.add_argument("--tag", default="mnist",
                    help="probe tag: mnist (Table 4) or cifar")
    ap.add_argument("--seeds", default="0,1,2,3,4,5")
    ap.add_argument("--out", default=None,
                    help="write markdown here (default: stdout only)")
    args = ap.parse_args()

    seeds = [int(x) for x in args.seeds.split(",") if x.strip()]
    rows = []
    for s in seeds:
        rec = load(args.dir, args.tag, s)
        if rec is None:
            rows.append((s, None))
            continue
        rows.append((s, rec))

    L = ["# Table 4. Late accuracy at the two extreme decays, %s, six seeds"
         % ("MNIST" if args.tag == "mnist" else "CIFAR-10"),
         "",
         "`late` = mean test accuracy over the final ten rounds. Swing = max",
         "minus min of `late` across all four decay settings, per seed.",
         "",
         "| Seed | 0.90 (FedAvg / SCAFFOLD) | 1.00 (FedAvg / SCAFFOLD) | "
         "SCAFFOLD swing | FedAvg swing |",
         "|---|---|---|---|---|"]
    for s, rec in rows:
        if rec is None:
            L.append("| %d | not run | not run | — | — |" % s)
            continue
        try:
            cells = ["%.4f / %.4f" % (rec["fedavg"][d]["late"],
                                      rec["scaffold"][d]["late"])
                     for d in EXTREMES]
            L.append("| %d | %s | %s | %.4f | %.4f |"
                     % (s, cells[0], cells[1],
                        swing(rec, "scaffold"), swing(rec, "fedavg")))
        except KeyError:
            L.append("| %d | incomplete | incomplete | — | — |" % s)
    L.append("")

    # how many seeds each method leads at the two extremes
    for d in EXTREMES:
        fa = sum(1 for _, r in rows if r and r["fedavg"].get(d, {}).get("late")
                 and r["scaffold"].get(d, {}).get("late")
                 and r["fedavg"][d]["late"] > r["scaffold"][d]["late"])
        tot = sum(1 for _, r in rows if r and r["fedavg"].get(d)
                  and r["scaffold"].get(d))
        if tot:
            L.append("FedAvg leads at decay %.2f on %d of %d seeds." % (d, fa, tot))
    L.append("")

    txt = "\n".join(L)
    print(txt)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        open(args.out, "w", encoding="utf-8").write(txt + "\n")
        print("\n-> " + args.out)


if __name__ == "__main__":
    main()
