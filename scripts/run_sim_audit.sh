#!/usr/bin/env bash
# ============================================================================
# Positive-control simulation audit for MRP-ST / LDI validation.
# Runs the SAME 7-variant audit on 3 simulated cohorts (A=strong, B=weak,
# C=no-signal+batch) to prove the audit discriminates correctly.
#
# Usage (server, GPU):
#   bash scripts/run_sim_audit.sh
#
# Outputs: results/results_SIM_<group>_<variant>_seed<s>.json
# Aggregate: python scripts/aggregate_sim_audit.py
# ============================================================================
set -euo pipefail

PYTHON=${PYTHON:-python}
DATA_ROOT=${DATA_ROOT:-data/sim_st}
SEEDS="0 1 2"

# Common flags:
#  --hpv_gene_set kegg_hpv : real KEGG-HPV panel matches simulated pathway genes
#  --fm none               : simulated H&E is placeholder; no FM backbone
#  --n_genes 3000          : full simulated panel (matches simulate script default)
#  --permutation_n 10000   : paper-grade permutation null
COMMON="--hpv_gene_set kegg_hpv --fm none --n_genes 3000 --permutation_n 10000 --dump_fused"

run_variant () {
    local group=$1
    local variant=$2
    local seed=$3
    local extra=$4
    local data_dir="${DATA_ROOT}/${group}"
    local run_id="SIM_${group}_${variant}_seed${seed}"
    echo "===== [${group}] ${variant} seed=${seed} ====="
    ${PYTHON} scripts/train_st.py \
        --data "${data_dir}" \
        --seed "${seed}" \
        --run_id "${run_id}" \
        ${COMMON} \
        ${extra} \
        2>&1 | tee "logs/sim_${group}_${variant}_seed${seed}.log"
}

mkdir -p logs results

for GROUP in group_A group_B group_C; do
    for SEED in ${SEEDS}; do
        # FULL
        run_variant ${GROUP} FULL ${SEED} ""
        # NO-IMAGE
        run_variant ${GROUP} NOIMAGE ${SEED} "--disable_image_branch"
        # NO-HPV
        run_variant ${GROUP} NOHPV ${SEED} "--lambda_hpv 0"
        # NO-NEIGH
        run_variant ${GROUP} NONEIGH ${SEED} "--no_neigh"
        # NO-PROG (remove ordinal labels)
        run_variant ${GROUP} NOPROG ${SEED} "--lambda_prog 0"
        # NO-SUP (remove labels + proxy)
        run_variant ${GROUP} NOSUP ${SEED} "--lambda_sup 0 --lambda_prog 0"
        # NO-ALL (remove labels + proxy + pathway prior)
        run_variant ${GROUP} NOALL ${SEED} "--lambda_sup 0 --lambda_prog 0 --lambda_hpv 0"
    done
done

echo ""
echo "===== ALL SIMULATION AUDIT RUNS COMPLETE ====="
echo "Next: python scripts/aggregate_sim_audit.py"
