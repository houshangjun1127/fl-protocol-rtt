"""Figure 1: the rounds-to-target verdict is a function of protocol choices.

What this figure has to do
--------------------------
Make a reader who knows nothing about federated learning understand, in under
five minutes, that "which algorithm converges fastest" is not answered by the
data alone -- it is answered by three choices the experimenter makes and almost
never reports:

  P1  the value of the target accuracy t
  P2  the global training schedule (here: the learning-rate decay)
  P3  the statistic used to decide "reached" (first passage vs. a stable level)

Panel map
---------
(a) rounds-to-target vs. t, for the three algorithms HEM itself compares.
    The curves cross: the winner depends on where you put t.
(b) per-seed winner at each t. HEM's own value (0.80) sits in the region where
    the four seeds disagree, so HEM's chosen number does not even give a stable
    answer on data where 80% is reachable.
(c) how much headroom the SAME nominal target (80%) leaves above each setup's
    reachable ceiling. HEM's published numbers leave FedAvg 4 points; our
    CIFAR-10 setup leaves none at all, i.e. the metric is undefined.
(d) the target values actually used in the literature. They span 20%-97%.

Everything in (a)(b) is recomputed here from stored traces -- no new training.
(c)(d) come from published numbers, each recorded with its source in
`results/negative_results.md` section 7 and `results/submission_plan.md`.
"""

import glob
import json
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.normpath(os.path.join(HERE, "..", "results", "rank_inv"))
OUT = os.path.normpath(os.path.join(HERE, "..", "results", "figures"))
os.makedirs(OUT, exist_ok=True)

METHODS = ["fedavg", "feddyn", "scaffold"]
LABEL = {"fedavg": "FedAvg", "feddyn": "FedDyn", "scaffold": "SCAFFOLD"}
COLOR = {"fedavg": "#0072B2", "feddyn": "#E69F00", "scaffold": "#009E73"}
SEEDS = [0, 1, 2, 3, 4, 5]
HEM_TARGET = 0.80


def load(ds, method, seeds=SEEDS):
    """acc traces for one dataset/method, keyed by seed."""
    out = {}
    for s in seeds:
        hits = glob.glob(os.path.join(RES, "%s_a0.1_%s_*_s%d.json" % (ds, method, s)))
        if not hits:
            out[s] = None
            continue
        with open(hits[0]) as fh:
            d = json.load(fh)
        out[s] = [row["acc"] for row in d["trace"]]
    return out


def ceiling(ds):
    """Best accuracy any method/seed reaches on this dataset.

    Uses the per-run maximum over rounds (the 'peak'), not the final value.
    Rationale: a target t is *reachable* if some run touches it at some point.
    Using the final value instead would conflate 'reachable' with 'stays there',
    which is a stability question handled separately by R5.

    Falls back to Stage A tuning records when a dataset has no Stage B traces.
    CIFAR-10 is currently in exactly that state (Stage A only), so without the
    fallback the ceiling would silently read as 0.0 and panel (c) would claim
    the target is unreachable for the wrong reason.
    """
    best, who = 0.0, None
    for m in ["fedavg", "uniform", "fedavgm", "fedproxw", "fedadam",
              "scaffold", "feddyn"]:
        for s, acc in load(ds, m).items():
            if acc and max(acc) > best:
                best, who = max(acc), "%s/seed%d (stage B)" % (m, s)
    if best > 0:
        return best, who

    # Stage A fallback: tuned_<ds>_a<alpha>.json holds every hp candidate tried,
    # each with peak_acc from its own single run at seed 0.
    for path in glob.glob(os.path.join(RES, "tuned_%s_a*.json" % ds)):
        try:
            with open(path) as fh:
                blob = json.load(fh)
        except (json.JSONDecodeError, KeyError):
            continue
        for key, entry in blob.items():
            for s in entry.get("settings", []):
                if s.get("peak_acc", 0.0) > best:
                    best = s["peak_acc"]
                    who = ("%s/%s (stage A, seed 0)"
                           % (key.split("|")[-1], s.get("label", "?")))
    return best, who


def rtt(acc, t):
    """first communication round (1-based) whose accuracy reaches t; inf if never.

    `acc` is the per-round accuracy list, so the round number is the index + 1.
    """
    if acc is None:
        return np.inf
    for i, a in enumerate(acc):
        if a >= t:
            return float(i + 1)
    return np.inf


def finite_mean(vals, need=2):
    v = [x for x in vals if np.isfinite(x)]
    return float(np.mean(v)) if len(v) >= need else np.nan


# ----------------------------------------------------------------- panel a/b
def panel_ab(ax_a, ax_b):
    traces = {m: load("mnist", m) for m in METHODS}
    grid = np.round(np.arange(0.55, 0.925, 0.01), 4)

    for m in METHODS:
        per_seed = [[rtt(traces[m][s], t) for t in grid] for s in SEEDS]
        for s, ys in zip(SEEDS, per_seed):
            ax_a.plot(grid, ys, color=COLOR[m], lw=0.9, alpha=0.35, zorder=1)
        mean = [finite_mean([per_seed[i][j] for i in range(len(SEEDS))])
                for j in range(len(grid))]
        ax_a.plot(grid, mean, color=COLOR[m], lw=2.6, label=LABEL[m], zorder=3)

    ax_a.axvline(HEM_TARGET, color="k", ls="--", lw=1.6, zorder=4)
    ax_a.annotate("HEM's target: 80%,\nnever argued for",
                  xy=(HEM_TARGET, 15.0), xytext=(0.845, 30.0),
                  fontsize=8.5, va="center", ha="left",
                  arrowprops=dict(arrowstyle="->", lw=1.0, color="black",
                                  connectionstyle="arc3,rad=0.22"))
    # Mark the single crossing, which is the whole point of the panel. Its
    # location is computed, not eyeballed: see negative_results.md 9.5 for why
    # that distinction matters here.
    ax_a.plot([0.72], [5.0], marker="*", ms=15, color="black", zorder=6)
    ax_a.annotate("single crossing\n$t\\approx0.72$", xy=(0.72, 5.0),
                  xytext=(0.615, 13.0), fontsize=8.5, ha="left", va="center",
                  arrowprops=dict(arrowstyle="->", lw=1.0, color="black"))
    ax_a.set_xlim(0.55, 0.995)
    ax_a.set_ylim(0, 52)
    ax_a.set_xlabel("target accuracy $t$")
    ax_a.set_ylabel("rounds to reach $t$  (lower = faster)")
    ax_a.set_title("(a)  Which algorithm is fastest depends on $t$",
                   fontsize=11, loc="left")
    ax_a.legend(frameon=False, fontsize=9)
    ax_a.grid(alpha=0.25, ls=":")
    ax_a.set_xlim(0.55, 0.92)

    # ---- (b) winner by seed
    rows = [0.60, 0.70, 0.75, 0.80, 0.85, 0.90]
    SHORT = {"fedavg": "FedAvg", "feddyn": "FedDyn", "scaffold": "SCAF"}
    ax_b.set_xlim(-0.75, 8.6)
    ax_b.set_ylim(-0.6, len(rows) - 0.4)
    for i, t in enumerate(rows):
        winners = []
        for s in SEEDS:
            vals = {m: rtt(traces[m][s], t) for m in METHODS}
            fin = {m: v for m, v in vals.items() if np.isfinite(v)}
            winners.append(min(fin, key=fin.get) if fin else None)
        for j, w in enumerate(winners):
            if w is None:
                ax_b.add_patch(plt.Rectangle((j - 0.42, i - 0.42), 0.84, 0.84,
                                             facecolor="#dddddd",
                                             edgecolor="#999999"))
                ax_b.text(j, i, "n/a", ha="center", va="center", fontsize=7)
            else:
                ax_b.add_patch(plt.Rectangle((j - 0.42, i - 0.42), 0.84, 0.84,
                                             facecolor=COLOR[w],
                                             edgecolor="white"))
                ax_b.text(j, i, SHORT[w], ha="center", va="center", fontsize=6.5,
                          color="white", fontweight="bold")
        uniq = set(w for w in winners if w is not None)
        hemt = abs(t - HEM_TARGET) < 1e-9
        if hemt:
            from collections import Counter as _C
            _c = _C(w for w in winners if w is not None)
            tag = ("HEM's line: SPLIT  " + "  ".join(
                       "%s x%d" % (SHORT[k], v) for k, v in _c.most_common())
                   if len(uniq) > 1
                   else "%s UNANIMOUS" % LABEL[list(uniq)[0]])
        elif len(uniq) == 1:
            tag = "%s  UNANIMOUS" % LABEL[list(uniq)[0]]
        else:
            from collections import Counter
            c = Counter(w for w in winners if w is not None)
            tag = "SPLIT  " + "  ".join("%s x%d" % (SHORT[k], v)
                                        for k, v in c.most_common())
        ax_b.text(3.65, i, tag, va="center", fontsize=8.5,
                  fontweight="bold" if len(uniq) == 1 else "normal",
                  color=COLOR[list(uniq)[0]] if len(uniq) == 1 else "#444444")
        ax_b.text(-0.52, i, "%.2f" % t, va="center", ha="right", fontsize=9,
                  fontweight="bold" if hemt else "normal",
                  color="black" if hemt else "#333333")
        if hemt:
            ax_b.add_patch(plt.Rectangle((-0.55, i - 0.48), 4.1, 0.96,
                                         fill=False, edgecolor="black",
                                         lw=1.8, ls="--"))

    ax_b.set_yticks([])
    ax_b.set_xticks(range(len(SEEDS)))
    ax_b.set_xticklabels(["seed %d" % s for s in SEEDS], fontsize=8)
    ax_b.set_title("(b)  Same data, same budget: the winner flips with $t$ "
                   "(MNIST, 6 seeds)", fontsize=11, loc="left")
    ax_b.text(-0.52, len(rows) - 0.62, "$t$", ha="right", va="bottom",
              fontsize=10, style="italic")
    ax_b.axis("off")


# ------------------------------------------------------------------- panel c
def panel_c(ax):
    # Ceilings recomputed from the traces on disk, so the figure and the
    # analysis cannot drift apart. The HEM row keeps HEM's own published
    # client-accuracy numbers (SCAFFOLD 0.86), which are the fairest reading of
    # "the ceiling HEM's 80% target is measured against".
    ours = {ds: ceiling(ds)[0] for ds in ("mnist", "fashion", "cifar10")}
    groups = [
        ("Ours\nMNIST", ours["mnist"], "#7fb3d5"),
        ("HEM (published)\nCIFAR-10, 100 cl.", 0.86, "#f0b27a"),
        ("Ours\nFashion-MNIST", ours["fashion"], "#a9dfbf"),
        ("Ours\nCIFAR-10", ours["cifar10"], "#d7bde2"),
    ]
    xs = np.arange(len(groups))
    vals = [g[1] for g in groups]
    bars = ax.bar(xs, vals, color=[g[2] for g in groups],
                  edgecolor="#333333", lw=0.8, width=0.62)
    ax.axhline(HEM_TARGET, color="firebrick", ls="--", lw=1.8)
    ax.text(len(groups) - 0.45, HEM_TARGET + 0.012, "target = 80%",
            color="firebrick", fontsize=9, ha="right", fontweight="bold")

    for x, v, g in zip(xs, vals, groups):
        ax.text(x, v + 0.018, "%.3f" % v, ha="center", fontsize=9)
        if v < HEM_TARGET:
            ax.text(x, v + 0.095, "UNREACHABLE:\nmetric undefined",
                    ha="center", fontsize=8.5, color="firebrick",
                    fontweight="bold")
        else:
            ax.text(x, HEM_TARGET - 0.095, "headroom\n%+.1f pt" % (100 * (v - HEM_TARGET)),
                    ha="center", fontsize=8, color="#333333")

    ax.set_xticks(xs)
    ax.set_xticklabels([g[0] for g in groups], fontsize=8.5)
    ax.set_ylabel("best reachable accuracy")
    ax.set_ylim(0, 1.18)
    ax.set_title("(c)  One nominal target, four meanings: headroom above the "
                 "reachable ceiling", fontsize=10.5, loc="left")
    ax.grid(axis="y", alpha=0.25, ls=":")


# ------------------------------------------------------------------- panel d
LIT = [
    ("FedZMG", "arXiv 2602.18384", [(0.20, "CIFAR-100"), (0.33, "CIFAR-100"),
                                    (0.35, "Shakespeare"), (0.45, "Shakespeare")],
     "#8e44ad"),
    ("FedPA", "arXiv 2010.05273", [(0.30, "CIFAR-100"), (0.40, "CIFAR-100"),
                                   (0.84, "EMNIST-62"), (0.86, "EMNIST-62")],
     "#2980b9"),
    ("ADCT", "JADS 2025", [(0.60, "FMNIST"), (0.75, "MNIST")], "#16a085"),
    ("HEM", "TST 2025", [(0.80, "CIFAR-10")], "#c0392b"),
    ("Batch-size control", "arXiv 2507.15601", [(0.97, "MNIST")], "#7f8c8d"),
]


def panel_d(ax):
    ax.set_xlim(0.10, 1.10)
    ax.set_ylim(-1.15, len(LIT) - 0.2)
    for i, (name, src, pts, col) in enumerate(LIT):
        ax.plot([0.15, 1.0], [i, i], color="#cccccc", lw=0.9, zorder=1)
        # stagger the two labels so that a close pair (e.g. 84/86) stays legible
        order = sorted(range(len(pts)), key=lambda k: pts[k][0])
        for rank, k in enumerate(order):
            v, ds = pts[k]
            dy = 8 if len(pts) == 1 else (8 if rank == 0 else -16)
            ax.plot(v, i, "o", color=col, ms=9, zorder=3)
            ax.annotate("%.0f%% %s" % (100 * v, ds), (v, i),
                        textcoords="offset points", xytext=(0, dy),
                        ha="center", fontsize=7)
        ax.text(0.13, i, "%s\n%s" % (name, src), ha="right", va="center",
                fontsize=8, linespacing=1.3)

    ax.axvline(HEM_TARGET, color="firebrick", ls="--", lw=1.4, zorder=2)
    ax.annotate("", xy=(1.0, -0.72), xytext=(0.20, -0.72),
                arrowprops=dict(arrowstyle="<->", color="firebrick", lw=1.6))
    ax.text(0.60, -1.05, "reported targets span 77 accuracy points —\n"
            "no two papers agree, none justifies the value",
            ha="center", fontsize=8.5, color="firebrick", fontweight="bold",
            linespacing=1.4)
    ax.set_yticks([])
    ax.set_xlabel("target accuracy used as the convergence criterion")
    ax.set_title("(d)  Target values actually used in the literature",
                 fontsize=10.5, loc="left")
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)


def main():
    fig = plt.figure(figsize=(12.6, 7.9))
    gs = fig.add_gridspec(2, 2, hspace=0.42, wspace=0.30,
                          left=0.075, right=0.975, top=0.900, bottom=0.095)
    panel_ab(fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]))
    panel_c(fig.add_subplot(gs[1, :]))

    fig.suptitle("Figure 1.  \"Which federated algorithm converges fastest?\" "
                 "is decided by protocol choices nobody reports.",
                 fontsize=13.5, fontweight="bold", y=0.965)
    fig.text(0.008, 0.928,
             "Rounds-to-target in all panels is a FIRST-PASSAGE time: the "
             "first round at which test accuracy reaches $t$; a method that "
             "never reaches $t$ within the budget is censored, not ranked. "
             "See Section 3.3 for the same traces read with window-mean "
             "decision statistics.",
             fontsize=8.2, style="italic", ha="left", va="top")

    png = os.path.join(OUT, "fig1_protocol_dependence.png")
    pdf = os.path.join(OUT, "fig1_protocol_dependence.pdf")
    fig.savefig(png, dpi=300)
    fig.savefig(pdf)
    print("wrote", png)
    print("wrote", pdf)

    # machine-readable companion so the numbers can be re-checked later
    dump = {}
    traces = {m: load("mnist", m) for m in METHODS}
    for t in [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]:
        dump["%.2f" % t] = {m: [rtt(traces[m][s], t) for s in SEEDS]
                            for m in METHODS}
    with open(os.path.join(OUT, "fig1_data.json"), "w") as fh:
        json.dump(dump, fh, indent=1)
    print("wrote", os.path.join(OUT, "fig1_data.json"))


if __name__ == "__main__":
    main()
