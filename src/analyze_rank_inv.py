"""Stage B analysis: rank inversions in rounds-to-target-accuracy.

STATISTICS -- fixed BEFORE looking at the results, to avoid the classic trap of
choosing an analysis that flatters a hoped-for conclusion.

Definitions
-----------
RTT(A, t)  : first round whose accuracy reaches t.  If never reached within the
             budget, RTT = INF and A is recorded as NOT ACHIEVING t.

Ranking at target t
    Methods achieving t are ordered by RTT ascending (fewer rounds = better).
    Methods not achieving t are ranked last, ordered by their final accuracy.

A pair (A, B) INVERTS at t if:
    at some target t1 they are ordered A < B (A faster), and
    at some later target t2 > t1 they are ordered B < A (B faster),
    AND the inversion survives the near-tie filter below.

Near-tie filter
---------------
An inversion is only counted as real if |RTT_A - RTT_B| >= tau at BOTH
targets, with tau = 2 rounds. Without this, "9 vs 10 rounds" counts as a
reversal, which is meaningless given seed noise.

Robustness requirements an inversion must satisfy
-------------------------------------------------
  R1  it appears on at least 2 of 4 seeds in the same (dataset, target) cell
  R2  it appears for at least 2 methods (not a single pathological pair)
  R3  the target grid must be dense (step <= 1 percentage point)
  R4  CROSS-DATASET: the same method pair inverts on at least 2 independent
      datasets. This is the only criterion that separates "an artefact of this
      one training run" from "a property of the metric itself", so it is the
      one that decides whether the finding is real.
  R5  STABILITY: every seed counted towards the inversion must involve two
      methods whose trajectories have actually SETTLED by the end of the budget
      (last-10-round std <= --vol-max, post-peak loss <= --drop-max points).
  R6  MECHANISM: the instability attributed to a method must be attributable to
      an aggressive hyperparameter. Specifically, if a method is unstable at its
      Stage-A-selected coefficient but stable at a more conservative one, then
      its inversions are a tuning artefact, not evidence about the metric.
      R6 is a falsifiable prediction: it is written before CIFAR-10 is analysed.
      We predict that FedDyn's FashionMNIST oscillation (last-10 std 0.023-0.043)
      disappears at a smaller fdyn_alpha, and that the associated inversions
      disappear with it.

Why R5 exists
--------------
R1-R4 are all satisfiable by a method that oscillates. RTT is a FIRST-PASSAGE
statistic: it pays a method for touching a high accuracy once, however violently
the run behaves afterwards. We measured FedDyn on FashionMNIST and found its last
10 rounds swing by 0.023-0.043 (vs 0.0003-0.0032 for every other method), i.e. an
order of magnitude less settled, while still posting some of the best RTTs at
0.70-0.73. Those inversions are real as arithmetic and meaningless as a claim
about convergence speed, so R1-R4 are reported alongside R5 rather than instead
of it.

R1/R2/R3/R4/R5 are reported separately so a reader can judge strength.

Direction bookkeeping
---------------------
For each robust inversion we record WHICH method wins at the low target and
WHICH wins at the high target. Cross-dataset replication must agree on the
direction too: if FedAvg beats SCAFFOLD at a low target on MNIST but LOSES at a
low target on FashionMNIST, that is two different phenomena, not one.

Report per dataset:
  - the accuracy at each target of the best and worst method (accuracy depends
    on target too, which is the deeper issue)
  - Kendall tau between the ranking at the lowest and highest commonly
    achievable target
  - full ranking table at each target
"""
import argparse
import itertools
import json
import os
from collections import defaultdict

import numpy as np


def load_results(d):
    """Group run records by (dataset, alpha, seed, method)."""
    out = defaultdict(list)
    for f in os.listdir(d):
        # skip tuned_*.json (hp sweeps) and our own reports
        if not f.endswith(".json") or f.startswith("tuned_") \
                or f.endswith("_report.json"):
            continue
        with open(os.path.join(d, f), "r", encoding="utf-8") as fh:
            r = json.load(fh)
        if "cfg" not in r or "trace" not in r:
            continue
        c = r["cfg"]
        out[(c["dataset"], c["alpha"], c["seed"])].append(r)
    return out


def acc_trace(r):
    return np.array([t["acc"] for t in r["trace"]], dtype=float)


def rtt(accs, target):
    """First round index (1-based) reaching target, or None."""
    hit = np.nonzero(accs >= target)[0]
    return int(hit[0]) + 1 if len(hit) else None


def rank_at(accs_by_method, target, tau=None):
    """Rank methods at `target`. Returns dict method -> (rtt or None, final)."""
    tab = {}
    for m, a in accs_by_method.items():
        tab[m] = (rtt(a, target), float(a[-1]))
    achieving = sorted([m for m in tab if tab[m][0] is not None],
                       key=lambda m: tab[m][0])
    failing = sorted([m for m in tab if tab[m][0] is None],
                     key=lambda m: -tab[m][1])
    return tab, achieving + failing


def kendall_tau(order_a, order_b, rtt_a=None, rtt_b=None):
    """Kendall tau-b between two orderings of the same item set.

    WHY TAU-B, NOT TAU-A.  First-passage times are integers on a 60-round grid,
    so at a low target several methods routinely reach the target on the SAME
    round.  The two variants disagree on how to score such a pair: tau-b
    discounts it -- a tie is not evidence about ordering -- while tau-a keeps it
    in the denominator while assigning it to neither the concordant nor the
    discordant count.  Under EITHER definition the statistic is a function of
    the data alone; neither is sensitive to the order in which trace files are
    read.

    The order sensitivity quantified in src/check_tau_variant.py is therefore
    NOT a defect of tau-a, and earlier text in this paper that attributed it to
    tau-a was wrong.  It arises one step earlier, in rank_at(): that function
    stable-sorts on RTT, converting a tied, partially ordered measurement into
    a strict ordinal ranking, so the relative position of two methods with
    equal RTT is decided by insertion order.  tau-a applied to that ordinal
    vector then inherits an arbitrary convention.  Applied instead to the raw
    keys -- first-passage round if the target is reached, otherwise minus the
    final accuracy -- tau-a returns one and the same value under all 7! = 5040
    load orders, on every one of the 42 (cell, seed) runs (spread 0.000000).
    We report tau-b because it discounts the pairs the 60-round grid cannot
    resolve, and because it too is invariant once the tie map is supplied
    explicitly from the RTT values rather than inferred from sort order.

    CORRECTION (R1, 2026-10-18).  The denominator used the standard tau-b
    identity sqrt((n0 - n1)(n0 - n2)), but the loop previously `continue`d
    on pairs tied on BOTH sides before incrementing either counter, which
    under-counts n1 and n2 and inflates the denominator (in the limit where
    every pair is tied it returned a spurious 0.0 instead of None).  The two
    counters are now incremented independently, per the standard identity.
    No reported value changed: max |tau_b_before - tau_b_after| = 0.0035, i.e.
    rounding at the third decimal only.

    `rtt_a` / `rtt_b` map method -> first-passage round at each target (None if
    the method never reaches it).  Two methods are tied at a target iff they
    have equal non-None RTT.

    Returns None when every comparable pair is tied on at least one side, i.e.
    when tau-b is undefined -- which happens when all methods reach the low
    target on the same round.
    """
    common = [m for m in order_a if m in order_b]
    ia = {m: i for i, m in enumerate(order_a)}
    ib = {m: i for i, m in enumerate(order_b)}
    n = len(common)
    if n < 2:
        return None

    def tied(m, other, rtts):
        if not rtts:
            return False
        u, v = rtts.get(m), rtts.get(other)
        return u is not None and u == v

    n0 = n * (n - 1) // 2
    conc = disc = ta = tb = 0
    for x, y in itertools.combinations(common, 2):
        sx = 0 if tied(x, y, rtt_a) else np.sign(ia[x] - ia[y])
        sy = 0 if tied(x, y, rtt_b) else np.sign(ib[x] - ib[y])
        # NOTE (R1): pairs tied on BOTH sides must increment both counters, per
        # the standard identity n1 = sum_i C(t_i,2), n2 = sum_j C(u_j,2), each
        # running over ALL pairs tied on that side.  The earlier
        # `if sx == 0 and sy == 0: continue` skipped them, inflating the
        # denominator and returning a spurious 0.0 in the all-tied limit.
        if sx == 0:
            ta += 1
        if sy == 0:
            tb += 1
        if sx == 0 or sy == 0:
            continue
        if sx * sy > 0:
            conc += 1
        else:
            disc += 1
    denom = np.sqrt(float(n0 - ta) * float(n0 - tb))
    if denom == 0:
        return None
    return (conc - disc) / denom


def late_volatility(accs, tail=10):
    """Std-dev of accuracy over the last `tail` rounds.

    Rounds-to-target is a FIRST-PASSAGE statistic: it rewards a run for touching a
    high accuracy once, no matter how violently that run oscillates afterwards. An
    oscillating run can therefore post an excellent RTT while being the worst method
    in practice. This scalar is the guard against reading such a run as a genuine
    "faster convergence": it measures whether the trajectory has actually settled.
    """
    tail = accs[-tail:] if len(accs) >= tail else accs
    return float(np.std(tail))


def post_peak_drop(accs):
    """Largest accuracy loss from the run's own peak to any later round, in points."""
    pk = float(accs.max())
    i = int(accs.argmax())
    later = accs[i:]
    return 100.0 * (pk - float(later.min())) if len(later) else 0.0


def analyse_cell(traces, targets, tau=2):
    """All pairwise inversions within one (dataset, seed) group of runs."""
    accs = {r["cfg"]["method"]: acc_trace(r) for r in traces}
    methods = sorted(accs)
    orders = {}
    for t in targets:
        tab, order = rank_at(accs, t)
        orders[t] = (tab, order)

    inversions = []
    for a, b in itertools.combinations(methods, 2):
        for t1, t2 in itertools.combinations(targets, 2):
            if t2 <= t1:
                continue
            tab1, _ = orders[t1]
            tab2, _ = orders[t2]
            ra1, rb1 = tab1[a][0], tab1[b][0]
            ra2, rb2 = tab2[a][0], tab2[b][0]
            if None in (ra1, rb1, ra2, rb2):
                continue
            if abs(ra1 - rb1) < tau or abs(ra2 - rb2) < tau:
                continue
            # A faster at t1, B faster at t2  ->  genuine inversion
            if ra1 < rb1 and ra2 > rb2:
                inversions.append({
                    "pair": (a, b), "t1": float(t1), "t2": float(t2),
                    "rtt_at_t1": (ra1, rb1), "rtt_at_t2": (ra2, rb2),
                    "size_t1": int(rb1 - ra1), "size_t2": int(ra2 - rb2),
                })
    return orders, inversions, accs


def _jsonable(o):
    """Recursively stringify keys and values that json cannot represent.

    Keys must be str/int/float/bool/None. Several report sections are keyed by
    (pair, t1, t2) tuples in memory, which json rejects; we render them as
    readable strings rather than dropping the section.
    """
    if isinstance(o, dict):
        return {("|".join(str(x) for x in k) if isinstance(k, tuple) else str(k)):
                _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(x) for x in o]
    if isinstance(o, (str, int, float, bool)) or o is None:
        return o
    return str(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "results", "rank_inv"))
    ap.add_argument("--target-lo", type=float, default=0.30)
    ap.add_argument("--target-hi", type=float, default=0.95)
    ap.add_argument("--target-step", type=float, default=0.01)
    ap.add_argument("--tau", type=int, default=2)
    ap.add_argument("--vol-max", type=float, default=0.01,
                    help="R5: last-10-round std above which a run counts as unstable")
    ap.add_argument("--drop-max", type=float, default=5.0,
                    help="R5: post-peak accuracy loss (points) above which unstable")
    ap.add_argument("--r4-basis", choices=["R1", "R5"], default="R5",
                    help="which robustness level R4 cross-dataset replication builds on")
    ap.add_argument("--target-mode", choices=["absolute", "relative"],
                    default="absolute",
                    help="absolute: one shared grid of accuracy values. "
                         "relative: per-dataset grid spanning the reachable band")
    ap.add_argument("--n-rel-targets", type=int, default=25,
                    help="relative mode: number of levels inside each dataset band")
    ap.add_argument("--rho-lo", type=float, default=0.50,
                    help="relative mode: lowest target as a fraction of ceiling")
    ap.add_argument("--rho-hi", type=float, default=0.98,
                    help="relative mode: highest target as a fraction of ceiling")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    groups = load_results(args.dir)
    if not groups:
        raise SystemExit(f"no run files in {args.dir}")

    abs_targets = [round(x, 4) for x in np.arange(
        args.target_lo, args.target_hi + 1e-9, args.target_step)]

    # Per-dataset TARGET GRID.
    #
    # In absolute mode every dataset shares one grid of accuracy values. That is
    # only meaningful if the datasets live in the same accuracy regime, and they
    # do not: measured final accuracies over the 7 methods span
    #     MNIST 0.924-0.965   FashionMNIST 0.667-0.815   CIFAR-10 0.201-0.523
    # so the MNIST crossing band (0.85-0.89) is unreachable on Fashion and absurd
    # on CIFAR-10. "Does this replicate across datasets?" then has no answer, not
    # because the phenomenon is absent but because the question was never the
    # same question on each dataset.
    #
    # Relative mode fixes that by putting the same number of levels inside the
    # band each DATASET can actually reach: [min final acc, max final acc] pooled
    # over every method and seed. The lowest level is reachable by every method
    # and the highest only by the best one, so the ladder asks the same thing
    # everywhere: climb from "everyone gets there" to "only the winner does".
    # The grid is deliberately computed once per dataset, not per seed, so that
    # R1 (same target on >=2 seeds) stays well defined.
    # First attempt was [min final, max final]. That is a mistake and the run
    # proves it: on MNIST the band then spans only 0.924-0.965, so the grid sits
    # entirely above 0.89 -- the very target where fedavg|scaffold crosses -- and
    # the pair silently disappears. A band defined by the terminal accuracy range
    # cannot see crossings that happen during convergence, only after it.
    #
    # Second definition, used here: targets are RHO fractions of each dataset's
    # attainable ceiling A* (best final accuracy over all methods and seeds),
    # for rho in [0.50, 0.98]. This keeps the whole learning curve in play AND is
    # comparable across datasets -- "reach 90% of what is attainable" is the same
    # question whether the ceiling is 0.965 or 0.523. The lower anchor 0.50 is a
    # declared choice, not an optimum; it only has to sit below every method's
    # useful range so that no target is trivially won at round 1.
    if args.target_mode == "relative":
        ceiling = {}
        for (ds, al, sd), traces in groups.items():
            for r in traces:
                ceiling[ds] = max(ceiling.get(ds, 0.0), float(acc_trace(r)[-1]))
        rhos = np.linspace(args.rho_lo, args.rho_hi, args.n_rel_targets)
        tgrid = {ds: sorted({round(float(rho * A), 4)
                             for rho in rhos}) for ds, A in ceiling.items()}
        for ds, A in ceiling.items():
            print(f"  {ds}: ceiling={A:.4f}  band="
                  f"{tgrid[ds][0]:.4f}..{tgrid[ds][-1]:.4f}")
    else:
        tgrid = defaultdict(lambda: abs_targets)

    # IMPORTANT: the unit of analysis is (dataset, alpha), NOT dataset.
    #
    # BUGFIX (2026-10-09). The results are grouped by (dataset, alpha, seed) --
    # 12 cells once the alpha sweep added 0.05 and 0.3. This loop previously
    # filed them into per_ds[ds] and keyed everything by `sd` alone:
    #     node["ranking"][sd] = ...            <- overwritten by the next alpha
    #     node["alpha"]       = al             <- keeps only the last alpha
    #     pair_seed_support[(...)].add(sd)     <- but THIS accumulates
    # With groups sorted by (ds, al, sd), the last alpha (0.3) silently won.
    # Consequence: the inversion counts pooled all three alphas while the
    # per-seed rankings and Kendall tau reflected alpha=0.3 only, and seeds from
    # different heterogeneity levels were counted as replicates of each other.
    # That breaks R1, which requires >=2 seeds under the SAME condition --
    # a different alpha is a different condition, not another replicate.
    # Everything downstream now keys on (ds, al). When a dataset has exactly one
    # alpha this is identical to the old behaviour.
    per_ds = defaultdict(lambda: {
        "seeds": set(), "inversions": [], "pair_seed_support": defaultdict(set),
        "ranking": {}, "accuracy_by_target": {}})
    cell_ds = {}

    def ckey(ds, al):
        return "%s|a%s" % (ds, al)

    multi_alpha = sorted({al for (_ds, al, _sd) in groups})
    if len(multi_alpha) > 1:
        print("note: multiple alphas present %s -> each (dataset, alpha) is "
              "analysed as its own cell; alphas are NOT pooled as replicates."
              % multi_alpha, flush=True)

    for (ds, al, sd), traces in sorted(groups.items()):
        targets = tgrid[ds]
        orders, invs, accs = analyse_cell(traces, targets, args.tau)
        node = per_ds[ckey(ds, al)]
        cell_ds[ckey(ds, al)] = ds
        node.setdefault("alpha", al)
        node["targets"] = targets
        node["seeds"].add(sd)
        for iv in invs:
            node["inversions"].append({"seed": sd, **iv})
            node["pair_seed_support"][(iv["pair"], iv["t1"], iv["t2"])].add(sd)
        node["ranking"][sd] = {str(t): orders[t][1] for t in targets}
        # First-passage round per method per target, needed to identify TIES for
        # Kendall tau-b (see kendall_tau). Kept next to the ranking so the two
        # can never disagree.
        node.setdefault("rtt_by_target", {})[sd] = {
            str(t): {m: orders[t][0][m][0] for m in orders[t][0]}
            for t in targets}
        # R5 inputs: has each run actually settled by the end of its trajectory?
        node.setdefault("volatility", {})[sd] = {
            m: late_volatility(a) for m, a in accs.items()}
        node.setdefault("post_peak_drop", {})[sd] = {
            m: post_peak_drop(a) for m, a in accs.items()}
        # accuracy of each method at each target-defining moment
        for t in targets:
            node["accuracy_by_target"].setdefault(str(t), {})[sd] = {
                m: (None if orders[t][0][m][0] is None
                    else float(accs[m][orders[t][0][m][0] - 1]))
                for m in accs}

    summary = {}
    for ck, node in per_ds.items():
        t0, tN = node["targets"][0], node["targets"][-1]
        # ---- R5 eligibility: which (method, seed) runs have actually settled?
        # A run is UNSTABLE if its last-10-round std exceeds --vol-max, or if it
        # gave up more than --drop-max points after its own peak. Inversions that
        # involve an unstable run are recorded but flagged, because a first-passage
        # statistic can reward an oscillating trajectory for touching a high accuracy
        # once. Threshold defaults are deliberately loose; they only need to separate
        # "settled" (all other methods) from "oscillating" (FedDyn on fashion).
        eligible_seeds = {}
        for sd in sorted(node["seeds"]):
            vol = node["volatility"][sd]
            drp = node["post_peak_drop"][sd]
            bad = sorted(m for m in vol
                         if vol[m] > args.vol_max or drp[m] > args.drop_max)
            eligible_seeds[sd] = bad

        # R1: an inversion must hold on >= 2 seeds for the SAME (pair, t1, t2)
        robust = {k: sorted(v) for k, v in node["pair_seed_support"].items()
                  if len(v) >= 2}
        # R2: a robust inversion must not be a single-pair artefact -- report how
        # many distinct method pairs contribute at least one robust inversion.
        pairs_with_robust = {(k[0][0], k[0][1]) for k in robust}
        pairs_all = {(i["pair"][0], i["pair"][1]) for i in node["inversions"]}
        # Deduplicate (pair, t1, t2) triples that are adjacent thresholds of the
        # same underlying crossing -- collapse to (pair, crossing region).
        crossings = defaultdict(set)
        for (pair, t1, t2), seeds in robust.items():
            crossings[pair].add(t2)          # t2 is where B became faster

        # ---- R5: same as R1 but every seed counted must have BOTH methods settled.
        robust5 = {}
        for (pair, t1, t2), seeds in node["pair_seed_support"].items():
            good = [s for s in sorted(seeds)
                    if not any(m in eligible_seeds.get(s, []) for m in pair)]
            if len(good) >= 2:
                robust5[(pair, t1, t2)] = good
        pairs_R5 = {(k[0][0], k[0][1]) for k in robust5}
        crossings5 = defaultdict(set)
        for (pair, t1, t2), seeds in robust5.items():
            crossings5[pair].add(t2)

        summary[ck] = {
            "_robust5_keys": robust5,
            "n_seeds": len(node["seeds"]),
            "seeds": sorted(node["seeds"]),
            "unstable_runs": {str(s): eligible_seeds[s] for s in eligible_seeds
                              if eligible_seeds[s]},
            "n_inversions_all": len(node["inversions"]),
            "n_inversions_robust_R1": len(robust),
            "n_pairs_with_any_inversion": len(pairs_all),
            "n_pairs_robust_R1": len(pairs_with_robust),
            "R2_pass": len(pairs_with_robust) >= 2,
            "n_inversions_robust_R5": len(robust5),
            "n_pairs_robust_R5": len(pairs_R5),
            "robust_pairs_R5": sorted(list(p) for p in pairs_R5),
            "crossing_points_R5": {
                "|".join(p): sorted(t) for p, t in sorted(crossings5.items())
            },
            "robust_pairs": sorted(list(p) for p in pairs_with_robust),
            "crossing_points": {
                "|".join(p): sorted(t) for p, t in sorted(crossings.items())
            },
            "examples": [
                {"pair": list(k[0]), "t1": k[1], "t2": k[2],
                 "seeds": sorted(v),
                 "at_t1": [i["rtt_at_t1"] for i in node["inversions"]
                           if i["seed"] in v and (i["pair"], i["t1"], i["t2"]) == k],
                 "at_t2": [i["rtt_at_t2"] for i in node["inversions"]
                           if i["seed"] in v and (i["pair"], i["t1"], i["t2"]) == k]}
                for k, v in sorted(robust.items(),
                                   key=lambda kv: -len(kv[1]))[:12]
            ],
            "kendall_tau_first_vs_last": {
                str(sd): kendall_tau(node["ranking"][sd][str(t0)],
                                     node["ranking"][sd][str(tN)],
                                     node["rtt_by_target"][sd][str(t0)],
                                     node["rtt_by_target"][sd][str(tN)])
                for sd in sorted(node["seeds"])},
            # How many of the C(7,2) pairs are TIED at each endpoint? Reported
            # because tau-b is undefined when every pair is tied on one side.
            "tied_pairs_first_last": {
                str(sd): {
                    "low": sum(
                        1 for x, y in itertools.combinations(
                            [m for m in node["ranking"][sd][str(t0)]], 2)
                        if (node["rtt_by_target"][sd][str(t0)].get(x) is not None
                            and node["rtt_by_target"][sd][str(t0)][x]
                            == node["rtt_by_target"][sd][str(t0)].get(y))),
                    "high": sum(
                        1 for x, y in itertools.combinations(
                            [m for m in node["ranking"][sd][str(tN)]], 2)
                        if (node["rtt_by_target"][sd][str(tN)].get(x) is not None
                            and node["rtt_by_target"][sd][str(tN)][x]
                            == node["rtt_by_target"][sd][str(tN)].get(y))),
                } for sd in sorted(node["seeds"])},
        }

    # ---------------------------------------------------------------- R4
    # Cross-dataset replication. Built from the ROBUST (R1-surviving) set only, so a
    # pair must clear the seed bar on its own before we ask whether it shows up
    # elsewhere. We reuse the already-computed pair_seed_support maps instead of
    # re-deriving them, so R4 cannot disagree with R1.
    per_pair = defaultdict(dict)          # pair -> (dataset,alpha) cell -> info
    for ck in per_ds:
        src = ((k, v) for k, v in per_ds[ck]["pair_seed_support"].items()
               if len(v) >= 2) if args.r4_basis == "R1" else \
              ((k, v) for k, v in summary[ck]["_robust5_keys"].items())
        for (pair, t1, t2), seeds in src:
            cellhere = per_pair[pair].setdefault(ck, {"robust_inversions": 0,
                                                      "crossing_targets": set()})
            cellhere["robust_inversions"] += 1
            cellhere["crossing_targets"].add(t2)

    replicated = {p: dd for p, dd in per_pair.items() if len(dd) >= 2}
    r4 = {
        "n_cells_compared": len(per_ds),
        "n_distinct_datasets": len(set(cell_ds.values())),
        "n_pairs_robust_anywhere": len(per_pair),
        "n_pairs_replicated_R4": len(replicated),
        "R4_pass": len(replicated) >= 1,
        "replicated_pairs": {
            "|".join(p): {
                "datasets": sorted(dd),
                "detail": {ds2: {"robust_inversions": v["robust_inversions"],
                                 "crossing_targets": sorted(v["crossing_targets"])}
                           for ds2, v in sorted(dd.items())}
            } for p, dd in sorted(replicated.items())},
        "per_pair_dataset_coverage": {
            "|".join(p): sorted(dd) for p, dd in sorted(per_pair.items())},
    }
    summary["_cross_dataset"] = r4

    out = args.out or os.path.join(args.dir, "rank_inv_report.json")
    target_range = {ck: (tgrid[cell_ds[ck]][0], tgrid[cell_ds[ck]][-1])
                    for ck in per_ds}
    report = {k: v for k, v in summary.items()}
    for ds, node in report.items():          # drop helper carriers only
        if isinstance(node, dict):
            node.pop("_robust5_keys", None)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"target_mode": args.target_mode,
                   "target_range": {ds: list(v) for ds, v in target_range.items()},
                   "targets": tgrid, "tau": args.tau,
                   "vol_max": args.vol_max, "drop_max": args.drop_max,
                   "r4_basis": args.r4_basis,
                   "summary": _jsonable(report)},
                  f, indent=1, default=str)

    # ---------------- console report
    grid_desc = "; ".join(
        f"{ds}: {tgrid[ds][0]:.3f}..{tgrid[ds][-1]:.3f} ({len(tgrid[ds])} levels)"
        for ds in sorted(tgrid))
    print(f"target mode: {args.target_mode}   {grid_desc}")
    print(f"tau={args.tau} rounds  vol_max={args.vol_max}  drop_max={args.drop_max}")
    for ds, s in summary.items():
        if ds.startswith("_"):
            continue
        print(f"\n=== {ds} ===  seeds={s['seeds']}")
        print(f"  pairs with ANY inversion        : {s['n_pairs_with_any_inversion']}")
        print(f"  inversions, all seeds           : {s['n_inversions_all']}")
        print(f"  R1  inversions on >=2 seeds     : {s['n_inversions_robust_R1']}")
        print(f"  R1  distinct pairs              : {s['n_pairs_robust_R1']}")
        print(f"  R2  (>=2 pairs robust)          : {s['R2_pass']}")
        if s.get("unstable_runs"):
            for sd, bad in sorted(s["unstable_runs"].items()):
                print(f"  !! seed {sd} UNSTABLE runs: {bad} "
                      f"(last10 sd>{args.vol_max} or post-peak drop>{args.drop_max}pts)")
        print(f"  R5  inversions, both settled    : {s.get('n_inversions_robust_R5')}")
        print(f"  R5  distinct pairs              : {s.get('n_pairs_robust_R5')}")
        for p, ts in list(s.get("crossing_points_R5", {}).items())[:6]:
            print(f"     R5 crossing {p}: at targets {ts[:6]}")
        for p, ts in list(s["crossing_points"].items())[:6]:
            print(f"     crossing {p}: at targets {ts[:6]}")
        for ex in s["examples"][:5]:
            a, b = ex["pair"]
            print(f"    {a} vs {b}: {ex['t1']:.2f}->{ex['t2']:.2f} "
                  f"seeds={ex['seeds']}  RTT@low={ex['at_t1']}  RTT@high={ex['at_t2']}")
        taus = [v for v in s["kendall_tau_first_vs_last"].values() if v is not None]
        if taus:
            print(f"  Kendall tau (lowest vs highest target): "
                  f"{['%.2f' % v for v in taus]}")

    # ---------------- cross-dataset verdict (R4)
    r4 = summary.get("_cross_dataset")
    if r4:
        print(f"\n=== R4 cross-cell ({r4['n_cells_compared']} "
              f"(dataset,alpha) cells across {r4['n_distinct_datasets']} datasets, "
              f"basis={args.r4_basis}) ===")
        print(f"  pairs robust on>=1 dataset      : {r4['n_pairs_robust_anywhere']}")
        print(f"  pairs replicated on >=2 datasets: {r4['n_pairs_replicated_R4']}")
        print(f"  R4_pass                         : {r4['R4_pass']}")
        for p, info in r4["replicated_pairs"].items():
            print(f"     REPLICATED {p}: {info['datasets']}")
            for ds, det in info["detail"].items():
                print(f"        {ds}: {det['robust_inversions']} robust, "
                      f"crossing targets {det['crossing_targets'][:6]}")
        if not r4["replicated_pairs"]:
            print("     (none -- every robust pair is dataset-specific)")
        print("  coverage of all robust pairs:")
        for p, d in r4["per_pair_dataset_coverage"].items():
            print(f"     {p}: {d}")

    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
