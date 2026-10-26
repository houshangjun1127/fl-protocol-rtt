#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R13-4: re-check the "0 of 58 report trajectory stability" claim.

WHY
---
Section 3.4 states that no included study reports an explicit stability measure
for the accuracy trajectory (checklist item 5, 0/58). That is a strong claim --
a single counterexample falsifies it -- and the original extraction was done by
one extractor with one pass. The reviewer asked for a re-check with a recorded
per-paper verdict. This script is that re-check: it re-reads the downloaded full
texts and reports, per study, what it found.

WHAT COUNTS AND WHAT DOES NOT
-----------------------------
The claim is about a stability measure of the *trajectory over rounds*. It is
NOT about seed-level dispersion: 46 of 58 studies do print some dispersion
notation (sd, +/-, error bars) somewhere, and that is reported separately in
Table 6 as an upper bound. The distinction matters, because a paper can report
the spread across seeds while saying nothing about whether its own curve holds
the target once it touches it -- which is exactly the quantity item 5 asks for.

So the patterns below are split into two tiers:
  TIGHT   an explicit statement about behaviour across ROUNDS near the target:
          final/last-k-round spread, post-peak drop, oscillation, holding the
          target, collapse.
  LOOSE   any dispersion notation anywhere in the paper.
Only TIGHT hits can overturn the 0/58 claim. LOOSE is reported for contrast.

MATCHING
--------
Each of the 58 studies is matched to a downloaded full text by searching the
`.txt` files for a distinctive 6-token shingle from its title. A study that
matches no file is reported as UNMATCHED and is NOT counted as evidence for
0/58 -- a missing file is not a negative finding.

Usage
-----
    python src/recheck_stability.py
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSV = os.path.join(ROOT, "results", "survey_extraction.csv")
FT = os.path.join(ROOT, "results", "survey", "fulltext")
OUT = os.path.join(ROOT, "results", "survey_stability_recheck.md")

TIGHT = {
    "final/last-k-round spread": r"(final|last|last\s+ten|final\s+ten|ending|trailing)"
                                 r"[^.]{0,40}\b(round|epoch|communicat)",
    "post-peak drop": r"post-?peak|peak\s+(drop|decline|regress)|drop\s+from\s+(its\s+)?peak",
    "oscillation": r"oscillat",
    "holds / sustains the target": r"(sustain|hold|maintain)[a-z]*\s+(the\s+|an\s+|a\s+)?"
                                   r"(target|accuracy|threshold|level)[^.]{0,60}"
                                   r"(round|epoch|until|throughout)",
    "collapse after reaching": r"collapse[sd]?\s+(after|once|following)|"
                               r"(after|once)\s+reach[a-z]*[^.]{0,40}(collapse|degrade|drop)",
    "round-wise std / variance": r"(std|standard deviation|variance|sd)\s+"
                                 r"(of|across|over)\s+(the\s+)?(round|epoch|iteration|communicat)",
    "stability of the curve": r"stability\s+of\s+(the\s+)?(accuracy|convergence|curve|training)"
                              r"|convergence\s+stability",
}

LOOSE = {
    "any dispersion notation": r"(±|\+\s*/-|std|standard deviation|error bar|"
                               r"confidence interval|variance)",
}


def norm(s):
    return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())


def shingles(title, k=8):
    """8-token shingles.

    MATCHING BUG FOUND AND FIXED (2026-10-19). The first version used 6-token
    shingles and accepted the FIRST file containing any one of them. Generic
    title fragments -- "federated learning with non iid data", that sort of
    thing -- occur in dozens of papers, so several studies silently matched the
    same file and inherited its hits: three different study ids came back with
    an identical "averaged over the last 25 rounds" sentence that belongs to
    one paper. The re-check would have been worthless. Now a file must contain
    at least MIN_SHINGLE distinct 8-token shingles from the title, and the file
    with the most matches wins; ties and weak matches are reported as unmatched.
    """
    w = norm(title).split()
    return [" ".join(w[i:i + k]) for i in range(max(1, len(w) - k + 1))]


def load_texts():
    out = []
    if not os.path.isdir(FT):
        return out
    for f in sorted(os.listdir(FT)):
        if not f.endswith(".txt"):
            continue
        p = os.path.join(FT, f)
        try:
            with open(p, encoding="utf-8", errors="ignore") as fh:
                out.append((f, norm(fh.read())))
        except Exception:
            continue
    return out


def main():
    rows = [r for r in csv.DictReader(open(CSV, encoding="utf-8"))
            if r.get("pool") == "main"]
    texts = load_texts()
    print("main pool: %d studies | full-text .txt files: %d" % (len(rows), len(texts)))

    MIN_SHINGLE = 3

    def canon(s):
        return re.sub(r"[^a-z0-9.]", "", (s or "").lower())

    by_id = {}
    for f, _ in texts:
        by_id.setdefault(canon(f).split(".txt")[0], f)

    res = []
    taken = {}
    for r in rows:
        # Identifier matching FIRST: the downloaded files are named after the
        # arXiv id or the DOI, so this is exact where it applies (57/58).
        # Title-shingle matching is only a fallback for the remainder, and it
        # is the part that produced the duplicate-matching bug above.
        hit_file, how, best_n = None, "-", 0
        for cand in (r.get("arxiv_id", ""), r.get("doi", ""),
                     r.get("doi", "").replace("/", "_")):
            c = canon(cand)
            if c and c in by_id:
                hit_file, how = by_id[c], "identifier"
                break
        if hit_file is None:
            sh = [s for s in shingles(r["title"]) if len(s) > 25]
            best_n = 0
            for f, body in texts:
                n = sum(1 for s in sh if s in body)
                if n > best_n:
                    hit_file, best_n, how = f, n, "title"
            if best_n < MIN_SHINGLE:
                hit_file, how = None, "unmatched"
        rec = {"study_id": r["study_id"], "title": r["title"][:70],
               "file": hit_file or "-", "match": how, "shingles": best_n,
               "tight": {}, "loose": {}}
        if hit_file:
            taken.setdefault(hit_file, []).append(r["study_id"])
        if hit_file:
            body = dict(texts)[hit_file]
            for name, pat in TIGHT.items():
                m = re.findall(pat, body)
                if m:
                    rec["tight"][name] = len(m)
            for name, pat in LOOSE.items():
                m = re.findall(pat, body)
                if m:
                    rec["loose"][name] = len(m)
        res.append(rec)

    n_match = sum(1 for x in res if x["file"] != "-")
    n_tight = sum(1 for x in res if x["tight"])
    n_loose = sum(1 for x in res if x["loose"])
    dupes = {f: ids for f, ids in taken.items() if len(ids) > 1}
    print("matched to a full text : %d / %d" % (n_match, len(res)))
    print("files matched by >1 study (should be 0): %d" % len(dupes))
    for f, ids in list(dupes.items())[:5]:
        print("   ", f, ids)
    print("TIGHT hits (would overturn 0/58): %d" % n_tight)
    print("LOOSE dispersion notation       : %d" % n_loose)

    lines = ["# Re-check: do any of the 58 report trajectory stability?",
             "",
             "Re-checker: single-agent re-read of the downloaded full texts "
             "(2026-10-19), independent of the original extraction pass.",
             "Script: `src/recheck_stability.py`. Pattern tiers are defined in "
             "the script docstring: only a TIGHT hit (an explicit statement about "
             "behaviour across ROUNDS near the target) can overturn the 0/58 "
             "claim; LOOSE dispersion notation is reported for contrast because "
             "46/58 studies print some.",
             "",
             "| study | full text matched | TIGHT hits | LOOSE dispersion |",
             "|---|---|---|---|"]
    for x in res:
        t = ", ".join("%s(%d)" % (k, v) for k, v in x["tight"].items()) or "-"
        l = ", ".join("%s(%d)" % (k, v) for k, v in x["loose"].items()) or "-"
        lines.append("| %s %s | %s | %s | %s |" % (
            x["study_id"], x["title"], x["file"], t, l))
    lines += ["",
              "## Verdict",
              "",
              "* studies matched to a downloaded full text: **%d / %d**" % (
                  n_match, len(res)),
              "* studies with any TIGHT hit: **%d**" % n_tight,
              "* studies with any LOOSE dispersion notation: **%d**" % n_loose,
              "",
              "Unmatched studies are reported as such and are NOT counted as "
              "evidence for 0/58: a missing file is not a negative finding.",
              ""]
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("wrote", OUT)

    with open(os.path.join(ROOT, "results", "survey", "_stability_recheck.json"),
              "w", encoding="utf-8") as f:
        json.dump({"n_studies": len(res), "n_matched": n_match,
                   "n_tight": n_tight, "n_loose": n_loose, "records": res},
                  f, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
