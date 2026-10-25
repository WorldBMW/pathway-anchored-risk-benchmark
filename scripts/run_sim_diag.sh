#!/usr/bin/env bash
# MRP-ST simulation: full diagnostic batch
# 3 arms x {FULL, NOALL} x seeds 0,1,2 = 18 runs.
# Sequential on one GPU; run_sim_one.sh skips runs whose JSON already exists,
# so this command is safe to re-run after an interruption.
#
# Usage:  bash scripts/run_sim_diag.sh [perm_n]
set -u

PERM="${1:-200}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ONE="$SCRIPT_DIR/run_sim_one.sh"

n=0
for g in group_A group_B group_C; do
  for v in FULL NOALL; do
    for s in 0 1 2; do
      echo "==================================================================="
      echo "[$(date '+%H:%M:%S')] $g / $v / seed=$s / perm_n=$PERM  ($((++n))/18)"
      echo "==================================================================="
      bash "$ONE" "$g" "$v" "$s" "$PERM" || {
        echo "FAILED at $g/$v/seed$s — stopping. Fix and re-run this same command."
        exit 1
      }
    done
  done
done

echo "ALL 18 DIAGNOSTIC RUNS COMPLETE."
echo "Next: python scripts/mrpst_lodo.py 10000"
