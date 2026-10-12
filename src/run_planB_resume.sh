#!/usr/bin/env bash
# ============================================================================
# Plan B queue -- RESUME from the T2 breakpoint
#
# Why this script exists:
#   The original run_planB_queue.sh was killed at 00:40 (10 of 28 CIFAR-10
#   Stage B runs written, run 11 in flight) when the driving session ended and
#   took its child processes with it. T0 (archive) and T1 (Stage A @0.9) had
#   already completed successfully, so this script resumes at T2 and runs the
#   remainder. It must NOT re-run Stage A.
#
# INTERLOCKS
#   1. Stage A output tuned_cifar10_a0.1.json MUST exist. If it is missing we
#      abort (exit 92) rather than silently re-tuning: tune_hp.py re-run
#      recomputes `best` over the grid minus the previous winner and overwrites
#      the selected hyper-params (negative_results.md 13.2).
#   2. Refuses to start while another python job is alive.
#   3. Every task logs start/end + exit status to the ledger; a failure stops
#      the queue instead of stacking on half-finished data.
#
# THREADING: FL_THREADS is deliberately NOT set, so rank_inv_runner.py keeps
# its default of 2 -- identical to the 112 Stage B runs already on disk.
# (Discipline 9: thread count must not change mid-study.)
# ============================================================================

set -u
PY=../.venv/Scripts/python.exe
OUT=../results/rank_inv
DECAY=0.9
LEDGER=../results/PHASE5_LEDGER.md
QUEUE_START=$(date "+%Y-%m-%d %H:%M:%S")

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LEDGER"; }

task_begin() {
    TASK="$1"; DESC="$2"
    T_BEGIN=$(date "+%Y-%m-%d %H:%M:%S")
    log ""
    log "## $TASK -- $DESC"
    log "   start   : $T_BEGIN"
}

task_end() {
    RC=$1
    T_END=$(date "+%H:%M:%S")
    if [ "$RC" -eq 0 ]; then
        log "   finish  : $T_END   STATUS=OK"
    else
        log "   finish  : $T_END   STATUS=FAILED (exit $RC)"
        log "   !! queue stopped here. Fix before resuming."
        exit "$RC"
    fi
}

{
echo ""
echo "=================================================================="
echo "Plan B RESUME started $QUEUE_START  (from T2, 10/28 CIFAR-10 runs done)"
echo "=================================================================="
} >> "$LEDGER"

log "=== RESUME BEGIN $QUEUE_START ==="
log "host time now : $(date '+%Y-%m-%d %H:%M:%S %a')"

# --- interlock 2: no competing job
BUSY=$(tasklist 2>/dev/null | grep -ci "python.exe" || true)
if [ "${BUSY:-0}" -gt 0 ]; then
    log "   waiting for $BUSY existing python process(es) to finish..."
    for i in $(seq 1 60); do
        sleep 10
        BUSY=$(tasklist 2>/dev/null | grep -ci "python.exe" || true)
        [ "${BUSY:-0}" -eq 0 ] && break
    done
fi
BUSY=$(tasklist 2>/dev/null | grep -ci "python.exe" || true)
if [ "${BUSY:-0}" -gt 0 ]; then
    log "   ABORT: another python job still running after 10 min wait."
    exit 90
fi
log "   interlock: no competing python job."

# --- interlock 1: Stage A must already be done (do NOT re-run it)
if [ ! -f "$OUT/tuned_cifar10_a0.1.json" ]; then
    log "   ABORT: tuned_cifar10_a0.1.json missing. Stage A must not be re-run here."
    exit 92
fi
log "   interlock: tuned_cifar10_a0.1.json present -> Stage A confirmed done, skipping it."

# ============================================================================
# T2 -- CIFAR-10 Stage B at lr_decay=0.9 (resumes; 10 of 28 already on disk)
# ============================================================================
task_begin "T2(resume)" "CIFAR-10 Stage B at lr_decay=$DECAY -- 18 runs remaining"
$PY rank_inv_runner.py --datasets cifar10 --alphas 0.1 \
    --seeds 0,1,2,3 --rounds 60 --lr 0.05 --lr-decay "$DECAY" \
    --out-dir "$OUT" --stage B
RC=$?
log "   output   : $(ls "$OUT" | grep -c '^cifar10_a0.1_')/28 cifar10_a0.1_*.json"
task_end $RC

# ============================================================================
# T3 -- MNIST decay probes, seeds 0 and 2 (seed 1 already exists)
# ============================================================================
for SD in 0 2; do
    task_begin "T3.s$SD" "MNIST decay-starvation probe, seed $SD"
    $PY check_decay_starvation.py --dataset mnist --alpha 0.1 --rounds 60 \
        --lr 0.05 --decays 0.9,0.95,0.98,1.0 --methods scaffold,fedavg \
        --seed "$SD" --out "$OUT/_decay_mnist_s$SD.json"
    RC=$?
    if [ -f "$OUT/_decay_mnist_s$SD.txt" ]; then
        grep -E "^  decay|^--- |^    spread" "$OUT/_decay_mnist_s$SD.txt" \
            | sed 's/^/      /' | tee -a "$LEDGER"
    fi
    task_end $RC
done

# ============================================================================
# T4 -- re-run the analyser over the now-complete grid
# ============================================================================
task_begin "T4a" "analyse, absolute target grid"
$PY analyze_rank_inv.py --dir "$OUT" --out "$OUT/rank_inv_report_alpha_sweep.json"
task_end $?

task_begin "T4b" "analyse, relative (ceiling-fraction) target grid"
$PY analyze_rank_inv.py --dir "$OUT" --out "$OUT/rank_inv_report_alpha_sweep_rel.json" \
    --target-mode relative --rho-lo 0.50 --rho-hi 0.98 --n-rel-targets 25
task_end $?

# ============================================================================
# T5 -- regenerate figure and table from the widened data
# ============================================================================
task_begin "T5a" "regenerate Figure 1"
$PY make_fig1.py
task_end $?

task_begin "T5b" "regenerate Table 2"
$PY make_table_knob.py
task_end $?

log ""
log "=== RESUME QUEUE END $(date '+%Y-%m-%d %H:%M:%S') ==="
log "Next: integrity check, then update verified_numbers.md and rewrite the draft."
