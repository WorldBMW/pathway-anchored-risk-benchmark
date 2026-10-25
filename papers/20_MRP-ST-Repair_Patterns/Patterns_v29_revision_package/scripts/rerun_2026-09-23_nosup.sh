#!/usr/bin/env bash
# =============================================================================
# rerun_2026-09-23_nosup.sh
#
# Adds the missing NO-SUP ablation arm to the JBI Table 3 matrix:
#   NO-SUP = lambda_sup 0 AND lambda_prog 0 (true zero-label arm), everything
#   else identical to the locked protocol (recon 0.2 / neigh 0.3 / hpv 1.0,
#   kegg_hpv panel, 40 epochs, fm_cache). Three seeds 0/1/2, matching
#   FULL/NO-HPV/NO-NEIGH. This is the same flag combination already proven by
#   the UNSUP_LODOv2_* folds in rerun_2026-09-15_regfix.sh.
#   train_st.py guard (2026-09-23): diagnostic-probe early stopping is disabled
#   whenever lambda_sup=0, so NO-SUP always runs the full locked 40 epochs (no
#   disease-derived quantity may control training length).
#
# Outputs (per seed s):
#   results/results_NOSUP_seed$s.json
#   results/fused_embs_NOSUP_seed$s.npz
# then regenerates results/rank_perm_B10000.json (B=10,000 permutation p for
# every variant, including NOSUP).
#
# Usage on the AutoDL server, from the repo root:
#   bash scripts/rerun_2026-09-23_nosup.sh preflight   # checks only
#   bash scripts/rerun_2026-09-23_nosup.sh all         # train 3 seeds + perm p
#
# After it finishes, sync back to the workstation:
#   results/results_NOSUP_seed{0,1,2}.json
#   results/fused_embs_NOSUP_seed{0,1,2}.npz
#   results/rank_perm_B10000.json
# then locally run:
#   python scripts/gen_figures_v10.py
#   copy /Y papers\07_CSBJ_v10\Figures\Fig3_ablation_multiseed.png papers\08_JBI\Figures\
#   python scripts/gen_supplementary_v10.py
#   python scripts/gen_jbi.py
# =============================================================================
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

DATA=data/st_visium/cervix_all_ext
LABELS=data/st_visium/labels/cervix_histology_labels_extended.csv

# final locked protocol (same as rerun_2026-09-15_regfix.sh)
RECON=0.2; NEIGH=0.3; HPV=1.0; SUP=5.0; PROG=1.5
EPOCHS=40
PERMN=1000
LOGDIR=logs/nosup20260923
mkdir -p "$LOGDIR" results
export PYTHONUNBUFFERED=1

ts() { date '+%Y-%m-%d %H:%M:%S'; }
hr() { printf '=%.0s' {1..72}; printf '\n'; }

train() {  # $1=run_id $2=extra args...
  local rid=$1; shift
  local log="$LOGDIR/${rid}.log"
  echo "[$(ts)] START $rid -> $log"
  python -u scripts/train_st.py \
    --data "$DATA" --histology_label_csv "$LABELS" --hpv_gene_set kegg_hpv \
    --lambda_recon $RECON --lambda_neigh $NEIGH --lambda_hpv $HPV \
    --lambda_sup $SUP --lambda_prog $PROG \
    --global_patch_cap 0 --epochs $EPOCHS --fm_cache --permutation_n $PERMN \
    --run_id "$rid" --dump_fused "$@" > "$log" 2>&1
  local rc=$?
  if [ $rc -ne 0 ]; then echo "[FAIL] $rid rc=$rc — tail $log"; tail -30 "$log"; return 1; fi
  python -c "import json;d=json.load(open('results/results_${rid}.json'));print('[$(ts)] OK $rid n=%s moran=%.4f lambda_sup=%s lambda_prog=%s'%(d['n_spots'],d['moran_i'],d['lambda_sup'],d['lambda_prog']))"
}

preflight() {
  hr; echo "[$(ts)] PREFLIGHT"; hr
  [ -d "$DATA" ] || { echo "[FAIL] $DATA missing"; return 1; }
  n=$(find "$DATA" -maxdepth 1 -mindepth 1 \( -type d -o -type l \) 2>/dev/null | wc -l)
  echo "cervix_all_ext entries: $n (expected 35)"
  [ "$n" -eq 35 ] || { echo "[FAIL] rebuild $DATA"; return 1; }
  [ -f "$LABELS" ] || { echo "[FAIL] labels csv missing: $LABELS"; return 1; }
  [ -f fm_cache/UNI/UNI-pytorch_model.bin ] \
    || echo "[warn] fm_cache/UNI/UNI-pytorch_model.bin missing (first run will download/extract)"
  nvidia-smi --query-gpu=memory.used,memory.total --format=csv 2>/dev/null || true
  echo "[$(ts)] PREFLIGHT OK"
}

run_all() {
  preflight || return 1
  hr; echo "[$(ts)] NO-SUP seeds 0/1/2 (lambda_sup=0 lambda_prog=0)"; hr
  for s in 0 1 2; do
    rm -f "results/results_NOSUP_seed$s.json" "results/fused_embs_NOSUP_seed$s.npz"
    train "NOSUP_seed$s" --seed "$s" --lambda_sup 0 --lambda_prog 0 || return 1
  done
  hr; echo "[$(ts)] B=10,000 sample-level label permutation p (all variants)"; hr
  python -u scripts/rank_perm_check.py 2>&1 | tee "$LOGDIR/rank_perm.log" || return 1
  echo "[$(ts)] ALL DONE — sync the 7 files listed in the script header back to the workstation"
}

case "${1:-help}" in
  preflight) preflight ;;
  all) run_all ;;
  *) sed -n '2,38p' "$0" ;;
esac
