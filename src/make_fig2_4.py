"""Figures 2-4: the three supporting panels the manuscript needs.

The paper carried eight tables and one figure. These three panels are each
generated from already-published artefacts -- NO training, NO new traces:

  Figure 2  Decay probe. Per-seed FedAvg-minus-SCAFFOLD late-accuracy gap on
            CIFAR-10 and MNIST across the four learning-rate decay settings.
            Source: results/rank_inv/_decay_{cifar,mnist}_s{0..5}.json.
            This is the picture behind Tables 3 and 4: the gap is not monotone
            and the six seeds do not move together.

  Figure 3  One trace set, three decision statistics. Mean RTT of FedDyn under
            first passage / 5-round mean / 10-round mean, per cell, with the
            FedAvg reference beside it.
            Source: results/rtt_stat_compare.json (the artefact behind Table 5).

  Figure 4  Target values reported by the 58 included studies.
            Source: results/survey_extraction.csv, pool == "main".
            This is the single most quotable finding in the paper and it was
            carried as prose only.

Style follows Figure 1: Okabe-Ito palette, 300 dpi PNG plus vector PDF, and a
machine-readable JSON companion beside each figure.

Usage:  python src/make_fig2_4.py
"""
from __future__ import annotations

import csv
import json
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
RES = os.path.join(ROOT, "results")
RI = os.path.join(RES, "rank_inv")
OUT = os.path.join(RES, "figures")
os.makedirs(OUT, exist_ok=True)

# Okabe-Ito qualitative palette (same as Figure 1).
C_FEDAVG = "#0072B2"
C_SCAFFOLD = "#009E73"
C_FEDDYN = "#E69F00"
C_GREY = "#4D4D4D"
C_LIGHT = "#BDBDBD"

SEEDS = [0, 1, 2, 3, 4, 5]
DECAYS = ["0.9", "0.95", "0.98", "1.0"]
DECAY_X = {"0.9": 0.90, "0.95": 0.95, "0.98": 0.98, "1.0": 1.00}


def _style(ax, xlabel, ylabel):
    ax.set_xlabel(xlabel, fontsize=9.5)
    ax.set_ylabel(ylabel, fontsize=9.5)
    ax.tick_params(labelsize=8.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.grid(axis="y", alpha=0.25, linewidth=0.6)
    ax.set_axisbelow(True)


# --------------------------------------------------------------- Figure 2
def load_decay(ds):
    """{seed: {decay: gap_in_points}}, and the per-decay mean."""
    per_seed = {}
    for s in SEEDS:
        p = os.path.join(RI, "_decay_%s_s%d.json" % (ds, s))
        if not os.path.exists(p):
            continue
        d = json.load(open(p))
        row = {}
        for dec in DECAYS:
            a = d["fedavg"][dec]["late"]
            b = d["scaffold"][dec]["late"]
            row[DECAY_X[dec]] = 100.0 * (a - b)
        per_seed[s] = row
    return per_seed


def fig2():
    data = {ds: load_decay(ds) for ds in ("cifar", "mnist")}
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.35), sharex=True)
    titles = {"cifar": "(a) CIFAR-10, \u03b1 = 0.1",
              "mnist": "(b) MNIST, \u03b1 = 0.1"}
    ymax = 0
    for ax, ds in zip(axes, ("cifar", "mnist")):
        rows = data[ds]
        xs = [DECAY_X[d] for d in DECAYS]
        for s in sorted(rows):
            ys = [rows[s][x] for x in xs]
            ax.plot(xs, ys, "-o", color=C_LIGHT, linewidth=1.0,
                    markersize=3.2, zorder=2,
                    label="one seed" if s == 0 else None)
            ymax = max(ymax, max(ys))
        mean = [np.mean([rows[s][x] for s in rows]) for x in xs]
        ax.plot(xs, mean, "-o", color=C_FEDAVG, linewidth=2.2,
                markersize=5.5, zorder=4, label="mean over 6 seeds")
        ax.axhline(0.0, color=C_GREY, linewidth=0.9, zorder=3)
        ax.axhspan(-0.09, 4.28, color=C_SCAFFOLD, alpha=0.10, zorder=1)
        ax.set_title(titles[ds], fontsize=9.4, loc="left")
        _style(ax, "learning-rate decay",
               "FedAvg \u2212 SCAFFOLD, late acc. (points)")
        ax.set_xticks(xs)
        ax.set_xticklabels(["0.90", "0.95", "0.98", "1.00"])
        ax.yaxis.set_major_locator(MultipleLocator(20))

    axes[0].legend(fontsize=7.6, frameon=False, loc="upper left")
    axes[0].annotate("shaded band: 95% CI of the\nmean gap at decay 0.90",
                     xy=(0.04, 0.055), xycoords="axes fraction",
                     fontsize=6.6, style="italic", color=C_GREY, va="bottom")
    fig.suptitle("Figure 2.  One knob, four settings: the FedAvg\u2013SCAFFOLD gap is\n"
                 "not monotone and the seeds do not move together.",
                 fontsize=10.0, x=0.02, ha="left", va="top")
    fig.text(0.02, 0.012,
             "Late accuracy = mean test accuracy over the final ten rounds; "
             "positive = FedAvg ahead. Recomputed from the released decay "
             "probes (Section 3.2).",
             fontsize=7.0, style="italic")
    fig.subplots_adjust(left=0.115, right=0.985, bottom=0.20, top=0.795,
                        wspace=0.34)
    png = os.path.join(OUT, "fig2_decay_probe.png")
    fig.savefig(png, dpi=300)
    fig.savefig(os.path.join(OUT, "fig2_decay_probe.pdf"))
    plt.close(fig)
    print("wrote", png)

    dump = {ds: {str(s): {"%.2f" % k: round(v, 4) for k, v in row.items()}
                 for s, row in rows.items()} for ds, rows in data.items()}
    with open(os.path.join(OUT, "fig2_data.json"), "w") as fh:
        json.dump(dump, fh, indent=1)
    return dump


# --------------------------------------------------------------- Figure 3
def fig3():
    d = json.load(open(os.path.join(RES, "rtt_stat_compare.json")))
    cells = ["mnist|a0.05", "mnist|a0.1", "mnist|a0.3",
             "fashion|a0.05", "fashion|a0.1", "fashion|a0.3",
             "cifar10|a0.1"]
    short = {"mnist|a0.05": "MNIST\n\u03b1=0.05", "mnist|a0.1": "MNIST\n\u03b1=0.1",
             "mnist|a0.3": "MNIST\n\u03b1=0.3",
             "fashion|a0.05": "Fashion\n\u03b1=0.05",
             "fashion|a0.1": "Fashion\n\u03b1=0.1",
             "fashion|a0.3": "Fashion\n\u03b1=0.3",
             "cifar10|a0.1": "CIFAR-10\n\u03b1=0.1"}
    stats = [("first", "first\npassage", C_FEDDYN),
             ("ma5", "5-round\nmean", C_FEDAVG),
             ("ma10", "10-round\nmean", C_SCAFFOLD)]

    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.05),
                             gridspec_kw={"width_ratios": [4.4, 3.0]})

    # (a) grouped bars: FedDyn mean RTT under the three statistics
    ax = axes[0]
    w = 0.26
    x = np.arange(len(cells))
    for i, (key, lab, col) in enumerate(stats):
        vals = []
        for c in cells:
            node = d["per_cell"][c]["methods"].get("feddyn", {})
            v = node.get(key, {}).get("mean_rtt")
            vals.append(np.nan if v is None else float(v))
        ax.bar(x + (i - 1) * w, vals, w, label=lab, color=col,
               edgecolor="white", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels([short[c] for c in cells], fontsize=6.8)
    ax.set_title("(a) FedDyn: mean rounds-to-target", fontsize=9.6, loc="left")
    _style(ax, "", "rounds")
    ax.legend(fontsize=7.6, frameon=False, ncol=3, loc="upper left")

    # (b) the same, as a multiple of the first-passage figure
    ax = axes[1]
    for i, (key, lab, col) in enumerate(stats):
        vals = []
        for c in cells:
            node = d["per_cell"][c]["methods"].get("feddyn", {})
            base = node.get("first", {}).get("mean_rtt")
            v = node.get(key, {}).get("mean_rtt")
            vals.append(np.nan if (v is None or base in (None, 0)) else v / base)
        ax.bar(x + (i - 1) * w, vals, w, label=lab, color=col,
               edgecolor="white", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace("|", " ").replace("mnist", "MNIST")
                        .replace("fashion", "Fash ").replace("cifar10", "CIFAR")
                        .replace("a0.", "\u03b1.") for c in cells],
                       fontsize=6.2, rotation=45, ha="right",
                       rotation_mode="anchor")
    ax.axhline(1.0, color=C_GREY, linewidth=0.9)
    ax.set_title("(b) relative to first passage", fontsize=9.6, loc="left")
    _style(ax, "", "multiple of the\nfirst-passage value")
    ax.set_ylim(0, 3.4)

    fig.suptitle("Figure 3.  The same 294 traces, three decision statistics:\n"
                 "nothing about the runs changed, only the reading rule.",
                 fontsize=10.0, x=0.02, ha="left", va="top")
    fig.text(0.02, 0.012,
             "Means over the six seeds at each cell's $t_{ref}$. Source of "
             "Table 5; no new training.",
             fontsize=7.0, style="italic")
    fig.subplots_adjust(left=0.085, right=0.985, bottom=0.27, top=0.80,
                        wspace=0.36)
    png = os.path.join(OUT, "fig3_statistic.png")
    fig.savefig(png, dpi=300)
    fig.savefig(os.path.join(OUT, "fig3_statistic.pdf"))
    plt.close(fig)
    print("wrote", png)

    dump = {c: {k: d["per_cell"][c]["methods"].get("feddyn", {}).get(k, {}).get("mean_rtt")
                for k in ("first", "ma5", "ma10")} for c in cells}
    with open(os.path.join(OUT, "fig3_data.json"), "w") as fh:
        json.dump(dump, fh, indent=1)
    return dump


# --------------------------------------------------------------- Figure 4
def fig4():
    rows = list(csv.DictReader(
        open(os.path.join(RES, "survey_extraction.csv"), encoding="utf-8")))
    main = [r for r in rows if r["pool"] == "main"]
    vals = sorted(float(r["target_value"]) for r in main if r["target_value"])
    # "target_justified" is coded no / post_hoc / relative_to_centralized /
    # post_hoc_baseline_peak. Anything other than "no" is a stated reason.
    just = [float(r["target_value"]) for r in main
            if r["target_value"]
            and r["target_justified"].strip().lower() not in ("", "no")]

    fig, (ax, ax2) = plt.subplots(
        1, 2, figsize=(7.6, 3.5),
        gridspec_kw={"width_ratios": [3.6, 1.15]})

    bins = np.arange(0.30, 1.025, 0.05)
    n, _, patches = ax.hist(vals, bins=bins, color=C_FEDAVG,
                            edgecolor="white", linewidth=0.6)
    # mark the studies that justify their number
    for v in just:
        ax.plot([v], [0.35], "v", color=C_FEDDYN, markersize=5.5,
                clip_on=False, zorder=5)
    ax.set_xlim(0.28, 1.02)
    ax.set_xticks([0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    ax.set_xticklabels(["30", "40", "50", "60", "70", "80", "90", "100"])
    ax.yaxis.set_major_locator(MultipleLocator(2))
    ax.set_title("(a) reported target accuracy (%%): n = %d studies" % len(vals),
                 fontsize=9.6, loc="left")
    _style(ax, "target accuracy (%)", "studies")
    ax.annotate("median 80%\nspan 30% \u2013 99.98%", xy=(0.80, max(n) * 0.82),
                fontsize=8.0, ha="center",
                bbox=dict(boxstyle="round,pad=0.28", fc="white",
                          ec=C_GREY, lw=0.6))

    # (b) the five Table 6 items that bear directly on the paper's thesis.
    # Each is derived here from the extraction CSV and ASSERTED against the
    # number printed in Table 6, so the figure cannot drift from the table.
    def n_yes(col):
        return sum(1 for r in main if r[col].strip().lower()
                   in ("yes", "y", "true", "1", "reported"))

    def n_specified(col):
        return sum(1 for r in main
                   if r[col].strip().lower() not in ("", "unspecified", "no"))

    items = [
        ("statistic defined", n_yes("chk4_statistic_definition"), 3),
        ("reason given for\nthe target", len(just), 4),
        ("per-seed results\nreported", n_yes("per_seed_results_reported"), 11),
        ("censoring\nconvention", n_yes("censoring_reported"), 14),
        ("heterogeneity\nparameter", n_specified("noniid_parameter"), 15),
        ("final-window\ndispersion", n_yes("stability_measure_reported"), 1),
    ]
    for lab, got, want in items:
        assert got == want, "Figure 4 disagrees with Table 6 on %r: %d vs %d" % (
            lab.replace("\n", " "), got, want)

    rates = [100.0 * n / len(main) for _, n, _ in items]
    y = np.arange(len(items))[::-1]
    ax2.barh(y, rates, color=C_SCAFFOLD, edgecolor="white", linewidth=0.5)
    ax2.set_yticks(y)
    ax2.set_yticklabels([lab for lab, _, _ in items], fontsize=7.0)
    ax2.set_ylim(-0.65, len(items) - 0.35)
    ax2.set_xlim(0, 105)
    for yi, r, (_, n, _) in zip(y, rates, items):
        ax2.text(r + 2.5, yi, "%d/58" % n, va="center", fontsize=7.4)
    ax2.set_title("(b) Table 6 items", fontsize=9.4, loc="left")
    _style(ax2, "% of the 58 studies", "")
    ax2.grid(axis="x", alpha=0.25, linewidth=0.6)

    handles = [Line2D([], [], marker="v", color=C_FEDDYN, linestyle="",
                      label="a stated reason for the\nvalue (%d of 58)" % len(just))]
    ax.legend(handles=handles, fontsize=7.6, frameon=False, loc="upper left")

    fig.suptitle("Figure 4.  What the 58 included studies actually report:\n"
                 "targets from 30% to 99.98%, and almost no protocol.",
                 fontsize=10.0, x=0.02, ha="left", va="top")
    fig.text(0.02, 0.012,
             "Screened from 1,136 records; every included paper opened and "
             "searched. Panel (b): share of the 58 studies disclosing each item "
             "(Section 3.4).",
             fontsize=7.0, style="italic")
    fig.subplots_adjust(left=0.09, right=0.985, bottom=0.175, top=0.845,
                        wspace=0.42)
    png = os.path.join(OUT, "fig4_survey_targets.png")
    fig.savefig(png, dpi=300)
    fig.savefig(os.path.join(OUT, "fig4_survey_targets.pdf"))
    plt.close(fig)
    print("wrote", png)

    dump = {"n": len(vals), "min": min(vals), "max": max(vals),
            "median": float(np.median(vals)),
            "justified": len(just),
            "disclosure": {lab.replace("\n", " "): [n, round(r, 2)]
                           for (lab, n, _), r in zip(items, rates)}}
    with open(os.path.join(OUT, "fig4_data.json"), "w") as fh:
        json.dump(dump, fh, indent=1)
    return dump


if __name__ == "__main__":
    a = fig2()
    b = fig3()
    c = fig4()
    print(json.dumps(c, indent=1))
