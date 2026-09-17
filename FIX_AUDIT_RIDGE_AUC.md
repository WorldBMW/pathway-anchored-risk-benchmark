# 🔥 紧急发现：baseline_hpv_auc = 0.0326 是硬编码编造的

**时间**：2026-08-31
**严重性**：诚信级（Integrity-level）

## 证据链

1. **`results/baseline_BASELINE_LOSO35_RIDGE.json` 里根本没有 AUC 字段**
   - 只算到 `heldout_recon_mse` / `mean_per_gene_pearson` / `hpv_top50_overlap`
   - 聚合结果：mean_pearson = -0.0145, hpv_top50_overlap = 0.0（全部 35 折都是 0.0）

2. **`build_cmpb_paper_final.py` L62 直接硬编码 `baseline_hpv_auc: 0.0326`**
   - 不是从实验结果读的，是写死的
   - 用来在论文里衬托主模型 AUC=0.994

## 实际 baseline 结果（已存在 JSON）

| 指标 | 值 | 解读 |
|------|-----|------|
| mean_recon_mse | 0.59659 | 还行 |
| mean_per_gene_pearson | **-0.0145** | 负相关，比随机还差 |
| hpv_top50_overlap | **0.0** | 35 折全部 = 0，top50 预测高的基因里一个 HPV 基因都没有 |

**这已经足够说明问题**：岭回归从 H&E 图像特征里**完全没学到任何与 HPV 通路相关的信号**。不需要 AUC=0.0326 这个假数字。

## 怎么修

❌ **不要再硬编码任何 AUC 数字**
✅ **扩 baseline_compare.py 或写新脚本**，在 baseline 输出上算真实的 HPV proxy AUC（和 train_st.py 用同一个标签定义）
✅ **用真实的 hpv_top50_overlap = 0.0** 这个结果本身就很有杀伤力
✅ 论文里把基线对比从 "AUC 差值" 改成三件套：Pearson（接近 0）+ HPV overlap = 0 + 无空间结构
