#!/bin/bash
# ============================================================================
# CMPB v1.3 ONE-SHOT SERVER RUNNER
# ============================================================================
# Purpose:
#   Run ALL v1.3 validation scripts + main training on a Linux server.
#   Produces honest results JSONs for manuscript revision.
#
# Prerequisites:
#   - Linux (Ubuntu/Debian/CentOS) with Python 3.10.x
#   - NVIDIA GPU with CUDA (optional but STRONGLY recommended)
#   - 16GB+ RAM (32GB+ for scanpy + 35 slices + torch simultaneous import)
#   - conda / mamba (recommended) or pip
#
# Usage:
#   # 1. cd to project root
#   cd /path/to/project4_cervix_multimodal
#
#   # 2. (Recommended) conda env
#   conda create -n cmpb python=3.10 -y && conda activate cmpb
#
#   # 3. Install deps
#   pip install -r requirements.txt
#
#   # 4. Run everything (single GPU, use CUDA_VISIBLE_DEVICES=1 to pick)
#   bash run_server.sh
#
#   # 5. Optional: skip long steps for quick smoke test
#   bash run_server.sh --skip-loso --skip-random
#
# Outputs (all under results/):
#   results/results_FULL.json              ← main model (should already exist)
#   results/results_NO-NEIGH.json           ← ablation (should already exist)
#   results/results_NO-HPV.json             ← ablation (should already exist)
#   results/align_hpv_cervix35.json          ← HPV signature (should already exist)
#   results/cox_multivar_adjusted.json       ← NEW: Cox honest result ✅
#   results/moran_null_model.json            ← NEW: Moran baseline vs model
#   results/hpv_auc_loso.json                ← NEW: LOSO held-out AUC (MAKE-OR-BREAK)
#   results/random_pathway_control.json      ← NEW: 10x random gene AUC (optional)
#   results/v1.3_honest_summary.json         ← NEW: ALL numbers in one place
#
# Timing estimates (single RTX 3090 / A100, CPU fallback for LOSO):
#   - Step 0 DataCheck:     <1 min
#   - Step 1 Main Train:     ~30 min (GPU) / ~3 h (CPU)
#   - Step 2 Ablations:      ~60 min (3 runs, GPU)
#   - Step 3 align_hpv:      ~5 min
#   - Step 4 Cox multivar:   ~5 min
#   - Step 5 Moran null:     ~10 min
#   - Step 6 HPV AUC LOSO:   ~2 h (GPU) / ~6 h (CPU)  ← MAKE-OR-BREAK
#   - Step 7 Random control: ~4 h CPU (optional)
#   Total with all:          ~4-12 h depending on GPU
# ============================================================================
set -euo pipefail

# --- Environment ---
export PYTHONHASHSEED=42
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-}"  # "" = all GPUs visible
export HDF5_DISABLE_VERSION_CHECK=1

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# --- Helpers ---
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
log() { echo -e "${GREEN}[v1.3]${NC} $(date '+%H:%M:%S') $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*"; exit 1; }
ok() { echo -e "${GREEN}[OK]${NC} $*"; }
step() { echo -e "\n${CYAN}========== $* ==========${NC}"; }

# --- Parse args ---
SKIP_LOSO=false; SKIP_RANDOM=false; SMOKE=false
for arg in "$@"; do
  case "$arg" in
    --skip-loso)    SKIP_LOSO=true ;;
    --skip-random)  SKIP_RANDOM=true ;;
    --smoke)        SMOKE=true ;;
  esac
done

# --- Auto-detect device ---
if python -c "import torch; print('cuda' if torch.cuda.is_available() else 'cpu')" 2>/dev/null | grep -q cuda; then
  DEVICE="cuda"
  NGPUS=$(python -c "import torch; print(torch.cuda.device_count())")
  log "GPU detected: ${NGPUS} card(s) available"
else
  DEVICE="cpu"
  warn "CUDA not available — falling back to CPU. This will be SLOW (6-12 h for LOSO)."
fi

log "Python: $(python --version)"
log "Working dir: $PROJECT_DIR"

# ============================================================================
step "0/8 DATA INTEGRITY CHECK"
# ============================================================================
EXPECTED_SLICES=(
  "geo_cesc/CA_HPV_1" "geo_cesc/CA_HPV_2" "geo_cesc/HSIL_HPV" "geo_cesc/N_HPV"
  "cervical_cancer_1"
  "geo_ectocervix/P001" "geo_ectocervix/P004" "geo_ectocervix/P007"
  "geo_ectocervix/P008" "geo_ectocervix/P014" "geo_ectocervix/P016"
  "geo_ectocervix/P018" "geo_ectocervix/P020" "geo_ectocervix/P021"
  "geo_ectocervix/P023" "geo_ectocervix/P024" "geo_ectocervix/P026"
  "geo_ectocervix/P028" "geo_ectocervix/P031" "geo_ectocervix/P044"
  "geo_ectocervix/P045" "geo_ectocervix/P047" "geo_ectocervix/P050"
  "geo_ectocervix/P057" "geo_ectocervix/P067" "geo_ectocervix/P080"
  "geo_ectocervix/P081" "geo_ectocervix/P087" "geo_ectocervix/P097"
  "geo_ectocervix/P105" "geo_ectocervix/P107" "geo_ectocervix/P108"
  "geo_ectocervix/P114" "geo_ectocervix/P117" "geo_ectocervix/P118"
)
MISSING=()
for s in "${EXPECTED_SLICES[@]}"; do
  h5="data/st_visium/$s/filtered_feature_bc_matrix.h5"
  pos="data/st_visium/$s/spatial/tissue_positions_list.csv"
  if [ ! -f "$h5" ] && [ ! -f "data/st_visium/$s/spatial/tissue_positions.csv" ]; then
    MISSING+=("$s")
  fi
done
if [ ${#MISSING[@]} -gt 0 ]; then
  fail "Missing ST slices (${#MISSING[@]}): ${MISSING[*]}"
fi
ok "All ${#EXPECTED_SLICES[@]} ST slices present"

for f in "data/cesc/cesc_clinical.csv" "data/cesc/cesc_rnaseq.csv" \
         "data/st_visium/labels/cervix_histology_labels_extended.csv"; do
  [ -f "$f" ] || fail "Missing: $f"
done
ok "Clinical + RNA-seq + labels present"

RESULTS="results"
mkdir -p "$RESULTS"
log "Results dir: $RESULTS"

# ============================================================================
step "1/8 MAIN MODEL TRAINING (train_st.py)"
# ============================================================================
# Re-run if results_FULL.json missing; skip if exists
if [ -f "$RESULTS/results_FULL.json" ]; then
  log "results_FULL.json already exists — skip main training"
else
  log "Starting main training (epochs=40, device=$DEVICE)..."
  python scripts/train_st.py \
    --data data/st_visium \
    --device "$DEVICE" \
    --fm uni \
    --epochs 40 \
    --dump_fused \
    --run_id FULL \
    --results_dir "$RESULTS"
  ok "Main training complete → results_FULL.json"
fi

# ============================================================================
step "2/8 ABLATION RUNS (if missing)"
# ============================================================================
for AB in "NO-NEIGH" "NO-HPV"; do
  if [ -f "$RESULTS/results_${AB}.json" ]; then
    log "results_${AB}.json exists — skip"
  else
    log "Running ablation $AB ..."
    FLAGS=""
    [ "$AB" = "NO-NEIGH" ] && FLAGS="--no_neigh"
    [ "$AB" = "NO-HPV" ]   && FLAGS="--lambda_hpv 0"
    python scripts/train_st.py \
      --data data/st_visium --device "$DEVICE" --fm uni --epochs 40 \
      --run_id "$AB" --results_dir "$RESULTS" $FLAGS
    ok "$AB ablation done"
  fi
done

# ============================================================================
step "3/8 HPV ALIGNMENT (align_hpv.py)"
# ============================================================================
if [ -f "$RESULTS/align_hpv_cervix35.json" ]; then
  log "align_hpv_cervix35.json exists — skip"
else
  python scripts/align_hpv.py \
    --results "$RESULTS/results_FULL.json" \
    --clinical data/cesc/cesc_clinical.csv \
    --rnaseq data/cesc/cesc_rnaseq.csv
  # align_hpv.py writes to results/align_hpv_results.json; rename
  [ -f "$RESULTS/align_hpv_results.json" ] && mv "$RESULTS/align_hpv_results.json" "$RESULTS/align_hpv_cervix35.json"
  ok "HPV alignment complete"
fi

# ============================================================================
step "4/8 COX MULTIVAR PATCH (cox_multivar_patch.py)"
# ============================================================================
log "Running Cox 4-step multivar (with auto-patch from vital_status)..."
python scripts/cox_multivar_patch.py \
  --rnaseq data/cesc/cesc_rnaseq.csv \
  --clinical data/cesc/cesc_clinical.csv \
  --signature_genes "$RESULTS/align_hpv_cervix35.json" \
  --out "$RESULTS/cox_multivar_adjusted.json"
ok "Cox result → results/cox_multivar_adjusted.json (HONEST: expect all p>0.4)"

# ============================================================================
step "5/8 MORAN NULL MODEL (moran_null_model_validation.py)"
# ============================================================================
log "Running Moran I null model (raw counts vs FULL vs NO-NEIGH)..."
python scripts/moran_null_model_validation.py \
  --data data/st_visium \
  --labels data/st_visium/labels/cervix_histology_labels_extended.csv \
  --results_dir "$RESULTS"
ok "Moran null model done → results/moran_null_model.json"

# ============================================================================
step "6/8 HPV AUC NON-CIRCULAR LOSO (hpv_auc_non_circular_validation.py) [MAKE-OR-BREAK]"
# ============================================================================
if [ "$SKIP_LOSO" = true ]; then
  warn "--skip-loso: skipping LOSO (MAKE-OR-BREAK step!)"
else
  log "Running LOSO held-out AUC (35 folds, device=$DEVICE)..."
  if [ "$SMOKE" = true ]; then
    log "SMOKE mode: limiting to 3 folds"
    python scripts/hpv_auc_non_circular_validation.py \
      --data data/st_visium \
      --labels data/st_visium/labels/cervix_histology_labels_extended.csv \
      --results_dir "$RESULTS" \
      --rnaseq data/cesc/cesc_rnaseq.csv \
      --device "$DEVICE" --max_folds 3 || warn "SMOKE LOSO failed (may need GPU)"
  else
    python scripts/hpv_auc_non_circular_validation.py \
      --data data/st_visium \
      --labels data/st_visium/labels/cervix_histology_labels_extended.csv \
      --results_dir "$RESULTS" \
      --rnaseq data/cesc/cesc_rnaseq.csv \
      --device "$DEVICE"
  fi
  ok "LOSO done → results/hpv_auc_loso.json"
  echo ""
  log "===== INTERPRETATION GUIDE ====="
  log "  LOSO AUC >= 0.70  → STORY HOLDS (real generalization)"
  log "  LOSO AUC 0.60-0.70 → WEAK but salvageable"
  log "  LOSO AUC < 0.60   → HPV anchor story COLLAPSES"
fi

# ============================================================================
step "7/8 RANDOM PATHWAY CONTROL (random_pathway_control.py) [OPTIONAL]"
# ============================================================================
if [ "$SKIP_RANDOM" = true ]; then
  warn "--skip-random: skipping 10x random gene control"
else
  log "Running 10x random 108-gene control (epochs=20, device=$DEVICE)..."
  python scripts/random_pathway_control.py \
    --data data/st_visium \
    --labels data/st_visium/labels/cervix_histology_labels_extended.csv \
    --results_dir "$RESULTS" \
    --n_permutations 10 --epochs 20 \
    --device "$DEVICE" || warn "Random control failed (may need more GPU RAM)"
  ok "Random control done → results/random_pathway_control.json"
fi

# ============================================================================
step "8/8 V1.3 HONEST SUMMARY ASSEMBLY"
# ============================================================================
python -c "
import json, pathlib
R = pathlib.Path('results')
summary = {}
for name in ['results_FULL', 'results_NO-NEIGH', 'results_NO-HPV',
             'align_hpv_cervix35', 'cox_multivar_adjusted',
             'moran_null_model', 'hpv_auc_loso', 'random_pathway_control']:
    fp = R / f'{name}.json'
    if fp.exists():
        try:
            summary[name] = json.loads(fp.read_text())
        except Exception as e:
            summary[name] = f'parse_error: {e}'
    else:
        summary[name] = 'MISSING'
summary['generation_time'] = __import__('datetime').datetime.now().isoformat()
(R / 'v1.3_honest_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2))
print('Summary keys:', list(summary.keys()))
"
ok "Honest summary → results/v1.3_honest_summary.json"

# ============================================================================
echo ""
log "====================================="
log "  CMPB v1.3 COMPLETE!"
log "====================================="
log ""
log "Key new results (vs v1.2):"
log "  Cox:           results/cox_multivar_adjusted.json"
log "  Moran null:    results/moran_null_model.json"
if [ "$SKIP_LOSO" != true ]; then
log "  LOSO AUC:      results/hpv_auc_loso.json   ← CHECK THIS FIRST!"
fi
if [ "$SKIP_RANDOM" != true ]; then
log "  Random ctrl:   results/random_pathway_control.json"
fi
log "  ALL IN ONE:    results/v1.3_honest_summary.json"
log ""
log "Next step: open results/v1.3_honest_summary.json and report HONEST numbers"
log "           in the CMPB v1.3 manuscript."
log ""
log "If LOSO AUC < 0.60 → HPV anchor story needs restructuring."
log "If all Cox models p>0.4 → report HPV sig as biol. discovery, not prognostic."
