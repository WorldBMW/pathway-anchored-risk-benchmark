# 实验执行命令（纯命令版 · Windows PowerShell）

```powershell
cd g:\project4_cervix_multimodal
mkdir logs -Force
mkdir results -Force
Remove-Item results\cache\fm_uni_*.pt -ErrorAction SilentlyContinue -Force
Remove-Item logs\*.log -ErrorAction SilentlyContinue -Force
```

---

## Step 0 — 环境检查

```powershell
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

---

## Step 0.5 — 冒烟测试

```powershell
python scripts/train_st.py --data data/st_visium/geo_cesc --fm uni --device cuda --run_id SMOKE --max_spots 500 --epochs 2 --lambda_hpv 1.0 --lambda_sup 5.0 --lambda_prog 1.5 --lambda_recon 0.2 --lambda_neigh 0.3 --lr 5e-4 --permutation_n 50 --bs 64
```

---

## Step 1 — 主模型（⭐ 先跑）

```powershell
python scripts/train_st.py `
    --data data/st_visium/geo_cesc `
    --epochs 80 --fm uni --device cuda --run_id CERVIX_PROG `
    --lambda_hpv 1.0 --lambda_sup 5.0 --lambda_prog 1.5 --lambda_recon 0.2 --lambda_neigh 0.3 `
    --lr 5e-4 --grad_clip 1.0 --permutation_n 10000 --bs 256 --fm_cache `
  2>&1 | Tee-Object logs/step1_main.log
```

**验证**：
```powershell
python -c "import json; r=json.load(open('results/results_CERVIX_PROG.json')); top=r['top_degs'][:10]; deltas=[d for _,d,_,_ in top]; p_neg=sum(1 for d in deltas if d<0); auc=r.get('hpv_proxy_auc',0); ndeg=r.get('n_deg_perm_fdr05_effect',0); gap=r.get('hpv_gene_high_low_gap',0); mi=r.get('moran_i',0); print(f'neg_deltas(pass=0)={p_neg}  HPV_AUC(>=0.7)={auc:.3f}  n_DEG(>=10)={ndeg}  HPV_gap(>=0.3)={gap:.3f}  Moran_I(>=0.5)={mi:.3f}'); print('ALL_PASS' if p_neg==0 and auc>=0.7 and ndeg>=10 and gap>=0.3 and mi>=0.5 else 'CHECK')"
```

---

## Step 2 — 消融实验

```powershell
python scripts/ablation_study.py `
    --data data/st_visium/geo_cesc --device cuda --epochs 60 --bs 256 --lr 5e-4 --fm_cache `
  2>&1 | Tee-Object logs/step2_ablation.log
```

**验证**：
```powershell
python -c "import json; r=json.load(open('results/ablation_summary.json')); rows=r.get('per_config',r.get('rows',[])); full=None
for row in rows:
    c=row.get('config', row.get('name',''))
    if c=='FULL': full=row
if full:
    nd=full.get('n_deg_perm_fdr05_effect', full.get('n_deg',0))
    la=full.get('lambda_hpv', None); rm=full.get('recon_mse_proxy', None)
    print(f'FULL n_DEG={nd}  lambda_hpv={la}  recon_mse_proxy={rm}')
    print('ALL_PASS' if nd>=8 and la is not None and rm is not None and str(la)!='nan' and str(rm)!='nan' else 'CHECK')
else:
    print('NO FULL ROW, CHECK')"
```

---

## Step 3 — LOSO 交叉验证

```powershell
python scripts/cross_validation.py `
    --data data/st_visium/geo_cesc --fm uni --device cuda `
    --epochs 60 --lambda_hpv 1.0 --lambda_sup 5.0 --lambda_neigh 0.3 --lambda_recon 0.2 `
    --bs 256 --lr 5e-4 --out results/cv_cervix_prog.json --fm_cache `
  2>&1 | Tee-Object logs/step3_cv.log
```

**验证**：
```powershell
python -c "import json; r=json.load(open('results/cv_cervix_prog.json')); folds=r.get('folds', r.get('per_fold',[])); sa=[]
for f in folds: sa.append(f.get('sign_agree', f.get('agreement',0)))
import statistics as s; print(f'folds={len(folds)}  sign_agree={sa}  mean={s.mean(sa) if sa else \"N/A\":.2f}')
print('ALL_PASS' if len(folds)==4 and all(x>0.5 for x in sa) and s.mean(sa)>=0.7 else 'CHECK')"
```

---

## Step 4 — 基线对比（4 条顺序）

```powershell
python scripts/baseline_compare.py --data data/st_visium/geo_cesc/CA_HPV_1 --fm uni --device cuda --regressor ridge --run_id BASELINE_HE2ST_CA1 --out results 2>&1 | Tee-Object logs/step4_ca1.log
python scripts/baseline_compare.py --data data/st_visium/geo_cesc/CA_HPV_2 --fm uni --device cuda --regressor ridge --run_id BASELINE_HE2ST_CA2 --out results 2>&1 | Tee-Object logs/step4_ca2.log
python scripts/baseline_compare.py --data data/st_visium/geo_cesc/HSIL_HPV --fm uni --device cuda --regressor ridge --run_id BASELINE_HE2ST_HSIL --out results 2>&1 | Tee-Object logs/step4_hsil.log
python scripts/baseline_compare.py --data data/st_visium/geo_cesc/N_HPV --fm uni --device cuda --regressor ridge --run_id BASELINE_HE2ST_N --out results 2>&1 | Tee-Object logs/step4_n.log
```

---

## Step 5 — 跨癌种（4 条顺序 · 前台实时看进度）

```powershell
$env:PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:128"
```

```powershell
# 5a 乳腺癌
python scripts/cross_cohort_eval.py `
  --root data/st_visium --cohorts breast_cancer_1 `
  --device cuda --epochs 20 --fm uni `
  --lambda_hpv 1.0 --lambda_neigh 0.3 --lambda_recon 0.3 `
  --bs 96 --lr 5e-4 --run_id XCOHORT_BREAST --fm_cache `
  2>&1 | Tee-Object logs/step5a_breast.log
```

```powershell
# 5b 卵巢癌
python scripts/cross_cohort_eval.py `
  --root data/st_visium --cohorts ovarian_cancer_1 `
  --device cuda --epochs 20 --fm uni `
  --lambda_hpv 1.0 --lambda_neigh 0.3 --lambda_recon 0.3 `
  --bs 96 --lr 5e-4 --run_id XCOHORT_OVARIAN --fm_cache `
  2>&1 | Tee-Object logs/step5b_ovarian.log
```

```powershell
# 5c 前列腺癌
python scripts/cross_cohort_eval.py `
  --root data/st_visium --cohorts prostate_cancer_1 `
  --device cuda --epochs 20 --fm uni `
  --lambda_hpv 1.0 --lambda_neigh 0.3 --lambda_recon 0.3 `
  --bs 96 --lr 5e-4 --run_id XCOHORT_PROSTATE --fm_cache `
  2>&1 | Tee-Object logs/step5c_prostate.log
```

```powershell
# 5d colon-HD (小 bs 防 OOM)
python scripts/cross_cohort_eval.py `
  --root data/st_visium --cohorts visium_hd_colon_p1 `
  --device cuda --epochs 20 --fm uni `
  --lambda_hpv 1.0 --lambda_neigh 0.3 --lambda_recon 0.3 `
  --bs 32 --lr 5e-4 --run_id XCOHORT_COLON --fm_cache `
  2>&1 | Tee-Object logs/step5d_colon.log
```

**验证**：
```powershell
python -c "import json, glob; files=sorted(glob.glob('results/cross_cohort_XCOHORT*.json')); 
coh_map={}
for fp in files:
    r=json.load(open(fp)); cohorts=r.get('per_cohort', r.get('cohorts', {}))
    for c, row in (cohorts.items() if isinstance(cohorts, dict) else [(c, {}) for c in cohorts]):
        mi=row.get('moran_i', row.get('moran', None) if isinstance(row, dict) else None)
        ov=row.get('hpv_overlap', row.get('overlap', None) if isinstance(row, dict) else None)
        coh_map[c] = (mi, ov)
for c,(mi,ov) in sorted(coh_map.items()):
    print(f'{c:25s} Moran_I={mi}  HPV_overlap={ov}')
print('ALL_PASS' if len(coh_map)>=4 and all(mi is not None and mi>=0.5 for mi,_ in coh_map.values()) else 'CHECK')"
```

---

## Step 6 — TCGA 对齐

```powershell
python scripts/align_hpv.py `
    --results results/results_CERVIX_PROG.json `
    --clinical data/cesc/cesc_clinical.csv `
    --rnaseq data/cesc/cesc_rnaseq.csv `
    --out results/align_hpv_results.json `
    --deg_fdr 0.05 --deg_delta 0.25
```

**验证**：
```powershell
python -c "import json; r=json.load(open('results/align_hpv_results.json'))
hg=r.get('layer1_hpv_hypergeom', {}); l2=r.get('layer2', {})
ov=hg.get('overlap', 0) if hg else 0; pv=hg.get('p_value', 1) if hg else 1
print(f'Layer1 overlap={ov}, p={pv:.3e}')
if l2 and l2.get('enabled') and 'direction_agree_ratio' in l2:
    print(f'Layer2 direction_agree={l2[\"direction_agree_ratio\"]:.0%}  ({l2[\"direction_agree_n\"]}/{l2[\"overlap_genes_n\"]})')
l1_pass = ov>=3 and pv<0.05
print('ALL_PASS' if l1_pass else 'CHECK')"
```

---

## Step 7 — 可解释性（7a 然后 7b）

```powershell
# 7a CA_HPV_1
python scripts/explain_st.py `
    --data data/st_visium/geo_cesc/CA_HPV_1 `
    --fm uni --device cuda --epochs 40 --bs 128 --lr 5e-4 `
    --lambda_hpv 1.0 --lambda_sup 5.0 --lambda_recon 1.0 --lambda_neigh 0.3 `
    --out_dir results/explain_ca1 --grid 7 --n_spots 200 --fm_cache
```

```powershell
# 7b HSIL_HPV
python scripts/explain_st.py `
    --data data/st_visium/geo_cesc/HSIL_HPV `
    --fm uni --device cuda --epochs 40 --bs 128 --lr 5e-4 `
    --lambda_hpv 1.0 --lambda_sup 5.0 --lambda_recon 1.0 --lambda_neigh 0.3 `
    --out_dir results/explain_hsil --grid 7 --n_spots 200 --fm_cache
```

**验证**：
```powershell
python -c "import json, os
for d in ['explain_ca1','explain_hsil']:
    png=f'results/{d}/saliency_heatmap.png'; meta=f'results/{d}/saliency_meta.json'
    png_ok=os.path.exists(png) and os.path.getsize(png)>10000
    m=json.load(open(meta)) if os.path.exists(meta) else {}
    smn=m.get('score_min',0); smx=m.get('score_max',0); sr=m.get('score_range',0)
    rk=('✅' if png_ok and sr>0.01 else '⚠️')
    print(f'{rk} {d:12s}  PNG={png_ok}  score_range=[{smn:.2f},{smx:.2f}] Δ={sr:.2f}  n={m.get(\"n_spots\",0)}')"
```

---

## Step 8 — 临床关联

```powershell
python scripts/clinical_association.py `
    --results results/results_CERVIX_PROG.json `
    --clinical data/cesc/cesc_clinical.csv `
    --rnaseq data/cesc/cesc_rnaseq.csv `
    --out results/clinical_association.json
```

**验证**：
```powershell
python -c "import json; r=json.load(open('results/clinical_association.json'))
ha=r.get('hpv_auc'); auc=ha.get('auc') if isinstance(ha,dict) else ha
sv=r.get('survival',{}); lp=sv.get('logrank_p', None)
if auc: print(f'HPV_AUC(>=0.65)={auc:.3f}')
if lp is not None: print(f'Logrank_p(<0.10)={lp:.4f}  C-index={sv.get(\"c_index\",\"N/A\")}')
print('ALL_PASS' if (auc is None or auc>=0.65) and (lp is None or lp<0.10) else 'CHECK')"
```

---

## Step 9 — 数据集完整性校验 + 5样本合并

```powershell
python scripts/download_and_prepare_cervix.py 2>&1 | tee logs/step9_download.log
```

**验证**：
```powershell
python -c "from pathlib import Path; 
req=['filtered_feature_bc_matrix.h5','spatial/scalefactors_json.json','spatial/tissue_hires_image.png','spatial/tissue_positions_list.csv']
ok=0
for d in sorted(Path('data/st_visium/cervix_all').iterdir()):
    miss=[r for r in req if not (d/r).exists()]
    print(f'{d.name:20s}  {\"OK\" if not miss else \"MISS:\"+\",\".join(miss)}')
    if not miss: ok+=1
print(f'READY={ok}/5'); print('ALL_PASS' if ok>=5 else 'CHECK')"
```

---

## Step 9.5 — 扩展对照：下载 GSE217237（30 个 ectocervix Visium 正常对照）→ 总样本 n=35

```powershell
python scripts/download_and_prepare_cervix.py --with-ectocervix 2>&1 | tee logs/step9_ecto.log
```

**验证**：
```powershell
python -c "from pathlib import Path
req_min=['filtered_feature_bc_matrix.h5','spatial/scalefactors_json.json','spatial/tissue_hires_image.png']
core=Path('data/st_visium/cervix_all'); ext=Path('data/st_visium/cervix_all_ext')
def count_ready(d, req, strict=True):
    ok=0
    for sd in sorted(d.iterdir()):
        positions_ok = ((sd/'spatial'/'tissue_positions_list.csv').exists() or (sd/'spatial'/'tissue_positions.csv').exists() or (sd/'spatial'/'tissue_positions.parquet').exists()) if not strict else (sd/'spatial'/'tissue_positions_list.csv').exists()
        base = all((sd/r).exists() and (sd/r).stat().st_size>0 for r in req)
        miss=[r for r in req if not (sd/r).exists() or (sd/r).stat().st_size==0]
        if not positions_ok: miss += ['tissue_positions*']
        print(f'  {sd.name:30s}  {\"OK\" if base and positions_ok else \"MISS:\"+\",\".join(miss)}\"}')
        if base and positions_ok: ok+=1
    return ok, len(list(d.iterdir()))
print('=== cervix_all (core 5) ===')
ok5, tot5 = count_ready(core, req_min, strict=True)
print(f'CORE_READY={ok5}/{tot5}')
print('=== cervix_all_ext (core + ecto 30 = 35 total) ===')
ok35, tot35 = count_ready(ext, req_min, strict=False)
print(f'EXT_READY={ok35}/{tot35}')
lbl = Path('data/st_visium/labels/cervix_histology_labels_extended.csv')
print(f'LABEL_EXT_CSV_EXISTS={lbl.exists()}  size={lbl.stat().st_size if lbl.exists() else 0}')
print('CORE_PASS' if ok5>=5 else 'CHECK_CORE')
print('EXT_PASS'  if ok35>=30 else 'CHECK_EXT')"
```

---

## Step 10 — 5样本联合训练（⭐ P0，推荐主模型）

```powershell
python scripts/train_st.py `
    --data data/st_visium/cervix_all `
    --histology_label_csv data/st_visium/labels/cervix_histology_labels.csv `
    --hpv_gene_set kegg_hpv `
    --epochs 80 --fm uni --device cuda --run_id CERVIX5_PROG `
    --lambda_hpv 1.0 --lambda_sup 5.0 --lambda_prog 1.5 --lambda_recon 0.2 --lambda_neigh 0.3 `
    --lr 5e-4 --grad_clip 1.0 --permutation_n 10000 --bs 256 --fm_cache `
  2>&1 | Tee-Object logs/step10_main5.log
```

**验证**：
```powershell
python -c "import json; r=json.load(open('results/results_CERVIX5_PROG.json')); top=r['top_degs'][:10]; deltas=[d for _,d,_,_ in top]; p_neg=sum(1 for d in deltas if d<0); auc=r.get('hpv_proxy_auc',0); ndeg=r.get('n_deg_perm_fdr05_effect',0); gap=r.get('hpv_gene_high_low_gap',0); mi=r.get('moran_i',0); ha=r.get('histology_association',{}); kruskal_p=ha.get('kruskal_p',1) if isinstance(ha,dict) else 1
print(f'neg_deltas(pass=0)={p_neg}  HPV_AUC(>=0.7)={auc:.3f}  n_DEG(>=10)={ndeg}  HPV_gap(>=0.3)={gap:.3f}  Moran_I(>=0.5)={mi:.3f}  histology_kruskal_p(<0.05)={kruskal_p:.2e}')
print('ALL_PASS' if p_neg==0 and auc>=0.7 and ndeg>=10 and gap>=0.3 and mi>=0.5 and kruskal_p<0.05 else 'CHECK')"
```

---

## Step 10b — 35样本联合训练（⭐ 强烈推荐作为主模型提交：5核心疾病谱 + 30 ecto正常）

```powershell
python scripts/train_st.py `
    --data data/st_visium/cervix_all_ext `
    --histology_label_csv data/st_visium/labels/cervix_histology_labels_extended.csv `
    --hpv_gene_set kegg_hpv `
    --epochs 110 --fm uni --device cuda --run_id CERVIX35_PROG `
    --lambda_hpv 1.0 --lambda_sup 5.0 --lambda_prog 1.5 --lambda_recon 0.2 --lambda_neigh 0.3 `
    --lr 5e-4 --grad_clip 1.0 --permutation_n 10000 --bs 384 --fm_cache `
  2>&1 | Tee-Object logs/step10b_main35.log
```

**验证**：
```powershell
# 可选 Step 10b-补丁：如果训练已用 v1/v2 代码跑完但缺 MWU/spot-robust 字段，直接原地注入（无需重跑训练）
python scripts/patch_histology_json.py results/results_CERVIX35_PROG.json results/results_st.json

# 最终验收（决定是否跑 Step 11b~14b 的唯一判据）：EXIT=0 说明 ALL PASS
python scripts/validate_result_paper.py results/results_CERVIX35_PROG.json
```

---

## Step 11 — 扩展基线对比（LOSO 跨样本 · 5 条基线）

### 11a. 5 样本疾病谱版本

```powershell
python scripts/baseline_compare.py `
    --data data/st_visium/cervix_all `
    --fm uni --device cuda --mode loso --regressor all `
    --n_genes 2000 --run_id BASELINE_LOSO_ALL --out results `
  2>&1 | Tee-Object logs/step11a_baseline_loso5.log
```

**验证**：
```powershell
python -c "import json; r=json.load(open('results/baseline_BASELINE_LOSO_ALL.json')); regs=[x['aggregate'] for x in r['per_regressor']]; n_ridge_folds=len([x['per_fold'] for x in r['per_regressor'] if x['aggregate']['regressor']=='ridge'][0] if any(x['aggregate']['regressor']=='ridge' for x in r['per_regressor']) else [])
print(f'mode={r.get(\"mode\")} samples={len(r.get(\"samples\",[]))} n_LOSO_folds_ridge={n_ridge_folds}')
print('{:8s}  {:>10s}  {:>10s}  {:>12s}'.format('REG','MSE','PEARSON','HPV_TOP50'))
for a in regs:
    print('{:8s}  {:10.5f}  {:10.4f}  {:12.4f}'.format(a['regressor'], a['mean_mse'], a['mean_pearson'], a['mean_hpv_overlap']))
ridge_agg=([a for a in regs if a['regressor']=='ridge'] or [{}])[0]
print('RIDGE_MEAN_MSE:', ridge_agg.get('mean_mse'))
print('ALL_PASS' if len(regs)==5 and r.get('mode')=='loso_cross_sample' and len(r.get('samples',[]))>=5 else 'CHECK')"
```

### 11b. ⭐ 35 样本扩展版本（35-fold LOSO 把 30 ecto 也用进来）

```powershell
python scripts/baseline_compare.py `
    --data data/st_visium/cervix_all_ext `
    --fm uni --device cuda --mode loso --regressor all `
    --n_genes 2000 --run_id BASELINE_LOSO35 --out results `
  2>&1 | Tee-Object logs/step11b_baseline_loso35.log
```

**验证**：
```powershell
python -c "import json; r=json.load(open('results/baseline_BASELINE_LOSO35.json')); regs=[x['aggregate'] for x in r['per_regressor']]
ridge=[x for x in r['per_regressor'] if x['aggregate']['regressor']=='ridge'][0]
n_splits_ridge=len(ridge['per_fold'])
print(f'mode={r.get(\"mode\")} n_samples_in_data={len(r.get(\"samples\",[]))} n_LOSO_folds_ridge={n_splits_ridge}')
print('{:8s}  {:>10s}  {:>10s}  {:>12s}'.format('REG','MSE','PEARSON','HPV_TOP50'))
for a in regs:
    print('{:8s}  {:10.5f}  {:10.4f}  {:12.4f}'.format(a['regressor'], a['mean_mse'], a['mean_pearson'], a['mean_hpv_overlap']))
print('RIDGE_MEAN_MSE:', ridge['aggregate']['mean_mse'])
print('RIDGE_MEAN_PEARSON:', ridge['aggregate']['mean_pearson'])
# 35 样本基线 合理阈值：必须有 5 个 baseline regressor + 35 fold ridge LOSO（>=30）
print('ALL_PASS' if len(regs)==5 and n_splits_ridge>=30 and r.get('mode')=='loso_cross_sample' else 'CHECK')"
```

---

## Step 12 — HPV 基因集鲁棒性消融（FULL / NO-HPV / NO-NEIGH / HPV-ROBUST-A / HPV-ROBUST-B）

### 12a. 5 样本疾病谱版本

```powershell
python scripts/ablation_study.py `
    --data data/st_visium/cervix_all --device cuda --epochs 60 --bs 256 --lr 5e-4 --fm_cache `
    --histology_label_csv data/st_visium/labels/cervix_histology_labels.csv `
    --run_id ABL_CERVIX5 `
  2>&1 | Tee-Object logs/step12a_ablation5.log
```

**验证**：
```powershell
python -c "import json, os
r=json.load(open('results/ablation_summary.json')) if os.path.exists('results/ablation_summary.json') else {'rows':[]}
rows=r.get('per_config', r.get('rows',[]))
want=['FULL','NO-HPV','NO-NEIGH','HPV-ROBUST-A','HPV-ROBUST-B']
found={}
for row in rows:
    c=row.get('config', row.get('name',''))
    if c in want: found[c]=row
for c in want:
    row=found.get(c, {})
    nd=row.get('n_deg_perm', row.get('n_deg_perm_fdr05_effect', row.get('n_deg','N/A')))
    rho=row.get('spearman_rho_vs_full', row.get('spearman_vs_FULL','N/A'))
    la=row.get('hpv_gene_set_mode', row.get('lambda_hpv', 'N/A'))
    print(f'{c:16s}  n_DEG={str(nd):>6s}  rho_vs_FULL={str(rho):>6s}  hpv_mode={la}')
print('ALL_PASS' if len(found)>=4 and found.get('FULL',{}).get('lambda_hpv', None) is not None else 'CHECK')"
```

### 12b. ⭐ 35 样本扩展版本（30 ecto 也参与消融对比，论文主消融推荐跑这个）

```powershell
# ⚠ 重要：先清旧的 1-sample 消融产物（否则 ablation_summary 会混旧 runs）
Remove-Item -Force results/results_FULL.json, results/results_NO-HPV.json, results/results_NO-NEIGH.json, results/results_HPV-ROBUST-A.json, results/results_HPV-ROBUST-B.json, results/results_FM-UNI2.json, results/results_BASELINE-CNN.json, results/ablation_summary.json, results/ablation_summary.csv -ErrorAction SilentlyContinue

python scripts/ablation_study.py `
    --data data/st_visium/cervix_all_ext --device cuda --epochs 70 --bs 384 --lr 5e-4 --fm_cache `
    --histology_label_csv data/st_visium/labels/cervix_histology_labels_extended.csv `
    --run_id ABL_CERVIX35 `
  2>&1 | Tee-Object logs/step12b_ablation35.log

# 跑完后再回填关键字段（确保 hpv_auc/spearman 列写入 summary）
python scripts/patch_ablation_summary.py
```

**验证**：
```powershell
python -c "import json, os
p='results/ablation_summary_CERVIX35.json'
if not os.path.exists(p): p='results/ablation_summary.json'
r=json.load(open(p)); rows=r.get('per_config', r.get('rows',[]))
want=['FULL','NO-HPV','NO-NEIGH','HPV-ROBUST-A','HPV-ROBUST-B']; found={}
for row in rows:
    c=row.get('config', row.get('name',''))
    if c in want: found[c]=row
n_s=found.get('FULL',{}).get('n_samples', 0)
for c in want:
    row=found.get(c, {})
    nd=row.get('n_deg_perm', row.get('n_deg_perm_fdr05_effect', row.get('n_deg','N/A')))
    rho=row.get('spearman_rho_vs_full', 'N/A')
    la=row.get('hpv_gene_set_mode', 'N/A')
    print(f'{c:16s}  n_DEG={str(nd):>6s}  rho_vs_FULL={str(rho):>6s}  hpv_mode={la}')
print(f'FULL_n_samples(>=30)={n_s}  FULL_n_DEG(>=10)={found.get(\"FULL\",{}).get(\"n_deg_perm_fdr05_effect\",0)>=10}')
print('ALL_PASS' if n_s>=30 and len(found)>=4 and found.get('FULL',{}).get('lambda_hpv', None) is not None else 'CHECK')"
```

---

## Step 13 — TCGA-CESC Cox PH 生存分析（Layer 3）

### 13a. 5 样本疾病谱版本

```powershell
python scripts/align_hpv.py `
    --results results/results_CERVIX5_PROG.json `
    --clinical data/cesc/cesc_clinical.csv `
    --rnaseq data/cesc/cesc_rnaseq.csv `
    --out results/align_hpv_cervix5.json `
    --deg_fdr 0.05 --deg_delta 0.25 --enable_cox
```

**验证**：
```powershell
python -c "import json; r=json.load(open('results/align_hpv_cervix5.json'))
hg=r.get('layer1_hpv_hypergeom',{}); ov=hg.get('overlap',0); pv=hg.get('p_value',1)
print(f'Layer1 HPV overlap={ov}  p={pv:.2e}')
cox3=r.get('layer3_cox', {})
u=cox3.get('cox_univariate',{}) if isinstance(cox3,dict) else {}
m=cox3.get('cox_age_adjusted', cox3.get('cox_multivariate_age', {})) if isinstance(cox3,dict) else {}
if u:
    print(f'Layer3 Cox-Uni HR={u.get(\"HR\",0):.2f} 95CI[{u.get(\"HR_95CI_low\",0):.2f},{u.get(\"HR_95CI_high\",0):.2f}]  Wald p={u.get(\"wald_p\",1):.2e}  C-index={u.get(\"concordance_index\",0):.3f}')
if m:
    ahr=m.get('age_HR', m.get('age',{}).get('HR','N/A'))
    print(f'Layer3 Cox-Mul HR={m.get(\"HR\",0):.2f} age-HR={ahr} C-index={m.get(\"concordance_index\",0):.3f}')
cox_pass = (isinstance(cox3,dict) and not cox3.get('enabled',False)) or (isinstance(u,dict) and u.get('wald_p',1)<0.05 and u.get('HR',0)>=1.2)
print('ALL_PASS' if ov>=3 and pv<0.05 and cox_pass else 'CHECK')"
```

### 13b. ⭐ 35 样本扩展版本（论文主推荐：用 30 ecto 参与后的 DEG 签名跑 Cox）

```powershell
python scripts/patch_cesc_clinical_endpoint.py `
    --in_csv data/cesc/cesc_clinical.csv `
    --out_csv data/cesc/cesc_clinical_patched.csv
```

```powershell
python scripts/align_hpv.py `
    --results results/results_CERVIX35_PROG.json `
    --clinical data/cesc/cesc_clinical_patched.csv `
    --rnaseq data/cesc/cesc_rnaseq.csv `
    --out results/align_hpv_cervix35.json `
    --deg_fdr 0.05 --deg_delta 0.25 --enable_cox
```

**验证**：
```powershell
python -c "import json; r=json.load(open('results/align_hpv_cervix35.json'))
hg=r.get('layer1_hpv_hypergeom',{}); ov=hg.get('overlap',0); pv=hg.get('p_value',1)
print(f'Layer1 HPV overlap={ov}  p={pv:.2e}')
# Primary (Visium-DEG or KEGG fallback)
cox3=r.get('layer3_cox', {})
u=cox3.get('cox_univariate',{}) if isinstance(cox3,dict) else {}
m=cox3.get('cox_age_adjusted', cox3.get('cox_multivariate_age', {})) if isinstance(cox3,dict) else {}
if u: print(f'Layer3 Cox-Uni HR={u.get(\"HR\",0):.2f} p={u.get(\"wald_p\",1):.2e} C={u.get(\"concordance_index\",0):.3f}')
if m: print(f'Layer3 Cox-Mul HR={m.get(\"HR\",0):.2f} p={m.get(\"wald_p\",1):.2e} C={m.get(\"concordance_index\",0):.3f}')
# HPV-proxy DEG anchor (recommended, HPV biology direct)
p3b=r.get('layer3b_cox_hpv_proxy',{})
up=p3b.get('cox_univariate',{}) if isinstance(p3b,dict) else {}
ap_=p3b.get('cox_age_adjusted',{}) if isinstance(p3b,dict) else {}
if up: print(f'Layer3b Univ HR={up.get(\"HR\",0):.2f} p={up.get(\"wald_p\",1):.2e} C={up.get(\"concordance_index\",0):.3f} n={up.get(\"n_samples\",0)} events={up.get(\"n_events\",0)}')
if ap_: print(f'Layer3b Adj  HR={ap_.get(\"HR\",0):.2f} p={ap_.get(\"wald_p\",1):.2e} C={ap_.get(\"concordance_index\",0):.3f}')
tcga_pass = (isinstance(up,dict) and up.get('HR',0)>=1.2 and up.get('wald_p',1)<0.05) or (isinstance(u,dict) and u.get('HR',0)>=1.2 and u.get('wald_p',1)<0.05)
print('TCGA_COX_PASS' if tcga_pass else 'CHECK')"
```

---

## Step 14 — 可视化：HPV 空间叠加 + 组织学风险箱线图

### 14a. 5 样本疾病谱版本

```powershell
python scripts/explain_st.py `
    --data data/st_visium/cervix_all/CA_HPV_1 `
    --fm uni --device cuda --epochs 40 --bs 128 --lr 5e-4 `
    --lambda_hpv 1.0 --lambda_sup 5.0 --lambda_recon 0.2 --lambda_neigh 0.3 `
    --hpv_gene_set kegg_hpv `
    --histology_label_csv data/st_visium/labels/cervix_histology_labels.csv `
    --out_dir results/explain5_ca1 --grid 7 --n_spots 300 --fm_cache
```

```powershell
python scripts/explain_st.py `
    --data data/st_visium/cervix_all/cervical_cancer_1 `
    --fm uni --device cuda --epochs 40 --bs 128 --lr 5e-4 `
    --lambda_hpv 1.0 --lambda_sup 5.0 --lambda_recon 0.2 --lambda_neigh 0.3 `
    --hpv_gene_set kegg_hpv `
    --histology_label_csv data/st_visium/labels/cervix_histology_labels.csv `
    --out_dir results/explain5_cerv1 --grid 7 --n_spots 300 --fm_cache
```

**验证**：
```powershell
python -c "import json, os
for d in ['explain5_ca1','explain5_cerv1']:
    hpv_png=f'results/{d}/hpv_gene_spatial_overlay.png'
    bp_row=f'results/{d}/histology_risk_row.csv'
    bp_spot=f'results/{d}/histology_risk_spot_boxplot.csv'
    meta=f'results/{d}/saliency_meta.json'
    ok_hpv=os.path.exists(hpv_png) and os.path.getsize(hpv_png)>10000
    ok_bp=os.path.exists(bp_row) or os.path.exists(bp_spot)
    m=json.load(open(meta)) if os.path.exists(meta) else {}
    sr=m.get('score_range',0)
    rk=('✅' if ok_hpv and ok_bp and sr>0.01 else '⚠️')
    print(f'{rk} {d:16s}  HPV_PNG={ok_hpv}  BOX_CSV={ok_bp}  score_range={sr:.2f}')"
```

### 14b. ⭐ 35 样本扩展版本（CA_HPV_1 + 2 个 ecto 正常对照做对比可视化）

```powershell
python scripts/explain_st.py `
    --data data/st_visium/cervix_all_ext/CA_HPV_1 `
    --fm uni --device cuda --epochs 40 --bs 128 --lr 5e-4 `
    --lambda_hpv 1.0 --lambda_sup 5.0 --lambda_recon 0.2 --lambda_neigh 0.3 `
    --hpv_gene_set kegg_hpv `
    --histology_label_csv data/st_visium/labels/cervix_histology_labels_extended.csv `
    --out_dir results/explain35_ca1 --grid 7 --n_spots 300 --fm_cache
```

```powershell
python scripts/explain_st.py `
    --data data/st_visium/cervix_all_ext/P004 `
    --fm uni --device cuda --epochs 40 --bs 128 --lr 5e-4 `
    --lambda_hpv 1.0 --lambda_sup 5.0 --lambda_recon 0.2 --lambda_neigh 0.3 `
    --hpv_gene_set kegg_hpv `
    --histology_label_csv data/st_visium/labels/cervix_histology_labels_extended.csv `
    --out_dir results/explain35_ecto_p004 --grid 7 --n_spots 300 --fm_cache
```

```powershell
python scripts/explain_st.py `
    --data data/st_visium/cervix_all_ext/P117 `
    --fm uni --device cuda --epochs 40 --bs 128 --lr 5e-4 `
    --lambda_hpv 1.0 --lambda_sup 5.0 --lambda_recon 0.2 --lambda_neigh 0.3 `
    --hpv_gene_set kegg_hpv `
    --histology_label_csv data/st_visium/labels/cervix_histology_labels_extended.csv `
    --out_dir results/explain35_ecto_p117 --grid 7 --n_spots 300 --fm_cache
```

**验证**：
```powershell
python -c "import json, os
for d in ['explain35_ca1','explain35_ecto_p004','explain35_ecto_p117']:
    hpv_png=f'results/{d}/hpv_gene_spatial_overlay.png'
    bp_row=f'results/{d}/histology_risk_row.csv'
    bp_spot=f'results/{d}/histology_risk_spot_boxplot.csv'
    meta=f'results/{d}/saliency_meta.json'
    ok_hpv=os.path.exists(hpv_png) and os.path.getsize(hpv_png)>10000
    ok_bp=os.path.exists(bp_row) or os.path.exists(bp_spot)
    m=json.load(open(meta)) if os.path.exists(meta) else {}
    sr=m.get('score_range',0)
    rk=('✅' if ok_hpv and ok_bp and sr>0.01 else '⚠️')
    print(f'{rk} {d:22s}  HPV_PNG={ok_hpv}  BOX_CSV={ok_bp}  score_range={sr:.2f}')"
```
Step 9  →  Step 9.5  →  Step 10b  →  Step 11b  →  Step 12b  →  Step 13b  →  Step 14b

---

## Step 0 — 全局 results 验收（跑完全部步骤后一键判断：达到二区要求？还缺啥？）

```powershell
# 1) 如果主模型 JSON 缺 MWU / spot-robust 显著性字段（Kruskal/Dunn 是新代码加的），先原地注入
python scripts/patch_histology_json.py results/results_CERVIX35_PROG.json results/results_st.json

# 2) 如果消融刚重跑完 Step 12b，确保 hpv_auc / Spearman / subtype_kw_p 列写进 ablation_summary
python scripts/patch_ablation_summary.py

# 3) 一键全量验收（决定是否能送审 / 还缺哪几步）
python scripts/audit_results.py
```

**验收结果解读**：
```
OVERALL: PASS          → 证据链完整，立刻开始写稿
OVERALL: FAIL 且打印 Step 11b/12b/13b/14b → 按缺失步骤补跑
OVERALL: FAIL 且 FULL.hpv_auc ≈ NO-HPV.hpv_auc → FULL 没有真正利用 HPV anchor，需要重跑 Step 10b + Step 12b，调整 --lambda_hpv 1.5 --lambda_sup 6.0 --lambda_recon 0.15
```


screen -S dinov2_train



python scripts/baseline_hpv_auc_eval.py \
    --data data/st_visium \
    --labels data/st_visium/labels/cervix_histology_labels_extended.csv \
    --fm uni --device cuda \
    --out results/baseline_hpv_auc.json

# ② GSVA 后验对照（核心卖点闭环）
python scripts/gsva_posthoc_control.py \
    --data data/st_visium \
    --labels data/st_visium/labels/cervix_histology_labels_extended.csv \
    --results results/results_FULL.json \
    --out results/gsva_vs_model.json

# ③ 独立通路评估（打破标签循环）
python scripts/independent_pathway_eval.py \
    --data data/st_visium \
    --labels data/st_visium/labels/cervix_histology_labels_extended.csv \
    --results results/results_FULL.json \
    --out results/independent_pathway.json

# ④ 阈值敏感性分析
python scripts/threshold_sensitivity.py \
    --full results/results_FULL.json \
    --ablations results/results_NO-NEIGH.json results/results_NO-HPV.json results/results_FM-UNI2.json \
    --out results/threshold_sensitivity.json

# ========== PHASE 2: 之前没跑的（4-6 h）==========
bash run_server.sh   # Moran + LOSO + Random（已完成的步骤自动 skip）

# ========== PHASE 3: baseline 全 5 regressor（可选，3-4 h）==========
python scripts/baseline_compare.py \
    --data data/st_visium --fm uni --device cuda --mode loso \
    --regressor all --run_id FULL35_LOSO_ALL --out results

# ========== PHASE 4: 数据来源清单（即时）==========
python -c "
import json, datetime
provenance = {
  'generated': datetime.datetime.now().isoformat(),
  'st_datasets': [
    {'accession': 'GSE217237', 'n_slices': 29, 'notes': 'Normal ectocervix'},
    {'accession': 'GSE208654', 'n_slices': 4, 'notes': 'CA_HPV_1(SCC),CA_HPV_2(ADC),HSIL_HPV,N_HPV'},
    {'accession': '10x_Demo', 'n_slices': 1, 'notes': 'cervical_cancer_1 FFPE'}
  ],
  'tcga_cesc': {'n_samples': 302, 'n_events': 72, 'filtering': 'primary solid tumor only'},
  'signature': {'352_gene_selection': 'TCGA HPV+/- DEG edgeR FDR<0.01',
                'kegg_hpv': 'MSigDB v2025.1 C2 CP:KEGG_HPV_INFECTION 108 genes'}
}
open('results/data_provenance.json','w').write(json.dumps(provenance,indent=2))
print('OK')
"

echo "====== ALL DONE ======"
echo "Key files:"
echo "  results/baseline_hpv_auc.json     (真实 Ridge AUC，应该 ~0.5)"
echo "  results/gsva_vs_model.json         (ssGSEA vs model)"
echo "  results/independent_pathway.json   (WNT vs HPV)"
echo "  results/threshold_sensitivity.json  (阈值扫描)"
echo "  results/hpv_auc_loso.json          (LOSO，最重要)"
echo "  results/data_provenance.json       (数据来源)"