#!/usr/bin/env bash
# Phase 3 RESUME (Stage B only).
#
# WHY Stage A IS NOT RUN HERE
# ---------------------------
# tune_hp.py's resume is unsafe to re-invoke once Stage A is complete:
#   - L76  `best = None` is reset per method, per invocation
#   - L80  skips exactly the config whose label == the STORED best
#   => `best` is recomputed over the grid MINUS the previous winner, and L121
#      then OVERWRITES tuned[key] with that restricted argmax. A rerun can
#      therefore silently replace the selected hyper-parameters.
#   - L115 additionally APPENDS to settings[], duplicating entries.
#
# Stage A is already complete for all four (dataset, alpha) blocks, so the safe
# resume is Stage B only, leaving every tuned_*.json untouched.
#
# DECAY
# -----
# rank_inv_runner.py reads cfg.get("lr_decay", 0.9) -- i.e. 0.9 is a DEFAULT,
# not an explicit pin. Passed explicitly here so the value does not depend on a
# default that someone may later change.
#
# Resumable: rank_inv_runner.py skips any run whose per-run json already exists,
# so completed configs cost nothing.

set -u
PY=../.venv/Scripts/python.exe
OUT=../results/rank_inv
DECAY=0.9

echo "=== Phase 3 RESUME START $(date) ==="
echo "    decay=$DECAY (explicit)"
echo "    Stage A SKIPPED (already complete; see header comment for why)"

for DS in mnist fashion; do
  for AL in 0.05 0.3; do
    n=$(ls "$OUT" 2>/dev/null | grep -c "^${DS}_a${AL}_" || true)
    echo "--- Stage B: $DS alpha=$AL (existing files: $n/28) $(date)"
    $PY rank_inv_runner.py --datasets "$DS" --alphas "$AL" \
        --seeds 0,1,2,3 --rounds 60 --lr 0.05 --lr-decay "$DECAY" \
        --out-dir "$OUT" --stage B \
        || { echo "!!! Stage B failed for $DS a=$AL -- stopping"; exit 1; }
    echo "--- done $DS a=$AL $(date)"
  done
done

echo "--- analysis: absolute target grid"
$PY analyze_rank_inv.py --dir "$OUT" --out "$OUT/rank_inv_report_alpha_sweep.json" \
    || echo "  (analyser returned non-zero; check output above)"

echo "--- analysis: relative target grid (ceiling-fraction)"
$PY analyze_rank_inv.py --dir "$OUT" --out "$OUT/rank_inv_report_alpha_sweep_rel.json" \
    --target-mode relative --rho-lo 0.50 --rho-hi 0.98 --n-rel-targets 25 \
    || echo "  (analyser returned non-zero; check output above)"

echo "=== Phase 3 RESUME DONE $(date) ==="
