=============================================================================
CMPB v1.3 SERVER SETUP CHECKLIST
=============================================================================

## 0. QUICK START (tl;dr)
```bash
# On a Linux server with Python 3.10 + CUDA:
cd project4_cervix_multimodal
conda create -n cmpb python=3.10 -y && conda activate cmpb
pip install -r requirements.txt
bash run_server.sh
# Then check results/v1.3_honest_summary.json
```

## 1. HARDWARE REQUIREMENTS
| Item        | Minimum          | Recommended        |
|-------------|------------------|--------------------|
| GPU         | None (CPU)       | 1× RTX 3090 / A100 |
| RAM         | 16 GB            | 32 GB              |
| Storage     | 2 GB (data+code) | 20 GB (with checkpoints) |
| Python      | 3.10.x           | 3.10.x             |

### CPU-only timing (no GPU)
- Step 5 Moran:        ~15 min
- Step 6 LOSO (35 folds): ~6 h ← SLOWEST
- Step 7 Random:        ~4 h
- Total without main train: ~10 h

### With GPU timing
- Step 5 Moran:         ~10 min
- Step 6 LOSO:          ~2 h
- Step 7 Random:        ~2 h  
- Total:                ~4 h

## 2. DATA DIR VERIFICATION
Before running, verify this tree exists:
```
data/
├── cesc/
│   ├── cesc_clinical.csv     (307 rows, columns: case_id, submitter_id, ..., OS_MONTHS, event)
│   └── cesc_rnaseq.csv       (genes × 308 samples, columns = TCGA-XX-XXXX-01)
└── st_visium/
    ├── labels/
    │   └── cervix_histology_labels_extended.csv  (35 rows, 4 columns)
    ├── geo_cesc/
    │   ├── CA_HPV_1/   (has filtered_feature_bc_matrix.h5 + spatial/)
    │   ├── CA_HPV_2/
    │   ├── HSIL_HPV/
    │   └── N_HPV/
    ├── cervical_cancer_1/
    └── geo_ectocervix/
        ├── P001/ ... P028/ P031/ P044/ P045/ P047/ P050/ P057/
        └── P067/ P080/ P081/ P087/ P097/ P105/ P107/ P108/
             P114/ P117/ P118/
```

**CRITICAL NOTE**: No supplementary ST data exists on GEO. These are ALL public 10x Visium
cervical cancer samples. HSIL n=1 / ADC n=1 / SCC n=3 is a DATA LIMITATION, not a bug.

## 3. ENVIRONMENT SETUP
```bash
# Option A: conda (recommended — avoids CUDA/driver conflicts)
conda create -n cmpb python=3.10 -y
conda activate cmpb
pip install -r requirements.txt

# Option B: venv
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Option C: pip system-wide (NOT recommended but works)
pip install -r requirements.txt
```

Verify key imports:
```bash
python -c "
import torch;              print(f'torch {torch.__version__}  cuda={torch.cuda.is_available()}')
import scanpy;             print(f'scanpy {scanpy.__version__}')
import squidpy;            print(f'squidpy {squidpy.__version__}')
import gseapy;             print(f'gseapy {gseapy.__version__}')
from lifelines import CoxPHFitter
from src import models as M; print(f'src.models OK, build_model={hasattr(M,\"build_model\")}')
print('ALL OK')
"
```

## 4. RUN STRATEGIES

### FULL RUN (recommended for first time)
```bash
bash run_server.sh
```
Will auto-skip steps where results already exist (main train + ablations + align_hpv + Cox
are already done in v1.2). Actual work starts at Step 5 (Moran null model).

### QUICK SMOKE TEST (10 min)
```bash
bash run_server.sh --skip-loso --skip-random
```
Only re-runs Moran + Cox + summary assembly. Useful to validate env before LOSO.

### LOSO ONLY (4-6 h CPU, MAKE-OR-BREAK)
```bash
# If you want to run only the critical LOSO step
bash run_server.sh --skip-random
```

### GPU SELECTION
```bash
CUDA_VISIBLE_DEVICES=1 bash run_server.sh        # pick GPU #1
CUDA_VISIBLE_DEVICES=0,1 bash run_server.sh       # use 2 GPUs (run.sh distributes)
CUDA_VISIBLE_DEVICES=""  bash run_server.sh      # force CPU
```

### BACKGROUND RUN (nohup / tmux)
```bash
# tmux session (interactive, recoverable)
tmux new -s cmpb
bash run_server.sh 2>&1 | tee logs/run_v1.3_$(date +%Y%m%d_%H%M%S).log
# Ctrl+B then D to detach; 'tmux attach -t cmpb' to reattach

# nohup (simple but less recoverable)
mkdir -p logs
nohup bash run_server.sh > logs/run_v1.3.log 2>&1 &
tail -f logs/run_v1.3.log
```

## 5. OUTPUTS — WHAT TO CHECK

### results/v1.3_honest_summary.json (ALL NUMBERS IN ONE FILE)
Open this FIRST — it aggregates every step's JSON into one dict.

### Step 4: Cox Multivar (results/cox_multivar_adjusted.json)
**EXPECTED OUTCOME**: ALL models p > 0.4, HR ~ 1.1-1.4 (not significant).
This is HONEST. Report as:
> "HPV proxy signature shows consistent hazard trend (HR = 1.12-1.36 across
> 4 Cox models) but does not reach statistical significance (p = 0.30-0.60).
> This aligns with the known biology: HPV-positive status is a tumorigenesis
> marker (>90% of cervical cancers are HPV-positive) but not an independent
> prognostic factor. The signature's value lies in spatial functional annotation
> rather than direct OS prediction."

### Step 5: Moran Null Model (results/moran_null_model.json)
**EXPECTED OUTCOME**:
| Metric              | Expected range | Interpretation |
|---------------------|---------------|----------------|
| Raw counts Moran I  | 0.85 - 0.92   | Native spatial autocorrelation |
| FULL Moran I        | 0.87 - 0.91   | Model output |
| NO-NEIGH Moran I    | 0.86 - 0.92   | Ablation baseline |
| ΔMoran (FULL - Raw) | < 0.02        | Model doesn't create fake autocorr |

Report as: "Raw HPV gene counts already show strong spatial autocorrelation
(Moran I = X). Our model output retains this native structure (ΔMoran = Y),
indicating the ℒ_neigh term does not artificially inflate spatial
autocorrelation scores."

### Step 6: LOSO AUC (results/hpv_auc_loso.json) [MAKE-OR-BREAK]
**THE MOST IMPORTANT NUMBER IN THE ENTIRE REVISION**.

| LOSO AUC range | Decision |
|----------------|----------|
| ≥ 0.70         | ✅ Story holds. Report as "real generalization AUC = X" |
| 0.60 - 0.70    | ⚠️ Weak salvage. Acknowledge in Limitations |
| < 0.60         | ❌ HPV anchor story collapses. Must restructure manuscript. |

**Note**: The OLD results_FULL.json says AUC=0.994 — that's the CIRCULAR self-test.
It stays in the paper but ONLY as a baseline comparison. The LOSO AUC is the real number.

### Step 7: Random Pathway Control (results/random_pathway_control.json)
**EXPECTED OUTCOME**: Random 108-gene AUC mean = 0.55-0.70 (± ~0.10 SD).
If KEGG_HPV AUC (circular self-test 0.99) >> random mean → proves HPV specificity.
If random mean ≈ 0.90 → any 108 genes work → HPV story collapses.

## 6. TROUBLESHOOTING

### torch CUDA DLL load fails (Windows only)
```bash
# Linux servers won't have this, but if they do:
export CUDA_VISIBLE_DEVICES=""     # force CPU
export PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True"
```

### scanpy import hangs / OOM on Windows
```bash
# Linux servers: not an issue.
# Windows workarounds: increase page file to 32GB+ OR run with --device cpu
```

### "No admissable pairs in the dataset" (Cox crash)
Already fixed in cox_multivar_patch.py (auto-patch event from vital_status).
If it crashes again, check cox_multivar_adjusted.json — it should have
72 events (auto-patched from vital_status "Dead" values).

### Moran script hangs on GSE217237 samples
Scanpy's `sc.pp.normalize_total` on 29 slices × 3-5k spots each is memory-heavy.
If OOM, set `OMP_NUM_THREADS=2` before running.

### LOSO takes forever (CPU)
Normal. 35 folds × simplified training loop × 20-40 epochs. Expected 4-6 h CPU.
Run with `--max_folds 5` for a quick sanity check first.

## 7. PUBLICATION DECISION TREE (after LOSO AUC is known)

```
LOSO AUC >= 0.70?
├── YES → Submit CMPB v1.3. Report ALL honest numbers (Cox p>0.4, Moran Δ<0.02, LOSO AUC=X).
│         This is publishable because:
│         - Model novelty (HPV-anchored multi-loss ST representation learning) is intact
│         - Honest validation (Moran null model, LOSO AUC, random pathway) strengthens
│         - CMPB values rigorous validation over flashy numbers
│
├── 0.60-0.70 → Still submittable, but add "validation of HPV anchor was performed on
│                held-out ST slices (LOSO AUC = X). Lower values vs. self-test AUC (0.99)
│                reflect the challenge of cross-slice generalization across heterogeneous
│                cervical tissues. We acknowledge this limitation."
│
└── < 0.60 → CRITICAL RESTructure needed. HPV anchor was an artifact. Options:
             A) Reframe as generic ST representation learning + spatial biology discovery
                (not HPV-specific). Drop HPV AUC claim entirely.
             B) Add independent validation cohort (collaborate with GEO submitters).
             C) Target lower-tier journal (BMC Medical Imaging, PLOS Comp Biol).
```

## 8. VERSION TRACKING
All scripts use these HARD-CODED HPV gene sets — verify consistency before running:
- KEGG_HPV_INFECTION_GENES = 108 genes defined in scripts/train_st.py L55-73
- LAMBDA_RECON=0.2, LAMBDA_HPV=1.0, LAMBDA_NEIGH=0.3, LAMBDA_SUP=5.0, LAMBDA_PROG=1.5
  (used in moran/null_model/random_pathway for ablation-consistent comparison)

If train_st.py λ values changed, update the other 3 scripts too.

=============================================================================
END OF CHECKLIST
=============================================================================
