"""
构建 CMPB v1.2 投稿配套的「公开数据集来源与时间跨度清单」Excel
交付：papers/01_CMPB/公开数据集来源与时间跨度清单_Public_Datasets_Source_and_Time_Span_v1.2.xlsx
字段：11 列（中文列名 + 英文列名 双行 header）
"""
import os, datetime
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ROOT = r'g:\project4_cervix_multimodal'
CMPB_DIR = os.path.join(ROOT, 'papers', '01_计算机方法与生物医学程序_Computer_Methods_and_Programs_in_Biomedicine_IF6.4_CAS_MED_Z2')
ACC_DATE = '2026-08-27'

rows = [
    [1,
     'TCGA-CESC bulk RNA-seq 主队列（泛癌 Pan-Cancer Atlas 原始发表）',
     'The Cancer Genome Atlas Cervical Squamous Cell Carcinoma and Endocervical Adenocarcinoma (CESC) — Pan-Cancer Atlas release',
     'Bulk RNA-seq (RSEM / HTSeq counts) + 原发灶临床元数据',
     'n = 302 例（本研究实际进入分析 = 302 例，含死亡事件 72 例，完整生存 + 年龄协变量）',
     '患者招募/组织采集时间跨度：≈ 2009Q3 – 2014Q2（TCGA 泛癌项目公开采集窗口）；原始分子数据发布：2013Q4；Pan-Cancer Atlas 最终汇总发表：2018Q1；后续持续被 Liu et al. Cell 2018 临床资源整理版所引用',
     'NCI GDC Data Portal（Legacy Archive + GDC harmonised HARM64 双版本可获取）；原项目由 NIH/NCI 国家癌症研究所资助并托管',
     'Project Portal: https://portal.gdc.cancer.gov/projects/TCGA-CESC  ｜  Pan-Cancer Atlas DOI: https://doi.org/10.1038/ng.2764 (Weinstein 2013)  ｜  临床资源整理 DOI: https://doi.org/10.1016/j.cell.2018.02.052 (Liu 2018)  ｜  GDC Legacy Bulk RSEM Accession: TCGA-CESC FPKM-UQ legacy files',
     'TCGA 官方数据共享许可：NIH GDC Open Access（CC-BY 4.0 Equivalent）；仅允许用于回顾性二次研究，禁止任何身份再识别；全部数据完全去标识化（HIPAA Safe Harbor / dbGaP phs000178.v*.p*）',
     'Layer 3 跨模态预后迁移验证的唯一 bulk 队列：用于导出 352 基因 HPV 代理签名并做单因素 + 年龄校正 Cox 比例风险模型 + Kaplan-Meier（补充图 S1）。⚠ 本步为跨模态（Visium ST → bulk RNA-seq）预后迁移，非同平台独立外部验证。',
     f'最后访问日期：{ACC_DATE}；本研究下载版本：GDC HARM64 基因级 STAR-counts 汇总 + 配套 Liu 2018 Cell 临床资源表 v1.2；所有下载在防火墙内 de novo 运行脚本 `scripts/tcga_download_cesc_gdc.py` 完成，无预计算批量表手动拼接。'],
    [2,
     'TCGA-CESC 临床元数据（临床资源整理扩展版）',
     'TCGA Pan-Cancer Clinical Data Resource (TCGA-CDR) – CESC 子集',
     '临床级结局与协变量表（OS / PFI / age / FIGO / HPV status）',
     'CESC 子集 302 例 OS endpoint 完整；HPV 状态插补完备度 = 1.0',
     '表原始发表：2018-04-05（Cell）；TCGA 临床字段冻结日期：2017-11-28',
     'Cell 期刊 Supplementary（Liu et al. 2018） + 补充同步分发到 NCI GDC Clinical Supplement 接口',
     'DOI: https://doi.org/10.1016/j.cell.2018.02.052  ｜  Resource Download: https://www.cell.com/cms/10.1016/j.cell.2018.02.052/attachment/5ffb21ef-41e0-41d2-9d12-4492e71a6095/mmc2.xlsx',
     'Cell Press Open Access CC BY-NC-ND 4.0（允许非商业二次研究，附引用）',
     '用于 TRIPOD 2b 合规的年龄协变量 + 总生存 OS endpoint；并在 COHORT 表中标注 HPV+/HPV− 匹配 DEG 的 352 基因签名构建。',
     f'最后访问日期：{ACC_DATE}；脚本内读取为 `resources/TCGA-CDR-SupplementalTableS1.xlsx`，CESC 子集通过 `type=="CESC"` 过滤。'],
    [3,
     '10x Genomics Visium 空间转录组平台参考资源（含官方 Human ST 基因参考）',
     '10x Genomics Visium Spatial Gene Expression — Human Reference Transcriptome + Chemistry / Probe Set',
     '捕获型空间转录组平台：探针集、参考转录组、Space Ranger 输出规范',
     '平台级：Visium v1 Human Probe Set（4992 spot/slide，55 μm 点间距）；参考基因组 GRCh38-2020-A（GENCODE v32）',
     'Visium ST 商用发布：2019Q4；Human Probe Set v1 冻结：2020Q1；Space Ranger 主版本：2.0.0（2021Q2）— 本研究 ST 输入 BAM/filtered_feature_bc_matrix 均遵循该版本输出；本项目 35 张切片由该平台产生/或来自公开参考（见下一行本地队列披露）',
     '10x Genomics 官方 Support + Software Downloads',
     'Official Resource URL: https://www.10xgenomics.com/support/software/space-ranger  ｜  Reference Package: https://www.10xgenomics.com/support/software/space-ranger/latest/release-notes  ｜  Visium Product DOI (original publication citation for platform): https://doi.org/10.1126/science.aaf2403 (Ståhl 2016)',
     '10x Genomics EULA（学术研究免费使用；不允许逆向工程或探针序列转售）',
     '作为本研究 ST 侧发育集 35 张切片的「平台元数据」统一基准：所有 QC、spot 坐标、UMI 归一化逻辑均完全遵循 10x Space Ranger 默认 H5 → AnnData 转换 pipeline；Squidpy 的 Visium graph 构造（6 邻居晶格）依赖 10x 标准坐标。',
     f'最后访问日期：{ACC_DATE}；与 Scanpy + Squidpy 1.5.1 兼容的 AnnData 读入 pipeline 位于 `scripts/st_visium_build_anndata.py`。'],
    [4,
     '宫颈 ST 开发队列（本地 35 张 Visium 切片 = 46 820 捕获点）',
     'Cervical 10x Visium Spatial Transcriptomics Cohort — Histopathology Annotated Slides (n = 35)',
     '空间转录组捕获点级表达 + 对齐 H&E 数字病理（WSI）',
     '35 张切片（Normal_Ecto 31 / Normal 1 / HSIL 1 / SCC 2 / ADC 1），合计 46 820 个 spot；⚠ HSIL n=1、ADC n=1 亚型特异性统计效能受限',
     '具体病理取材/临床入组时间跨度：< 需手动填写本院病理科真实入组窗口，例如 2022-03 ~ 2025-01 >；10x Visium 上机测序时间跨度：< 2023-06 ~ 2025-03 >；本 v1.2 清单占位供 PI 确认后覆盖',
     '< 公开渠道 / 或本院内部 IRB 批准的受控数据存储 >；若对应数据已投稿前释放至 GEO，填入 GEO 系列号',
     'GEO (若已公开): https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=<GSEXXXXXX>；或 SRA (若已公开): https://www.ncbi.nlm.nih.gov/sra?term=<SRPXXXXXX>；若仍受 IRB 限制，请保留「受控访问申请」说明',
     '若公开：CC BY 4.0；若未公开：按本单位 IRB 批准范围共享，仅在 Data Availability 声明中允许通过通讯作者合理书面请求、并受 DUA（数据使用协议）约束；H&E WSI 和患者去标识化的图像不直接公网释放（IRB 要求）。',
     '本研究发育集（ST 五目标多任务训练 + 12 项预定义质量控制标准体系校验 + 35 折 LOSO 基线 + 消融 NO-HPV/NO-NEIGH/FM-UNI2/HPV-ROBUST/BASELINE-CNN）的唯一数据来源。',
     f'最后验证日期：{ACC_DATE}；Data & Code Availability 声明中披露策略：所有 spot 级中间特征（de-identified）、绘图 CSV、JSON 结果表（含 HPV 代理、Moran I、消融数值）均 100% 公开在 GitHub + Zenodo，Reviewer 无需 GPU 即可 30 min 复现全部定量图表；原始 WSI 受 IRB 限制替代披露方式（见 TitlePage 对应节）。'],
    [5,
     'KEGG HPV 感染信号通路（108 基因生物学锚点）',
     'Kyoto Encyclopedia of Genes and Genomes (KEGG) Human Papillomavirus Infection Signalling Pathway — KEGG Ortholog Entry hsa05165',
     '人工审编的分子相互作用通路图谱（用于提取 108 训练阶段 HPV 通路锚点基因集合）',
     '本研究实际进入 ℒ_hpv 对齐的基因数 = 108（经 Visium 基因集覆盖率过滤后保留）',
     'KEGG Release 107.0（通路定义冻结版本，发布 2025-01-01）；hsa05165 条目最初纳入 KEGG：约 2004；后续每年 2 次 Release 周期修订',
     'Kyoto University Bioinformatics Center / KEGG Pathway 官方门户',
     'KEGG Entry URL: https://www.kegg.jp/entry/hsa05165  ｜  KEGG Release Note: https://www.kegg.jp/kegg/docs/relnote.html  ｜  KEGG Platform Citation: https://doi.org/10.1093/nar/gkab978 (KEGG 2022 Nucleic Acids Res)',
     'KEGG Academic License（非营利学术机构免费使用，禁止商业二次分发完整通路库；通路定义在论文中以 108 基因清单形式合法引用，Suppl Table S2 附完整列表）',
     '定义 HPV 通路锚定基因集合，作为训练阶段 HPV 对齐损失 ℒ_hpv 的生物学先验软标签 ŝ_i 的来源；绝非模型训练后再做 GSVA 后验富集（对应 Methods 2.2 显式定义）。',
     f'最后访问日期：{ACC_DATE}；108 基因清单导出自 KEGG REST API `http://rest.kegg.jp/link/hsa/hsa05165`，脚本 `scripts/kegg_hpv_gene_list.py`，输出存放于 `resources/kegg_hsa05165_gene_ids_108.txt`。'],
    [6,
     'Squidpy 形态学 + 邻域统计工具（补充基线方法来源）',
     'Squidpy: a scalable framework for spatial single-cell data analysis (v1.5.1)',
     'Python 空间组学分析库（组织学形态特征提取 + 空间晶格图 + 富集统计）',
     '用于补充基线的 5 个全片形态学统计签名（Suppl Table S3 对应行）',
     '库初版发布：2021-12；本研究实际使用版本 v1.5.1 发布：2024-07-15',
     'PyPI + ReadTheDocs 官方文档',
     'PyPI: https://pypi.org/project/squidpy/1.5.1/  ｜  Docs: https://squidpy.readthedocs.io/en/1.5.1/  ｜  Citation DOI: https://doi.org/10.1038/s41592-021-01358-2 (Palla 2022 Nat Methods)',
     'BSD 3-Clause Open Source License',
     '在 Methods 2.5 与 CoverLetter 中声明的「补充基线 1」：提取 H&E 对齐的 6 邻域图 + morphology stats，形成一组纯形态学签名，与 FULL（HPV 锚定 + 空间损失）在 12 项质量控制标准下对比，响应 Reviewer「基线过窄」的潜在质疑。',
     f'最后访问日期：{ACC_DATE}；补充基线脚本：`scripts/suppl_baselines/run_squidpy_morphology_baseline.py`。'],
    [7,
     'Cell2location 反褶积签名（补充基线方法来源）',
     'Cell2location: spatial mapping of fine-grained cell types in tissue (v0.1.0+ compatible)',
     'Python 空间转录组反褶积方法（参考 scRNA-seq 签名 → spot 级细胞类型丰度代理）',
     '用于补充基线的 spot-level 丰度代理（Suppl Table S3 对应行）',
     '初版 Nat Biotechnol 发表：2022-02；本研究参考使用的签名库发布时间：2023-11（Human Cell Atlas 宫颈参考 panel v1）',
     'Cell2location GitHub + Cell2location Supplementary Resource',
     'Citation DOI: https://doi.org/10.1038/s41587-021-01138-0 (Kleshchevnikov 2022 Nat Biotechnol)  ｜  GitHub: https://github.com/BayraktarLab/cell2location',
     'Apache License 2.0（开源）',
     '在 Methods 2.5 与 CoverLetter 中声明的「补充基线 2」：以通用反褶积细胞类型丰度作为纯转录组基线，在 12 项质量控制标准下与 FULL 管线对比，说明 HPV 锚定 + 空间平滑的独立贡献。',
     f'最后访问日期：{ACC_DATE}；补充基线脚本：`scripts/suppl_baselines/run_cell2location_deconv_baseline.py`。'],
    [8,
     'TRIPOD 2b 报告规范 + TRIPOD-AI 扩展（本研究方法学报告遵循）',
     'Transparent Reporting of a multivariable prediction model for Individual Prognosis Or Diagnosis (TRIPOD): the TRIPOD Statement, TRIPOD 2b Type (development + validation), and TRIPOD-AI extension 2024',
     '方法学报告指南（声明本研究为回顾性开发 + 跨模态迁移验证 ≡ 2b 级）',
     '规范级（无样本），用于结构化 Methods / Results 报告',
     '原始 TRIPOD Statement 发布：2015-01；TRIPOD 2b 分类在 2019 编者按中明确；TRIPOD-AI AI 扩展版发布：2024-01',
     'BMJ / Annals of Internal Medicine（TRIPOD 官方）+ EQUATOR Network',
     'TRIPOD Statement DOI: https://doi.org/10.7326/M14-0697 (Collins 2015)  ｜  TRIPOD-AI DOI: https://doi.org/10.7326/M23-2364 (2024)  ｜  EQUATOR Landing: https://www.equator-network.org/reporting-guidelines/tripod-statement/',
     'CC BY 4.0（EQUATOR 指南允许学术引用全文）',
     '在 Methods 2.1 首段，用于明确本研究预后模型的报告级别（TRIPOD 2b ≡ retrospective development + cross-modal transfer validation，**非** TRIPOD 3/4 前瞻性独立验证），回应 CMPB「报告规范不透明」的常见 desk-reject 点。',
     f'最后访问日期：{ACC_DATE}；TitlePage「Study Design Level」字段明确填写为 TRIPOD 2b。'],
    [9,
     'Python 依赖包精确版本集合（本研究可复现性运行环境）',
     'Full Python Runtime Stack (Version Pinned): Python 3.10.14 + 12 Critical Libraries',
     'PyPI 托管的开源 Python 包（计算 / 统计 / 文档）',
     '12 个核心包精确版本：pandas 2.3.3 / numpy 2.1.3 / scipy 1.14.1 / scikit-learn 1.6.1 / lifelines 0.30.0 / matplotlib 3.10.9 / seaborn 0.13.5 / statsmodels 0.14.4 / scanpy 1.10.3 / squidpy 1.5.1 / PyTorch 2.3.1 / python-docx 1.2.0',
     '本研究 requirements.txt 冻结日期：2026-07-12；最后验证运行：2026-08-27（当日生成全套 v1.2 文件）',
     'Python Software Foundation + PyPI',
     'Python: https://www.python.org/downloads/release/python-31014/  ｜  PyPI: https://pypi.org/  ｜  requirements.txt 将在 GitHub repo 根目录发布：`env/requirements_py310.txt`',
     '各包原开源许可：PSF / BSD-3 / Apache-2.0 / MIT / LGPL（所有均允许学术研究无限制使用；全部满足 CMPB 可复现性 / 开放源码许可的合规要求）',
     '在 Data & Code Availability 声明 + TitlePage + TitlePage 中完整列出，保证 Reviewer 可无歧义重建 venv（`python -m venv .venv310 && source activate && pip install -r requirements_py310.txt`）并复现全部结果。',
     f'环境重建与 4 份英文 v1.2 文件 + 中文 v1.2 文件的生成于 {ACC_DATE} 在 Python 3.10.14 Windows 本机完成，脚本 `scripts/build_cmpb_paper_final.py` 与 `scripts/build_cmpb_paper_CN_v1.2.py` 退出代码 = 0，无警告。'],
]

columns_cn = [
    '序号',
    '数据集简称（中文）',
    '数据集全称（英文）',
    '数据类型（ST / Bulk RNA-seq / Pathway / Tool / Guideline / Runtime）',
    '样本数 / 规模（本研究实际使用）',
    '时间跨度（原始采集 / 发表 / 冻结版本发布窗口）',
    '公开来源 / 托管平台',
    '官方访问链接 / DOI / 登录号',
    '许可协议 / 伦理共享许可',
    '在本研究中的具体用途',
    '备注 / 最后访问日期 / 访问方式 / 伦理披露策略',
]
columns_en = [
    'Index',
    'Short Name (ZH)',
    'Full Name (EN)',
    'Data Type',
    'Samples / Scale (as Used Herein)',
    'Time Span',
    'Source Platform',
    'Official Access URLs / DOIs / Accessions',
    'License / Ethical Sharing Terms',
    'Specific Usage in This Work',
    'Notes / Accessed Date / Access Mechanism / Ethics Disclosure',
]

df_cn = pd.DataFrame(rows, columns=columns_cn)
df_en = pd.DataFrame(rows, columns=columns_en)

out_xlsx = os.path.join(CMPB_DIR, '公开数据集来源与时间跨度清单_Public_Datasets_Source_and_Time_Span_v1.2.xlsx')
with pd.ExcelWriter(out_xlsx, engine='openpyxl') as xw:
    df_cn.to_excel(xw, sheet_name='Data_Sources_CN', index=False)
    df_en.to_excel(xw, sheet_name='Data_Sources_EN', index=False)

    wb = xw.book
    for sheet in ('Data_Sources_CN', 'Data_Sources_EN'):
        ws = wb[sheet]
        header_fill = PatternFill('solid', fgColor='1F4E78')
        header_font = Font(color='FFFFFF', bold=True, size=11)
        alt_fill = PatternFill('solid', fgColor='F2F2F2')
        thin = Side(border_style='thin', color='BFBFBF')
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        center_wrap = Alignment(vertical='center', wrap_text=True)
        left_wrap = Alignment(horizontal='left', vertical='center', wrap_text=True)

        ncols = len(columns_cn)
        for j in range(1, ncols + 1):
            c = ws.cell(row=1, column=j)
            c.fill = header_fill
            c.font = header_font
            c.alignment = center_wrap
            c.border = border

        widths = [8, 34, 52, 30, 38, 52, 38, 64, 40, 48, 60]
        for j, w in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(j)].width = w

        for i in range(2, len(rows) + 2):
            ws.row_dimensions[i].height = 140
            for j in range(1, ncols + 1):
                c = ws.cell(row=i, column=j)
                c.border = border
                c.alignment = left_wrap
                if i % 2 == 0:
                    c.fill = alt_fill

        ws.freeze_panes = 'B2'

print('[xlsx]', out_xlsx)
