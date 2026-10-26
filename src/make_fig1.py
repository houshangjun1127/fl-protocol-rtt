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
    the six seeds disagree, so HEM's chosen number does not even give a stable
    answer on data where 80% is reachable.
(c) how much headroom the SAME nominal target (80%) leaves below the attainable
    maximum of each of our three α = 0.1 cells. On CIFAR-10 the setup sits 25.05
    points *below* the target, i.e. the metric is undefined there. (HEM's own
    setup is deliberately not drawn: its Table III reports *client* accuracy, a
    different metric from the one defining the bars here, so a headroom bar for
    it could not be computed from the paper.)

The target values used across the literature are reported as a survey result in
Section 3.4 (N = 58 studies, spanning 30%-99.98%) rather than as a panel here:
a five-point illustration would misrepresent a distribution that is now measured
on a screened sample.

Everything in (a)(b) is recomputed here from stored traces -- no new training.
The HEM bar in (c) comes from HEM's own published Table III, recorded with its
source in `results/verified_numbers.md` section 9.12.

Accessibility
-------------
Panels (a)(b) use the Okabe-Ito colourblind-safe qualitative palette. Panel (c)
uses the same palette for the three "ours" bars and separates the one bar drawn
from external published data by hatching rather than by hue, so that no panel
encodes information in colour alone. Output is written at 300 dpi (PNG) and as
vector PDF.
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
# Okabe-Ito qualitative palette: safe for deuteranopia / protanopia / tritanopia.
COLOR = {"fedavg": "#0072B2", "feddyn": "#E69F00", "scaffold": "#009E73"}
SEEDS = [0, 1, 2, 3, 4, 5]
HEM_TARGET = 0.80

# The crossing of the FedAvg and FedDyn mean curves, located numerically on a
# 0.005 grid over six seeds (verified_numbers.md 9.10). The two means are exactly
# equal over [0.615, 0.635] and FedDyn leads from t = 0.665 onward, so a point
# estimate would overstate what the grid resolves; we quote the band.
CROSSING = 0.64
CROSSING_BAND = (0.615, 0.665)


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
    # 0.005 grid: the same resolution at which the crossing band was located.
    grid = np.round(np.arange(0.55, 0.925, 0.005), 4)

    for m in METHODS:
        per_seed = [[rtt(traces[m][s], t) for t in grid] for s in SEEDS]
        for s, ys in zip(SEEDS, per_seed):
            ax_a.plot(grid, ys, color=COLOR[m], lw=0.9, alpha=0.35, zorder=1)
        mean = [finite_mean([per_seed[i][j] for i in range(len(SEEDS))])
                for j in range(len(grid))]
        ax_a.plot(grid, mean, color=COLOR[m], lw=2.6, label=LABEL[m], zorder=3)

    ax_a.axvline(HEM_TARGET, color="k", ls="--", lw=1.6, zorder=4)
    ax_a.annotate("HEM's target: 80%\n(ceiling not reported)",
                  xy=(HEM_TARGET, 15.0), xytext=(0.845, 30.0),
                  fontsize=8.5, va="center", ha="left",
                  arrowprops=dict(arrowstyle="->", lw=1.0, color="black",
                                  connectionstyle="arc3,rad=0.22"))
    # Mark the single crossing, which is the whole point of the panel. Its
    # location is computed, not eyeballed, and it is drawn as a band because the
    # grid cannot resolve it to a point: the two six-seed means are exactly
    # equal over [0.615, 0.635] and FedDyn leads at every point from 0.665 on.
    # (verified_numbers.md 9.10; the 4-seed draft's t ~ 0.72 is superseded.)
    ax_a.axvspan(CROSSING_BAND[0], CROSSING_BAND[1], color="#b0b0b0",
                 alpha=0.45, zorder=0)
    ax_a.annotate("crossing band\n$t\\approx0.64$",
                  xy=(CROSSING, 3.9), xytext=(0.695, 13.5),
                  fontsize=8.5, ha="left", va="center",
                  arrowprops=dict(arrowstyle="->", lw=1.0, color="black",
                                  connectionstyle="arc3,rad=0.18"))
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
    # Layout constants: six seed cells occupy x = 0..5; the per-row verdict tag
    # starts just right of the last cell. (These were sized for four seeds once
    # and the tag then sat on top of the two cells added in the six-seed
    # expansion -- hence the explicit constants rather than magic numbers.)
    NCELL = len(SEEDS)
    TAG_X = NCELL + 0.7          # first tag character, clear of the last cell
    XMAX = NCELL + 6.8           # room for the longest tag ("... SCAF x1, 1 tie")
    BOX_W = NCELL + 1.1          # HEM highlight box spans the full cell strip
    rows = [0.60, 0.70, 0.75, 0.80, 0.85, 0.90]
    SHORT = {"fedavg": "FedAvg", "feddyn": "FedDyn", "scaffold": "SCAF"}
    # two-letter codes for tie cells, where up to three methods must fit
    SHORT2 = {"fedavg": "FA", "feddyn": "FD", "scaffold": "SC"}
    ax_b.set_xlim(-0.75, XMAX)
    ax_b.set_ylim(-0.6, len(rows) - 0.4)
    for i, t in enumerate(rows):
        cells = []                      # per seed: ("win", m) | ("tie", [m]) | ("na", None)
        for s in SEEDS:
            vals = {m: rtt(traces[m][s], t) for m in METHODS}
            fin = {m: v for m, v in vals.items() if np.isfinite(v)}
            if not fin:
                cells.append(("na", None))
                continue
            mn = min(fin.values())
            win = sorted(m for m, v in fin.items() if v == mn)
            # A tie at the minimum is a tie, NOT a win for whichever method
            # dict order happens to favour: Section 3.1/3.4 and the text of
            # Section 4 count "outright wins" and "ties" separately, and the
            # figure must use the same rule or the cells contradict the text.
            cells.append(("win", win[0]) if len(win) == 1 else ("tie", win))
        for j, (kind, payload) in enumerate(cells):
            if kind == "na":
                ax_b.add_patch(plt.Rectangle((j - 0.42, i - 0.42), 0.84, 0.84,
                                             facecolor="#dddddd",
                                             edgecolor="#999999"))
                ax_b.text(j, i, "n/a", ha="center", va="center", fontsize=7)
            elif kind == "win":
                ax_b.add_patch(plt.Rectangle((j - 0.42, i - 0.42), 0.84, 0.84,
                                             facecolor=COLOR[payload],
                                             edgecolor="white"))
                ax_b.text(j, i, SHORT[payload], ha="center", va="center",
                          fontsize=6.5, color="white", fontweight="bold")
            else:
                ax_b.add_patch(plt.Rectangle((j - 0.42, i - 0.42), 0.84, 0.84,
                                             facecolor="white",
                                             edgecolor="#666666", lw=1.1,
                                             ls=(0, (2, 1.4))))
                ax_b.text(j, i, "=".join(SHORT2[m] for m in payload),
                          ha="center", va="center", fontsize=6.0,
                          color="#333333")
        outright = {}
        ties = 0
        for kind, payload in cells:
            if kind == "win":
                outright[payload] = outright.get(payload, 0) + 1
            elif kind == "tie":
                ties += 1
        hemt = abs(t - HEM_TARGET) < 1e-9
        parts = ["%s x%d" % (SHORT[m], k) for m, k in
                 sorted(outright.items(), key=lambda kv: -kv[1])]
        if ties:
            parts.append("%d tie%s" % (ties, "s" if ties > 1 else ""))
        if hemt:
            head = "HEM's line: SPLIT\n" if len(outright) > 1 or ties else ""
            tag = head + ", ".join(parts)
        elif len(outright) == 1 and ties == 0:
            tag = "%s  UNANIMOUS" % LABEL[list(outright)[0]]
        else:
            tag = "SPLIT  " + ", ".join(parts)
        ax_b.text(TAG_X, i, tag, va="center", fontsize=8.5,
                  fontweight="bold" if len(outright) == 1 and ties == 0
                  else "normal",
                  color=COLOR[list(outright)[0]]
                  if len(outright) == 1 and ties == 0 else "#444444")
        ax_b.text(-0.52, i, "%.2f" % t, va="center", ha="right", fontsize=9,
                  fontweight="bold" if hemt else "normal",
                  color="black" if hemt else "#333333")
        if hemt:
            ax_b.add_patch(plt.Rectangle((-0.55, i - 0.48), BOX_W, 0.96,
                                         fill=False, edgecolor="black",
                                         lw=1.8, ls="--"))

    ax_b.set_yticks([])
    ax_b.set_xticks(range(len(SEEDS)))
    ax_b.set_xticklabels(["seed %d" % s for s in SEEDS], fontsize=8)
    ax_b.tick_params(axis="x", length=0, pad=2)
    # hide everything except the x tick labels (axis("off") would hide those
    # too, and the seed index is the only way to read the columns)
    for sp in ("top", "right", "left", "bottom"):
        ax_b.spines[sp].set_visible(False)
    ax_b.set_title("(b)  Same data, same budget: the winner flips with $t$ "
                   "(MNIST, 6 seeds)", fontsize=11, loc="left")
    ax_b.text(-0.52, len(rows) - 0.62, "$t$", ha="right", va="bottom",
              fontsize=10, style="italic")


# ------------------------------------------------------------------- panel c
def panel_c(ax):
    # Ceilings recomputed from the traces on disk, so the figure and the
    # analysis cannot drift apart. The HEM row keeps HEM's own published
    # client-accuracy numbers (SCAFFOLD 0.86), which are the fairest reading of
    # "the ceiling HEM's 80% target is measured against".
    ours = {ds: ceiling(ds)[0] for ds in ("mnist", "fashion", "cifar10")}
    # Two visual variables, each carrying one meaning. Hue separates "ours"
    # (Okabe-Ito blue) from "external published data" (Okabe-Ito orange); the
    # published bar is additionally hatched, so the distinction survives
    # greyscale printing and any form of colour-vision deficiency. The four bars
    # are identified by their x-axis labels, not by colour.
    groups = [
        ("Ours\nMNIST", ours["mnist"], "#0072B2", None),
        ("HEM (published)\nCIFAR-10, 100 cl.", 0.86, "#E69F00", "//"),
        ("Ours\nFashion-MNIST", ours["fashion"], "#0072B2", None),
        ("Ours\nCIFAR-10", ours["cifar10"], "#0072B2", None),
    ]
    xs = np.arange(len(groups))
    vals = [g[1] for g in groups]
    bars = ax.bar(xs, vals, color=[g[2] for g in groups],
                  hatch=[g[3] for g in groups],
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
            # the headroom label sits inside the bar (bars exceed 0.80 here),
            # so it must be light-on-dark rather than the default dark grey
            ax.text(x, HEM_TARGET - 0.095, "headroom\n%+.1f pt" % (100 * (v - HEM_TARGET)),
                    ha="center", fontsize=8, color="white",
                    fontweight="bold")

    ax.set_xticks(xs)
    ax.set_xticklabels([g[0] for g in groups], fontsize=8.5)
    ax.set_ylabel("best reachable accuracy")
    ax.set_ylim(0, 1.18)
    ax.set_title("(c)  One nominal target, three meanings: headroom below the "
                 "attainable maximum", fontsize=10.5, loc="left")
    ax.grid(axis="y", alpha=0.25, ls=":")


# NOTE: a fourth panel illustrating the spread of literature target values was
# removed. It drew on five hand-picked papers, one of which (FedZMG) could not be
# verified against any resolvable identifier, and a five-point illustration is
# now strictly worse evidence than the screened survey the paper actually
# reports (Section 3.4: N = 58 studies, targets spanning 30%-99.98%). Survey
# figures live in the released extraction table, not in a hand-drawn panel.


def main():
    fig = plt.figure(figsize=(12.6, 8.3))
    # bottom=0.115 reserves a caption strip under the panels; the reading note
    # lives there. (It used to sit at the top at y=0.928, where it ran straight
    # through the two panel titles once the suptitle wrapped to two lines.)
    gs = fig.add_gridspec(2, 2, hspace=0.42, wspace=0.30,
                          left=0.075, right=0.975, top=0.905, bottom=0.115)
    panel_ab(fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]))
    panel_c(fig.add_subplot(gs[1, :]))

    fig.suptitle("Figure 1.  \"Which federated algorithm converges fastest?\" "
                 "is answered by protocol choices nobody reports.",
                 fontsize=13.5, fontweight="bold", y=0.972)
    fig.text(0.075, 0.052,
             "Reading note. Rounds-to-target in all panels is a FIRST-PASSAGE "
             "time: the first round at which test accuracy reaches $t$; a "
             "method that never reaches $t$ within the 60-round budget is "
             "censored, not ranked. See Section 3.3 for the same traces read "
             "with window-mean decision statistics, and Section 3.0 for the "
             "censoring convention used by every mean quoted here.",
             fontsize=8.2, style="italic", ha="left", va="center",
             wrap=True)

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
