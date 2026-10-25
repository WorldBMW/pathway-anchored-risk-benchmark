# Project 4 · 基于空间转录组(ST)与全切片病理图像(H&E)跨模态融合的宫颈肿瘤微环境解析与风险分层

> 顶配二区/一区（SCI Q1/Q2）计算病理学实验方案 · 空间多模态融合 · 同患者配对 · 可复现 · 公开数据集

---

## 一、研究计划书（顶配期刊范式）

### 1.1 科学问题与立项逻辑
宫颈肿瘤进展由肿瘤微环境（TME）的空间结构驱动。2025–2026 年 Nature / Nature Medicine
（TITAN、STORM 等）确立了 **「空间转录组 ST + 病理图像跨模态对齐」** 为最前沿、
最受审稿人认可的方向。本研究聚焦 **同一张切片上 ST 基因表达与 H&E 图像的同位置跨模态融合**，
解析宫颈肿瘤微环境的空间生态位结构，并构建微环境风险分层。

### 1.2 关键设计决策（规避审稿瑕疵）
- **同患者、同切片严格配对**：每个 Visium spot 的基因表达与 H&E patch 来自**同一物理位置、
  同一张切片、同一患者**（`src/st_data.py` 按 barcode 1:1 对齐，已验证 exp/img 严格 2781:2781）。
  → 彻底规避原方案「LACCI 细胞图 + TCGA-CESC 分子」跨队列拼接的方法学瑕疵。
- **无外部标签的自监督目标**：10x 数据集不含生存随访，若将目标定为「生存预后」会引入标签缺失瑕疵。
  故将目标改为**空间微环境风险分层**（自监督表达重建 + 风险评分空间一致性），
  仅依赖数据自身信号，逻辑自洽、无外部标签依赖。

### 1.3 数据源（全部公开、可下载、可溯源）
| 模态 | 数据集 | 来源 | 配对关系 |
|------|--------|------|----------|
| 空间转录组 + H&E | **10x Visium Human Cervical Cancer (FFPE)** | 10x Genomics 官网 | 同一张切片：ST spot + H&E patch 天然同患者配对 |
| 空间转录组 + H&E | **10x Visium Human Breast Cancer (FFPE)** | 10x Genomics 官网 | 同上（泛癌扩展） |
| 空间转录组 + H&E | **10x Visium Human Ovarian Cancer (FFPE)** | 10x Genomics 官网 | 同上（泛癌扩展） |
| 空间转录组 + H&E | **10x Visium Human Prostate Cancer (FFPE)** | 10x Genomics 官网 | 同上（泛癌扩展） |
| （可选补充）分子先验 | TCGA-CESC HPV 状态 | GDC 公开 API | 仅作宫颈生物学先验印证，不做跨队列配对 |

> 当前已下载并验证：10x Visium 泛癌样本 **4 例（宫颈/乳腺/卵巢/前列腺）**，合计 **13125 spots × 17943 genes + 配对 H&E patch 64×64**，均通过 `st_data.py` 单样本 1:1 配对验证。

### 1.4 技术路线（2025–2026 SOTA 范式）
```
下载 10x Visium (ST+H&E 同切片) → st_data 加载器(1:1 配对)
   → 基因表达(高变基因 log1p) 编码器
   + H&E patch 经 病理 Foundation Model (UNI/UNI2/CHIEF, 冻结) 抽取形态学特征  ← 前沿标配
   → 跨模态注意力融合 (cross-modal attention)
   → 自监督重建(表达) + 空间一致性风险评分(相邻 spot 评分连贯)
   → 微环境风险分层(高/低评分区)
   → 差异基因(Mann-Whitney U + BH-FDR) + TME 标记富集 + 空间生态位(niche)发现
```

### 1.5 核心实验（全套、逻辑闭环）
- **实验 1**：ST-H&E 跨模态融合表征学习（重建损失验证融合有效性）
- **实验 2**：微环境风险分层（per-spot 风险评分 → 高/低评分空间区域划分）
- **实验 3**：高/低风险区差异基因（**Mann-Whitney U + Benjamini-Hochberg FDR<0.05**）+ 通路富集 + TME 标记解析（消除管家基因噪声主导隐患）
- **实验 4**：空间一致性验证（相邻 spot 风险评分连贯性 / Moran's I = 微环境平滑性；该损失项已**真正进入反向传播**）
- **实验 5**：空间生态位(niche)发现与跨癌种比较（`src/niche.py`，图对比学习，对应 STAIG 2025）
- **实验 6**：可解释性（Grad-CAM on H&E + 基因贡献归因）
- **实验 7**（冲 Q1）：Foundation Model (UNI) vs 随机 CNN 消融，证明形态学基础模型增益

### 1.6 评价指标
- 自监督：重建 MSE、下游任务判别性
- 风险分层：高/低区差异基因 FDR 显著数、空间自相关（Moran's I）
- 可靠性：跨 spot 一致性、多样本可复现性、消融增益

### 1.7 冲高区（Q1）增量计划（进行中）
- ✅ 已完成：泛癌 Visium 扩展至 4 癌种（宫颈/乳腺/卵巢/前列腺，13125 spots），做跨癌种泛化 + 宫颈亚组重点分析
- ✅ 已完成：接入 **病理 Foundation Model (UNI)** 编码 H&E（2025-2026 前沿标配），修复空间一致性损失未参与训练的 bug
- ✅ 已完成：差异基因加 **FDR 显著性检验 + TME 标记富集**，空间生态位聚类模块
- 📌 建议补充：**Visium HD / Xenium 亚细胞分辨率数据**（2025 热点，分辨率高 1-2 数量级，非老旧 55µm 平台）——在 4090 服务器按需拉取
- 📌 争取多患者重复样本（同一癌种 ≥3 例）以强化统计效力；对接 STOMICS/CROST 做外部验证

---

## 二、项目结构
```
project4_cervix_multimodal/
├── data/
│   ├── st_visium/
│   │   ├── cervical_cancer_1/   # 10x Visium 宫颈(ST+H&E 同患者配对)
│   │   ├── breast_cancer_1/     # 10x Visium 乳腺
│   │   ├── ovarian_cancer_1/    # 10x Visium 卵巢
│   │   └── prostate_cancer_1/   # 10x Visium 前列腺
│   │       ├── filtered_feature_bc_matrix.h5
│   │       ├── spatial/  (tissue_hires_image.png + 坐标 + scalefactors)
│   │   └── image.jpg
│   ├── cesc/                          # TCGA-CESC 分子(可选先验)
│   ├── lacci/                         # LACCI(可选补充细胞模态)
│   └── molecular/
├── src/
│   ├── st_data.py            # ST+H&E 加载器(1:1 配对)
│   ├── models.py             # ST-H&E 跨模态注意力融合(支持注入 foundation encoder)
│   ├── foundation_encoder.py # 病理 Foundation Model (UNI/UNI2/CHIEF) H&E 编码
│   ├── niche.py              # 空间生态位聚类 + 跨样本比较
│   └── metrics.py
├── scripts/
│   ├── download_10x_st.py  # 下载 10x Visium
│   ├── download_lacci.py   # (可选)下载 LACCI
│   ├── download_cesc.py    # (可选)下载 TCGA-CESC
│   └── train_st.py         # ST-H&E 训练 + 风险分层(FDR/TME/niche)
└── README.md
```

## 三、快速开始
```bash
# 0. （4090 服务器）安装依赖
pip install timm transformers scanpy anndata   # UNI 需要 timm；analysis 需要 scanpy

# 1. 下载同患者配对数据（已下好可跳过）
python scripts/download_10x_st.py --mode std     # 4 癌种 55um Visium（默认）
python scripts/download_10x_st.py --mode hd      # Visium HD 亚细胞（结肠 P1/P2）
#    注：HD 的 binned_outputs.tar.gz 单样本 ~12GB，需足够磁盘（已验证本机 H 盘可下）

# 2. 训练 ST-H&E 跨模态融合 + 风险分层（推荐用 UNI 基础模型，GPU 上跑）
python scripts/train_st.py --epochs 40 --device cuda --fm uni
#    Visium HD 样本（亚细胞）：用 --max_spots 控制显存，patch 自动 224 适配 UNI
python scripts/train_st.py --epochs 40 --device cuda --fm none --max_spots 40000

# 2b. 消融研究（二区以上必备：证明增益来源）—— 一键跑 FULL/BASELINE-CNN/NO-NEIGH/NO-RECON/FM-UNI2/FM-CHIEF
python scripts/ablation_study.py --data data/st_visium --device cuda --epochs 40
#     结果汇总：ablation_summary.json / ablation_summary.csv

# 2c. 可解释性（H&E 遮挡显著性图，冻结 FM 也适用）
python scripts/explain_st.py --data data/st_visium/cervical_cancer_1 \
    --fm none --device cuda --out_dir results/explain

# 3. 查看结果（含 FDR 显著差异基因 + TME 标记富集）
cat results_st.json
```

> 本地 CPU 亦可快速验证流程（`--fm none --epochs 2`），但完整实验请在 4090 服务器运行。

## 四、当前数据状态（实时）
- ✅ **10x Visium 泛癌 ST+H&E（4 癌种，55µm）**：已下载并验证。
  - cervical_cancer_1：2781 spots；breast_cancer_1：2518 spots；ovarian_cancer_1：3455 spots；prostate_cancer_1：4371 spots
  - 合计 **13125 spots × 17943 genes + 配对 H&E patch**（均经 `st_data.py` 1:1 配对验证）。
  - pipeline 已跑通（CPU `--fm none`）：重建 MSE 收敛，风险分层 6563/13125 高/低；FDR/TME 模块已就绪。
- ✅ **Visium HD（亚细胞分辨率，8µm bins）**：已下载完成（110 文件）。`st_data.py` 已支持 HD 自动探测（binned_outputs/square_008um + parquet 坐标），坐标缩放/spot 直径已修复。
- ✅ **TCGA-CESC 分子**：已下载。
  - `data/cesc/cesc_clinical.csv`（HPV 状态/生存，56KB）
  - `data/cesc/cesc_rnaseq.csv`（UCSC Xena 公开镜像，20530×308，用于跨队列 HPV 对齐 Layer2）
- ❌ **LACCI**：figshare 源清单本身缺失 `JPEGImages.z09` 分卷，**不可恢复**；已确认并刻意放弃（方案 b 不依赖）。详见 `实验方案与执行指南.md` 第 0/6 节。
- ✅ **代码升级**：接入 UNI/UNI2/CHIEF 病理基础模型、FDR 显著性检验、TME 富集、niche 聚类、Moran's I 空间自相关、消融研究编排（`scripts/ablation_study.py`）、可解释性（`scripts/explain_st.py`）；修复 HD 坐标缩放与 spot 直径 bug。
- 📌 冲 Q1 待扩展：多患者重复样本（同癌种 ≥3 例）+ 独立外部验证队列（STOMICS/CROST）。

## 五、方法学严谨性说明（面向审稿人）
1. **配对无瑕疵**：ST 与 H&E 来自同一张切片，`st_data.py` 按 barcode 严格 1:1 对齐（已单测验证）。
2. **标签无瑕疵**：采用自监督风险分层，不依赖缺失的生存标签，避免「无结局标签却做预后」的质疑。
3. **前沿方法无瑕疵**：H&E 经冻结的病理 Foundation Model (UNI/UNI2/CHIEF) 编码，符合 2025-2026 SOTA 范式；并设随机 CNN 消融对照。
4. **统计严谨**：差异基因经 Mann-Whitney U + Benjamini-Hochberg FDR 校正，仅报显著基因；TME 标记富集提供生物学可解释性。
5. **可复现**：全部数据公开可下载，脚本端到端可复现。



python scripts/train_st.py --data data/st_visium/geo_cesc \
  --epochs 60 --fm uni --device cuda --run_id CERVIX_V3 \
  --lambda_hpv 1.0 --lambda_sup 3.0 --lambda_recon 0.3 --lr 5e-4 \
  --grad_clip 1.0

