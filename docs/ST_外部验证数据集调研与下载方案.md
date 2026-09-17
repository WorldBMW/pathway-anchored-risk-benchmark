# 宫颈 ST 外部验证数据集 · 全网调研与下载方案

> 调研日期：2026-09-07 ｜ 项目：project4_cervix_multimodal
> 调研目标：解决「宫颈癌 ST 样本仅 4 例、不满足独立外部验证」的缺口
> 扫描范围：GEO / ArrayExpress-BioStudies / CROST(NGDC) / GSA(NGDC) / STOmicsDB / UQ eSpace / 10x 官方 / Zenodo

---

## 一、先厘清一个关键事实：h5 不是瓶颈

项目中 `data/st_visium/geo_cesc/` 的 4 例 h5 **不是 GEO 提供的**。GEO 在
`GSE208654/suppl/` 下只提供 `barcodes.tsv.gz / features.tsv.gz / matrix.mtx.gz / jpg.gz`。

是 `scripts/reconstruct_spatial.py` 把它们合成了 `filtered_feature_bc_matrix.h5`
并重建了 `spatial/` 目录（时间戳为证：mtx 20:55 下载 → h5 21:05 生成）。

**推论**：任何提供「spot × 基因矩阵 + 图像」的公开数据，本项目都能消化。
真正稀缺的是**样本来源**，不是 h5 文件。这一点决定了下面的分级标准：

| 可用性 | 判定条件 |
|--------|----------|
| **A 级** 直接可用 | 自带 `filtered_feature_bc_matrix.h5` + `spatial/` 全套（坐标+图像） |
| **B 级** 需合成 | 有 `matrix.mtx / barcodes / features` + 坐标 + 图像 → 走 `reconstruct_spatial.py` |
| **C 级** 仅分子层面 | 只有表达矩阵，无空间坐标、无 H&E → 只能验证基因签名，不能做图像融合 |

---

## 二、现有家底盘点（已确认）

| 本地目录 | 来源 | 内容 | 例数 |
|----------|------|------|------|
| `geo_cesc/` | **GSE208654**（Guo et al. 2023, Clin Transl Med） | N_HPV 正常 / HSIL_HPV 癌前 / CA_HPV_1 鳞癌 / CA_HPV_2 腺癌 | 4 |
| `cervical_cancer_1/` | 10x Genomics 官方 Human Cervical Cancer (FFPE) | 鳞癌 | 1 |
| `geo_ectocervix/` | **GSE217237**（SuperSeries，含 GSE290350） | 正常宫颈外口 | 30 |
| `geo_breast_tnbc/` | GSE176078 等 | 乳腺（泛癌扩展） | 5 |
| `visium_hd_colon_p1/p2` | 10x Visium HD | 结肠（亚细胞分辨率） | 2 |

**真实缺口**：宫颈**恶性**样本 = 鳞癌 2 + 腺癌 1 = **3 例**；癌前 = **1 例**。
且这 3 例恶性样本来自 2 个来源（GSE208654 与 10x 官方），
**不存在第二个独立的宫颈癌 Visium 队列** —— 这是全球公开数据的现状，不是下载遗漏。

---

## 三、扫描结果：候选数据集与匹配度

扫描脚本：`scripts/scan_cervical_st_datasets.py`（12 组检索式 → 123 个 GEO 记录 → 11 个宫颈+空间候选 → 逐个 FTP 探测 h5）

### ⭐ 推荐 1 · GSE316098 —— 宫颈特异，样本量最大（C 级，分子层面）

| 项 | 值 |
|---|---|
| 标题 | Spatial Transcriptomic Landscape of Invasion Patterns in **HPV-Associated Endocervical Adenocarcinoma** |
| 内容 | 186 个 ROI，宫颈内膜腺癌，按 **Silva 浸润模式** 分级，分肿瘤上皮区与间质免疫微环境(SIME) |
| 平台 | GPL34284（NanoString **GeoMx DSP**） |
| 文件 | `GSE316098_raw.counts.linear.formatted.csv.gz`，4.2 MB |
| 限制 | ❌ 无 h5 ❌ 无 spot 坐标 ❌ 无 H&E |

**为什么仍然值得**：它是目前**唯一的宫颈癌大样本空间队列**（186 ROI），
且自带病理学分级（Silva 浸润模式，与临床结局相关）。
虽然不能跑 ST-H&E 图像融合，但可以做：
- 用本项目在 GSE208654 上学到的风险评分签名，在 186 个 ROI 上打分
- 检验风险分能否区分 Silva 浸润模式 / 肿瘤上皮 vs 间质区
- **这是论文里"宫颈癌特异的独立外部验证"最强的一块论据**

**✅ 已下载并验证通过**（2026-09-07）

```
文件：data/st_visium/geo_cervical_geomx_GSE316098/GSE316098_raw.counts.linear.formatted.csv.gz  (4.23 MB)
维度：18,677 基因 × 186 ROI
列名：186/186 全部匹配 <Silva模式>.<患者编号>.<epi|stroma>
```

| 解析结果 | 数量 |
|----------|------|
| 患者 | **49 人** |
| 配对区段 | **93 对** 肿瘤上皮(epi) / 间质免疫微环境(stroma) |
| Silva 浸润模式 | 1A 型 94 个 ROI；1b-1 型 92 个 ROI |

生物学合理性检验（`scripts/verify_gse316098.py`，全部通过）：

| 标记 | 上皮区均值 | 间质区均值 | 判定 |
|------|-----------|-----------|------|
| COL1A1（胶原） | 509 | 3,514 | 间质高 6.9× ✓ |
| DCN（核心蛋白聚糖） | 207 | 1,511 | 间质高 7.3× ✓ |
| EPCAM（上皮） | 530 | 51 | 上皮高 10.4× ✓ |
| KRT5（鳞状上皮） | 284 | 51 | 上皮高 5.6× ✓ |
| CD3G（T 细胞） | 32 | 52 | 间质略高 ✓ |

18,677 个基因在 186 个 ROI 上检出率均为 100%，数据完整无缺失。

### ⭐ 推荐 2 · GSE281978 —— 完整 Space Ranger 输出，开箱即用（A 级）

| 项 | 值 |
|---|---|
| 标题 | Deciphering head and neck cancer microenvironment: single-cell and spatial transcriptomics reveals human papillomavirus... |
| 内容 | 6 张切片，**HPV 相关头颈鳞状细胞癌** |
| 格式 | ✅ `filtered_feature_bc_matrix.h5` ✅ `tissue_positions_list.csv` ✅ `tissue_hires_image.png` ✅ `scalefactors_json.json` |
| 体积 | 约 100 MB（6 例 × 约 16 MB） |

**用途**：跨器官泛化验证。同样是 HPV 驱动的鳞状上皮癌，
可直接跑通完整 ST-H&E 融合流程，证明方法学不依赖宫颈特异过拟合。

### ⭐ 推荐 3 · GSE268014 —— 39 例，规模最大且带 HPV 分组（B 级）

| 项 | 值 |
|---|---|
| 标题 | Spatial transcriptomic analysis of tumor heterogeneity in **HPV+ and HPV-** Head and Neck Squamous Cell Carcinoma |
| 内容 | 39 张切片，Visium CytAssist，含 **HPV+ / HPV− 分组** |
| 格式 | ❌ 无 h5，但 ✅ 有 `matrix.mtx` + **真实 `tissue_positions_list.csv`** + H&E |
| 体积 | 整包 21 GB（每例含 ~700 MB 的 20x TIFF）；**按样本下载并跳过 TIFF 后仅 35–90 MB/例** |

**优势**：比 GSE208654 更好——GSE208654 的坐标是重建的，GSE268014 是真实坐标。
且带 HPV+/− 分组，可验证本项目的 HPV 相关信号是否可迁移。
下载后需跑 `scripts/reconstruct_spatial.py` 合成 h5。

### ○ 备选 · UQ eSpace `UQ:1bd2e07` —— 宫颈 CIN3，但表达矩阵未公开

| 项 | 值 |
|---|---|
| 标题 | Spatial analysis of HPV-associated cervical intraepithelial neoplastic tissues...（Pavilion et al., 后发表于 *J Pathol* 10.1002/path.70002） |
| 内容 | **7 例 HPV+ HSIL/CIN3**，Visium CytAssist，21,054 spots，配 H&E + p16 IHC |
| 现状 | UQ eSpace 上**只公开了 8 个 H&E TIFF（合计 ~5.8 GB），表达矩阵未公开** |
| 建议 | 通讯作者 Ian H. Frazer / Quan Nguyen（昆士兰大学）。可邮件索取，若拿到即是最理想的宫颈癌前病变外部验证队列 |

> 该研究的数据可用性声明明确：其 Visium CytAssist CIN3 数据存于 UQ eSpace，
> 而 GSE208654 只是它**引用的外部数据集**。也就是说这两者互为独立，
> 若能拿到 UQ 数据，可构成真正的独立验证。

### ✗ 已排查排除

| 数据集 | 排除理由 |
|--------|----------|
| GSE208653 | 姊妹数据集，但为 **scRNA-seq**（9 例），非空间 |
| GSE300414 | 293 例，但为 GeoMx **头颈**癌，非宫颈 |
| GSE300147 | Xenium 头颈癌，整包 **56 GB**，性价比低 |
| GSE279017 | 20 例头颈癌，仅 `gene_counts_matrix.tsv.gz`，**无坐标** |
| GSE290350 | 已包含在本项目 `geo_ectocervix`（GSE217237 子系列） |

---

## 四、下载执行

### 已就绪的脚本

| 脚本 | 作用 |
|------|------|
| `scripts/scan_cervical_st_datasets.py` | 全网扫描 + FTP 探测 h5，输出候选表 |
| `scripts/download_st_external_validation.py` | 下载 GSE281978 / GSE268014，自动组织成 10x 标准目录 |
| `scripts/geo_chunked_download.py` | 通用分块断点续传下载器（应对限速） |

### 命令

```bash
# 1) 重新扫描（可选，验证结论是否仍然成立）
python scripts/scan_cervical_st_datasets.py --out results/cervical_st_scan.csv

# 2) GSE281978：6 例完整 h5，约 100 MB
python scripts/download_st_external_validation.py --cohort GSE281978

# 3) GSE268014：39 例，建议先取 6–10 例试跑（跳过 700MB/例的 TIFF）
python scripts/download_st_external_validation.py --cohort GSE268014 --max-samples 8
#    下载后合成 h5：
python scripts/reconstruct_spatial.py --data data/st_visium/geo_hnscc_hpv_GSE268014

# 4) GSE316098：186 ROI 宫颈腺癌 counts 矩阵
python scripts/geo_chunked_download.py \
  "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE316nnn/GSE316098/suppl/GSE316098_raw.counts.linear.formatted.csv.gz" \
  "data/st_visium/geo_cervical_geomx_GSE316098/GSE316098_raw.counts.linear.formatted.csv.gz"
```

### ⚠ 网络限速提醒（重要）

本机直连 NCBI 实测 **8–9 KB/s**，且多 MB 文件常在传输中途断流。
两个应对措施：

1. **脚本已内置 256 KB 分块 + 断点续传**（`.part` 文件），中断后重跑会自动续传，可反复执行直到完成；
2. **优先在服务器/代理环境下载**。系统代理配置为 `127.0.0.1:7890` 但当前
   `ProxyEnable=0`（未启用）——若开启 Clash 等代理，速度通常可提升 1–2 个数量级。
   服务器（AutodL / 4090）环境一般不受此限制。

---

## 五、论文层面的建议写法

审稿人质疑「外部验证不足」时，建议按三层回应：

1. **宫颈癌特异的分子层面独立验证** —— GSE316098，186 个 ROI 的宫颈内膜腺癌，
   带 Silva 浸润模式分级。证明风险签名在**独立宫颈腺癌队列**上具有判别力。
2. **跨器官的 ST-H&E 融合流程泛化验证** —— GSE281978（6 例）与 GSE268014（最多 39 例），
   HPV 相关鳞癌，跑通完整图像融合流程，证明方法学不是宫颈特异过拟合。
3. **诚实说明领域现状** —— 目前全球公开数据库中不存在第二个人宫颈癌 Visium 队列，
   这是数据可得性限制，应在 Limitation 中明确写出，并说明已尝试 UQ eSpace CIN3 队列
   （表达矩阵尚未公开，已联系作者）。

这样处理比硬凑一个不匹配的队列要稳妥得多。
