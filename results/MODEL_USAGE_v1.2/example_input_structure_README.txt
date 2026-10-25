==========================================================================
  Example Input Structure for the HPV-Anchored Spatial Multitask Model
  (v1.2 · required by predict_one_slice.py / scripts/train_st.py)
==========================================================================

RULE 1: Every 10x Visium slide must live in its own folder under  data/st_visium/
--------------------------------------------------------------------------------
data/st_visium/
├── CA_HPV_1/                       <- sample_id = "CA_HPV_1" (SCC case, GEO GSM6360691)
│   ├── filtered_feature_bc_matrix.h5    <- ⭐ 必须！这是主输入文件（gene × barcode × counts）
│   │                                         注意：请一定是 Space Ranger 输出的 .h5，不要自己导出 CSV/TSV.gz
│   │                                         否则 barcode 顺序、feature_id 映射将错位导致 HPV AUC 错。
│   │
│   ├── image.jpg  OR  spatial/tissue_hires_image.png   <- ⭐ 二选一就行（画热力图用），
│   │                                                       建议 2000×2000 px 以上。
│   │
│   ├── spatial/                          <- ⭐ 必须存在该目录！
│   │   ├── scalefactors_json.json        <- ⭐ 必须！spot ↔ 图像像素的转换参数
│   │   │                                   （SpotDiameter、tissue_lowres_scalef 等）
│   │   ├── tissue_positions_list.csv  或者  tissue_positions.csv  <- ⭐ 必须其一
│   │   │   （列：barcode / in_tissue / array_row / array_col / pxl_row_in_fullres / pxl_col_in_fullres）
│   │   ├── tissue_hires_image.png        <- 可选，优先于 image.jpg
│   │   ├── tissue_lowres_image.png       <- 可选
│   │   └── aligned_fiducials.jpg         <- 可选，Space Ranger 自带
│   │
│   └── [可选] raw_feature_bc_matrix.h5 / web_summary.html / spatial.tar.gz
│       （如果有，不影响推理；但提供更完整溯源信息，推荐保留）
│
├── Ecto_P004/                      <- sample_id = "Ecto_P004" (Normal_Ecto)
│   ├── filtered_feature_bc_matrix.h5
│   └── spatial/ (同上结构)
│
├── 【训练集必须的 35 张切片清单】（train_st.py 默认会自动扫描 data/st_visium/ 下所有子文件夹）
│   Geo_CESC 集合：CA_HPV_1 (SCC)、CA_HPV_2 (ADC)、HSIL_HPV、N_HPV（4 张）
│   Geo_ectocervix 集合：P001, P004, P007, P008, P014, P016, P018, P020, P021, P023,
│   P024, P026, P028, P031, P044, P045, P047, P050, P057, P067, P080, P081, P087,
│   P097, P105, P107, P108, P114, P117, P118 （共 31 张 Normal_Ecto）
│   合计 = 4 + 31 = 35 张（本研究 MAIN_MODEL_PASS 12/12 的标准组成）
│
==========================================================================

RULE 2: TCGA-CESC cross-modal Cox 需要的 data/cesc/ 两张输入（Use Case 4）
--------------------------------------------------------------------------------
data/cesc/
├── cesc_clinical.csv        <- 临床元数据表（302 行 × 多个字段）
│                              要求至少包含 4 列：
│                              · TCGA_id        (12 字符，如 "TCGA-2Y-A9GU")
│                              · OS_MONTHS      (数字，总生存月数)
│                              · OS_EVENT       (0/1，0 = 删失，1 = 死亡)
│                              · AGE_AT_DIAGNOSIS  (数字，年龄协变量)
│                              · HPV_STATUS     ("Positive" / "Negative" / "Indeterminate")
│
└── cesc_rnaseq.csv           <- 表达矩阵（gene_symbol × 302 TCGA sample）
                                 行名 = GeneSymbol（如 "TP63"、"E6*"、"CDKN2A"，
                                 需与 ST 侧使用的 10x 参考基因组 GRCh38 / GENCODE v32 基因名
                                 完全一致；大小写敏感！）
                                 推荐值：log2(FPKM+1) 或 vst-normalised count。

==========================================================================

RULE 3: 可选组织学标签 CSV（用于 Results 3.3 组织学亚型 / CIN 分级统计）
--------------------------------------------------------------------------------
resources/cervix35_histology_labels.csv
列 1 = sample_id (必须与 st_visium 下文件夹名完全一致)
列 2 = histology_subtype  ∈ {Normal_Ecto, Normal, HSIL, SCC, ADC}
列 3 = cin_grade            ∈ {0, 1, 2, 3, 4}   （0=Normal，1-2=CIN1/CIN2合并，3=CIN3/SCC，4=ADC）
列 4 = n_spots              (整数，每张切片的 spot 数量，用于 MWU spot-level 敏感性分析)

==========================================================================

COMMON MISTAKES（推理出错的 6 个常见坑）
--------------------------------------------------------------------------------
❌ 错误 1：把 .h5 解包成 barcodes.tsv.gz + features.tsv.gz + matrix.mtx.gz 三份文件推理
   解决：predict_one_slice.py / train_st.py 统一读 .h5（通过 scanpy.read_10x_h5）速度快且不会错位。

❌ 错误 2：spatial/ 文件夹丢失，只给了一张 png 图
   解决：没有 scalefactors_json.json + tissue_positions.csv，热力图无法准确画在 H&E 对应位置。

❌ 错误 3：TCGA cesc_rnaseq.csv 的列名是 TCGA full barcode（约 28 字符）而非 12 字符 patient id
   解决：align_hpv.py 会自动取前 12 字符做映射；如果有重复 12 字符 ID（同一患者多个 vial），
   align_hpv.py 会自动报警并保留第一个样本（与 CMPB 主文一致）。

❌ 错误 4：新切片基因名是 Ensembl ID（"ENSG00000141510"），不是 GeneSymbol（"TP63"）
   解决：先用 resources/gencode_v32_ensg_to_symbol.tsv 转换一次，否则与 KEGG 108 基因对不上。

❌ 错误 5：组织学标签里 HSIL / ADC 写成大写 "SCC-like HSIL" 或 "Adenocarcinoma"
   解决：必须严格按 5 类枚举值拼写，否则 MWU focus pair（Normal_Ecto_vs_HSIL、_vs_ADC）
   匹配不到，对应 p 值显示 nan，会被 12 项 QC 拒。

❌ 错误 6：在不同机器上把 PYTHONHASHSEED 改成其他值或没设置
   解决：跨平台复现时，强制 export PYTHONHASHSEED=42 + CUBLAS_WORKSPACE_CONFIG=":4096:8"。
==========================================================================
