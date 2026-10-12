#!/usr/bin/env bash
# ============================================================================
# decay-starvation probe -- extend to 6 seeds (execution_plan_20261011.md, A-2)
#
# WHY
#   execution_plan v2 section 1.3: if Stage B moves to 6 seeds while the probe
#   stays at 3-4, the seed-count asymmetry that reviewers M3/M13 complained
#   about simply moves somewhere else. So the probe is brought to 6 seeds too.
#
# GAP AUDIT (done before writing this script)
#   on disk: _decay_mnist_s0, s1, s2            -> need s3, s4, s5
#            _decay_cifar_s1, s2                 -> need s0, s3, s4, s5
#   (cifar is missing s0 as well, i.e. 4 seeds, not the 3 the plan assumed:
#    7 seed-files x 8 runs = 56 runs, not 48.)
#
# WHAT IS DELIBERATELY NOT CHANGED
#   --rounds 60 --lr 0.05 --decays 0.9,0.95,0.98,1.0 --methods scaffold,fedavg:
#   identical to the five probe files already on disk, so the new seeds are
#   directly comparable with them.
#   FL_THREADS is NOT set -> rank_inv_runner default of 2 is inherited.
#
# HONEST-REPORTING RULE (execution_plan discipline 4)
#   Whatever the new seeds do to the 0.90-0.95 divergence verdict, it is
#   reported as measured. Adding seeds buys statistical power, not a favourable
#   result; selectively dropping a seed is grounds for reworking the task.
# ============================================================================

set -u
PY="${PYTHON:-python}"
cd "$(dirname "$0")" || exit 1
OUT=../results/rank_inv
LOG=../results/_decay_seeds_queue.log
LEDGER=../results/PHASE5_LEDGER.md

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG" >> "$LEDGER"; }

{
echo ""
echo "=================================================================="
echo "A-2 decay probe seed extension started $(date '+%Y-%m-%d %H:%M:%S')"
echo "=================================================================="
echo "gap: mnist s3,s4,s5 | cifar10 s0,s3,s4,s5  (56 runs)"
} >> "$LEDGER"

log "=== A-2 BEGIN $(date '+%Y-%m-%d %H:%M:%S') ==="

BUSY=$(tasklist 2>/dev/null | grep -ci "python.exe" || true)
if [ "${BUSY:-0}" -gt 0 ]; then
    log "   ABORT: ${BUSY} python process(es) alive. Serial queue only."
    exit 90
fi
log "   interlock: no competing python job."

run_probe() {
    DS="$1"; TAG="$2"; SD="$3"
    log "## A2.${TAG}.s${SD} -- decay probe ${DS} seed ${SD} (8 runs)"
    "$PY" check_decay_starvation.py --dataset "$DS" --alpha 0.1 --rounds 60 \
        --lr 0.05 --decays 0.9,0.95,0.98,1.0 --methods scaffold,fedavg \
        --seed "$SD" --out "$OUT/_decay_${TAG}_s${SD}.json"
    RC=$?
    if [ "$RC" -ne 0 ]; then
        log "   A2.${TAG}.s${SD} FAILED (exit $RC) -- queue stopped here"
        exit "$RC"
    fi
    log "   A2.${TAG}.s${SD} finish OK"
}

for SD in 3 4 5; do run_probe mnist mnist "$SD"; done
for SD in 0 3 4 5; do run_probe cifar10 cifar "$SD"; done

log "=== A-2 QUEUE END $(date '+%Y-%m-%d %H:%M:%S') ==="
