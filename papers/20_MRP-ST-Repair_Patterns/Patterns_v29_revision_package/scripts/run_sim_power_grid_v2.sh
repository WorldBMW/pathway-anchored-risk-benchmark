#!/usr/bin/env bash
# =============================================================================
# MRP-ST operating-characteristic grid  ** v2: graded difficulty **
# -----------------------------------------------------------------------------
# v1 problem (verified 2026-10-13): amplitudes 2.5/1.0/0.4/0.2 ALL saturate
# the LODO probe (tau identical across levels) because (i) even amp=0.2 of a
# coherent shared program is trivially separable across 40 donors and (ii) the
# simulator had a hard amp>0.05 capture switch -> on/off cliff.
#
# v2 design (calibrated by raw-expression LODO pilot):
#   * responder amplitude fixed at 0.10 (continuous amplitude-coupled capture)
#   * difficulty graded by NON-RESPONDER fraction (donors with zero footprint),
#     i.e. clinical response heterogeneity:
#         L1 0.00  L2 0.25  L3 0.50  L4 0.75
#   * per-donor program-gene dropout 0.80
#   pilot gradient (3 gen seeds, raw-expression probe):
#     main  tau 0.705 -> 0.321 -> 0.162 -> 0.130
#     small tau 0.457 -> 0.390 -> 0.245 -> 0.093
#
#   control arm C regenerated identically (spurious branch unchanged); its
#   v1 training outputs are copied back, so the 36 control runs are SKIPPED.
# =============================================================================
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p logs results data

# ------------------------------- CONFIG --------------------------------------
PERM="${PERM:-2000}"
OUTROOT="${OUTROOT:-data/sim_power_v2}"
GEN_SEEDS="${GEN_SEEDS:-20261006 20261007 20261008}"
# label:responder_amplitude:nonresponder_fraction
LEVELS="${LEVELS:-L1:0.10:0.00 L2:0.10:0.25 L3:0.10:0.50 L4:0.10:0.75}"
PRESENT="${PRESENT:-0.80}"
TRAIN_SEEDS="${TRAIN_SEEDS:-0 1 2}"
SIZES="${SIZES:-main small}"
WITH_CONTROL="${WITH_CONTROL:-1}"
CTRL_SIGNAL="${CTRL_SIGNAL:-1.2}"
# -----------------------------------------------------------------------------

export DATA_ROOT="$OUTROOT"

n_done=0; n_fail=0

size_args ()   { case "$1" in main) echo "--n_normal 50 --n_diseased 40";;
                            small) echo "--n_normal 31 --n_diseased 4";; esac; }
size_suffix () { case "$1" in small) echo "_small";; *) echo "";; esac; }

run_one () {
  if bash scripts/run_sim_one.sh "$1" "$2" "$3" "$PERM"; then
    n_done=$((n_done + 1))
  else
    n_fail=$((n_fail + 1)); echo "[FAIL] $1 / $2 / $3"
  fi
}

echo "############## MRP-ST v2 graded grid ##############"
echo " levels          : $LEVELS"
echo " present_prob    : $PRESENT   perm=$PERM"
echo " output root     : $OUTROOT"
echo "###################################################"

for g in $GEN_SEEDS; do
  for lv in $LEVELS; do
    lab="$(echo "$lv" | cut -d: -f1)"
    amp="$(echo "$lv" | cut -d: -f2)"
    nr="$(echo "$lv"  | cut -d: -f3)"
    for sz in $SIZES; do
      tag="g${g}_${lab}$(size_suffix "$sz")"
      grp="group_A_${tag}"
      echo "=== [gen] $grp (amp=$amp nonresp=$nr present=$PRESENT $sz) ==="
      python scripts/simulate_st_positive_control.py \
        --out "$OUTROOT" --seed "$g" --only A --signal_a "$amp" \
        --nonresp_a "$nr" --present_a "$PRESENT" \
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
      echo "=== [gen] $grp (identity control, $sz; training outputs reused from v1) ==="
      python scripts/simulate_st_positive_control.py \
        --out "$OUTROOT" --seed "$g" --only C --signal_c "$CTRL_SIGNAL" \
        --tag "$tag" $(size_args "$sz") \
  2>&1 | tee -a "logs/gen_${grp}.log"
      for ts in $TRAIN_SEEDS; do
        run_one "$grp" NOALL "$ts"
        run_one "$grp" FULL "$ts"
      done
    done
  fi
done

echo "############## v2 grid finished: ok=$n_done fail=$n_fail ##############"
echo "Next:  python scripts/sim_power_grid.py --force"
