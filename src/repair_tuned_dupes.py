"""Repair duplicate entries in tuned_*.json `settings` lists.

Background
----------
`run_phase3.sh` was re-invoked after all four Stage A blocks were already
complete. tune_hp.py's resume is not safe for that:

  L76  `best = None` is reset per method on every invocation
  L80  skips the config whose label equals the STORED best
  => `best` is recomputed over the grid MINUS the previous winner, and L121
     then overwrites tuned[key] with that restricted argmax.
  L115 additionally APPENDS to settings[], so every re-run duplicates entries.

The re-run was caught and killed ~4 minutes in, before any method finished, so
`best_hp` / `label` were never overwritten (verified: no method's stored label
disagrees with the hyper-parameters encoded in the Stage B output filenames).
What WAS contaminated is `settings[]`, which now holds duplicate records.

This script de-duplicates settings[] by label, keeping the FIRST occurrence, and
verifies afterwards that nothing else drifted. It also reports whether the
duplicates were bit-identical -- a small side check on same-seed determinism.

Safe to run repeatedly (idempotent). Backs up each file before rewriting.
"""
import json
import os
import shutil
import glob
import sys

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "rank_inv")
BACKUP = os.path.join(OUT, "_backup_tuned_prededupe")

METHODS = ["fedavgm", "fedproxw", "fedadam", "feddyn", "scaffold", "fedavg", "uniform"]


def main():
    os.makedirs(BACKUP, exist_ok=True)
    paths = sorted(glob.glob(os.path.join(OUT, "tuned_*.json")))
    touched = 0

    for p in paths:
        name = os.path.basename(p)
        data = json.load(open(p, encoding="utf-8"))
        changed = False
        report = []

        for key, val in data.items():
            settings = val.get("settings", [])
            seen = {}
            dup_identical = 0
            dup_differ = 0
            kept = []
            for s in settings:
                lab = s.get("label")
                if lab in seen:
                    if s == seen[lab]:
                        dup_identical += 1
                    else:
                        dup_differ += 1
                    continue
                seen[lab] = s
                kept.append(s)
            if len(kept) != len(settings):
                report.append((key.split("|")[2], len(settings), len(kept),
                               dup_identical, dup_differ))
                val["settings"] = kept
                changed = True

        if changed:
            shutil.copy2(p, os.path.join(BACKUP, name))
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=1)
            touched += 1
            print("== %s" % name)
            for m, before, after, same, diff in report:
                print("   %-9s settings %d -> %d  (removed: %d identical, %d differing)"
                      % (m, before, after, same, diff))

    print("\nfiles rewritten: %d ; backups in %s" % (touched, BACKUP))

    # consistency: stored best label vs what Stage B actually used (encoded in filenames)
    print("\n=== cross-check: tuned best label vs Stage B filenames ===")
    bad = 0
    for ds, al in [("mnist", "0.05"), ("mnist", "0.3"),
                   ("fashion", "0.05"), ("fashion", "0.3")]:
        tp = os.path.join(OUT, "tuned_%s_a%s.json" % (ds, al))
        if not os.path.exists(tp):
            continue
        tuned = json.load(open(tp, encoding="utf-8"))
        used = {}
        for f in glob.glob(os.path.join(OUT, "%s_a%s_*_s0.json" % (ds, al))):
            b = os.path.basename(f)[: -len("_s0.json")].replace("%s_a%s_" % (ds, al), "")
            for m in METHODS:
                if b == m + "_def":
                    used[m] = "def"
                    break
                if b.startswith(m + "_"):
                    used[m] = b[len(m) + 1:]
                    break
        for key, val in tuned.items():
            m = key.split("|")[2]
            if m in used and used[m] != val.get("label"):
                print("   MISMATCH %s %s: StageB=%s tuned=%s"
                      % (ds, al, used[m], val.get("label")))
                bad += 1
    print("mismatches: %d" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
