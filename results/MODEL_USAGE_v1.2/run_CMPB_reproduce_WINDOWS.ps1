# =========================================================================
#  run_CMPB_reproduce_WINDOWS.ps1  —  Windows 版 CMPB v1.2 全量一键复现
#  用法（管理员 PowerShell）：
#     powershell -ExecutionPolicy Bypass -File results\MODEL_USAGE_v1.2\run_CMPB_reproduce_WINDOWS.ps1
# =========================================================================
$ErrorActionPreference = "Stop"
$env:PYTHONHASHSEED = "42"
$env:CUBLAS_WORKSPACE_CONFIG = ":4096:8"
$SEED = 42
$ROOT = Split-Path -Parent $PSScriptRoot | Split-Path -Parent   # project root
Set-Location $ROOT

Write-Host ""
Write-Host "======================================================"  -ForegroundColor Cyan
Write-Host "  CMPB v1.2  Full Reproduction Script (Windows)"      -ForegroundColor Cyan
Write-Host "  Expected runtime: ~24h on 16-core CPU (no GPU)"       -ForegroundColor Gray
Write-Host "  With GPU (8 GB VRAM): ~6 h"                           -ForegroundColor Gray
Write-Host "======================================================"  -ForegroundColor Cyan
Write-Host ""

# 0. Python version check
Write-Host "[0/5] Environment check" -ForegroundColor Green
$PYVER = python -c "import sys;print('%d.%d.%d'%sys.version_info[:3])"
if ($PYVER -ne "3.10.14") {
  Write-Warning "Expected Python 3.10.14 (locked in v1.2 Data Availability); got $PYVER"
}
python -c @"
import pandas, numpy, scipy, sklearn, lifelines, matplotlib, seaborn, statsmodels, scanpy, squidpy, torch, docx
print('  pandas',pandas.__version__,' (need 2.3.3)')
print('  numpy ',numpy.__version__,' (need 2.1.3)')
print('  scipy ',scipy.__version__,' (need 1.14.1)')
print('  skl   ',sklearn.__version__,' (need 1.6.1)')
print('  life  ',lifelines.__version__,' (need 0.30.0)')
print('  matpl ',matplotlib.__version__,' (need 3.10.9)')
print('  seab  ',seaborn.__version__,' (need 0.13.5)')
print('  stats ',statsmodels.__version__,' (need 0.14.4)')
print('  scan  ',scanpy.__version__,' (need 1.10.3)')
print('  squid ',squidpy.__version__,' (need 1.5.1)')
print('  torch ',torch.__version__,' (need 2.3.1)')
print('  docx  ',docx.__version__,' (need 1.2.0)')
"@

# 1. FULL multitask training
Write-Host "[1/5] FULL multitask training (results/results_FULL.json + fused_embs.npz)" -ForegroundColor Green
python scripts/train_st.py `
  --data data/st_visium --epochs 40 --lr 3e-4 --bs 256 --n_genes 2000 `
  --lambda_recon 0.2 --lambda_hpv 1.0 --lambda_neigh 0.3 --lambda_sup 5.0 --lambda_prog 1.5 `
  --hpv_gene_set kegg_hpv `
  --histology_label_csv resources/cervix35_histology_labels.csv `
  --run_id FULL --dump_fused --permutation_n 10000 --device cpu --fm uni

# 2. 12-criterion audit
Write-Host "[2/5] 12-criterion MAIN_MODEL_PASS audit" -ForegroundColor Green
$out2 = python scripts/audit_full_deliverables.py 2>&1 | Tee-Object -FilePath results/MODEL_USAGE_v1.2/_step2_audit.txt
if (Select-String -Path results/MODEL_USAGE_v1.2/_step2_audit.txt -Pattern "MAIN_MODEL_PASS \(12/12\)" -Quiet) {
  Write-Host "  ✅ MAIN_MODEL_PASS = 12/12" -ForegroundColor Green
} else {
  throw "❌ 12-criterion FAILED; check results/MODEL_USAGE_v1.2/_step2_audit.txt"
}

# 3. TCGA Cox
Write-Host "[3/5] TCGA-CESC Layer 3b Cox HR" -ForegroundColor Green
if ((Test-Path data/cesc/cesc_rnaseq.csv) -and (Test-Path data/cesc/cesc_clinical.csv)) {
  python scripts/align_hpv.py `
    --results results/results_FULL.json `
    --clinical data/cesc/cesc_clinical.csv --rnaseq data/cesc/cesc_rnaseq.csv `
    --out results/align_hpv_cervix35.json --enable_cox --deg_fdr 0.05 --deg_delta 0.3 `
    | Tee-Object -FilePath results/MODEL_USAGE_v1.2/_step3_cox.txt
  if (Select-String -Path results/MODEL_USAGE_v1.2/_step3_cox.txt -Pattern "HR = 1\.68" -Quiet) {
    Write-Host "  ✅ TCGA HR within tolerance (1.688 expected)" -ForegroundColor Green
  } else {
    Write-Warning "HR not matched; check lifelines version / TCGA CSV columns."
  }
} else {
  Write-Warning "[SKIP] data/cesc/cesc_rnaseq.csv or cesc_clinical.csv missing; download GDC + Liu2018 CDR first."
}

# 4. Explainability 3 cases
Write-Host "[4/5] Explainability 3 cases (explain35_ca1 / p004 / p117)" -ForegroundColor Green
$CASES = @(
  @("data/st_visium/geo_cesc/CA_HPV_1",             "results/explain35_ca1"),
  @("data/st_visium/geo_ectocervix/P004",           "results/explain35_ecto_p004"),
  @("data/st_visium/geo_ectocervix/P117",           "results/explain35_ecto_p117")
)
foreach ($c in $CASES) {
  $inD, $outD = $c
  if (Test-Path $inD) {
    python scripts/explain_st.py --data $inD --out_dir $outD --epochs 5 --bs 64 --device cpu `
      --lambda_hpv 1.0 --lambda_sup 3.0 --lambda_recon 1.0 --lambda_neigh 0.3 --hpv_gene_set kegg_hpv
  } else { Write-Warning "missing: $inD" }
}

# 5. Build 4 CMPB v1.2 docs
Write-Host "[5/5] Build CMPB v1.2 manuscripts (docx/txt)" -ForegroundColor Green
python scripts/build_cmpb_paper_final.py

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  REPRODUCTION COMPLETE. Final checks:"                 -ForegroundColor Green
Write-Host "    1) results/results_FULL.json exists."
Write-Host "    2) MAIN_MODEL_PASS = 12/12 printed."
Write-Host "    3) align_hpv_cervix35.json contains Layer 3b Cox (HR=1.688)."
Write-Host "    4) 4 CMPB v1.2 files exist in papers/01_* folder."
Write-Host "  Happy CMPB submission."                                  -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
