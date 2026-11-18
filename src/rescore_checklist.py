#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Re-score the 58-study main pool against the reorganised five-item checklist
(target and task / training and tuning / attainment event / budget and
non-attainment / replication and aggregation).

The old chk1..chk5 columns of results/survey_extraction.csv encode the earlier
five items (target+justification / attainable maximum / schedule / statistic /
stability). The reorganised checklist groups the disclosure differently:

  N1 Target and task        metric, evaluation split, target value, reason
  N2 Training and tuning    schedule disclosed + tuning policy stated
  N3 Attainment event       statistic defined / derivable, window, timestamp
  N4 Budget and non-attainment  round cap + censoring/tie convention
  N5 Replication and aggregation  seeds, per-seed results, dispersion

Scores are derived DETERMINISTICALLY from the raw adjudicated fields of the
released extraction table (no re-adjudication): each item scores
1 (explicitly stated) / 0.5 (partially stated or recoverable by unambiguous
implication) / 0 (absent), using exactly the rules below. The attainable
maximum (old item 2) is demoted to auxiliary context.

Rules (column names are those of results/survey_extraction.csv):
  N1: 1.0 if metric_name, metric_split, target_value all specified AND
         target_justified != "no";
      0.5 if target_value and metric_name specified (split unspecified or
         no stated reason);
      0 otherwise.  (All 58 rows carry a target value by inclusion I2-I3.)
  N2: 1.0 if lr_schedule_disclosed == "yes" AND lr_schedule_tuned_per_method
         in {"yes", "no"} (a tuning policy is stated);
      0.5 if lr_schedule_disclosed in {"yes", "partial"};
      0 if "no".
  N3: 1.0 if rtt_statistic_type != "unspecified";
      0.5 elif rtt_derived == "yes" (statistic recoverable from stated
         quantities);
      0 otherwise.
  N4: budget = total_rounds_budget not in {"", "unspecified"};
      cens = censoring_reported == "yes";
      1.0 if budget and cens; 0.5 if exactly one; 0 if neither.
  N5: seeds = n_seeds not in {"", "unspecified"};
      perseed = per_seed_results_reported == "yes";
      disp = seed_dispersion_reported == "yes" or stability_measure_reported
             == "yes";
      1.0 if seeds and (perseed or disp);
      0.5 if seeds or perseed or disp;
      0 otherwise.

Writes checklist_rescore.json next to the extraction table and prints the
summary that Section 3.4 quotes. Run: python src/rescore_checklist.py
"""
import csv
import json
import os
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
for _d in (HERE, os.path.dirname(HERE), os.path.dirname(
        os.path.dirname(HERE)), os.path.dirname(os.path.dirname(
            os.path.dirname(HERE)))):
    for _sub in ("results", "survey"):
        _c = os.path.join(_d, _sub, "survey_extraction.csv")
        if os.path.exists(_c):
            CSV = _c
            break
    if os.path.exists(_c):
        break
else:
    raise SystemExit(
        "survey_extraction.csv not found near the script")
OUT = os.path.join(os.path.dirname(CSV), "checklist_rescore.json")

SPEC = {"", "unspecified"}


def specified(v):
    return v.strip().lower() not in SPEC


def yes(v):
    return v.strip().lower() in ("yes", "y", "true", "1", "reported")


def score_row(r):
    # N1 target and task
    if (specified(r["metric_name"]) and specified(r["metric_split"])
            and specified(r["target_value"])
            and r["target_justified"].strip().lower() != "no"):
        n1 = 1.0
    elif specified(r["target_value"]) and specified(r["metric_name"]):
        n1 = 0.5
    else:
        n1 = 0.0
    # N2 training and tuning
    sched = r["lr_schedule_disclosed"].strip().lower()
    tuned = r["lr_schedule_tuned_per_method"].strip().lower()
    if sched == "yes" and tuned in ("yes", "no"):
        n2 = 1.0
    elif sched in ("yes", "partial"):
        n2 = 0.5
    else:
        n2 = 0.0
    # N3 attainment event
    if specified(r["rtt_statistic_type"]):
        n3 = 1.0
    elif yes(r["rtt_derived"]):
        n3 = 0.5
    else:
        n3 = 0.0
    # N4 budget and non-attainment
    budget = specified(r["total_rounds_budget"])
    cens = yes(r["censoring_reported"])
    n4 = 1.0 if (budget and cens) else (0.5 if (budget or cens) else 0.0)
    # N5 replication and aggregation
    seeds = specified(r["n_seeds"])
    perseed = yes(r["per_seed_results_reported"])
    disp = yes(r["seed_dispersion_reported"]) or yes(
        r["stability_measure_reported"])
    if seeds and (perseed or disp):
        n5 = 1.0
    elif seeds or perseed or disp:
        n5 = 0.5
    else:
        n5 = 0.0
    return [n1, n2, n3, n4, n5]


def main():
    with open(CSV, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["pool"].strip() == "main"]
    assert len(rows) == 58, "main pool is %d, expected 58" % len(rows)

    scores = {r["study_id"]: score_row(r) for r in rows}
    totals = [sum(v) for v in scores.values()]
    per_item = list(zip(*scores.values()))

    # old five items for comparison (reported=1, partial=0.5, absent=0)
    old_cols = ["chk1_target_value_and_justification", "chk2_reachable_ceiling",
                "chk3_global_training_schedule", "chk4_statistic_definition",
                "chk5_stability_and_dispersion"]
    old_map = {"reported": 1.0, "partial": 0.5, "absent": 0.0}
    old_totals = [sum(old_map[r[c].strip().lower()] for c in old_cols)
                  for r in rows]

    summary = {
        "n_studies": len(rows),
        "new_items": {
            "mean_disclosed": round(statistics.mean(totals), 4),
            "sd_disclosed": round(statistics.stdev(totals), 4),
            "mean_missing": round(5 - statistics.mean(totals), 4),
            "distribution": {str(t): totals.count(t)
                             for t in sorted(set(totals))},
            "per_item": {
                "N%d" % (i + 1): {
                    "full": sum(1 for v in per_item[i] if v == 1.0),
                    "partial": sum(1 for v in per_item[i] if v == 0.5),
                    "absent": sum(1 for v in per_item[i] if v == 0.0),
                    "mean": round(statistics.mean(per_item[i]), 4),
                } for i in range(5)
            },
        },
        "old_items": {
            "mean_disclosed": round(statistics.mean(old_totals), 4),
            "sd_disclosed": round(statistics.stdev(old_totals), 4),
        },
        "per_study": {k: v + [sum(v)] for k, v in scores.items()},
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1)

    ni = summary["new_items"]
    print("N = %d main-pool studies" % len(rows))
    print("NEW five items: mean disclosed %.2f of 5 (sd %.2f); mean missing %.2f"
          % (ni["mean_disclosed"], ni["sd_disclosed"], ni["mean_missing"]))
    for i in range(5):
        p = ni["per_item"]["N%d" % (i + 1)]
        print("  N%d: full %2d/58, partial %2d/58, absent %2d/58 (mean %.2f)"
              % (i + 1, p["full"], p["partial"], p["absent"], p["mean"]))
    print("  score distribution:", ni["distribution"])
    print("OLD five items: mean %.4f (sd %.4f)"
          % (summary["old_items"]["mean_disclosed"],
             summary["old_items"]["sd_disclosed"]))
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
