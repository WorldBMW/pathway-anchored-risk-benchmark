#!/usr/bin/env bash
# ============================================================================
# C2 · scale-matched positive-control arm.
#
# The main three-arm validation was generated at 50 normal + 40 diseased = 90
# donors. The real cervical cohort is 31 normal + 4 diseased = 35 donors. This
# script regenerates the SAME three arms (A/B/C) at the real cohort scale and
# re-runs the audit, so the pre-registered grading thresholds can be checked
# where it matters most — the smallest, most label-starved regime.
#
# Steps: (1) generate scale-matched cohorts, (2) train {FULL,NOALL} x
# {A,B,C}_small x seeds {0,1,2} = 18 runs, (3) official three-tier grading.
# Sequential on one GPU; run_sim_one.sh skips runs whose JSON already exists,
# so this command is safe to re-run after an interruption.
#
# Usage:  bash scripts/run_sim_small.sh [perm_n]
# Output: data/sim_st_small/{group_A_small,group_B_small,group_C_small}
#         results/sim_lodo_summary_small.json   (main summary left untouched)
# ============================================================================
set -u

PERM="${1:-10000}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
ONE="$SCRIPT_DIR/run_sim_one.sh"
DATA="$ROOT/data/sim_st_small"

echo "===== [1/3] generate scale-matched cohorts (31 normal + 4 diseased) ====="
python "$SCRIPT_DIR/simulate_st_positive_control.py" \
  --out "$DATA" --n_normal 31 --n_diseased 4 --tag small --seed 20261006

echo "===== [2/3] train {FULL,NOALL} x {A,B,C}_small x seeds 0,1,2 (18 runs) ====="
export DATA_ROOT="$DATA"
n=0
for g in group_A_small group_B_small group_C_small; do
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

echo "===== [3/3] official three-tier grading (scale-matched) ====="
python "$SCRIPT_DIR/mrpst_lodo.py" "$PERM" \
  --groups group_A_small group_B_small group_C_small \
  --seeds 0 1 2 --out sim_lodo_summary_small.json

echo "DONE. Compare results/sim_lodo_summary_small.json against results/sim_lodo_summary.json."