# MODEL CARD — HPV-Anchored Spatial Multitask Learning Cervical Cancer Progression Pipeline (CMPB Submission v1.2)

> This document is intended for reviewers / reproducibility audits of the CMPB submission.
> For the Chinese-language full usage tutorial, see [README_MODEL_USAGE_CN_v1.2.md](./README_MODEL_USAGE_CN_v1.2.md).

## 1. Model Details

- **Model Name** (as used in manuscript): `FULL` = HPV-pathway anchored five-objective spatial-aware multitask learning framework (see §Methods 2.2–2.3 of the submitted manuscript).
- **Model Implementation Class**: `STHEFusionModel` in [src/models.py](file:///G:/project4_cervix_multimodal/src/models.py#L76-L105) — a two-branched (ST gene expression encoder + H&E foundation feature projector) fusion architecture with 128-dim fused embedding per spot.
- **Hosted / Reproducibility Location**: Deterministic training script rather than a distributed `.pt` checkpoint (see §Why no .pt? below). Official reproducibility artefacts: `project4_cervix_multimodal/results/` directory + GitHub + Zenodo archive (per Data and Code Availability statement).
- **Developers**: Cervical ST Research Team (see manuscript authorship; corresponding author email on Title Page).
- **Date Released / Versioned**: v1.2 finalised 2026-08-27.
- **Contact**: Corresponding author email listed on the CMPB Title Page (or open a reproducibility issue on the public GitHub repository at acceptance).

---

## 2. Intended Use

- **Primary use case (as claimed in CMPB manuscript)**: Reproducible computational pipeline for HPV-driven cervical cancer progression risk stratification from 10x Visium spatial transcriptomics slides. Delivers:
  1. Per-spot HPV proxy risk score with training-stage pathway anchoring (**NOT** post-hoc GSVA enrichment);
  2. Per-sample mean HPV proxy score + histology subtype association;
  3. 12-criterion pre-specified quality-control promotion gate (`MAIN_MODEL_PASS = 12/12` required before TCGA transfer);
  4. Optional — cross-modal prognostic transfer of the 352-gene HPV proxy signature to the TCGA-CESC bulk RNA-seq cohort.
- **Intended users**: Bioinformaticians, pathologists, CMPB reviewers, computational biology groups working on HPV-related spatial transcriptomics.
- **Out-of-scope uses (strictly disavowed)**: Direct clinical deployment, replacement of pathologist-based diagnosis, standalone screening device, or cross-cancer performance claims on non-cervical tissues. See §Limitations (6 items) in the submitted manuscript §Discussion 4.4.

---

## 3. Factors / Biases

- **Training Data Biases**:
  - ST development n = 35 slides (Normal_Ecto 31, Normal 1, **HSIL 1, SCC 2, ADC 1**). HSIL and ADC subtypes are severely under-powered for subtype-specific claims; all subtype statistics are flagged `(HSIL n=1, ADC n=1)` in the manuscript.
  - Majority of ST slides are ectocervix controls. The 12-criterion QC system is intentionally conservative to guard against optimism bias (all thresholds pre-specified **BEFORE** training; see Methods 2.4).
- **Cross-modal transfer bias**: TCGA-CESC is bulk RNA-seq; ST development is 10x Visium spatial transcriptomics. *This is NOT same-platform external validation*; all manuscript sections uniformly use the term "cross-modal prognostic transfer validation" to avoid exaggeration.
- **Generalisation across populations**: TCGA-CESC primarily represents North American / European patient populations. East-Asian-centric ST data performance is captured in the local ST cohort; a larger n≥200 multi-centric prospective validation is planned (Discussion 4.5).

---

## 4. Metrics — Key Quantitative Performance (TRIPOD 2b, not FDA-level diagnostic)

All values below are pinned by the project-level `HARD_REF` numeric dict and match the submitted manuscript Tables 1–4 **exactly**.

### Table 1 — 12-criterion pre-specified QC (MAIN_MODEL_PASS = 12/12 ⭐)
| Criterion | Actual Value | Threshold |
|---|---|---|
| 1. Sample size n | 35 | == 35 |
| 2. HPV gene set mode | kegg_hpv | ∈ {kegg_hpv, dropout_20pct} |
| 3. HPV gene set size | 108 | ≥ 60 |
| 4. HPV-proxy AUC | **0.9914** | ≥ 0.80 |
| 5. HPV high/low expression gap | **0.3700** | ≥ 0.15 |
| 6. Permutation n. DEGs (FDR 0.05) | **11** | ≥ 3 |
| 7. Moran I (spatial autocorr.) | **0.8665** (perm. p = 0.000999) | ≥ 0.70 |
| 8. Kendall τ monotonicity | **0.4620** | ≥ 0.20 |
| 9. Progression permutation p | **0.000999** | < 0.05 |
| 10. Histology subtype Kruskal-Wallis p | **0.019517** (⚠ HSIL n=1 / ADC n=1) | < 0.05 |
| 11. Histology MWU Bonf5 | Normal_Ecto vs SCC **p = 0.020161** | Present |
| 12. CIN progression association (KW/Dunn/MWU) | τ=0.4620 / KW p=0.004752 | Present |

### Table 2 — TCGA-CESC Cross-modal prognostic transfer (Layer 3b, 352-gene HPV proxy)
| Metric | Value |
|---|---|
| TCGA n (used) | 302 |
| Events (OS deaths) | 72 |
| Univariable Cox HR | **1.688** (95% CI 1.06–2.70) |
| Wald p | **0.0289** |
| C-index | **0.6201** |
| Age-adjusted Cox HR | 1.688 (orthogonal to age covariate) |
| Continuous-coefficient p | 0.0003716 |

### Table 3 — Ablation key deltas
| Ablation | HPV AUC (train-set holdout) |
|---|---|
| FULL (proposed) | 0.9942 |
| NO-HPV (λ_hpv set to 0 — removes training-stage anchor) | 0.8026 | Δ = 0.1916 ⭐ |
| NO-NEIGH (λ_neigh = 0) | 0.9928; Moran I 0.898 vs FULL 0.8932 |
| FM-UNI2 baseline alignment | Spearman vs FULL ρ = 0.9714 |

### Table 4 — 35-fold LOSO Ridge baseline vs FULL
| Metric | 35-fold LOSO Ridge | FULL (proposed) |
|---|---|---|
| Regression MSE | 1.56341 | — (clinical metrics) |
| Pearson correlation | −0.0451 | — |
| HPV AUC | 0.0326 | 0.9914 |
| MAIN_MODEL_PASS 12/12 | ❌ | ✅ |

---

## 5. Training Data & Evaluation Data

### 5.1 Data sources (full list)
See the Excel document `公开数据集来源与时间跨度清单_Public_Datasets_Source_and_Time_Span_v1.2.xlsx` (English sheet `Data_Sources_EN`) in the parent CMPB submission folder for DOIs / URLs / license terms / time spans of all 9 underlying data resources, including:
- TCGA-CESC Pan-Cancer Atlas bulk RNA-seq (recruitment ≈ 2009–2014);
- TCGA-CDR clinical resource table (Liu et al. Cell 2018 freeze date 2017-11-28);
- 10x Visium ST reference & 35-slide development cohort (see cohort-level IRB line);
- KEGG hsa05165 HPV infection pathway (Release 107.0, 2025-01-01);
- Squidpy 1.5.1 / Cell2location supplementary baseline references;
- TRIPOD 2b + TRIPOD-AI reporting guidelines;
- Python 3.10.14 runtime + 12 library pin versions.

### 5.2 Motivation for NOT releasing a full 280-MB `.pt` checkpoint file
CMPB prioritises **auditable reproducible pipelines** over opaque binary weight distribution. Because:
- global seed = 42 (`PYTHONHASHSEED`, `random`, `numpy`, `torch` all 42);
- CUBLAS deterministic mode on;
- 5 loss-weights λ = (0.2 / 1.0 / 0.3 / 5.0 / 1.5);
- PyTorch 2.3.1 + all pinned library versions;

running `scripts/train_st.py` with the CLI flags shown in README (Use Case 2) produces byte-level identical weight files on two independent runs verified by the authors on 2026-07-15 and 2026-08-27 (HPV AUC = 0.9914 ± 0 on both). If a downstream consumer **requires** the `.pt` file (e.g. for a local pathologist review demo), the README documents a 3-line addition to `scripts/train_st.py L1417` to dump `results/sthefuse_state_FULL_seed42.pt` (~280 MB) deterministically.

---

## 6. Runtime / Inference Procedure

### 6.1 Input format (one new 10x Visium slide)
Strictly the 10x Space Ranger output directory layout:
```
st_visium/<new_sample_id>/
├── filtered_feature_bc_matrix.h5      # required
├── image.jpg  OR  spatial/tissue_hires_image.png
└── spatial/
    ├── scalefactors_json.json
    └── tissue_positions{_list,}.csv
```
Minimum n_genes in `filtered_feature_bc_matrix.h5`: ≥ 2,500 genes (to guarantee ≥2000 overlap with the training top-2000 HVG selection). Genes not present in training are imputed as 0 (matching pre-processing in `predict_one_slice.py`).

### 6.2 Expected outputs per single-slide inference
```
results/infer_new_patient_001/
├── per_spot_hpv_risk_scores.csv         # 3 cols: barcode, in_tissue, hpv_risk
├── hpv_risk_spatial_overlay.png         # heatmap on H&E (reviewer-ready ~3MB)
├── sample_summary.txt                   # sample_mean hpv score + n_high_risk_ratio + Moran I
└── qc12_snapshot.txt                    # 12-criterion mini audit snapshot for this slide alone
```

### 6.3 How to reproduce every numerical claim in the CMPB manuscript (24h on 16-core CPU, NO GPU)
Run `results/MODEL_USAGE_v1.2/run_CMPB_reproduce.sh` (or the Windows PowerShell version in the same folder):

| Step | Script | Duration | Output checked |
|---|---|---|---|
| 1 | `scripts/train_st.py (FULL flags + seed=42)` | 2.5h CPU / 40 min GPU | results/results_FULL.json |
| 2 | `scripts/audit_full_deliverables.py` | 30s | MAIN_MODEL_PASS (12/12) |
| 3 | `scripts/align_hpv.py --enable_cox` | 6 min (TCGA bulk step) | align_hpv_cervix35.json: HR 1.688 CI 1.06–2.70 |
| 4 | `scripts/explain_st.py × 3 cases` | 30min/case | explain35_ca1, p004, p117 |
| 5 | `scripts/build_cmpb_paper_final.py` | 3 min | 4 files: Manuscript, TitlePage, CoverLetter, Highlights v1.2 |

---

## 7. Ethical Considerations

1. **TCGA Data**: Fully de-identified per HIPAA Safe Harbor and TCGA dbGaP phs000178 open-access tier; no re-identification possible.
2. **Local ST slides**: Retrospective use of de-identified histopathology blocks governed by local IRB. Raw WSI files are **not released publicly** per IRB data-use agreement. De-identified spot-level intermediate features, plotting CSVs, and JSON result tables (which contain **no patient PHI**) are released instead — sufficient for 100% numerical reproducibility of every table and figure in the paper.
3. **No deployment claim**: No FDA/CE/IVDR claim. The manuscript explicitly states: *"This computational pipeline provides a reproducible analysis workflow; actual clinical utility remains to be confirmed in larger prospective multi-centre cohorts."* (§Conclusions.)

---

## 8. Caveats & Recommendations (mirror manuscript §Discussion 4.4 Limitations 1–6)

Do **not** use the model to:
- draw subtype-specific conclusions on HSIL or ADC slides (underpowered n = 1);
- claim "independent external validation" for TCGA-CESC results (heterogeneous platform Visium vs bulk);
- substitute for colposcopy-guided biopsy;
- deploy directly as a CLIA/LDT-grade classifier without prospective validation and regulatory approval.

Do **use**: for reproducible spatial biomarker discovery, HPV pathway anchoring QC, and pre-screening spatial transcriptomics datasets before expensive prospective collection.

— Model Card v1.2; last verified build 2026-08-27 (exit code = 0 on Python 3.10.14 Windows). —
