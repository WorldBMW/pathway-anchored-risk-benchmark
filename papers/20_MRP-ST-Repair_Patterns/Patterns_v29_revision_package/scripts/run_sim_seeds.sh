#!/usr/bin/env bash
# MRP-ST simulation: diagnostic batch, 3 arms x {FULL, NOALL} x seeds 1,2
# plus the stale group_B NOALL seed0 (v2 leftover must be redone on v2.1).
# Sequential on one GPU; run_sim_one.sh skips runs whose JSON already exists,
# so this command is safe to re-run after an interruption.
#
# Usage:  bash scripts/run_sim_seeds.sh [perm_n]
set -u

PERM="${1:-200}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ONE="$SCRIPT_DIR/run_sim_one.sh"

# stale v2 leftover -> force redo
RES_DIR="$(dirname "$SCRIPT_DIR")/results"
rm -f "$RES_DIR/results_SIM_group_B_NOALL_seed0.json" \
      "$RES_DIR/fused_embs_SIM_group_B_NOALL_seed0.npz"

n=0
for g in group_A group_B group_C; do
  for v in FULL NOALL; do
    for s in 1 2; do
      echo "==================================================================="
      echo "[$(date '+%H:%M:%S')] $g / $v / seed=$s / perm_n=$PERM  ($((++n))/13)"
      echo "==================================================================="
      bash "$ONE" "$g" "$v" "$s" "$PERM" || {
        echo "FAILED at $g/$v/seed$s — stopping. Fix and re-run this same command."
        exit 1
      }
    done
  done
done

# plus the redone B NOALL seed0 (13th run)
echo "==================================================================="
echo "[$(date '+%H:%M:%S')] group_B / NOALL / seed=0 (v2.1 redo)  (13/13)"
echo "==================================================================="
bash "$ONE" group_B NOALL 0 "$PERM"

echo "ALL 13 DIAGNOSTIC RUNS COMPLETE."
echo "Next: python scripts/mrpst_lodo.py 10000"
