#!/usr/bin/env bash
# =========================================================================
#  run_CMPB_reproduce.sh  —  一键复现 CMPB v1.2 全文所有数值结果（24h CPU）
#  Windows 用户请用 PowerShell 运行 run_CMPB_reproduce_WINDOWS.ps1（同目录）。
# =========================================================================
set -euo pipefail

export PYTHONHASHSEED=42
export CUBLAS_WORKSPACE_CONFIG=":4096:8"
SEED=42

echo "======================================================"
echo "  CMPB v1.2  Full Reproduction Script"
echo "  Expected runtime: ~24 h on 16-core CPU (no GPU)"
echo "  With GPU (8 GB VRAM): ~6 h"
echo "======================================================"
echo ""

# ------------------------------------------------------------------
# 0. Check Python 3.10.14 + environment
# ------------------------------------------------------------------
echo "[0/5] Environment check"
PYVER=$(python -c "import sys;print('%d.%d.%d'%sys.version_info[:3])")
if [ "$PYVER" != "3.10.14" ]; then
  echo "[WARN] Expected Python 3.10.14 (locked in v1.2 Data Availability); got $PYVER"
  echo "       → Numerical reproducibility not guaranteed. Consider pyenv/conda install."
fi

python -c "
import pandas, numpy, scipy, sklearn, lifelines, matplotlib, seaborn, statsmodels, scanpy, squidpy, torch, docx
print('  pandas', pandas.__version__,  '(need 2.3.3)')
print('  numpy ', numpy.__version__,   '(need 2.1.3)')
print('  scipy ', scipy.__version__,   '(need 1.14.1)')
print('  skl   ', sklearn.__version__, '(need 1.6.1)')
print('  life  ', lifelines.__version__,'(need 0.30.0)')
print('  matpl ', matplotlib.__version__,'(need 3.10.9)')
print('  seab  ', seaborn.__version__,  '(need 0.13.5)')
print('  stats ', statsmodels.__version__,'(need 0.14.4)')
print('  scan  ', scanpy.__version__,   '(need 1.10.3)')
print('  squid ', squidpy.__version__,  '(need 1.5.1)')
print('  torch ', torch.__version__,    '(need 2.3.1)')
print('  docx  ', docx.__version__,     '(need 1.2.0)')
"

# ------------------------------------------------------------------
# 1. FULL multitask training (35 Visium slices)
# ------------------------------------------------------------------
echo "[1/5] FULL multitask training — writes results/results_FULL.json + fused_embs.npz"
python scripts/train_st.py \
  --data data/st_visium --epochs 40 --lr 3e-4 --bs 256 --n_genes 2000 \
  --lambda_recon 0.2 --lambda_hpv 1.0 --lambda_neigh 0.3 --lambda_sup 5.0 --lambda_prog 1.5 \
  --hpv_gene_set kegg_hpv \
  --histology_label_csv resources/cervix35_histology_labels.csv \
  --run_id FULL --dump_fused --permutation_n 10000 --device cpu \
  --fm uni

# ------------------------------------------------------------------
# 2. 12-criterion audit (MAIN_MODEL_PASS must be 12/12)
# ------------------------------------------------------------------
echo "[2/5] 12-criterion audit (MAIN_MODEL_PASS check)"
python scripts/audit_full_deliverables.py | tee results/MODEL_USAGE_v1.2/_step2_audit.txt
grep -q "MAIN_MODEL_PASS (12/12)" results/MODEL_USAGE_v1.2/_step2_audit.txt \
  && echo "  ✅ MAIN_MODEL_PASS = 12/12" \
  || (echo "  ❌ 12-criterion failed — check step 1 output"; exit 42)

# ------------------------------------------------------------------
# 3. TCGA-CESC cross-modal Cox (Layer 3b, 352-gene signature)
# ------------------------------------------------------------------
echo "[3/5] TCGA-CESC Layer 3b Cox HR (needs data/cesc/cesc_clinical.csv + cesc_rnaseq.csv)"
if [ -f data/cesc/cesc_rnaseq.csv ] && [ -f data/cesc/cesc_clinical.csv ]; then
  python scripts/align_hpv.py \
    --results results/results_FULL.json \
    --clinical data/cesc/cesc_clinical.csv \
    --rnaseq data/cesc/cesc_rnaseq.csv \
    --out results/align_hpv_cervix35.json \
    --enable_cox --deg_fdr 0.05 --deg_delta 0.3 \
    | tee results/MODEL_USAGE_v1.2/_step3_cox.txt
  grep -q "HR = 1.68" results/MODEL_USAGE_v1.2/_step3_cox.txt \
    && echo "  ✅ TCGA HR within tolerance (1.688 expected)" \
    || echo "  ⚠  HR not matched; check lifelines version / TCGA CSV colnames."
else
  echo "  [SKIP] data/cesc/cesc_rnaseq.csv or clinical.csv missing. Download from GDC + Liu2018 CDR first."
fi

# ------------------------------------------------------------------
# 4. Explainability 3 cases (ca1 / ecto_p004 / ecto_p117)
# ------------------------------------------------------------------
echo "[4/5] Explainability 3 cases (saliency + HPV overlay → explain35_*)"
for dir in data/st_visium/geo_cesc/CA_HPV_1  data/st_visium/geo_ectocervix/P004  data/st_visium/geo_ectocervix/P117; do
  out=$(basename "$dir" | sed 's/CA_HPV_1/ca1/;s/P004/ecto_p004/;s/P117/ecto_p117/')
  python scripts/explain_st.py --data "$dir" \
    --out_dir results/explain35_"$out" --epochs 5 --bs 64 --device cpu \
    --lambda_hpv 1.0 --lambda_sup 3.0 --lambda_recon 1.0 --lambda_neigh 0.3 \
    --hpv_gene_set kegg_hpv
done
echo "  ✔ 3 explain dirs produced (explain35_ca1 / explain35_ecto_p004 / explain35_ecto_p117)."

# ------------------------------------------------------------------
# 5. Build the 4 CMPB submission documents (v1.2)
# ------------------------------------------------------------------
echo "[5/5] Build Manuscript / TitlePage / CoverLetter / Highlights → CMPB folder (v1.2)"
python scripts/build_cmpb_paper_final.py

echo ""
echo "======================================================"
echo "  REPRODUCTION COMPLETE. Final checks:"
echo "    1) results/results_FULL.json exists."
echo "    2) MAIN_MODEL_PASS = 12/12 printed (step 2)."
echo "    3) align_hpv_cervix35.json contains layer3b_cox_hpv_proxy (HR 1.688)."
echo "    4) 4 CMPB v1.2 files in papers/01_*/."
echo "  Happy CMPB submission 🎉."
echo "======================================================"
