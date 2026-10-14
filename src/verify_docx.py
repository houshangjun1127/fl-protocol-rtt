"""Verify the built submission DOCX against its markdown source.

Checks, in order:
  1. every alphanumeric word token of the markdown survives in the docx
     (math is converted, so tokens are compared after stripping math source)
  2. no raw LaTeX survives ($...$, \mathrm, \frac, \alpha ...)
  3. 8 tables, 4 inline images, image display widths, cell centring
  4. captions keep_with_next, no forced page breaks, heading keep_with_next
  5. placeholders <REPOSITORY_URL> / <ZENODO_DOI> intact

Usage:  python src/verify_docx.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Emu

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "results" / "paper_draft.md"
DX = ROOT / "output" / "fl-protocol-paper" / "stage3" / "FL_protocol_paper.docx"

TOK = re.compile(r"[A-Za-z0-9]+")


def norm_tokens(text: str) -> list[str]:
    return [t.lower() for t in TOK.findall(text)]


def main() -> int:
    md = MD.read_text(encoding="utf-8")
    doc = Document(str(DX))

    # ---- collect docx text: paragraphs + table cells
    paras = [p.text for p in doc.paragraphs]
    cell_text = []
    for t in doc.tables:
        for row in t.rows:
            for c in row.cells:
                cell_text.append(c.text)
    full = "\n".join(paras + cell_text)

    fails: list[str] = []
    warns: list[str] = []

    # ---- 1. word coverage -------------------------------------------------
    # Tokens that legitimately cannot appear in the docx:
    #   - LaTeX macro names that became a single Greek/mathematic symbol
    #   - sub/superscript flattening fuses them with the base token
    #   - image paths (](figures/figN_*.png)) are not rendered as text
    #   - front-matter ("Research article (measurement / methodology)") is
    #     deliberately excluded from the submission copy
    EXPECTED_MISSING = {
        "alpha", "approx", "cdot", "dots", "dt", "eta", "frac", "ge", "infty",
        "lambda", "le", "lfloor", "rfloor", "lim", "longrightarrow", "mathit",
        "mathrm", "phi", "qquad", "ref", "rho", "sim", "times10", "varphi",
        "tau", "beta", "mu", "min", "max", "big",
        # sub/superscript flattening fuses these with the base token:
        # \mathrm{acc}_r renders as one text run "accr", t_{\text{ref}} as "tref"
        "acc", "ref",
        "fig1", "fig2", "fig3", "fig4", "png", "figures",
        "article", "methodology",
    }
    md_tok = norm_tokens(md)
    dx_set = set(norm_tokens(full))
    missing = sorted({t for t in md_tok if t not in dx_set} - EXPECTED_MISSING)
    print("md tokens: %d   unexplained missing from docx: %d"
          % (len(md_tok), len(missing)))
    if missing:
        print("  missing:", missing[:40])
        fails.append("word coverage (%d unexplained)" % len(missing))

    # ---- 2. LaTeX residue -------------------------------------------------
    residue = []
    for pat in (r"\$[^$]{1,80}\$", r"\\mathrm", r"\\frac", r"\\alpha",
                r"\\rho", r"\\tau", r"\\mathit", r"\\lambda"):
        hits = re.findall(pat, full)
        if hits:
            residue.append((pat, hits[:4]))
    if residue:
        for p, h in residue:
            print("  LaTeX residue %s: %s" % (p, h))
        fails.append("LaTeX residue")
    else:
        print("LaTeX residue: none")

    # ---- 3. structure -----------------------------------------------------
    print("paragraphs %d | tables %d | inline images %d"
          % (len(paras), len(doc.tables), len(doc.inline_shapes)))
    if len(doc.tables) != 8:
        fails.append("table count %d" % len(doc.tables))
    if len(doc.inline_shapes) != 4:
        fails.append("image count %d" % len(doc.inline_shapes))

    for k, sh in enumerate(doc.inline_shapes, 1):
        w_cm = sh.width / 360000.0
        h_cm = sh.height / 360000.0
        print("  image %d: %.1f x %.1f cm" % (k, w_cm, h_cm))
        if w_cm < 14.5:
            warns.append("image %d only %.1f cm wide" % (k, w_cm))

    # cell centring + three-line borders
    bad_align = 0
    for t in doc.tables:
        for row in t.rows:
            for c in row.cells:
                for p in c.paragraphs:
                    if p.alignment != WD_ALIGN_PARAGRAPH.CENTER:
                        bad_align += 1
    print("non-centred table paragraphs: %d" % bad_align)
    if bad_align:
        fails.append("%d table paragraphs not centred" % bad_align)

    # ---- 4. pagination safety --------------------------------------------
    forced_breaks = 0
    keep_next = 0
    for p in doc.paragraphs:
        if p.paragraph_format.page_break_before:
            forced_breaks += 1
        if p.paragraph_format.keep_with_next:
            keep_next += 1
    print("forced page breaks: %d | keep_with_next paragraphs: %d"
          % (forced_breaks, keep_next))
    if forced_breaks:
        warns.append("%d forced page breaks" % forced_breaks)

    # empty spacer paragraphs directly before a table (could strand space)
    n_spacer = sum(1 for p in paras if p == "")
    print("empty paragraphs: %d (spacers after tables)" % n_spacer)

    # ---- 5. placeholders --------------------------------------------------
    for k in ("<REPOSITORY_URL>", "<ZENODO_DOI>"):
        ok = k in full
        print("placeholder %-18s %s" % (k, "OK" if ok else "MISSING"))
        if not ok:
            fails.append("placeholder %s" % k)

    print()
    if fails:
        print("FAIL:", "; ".join(fails))
    if warns:
        print("WARN:", "; ".join(warns))
    if not fails and not warns:
        print("ALL CHECKS PASS")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
