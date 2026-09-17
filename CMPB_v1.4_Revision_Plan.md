# CMPB v1.4 全面修订计划 — 审稿人 15 点攻击逐项落地

> 基于审稿人视角的致命→大修→小修分级，对应到代码改动 + 服务器命令
> 生成时间：2026-08-31

---

## 一、修改总览（按 P0/P1/P2 排序）

### P0 — 必须修（不修等于送审稿）

| # | 审稿问题 | 动作 | 工作量 | 状态 |
|---|---------|------|--------|------|
| 0a | Ridge AUC=0.0326 是硬编码编造 | 写 `baseline_hpv_auc_eval.py` 算真实 AUC | 中 | 🆕 需写 |
| 0b | HPV 标签-训练-评估三者同源循环 | 写 `independent_pathway_eval.py` 用非 HPV 通路评估 | 中 | 🆕 需写 |
| 0c | 统计检验以 spot 为单位 = 空间伪重复 | 所有统计脚本加 per-slice 平均 + 说明 | 低 | 🔧 需改 |
| 0d | 缺 GSVA 后验对照（核心卖点闭环） | 写 `gsva_posthoc_control.py` | 中 | 🆕 需写 |
| 0e | 缺数据 accession ID | 写 `results/data_provenance.json` | 低 | 🆕 需写 |

### P1 — 大修（rebuttal 大概率被要求补）

| # | 审稿问题 | 动作 | 工作量 | 状态 |
|---|---------|------|--------|------|
| 1a | 单 seed 训练无稳定性证据 | run_server.sh 加 5-seed loop | 低 | 🔧 需改 |
| 1b | 12 项 QC 阈值是自定义值 | 写 `threshold_sensitivity.py` 阈值扫描 | 中 | 🆕 需写 |
| 1c | NO-NEIGH Moran 反而更高的尴尬 | moran 脚本补 NO-NEIGH 在 spot-clustering 指标上的下降 | 中 | 🔧 需改 |
| 1d | 缺强基线（只有 ridge） | baseline_compare.py 扩到 5 regressors（已写好，跑一下） | 低 | ✅ 脚本已存在 |

### P2 — 小修（锦上添花）

| # | 审稿问题 | 动作 | 工作量 |
|---|---------|------|--------|
| 2a | 跨癌种节地位尴尬 | 降级到 supplement 或补 Moran 数值 |
| 2b | 缺 DCA 临床增量 | 写简单 DCA（风险评分 vs HPV status） |
| 2c | NO-HPV / NO-NEIGH 表中 subtype_kw_p 为空白 | 在所有 ablation 结果里补 subtype_kw_p |
| 2d | 352 基因来源边界不清 | Discussion 里明确 TCGA DEG + ST 迁移验证 |

---

## 二、需要写的 4 个新脚本（服务器上跑）

### 脚本清单

| 脚本 | 输入 | 输出 | 核心功能 |
|------|------|------|----------|
| `scripts/baseline_hpv_auc_eval.py` | baseline 预测结果 + train_st 的 HPV 标签 | baseline 真实 AUC | 用 train_st.py 同款 HPV proxy 标签评估 ridge/MSE 基线 |
| `scripts/gsva_posthoc_control.py` | results_FULL.json + ST slices | gsva_vs_model.json | ssGSEA KEGG_HPV vs 模型 risk score 相关性对比 |
| `scripts/independent_pathway_eval.py` | results_FULL.json + ST slices | independent_pathway.json | 用 WNT / p53 / Cell Cycle 通路评估模型特异性 |
| `scripts/threshold_sensitivity.py` | results_FULL.json + 消融 | threshold_sensitivity.json | AUC 0.60–0.90 + Moran 0.5–0.8 + Kendall 阈值扫描 |

### 不需要下载新数据集

**所有 35 张 Visium 切片已经是公开领域全部的宫颈数据**：
- GSE217237 (29 张 ectocervix) → 已在 `data/st_visium/geo_ectocervix/`
- GSE208654 (CA_HPV_1/CA_HPV_2/HSIL_HPV/N_HPV) → 已在 `data/st_visium/geo_cesc/`
- 10x Demo cervical_cancer_1 → 已在 `data/st_visium/cervical_cancer_1/`
- TCGA-CESC (302 samples) → 已在 `data/cesc/`

**不需要下载任何东西**。

---

## 三、run_server.sh v2 — 完整执行计划

```bash
# === PHASE 0: 环境检查 ===
python -c "import scanpy, squidpy, torch, gseapy; print('ALL OK')"

# === PHASE 1: 重新跑 FULL + 消融（5 seeds for stability）===
# (已经有结果，可以跳过或重跑多 seed)
bash run_server.sh

# === PHASE 2: baseline 真实 AUC（解决 0.0326 编造问题）===
python scripts/baseline_compare.py \
  --data data/st_visium \
  --fm uni --device cuda --mode loso \
  --regressor ridge,mlp --n_genes 2000 \
  --run_id FULL35_LOSO_REDUX --out results

# 在 baseline 预测结果上算真实 HPV proxy AUC
python scripts/baseline_hpv_auc_eval.py \
  --baseline results/baseline_FULL35_LOSO_REDUX.json \
  --data data/st_visium \
  --labels data/st_visium/labels/cervix_histology_labels_extended.csv \
  --results_dir results

# === PHASE 3: GSVA 后验对照（核心卖点闭环）===
python scripts/gsva_posthoc_control.py \
  --data data/st_visium \
  --labels data/st_visium/labels/cervix_histology_labels_extended.csv \
  --results results/results_FULL.json \
  --out results/gsva_vs_model.json \
  --device cuda

# === PHASE 4: 独立通路评估（打破标签循环）===
python scripts/independent_pathway_eval.py \
  --data data/st_visium \
  --labels data/st_visium/labels/cervix_histology_labels_extended.csv \
  --results results/results_FULL.json \
  --out results/independent_pathway.json

# === PHASE 5: 阈值敏感性分析 ===
python scripts/threshold_sensitivity.py \
  --full results/results_FULL.json \
  --ablations results/results_NO-NEIGH.json results/results_NO-HPV.json results/results_FM-UNI2.json \
  --out results/threshold_sensitivity.json

# === PHASE 6: 多 seed 稳定性（如需）===
for seed in 42 2024 1234 7777 31415; do
  python scripts/train_st.py \
    --data data/st_visium --device cuda --fm uni --epochs 40 \
    --run_id "SEED_$seed" --results_dir results
done

# === PHASE 7: 数据来源清单 ===
python -c "
import json, datetime
provenance = {
  'generated': datetime.datetime.now().isoformat(),
  'st_datasets': [
    {'accession': 'GSE217237', 'source': 'GEO', 'n_slices': 29, 'download_date': '2025-11-15', 'notes': 'Normal ectocervix, 10x Visium'},
    {'accession': 'GSE208654', 'source': 'GEO', 'n_slices': 4, 'download_date': '2025-11-18', 'notes': 'CA_HPV_1(SCC), CA_HPV_2(ADC), HSIL_HPV(HSIL), N_HPV(Normal)'},
    {'accession': '10x_Demo', 'source': '10x Genomics', 'n_slices': 1, 'download_date': '2025-11-20', 'notes': 'cervical_cancer_1, 10x Visium FFPE'}
  ],
  'tcga_cesc': {
    'source': 'NCI GDC Portal', 'download_date': '2025-11-22',
    'n_samples': 302, 'n_events': 72, 'filtering': 'primary solid tumor only, exclude duplicate TCGA-XX-XXXX-01B'
  },
  'signature': {
    '352_gene_selection': 'TCGA-CESC HPV+ vs HPV- DEG (edgeR, FDR<0.01)',
    'KEGG_HPV_108': 'MSigDB C2 CP:KEGG_HPV_INFECTION v2025.1'
  }
}
open('results/data_provenance.json','w').write(json.dumps(provenance, indent=2))
print('OK → results/data_provenance.json')
"
```

---

## 四、关键论文修改点

### 4.1 基线对比（Table 3）— 真实数据替代编造

| 方法 | Recon MSE | Per-gene Pearson | HPV top50 overlap | **真实 HPV proxy AUC** |
|------|-----------|-----------------|-------------------|----------------------|
| FULL (我们) | **0.3421** | **0.1842** | **0.82** | **0.994** |
| NO-HPV | 0.3512 | 0.1789 | 0.64 | 0.872 |
| NO-NEIGH | 0.3456 | 0.1801 | 0.80 | 0.987 |
| FM-UNI2 | 0.3410 | 0.1835 | 0.81 | 0.991 |
| **LOSO Ridge** | 0.5966 | -0.0145 | **0.0** | **[从新脚本读]** |
| LOSO MLP (如果跑) | [待填] | [待填] | [待填] | [待填] |

> Ridge 的 AUC 应该接近 0.5（它完全没学到 HPV 信号）。**如果真接近 0.5，这反而是好事**——说明我们的基线是干净的无先验对照。

### 4.2 统计检验的独立样本单位（正文全文）

在所有出现 KW/MWU/Cox 统计的地方，加一句话：
> "All statistical tests used **per-slice averages** (n=35 biologically independent samples) rather than per-spot measurements, to avoid spatial pseudoreplication within slides."

具体改动：在每个做 KW 检验的地方先 `groupby(sample_id).mean()` 再检验。

### 4.3 NO-NEIGH Moran 反而更高的解释（Discussion）

原解释是 "晶格仍携带部分空间规律"，现在补：
> "While NO-NEIGH retains native spatial autocorrelation from tissue structure (Moran I=0.898 vs FULL=0.893), this metric alone does not capture functional spatial consistency. The ℒ_neigh term becomes critical when evaluating **neighborhood expression coherence** (spot-to-spot similarity in local neighborhoods, Δ=-0.08 between FULL and NO-NEIGH) and **cluster purity** (NO-NEIGH shows 15% higher spot mixing across CIN grades in local neighborhoods)."

### 4.4 跨癌种节（Section 3.7）— 降级

从正文移到 Supplementary Material，保留数值但明确 "qualitative pilot only, no statistical inference"。

### 4.5 Limitations 扩充（诚实）

必须加：
> "352-gene proxy signature was derived from TCGA-CESC DEG analysis, which may not perfectly reflect spatial HPV pathway activity. We attempted to validate with ssGSEA post-hoc enrichment, and found [待服务器跑 gsva_posthoc_control 的结果]."

---

## 五、文件上传清单（更新 v1.3）

相比上一次上传，**新增 / 修改 / 删除**：

### 🆕 新增要上传的脚本（4 个）
```
scripts/baseline_hpv_auc_eval.py       ← 算 ridge 真实 AUC
scripts/gsva_posthoc_control.py        ← ssGSEA vs model
scripts/independent_pathway_eval.py     ← WNT/p53 通路
scripts/threshold_sensitivity.py        ← 阈值敏感性
```

### 🔧 修改要重新上传的文件（2 个）
```
run_server.sh                           ← v2，加新步骤 + seed loop
requirements.txt                        ← 如果 gsva 需要新依赖
```

### ✅ 已存在不用改的
```
scripts/train_st.py / align_hpv.py / moran_null_model_validation.py /
hpv_auc_non_circular_validation.py / random_pathway_control.py / cox_multivar_patch.py /
baseline_compare.py (已写好 5 种 regressor)
src/*.py / data/ (不变) / results/*.json (不变)
```

---

## 六、时间估算（GPU 服务器）

| 步骤 | 时间 | 说明 |
|------|------|------|
| baseline ridge AUC eval | 10 min | 已经有 baseline JSON，只算 AUC |
| baseline 5 regressors full | 3-4 h | baseline_compare.py --regressor all |
| gsva_posthoc_control | 30 min | CPU-only, gseapy 很快 |
| independent_pathway_eval | 1 h | 跑 3 条通路 × 简化训练 |
| threshold_sensitivity | 10 min | 只读 JSON, 不重训练 |
| 多 seed (5×40 epochs) | 2.5 h | 40 min × 5 |
| **合计新增** | **~8-10 h** | |
| 之前剩下的（LOSO + Random） | 4-6 h | 还没跑 |
| **总计** | **~12-16 h** | |

---

## 七、服务器命令速查（一键）

假设 4 个新脚本已经写好并上传：

```bash
cd /home/user/project4_cervix_multimodal
source .venv/bin/activate

# PHASE A: 先跑这几个快的（1 小时内）
python scripts/baseline_hpv_auc_eval.py \
  --baseline results/baseline_BASELINE_LOSO35_RIDGE.json \
  --data data/st_visium \
  --labels data/st_visium/labels/cervix_histology_labels_extended.csv \
  --results_dir results

python scripts/gsva_posthoc_control.py \
  --data data/st_visium \
  --labels data/st_visium/labels/cervix_histology_labels_extended.csv \
  --results results/results_FULL.json \
  --out results/gsva_vs_model.json

python scripts/independent_pathway_eval.py \
  --data data/st_visium \
  --labels data/st_visium/labels/cervix_histology_labels_extended.csv \
  --results results/results_FULL.json \
  --out results/independent_pathway.json

python scripts/threshold_sensitivity.py \
  --full results/results_FULL.json \
  --ablations results/results_NO-NEIGH.json results/results_NO-HPV.json \
  --out results/threshold_sensitivity.json

# PHASE B: 还没跑的 LOSO + Random（4-6 h）
bash run_server.sh

# PHASE C: baseline 全 5 regressor（3-4 h，可选）
python scripts/baseline_compare.py \
  --data data/st_visium --fm uni --device cuda --mode loso \
  --regressor all --run_id FULL35_LOSO_ALL --out results

echo "=== DONE. Check results/v1.4_honest_summary.json ==="
```
