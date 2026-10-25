#!/usr/bin/env bash
# =============================================================================
# MRP-ST operating-characteristic grid (A3)
# -----------------------------------------------------------------------------
# Purpose: replace the single-realisation simulations (1 generator cohort x 3
# training seeds, which only measures optimisation variation) with an INDEPENDENT
# REPLICATION grid, so that detection rate (power) and type-I error of the
# MRP-ST grading rule can be estimated. This is the experiment that turns the
# "audit workflow" into a "validated protocol".
#
# Design (edit the CONFIG block below to change):
#   generator seeds : 3 independent realisations
#   signal levels   : 4 shared-program amplitudes, strong -> weak
#   neg. control    : identity-confounding arm C (in-sample separable, no
#                     disease signal) -> type-I error estimate
#   sample scales   : main    = 50 normal + 40 diseased
#                     matched = 31 normal +  4 diseased (real-cohort scale)
#   training seeds  : 0, 1, 2
#   variants        : NOALL on every arm (primary label-free readout)
#                     FULL on the control arm only (in-sample contrast)
#
#   => 3 x 4 x 2 x 3 = 72 primary runs + 3 x 2 x 3 x 2 = 36 control runs = 108
#
# Resume: run_sim_one.sh skips any run whose results JSON already exists, so
# this script is safe to re-launch after an interruption or a preemption.
#
# On AutoDL:
#   cd /root/<path>/project4_cervix_multimodal
#   nohup bash scripts/run_sim_power_grid.sh > logs/power_grid.log 2>&1 &
#   tail -f logs/power_grid.log
#   # after it finishes:
#   python scripts/sim_power_grid.py
# =============================================================================
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p logs results data

# ------------------------------- CONFIG --------------------------------------
PERM="${PERM:-10000}"                        # label permutations per probe
OUTROOT="${OUTROOT:-data/sim_power}"         # generated cohorts live here
GEN_SEEDS="${GEN_SEEDS:-20261006 20261007 20261008}"
LEVELS="${LEVELS:-L1:2.5 L2:1.0 L3:0.4 L4:0.20}"   # label:shared-program amplitude
TRAIN_SEEDS="${TRAIN_SEEDS:-0 1 2}"
SIZES="${SIZES:-main small}"
WITH_CONTROL="${WITH_CONTROL:-1}"
CTRL_SIGNAL="${CTRL_SIGNAL:-1.2}"
# -----------------------------------------------------------------------------

export DATA_ROOT="$OUTROOT"   # consumed by run_sim_one.sh

n_done=0; n_fail=0

size_args ()   { case "$1" in main) echo "--n_normal 50 --n_diseased 40";;
                            small) echo "--n_normal 31 --n_diseased 4";; esac; }
size_suffix () { case "$1" in small) echo "_small";; *) echo "";; esac; }

run_one () {  # $1=group $2=variant $3=seed
  if bash scripts/run_sim_one.sh "$1" "$2" "$3" "$PERM"; then
    n_done=$((n_done + 1))
  else
    n_fail=$((n_fail + 1)); echo "[FAIL] $1 / $2 / seed$3"
  fi
}

echo "############## MRP-ST operating-characteristic grid ##############"
echo " generator seeds : $GEN_SEEDS"
echo " signal levels   : $LEVELS"
echo " sample sizes    : $SIZES"
echo " training seeds  : $TRAIN_SEEDS   (perm=$PERM)"
echo " call : run_sim_one.sh <group> <variant> <seed> $PERM"
echo " output root     : $OUTROOT"
echo "##################################################################"

for g in $GEN_SEEDS; do
  for lv in $LEVELS; do
    lab="${lv%%:*}"; amp="${lv##*:}"
    for sz in $SIZES; do
      tag="g${g}_${lab}$(size_suffix "$sz")"
      grp="group_A_${tag}"
      echo "=== [gen] $grp  (signal_a=$amp, size=$sz) ==="
      python scripts/simulate_st_positive_control.py \
        --out "$OUTROOT" --seed "$g" --only A --signal_a "$amp" \
        --tag "$tag" $(size_args "$sz") \
        2>&1 | tee -a "logs/gen_${grp}.log"
      for ts in $TRAIN_SEEDS; do
        run_one "$grp" NOALL "$ts"
      done
    done
  done

  if [ "$WITH_CONTROL" = "1" ]; then
    for sz in $SIZES; do
      tag="g${g}_CTRL$(size_suffix "$sz")"
      grp="group_C_${tag}"
      echo "=== [gen] $grp  (identity control, signal_c=$CTRL_SIGNAL, size=$sz) ==="
      python scripts/simulate_st_positive_control.py \
        --out "$OUTROOT" --seed "$g" --only C --signal_c "$CTRL_SIGNAL" \
        --tag "$tag" $(size_args "$sz") \
        2>&1 | tee -a "logs/gen_${grp}.log"
      for ts in $TRAIN_SEEDS; do
        run_one "$grp" NOALL "$ts"
        run_one "$grp" FULL  "$ts"
      done
    done
  fi
done

echo "############## grid finished: ok=$n_done  fail=$n_fail ##############"
echo "Next:  python scripts/sim_power_grid.py"