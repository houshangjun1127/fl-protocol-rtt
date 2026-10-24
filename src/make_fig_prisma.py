# -*- coding: utf-8 -*-
"""Figure 5 (supplementary): PRISMA-style flow of the survey.

WHY
---
Section 3.4 reports a survey of 58 studies. The flow from 1,136 identified
records to 58 inclusions is described in prose, but prose hides the one number
a reader needs in order to judge the flow: the 139 records queued for
full-text retrieval are NOT the 238 full texts actually adjudicated, because
the harvest was deliberately continued into the lower tiers after abstract
screening turned out to be a weak filter. A diagram makes that visible; a
paragraph does not reliably.

Conventions shared with Figures 1-4: Agg backend, 300 dpi PNG plus PDF, no
information encoded in colour alone (every box is labelled, and the single
"deviation" arrow carries a text annotation as well as a distinct dash
pattern).

Boxes are drawn as text with a bbox so matplotlib sizes them to their
contents. The first version used FancyBboxPatch with explicit geometry, and the
boxes collided: the patch pad is specified in the same data units as the box,
so pad=0.02 with a box height of 0.105 inflated every box by nearly 40%.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIGDIR = os.path.join(ROOT, "results", "figures")

FLOW = [
    ("Records identified\nSemantic Scholar + arXiv + OpenAlex\n2017-2026",
     "1,136", "#ffffff", "#333333"),
    ("After de-duplication\nDOI -> arXiv id -> title + surname + year",
     "1,082", "#ffffff", "#333333"),
    ("Title/abstract screening\nT1 57 | T2 82 | T3 152 | T0 845",
     "1,082", "#ffffff", "#333333"),
    ("Queued for full-text retrieval (N2)\nT1 + T2 only",
     "139", "#ffffff", "#333333"),
    ("Full texts obtained and adjudicated\nharvest continued into T3 and T0",
     "238", "#fdf3f0", "#a04030"),
    ("Distinct records (2 duplicate local copies removed;\n219 match a tier, 17 do not)",
     "236", "#ffffff", "#333333"),
    ("Main pool (N3)\nI1-I5 met, E1-E6 clear",
     "58", "#eef4ee", "#2e6b2e"),
    ("Secondary pool\nneighbouring constructions, not counted",
     "15", "#f2f2f2", "#666666"),
]

EXCL = [("E2  no threshold-timing construction", 118),
        ("E3(d)  timed quantity is not rounds", 15),
        ("E3(c)  loss/gradient convergence", 14),
        ("E3  other", 9),
        ("E6  not federated / out of window", 5),
        ("E4  review", 1),
        ("E3(b)", 1)]


def main():
    os.makedirs(FIGDIR, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9.0, 10.4))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    CX = 0.46                      # centre of the main column
    ys = [0.93, 0.807, 0.684, 0.561, 0.438, 0.315, 0.192, 0.07]

    centres = []
    for (text, n, fc, ec), y in zip(FLOW, ys):
        ax.text(CX, y + 0.014, text, ha="center", va="center", fontsize=8.2,
                linespacing=1.45,
                bbox=dict(boxstyle="round,pad=0.55", facecolor=fc,
                          edgecolor=ec, linewidth=1.2))
        ax.text(CX, y - 0.031, n, ha="center", va="center", fontsize=11,
                fontweight="bold", color=ec)
        centres.append(y)

    # arrows between consecutive boxes
    labels = ["54 duplicates removed", "4 tiers assigned", "T1+T2 queued first",
              None, "2 duplicates removed", "included",
              "registered separately"]
    for i in range(len(FLOW) - 1):
        y1 = ys[i] - 0.052
        y2 = ys[i + 1] + 0.052
        dashed = (i == 3)
        ax.annotate("", xy=(CX, y2), xytext=(CX, y1),
                    arrowprops=dict(arrowstyle="-|>", mutation_scale=12,
                                    linewidth=1.2,
                                    color="#a04030" if dashed else "#333333",
                                    linestyle=":" if dashed else "-"))
        if labels[i]:
            ax.text(CX + 0.015, (y1 + y2) / 2.0, labels[i], ha="left",
                    va="center", fontsize=7.4, style="italic",
                    color="#a04030" if dashed else "#333333")

    # deviation annotation, placed to the left where there is room
    ax.text(0.012, ys[3] - 0.075,
            "DEVIATION (logged):\nharvest continued into T3 and T0 --\n"
            "abstract screening was a weak filter\n(32 of 125 adjudicated T0\n"
            "records were included, not far\nbelow T1's rate)",
            ha="left", va="center", fontsize=7.2, color="#a04030",
            bbox=dict(boxstyle="round,pad=0.35", facecolor="#fdf3f0",
                      edgecolor="#a04030", linewidth=0.9))

    # exclusion panel, right column
    EX = 0.795
    ax.text(EX, ys[5] + 0.090,
            "Excluded, one primary code each\n(n = 163)",
            ha="center", va="center", fontsize=8.4, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.35", facecolor="#ffffff",
                      edgecolor="#666666", linewidth=0.9))
    yy = ys[5] + 0.042
    for label, n in EXCL:
        ax.text(EX, yy, "%s   %d" % (label, n), ha="center", va="top",
                fontsize=7.2)
        yy -= 0.030
    ax.annotate("", xy=(EX - 0.115, ys[5] + 0.090), xytext=(CX + 0.185, ys[5]),
                arrowprops=dict(arrowstyle="-|>", mutation_scale=10,
                                linewidth=1.0, color="#666666",
                                connectionstyle="arc3,rad=-0.15"))

    ax.set_title("Figure 5. Survey flow (PRISMA-style). Every included study "
                 "was opened and searched.", fontsize=10.5, loc="left",
                 pad=10)
    fig.text(0.02, 0.012,
             "N2 = 139 counts the records QUEUED first (tiers T1+T2); 238 "
             "counts the full texts actually read. The gap is a logged "
             "deviation, not an error: see Section 3.4.",
             fontsize=7.4, ha="left", va="bottom", style="italic")

    png = os.path.join(FIGDIR, "fig5_survey_flow.png")
    pdf = os.path.join(FIGDIR, "fig5_survey_flow.pdf")
    fig.savefig(png, dpi=300, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    print("wrote", png)
    print("wrote", pdf)

    log = os.path.join(ROOT, "results", "survey_fulltext_log.md")
    if os.path.exists(log):
        txt = open(log, encoding="utf-8").read()
        for tok in ("1136", "1082", "139", "238", "58"):
            if tok not in txt:
                print("WARNING: %s not found in the screening log" % tok)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
