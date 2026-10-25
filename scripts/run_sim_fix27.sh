#!/usr/bin/env bash
# ============================================================================
# MRP-ST simulation: targeted 27-run paper-grade repair batch.
#
# Why this batch exists
# ---------------------
# Audit of results/results_SIM_*.json (63 files) showed:
#   * NOPROG (9): kendall_tau = null  -> old train_st.py (pre tau-fix), 10-06
#   * NOSUP seed1/2 (6): null         -> old train_st.py, 10-06/10-07
#   * FULL (9) + NOSUP seed0 (3): valid tau but permutation_n = 200 (p only
#     resolved to 0.005), i.e. the 10-08 quick diagnostic, not paper grade
# This script reruns FULL + NOPROG + NOSUP x 3 arms x 3 seeds = 27 runs at
# permutation_n = 10000 with the FIXED train_st.py.
#
# Deliberately KEPT (do not delete, not rerun here):
#   * NOALL (9): frozen fused npz already feed scripts/mrpst_lodo.py which
#     computes its own B=10000 probe permutations -> sim_lodo_summary.json;
#     the NOALL scalar head is direction-unidentifiable and is NOT evidence.
#   * NOIMAGE / NOHPV / NONEIGH (27): already perm=10000 with valid tau.
#
# Resume-safe: run_sim_one.sh skips any run whose result JSON already exists.
# After deletion of the 27 stale JSONs this runs exactly 27 trainings; if
# interrupted, re-run the same command and it continues where it stopped.
#
# Usage (server, inside the repo, GPU env activated):
#   bash scripts/run_sim_fix27.sh [perm_n]      # default 10000
# ============================================================================
set -u

PERM="${1:-10000}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ONE="$SCRIPT_DIR/run_sim_one.sh"

n=0
for g in group_A group_B group_C; do
  for v in FULL NOPROG NOSUP; do
    for s in 0 1 2; do
      echo "==================================================================="
      echo "[$(date '+%F %T')] ($((++n))/27) $g / $v / seed=$s / perm_n=$PERM"
      echo "==================================================================="
      bash "$ONE" "$g" "$v" "$s" "$PERM" || {
        echo "FAILED at $g / $v / seed=$s — fix and re-run this same command (resume-safe)."
        exit 1
      }
    done
  done
done

echo ""
echo "===== ALL 27 FIX RUNS COMPLETE ====="
echo "[1/2] official three-tier LODO grading (NOALL frozen embeddings, B=10000)"
python scripts/mrpst_lodo.py 10000
echo "[2/2] seven-variant cascade aggregation (for Supplementary Table S3)"
python scripts/aggregate_sim_audit.py
echo "DONE."
