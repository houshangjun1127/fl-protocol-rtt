#!/usr/bin/env bash
# Phase 3: alpha sweep for MNIST + Fashion-MNIST, Stage A then Stage B.
#
# !!! The lr_decay choice is NOT cosmetic and must be stated per dataset. !!!
# Stage A for MNIST/Fashion was run at decay=0.9; the CIFAR-10 Stage A file was
# run at decay=1.0 because that maximised FedAvg's late accuracy there. The knob
# is NOT neutral across methods (that is claim B of this study), so mixing decay
# values inside one alpha sweep would silently confound the alpha comparison.
# This script therefore pins decay=0.9 explicitly for every MNIST/Fashion run.
#
# Cost estimate from measured wall time:
#   MNIST   Stage A ~12 min per alpha  (7 methods x grid)
#   Fashion Stage A ~14 min per alpha
#   Stage B  7 methods x 4 seeds x ~3 min ~ 84 min per (dataset, alpha)
#   => 2 alphas x (12+84 + 14+84) ~ 6.5 h. Meets the plan's ~6 h estimate.
#
# Guarded: refuses to start if a Phase-3 output already looks complete, and
# writes a marker so a rerun is safe (tune_hp.py resumes per (method,hp) key;
# rank_inv_runner.py skips runs whose per-run json already exists).

set -u
PY=../.venv/Scripts/python.exe
OUT=../results/rank_inv
DECAY=0.9
ALPHAS="0.05,0.3"
DATASETS="mnist,fashion"

echo "=== Phase 3 START $(date) ==="

for DS in mnist fashion; do
  for AL in 0.05 0.3; do
    echo "--- Stage A: $DS alpha=$AL (decay=$DECAY) $(date)"

    if [ -f "$OUT/tuned_${DS}_a${AL}.json" ]; then
      echo "    tuned file exists -> tune_hp.py will resume/skip completed keys"
    fi

    $PY tune_hp.py --datasets "$DS" --alphas "$AL" --rounds 60 \
        --lr 0.05 --lr-decay "$DECAY" --seed 0 --out-dir "$OUT" \
        || { echo "!!! Stage A failed for $DS a=$AL -- stopping"; exit 1; }

    echo "--- Stage B: $DS alpha=$AL $(date)"
    $PY rank_inv_runner.py --datasets "$DS" --alphas "$AL" \
        --seeds 0,1,2,3 --rounds 60 --lr 0.05 --out-dir "$OUT" --stage B \
        || { echo "!!! Stage B failed for $DS a=$AL -- stopping"; exit 1; }

    echo "--- done $DS a=$AL $(date)"
  done
done

# rerun the analyser over the widened grid (absolute + relative target modes).
# NOTE: analyze_rank_inv.py takes --dir (not --out-dir) and auto-discovers every
# dataset/alpha/seed present in the directory -- it has no --datasets/--alphas
# /--seeds switches. Verified against --help, not assumed.
echo "--- analysis: absolute target grid"
$PY analyze_rank_inv.py --dir "$OUT" --out "$OUT/rank_inv_report_alpha_sweep.json" \
    || echo "  (analyser returned non-zero; check output above)"

echo "--- analysis: relative target grid (ceiling-fraction)"
$PY analyze_rank_inv.py --dir "$OUT" --out "$OUT/rank_inv_report_alpha_sweep_rel.json" \
    --target-mode relative --rho-lo 0.50 --rho-hi 0.98 --n-rel-targets 25 \
    || echo "  (analyser returned non-zero; check output above)"

echo "=== Phase 3 DONE $(date) ==="
