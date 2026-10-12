#!/usr/bin/env bash
# ============================================================================
# Plan B queue -- CIFAR-10 rebuilt at lr_decay=0.9 + missing-metric probes
#
# Started at 23:10 local time by the one-time automation. Runs every task
# SEQUENTIALLY so no two training jobs compete for CPU.
#
# Why Plan B (see results/CHECKPOINT.md section 3, addendum 1):
#   CIFAR-10's Stage A was tuned at lr_decay=1.0, which our own notes admit
#   unfairly degrades SCAFFOLD. Plan B re-tunes and re-runs CIFAR-10 at 0.9 so
#   all three datasets share one protocol, at the cost of lower absolute
#   accuracy there (0.4975 -> 0.3765 for FedAvg late acc, measured earlier).
#
# SAFETY INTERLOCKS
#   1. Stage A refuses to run if tuned_cifar10_a0.1.json already exists.
#      tune_hp.py's resume recomputes `best` over the grid MINUS the previous
#      winner and then overwrites it -- silently replacing selected hyper-params.
#      The only safe Stage A is a clean one. (See negative_results.md 13.2.)
#   2. Every task logs start/end time and exit status to the ledger.
#   3. Refuses to start while another training job is alive.
# ============================================================================

set -u
PY=../.venv/Scripts/python.exe
OUT=../results/rank_inv
ARCHIVE="$OUT/_archive"
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

# ---------------------------------------------------------------- preamble
{
echo ""
echo "=================================================================="
echo "Plan B queue started $QUEUE_START"
echo "=================================================================="
} >> "$LEDGER"

log "=== QUEUE BEGIN $QUEUE_START (Plan B: CIFAR-10 @ lr_decay=$DECAY) ==="
log "host time now : $(date '+%Y-%m-%d %H:%M:%S %a')"

# --- interlock 3: no other training job alive
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
    log "   ABORT: another python job is still running after 10 min wait."
    exit 90
fi
log "   interlock: no competing python job. Proceeding."

mkdir -p "$ARCHIVE"

# ============================================================================
# T0 -- archive the decay=1.0 Stage A file so Stage A can run clean
# ============================================================================
task_begin "T0" "archive decay=1.0 CIFAR-10 Stage A (Plan B supersedes it)"
if [ -f "$OUT/tuned_cifar10_a0.1.json" ]; then
    mv "$OUT/tuned_cifar10_a0.1.json" \
       "$ARCHIVE/tuned_cifar10_a0.1__DECAY1.0_superseded_by_planB.json"
    log "   moved -> $ARCHIVE/tuned_cifar10_a0.1__DECAY1.0_superseded_by_planB.json"
else
    log "   nothing to archive (file already absent)"
fi
# interlock 1
if [ -f "$OUT/tuned_cifar10_a0.1.json" ]; then
    log "   ABORT: tuned file still present; Stage A would silently corrupt it."
    exit 91
fi
log "   interlock: tuned_cifar10_a0.1.json absent -> clean Stage A guaranteed."
task_end 0

# ============================================================================
# T1 -- CIFAR-10 Stage A at lr_decay=0.9   (~53 min)
# ============================================================================
task_begin "T1" "CIFAR-10 Stage A re-tuned at lr_decay=$DECAY (18 configs)"
$PY tune_hp.py --datasets cifar10 --alphas 0.1 --rounds 60 \
    --lr 0.05 --lr-decay "$DECAY" --seed 0 --out-dir "$OUT"
RC=$?
log "   output   : $OUT/tuned_cifar10_a0.1.json ($(stat -c%s "$OUT/tuned_cifar10_a0.1.json" 2>/dev/null || echo ?) bytes)"
if [ -f "$OUT/tuned_cifar10_a0.1.json" ]; then
    $PY - <<'PYEOF' 2>&1 | tee -a "$LEDGER"
import json
d = json.load(open("../results/rank_inv/tuned_cifar10_a0.1.json", encoding="utf-8"))
for k, v in d.items():
    print("      %-22s %-26s late=%.4f peak=%.4f stable=%s" %
          (k.split("|")[2], v.get("label"), v.get("late_acc", 0),
           v.get("peak_acc", 0), any(s.get("stable") for s in v.get("settings", []))))
PYEOF
fi
task_end $RC

# ============================================================================
# T2 -- CIFAR-10 Stage B at lr_decay=0.9   (~70-100 min)
# ============================================================================
task_begin "T2" "CIFAR-10 Stage B at lr_decay=$DECAY (7 methods x 4 seeds = 28 runs)"
$PY rank_inv_runner.py --datasets cifar10 --alphas 0.1 \
    --seeds 0,1,2,3 --rounds 60 --lr 0.05 --lr-decay "$DECAY" \
    --out-dir "$OUT" --stage B
RC=$?
log "   output   : $(ls "$OUT" | grep -c '^cifar10_a0.1_')/28 cifar10_a0.1_*.json"
task_end $RC

# ============================================================================
# T3 -- MNIST decay probes, seeds 0 and 2
#      Existing data covers MNIST seed 1 ONLY; the paper's Limitations admits
#      the 0.90-0.95 divergence threshold rests on a single seed. Adding two
#      seeds removes that caveat. (8 runs per seed: 2 methods x 4 decays)
# ============================================================================
for SD in 0 2; do
    task_begin "T3.s$SD" "MNIST decay-starvation probe, seed $SD (confirms the 0.90-0.95 threshold)"
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
# T5 -- regenerate figures and tables from the widened data
# ============================================================================
task_begin "T5a" "regenerate Figure 1 (ceiling now reflects Plan B CIFAR-10)"
$PY make_fig1.py
task_end $?

task_begin "T5b" "regenerate Table 2 (knob table)"
$PY make_table_knob.py
task_end $?

log ""
log "=== QUEUE END $(date '+%Y-%m-%d %H:%M:%S') ==="
log "Next: integrity check, then update verified_numbers.md and rewrite the draft."
