# Survey of reporting practice: summary statistics (B-4)

Main pool N = 58; secondary pool = 15. All intervals are Wilson 95% score intervals. Denominators are the number of studies in which the field was assessable.


## 1. The five-item disclosure checklist

| item | reported (disclosed) | partial | absent | disclosed rate [95% CI] |
|---|---|---|---|---|
| 1 Target value and its justification | 4 | 54 | 0 | 4/58 (6.9% [2.7, 16.4]) |
| 2 Reachable ceiling | 2 | 45 | 11 | 2/58 (3.4% [1.0, 11.7]) |
| 3 Global training schedule | 0 | 57 | 1 | 0/58 (0.0% [0.0, 6.2]) |
| 4 Statistic definition | 3 | 0 | 55 | 3/58 (5.2% [1.8, 14.1]) |
| 5 Stability and dispersion | 0 | 47 | 11 | 0/58 (0.0% [0.0, 6.2]) |

Mean number of the five items disclosed: **1.91** (sd 0.42); equivalently **3.09** of five items are missing from the average report.

Caveat recorded in the extraction script: item 2 is derived with a permissive keyword rule, so its disclosed rate is an UPPER bound; items 3-5 are derived from documented regexes over the full text and item 1 from the adjudicated target/ justification fields.


## 2. The target value itself

- studies with a numeric target: 58/58
- range: **30.00% to 99.98%** (span 69.98 accuracy points)
- quartiles: Q1 70.0%, median 80.0%, Q3 90.0%
- distinct values: 20
- distribution by decade: 30s%: 1, 40s%: 2, 50s%: 5, 60s%: 5, 70s%: 11, 80s%: 19, 90s%: 15
- target justified: no 54, relative_to_centralized 2, post_hoc 1, post_hoc_baseline_peak 1
- a stated reason for the number: 4/58 (6.9% [2.7, 16.4])


## 3. Other protocol elements a reader needs

| element | disclosed rate [95% CI] |
|---|---|
| number of seeds / independent runs stated | 11/58 (19.0% [10.9, 30.9]) |
| per-seed (not seed-averaged) results reported | 11/58 (19.0% [10.9, 30.9]) |
| some dispersion notation (sd / +- / error bars) appears somewhere in the paper (permissive rule, upper bound) | 46/58 (79.3% [67.2, 87.7]) |
| total round budget (the censoring horizon) stated | 45/58 (77.6% [65.3, 86.4]) |
| a convention for methods that never reach t | 14/58 (24.1% [15.0, 36.5]) |
| heterogeneity type stated | 57/58 (98.3% [90.9, 99.7]) |
| heterogeneity parameter (e.g. alpha) stated | 15/58 (25.9% [16.3, 38.4]) |
| number of clients stated | 45/58 (77.6% [65.3, 86.4]) |
| which split the threshold is evaluated on | 19/58 (32.8% [22.1, 45.6]) |
| learning-rate schedule at least mentioned (permissive rule, upper bound) | 34/58 (58.6% [45.8, 70.4]) |
| RTT statistic type named | 3/58 (5.2% [1.8, 14.1]) |


## 4. Composition of the main pool

| field | counts |
|---|---|
| metric_name | accuracy: 52, other: 3, top1_accuracy: 1, auc: 1, f1: 1 |
| rtt_statistic_type | unspecified: 55, first_passage: 3 |
| target_value_scale | percent_0_100: 53, fraction_0_1: 5 |
| year range | 2018-2026, median 2023 |


## 5. Identifier integrity check

Every identifier attached to an included study was re-resolved against the live arXiv API (falling back to Crossref) and the canonical title compared with the extracted title by token Jaccard similarity. A study is `OK` at similarity >= 0.55 and `DIFFER` below it.

| outcome | n |
|---|---|
| OK | 71 |
| NORESOLVE | 2 |

`NORESOLVE` records carry no resolvable identifier: S027, S031. These two entered the pool from a non-indexed source and are retained on the strength of the full text that was actually downloaded and read; their identifiers were recovered from the stored retrieval URL where possible.

No record was found to point at a different paper than the one adjudicated.
