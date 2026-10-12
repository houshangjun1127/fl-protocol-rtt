#!/usr/bin/env bash
# ============================================================================
# Seeds 4,5 extension -- Stage B grid (execution_plan_20261011.md, task A-1)
#
# WHY THIS SCRIPT EXISTS
#   The 196 Stage B runs on disk cover seeds 0-3. execution_plan v2 section 1
#   judged 6 seeds necessary (sign test: n=4 cannot reach p<0.05 even at 4/4
#   agreement, p=0.125; n=6 at 6/6 gives p=0.031). This script adds seeds 4
#   and 5 only: 7 cells x 7 methods x 2 seeds = 98 runs.
#
# WHAT IS DELIBERATELY NOT CHANGED
#   - lr=0.05, lr_decay=0.9, rounds=60: identical to every run already on disk.
#     Verified by reading the cfg of all 196 existing files (all cells report
#     lr=0.05, rounds=60, batch_size=64, n_clients=10, local_epochs=1).
#   - FL_THREADS is NOT set, so rank_inv_runner.py keeps its default of 2,
#     identical to the 196 existing runs. Raising it changes the floating-point
#     reduction order and makes new seeds non-comparable with old ones.
#   - Tuned coefficients are NOT passed on the command line: rank_inv_runner.py
#     injects them from results/rank_inv/tuned_<ds>_a<alpha>.json, which is how
#     the existing tags (e.g. mnist_a0.1_fedadam_lr_s=0.01,tau=0.001_s0) were
#     produced. Passing them by hand risks a different tag and a duplicate run.
#
# CANARY (checked by the driving agent, not by this script)
#   Expected single-run wall time: MNIST/Fashion 113-151 s, CIFAR 161-186 s.
#   If the first run lands clearly below 90 s, the thread count changed ->
#   stop immediately, the run would not be comparable.
# ============================================================================

set -u
PY="${PYTHON:-python}"
cd "$(dirname "$0")" || exit 1
OUT=../results/rank_inv
LOG=../results/_seeds45_queue.log
LEDGER=../results/PHASE5_LEDGER.md

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG" >> "$LEDGER"; }

task_end() {
    RC=$1; TASK="$2"
    if [ "$RC" -eq 0 ]; then
        log "   $TASK finish OK"
    else
        log "   $TASK FAILED (exit $RC) -- queue stopped here"
        exit "$RC"
    fi
}

{
echo ""
echo "=================================================================="
echo "A-1 seeds 4,5 extension started $(date '+%Y-%m-%d %H:%M:%S')"
echo "=================================================================="
} >> "$LEDGER"

log "=== A-1 BEGIN $(date '+%Y-%m-%d %H:%M:%S') ==="
log "grid: mnist/fashion alpha in {0.05,0.1,0.3} + cifar10 alpha 0.1; seeds 4,5; 7 methods"

# --- interlock: no competing training job
BUSY=$(tasklist 2>/dev/null | grep -ci "python.exe" || true)
if [ "${BUSY:-0}" -gt 0 ]; then
    log "   ABORT: ${BUSY} python process(es) already alive. Serial queue only."
    exit 90
fi
log "   interlock: no competing python job."

# --- interlock: every tuned file must be present, or tags will silently differ
for TF in tuned_mnist_a0.05 tuned_mnist_a0.1 tuned_mnist_a0.3 \
          tuned_fashion_a0.05 tuned_fashion_a0.1 tuned_fashion_a0.3 \
          tuned_cifar10_a0.1; do
    if [ ! -f "$OUT/$TF.json" ]; then
        log "   ABORT: $TF.json missing -- tuned hyper-params would not be injected."
        exit 91
    fi
done
log "   interlock: all 7 tuned_*.json present."

# ============================================================================
# MNIST -- 3 alphas x 7 methods x 2 seeds = 42 runs
# ============================================================================
log "## A1.mnist -- MNIST seeds 4,5 (42 runs)"
"$PY" rank_inv_runner.py --datasets mnist --alphas 0.05,0.1,0.3 \
    --seeds 4,5 --rounds 60 --lr 0.05 --lr-decay 0.9 \
    --out-dir "$OUT" --stage B
task_end $? "A1.mnist"

# ============================================================================
# FashionMNIST -- 3 alphas x 7 methods x 2 seeds = 42 runs
# ============================================================================
log "## A1.fashion -- FashionMNIST seeds 4,5 (42 runs)"
"$PY" rank_inv_runner.py --datasets fashion --alphas 0.05,0.1,0.3 \
    --seeds 4,5 --rounds 60 --lr 0.05 --lr-decay 0.9 \
    --out-dir "$OUT" --stage B
task_end $? "A1.fashion"

# ============================================================================
# CIFAR-10 -- 1 alpha x 7 methods x 2 seeds = 14 runs
# ============================================================================
log "## A1.cifar -- CIFAR-10 seeds 4,5 (14 runs)"
"$PY" rank_inv_runner.py --datasets cifar10 --alphas 0.1 \
    --seeds 4,5 --rounds 60 --lr 0.05 --lr-decay 0.9 \
    --out-dir "$OUT" --stage B
task_end $? "A1.cifar"

log "=== A-1 QUEUE END $(date '+%Y-%m-%d %H:%M:%S') ==="
