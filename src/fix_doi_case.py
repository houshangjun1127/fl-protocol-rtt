"""Fetch the canonical (registrant-registered) casing for every DOI in the
reference list of results/paper_draft.md.

Writes results/survey/_doi_canonical.json mapping the lowercase-normalised DOI
to the canonical string returned by Crossref (or DataCite for 10.48550/*).

Usage:  python src/fix_doi_case.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "results" / "paper_draft.md"
OUT = ROOT / "results" / "survey" / "_doi_canonical.json"

UA = {"User-Agent": "fl-fedpc-reference-check/1.0 (mailto:author@example.org)"}


def get_json(url: str, tries: int = 3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:  # pragma: no cover - network dependent
            if i == tries - 1:
                return {"_error": f"{type(exc).__name__}: {exc}"}
            time.sleep(1.5 * (i + 1))
    return None


def canonical(doi: str):
    """Return (canonical_doi, source) or (None, reason)."""
    low = doi.lower()
    if low.startswith("10.48550/"):
        d = get_json(f"https://api.datacite.org/dois/{low}")
        got = (d or {}).get("data", {}).get("attributes", {}).get("doi")
        return (got, "datacite") if got else (None, str(d)[:120])
    d = get_json(f"https://api.crossref.org/works/{urllib.parse.quote(low)}")
    got = (d or {}).get("message", {}).get("DOI")
    return (got, "crossref") if got else (None, str(d)[:120])


def main() -> int:
    import urllib.parse  # noqa: F401  (used inside canonical)

    text = PAPER.read_text(encoding="utf-8")
    ref_block = text.split("## References", 1)[1]
    raw = re.findall(r"DOI\s+(10\.[^,\s)]+)", ref_block)
    dois = sorted({d.rstrip(".,;") for d in raw})
    print(f"found {len(dois)} distinct DOIs", flush=True)

    out = {}
    for i, d in enumerate(dois, 1):
        canon, src = canonical(d)
        out[d.lower()] = {"as_written": d, "canonical": canon, "source": src}
        flag = "" if canon and canon == d else ("  <-- CHANGE" if canon else "  <-- UNRESOLVED")
        print(f"[{i:2d}/{len(dois)}] {d}  ->  {canon}  ({src}){flag}", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
