#!/usr/bin/env bash
# =============================================================================
# rerun_2026-09-15_regfix.sh
#
# Full rerun after the 2026-09-15 image-registration bug fix in
# src/st_data.py (standard Visium tissue_positions fullres coords were never
# multiplied by tissue_hires_scalef; 31/35 sections received identical
# corner-clamped H&E patches). GSE208654 (hires_scalef=1.0) and every
# expression-only analysis were numerically unaffected.
#
# MUST sync these fixed/new files to the server before running:
#   src/st_data.py                         (coordinate fix)
#   scripts/notes1_uni_embed_moran.py     (new, Note S1)
#
# Usage:
#   bash scripts/rerun_2026-09-15_regfix.sh 0     preflight + clean stale cache
#   bash scripts/rerun_2026-09-15_regfix.sh 1     Note S1 (frozen UNI Moran)
#   bash scripts/rerun_2026-09-15_regfix.sh 2     deploy checkpoint (seed42)
#   bash scripts/rerun_2026-09-15_regfix.sh 3     multiseed image-using variants
#   bash scripts/rerun_2026-09-15_regfix.sh 4     B=10000 label permutation p
#   bash scripts/rerun_2026-09-15_regfix.sh 5     MAIN_KEGG + 30 random panels
#   bash scripts/rerun_2026-09-15_regfix.sh 6     LODOv2: 4 semi + 4 unsup folds
#   bash scripts/rerun_2026-09-15_regfix.sh 7     external re-scoring (new ckpt)
#   bash scripts/rerun_2026-09-15_regfix.sh 8     downstream + corrected numbers
#   bash scripts/rerun_2026-09-15_regfix.sh all   1->2->3->4->5->6->7->8
#
# After `all`, sync the results/ JSONs (+npz) back to the workstation and run
# the document generators locally:
#   python scripts/gen_figures_v10.py
#   python scripts/gen_supplementary_v10.py
#   python scripts/gen_word_v10.py
#   python scripts/gen_submission_v10.py
# =============================================================================
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

DATA=data/st_visium/cervix_all_ext
LABELS=data/st_visium/labels/cervix_histology_labels_extended.csv
HNSCC268=data/st_visium/geo_hnscc_hpv_GSE268014
HNSCC281=data/st_visium/geo_hpv_hnscc_GSE281978
CKPT=results/checkpoint_FULL_DEPLOY_FAST_seed42.pt

# final locked protocol (46,820 spots)
RECON=0.2; NEIGH=0.3; HPV=1.0; SUP=5.0; PROG=1.5
EPOCHS=40
PERMN=1000
LOGDIR=logs/regfix20260915
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
  python -c "import json;d=json.load(open('results/results_${rid}.json'));print('[$(ts)] OK $rid n=%s moran=%.4f auc=%.4f'%(d['n_spots'],d['moran_i'],d['hpv_proxy_auc']))"
}

# ---------------------------------------------------------------- stage 0
stage0() {
  hr; echo "[$(ts)] STAGE 0 — preflight + purge pre-fix FM caches"; hr
  # the two files this rerun depends on
  grep -q "pxl_row \* scale" src/st_data.py \
    || { echo "[FAIL] src/st_data.py coordinate fix not found — sync it first"; return 1; }
  [ -f scripts/notes1_uni_embed_moran.py ] \
    || { echo "[FAIL] scripts/notes1_uni_embed_moran.py missing"; return 1; }
  [ -f fm_cache/UNI/UNI-pytorch_model.bin ] \
    || { echo "[FAIL] fm_cache/UNI/UNI-pytorch_model.bin missing"; return 1; }
  n=$(find "$DATA" -maxdepth 1 -mindepth 1 \( -type d -o -type l \) 2>/dev/null | wc -l)
  echo "cervix_all_ext entries: $n (expected 35)"
  [ "$n" -eq 35 ] || { echo "[FAIL] rebuild $DATA (see run_multiseed.sh ensure_dataset)"; return 1; }
  nvidia-smi --query-gpu=memory.used,memory.total --format=csv 2>/dev/null || true
  # CRITICAL: cache key has no code-version hash. Every fm cache built before
  # the fix contains corner-clamped features for the 31 scalef<1 sections.
  echo "purging stale FM backbone caches ..."
  rm -fv results/cache/fm_uni_*.pt results/cache/fm_uni2_*.pt 2>/dev/null | tail -3
  echo "[$(ts)] STAGE 0 OK"
}

# ---------------------------------------------------------------- stage 1
stage1() {
  hr; echo "[$(ts)] STAGE 1 — Note S1: frozen-UNI within-slide Moran's I"; hr
  python -u scripts/notes1_uni_embed_moran.py \
    --data "$DATA" --out results/uni_embed_moran_s1.json \
    --n_perm 10000 --seed 20260915 2>&1 | tee "$LOGDIR/notes1.log"
}

# ---------------------------------------------------------------- stage 2
stage2() {
  hr; echo "[$(ts)] STAGE 2 — deploy checkpoint (FULL, seed 42, final protocol)"; hr
  rm -f "$CKPT" results/results_FULL_DEPLOY_FAST.json
  # checkpoint is saved as results/checkpoint_<run_id>_seed<seed>.pt
  train FULL_DEPLOY_FAST --seed 42 --save_checkpoint
  [ -f "$CKPT" ] || { echo "[FAIL] $CKPT not produced"; return 1; }
}

# ---------------------------------------------------------------- stage 3
stage3() {
  hr; echo "[$(ts)] STAGE 3 — multiseed variants that actually consume images"; hr
  # NO-IMAGE seeds are NOT redone: with --disable_image_branch the image tensor
  # never reaches the risk head; those results are mathematically independent of
  # patch content and stay valid.
  for s in 0 3 4; do rm -f results/results_FULL_seed$s.json results/fused_embs_FULL_seed$s.npz; done
  for s in 0 1 2; do rm -f results/results_NOHPV_seed$s.json results/fused_embs_NOHPV_seed$s.npz; done
  for s in 0 1 2; do rm -f results/results_NONEIGH_seed$s.json results/fused_embs_NONEIGH_seed$s.npz; done
  for s in 0 1 2 3; do rm -f results/results_NOPROG_seed$s.json results/fused_embs_NOPROG_seed$s.npz; done
  for s in 0 3 4; do train FULL_seed$s   --seed $s || return 1; done
  for s in 0 1 2; do train NOHPV_seed$s  --seed $s --lambda_hpv 0 || return 1; done
  for s in 0 1 2; do train NONEIGH_seed$s --seed $s --no_neigh || return 1; done
  for s in 0 1 2 3; do train NOPROG_seed$s --seed $s --lambda_prog 0 || return 1; done
  echo "[$(ts)] STAGE 3 OK (NO-IMAGE seeds 0/1/2 retained unchanged)"
}

# ---------------------------------------------------------------- stage 4
stage4() {
  hr; echo "[$(ts)] STAGE 4 — sample-level label permutation p (B=10000)"; hr
  python -u scripts/rank_perm_check.py 2>&1 | tee "$LOGDIR/rank_perm.log"
}

# ---------------------------------------------------------------- stage 5
stage5() {
  hr; echo "[$(ts)] STAGE 5 — MAIN_KEGG reference + 30 size-matched random panels"; hr
  echo "NOTE: this uses the ORIGINAL control protocol (30,000-spot cap, "
  echo "recon=1.0/hpv=0.5/sup=2/prog=1) so random-vs-KEGG stays like-for-like."
  rm -f results/results_MAIN_KEGG.json results/results_RANDOM108_S*.json
  python -u scripts/train_st.py \
    --data "$DATA" --histology_label_csv "$LABELS" --hpv_gene_set kegg_hpv \
    --lambda_recon 1.0 --lambda_neigh 0.3 --lambda_hpv 0.5 \
    --lambda_sup 2.0 --lambda_prog 1.0 --epochs $EPOCHS --seed 42 --fm_cache \
    --run_id MAIN_KEGG > "$LOGDIR/MAIN_KEGG.log" 2>&1 \
    || { echo "[FAIL] MAIN_KEGG"; tail -30 "$LOGDIR/MAIN_KEGG.log"; return 1; }
  for s in $(seq 0 29); do
    python -u scripts/train_st.py \
      --data "$DATA" --histology_label_csv "$LABELS" --hpv_gene_set random:108:$s \
      --lambda_recon 1.0 --lambda_neigh 0.3 --lambda_hpv 0.5 \
      --lambda_sup 2.0 --lambda_prog 1.0 --epochs $EPOCHS --seed $s --fm_cache \
      --run_id RANDOM108_S$s > "$LOGDIR/RANDOM108_S$s.log" 2>&1 \
      || { echo "[FAIL] RANDOM108_S$s"; tail -30 "$LOGDIR/RANDOM108_S$s.log"; return 1; }
    echo "[$(ts)] RANDOM108_S$s done"
  done
  python -u scripts/random_control_summary.py | tee "$LOGDIR/random_summary.log"
}

# ---------------------------------------------------------------- stage 6
lodo_fold() {  # $1=tag-suffix disease  $2=extra (empty | unsup flags)
  local d=$1; shift
  local rid=$1; shift
  rm -f "results/results_${rid}.json"
  python -u scripts/train_st.py \
    --data "$DATA" --histology_label_csv "$LABELS" --hpv_gene_set kegg_hpv \
    --lambda_recon $RECON --lambda_neigh $NEIGH --lambda_hpv $HPV \
    --global_patch_cap 0 --epochs $EPOCHS --fm_cache --permutation_n $PERMN \
    --leave_out_substr "$d" --run_id "$rid" "$@" > "$LOGDIR/${rid}.log" 2>&1
  local rc=$?
  if [ $rc -ne 0 ]; then echo "[FAIL] $rid"; tail -30 "$LOGDIR/${rid}.log"; return 1; fi
  python -c "import json;d=json.load(open('results/results_${rid}.json'));assert d['n_samples']==34,(d['n_samples']);print('[$(ts)] OK $rid n_train=34 holdout=%s'%list(d.get('holdout',{}).keys()))"
}
stage6() {
  hr; echo "[$(ts)] STAGE 6 — LODOv2 4 semi + 4 unsupervised folds (34 train each)"; hr
  for d in HSIL_HPV CA_HPV_1 CA_HPV_2 cervical_cancer_1; do
    lodo_fold "$d" "LODOv2_$d" --seed 42 --lambda_sup $SUP --lambda_prog $PROG || return 1
  done
  for d in HSIL_HPV CA_HPV_1 CA_HPV_2 cervical_cancer_1; do
    lodo_fold "$d" "UNSUP_LODOv2_$d" --seed 42 --lambda_sup 0 --lambda_prog 0 || return 1
  done
  echo "[$(ts)] STAGE 6 OK"
}

# ---------------------------------------------------------------- stage 7
stage7() {
  hr; echo "[$(ts)] STAGE 7 — external re-scoring with the new checkpoint"; hr
  [ -f "$CKPT" ] || { echo "[FAIL] run stage 2 first"; return 1; }
  # (a) GeoMx GSE316098 (expression branch only)
  python -u scripts/score_geomx.py --checkpoint "$CKPT" \
    --out results/external_gse316098_validation_FINAL.json 2>&1 | tee "$LOGDIR/geomx.log"
  # (b) HNSCC FINAL inference, expression-only, ALL spots, locked section lists
  python -u scripts/infer_st.py --checkpoint "$CKPT" \
    --data "$HNSCC268" --expression_only --max_spots 0 --run_id XCOHORT_HNSCC_FINAL \
    --only GSM8283897,GSM8283898,GSM8283899,GSM8283900,GSM8283901,GSM8283902,GSM8283903,GSM8283904 \
    2>&1 | tee "$LOGDIR/hnscc268.log"
  python -u scripts/infer_st.py --checkpoint "$CKPT" \
    --data "$HNSCC281" --expression_only --max_spots 0 --run_id XCOHORT_HNSCC_GSE281978_FINAL \
    --only LI_SING_21_00757,LI_SING_21_00758,LI_SING_21_01569,LI_SING_21_01570,LI_SING_21_01586,LI_SING_21_01587 \
    2>&1 | tee "$LOGDIR/hnscc281.log"
  # (c) coordinate-permutation null + discriminative section-level tests
  python -u scripts/hnscc_moran_permutation_control.py \
    --g268014_full results/infer_XCOHORT_HNSCC_FINAL_full.json \
    --g281978_full results/infer_XCOHORT_HNSCC_GSE281978_FINAL_full.json \
    --out results/hnscc_moran_permutation_control_FINAL.json 2>&1 | tee "$LOGDIR/hnscc_perm.log"
  python -u scripts/hnscc_discriminative_eval.py \
    --g268014_full results/infer_XCOHORT_HNSCC_FINAL_full.json \
    --g281978_full results/infer_XCOHORT_HNSCC_GSE281978_FINAL_full.json \
    2>&1 | tee "$LOGDIR/hnscc_disc.log"
  # (d) TCGA-CESC expression-branch direct score (the stated negative result)
  python -u scripts/apply_model_to_tcga.py --checkpoint "$CKPT" \
    --out results/apply_model_tcga.json 2>&1 | tee "$LOGDIR/tcga.log"
  echo "[$(ts)] STAGE 7 OK"
}

# ---------------------------------------------------------------- stage 8
stage8() {
  hr; echo "[$(ts)] STAGE 8 — downstream analysis + corrected external numbers"; hr
  python -u scripts/downstream_spot_analysis.py --run_id FULL_seed0 \
    2>&1 | tee "$LOGDIR/downstream.log"
  # GeoMx corrected stats from the FINAL scores; LODO stats read LODOv2/UNSUP
  GEO_MX_SCORE_JSON=results/external_gse316098_validation_FINAL.json \
  GEO_MX_OUT=results/external_corrected_numbers.json \
    python -u scripts/build_external_corrected.py 2>&1 | tee "$LOGDIR/external_corr.log"
  echo "[$(ts)] STAGE 8 OK — sync results/ back and run the doc generators locally"
}

case "${1:-help}" in
  0) stage0 ;;
  1) stage1 ;;
  2) stage2 ;;
  3) stage3 ;;
  4) stage4 ;;
  5) stage5 ;;
  6) stage6 ;;
  7) stage7 ;;
  8) stage8 ;;
  all) stage0 && stage1 && stage2 && stage3 && stage4 && stage5 && stage6 && stage7 && stage8 ;;
  *) sed -n '2,30p' "$0" ;;
esac
