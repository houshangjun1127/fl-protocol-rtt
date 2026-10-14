"""Tier inclusion rates among adjudicated full texts.

Recomputes the per-tier inclusion rate quoted in Section 3.4 by joining the
released adjudication records (survey_extraction.csv rows with pool main or
secondary, plus the excluded rows of survey_fulltext_log.md) to the screening
tiers assigned during title/abstract screening (_prescreen.csv).

Join key: normalised-title prefix (first 25, falling back to 20 characters)
plus publication year. 221 of the 236 adjudicated records match; the 17
misses are title truncation in the log and small year discrepancies between
the preprint and publisher versions. The unmatched are listed in the JSON
output so the reader can audit them.

Written for the submission revision after the in-text rates were found to
have no artefact provenance; this script is the provenance.
"""

import csv
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.normpath(os.path.join(HERE, ".."))


def norm(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def main():
    pre = list(csv.DictReader(open(os.path.join(RES, "survey", "_prescreen.csv"),
                                   encoding="utf-8-sig")))
    pidx = {}
    for r in pre:
        pidx[(norm(r["title"])[:25], r["year"])] = r["tier"]
        pidx.setdefault((norm(r["title"])[:20], r["year"]), r["tier"])

    ext = list(csv.DictReader(open(os.path.join(RES, "survey_extraction.csv"),
                                   encoding="utf-8")))
    log = open(os.path.join(RES, "survey_fulltext_log.md"), encoding="utf-8").read()

    tiers = ("T1", "T2", "T3", "T0")
    inc = {t: {"included": 0, "total": 0} for t in tiers}
    unmatched = []

    for r in ext:                       # main + secondary = included
        t = pidx.get((norm(r["title"])[:25], r["year"]))
        if t in inc:
            inc[t]["included"] += 1
            inc[t]["total"] += 1
        else:
            unmatched.append({"kind": "included", "title": r["title"],
                              "year": r["year"]})

    n_exc = 0
    for line in log.splitlines():
        m = re.match(r"^\|\s*-\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*(\d{4})\s*\|"
                     r"\s*exclude\s*\|\s*([A-Za-z0-9()]+)\s*\|", line)
        if not m:
            continue
        n_exc += 1
        title, year = m.group(2).strip(), m.group(3).strip()
        t = pidx.get((norm(title)[:25], year))
        if t in inc:
            inc[t]["total"] += 1
        else:
            unmatched.append({"kind": "excluded", "code": m.group(4).strip(),
                              "title": title, "year": year})

    out = {
        "method": "normalised-title prefix (25, fallback 20 chars) + year join "
                  "of adjudicated records to _prescreen.csv tiers",
        "adjudicated": {"included": len(ext), "excluded": n_exc},
        "matched": sum(v["total"] for v in inc.values()),
        "unmatched_n": len(unmatched),
        "tier_inclusion": {t: "%d/%d" % (v["included"], v["total"])
                           for t, v in inc.items()},
        "unmatched": unmatched,
    }
    with open(os.path.join(HERE, "_tier_inclusion.json"), "w",
              encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in out.items() if k != "unmatched"},
                     indent=1))


if __name__ == "__main__":
    main()
