#!/usr/bin/env bash
# ============================================================================
# Single-run launcher for the MRP-ST positive-control simulation audit.
# Lets you run ONE group × ONE variant × ONE seed at a time for fast
# diagnostics, instead of committing to all 63 runs up front.
#
# Usage:
#   bash scripts/run_sim_one.sh <group> <variant> <seed> [perm_n]
#
#   group:   group_A | group_B | group_C
#   variant: FULL | NOIMAGE | NOHPV | NONEIGH | NOPROG | NOSUP | NOALL
#   seed:    0 | 1 | 2
#   perm_n:  optional permutation count (default 10000; use 200 for quick
#            diagnostics — τ is unaffected, only p-value precision is coarser)
#
# Examples:
#   # fast 6-run diagnostic (~30-40 min, perm_n=200):
#   bash scripts/run_sim_one.sh group_A FULL   0 200
#   bash scripts/run_sim_one.sh group_A NOALL  0 200
#
#   # paper-grade single run:
#   bash scripts/run_sim_one.sh group_C NOSUP  1
# ============================================================================
set -euo pipefail

GROUP=${1:?"usage: run_sim_one.sh <group> <variant> <seed> [perm_n]"}
VARIANT=${2:?"missing variant: FULL|NOIMAGE|NOHPV|NONEIGH|NOPROG|NOSUP|NOALL"}
SEED=${3:?"missing seed: 0|1|2"}
PERM_N=${4:-10000}
DATA_ROOT=${DATA_ROOT:-data/sim_st}

case "$VARIANT" in
  FULL)    EXTRA="" ;;
  NOIMAGE) EXTRA="--disable_image_branch" ;;
  NOHPV)   EXTRA="--lambda_hpv 0" ;;
  NONEIGH) EXTRA="--no_neigh" ;;
  NOPROG)  EXTRA="--lambda_prog 0" ;;
  NOSUP)   EXTRA="--lambda_sup 0 --lambda_prog 0" ;;
  NOALL)   EXTRA="--lambda_sup 0 --lambda_prog 0 --lambda_hpv 0" ;;
  *) echo "[error] unknown variant: $VARIANT"; exit 1 ;;
esac

mkdir -p logs results
RUN_ID="SIM_${GROUP}_${VARIANT}_seed${SEED}"
OUT_JSON="results/results_${RUN_ID}.json"

# skip if a result already exists (resume support)
if [ -f "${OUT_JSON}" ]; then
  echo "[skip] ${OUT_JSON} already exists — delete it first if you want to rerun"
  exit 0
fi

echo "===== ${GROUP} / ${VARIANT} / seed=${SEED} / perm_n=${PERM_N} ====="
python scripts/train_st.py \
  --data "${DATA_ROOT}/${GROUP}" \
  --seed "${SEED}" \
  --run_id "${RUN_ID}" \
  --hpv_gene_set kegg_hpv \
  --fm none \
  --n_genes 3000 \
  --permutation_n "${PERM_N}" \
  --dump_fused \
  ${EXTRA} \
  2>&1 | tee "logs/sim_${GROUP}_${VARIANT}_seed${SEED}.log"
