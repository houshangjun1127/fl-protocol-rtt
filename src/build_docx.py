"""Build the TST submission DOCX from results/paper_draft.md.

Replaces the pipeline that was cleaned up after the previous build. Design
goals, in priority order:

  1. Content fidelity  -- not a word of the markdown may be lost or reworded.
  2. Math rendering    -- no raw $...$ LaTeX survives; variables italic,
                          \mathrm upright, real sub/superscript runs.
  3. TST layout        -- A4, 2.54/3.17 cm margins, Times New Roman 10.5 pt,
                          single column, 1.5 line spacing (SciOpen asks for
                          double spacing; 1.5 is the deliberate compromise --
                          double spacing pushes this manuscript past the same
                          guidelines' 30-page advice. Change LINE_SPACING below
                          if the editor wants strict compliance).
  4. Tables            -- 8 three-line tables, every cell centred.
  5. Figures           -- 4 figures at 300 dpi, centred, 15-16 cm wide, with
                          their captions kept on the same page.
  6. No large blank areas -- nothing forces a page break except the title page;
                          headings and figure+caption use keep_with_next only.

Usage:  python src/build_docx.py
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "results" / "paper_draft.md"
FIGDIR = ROOT / "results" / "figures"
OUT = ROOT / "output" / "fl-protocol-paper" / "stage3" / "FL_protocol_paper.docx"

FONT = "Times New Roman"
SIZE_BODY = Pt(10.5)
SIZE_TABLE = Pt(9)
SIZE_CAPTION = Pt(9)
LINE_SPACING = 1.5

# --------------------------------------------------------------------- math
GREEK = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
    "varepsilon": "ε", "zeta": "ζ", "eta": "η", "theta": "θ", "iota": "ι",
    "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "pi": "π",
    "rho": "ρ", "sigma": "σ", "tau": "τ", "upsilon": "υ", "phi": "φ",
    "varphi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω", "Gamma": "Γ",
    "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Phi": "Φ", "Psi": "Ψ",
    "Omega": "Ω", "infty": "∞", "cdot": "·", "times": "×", "approx": "≈",
    "ge": "≥", "geq": "≥", "le": "≤", "leq": "≤", "ne": "≠", "in": "∈",
    "notin": "∉", "subset": "⊂", "subseteq": "⊆", "cup": "∪", "cap": "∩",
    "to": "→", "rightarrow": "→", "leftarrow": "←", "Rightarrow": "⇒",
    "Longrightarrow": "⇒", "mapsto": "↦", "pm": "±", "mp": "∓", "sim": "∼",
    "propto": "∝", "ell": "ℓ", "hbar": "ℏ", "partial": "∂", "nabla": "∇",
    "sum": "∑", "prod": "∏", "int": "∫", "sqrt": "√", "angle": "∠",
    "lfloor": "⌊", "rfloor": "⌋", "lceil": "⌈", "rceil": "⌉", "langle": "⟨",
    "rangle": "⟩", "perp": "⊥", "parallel": "∥", "forall": "∀", "exists": "∃",
}
SKIP_MACROS = {"left", "right", "big", "Big", "bigg", "Bigg", "!", ";", ",",
               ":", ".", "quad", "qquad", "displaystyle", "limits", "nolimits"}
SPACE_MACROS = {",": " ", ";": " ", ":": " ", "quad": "  ", "qquad": "    "}
FUNCS = {"ln": "ln", "log": "log", "min": "min", "max": "max", "exp": "exp",
         "sin": "sin", "cos": "cos", "tan": "tan", "det": "det"}


def _find_group(s: str, i: int) -> tuple[str, int]:
    """s[i] == '{'. Return (inner, index_after_closing_brace)."""
    depth = 1
    k = i + 1
    while k < len(s) and depth:
        if s[k] == "{":
            depth += 1
        elif s[k] == "}":
            depth -= 1
        k += 1
    return s[i + 1:k - 1], k


def _needs_parens(s: str) -> bool:
    """True if s has a top-level +, - or space (so a/b needs parentheses)."""
    depth = 0
    for k, ch in enumerate(s):
        if ch in "{([":
            depth += 1
        elif ch in "})]":
            depth -= 1
        elif depth == 0 and ch in "+- " and k > 0:
            return True
    return False


def math_runs(e: str, italic: bool = True, sub: bool = False,
              sup: bool = False) -> list[tuple[str, bool, bool, bool]]:
    """Convert a LaTeX fragment to [(text, italic, sub, sup)] runs."""
    out: list[tuple[str, bool, bool, bool]] = []
    i = 0
    n = len(e)
    while i < n:
        c = e[i]
        if c == "\\":
            m = re.match(r"\\([a-zA-Z]+)", e[i:])
            if not m:  # \{ \} \% \* \, ...
                nxt = e[i + 1] if i + 1 < n else ""
                if nxt in "{}":
                    out.append((nxt, False, sub, sup))
                elif nxt == "*":
                    out.append(("*", False, sub, sup))
                elif nxt == "%":
                    out.append(("%", False, sub, sup))
                elif nxt in SPACE_MACROS:
                    out.append((SPACE_MACROS[nxt], False, sub, sup))
                i += 2
                continue
            name = m.group(1)
            i += len(m.group(0))
            if name in ("mathrm", "text", "mathit", "operatorname", "textbf"):
                inner, i = _find_group(e, i)
                out += math_runs(inner, italic=(name == "mathit"), sub=sub, sup=sup)
            elif name == "frac":
                num, i = _find_group(e, i)
                den, i = _find_group(e, i)
                a = "(%s)" % num if _needs_parens(num) else num
                b = "(%s)" % den if _needs_parens(den) else den
                out += math_runs(a + "/" + b, italic, sub, sup)
            elif name in SKIP_MACROS:
                continue
            elif name in SPACE_MACROS:
                out.append((SPACE_MACROS[name], False, sub, sup))
            elif name in FUNCS:
                out.append((FUNCS[name], False, sub, sup))
            elif name in GREEK:
                out.append((GREEK[name], italic, sub, sup))
            elif name == "dots" or name == "ldots":
                out.append(("…", False, sub, sup))
            elif name == "cdots":
                out.append(("⋯", False, sub, sup))
            else:
                out.append((name, False, sub, sup))
        elif c in "^_":
            is_sup = c == "^"
            i += 1
            if i < n and e[i] == "{":
                inner, i = _find_group(e, i)
            else:
                m2 = re.match(r"\\[a-zA-Z]+|\\.", e[i:])
                inner = m2.group(0) if m2 else (e[i] if i < n else "")
                i += len(inner)
            out += math_runs(inner, italic, sub=(not is_sup), sup=is_sup)
        elif c == "{":
            inner, i = _find_group(e, i)
            out += math_runs(inner, italic, sub, sup)
        elif c == "}":
            i += 1
        elif c.isalpha():
            out.append((c, italic, sub, sup))
            i += 1
        else:
            out.append((c, False, sub, sup))
            i += 1
    # merge adjacent equal-style runs
    merged: list[tuple[str, bool, bool, bool]] = []
    for t, it, sb, sp in out:
        if merged and merged[-1][1] == it and merged[-1][2] == sb and merged[-1][3] == sp:
            merged[-1] = (merged[-1][0] + t, it, sb, sp)
        else:
            merged.append((t, it, sb, sp))
    return merged


def add_math_runs(par, expr: str, size=SIZE_BODY, bold=False) -> None:
    for text, it, sb, sp in math_runs(expr):
        r = par.add_run(text)
        r.font.name = FONT
        r.font.size = size
        r.bold = bold
        r.italic = it
        if sb:
            r.font.subscript = True
        if sp:
            r.font.superscript = True


# ------------------------------------------------------------- inline parse
TOKEN = re.compile(r"(\$[^$]*\$)|(\*\*[^*]+\*\*)|(\*[^*\n]+\*)|(`[^`]+`)")


def add_inline(par, text: str, size=SIZE_BODY, base_bold=False,
               base_italic=False) -> None:
    pos = 0
    for m in TOKEN.finditer(text):
        if m.start() > pos:
            _plain(par, text[pos:m.start()], size, base_bold, base_italic)
        tok = m.group(0)
        if tok.startswith("$"):
            add_math_runs(par, tok[1:-1], size, bold=base_bold)
        elif tok.startswith("**"):
            # recurse: bold spans may contain $math$ and `code`
            add_inline(par, tok[2:-2], size, base_bold=True,
                       base_italic=base_italic)
        elif tok.startswith("`"):
            r = par.add_run(tok[1:-1])
            r.font.name = "Consolas"
            r.font.size = size
            r.bold = base_bold
        else:
            add_inline(par, tok[1:-1], size, base_bold=base_bold,
                       base_italic=True)
        pos = m.end()
    if pos < len(text):
        _plain(par, text[pos:], size, base_bold, base_italic)


def _plain(par, text, size, bold, italic):
    r = par.add_run(text)
    r.font.name = FONT
    r.font.size = size
    r.bold = bold
    r.italic = italic


# ------------------------------------------------------------------ tables
def set_cell_borders(cell, top=None, bottom=None):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = tcPr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tcPr.append(borders)
    for edge, val in (("top", top), ("bottom", bottom)):
        if val is None:
            continue
        el = borders.find(qn("w:%s" % edge))
        if el is None:
            el = OxmlElement("w:%s" % edge)
            borders.append(el)
        el.set(qn("w:val"), "single" if val else "nil")
        if val:
            el.set(qn("w:sz"), "8")
            el.set(qn("w:color"), "000000")


def add_table(doc, rows: list[list[str]]):
    """rows[0] = header. Three-line rule, centred cells, full text width."""
    n_cols = max(len(r) for r in rows)
    tbl = doc.add_table(rows=len(rows), cols=n_cols)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = True
    tblPr = tbl._tbl.tblPr
    # span the full text width so Word distributes columns evenly
    tblW = OxmlElement("w:tblW")
    tblW.set(qn("w:w"), "5000")
    tblW.set(qn("w:type"), "pct")
    tblPr.append(tblW)
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "autofit")
    tblPr.append(layout)
    # kill default grid style borders
    style = OxmlElement("w:tblStyle")
    style.set(qn("w:val"), "TableGrid")
    tblPr.append(style)
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement("w:%s" % edge)
        el.set(qn("w:val"), "nil")
        borders.append(el)
    tblPr.append(borders)

    for ri, row in enumerate(rows):
        for ci in range(n_cols):
            cell = tbl.cell(ri, ci)
            txt = row[ci] if ci < len(row) else ""
            par = cell.paragraphs[0]
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pf = par.paragraph_format
            pf.line_spacing = 1.0
            pf.space_before = Pt(1.5)
            pf.space_after = Pt(1.5)
            size = SIZE_TABLE
            if ri == 0:
                add_inline(par, txt, size=size, base_bold=True)
            else:
                add_inline(par, txt, size=size)
            # three-line rules: top of header, under header, bottom of last row
            set_cell_borders(cell,
                             top=(ri == 0),
                             bottom=(ri == 0 or ri == len(rows) - 1))
            # vertical centring
            vAlign = OxmlElement("w:vAlign")
            vAlign.set(qn("w:val"), "center")
            cell._tc.get_or_add_tcPr().append(vAlign)
    # repeat header row across pages
    trPr = tbl.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader")
    th.set(qn("w:val"), "true")
    trPr.append(th)
    return tbl


# ------------------------------------------------------------------- parse
def parse_markdown(text: str):
    """Yield ('h1'|'h2'|'h3'|'p'|'bullet'|'table'|'image'|'display'|'code',
              payload)."""
    lines = text.split("\n")
    # drop the submission front-matter lines, keep the title
    drop_prefixes = ("**Target journal:**", "**Type:**")
    lines = [ln for k, ln in enumerate(lines)
             if not any(ln.startswith(p) for p in drop_prefixes)
             or k == 0]
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.strip() in ("---", "***"):  # markdown rule, not content
            i += 1
            continue
        if ln.startswith("```"):
            j = i + 1
            buf = []
            while j < len(lines) and not lines[j].startswith("```"):
                buf.append(lines[j])
                j += 1
            yield ("code", buf)
            i = j + 1
            continue
        if ln.startswith("$$"):
            buf = [ln[2:]]
            if buf[0].rstrip().endswith("$$"):
                yield ("display", buf[0].rstrip()[:-2])
                i += 1
                continue
            j = i + 1
            while j < len(lines) and not lines[j].rstrip().endswith("$$"):
                buf.append(lines[j])
                j += 1
            buf.append(lines[j].rstrip()[:-2])
            yield ("display", " ".join(b for b in buf if b.strip()))
            i = j + 1
            continue
        if ln.startswith("!["):
            # the caption may span several lines; scan to the closing ](...)
            joined = ln
            j = i + 1
            while j < len(lines) and not re.search(r"\]\([^)]*\)\s*$", joined):
                joined += "\n" + lines[j]
                j += 1
            m = re.match(r"!\[(.*)\]\(([^)]*)\)", joined, re.S)
            if m:
                yield ("image", (m.group(1), m.group(2)))
                i = j + 1 if j < len(lines) else j
                continue
            # not a well-formed image: fall through as a paragraph
        if ln.startswith("|"):
            j = i
            rows = []
            while j < len(lines) and lines[j].startswith("|"):
                rows.append(lines[j])
                j += 1
            yield ("table", rows)
            i = j
            continue
        if ln.startswith("### "):
            yield ("h3", ln[4:].strip())
            i += 1
            continue
        if ln.startswith("## "):
            yield ("h2", ln[3:].strip())
            i += 1
            continue
        if ln.startswith("# "):
            yield ("h1", ln[2:].strip())
            i += 1
            continue
        if ln.startswith("- "):
            yield ("bullet", ln[2:].strip())
            i += 1
            continue
        if not ln.strip():
            i += 1
            continue
        # paragraph: gather until blank line or block starter
        j = i
        buf = []
        while j < len(lines) and lines[j].strip() and not lines[j].startswith(
                ("|", "```", "$$", "![", "### ", "## ", "# ", "- ")):
            buf.append(lines[j])
            j += 1
        yield ("p", " ".join(buf))
        i = j if j > i else i + 1  # never stall on an unmatched block starter


# ------------------------------------------------------------------- build
def main() -> int:
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.top_margin = sec.bottom_margin = Cm(2.54)
    sec.left_margin = sec.right_margin = Cm(3.17)

    style = doc.styles["Normal"]
    style.font.name = FONT
    style.font.size = SIZE_BODY
    style.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    pf = style.paragraph_format
    pf.line_spacing = LINE_SPACING
    pf.space_after = Pt(6)

    md = MD.read_text(encoding="utf-8")
    in_refs = False
    n_tables = n_images = 0

    for kind, payload in parse_markdown(md):
        if kind == "h2":
            if payload.strip().lower() == "references":
                in_refs = True
            p = doc.add_paragraph()
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(6)
            add_inline(p, payload, size=Pt(12), base_bold=True)
        elif kind == "h3":
            p = doc.add_paragraph()
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(4)
            add_inline(p, payload, size=Pt(11), base_bold=True)
        elif kind == "h1":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_inline(p, payload, size=Pt(14), base_bold=True)
        elif kind == "p":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            if in_refs:
                p.paragraph_format.left_indent = Cm(0.75)
                p.paragraph_format.first_line_indent = Cm(-0.75)
                p.paragraph_format.line_spacing = 1.15
                p.paragraph_format.space_after = Pt(3)
                add_inline(p, payload, size=Pt(9.5))
            else:
                add_inline(p, payload)
        elif kind == "bullet":
            p = doc.add_paragraph(style="List Bullet")
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            add_inline(p, payload)
        elif kind == "display":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(6)
            add_math_runs(p, payload)
        elif kind == "code":
            p = doc.add_paragraph()
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run("\n".join(payload))
            r.font.name = "Consolas"
            r.font.size = Pt(8.5)
        elif kind == "table":
            rows = []
            for ri, raw in enumerate(payload):
                cells = [c.strip() for c in raw.strip().strip("|").split("|")]
                if ri == 1 and all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    continue
                rows.append(cells)
            add_table(doc, rows)
            n_tables += 1
            # spacing after table
            sp = doc.add_paragraph()
            sp.paragraph_format.space_after = Pt(0)
            sp.paragraph_format.line_spacing = 1.0
            sp.add_run("")
        elif kind == "image":
            cap, rel = payload
            path = FIGDIR / Path(rel).name
            if not path.exists():
                raise FileNotFoundError(path)
            # width: fig1 slightly smaller so it never forces a near-empty page
            width = Cm(15.0) if "fig1" in path.name else Cm(16.0)
            pi = doc.add_paragraph()
            pi.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pi.paragraph_format.keep_with_next = True  # image sticks to caption
            pi.paragraph_format.space_before = Pt(8)
            pi.paragraph_format.space_after = Pt(2)
            pi.add_run().add_picture(str(path), width=width)
            cp = doc.add_paragraph()
            # LEFT, not JUSTIFY: captions contain many inline-math runs, and
            # justification stretches the inter-word gaps unacceptably
            cp.alignment = WD_ALIGN_PARAGRAPH.LEFT
            cp.paragraph_format.line_spacing = 1.15
            cp.paragraph_format.space_after = Pt(10)
            add_inline(cp, cap, size=SIZE_CAPTION)
            n_images += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUT))
    print("wrote", OUT)
    print("tables:", n_tables, " images:", n_images)

    # quick structural report
    d = Document(str(OUT))
    txt = "\n".join(p.text for p in d.paragraphs)
    print("paragraphs:", len(d.paragraphs), "tables:", len(d.tables),
          "images:", len(d.inline_shapes))
    print("dollar count:", txt.count("$"))
    for k in ("REPOSITORY_URL", "ZENODO_DOI", "Appendix D", "References"):
        print(" %-16s %s" % (k, k in txt))
    return 0


if __name__ == "__main__":
    sys.exit(main())
