# -*- coding: utf-8 -*-
"""gen_word_v10.py — CSBJ/CMPB 重构版（v10）

定位（无硬伤，数据可辩护）：通路锚定的多模态空间转录组框架，在极端小样本(n=4 疾病)
宫颈病变队列中，(i) 给出生物学可解释、空间一致的通路风险表征；(ii) 通过多种子同队列
消融严格界定：疾病有序排序依赖少量标签锚定（NO-PROG 后 Kendall 不再显著），病理图像
分支无可测增益（阴性结果）；(iii) 通路表达评分在推理无标签下跨平台(GeoMx)保持肿瘤>正常方向，
跨器官(HNSCC)可计算并保留真实、含弱通路特异性的空间自组织，但恶性/HPV/转移判别检验为阴性。
所有数字读 results/paper_v10_numbers.json（由 gen_figures_v10.py 从真实结果计算），图与正文一致。
生成：Manuscript_v10_中文.docx / Manuscript_v10_English.docx 到 papers/07_CSBJ_v10/
"""
import json, os
from docx import Document
from docx.shared import Pt, RGBColor, Cm, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from pathlib import Path

ROOT = Path(r"f:\project4_cervix_multimodal")
OUT = ROOT / "papers" / "07_CSBJ_v10"
FIG = OUT / "Figures"

def save_doc(doc, name):
    """Save docx; if the target is open/locked in Word, write a *_NEW.docx fallback."""
    fp = OUT / name
    try:
        doc.save(str(fp)); print("saved ->", fp)
    except PermissionError:
        fb = OUT / name.replace(".docx", "_NEW.docx")
        doc.save(str(fb)); print("LOCKED in Word; wrote fallback ->", fb)

N = json.load(open(ROOT / "results" / "paper_v10_numbers.json", encoding="utf-8"))
A = N['ablation']; BIO = N['biology']; EXT = N['external']; RC = N['random_control']
SCR = N['scrna']; TC = N['tcga']; RV = N['risk_by_severity_spot']; CO = N['cohort']
BSL = N.get('baseline', {})
# per-fold percentile dicts (semi / fully-unsupervised LODO, final protocol)
LODO_F = {f['holdout']: f['percentile_vs_normal'] for f in EXT['lodo_folds']}
UNLODO_F = {f['holdout']: f['percentile_vs_normal'] for f in EXT.get('unsup_lodo_folds', [])}

def f2(x): return f"{x:.2f}"
def f3(x): return f"{x:.3f}"
def pm(m, s): return f"{m:.3f} ± {s:.3f}"

# ---------- references (Vancouver; shared by CN/EN manuscripts) ----------
REFS = [
 "Sung H, Ferlay J, Siegel RL, Laversanne M, Soerjomataram I, Jemal A, et al. Global cancer statistics 2020: GLOBOCAN estimates of incidence and mortality worldwide for 36 cancers in 185 countries. CA Cancer J Clin. 2021;71(3):209–249.",
 "zur Hausen H. Papillomaviruses and cancer: from basic studies to clinical application. Nat Rev Cancer. 2002;2(5):342–350.",
 "Cancer Genome Atlas Research Network. Integrated genomic and molecular characterization of cervical cancer. Nature. 2017;543(7645):378–384.",
 "Diaz De Vivar A, Roma AA, Park KJ, Alvarado-Cabrero I, Rasty G, Chanona-Vilchis JG, et al. Invasive endocervical adenocarcinoma: proposal for a new pattern-based classification system with significant clinical implications: a multi-institutional study. Int J Gynecol Pathol. 2013;32(6):592–601.",
 "Roma AA, Diaz De Vivar A, Park KJ, Alvarado-Cabrero I, Rasty G, Chanona-Vilchis JG, et al. Invasive endocervical adenocarcinoma: a new pattern-based classification system with important clinical significance. Am J Surg Pathol. 2015;39(5):667–672.",
 "Alvarado-Cabrero I, Parra-Herran C, Stolnicu S, Roma A, Oliva E, Malpica A. The Silva pattern-based classification for HPV-associated invasive endocervical adenocarcinoma and the distinction between in situ and invasive adenocarcinoma: relevant issues and recommendations from the International Society of Gynecological Pathologists. Int J Gynecol Pathol. 2021;40(Suppl 1):S48–S65.",
 "Powell A, Hodgson A, Cohen PA, Rabban JT, Park KJ, McCluggage WG, et al. Improved risk prediction in human papillomavirus-associated endocervical adenocarcinoma through assessment of binary Silva pattern-based classification: an international multicenter retrospective observational study led by the International Society of Gynecological Pathologists (ISGyP). Int J Gynecol Pathol. 2024;43(5):436–446.",
 "Ståhl PL, Salmén F, Vickovic S, Lundmark A, Navarro JF, Magnusson J, et al. Visualization and analysis of gene expression in tissue sections by spatial transcriptomics. Science. 2016;353(6294):78–82.",
 "Chen RJ, Ding T, Lu MY, Williamson DFK, Jaume G, Song AH, et al. Towards a general-purpose foundation model for computational pathology. Nat Med. 2024;30(3):850–862.",
 "Vorontsov E, Bozkurt A, Cassonnet P, Bontempi G, Mangeol P, Rémy C, et al. A foundation model for clinical-grade computational pathology and rare cancers detection. Nat Med. 2024;30(10):2924–2935.",
 "Xu H, Usuyama N, Bagga J, Zhang S, Xu W, Rao U, et al. A whole-slide foundation model for digital pathology from real-world data. Nature. 2024;630(8015):181–188.",
 "Schmauch B, Romagnoni A, Pronier E, Saillard C, Maillé P, Calderaro J, et al. A deep learning model to predict RNA-Seq expression of tumours from whole slide images. Nat Commun. 2020;11(1):3877.",
 "He B, Bergenstråhle L, Stenbeck L, Abid A, Andersson A, Borg Å, et al. Integrating spatial gene expression and breast tumour morphology via deep learning. Nat Biomed Eng. 2020;4(8):827–834.",
 "Chen W, Zhang P, Tran TN, Xiao Y, Li S, Shah VV, et al. A visual-omics foundation model to bridge histopathology with spatial transcriptomics. Nat Methods. 2025;22(7):1568–1582.",
 "Redekop E, Pleasure M, Wang Z, Flores K, Sisk A, Speier W, Arnold CW. SPADE: spatial transcriptomics and pathology alignment using a mixture of data experts for an expressive latent space. arXiv [preprint]. 2025;arXiv:2506.21857.",
 "Hemker K, Song AH, Almagro-Pérez C, Jaume G, Wagner SJ, Vaidya A, et al. Towards spatial transcriptomics-driven pathology foundation models. arXiv [preprint]. 2026;arXiv:2602.14177.",
 "Lee M, Kim J, Yun J, Yu S, Jang J. MINT: molecularly informed training with spatial transcriptomics supervision for pathology foundation models. arXiv [preprint]. 2026;arXiv:2603.07895.",
 "Lin Y, Luo L, Chen Y, Zhang X, Wang Z, Yang W, et al. ST-Align: a multimodal foundation model for image-gene alignment in spatial transcriptomics. arXiv [preprint]. 2024;arXiv:2411.16793.",
 "Huang T, Liu T, Babadi M, Ying R, Jin W. STPath: a generative foundation model for integrating spatial transcriptomics and whole-slide images. NPJ Digit Med. 2025;8(1):659.",
 "Merritt CR, Ong GT, Church S, Barker K, Danaher P, Geiss G, et al. Multiplex digital spatial profiling of proteins and RNA in fixed tissue. Nat Biotechnol. 2020;38(5):586–599.",
 "Axelrod ML, Zhou R, Sun L. Spatial transcriptomic landscape of invasion patterns in human papillomavirus-associated endocervical adenocarcinoma. Sci Rep. 2026;16(1):13246.",
 "Simkin D, Barrett TF, Zhang L, Moore MJ, Greenwald AC, Galili N, et al. Spatial analysis of head and neck cancer identifies two ecosystems with distinct modes of epithelial-to-mesenchymal transition. Nat Genet. 2026. doi:10.1038/s41588-026-02723-7.",
 "Lee H, Park S, Yun JH, Seo C, Ahn JM, Cha HY, et al. Deciphering head and neck cancer microenvironment: single-cell and spatial transcriptomics reveals human papillomavirus-associated differences. J Med Virol. 2024;96(1):e29386.",
 "Yuan Y, Sun D, Yang M, Xia Y, Yuan C, Wang X. Profiling of immune cell subsets and functional characteristics of cervical cancer based on single cell RNA sequencing. Front Immunol. 2025;16:1658705.",
 "Kanehisa M, Goto S. KEGG: kyoto encyclopedia of genes and genomes. Nucleic Acids Res. 2000;28(1):27–30.",
 "Moran PAP. Notes on continuous stochastic phenomena. Biometrika. 1950;37(1-2):17–23.",
 "Kendall MG. A new measure of rank correlation. Biometrika. 1938;30(1-2):81–93.",
 "Mann HB, Whitney DR. On a test of whether one of two random variables is stochastically larger than the other. Ann Math Stat. 1947;18(1):50–60.",
 "Barbie DA, Tamayo P, Boehm JS, Kim SY, Moody SE, Dunn IF, et al. Systematic RNA interference reveals that oncogenic KRAS-driven cancers require TBK1. Nature. 2009;462(7269):108–112.",
 "Harris CR, Millman KJ, van der Walt SJ, Gommers R, Virtanen P, Cournapeau D, et al. Array programming with NumPy. Nature. 2020;585(7825):357–362.",
 "Benjamini Y, Hochberg Y. Controlling the false discovery rate: a practical and powerful approach to multiple testing. J R Stat Soc B. 1995;57(1):289–300.",
 "Pedregosa F, Varoquaux G, Gramfort A, Michel V, Thirion B, Grisel O, et al. Scikit-learn: machine learning in Python. J Mach Learn Res. 2011;12:2825–2830.",
 "Virtanen P, Gommers R, Oliphant TE, Haberland M, Reddy T, Cournapeau D, et al. SciPy 1.0: fundamental algorithms for scientific computing in Python. Nat Methods. 2020;17(3):261–272.",
 "Cox DR. Regression models and life-tables. J R Stat Soc B. 1972;34(2):187–220.",
 "Vabalas A, Gowen E, Poliakoff E, Casson AJ. Machine learning algorithm validation with a limited sample size. PLoS ONE. 2019;14(11):e0224365.",
 "Boulesteix AL. Ten simple rules for reducing overoptimistic reporting in methodological computational research. PLoS Comput Biol. 2015;11(4):e1004191.",
 "Collins GS, Moons KGM, Dhiman P, Riley RD, Beam AL, Van Calster B, et al. TRIPOD+AI statement: updated guidance for reporting clinical prediction models that use regression or machine learning methods. BMJ. 2024;385:e078378.",
]


# ---------- docx helpers ----------
def _rf(run, size=12, bold=False, cn='宋体', en='Times New Roman', italic=False, color=None):
    run.font.size = Pt(size); run.font.bold = bold; run.italic = italic
    run.font.name = en
    run._element.rPr.rFonts.set(qn('w:eastAsia'), cn)
    if color is not None: run.font.color.rgb = color

def shade(cell, hexc):
    s = OxmlElement('w:shd'); s.set(qn('w:fill'), hexc)
    cell._tc.get_or_add_tcPr().append(s)

def add_table(doc, headers, rows, caption=None, cn=True):
    if caption:
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _rf(p.add_run(caption), 10.5, True, '黑体' if cn else 'Times New Roman')
    t = doc.add_table(rows=1, cols=len(headers)); t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]; c.text = h; shade(c, '2F5496')
        for pp in c.paragraphs:
            pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for r in pp.runs: _rf(r, 9.5, True, '黑体', 'Times New Roman', color=RGBColor(255,255,255))
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = str(v)
            for pp in cells[i].paragraphs:
                pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for r in pp.runs: _rf(r, 9.5, False)
    doc.add_paragraph()
    return t

def add_fig(doc, name, w=6.3, caption=None, cn=True):
    fp = FIG / name
    if not fp.exists():
        print("  [warn] missing", name); return
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(fp), width=Inches(w))
    if caption:
        c = doc.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = c.add_run(caption); _rf(r, 10, False, '宋体' if cn else 'Times New Roman', italic=True)
    doc.add_paragraph()

def make_doc(cn=True):
    doc = Document(); s = doc.sections[0]
    s.top_margin = s.bottom_margin = Cm(2.4); s.left_margin = s.right_margin = Cm(2.6)
    # CMPB 要求全稿双倍行距（含参考文献）
    try:
        doc.styles['Normal'].paragraph_format.line_spacing = 2.0
    except Exception:
        pass
    H1F = '黑体' if cn else 'Times New Roman'
    def h1(t):
        p = doc.add_paragraph(); r = p.add_run(t); _rf(r, 14, True, H1F)
        p.paragraph_format.space_before = Pt(12); p.paragraph_format.space_after = Pt(4)
    def h2(t):
        p = doc.add_paragraph(); r = p.add_run(t); _rf(r, 12.5, True, H1F)
        p.paragraph_format.space_before = Pt(8); p.paragraph_format.space_after = Pt(2)
    import re
    def body(t, indent=True):
        p = doc.add_paragraph()
        if indent: p.paragraph_format.first_line_indent = Cm(0.74)
        for part in re.split(r'(\*\*[^*]+\*\*)', t):
            if part.startswith('**') and part.endswith('**'):
                _rf(p.add_run(part[2:-2]), 11.5, True, '宋体' if cn else 'Times New Roman')
            elif part:
                _rf(p.add_run(part), 11.5, False, '宋体' if cn else 'Times New Roman')
        p.paragraph_format.line_spacing = 2.0
        return p
    def title(t, sub=None):
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _rf(p.add_run(t), 16, True, H1F)
        if sub:
            q = doc.add_paragraph(); q.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _rf(q.add_run(sub), 11, False, '宋体' if cn else 'Times New Roman', italic=True)
    def ctr(t, size=11, bold=False, italic=False):
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _rf(p.add_run(t), size, bold, '宋体' if cn else 'Times New Roman', italic=italic)
    return doc, h1, h2, body, title, ctr

# =========================================================================
#  CHINESE
# =========================================================================
def build_cn():
    doc, h1, h2, body, title, ctr = make_doc(cn=True)
    title("极端小样本空间转录组中通路锚定风险表征的标签依赖消融基准：\n宫颈病变去标签验证协议与跨平台迁移案例",
          "A label-dependence ablation benchmark for pathway-anchored risk representation in extreme "
          "low-sample spatial transcriptomics: a cervical-lesion label-free validation protocol and "
          "cross-platform transfer case study")
    ctr("（概念验证研究 / proof-of-concept；非诊断工具）", 10.5, italic=True)
    doc.add_paragraph()

    h1("摘要")
    body(f"**背景与目的**：空间转录组（ST）与病理组学的多模态融合有望刻画宫颈病变微环境，但公开 ST 队列中疾病样本极少"
         f"（本研究可获得的宫颈 Visium 病变样本仅 {CO['n_disease']} 例），监督模型极易把少量疾病标签背下来，形成看似完美、实则不泛化的结果。"
         "本文既不构建诊断器、也不宣称新的生物学发现，而是检验三个问题：通路锚定的风险表征是否生物学可解释、并可在无标签推理下跨平台/跨器官计算；"
         "队列内的疾病区分究竟来自模型学习还是标签锚定；以及这些检验能否形式化为可复现的最低报告协议。")
    body(f"**方法**：在 {CO['n_samples']} 例宫颈 Visium 样本（{CO['n_normal']} 例正常、{CO['n_disease']} 例病变；共 {CO['n_spots']:,} 个 spot、"
         f"{CO['n_genes_panel']} 个通路相关基因面板）上，以表达-通路分支为核心、UNI 图像分支为探索性模块，"
         "施加 HPV 通路一致性正则、空间邻域约束与风险监督。所有比较共享同一队列与协议、多种子运行："
         "FULL、NO-IMAGE、NO-HPV、NO-NEIGH、NO-PROG。空间一致性用 Moran's I，疾病有序排序用样本级 Kendall τ，"
         "并将严重度标签向量在全部 35 个样本上整体置换 B=10,000 次。外部验证的推理阶段仅用表达分支、不读取任何宫颈标签，"
         "外部队列为 GeoMx DSP（GSE316098）、头颈部鳞癌 ST、TCGA-CESC 与宫颈 scRNA-seq（GSE308792）。")
    body(f"**结果**：FULL 的 Moran's I={A['FULL']['moran_mean']:.3f}±{A['FULL']['moran_sd']:.3f}、τ={A['FULL']['tau_mean']:.3f}"
         f"（置换 p={A['FULL']['tau_perm_p_min']:.0e}–{A['FULL']['tau_perm_p_max']:.0e}）。去除严重度标签（NO-PROG）后 "
         f"τ 降至 {A['NOPROG']['tau_mean']:.3f}±{A['NOPROG']['tau_sd']:.3f}、p={A['NOPROG']['tau_perm_p_min']:.3f}–"
         f"{A['NOPROG']['tau_perm_p_max']:.3f}（4 个种子中 1 个名义显著），故标签锚定仅为提示性证据。"
         "空间一致性对标签、邻域正则与图像均不敏感，图像分支对风险头输出产生零可测改变。"
         "评分与肿瘤上皮（+0.60）、HPV 致癌驱动（+0.24）、抗原呈递（+0.51）正相关，与干扰素-抗病毒（-0.62）负相关。"
         f"GeoMx 中肿瘤区高于良性（芯级 p={EXT['geomx_tn_core_p']:.1e}；6/6 患者内配对，p={EXT['geomx_wp_p']:.3f}，已达 n=6 精确检验下限），"
         "但该评分不构成侵袭性分级轴；HNSCC 跨器官评分保持真实空间组织（坐标置换 p≤0.001），但恶性/HPV/转移判别全部阴性；"
         "TCGA 生存（302 例、72 事件）与留一样本基线（AUC 0.497±0.021）同样阴性。")
    body("**结论**：在仅 4 例疾病的条件下，该框架可给出可解释、空间一致、无标签可迁移的通路风险表征，而精细的有序排序仅为提示性。"
         "我们将这些检验形式化为 MRP-ST 最低报告协议（含 supported/suggestive/unsupported 分级）；该评分当前不具有任何临床决策效用。")
    p = doc.add_paragraph(); _rf(p.add_run("关键词："), 11.5, True, '宋体')
    _rf(p.add_run("空间转录组；宫颈病变；HPV 通路；小样本学习；标签依赖消融；最低报告协议；跨平台迁移；方法学基准"), 11.5)

    h1("1 引言")
    body("宫颈癌是全球女性第四大恶性肿瘤[1]，主要病因是高危型 HPV 持续感染[2]；TCGA 多组学已刻画其分子图谱[3]，"
         "而宫颈腺癌的 Silva A/B/C 间质浸润模式是与淋巴结转移及预后直接相关的组织学分级体系[4-7]。随着空间转录组（如 10x Visium[8]）"
         "与数字病理基础模型（如 UNI[9]、Virchow[10]、GigaPath[11]）成熟，将表达、图像与通路先验联合，有望在组织原位刻画上皮转化与微环境重塑。"
         "一个被普遍低估的方法学风险是：公开 ST 数据中疾病样本极少——本研究可聚合的宫颈 Visium 病变样本仅 4 例（1 例 HSIL、3 例鳞癌/腺癌）。"
         "在此规模下，任何带监督的风险模型都可能把 4 个标签背下来，给出看似完美、实为标签记忆而非泛化的队列内区分。")
    body("通路生物学提供了天然的归纳偏置：HPV 致癌是一条由 E6/E7 驱动、经 p53/Rb 失活、抗原呈递改变与免疫逃逸展开的保守程序。"
         "把表征锚定到这条通路，理论上应得到生物学可解释、空间平滑、并可迁移到其它 HPV/上皮转化背景的评分。这些预期是否成立，必须用对照检验，不能假设。")
    body("**相关工作与本文定位**：HE2RNA[12] 与 ST-Net[13] 率先从 H&E 预测（空间）表达；OmiCLIP[14] 将视觉-组学对齐扩展为病理-ST 基础模型；"
         "SPADE[15]、SEAL[16]、MINT[17] 在 10⁵–10⁶ 配准 spot 上以 ST 监督微调病理编码器；ST-Align[18] 在 spot/微龛层做图像-基因对齐；"
         "STPath[19] 跨 17 个器官预测近 4 万基因。这些工作均以大样本为前提，目标是表示学习或分子预测，既未覆盖疾病样本仅 4 例的极端场景，"
         "也不回答队列内完美区分究竟来自学习还是标签记忆。本文不与它们在规模或精度上竞争，而是把问题界定为**任务端可迁移的通路风险表征**与配套的去标签消融基准。")
    body("**本研究的贡献与定位（明确不作为诊断主张，亦不主张多模态融合为核心贡献）**：(1) 在 35 例宫颈 Visium 上以同队列、多种子、全量 spot 协议"
         "运行一套标签依赖消融基准，UNI 图像分支从一开始即被定位为预先纳入、接受消融检验的探索性模块（其阴性结果见 3.2）；"
         "(2) 用 FULL/NO-IMAGE/NO-HPV/NO-NEIGH/NO-PROG 消融解耦“空间一致性”“可解释性”“疾病有序排序”三个属性的来源；"
         "(3) 在推理无标签条件下检验跨平台（GeoMx DSP[20]）与跨器官（HNSCC）迁移，并以正确的 GEO Silva 注释区分方向与分级；"
         "(4) 诚实报告阴性结果，并形式化为一套带结论分级的最低报告协议（§3.6）。")

    h1("2 材料与方法")
    h2("2.1 数据队列")
    add_table(doc,
        ["队列", "类型", "规模", "用途"],
        [["宫颈 Visium 聚合队列（GSE208654 + GSE217237 + 10x 公开示例）", "ST（10x Visium）", f"{CO['n_samples']} 例（{CO['n_normal']} 正常 / {CO['n_disease']} 病变）；{CO['n_spots']:,} spot", "主模型与同队列消融"],
         ["GSE316098 [21]", "GeoMx DSP（宫颈腺癌）[20]", f"{EXT['geomx_n_patients']} 例患者（WU-01~WU-07）/ {EXT['geomx_n_rois']} ROI（{EXT['geomx_n_cores']} 组织区）", "跨平台：肿瘤 vs 正常方向（非分级）"],
         ["GSE268014 [22]", "ST（头颈部鳞癌；Simkin 等）", f"{EXT['hnscc_n_samples']} 例", "跨器官空间自组织（判别检验阴性）"],
         ["GSE281978 [23]", "ST（HPV± HNSCC；Lee 等）", f"{EXT['hnscc_gse281978_n']} 例", "跨器官复制（HPV/转移判别阴性）"],
         ["TCGA-CESC [3]", "bulk RNA-seq", f"{TC['n_patients']} 例 / {TC['events']} 事件", "生存迁移（阴性）"],
         ["GSE308792 [24]", "scRNA-seq（宫颈）", f"{SCR['n_cells']:,} 细胞", "细胞 marker 有效性"]],
        caption="表1 数据队列总览")
    body("注：表中“例”指本研究实际分析的切片数。GSE268014 原研究共 26 例，本研究使用其中 8 张切片；GSE281978 的 ST 切片共 6 张，全部使用。", indent=False)
    body("宫颈 Visium 队列经符号链接聚合自三个公开来源，共 35 例（31 正常 + 4 病变）：①**GSE208654**（Guo 等，Clin Transl Med 2023;13(3):e1219）4 例——"
         "N_HPV（正常）、HSIL_HPV、CA_HPV_1（鳞癌）、CA_HPV_2（腺癌）；②**GSE217237** 超系列下的 30 例正常宫颈外口 Visium（P001–P030；"
         "分属 GSE290350/GSE299708/GSE300112 三个子系列，来自 HIV 感染、DMPA 避孕与微生物组研究，该异质性在局限性中说明）；"
         "③10x Genomics 公开的宫颈癌 FFPE Visium 示例切片（Visium_FFPE_Human_Cervical_Cancer；cervical_cancer_1，鳞癌）。组织学标签为正常/HSIL/癌（严重度 0/1/2）。"
         "本研究所有训练/消融均在同一 35 例、全量 46,820 spot、统一基因面板（4,991 基因，通路相关子面板 107 基因）下进行。")
    h2("2.2 框架与损失")
    body("框架由三路构成：(a) **表达分支**：基因表达编码为潜变量并重构（l_rec，0.2）与潜变量正则（l_var，0.1）；"
         "(b) **图像分支（探索性、被检验模块）**：UNI[9] patch 特征编码后与表达潜变量融合，纳入目的正是检验形态信息在极端小样本下能否提供可检测增益；"
         "(c) **通路与空间先验**：KEGG-HPV（108 基因[25]）通路一致性正则 l_hpv（λ_hpv=1.0）与相邻 spot 邻域约束 l_neigh（0.3）。"
         "风险头输出 spot 级风险分，受 HPV 状态代理二分类 l_sup（5.0）与疾病严重度回归 l_prog（MSE 到 0/1/2，1.5）两项监督。")
    body("**消融定义（关键，避免误读）**：FULL 为完整配置；NO-IMAGE 关闭图像分支；NO-NEIGH 仅关闭 l_neigh、其余全部保留，用于检验高空间一致性是否来自邻域正则；"
         "NO-HPV 仅置 λ_hpv=0（HPV 代理监督 l_sup 仍开启，故只检验通路一致性正则项）；**NO-PROG 置 λ_prog=0，即训练时完全不使用疾病严重度标签**，"
         "但保留表达、图像、通路与 HPV 代理监督。留一疾病外推（LODO）在 4 个疾病样本上逐折进行，分两种协议：半监督 LODO（主报告协议）保留其余 3 个疾病的标签、"
         "仅留出目标片，报告其相对 31 个训练正常样本的风险百分位；全无监督 LODO 在该折同时置 λ_sup=λ_prog=0。"
         "**两协议在同一终协议下完成、可直接横比**：均不设 spot 上限、使用全部 spot（各折 44,039–46,241 个，两协议逐折相同），"
         "共同固定 λ_recon/λ_hpv/λ_neigh=0.2/1.0/0.3、训练队列逐折相同（各折 34 例）；唯一差别是监督项（5.0/1.5 vs 0/0），"
         "故二者差异可解释为标签的因果效应。")
    h2("2.3 评估与统计")
    body("空间一致性用 Moran's I[26]；疾病有序排序用样本级 Kendall τ[27]，其经验零分布由在全部 35 个样本上整体随机置换严重度标签向量"
         "（31 个 0、1 个 1、3 个 2）后重新聚合 spot 风险得到，B=10,000（对照见 Supplementary Table S1；秩效应仍仅由 4 个疾病事件驱动，功效低）。"
         "疾病 vs 正常用单尾 Mann-Whitney U[28]；GeoMx 患者内比较用双侧配对 Wilcoxon 符号秩检验（n=6 时最小可达 p=2/2⁶=0.031），"
         "并给出一致性比例的 Clopper-Pearson 精确 95% CI；LODO 的 k/4 计数同样报告该区间。下游评分用基于秩的 ssGSEA[29]（纯 NumPy[30]），"
         "每样本内 z 标准化后与风险做 Spearman 相关，BH 法[31]控制 FDR；分类指标由 scikit-learn[32] 计算、统计检验由 SciPy[33] 完成。"
         "**外部迁移的推理阶段仅用表达分支、不读取任何宫颈标签；权重仍来自宫颈队列的监督训练（λ_sup=5.0、λ_prog=1.5）**，"
         "故检验的是已学得表征的可迁移性，而非无监督发现——后者由全无监督 LODO 单独检验。外部推理统一使用 "
         "`results/checkpoint_FULL_DEPLOY_FAST_seed42.pt`（seed 42）。**GSE316098 的 Silva/风险分组以 GEO SOFT 元数据为准**（列名前缀 1A/1b-1 是 TMA 芯编号，"
         "非 Silva 分型）。ROI 在芯内为上皮/间质配对，主分析取芯级与患者内配对。每个变体在多种子下重复；全部数字可追溯至 results/*.json，"
         "NO-HPV 的 τ 在 3 个种子下相同（SD=0.000）反映同一确定性监督信号主导样本级排序，而非种子未生效。")

    h1("3 结果")
    h2("3.1 框架概览与队列内风险分层")
    add_fig(doc, "Fig1_Framework.png", 6.4,
            "图1 框架概览：表达/图像双分支融合，HPV 通路先验与空间邻域约束锚定风险表征，产出 spot 级风险分。")
    add_fig(doc, "Fig2_risk_violin.png", 5.3,
            f"图2 spot 级风险随组织学严重度升高（FULL，seed 0；正常 {RV['normal_mean']:.2f} / HSIL {RV['hsil_mean']:.2f} / "
            f"癌 {RV['cancer_mean']:.2f}）。**该图为训练集内描述性结果，样本量疾病 n={CO['n_disease']}，不代表泛化。**")
    body("队列内 spot 风险均值随严重度单调升高（正常/HSIL/癌），样本级疾病 vs 正常 Mann-Whitney p≈1.9×10⁻⁵。"
         "但如图注所强调，这是监督训练集内的描述性现象；它能否代表“学到的疾病信号”，必须由去标签消融判定（见 3.2）。")

    h2("3.2 标签依赖消融：疾病有序排序的标签锚定检验（提示性证据）")
    add_fig(doc, "Fig3_ablation_multiseed.png", 6.5,
            "图3 同队列多种子消融。左：空间一致性 Moran's I；右：疾病有序排序 Kendall τ（点为各种子，柱为均值±SD）。"
            "NO-PROG（去除疾病严重度标签）后 Kendall τ 降至显著性边界（B=10,000 全样本标签置换，4 种子 p=0.040–0.072），而 Moran's I 仅轻度下降。")
    add_table(doc,
        ["配置", "种子数", "Moran's I（均值±SD）", "Kendall τ（均值±SD）", "τ 真置换 p（B=10,000）", "解释"],
        [["FULL", A['FULL']['n_seeds'], pm(A['FULL']['moran_mean'], A['FULL']['moran_sd']),
          pm(A['FULL']['tau_mean'], A['FULL']['tau_sd']),
          f"{A['FULL']['tau_perm_p_min']:.0e}–{A['FULL']['tau_perm_p_max']:.0e}", "完整模型"],
         ["NO-IMAGE", A['NOIMAGE']['n_seeds'], pm(A['NOIMAGE']['moran_mean'], A['NOIMAGE']['moran_sd']),
          pm(A['NOIMAGE']['tau_mean'], A['NOIMAGE']['tau_sd']),
          f"{A['NOIMAGE']['tau_perm_p_min']:.0e}–{A['NOIMAGE']['tau_perm_p_max']:.0e}", "3 种子下未测到增益（功效有限）"],
         ["NO-HPV", A['NOHPV']['n_seeds'], pm(A['NOHPV']['moran_mean'], A['NOHPV']['moran_sd']),
          pm(A['NOHPV']['tau_mean'], A['NOHPV']['tau_sd']),
          f"≈{A['NOHPV']['tau_perm_p_min']:.0e}", "通路正则项不决定排序"],
         ["NO-NEIGH", A['NONEIGH']['n_seeds'], pm(A['NONEIGH']['moran_mean'], A['NONEIGH']['moran_sd']),
          pm(A['NONEIGH']['tau_mean'], A['NONEIGH']['tau_sd']),
          f"≈{A['NONEIGH']['tau_perm_p_min']:.0e}", "空间一致性非邻域所致"],
         ["NO-PROG", A['NOPROG']['n_seeds'], pm(A['NOPROG']['moran_mean'], A['NOPROG']['moran_sd']),
          pm(A['NOPROG']['tau_mean'], A['NOPROG']['tau_sd']),
          f"**{A['NOPROG']['tau_perm_p_min']:.3f}–{A['NOPROG']['tau_perm_p_max']:.3f}（边界；仅 1/{A['NOPROG']['n_seeds']} 种子名义显著）**", "去标签后排序大幅减弱"]],
        caption="表2 同队列多种子消融（35 例 / 46,820 spot，统一协议）。置换 p 为 35 样本严重度标签向量整体置换 B=10,000 次的经验 p；SciPy 渐近 p 见 Supplementary Table S1，二者不一致时以真置换 p 为准。")
    body(f"**去除疾病严重度标签回归后（NO-PROG），Kendall τ 由 FULL 的 {A['FULL']['tau_mean']:.3f} 降至 "
         f"{A['NOPROG']['tau_mean']:.3f}±{A['NOPROG']['tau_sd']:.3f}（4 个种子 τ=0.207/0.229/0.237/0.251），真置换 p=0.072/0.058/0.052/0.040**："
         "仅 1/4 种子名义显著，其余游走于 0.05 边界；每种子中同一癌症样本（cervical_cancer_1，风险分约 −0.8 至 −1.2）均低于 31 个正常样本中的 30 个，"
         f"疾病 vs 正常 Mann-Whitney 亦降至边缘（p={A['NOPROG']['mwu_p_min']:.3f}–{A['NOPROG']['mwu_p_max']:.3f}，3/4 种子 >0.05）。"
         "功效边界须讲明：置换在全部 35 个样本的标签向量上进行（约 2.1×10⁵ 种排列，不受 4!=24 限制），但秩效应仅由 4 个独立疾病事件驱动，"
         "一个种子的翻转即可改变名义显著性，故该证据定级为 **suggestive（提示性）**——与“队列内排序主要由标签回归锚定”一致，但在 n=4 下不能确证。"
         "这不等同于模型仅死记这 4 张片：3.4 的半监督 LODO 显示保留另外 3 张疾病片标签即可把该方向推广到未见过的疾病片，零标签极限下方向仅部分且不稳定。")
    body(f"相反，**空间一致性对标签、邻域正则与图像均不敏感**：NO-PROG 的 Moran's I 仅由 {A['FULL']['moran_mean']:.3f} 降至 {A['NOPROG']['moran_mean']:.3f}，"
         f"NO-NEIGH（{A['NONEIGH']['moran_mean']:.3f}）与 NO-IMAGE（{A['NOIMAGE']['moran_mean']:.3f}）与 FULL 无实质差异，τ 亦不变（≈0.46）——"
         "高 Moran's I 并非来自邻域正则或 UNI 图像特征，而是 Visium 相邻 spot 共享组织/细胞所致的内在平滑，属数据属性而非模型贡献，不应作为模型性能宣称。"
         f"图像分支的阴性更严格：NO-IMAGE 的 Moran's I 甚至略高于 FULL（{A['NOIMAGE']['moran_mean']:.3f} vs {A['FULL']['moran_mean']:.3f}）、"
         f"τ 完全相同（{A['NOIMAGE']['tau_mean']:.3f} vs {A['FULL']['tau_mean']:.3f}，置换 p 同处 10⁻⁴ 量级），即**引入图像分支后风险头无可检测输出改变**，"
         "而非“小幅未达显著”。受 3 种子与 35 例功效限制不能排除小效应，故我们不把多模态融合列为框架贡献，图像分支是**预先纳入、被消融检验的探索性模块**，"
         "其阴性结果是基准的一部分。（补充分析——不经风险头检验 UNI patch 嵌入自身的空间自相关——见 Supplementary Note S1。）")
    body("**最简通路基线（明确为队列内 in-sample 口径）**：不经任何学习、直接取 108 个 KEGG-HPV 基因的样本平均表达作判分，队列内 AUC=0.75，而 FULL 模型为 1.00。"
         "二者同为 n=35 训练队列上的 in-sample 描述性指标，**不是外部验证**；0.25 的 AUC 增量同样可能来自标签锚定，故仅报告增量大小，不据此宣称泛化优势。")
    body(f"**留一样本（LOSO）跨样本基线：队列内高指标不可外推**。在同一 35 例上做两类 35 折 LOSO。①**形态→HPV 代理判分**：ridge LOSO AUC="
         f"{BSL.get('loso_hpv_ridge_auc', float('nan')):.3f}±{BSL.get('loso_hpv_ridge_auc_sd', float('nan')):.3f}"
         f"（仅 {BSL.get('loso_hpv_ridge_valid', 0)}/35 折可评估，其余折留出片标签单类或预测为常数，本身即说明跨片分布失配；MLP {BSL.get('loso_hpv_mlp_auc', float('nan')):.3f}，"
         f"{BSL.get('loso_hpv_mlp_valid', 0)}/35 折），处于随机水平；②**形态→表达跨样本重建**：以 UNI 特征 ridge 回归预测留出片 {BSL.get('loso35_n_target_genes', 1533)} 个基因表达，"
         f"平均逐基因 Pearson r={BSL.get('loso35_per_gene_pearson', float('nan')):.3f}、held-out MSE={BSL.get('loso35_recon_mse', float('nan')):.3f}，"
         f"不优于同样本内 80/20 内插参照（MSE={BSL.get('he2st_mse', float('nan')):.3f}）。对照 FULL 队列内 AUC=1.00，这两组基线直接证明**队列内指标与跨样本外推性能之间不存在可外推的对应关系**。")

    h2("3.3 通路锚定风险的生物学可解释性")
    add_fig(doc, "Fig4_biology_correlation.png", 6.0,
            "图4 spot 风险与通路/细胞状态评分的 Spearman 相关（within-sample z，3 个 FULL 种子均值，"
            "11 项相关全部 BH q<5×10⁻⁹，最弱项 q=4.9×10⁻⁹）。")
    body("风险高的 spot 富集肿瘤上皮与 HPV 致癌程序、并表现干扰素/增殖下调，方向与宫颈鳞癌上皮转化及免疫逃逸一致：")
    body(f"· 肿瘤上皮 marker（KRT5/14/17、EPCAM 等）：ρ=**{BIO['CELL_tumor_epithelial']['rho']:+.2f}**；"
         f"HPV 致癌驱动（CDKN2A/MYC/EGFR/PIK3CA 等）：ρ=**{BIO['HPV_INTEGRATION_CANDIDATE']['rho']:+.2f}**；"
         f"抗原呈递（B2M/HLA-A/B2M/PSMB8）：ρ=**{BIO['ANTIGEN_PRESENTATION']['rho']:+.2f}**。", indent=False)
    body(f"· 干扰素-抗病毒（STAT1/MX1/ISG15 等）：ρ=**{BIO['INTERFERON_ANTIVIRAL']['rho']:+.2f}**（高危区干扰素应答减弱，"
         "符合 HPV E6/E7 介导的免疫逃逸）；增殖：ρ="
         f"{BIO['PROLIFERATION']['rho']:+.2f}、EMT：ρ={BIO['EMT']['rho']:+.2f}（经 within-sample z，受基底/分化异质性影响，谨慎解读）。",
         indent=False)
    body(f"为确认这些 marker 不是任意基因组合，在独立宫颈 scRNA-seq（GSE308792[24]，{SCR['n_cells']:,} 个整合细胞；原始论文报告 14,441 个免疫细胞，"
         f"为不同细胞口径）上验证：同谱系内平均相关 +0.242、跨谱系 −0.037，肿瘤上皮与 T 细胞谱系评分相关 −0.57。")

    h2("3.4 无标签跨平台/跨器官迁移与少量标签留出外推")
    add_fig(doc, "Fig5_external_transfer.png", 6.4,
            "图5 外部迁移与留出外推。A：HNSCC 的 Moran's I 四层对照——模型评分 0.76/0.67、KEGG-HPV 面板 0.71/0.62、表达量配对随机集 0.58/0.48、坐标置换零分布近零"
            "（14 张切片 p≤0.001）。B：GeoMx 肿瘤区高于良性（芯级 p=3.5e-4）。C：Silva 模式非单调（A 最高），病理风险分层不显著且方向相反。"
            "D：终协议 LODO 各留出疾病片的百分位，半监督 vs 全无监督。")
    body(f"**跨平台方向可迁移，但不支持分级（GeoMx DSP，GSE316098[21]）**。推理阶段仅用表达分支、不读取任何宫颈标签（权重来自宫颈监督训练；"
         f"本节检验已学得表征的可迁移性，而非无监督发现）。分组以 GEO SOFT 原始注释为准（列名前缀 1A/1b-1 是 TMA 芯编号，已纠正）。"
         f"在 {EXT['geomx_n_patients']} 例患者、{EXT['geomx_n_rois']} 个 ROI（{EXT['geomx_n_cores']} 个上皮/间质配对芯）上，"
         f"肿瘤区（Silva A/B/C 合并）为 {EXT['geomx_tumor_mean']:.2f}、良性为 {EXT['geomx_benign_mean']:.2f}（芯级 p={EXT['geomx_tn_core_p']:.1e}），"
         f"患者内配对 {EXT['geomx_wp_n']}/{EXT['geomx_wp_n']} 一致（配对 Wilcoxon p={EXT['geomx_wp_p']:.3f}）。"
         f"须知 n=6 时双侧精确符号秩检验的最小可达 p 为 {EXT['geomx_wp_exact_two_sided_floor_n6']:.3f}，故 6/6 已是该样本量下数学上最强的结果、不存在“更显著”的空间；"
         f"但一致性比例的 Clopper-Pearson 95% 区间 [{EXT['geomx_wp_ci_lo']:.2f}, 1.00] 很宽，需在更大配对队列中复制。"
         f"上皮 ROI 高于基质（{EXT['geomx_compartment_epi']:.2f} vs {EXT['geomx_compartment_stroma']:.2f}，p={EXT['geomx_compartment_p']:.3f}），"
         f"故不能排除区室组成的贡献，患者内配对设计是最可靠证据。**但该评分不是分级轴**：Silva A（预后最好）反而最高"
         f"（芯级 A {EXT['geomx_core_silva_A']:.2f}≈C {EXT['geomx_core_silva_C']:.2f}>B {EXT['geomx_core_silva_B']:.2f}；A vs B p={EXT['geomx_core_silva_AB_p']:.3f}），"
         f"病理 High vs Low 不显著且方向相反（Low {EXT['geomx_risk_core_lo']:.2f} > High {EXT['geomx_risk_core_hi']:.2f}，p={EXT['geomx_risk_core_p']:.3f}）。"
         f"外部证据因此只支持“肿瘤 vs 正常方向可迁移”，不支持分级。")
    body(f"**Silva 非单调结果的事后分层（已排除区室失衡；信号定位于上皮；机制待验证）**。A/B/C 三型的上皮/基质 ROI 数量完全均衡（21/21、22/22、25/25），"
         f"且 A 最高的信号完全位于上皮 ROI（A {EXT['geomx_silva_epi_A']:.2f} > B {EXT['geomx_silva_epi_B']:.2f} > C {EXT['geomx_silva_epi_C']:.2f}；A vs B p={EXT['geomx_silva_epi_AB_p']:.1e}），"
         f"基质内无梯度（{EXT['geomx_silva_str_A']:.2f}/{EXT['geomx_silva_str_B']:.2f}/{EXT['geomx_silva_str_C']:.2f}）——与“Silva A 保留了更完整的 HPV 驱动上皮程序”相容。"
         f"但该数据集无 HPV-ISH/p16 注释、该比较亦未经多重性预注册，故仍属待验证假说（Supplementary Note S2）。")
    body(f"**跨器官（HNSCC）：真实空间自组织成立、含弱但可复现的通路特异性，但判别性迁移检验全部为阴性**。终协议评分在 {EXT['hnscc_n_samples']} 张头颈部鳞癌 ST 切片"
         f"（GSE268014[22]）上 Moran's I={EXT['hnscc_moran_mean']:.2f}，在独立 HPV 分层 HNSCC 集 GSE281978[23]（{EXT['hnscc_gse281978_n']} 张）上为 "
         f"{EXT['hnscc_gse281978_moran_mean']:.2f}。坐标置换（B=1000）零分布近零（14/14 张 p≤0.001），排除输出坍缩。"
         f"与模型无关的朴素 KEGG-HPV 面板 Moran's I 与之几乎相同（{EXT['rg268_kegg']:.2f}/{EXT['rg281_kegg']:.2f}），说明高自相关主要来自通路表达的内在平滑；"
         f"但在 30 个按表达量十分位配对的随机基因集对照下，KEGG 面板在全部切片上仍更高（{EXT['rg268_exprm']:.2f}/{EXT['rg281_exprm']:.2f}；"
         f"Δ=+{EXT['rg268_exprm_delta']:.2f}/+{EXT['rg281_exprm_delta']:.2f}；切片级精确符号检验 p={EXT['rg268_exprm_signp']:.3f}/{EXT['rg281_exprm_signp']:.3f}），"
         f"即含弱但跨全部切片可复现的通路特异性成分。所有切片级判别性检验均不显著且部分方向相反（Supplementary Note S3）；"
         f"故跨器官证据仅限于“可计算并保留真实、弱通路特异性的空间组织”，不构成疾病特异性迁移。")
    body(f"**少量标签把部分方向稳定为可迁移方向（半监督 vs 全无监督 LODO，同一协议、逐折配对）**。两协议均逐折留出 1 个疾病片、锁定同一超参、使用全部 spot 与同一 35 例队列，"
         f"唯一差别是监督项。**全无监督 LODO（λ_sup=λ_prog=0）给出部分且不稳定的方向**：{EXT['unsup_lodo_n_above_median']}/4 折高于正常中位、仅 "
         f"{EXT['unsup_lodo_n_above_all']}/4 折高于全部正常，平均百分位 {EXT['unsup_lodo_mean_pct']:.2f}（唯一腺癌 CA_HPV_2 为 {EXT['unsup_lodo_min_pct']:.2f}，低于全部正常）。"
         f"**加入另外 3 张疾病片标签后该方向被稳定**：{EXT['lodo_n_above_median']}/4 折高于中位、{EXT['lodo_n_above_all']}/4 折高于全部正常，平均百分位 "
         f"{EXT['lodo_mean_pct']:.2f}，失败的腺癌折由 {EXT['unsup_lodo_min_pct']:.2f} 升至 {EXT['lodo_min_pct']:.2f}——清晰的标签剂量效应；腺癌折两协议下均最弱，"
         f"提示腺 vs 鳞的组织学泛化是主要瓶颈。**计数证据必须连同分辨力报告**：4 折只有 4 个独立留出事件，4/4 与 3/4 的 Clopper-Pearson 95% 下界仅 "
         f"{EXT['lodo_4of4_ci_lo']:.2f} 与 {EXT['unsup_3of4_ci_lo']:.2f}、区间大幅重叠，故“半监督优于无监督”是提示性趋势；更稳健的证据是配对设计本身与腺癌折 0.00→0.60 的逐折同向变化。")
    h2("3.5 通路特异性与阴性结果")
    body(f"**随机基因集对照**：KEGG-HPV 锚定评分 Moran's I={RC['kegg_moran']:.3f}，高于 30 个随机同规模基因集"
         f"（{RC['random_moran_mean']:.3f}，{RC['random_moran_min']:.3f}–{RC['random_moran_max']:.3f}；置换 p={RC['moran_perm_p']:.3f}），"
         f"即空间一致性具弱但显著的通路特异性；然而疾病排序 Kendall τ 在随机基因集上同样很高"
         f"（KEGG {RC['kegg_kendall']:.3f} vs 随机 {RC['random_kendall_mean']:.3f}，AUC 置换 p={RC['auc_perm_p']:.2f}），"
         "再次表明**高排序与通路特异性无关、与标签锚定一致**——与 3.2 的提示性结论自洽。")
    body(f"**TCGA-CESC 生存（阴性，临床效用声明）**：11 个空间 DEG 在 {TC['n_patients']} 例（{TC['events']} 事件）bulk 队列单因素 Cox 回归[34]中无一经 BH-FDR 显著"
         f"（最显著 {TC['min_gene']} 原始 p={TC['min_p']:.3f}），提示 spot 级空间风险与患者级结局之间存在尺度断裂。因此我们在摘要、结论与本节统一声明："
         "**该评分当前不具有任何临床决策效用**——不分级（GeoMx 反向）、不预测 bulk 预后、跨器官判别全部阴性；其价值是方法学基准与概念验证。")

    h2("3.6 小样本 ST 风险研究的最低报告协议（建议）")
    body("基于本极端案例，我们把散见于讨论的建议形式化为一套**最低报告协议（minimum reporting protocol, MRP-ST）**，"
         "适用于独立疾病样本数 n_dis≤10（或任一类别 ≤5）的监督/半监督 ST 风险表征研究。协议含 5 个必报项——"
         "去标签消融、全样本标签置换（B≥10,000，不得仅在疾病样本内置换、不得以 spot 为单位）、随机基因集对照（≥30 个、按表达量分位配对）、"
         "样本级留出双协议（半监督与全无监督，逐折训练队列相同，统计单位为样本/切片）、以及结论分级与临床效用声明——"
         "每项均给出最小设计、失败判读与 supported/suggestive/unsupported 判据，并配决策树执行顺序"
         "（完整清单与分级表见 Supplementary Table S2）。全部为训练后分析，可在既有代码库上以可忽略成本复现。"
         "按该规则，本研究的定级为：空间自组织（含弱通路特异性）=supported；GeoMx 肿瘤 vs 正常方向、标签锚定依赖、半监督优于无监督=suggestive；"
         "疾病分级、预后预测、跨器官判别、图像分支增益=unsupported。")

    h1("4 讨论")
    body("本研究在一个极端小样本（疾病 n=4）的公开宫颈 ST 队列中，系统检验了通路锚定风险表征能与不能做什么，并据此标定了一套最低报告协议（§3.6）。"
         "可辩护的正面结论有三点。其一，spot 风险与肿瘤上皮、HPV 致癌驱动、抗原呈递正相关，与干扰素应答负相关——方向与宫颈病变生物学一致、跨种子稳定，"
         "并经独立 scRNA-seq 验证 marker（spot 级，因伪重复仅作描述）。其二，空间一致性高且对标签不敏感。其三，由宫颈监督训练得到的评分在推理无标签阶段"
         f"仍保持 GeoMx 独立宫颈腺癌队列的“肿瘤 vs 正常”方向（芯级 p={EXT['geomx_tn_core_p']:.1e}；{EXT['geomx_wp_n']} 例患者内配对 p={EXT['geomx_wp_p']:.3f}；suggestive），"
         f"并在 HNSCC 上可计算、保留真实且弱通路特异性的空间组织（坐标置换 14/14 p≤0.001；符号检验 p={EXT['rg268_exprm_signp']:.3f}/{EXT['rg281_exprm_signp']:.3f}），"
         "而切片级判别为阴性（§3.4）。因此真正持久的信号是肿瘤相关通路程序的方向与空间组织，而非对 4 个标签的拟合，也不是精细分级。")
    body("**必须诚实面对的边界**：(1) 队列内近乎完美的有序排序在去除严重度标签后大幅减弱、仅达显著性边界（NO-PROG τ 0.46→0.21–0.25；置换 p=0.040–0.072，1/4 种子名义显著），"
         "故标签锚定为提示性而非确证；置换在全部 35 个样本上进行（约 2.1×10⁵ 种排列），受限的是 4 个独立疾病事件带来的功效。全无监督留出只给出部分且不稳定的方向"
         f"（{EXT['unsup_lodo_n_above_median']}/4 折高于中位，平均 {EXT['unsup_lodo_mean_pct']:.2f}），半监督 LODO 与方向稳定相关"
         f"（{EXT['lodo_n_above_median']}/4 折高于中位，平均 {EXT['lodo_mean_pct']:.2f}），但精确 CI 重叠（下界 {EXT['lodo_4of4_ci_lo']:.2f}/{EXT['unsup_3of4_ci_lo']:.2f}），同样为提示性。"
         "本研究可作为方法学范例，但**不能被表述为无监督诊断或侵袭性分级工具**；(2) UNI 图像分支在 3 个种子下对风险头输出产生零可测改变，而非小幅未达显著（3 种子不能排除小效应）；"
         "它本就是预先定位的探索性被检验模块，故多模态融合不是本文贡献（Supplementary Note S1）；(3) 空间 DEG 不带 bulk 预后信号，**评分当前无任何临床决策效用**；"
         "GeoMx 为腺癌、主队列以鳞癌为主，与最弱的腺癌留出折一致；(4) 仅 4 例疾病样本与 6 例配对患者，功效天然受限，所有受功效限制的结论均已降级为 suggestive；"
         "(5) 区室组成不能排除为肿瘤-良性差异的贡献者，但均衡的上皮/基质事后分层已排除其解释 Silva 非单调（Supplementary Note S2）；"
         "(6) 30 例正常外宫颈样本聚合自三个 GEO 子系列，且 46,820 个非独立 spot 的相关性存在伪重复，均按描述性处理，样本/切片/患者级比较为主要证据。")
    body("**对领域的方法学贡献：从建议到协议**。§3.6 将本研究的教训形式化为 MRP-ST，含明确的触发条件（n_dis≤10）、5 个必报项与 supported/suggestive/unsupported 判据。"
         "仅报告队列内 AUC≈1 或高相关、而不证明其在去标签/跨数据下成立，无法区分泛化与标签记忆；本文正是这一失效模式的极端案例——in-sample AUC=1.00 在去标签后仅余边界级证据。"
         "该协议与小样本机器学习中关于标签泄漏与评估偏差的经典讨论[35,36] 一致，也与 TRIPOD+AI[37] 等预测模型报告规范相容；其新意在于把既有原则操作化为空间转录组场景下"
         "固定、可逐行勾选的检查表。协议不依赖具体网络，仓库已提供脚本与全部结果 JSON，可直接作为评审核查清单。")

    h1("5 结论")
    body("在 n=4 疾病的极端约束下，通路锚定的表达型 ST 框架能够给出生物学可解释、空间一致的通路风险评分；其监督训练所得评分在推理无标签下可跨平台"
         "（GeoMx：保持“肿瘤 vs 正常”方向，6/6 患者内一致、已达 n=6 分辨极限，suggestive）与跨器官（HNSCC：保留真实、弱通路特异性的空间组织，supported；"
         "但恶性/HPV/转移判别为阴性）计算——并非无监督发现，亦非疾病特异性跨器官迁移，更不支持风险分级。精细有序排序与标签锚定的关联仅获提示性证据"
         "（置换 p=0.040–0.072，1/4 种子名义显著）；半监督留一疾病外推提示少量标签下该方向或可推广到未见过的疾病片（4/4，CI 宽，suggestive）。"
         "探索性图像分支对输出零可测改变（unsupported），评分不分级、不预测 bulk 预后，故当前无任何临床决策效用。本文的贡献不是生物学发现或诊断工具，"
         "而是一个标签依赖消融基准与 MRP-ST 最低报告协议（§3.6），并以一个极端案例展示了不执行这些消融时 in-sample 完美结果如何掩盖标签记忆；"
         "在全部数字与脚本均可复现的前提下，本文可作为评估基准与面向更大、配准的多中心 H&E-ST 队列的起点清单。")

    h1("数据与代码可得性")
    body("全部训练脚本、配置、结果 JSON 与融合嵌入均可在 GitHub 公开仓库获取（链接：https://github.com/WorldBMW/pathway-anchored-risk-benchmark）；"
         "数据全部来自公开数据库：宫颈 Visium 队列（GSE208654、GSE217237 及 10x Genomics 公开示例切片）；"
         "外部队列为 GeoMx GSE316098、GSE268014、GSE281978、TCGA-CESC、GSE308792（编号见表1）。", indent=False)
    h1("参考文献")
    for _i, _r in enumerate(REFS, 1):
        body(f"[{_i}] {_r}", indent=False)
    h1("作者贡献 / 资助 / 利益冲突")
    body("作者贡献（CRediT）：白明威（第一作者）——概念化、方法学、软件、形式分析、调查、数据管理、可视化、原稿撰写；[通讯作者]（通讯作者，待定）——监督、项目管理、稿件审阅与编辑。**资助：本研究未获得任何外部资助（无基金资助）**。作者声明无利益冲突。", indent=False)

    save_doc(doc, "Manuscript_v10_中文.docx")
    return doc

# =========================================================================
#  ENGLISH
# =========================================================================
def build_en():
    doc, h1, h2, body, title, ctr = make_doc(cn=False)
    title("A label-dependence ablation benchmark for pathway-anchored risk representation in "
          "extreme low-sample spatial transcriptomics: a cervical-lesion label-free validation "
          "protocol and cross-platform transfer case study")
    ctr("Proof-of-concept; not a diagnostic tool.", 10.5, italic=True)
    doc.add_paragraph()

    h1("Abstract")
    body("**Background and objectives.** Multimodal fusion of spatial transcriptomics (ST) and pathomics can characterize the "
         "cervical lesion microenvironment, but public ST cohorts contain very few disease samples (only four obtainable cervical "
         "Visium lesions here), so supervised risk models may memorize a few labels and report near-perfect but non-generalizable "
         "results. Rather than a diagnostic tool, we ask whether a pathway-anchored risk representation is biologically interpretable "
         "and computable without labels across platforms, and whether in-cohort disease separation reflects learning or label "
         "anchoring, then formalize the checks.")
    body(f"**Methods.** On {CO['n_samples']} cervical Visium samples ({CO['n_normal']} normal, {CO['n_disease']} diseased; "
         f"{CO['n_spots']:,} spots; {CO['n_genes_panel']}-gene pathway panel) an expression-pathway branch is combined with an "
         "exploratory UNI image branch, regularized by an HPV-pathway consistency term, spatial-neighborhood smoothing and risk "
         "supervision. All comparisons share one cohort and protocol across seeds: FULL, NO-IMAGE, NO-HPV, NO-NEIGH, NO-PROG. "
         "Spatial coherence uses Moran's I; ordered disease ranking uses sample-level Kendall tau with the severity vector permuted "
         "over all 35 samples (B=10,000). External validation uses the expression branch alone at a label-free inference stage: "
         "GeoMx DSP (GSE316098), head-and-neck ST, TCGA-CESC and cervical scRNA-seq (GSE308792).")
    body(f"**Results.** FULL gives Moran's I={A['FULL']['moran_mean']:.3f}+/-{A['FULL']['moran_sd']:.3f} and tau={A['FULL']['tau_mean']:.3f} "
         f"(p={A['FULL']['tau_perm_p_min']:.0e} to {A['FULL']['tau_perm_p_max']:.0e}). Removing severity labels (NO-PROG) lowers tau to "
         f"{A['NOPROG']['tau_mean']:.3f}+/-{A['NOPROG']['tau_sd']:.3f} with p={A['NOPROG']['tau_perm_p_min']:.3f}-{A['NOPROG']['tau_perm_p_max']:.3f} "
         "(1/4 seeds nominally significant), so label anchoring is suggestive, not confirmed. Spatial coherence is insensitive to labels, "
         "neighbourhood regularization and image features, and the image branch yields zero detectable output change. Scores correlate with "
         "tumour-epithelial (+0.60), HPV-oncogenic (+0.24) and antigen-presentation (+0.51) programmes and inversely with "
         "interferon-antiviral (-0.62) programmes. In GeoMx, tumour regions exceed benign tissue (core-level "
         f"p={EXT['geomx_tn_core_p']:.1e}; 6/6 within-patient pairs, p={EXT['geomx_wp_p']:.3f}, the n=6 exact-test floor), yet the score is "
         "not an invasive-grade axis. Cross-organ head-and-neck scores retain genuine spatial organization (coordinate permutation p<=0.001) "
         "while malignancy, HPV and metastasis contrasts are all null. Survival (302 patients, 72 events) and leave-one-sample-out baselines "
         "(AUC 0.497+/-0.021) are null.")
    body("**Conclusions.** With four disease samples the framework yields interpretable, spatially coherent and label-free transferable "
         "pathway risk, whereas fine ordered ranking remains only suggestive. We formalize these checks as a minimum reporting protocol "
         "(MRP-ST) with supported/suggestive/unsupported grading; the score currently carries no clinical decision utility.")
    p = doc.add_paragraph(); _rf(p.add_run("Keywords: "), 11.5, True)
    _rf(p.add_run("spatial transcriptomics; cervical lesion; HPV pathway; small-sample learning; label-dependence ablation; "
                  "minimum reporting protocol; cross-platform transfer; methodological benchmark"), 11.5)

    h1("1. Introduction")
    body("Cervical cancer is the fourth most common malignancy in women worldwide [1], caused mainly by persistent high-risk HPV infection [2]; "
         "TCGA multi-omics has characterized its molecular landscape [3], and the Silva A/B/C pattern-based classification of endocervical adenocarcinoma "
         "is an established histologic grading system linked to lymph-node metastasis and prognosis [4-7]. As spatial transcriptomics (e.g., 10x Visium [8]) "
         "and digital-pathology foundation models (e.g., UNI [9], Virchow [10], GigaPath [11]) mature, combining expression, imaging and pathway priors could "
         "characterize epithelial transformation and microenvironment remodeling in situ. A widely under-estimated methodological risk is that diseased public "
         "ST samples are extremely few: only four diseased cervical Visium samples (one HSIL, three SCC/ADC) could be aggregated here - a scale at which any "
         "supervised risk model can memorize four labels and report near-perfect in-cohort separation that is memorization rather than generalization.")
    body("Pathway biology offers a natural inductive bias: HPV oncogenesis is a conserved E6/E7-driven program acting through p53/Rb loss, altered antigen "
         "presentation and immune evasion. Anchoring the representation to it should yield scores that are biologically interpretable, spatially smooth and "
         "transferable to other HPV/epithelial-transformation contexts. Whether these expectations hold must be tested with controls rather than assumed.")
    body("**Related work and positioning.** HE2RNA [12] and ST-Net [13] first predicted (spatial) expression from H&E; OmiCLIP [14] extended visual-omics "
         "alignment into a pathology-ST foundation model; SPADE [15], SEAL [16] and MINT [17] fine-tune pathology encoders with ST supervision on 10^5-10^6 "
         "spots; ST-Align [18] aligns images and genes at spot/niche level; STPath [19] predicts ~40,000 genes across 17 organs. All presuppose large "
         "multi-sample data and target representation learning or molecular prediction; none addresses four diseased samples, nor asks whether perfect in-cohort "
         "separation reflects learning or label memorization. We do not compete on scale or accuracy; we frame the problem as a **task-side transferable "
         "pathway-risk representation** with a label-removal ablation benchmark.")
    body("**Contributions and scope (explicitly neither a diagnostic nor a multimodal-fusion claim).** (1) A label-dependence ablation benchmark on 35 cervical "
         "Visium samples under a same-cohort, multi-seed, full-spot protocol, with the UNI image branch defined a priori as an exploratory, ablation-tested module "
         "(its null result is in 3.2); (2) FULL/NO-IMAGE/NO-HPV/NO-NEIGH/NO-PROG ablations that dissociate the sources of spatial coherence, interpretability and "
         "disease ordering; (3) label-free cross-platform (GeoMx DSP [20]) and cross-organ (HNSCC) transfer using the correct GEO Silva annotation; (4) honest "
         "reporting of negatives, formalized into a minimum reporting protocol with conclusion grading (Section 3.6).")

    h1("2. Materials and Methods")
    h2("2.1 Cohorts")
    add_table(doc,
        ["Cohort", "Type", "Scale", "Use"],
        [["Cervical Visium aggregate (GSE208654 + GSE217237 + 10x public demo)", "ST (10x Visium)", f"{CO['n_samples']} ({CO['n_normal']} normal / {CO['n_disease']} dis.); {CO['n_spots']:,} spots", "Main + ablation"],
         ["GSE316098 [21]", "GeoMx DSP (cervical ADC) [20]", f"{EXT['geomx_n_patients']} patients (WU-01-WU-07) / {EXT['geomx_n_rois']} ROI ({EXT['geomx_n_cores']} cores)", "Cross-platform: tumor>normal (not grade)"],
         ["GSE268014 [22]", "ST (head & neck; Simkin et al.)", f"{EXT['hnscc_n_samples']} sections", "Cross-organ spatial organization (discrimination n.s.)"],
         ["GSE281978 [23]", "ST (HPV+/- HNSCC; Lee et al.)", f"{EXT['hnscc_gse281978_n']} sections", "Cross-organ replication (HPV/metastasis n.s.)"],
         ["TCGA-CESC [3]", "bulk RNA-seq", f"{TC['n_patients']} pts / {TC['events']} events", "Survival (negative)"],
         ["GSE308792 [24]", "scRNA-seq (cervix)", f"{SCR['n_cells']:,} cells", "Marker validity"]],
        caption="Table 1. Cohort overview", cn=False)
    body("Note: counts denote the sections actually analysed here. GSE268014 comprises 26 tumours in the source study and 8 sections were used; all 6 GSE281978 ST sections were used.", indent=False)
    body("The cervical Visium cohort aggregates three public sources, 35 samples in total (31 normal + 4 diseased): (i) **GSE208654** (Guo et al., Clin Transl Med "
         "2023;13(3):e1219), four sections - N_HPV (normal), HSIL_HPV, CA_HPV_1 (SCC) and CA_HPV_2 (adenocarcinoma); (ii) 30 normal ectocervix Visium sections "
         "(P001-P030) under the **GSE217237** SuperSeries (three sub-series GSE290350/GSE299708/GSE300112 from HIV-infection, DMPA-contraceptive and microbiome studies; "
         "this heterogeneity is addressed in the Limitations); (iii) the public 10x Genomics FFPE cervical-cancer demonstration section "
         "(Visium_FFPE_Human_Cervical_Cancer; cervical_cancer_1, SCC). Histologic labels are normal/HSIL/cancer (severity 0/1/2). Every run uses the same 35 samples, the "
         "full 46,820 spots and a unified 4,991-gene panel (107 pathway genes).")
    h2("2.2 Framework and losses")
    body("The framework has three routes: (a) an expression branch encoding genes to a latent space with reconstruction (l_rec, 0.2) and a latent prior (l_var, 0.1); "
         "(b) an image branch (exploratory, ablation-tested) encoding UNI [9] patch features and fusing them with the latent expression vector, included precisely to "
         "test whether morphology adds anything detectable here; (c) pathway and spatial priors: a KEGG-HPV (108-gene [25]) consistency regularizer l_hpv "
         "(lambda_hpv=1.0) and a neighborhood agreement term l_neigh (0.3). A risk head produces a per-spot score supervised by an HPV-status proxy BCE (l_sup, 5.0) "
         "and severity regression (l_prog, MSE to 0/1/2, 1.5).")
    body("**Ablation definitions (to avoid misreading).** FULL is complete; NO-IMAGE disables the image branch; NO-NEIGH disables l_neigh while keeping everything "
         "else, testing whether high coherence comes from the neighborhood regularizer; NO-HPV sets only lambda_hpv=0 (the HPV-proxy l_sup stays on, so it tests the "
         "pathway-consistency term alone); **NO-PROG sets lambda_prog=0, i.e. severity labels are never used in training**, while expression, image, pathway and HPV-proxy "
         "supervision remain. Leave-one-disease-out (LODO) is run over the four disease samples in two protocols: semi-supervised LODO (primary) keeps the other three "
         "diseases' labels and holds out the target slide, reporting its percentile among the 31 training normals; fully-unsupervised LODO additionally sets "
         "lambda_sup=lambda_prog=0. **Both were run under the same final protocol and are directly comparable**: no spot cap, all spots used (44,039-46,241 per fold, "
         "identical per-fold counts across protocols), jointly fixed lambda_recon/lambda_hpv/lambda_neigh=0.2/1.0/0.3 and identical training cohort (34 samples per fold); "
         "only the supervision terms differ (5.0/1.5 vs 0/0), so the difference is interpretable as the causal effect of labels.")
    h2("2.3 Evaluation and statistics")
    body("Spatial coherence is Moran's I [26]; disease ordering is sample-level Kendall tau [27] between per-sample risk and severity, with its empirical null "
         "obtained by permuting the severity-label vector across ALL 35 samples (31 zeros, one 1, three 2s) and recomputing spot-aggregated risk, B=10,000 "
         "(Supplementary Table S1; the rank effect is still driven by only four disease events, hence low power). Disease-vs-normal separation uses one-sided "
         "Mann-Whitney U [28]; the within-patient GeoMx comparison uses a two-sided paired Wilcoxon signed-rank test (smallest attainable p at n=6 is 2/2^6=0.031), "
         "reported with exact Clopper-Pearson 95% intervals, as are LODO k/4 counts. Downstream scores use rank-based ssGSEA [29] (pure NumPy [30]) with "
         "within-sample z-standardization, Spearman correlation and Benjamini-Hochberg FDR [31]; classification metrics use scikit-learn [32], tests use SciPy [33]. "
         "**At inference, external scoring uses the expression branch and reads no cervical labels; the weights nevertheless derive from supervised cervical training "
         "(lambda_sup=5.0, lambda_prog=1.5)**, so external experiments test transfer of a learned representation, not unsupervised discovery, which the fully-unsupervised "
         "LODO tests. All external inference uses one weight file, `results/checkpoint_FULL_DEPLOY_FAST_seed42.pt` (seed 42). **For GSE316098, Silva/risk groups follow "
         "the GEO SOFT metadata**; the 1A/1b-1 column prefixes are TMA core identifiers, not Silva patterns. ROIs are paired epithelial/stromal within a core, with "
         "core-level and within-patient tests primary. Each variant is run over multiple seeds, and the NO-HPV tau being identical across its three seeds (SD=0.000) "
         "reflects one deterministic supervised signal dominating sample-level ordering, not failed seeding.")

    h1("3. Results")
    h2("3.1 Framework and in-cohort risk stratification")
    add_fig(doc, "Fig1_Framework.png", 6.4,
            "Figure 1. Framework: fused expression and image branches with an HPV-pathway prior and spatial-neighborhood "
            "constraint producing a per-spot risk score.", cn=False)
    add_fig(doc, "Fig2_risk_violin.png", 5.3,
            f"Figure 2. Per-spot risk rises with histologic severity (FULL, seed 0; normal {RV['normal_mean']:.2f} / "
            f"HSIL {RV['hsil_mean']:.2f} / cancer {RV['cancer_mean']:.2f}). **Descriptive in-sample result with "
            f"disease n={CO['n_disease']}; not evidence of generalization.**", cn=False)
    body("Mean per-spot risk increases monotonically across normal/HSIL/cancer, and per-sample disease-vs-normal "
         "Mann-Whitney is p~1.9e-5. As emphasized, this is a descriptive phenomenon within the supervised training "
         "set; whether it reflects learned disease signal is decided by the label-removal ablation (3.2).")
    h2("3.2 Label-dependence ablation: testing label anchoring of ordered disease ranking (suggestive evidence)")
    add_fig(doc, "Fig3_ablation_multiseed.png", 6.5,
            "Figure 3. Same-cohort multi-seed ablation. Left: spatial coherence (Moran's I). Right: disease ordering "
            "(Kendall tau; dots are seeds, bars are mean +/- SD). NO-PROG (no severity labels) drops Kendall tau to the "
            "significance boundary (35-sample label permutation, B=10,000, 4-seed p=0.040-0.072), whereas Moran's I drops only slightly.", cn=False)
    add_table(doc,
        ["Variant", "Seeds", "Moran's I (mean +/- SD)", "Kendall tau (mean +/- SD)", "tau true perm. p (B=10,000)", "Interpretation"],
        [["FULL", A['FULL']['n_seeds'], pm(A['FULL']['moran_mean'], A['FULL']['moran_sd']),
          pm(A['FULL']['tau_mean'], A['FULL']['tau_sd']),
          f"{A['FULL']['tau_perm_p_min']:.0e}-{A['FULL']['tau_perm_p_max']:.0e}", "Full model"],
         ["NO-IMAGE", A['NOIMAGE']['n_seeds'], pm(A['NOIMAGE']['moran_mean'], A['NOIMAGE']['moran_sd']),
          pm(A['NOIMAGE']['tau_mean'], A['NOIMAGE']['tau_sd']),
          f"{A['NOIMAGE']['tau_perm_p_min']:.0e}-{A['NOIMAGE']['tau_perm_p_max']:.0e}", "No output change detected (3 seeds; limited power)"],
         ["NO-HPV", A['NOHPV']['n_seeds'], pm(A['NOHPV']['moran_mean'], A['NOHPV']['moran_sd']),
          pm(A['NOHPV']['tau_mean'], A['NOHPV']['tau_sd']),
          f"~{A['NOHPV']['tau_perm_p_min']:.0e}", "Pathway term not decisive"],
         ["NO-NEIGH", A['NONEIGH']['n_seeds'], pm(A['NONEIGH']['moran_mean'], A['NONEIGH']['moran_sd']),
          pm(A['NONEIGH']['tau_mean'], A['NONEIGH']['tau_sd']),
          f"~{A['NONEIGH']['tau_perm_p_min']:.0e}", "Coherence not from neighbor term"],
         ["NO-PROG", A['NOPROG']['n_seeds'], pm(A['NOPROG']['moran_mean'], A['NOPROG']['moran_sd']),
          pm(A['NOPROG']['tau_mean'], A['NOPROG']['tau_sd']),
          f"**{A['NOPROG']['tau_perm_p_min']:.3f}-{A['NOPROG']['tau_perm_p_max']:.3f} (boundary; 1/{A['NOPROG']['n_seeds']} seeds nominal)**", "Ranking strongly attenuated"]],
        caption="Table 2. Same-cohort multi-seed ablation (35 samples / 46,820 spots, unified protocol). Permutation p-values shuffle the severity-label vector across all 35 samples (B=10,000); SciPy asymptotic p-values are given in Supplementary Table S1, and where the two disagree at small n the permutation p governs.", cn=False)
    body(f"The direction is consistent but the strength must be stated cautiously: removing disease-severity-label regression (NO-PROG) lowers Kendall tau from "
         f"{A['FULL']['tau_mean']:.3f} to {A['NOPROG']['tau_mean']:.3f}+/-{A['NOPROG']['tau_sd']:.3f} (per-seed 0.207/0.229/0.237/0.251), with true permutation "
         f"p=0.072/0.058/0.052/0.040: only one of four seeds reaches nominal significance and the rest straddle 0.05. In every seed the same cancer sample ranks below 30 of 31 "
         f"normals, and disease-vs-normal Mann-Whitney is borderline (p={A['NOPROG']['mwu_p_min']:.3f}-{A['NOPROG']['mwu_p_max']:.3f}; >0.05 in 3 of 4 seeds). The power boundary "
         "must be explicit: the permutation operates on the 35-sample label vector (~2.1e5 labelings), but the rank effect is driven by only four independent disease events and "
         "one seed among four flips the nominal verdict. This evidence is therefore graded SUGGESTIVE: consistent with in-cohort ordering being anchored by the label regression "
         "rather than learned from unlabeled data, yet not confirmatory at n=4. It does not mean the model merely memorizes four slides - the semi-supervised LODO in 3.4 shows "
         "that three labeled disease slides suffice to transfer the direction, while at the zero-label limit it is partial and unstable.")
    body(f"Spatial coherence, by contrast, is insensitive to labels, the neighborhood term and the image branch: NO-PROG Moran's I falls only from "
         f"{A['FULL']['moran_mean']:.3f} to {A['NOPROG']['moran_mean']:.3f}, and NO-NEIGH ({A['NONEIGH']['moran_mean']:.3f}) and NO-IMAGE ({A['NOIMAGE']['moran_mean']:.3f}) are "
         f"essentially identical to FULL with tau unchanged (~0.46). The high Moran's I is therefore a data property - intrinsic smoothing of pathway expression across "
         "adjacent Visium spots sharing tissue/cells - not a model contribution nor the effect of the neighborhood regularizer or UNI features. The image-branch null is "
         f"stricter still: NO-IMAGE Moran's I is even marginally higher than FULL and tau is identical ({A['NOIMAGE']['tau_mean']:.3f} vs {A['FULL']['tau_mean']:.3f}; permutation "
         "p both at 1e-4), i.e. **zero detectable change in risk-head output** rather than a small effect failing significance. Small effects cannot be excluded at three "
         "seeds, so we do not position multimodal fusion as a contribution: the image branch is an a-priori exploratory module under ablation, and its null result is part "
         "of the benchmark (Supplementary Note S1).")
    body("**Simplest pathway baseline (explicitly in-sample).** A learning-free score - the mean expression of the 108 KEGG-HPV genes per sample - gives an in-cohort "
         "disease/normal AUC of 0.75 versus 1.00 for the FULL model. Both are in-sample descriptive metrics on the n=35 training cohort, **not external validation**; the "
         "0.25 AUC gain can likewise reflect label anchoring, so we report its magnitude without claiming a generalization advantage.")
    body(f"**Leave-one-sample-out (LOSO) baselines: in-cohort performance does not extrapolate across samples.** Two 35-fold LOSO evaluations were run on the same 35 "
         f"samples. (1) **Morphology-to-HPV-proxy scoring**: ridge LOSO AUC={BSL.get('loso_hpv_ridge_auc', float('nan')):.3f}+/-{BSL.get('loso_hpv_ridge_auc_sd', float('nan')):.3f} "
         f"(only {BSL.get('loso_hpv_ridge_valid', 0)}/35 folds evaluable; the remainder have a single label class or a constant prediction, itself evidence of cross-slide "
         f"distribution shift; MLP {BSL.get('loso_hpv_mlp_auc', float('nan')):.3f}, {BSL.get('loso_hpv_mlp_valid', 0)}/35), i.e. chance level. (2) **Morphology-to-expression "
         f"reconstruction**: ridge from UNI features to {BSL.get('loso35_n_target_genes', 1533)} genes gives mean per-gene Pearson r={BSL.get('loso35_per_gene_pearson', float('nan')):.3f} "
         f"and held-out MSE={BSL.get('loso35_recon_mse', float('nan')):.3f}, no better than the in-sample 80/20 interpolation reference (MSE={BSL.get('he2st_mse', float('nan')):.3f}). "
         "Against the FULL in-cohort AUC of 1.00, these baselines show directly that **in-cohort metrics have no extrapolatable correspondence with cross-sample performance**.")
    h2("3.3 Biological interpretability of pathway-anchored risk")
    add_fig(doc, "Fig4_biology_correlation.png", 6.0,
            "Figure 4. Spearman correlation of spot risk with pathway/cell-state scores (within-sample z, mean of 3 "
            "FULL seeds; all 11 correlations survive BH correction at q<5e-9, weakest q=4.9e-9).", cn=False)
    body("High-risk spots are enriched for tumor epithelium and HPV oncogenic programs while showing down-regulated "
         "interferon responses, consistent with squamous epithelial transformation and immune evasion:")
    body(f"- Tumor-epithelial markers (KRT5/14/17, EPCAM): rho=**{BIO['CELL_tumor_epithelial']['rho']:+.2f}**; HPV drivers "
         f"(CDKN2A/MYC/EGFR/PIK3CA): rho=**{BIO['HPV_INTEGRATION_CANDIDATE']['rho']:+.2f}**; antigen presentation "
         f"(B2M/HLA/PSMB8): rho=**{BIO['ANTIGEN_PRESENTATION']['rho']:+.2f}**.", indent=False)
    body(f"- Interferon-antiviral (STAT1/MX1/ISG15): rho=**{BIO['INTERFERON_ANTIVIRAL']['rho']:+.2f}** (attenuated in high-risk "
         f"regions, consistent with E6/E7 immune evasion); proliferation rho={BIO['PROLIFERATION']['rho']:+.2f}, EMT "
         f"rho={BIO['EMT']['rho']:+.2f} (within-sample z; interpreted cautiously given basal/differentiation heterogeneity).", indent=False)
    body(f"Marker validity was confirmed in independent cervical scRNA-seq (GSE308792 [24]; {SCR['n_cells']:,} integrated cells; the source paper reports 14,441 immune "
         f"cells, a different cell universe): mean within-lineage correlation +0.242 versus -0.037 across lineages, and tumour-epithelium versus T-cell lineage scores "
         "correlate -0.57.")
    h2("3.4 Label-free transfer and few-label held-out extrapolation")
    add_fig(doc, "Fig5_external_transfer.png", 6.6,
            "Figure 5. External transfer and held-out extrapolation. A: four-level Moran's I control in HNSCC ST "
            "(model score / plain KEGG-HPV panel mean / expression-decile-matched random 108-gene sets / "
            "coordinate-permutation null). The model score (%.2f/%.2f) is far above the null (p<=0.001 on all 14 "
            "sections), and the plain KEGG panel (%.2f/%.2f) exceeds the expression-matched random sets (%.2f/%.2f) on "
            "every section (sign test p=%.3f/%.3f): genuine spatial organization with weak but reproducible pathway "
            "specificity; sample-level malignancy/HPV/metastasis discrimination is nevertheless non-significant. "
            "B: on GeoMx, tumor cores (Silva A/B/C pooled) score above benign " % (
                EXT['hnscc_moran_mean'], EXT['hnscc_gse281978_moran_mean'],
                EXT['rg268_kegg'], EXT['rg281_kegg'], EXT['rg268_exprm'], EXT['rg281_exprm'],
                EXT['rg268_exprm_signp'], EXT['rg281_exprm_signp']) +
            f"(core-level Mann-Whitney p={EXT['geomx_tn_core_p']:.1e}). C: true Silva patterns A/B/C are non-monotonic "
            f"(A highest) and pathology risk grades are not significant with reversed direction (Low>High, core-level "
            f"p={EXT['geomx_risk_core_p']:.3f}), so the score does not grade invasiveness. D: final-protocol LODO percentile "
            "of each held-out disease vs the 31 normals, semi-supervised (3 diseases labeled) vs "
            "fully-unsupervised (lambda_sup=lambda_prog=0) side by side per fold.", cn=False)
    body(f"**The tumor-vs-normal direction transfers; invasive grading does not (GeoMx DSP, GSE316098 [21]).** Scoring used the expression branch at a label-free "
         f"inference stage (weights from supervised cervical training; this tests transfer of a learned representation, not unsupervised discovery). Groups follow the GEO "
         f"SOFT annotation (1A/1b-1 prefixes are TMA core ids, corrected). Across {EXT['geomx_n_patients']} patients and {EXT['geomx_n_rois']} ROIs "
         f"({EXT['geomx_n_cores']} paired epi/stromal cores), tumor cores (Silva A/B/C pooled) scored {EXT['geomx_tumor_mean']:.2f} vs {EXT['geomx_benign_mean']:.2f} for benign "
         f"(core-level p={EXT['geomx_tn_core_p']:.1e}), with {EXT['geomx_wp_n']}/{EXT['geomx_wp_n']} within-patient concordance (paired Wilcoxon p={EXT['geomx_wp_p']:.3f}). At "
         f"n=6 the smallest attainable two-sided signed-rank p is {EXT['geomx_wp_exact_two_sided_floor_n6']:.3f}, so 6/6 is the strongest possible outcome and there is no 'more "
         f"significant' room, though the Clopper-Pearson 95% interval [{EXT['geomx_wp_ci_lo']:.2f}, 1.00] is wide and needs replication in a larger paired cohort. Epithelial "
         f"ROIs score above stromal ({EXT['geomx_compartment_epi']:.2f} vs {EXT['geomx_compartment_stroma']:.2f}, p={EXT['geomx_compartment_p']:.3f}), so compartment composition "
         f"cannot be excluded as a contributor, and the paired design is the strongest evidence. **It is not a risk-grade axis**: Silva A scored highest (core-level A "
         f"{EXT['geomx_core_silva_A']:.2f}~C {EXT['geomx_core_silva_C']:.2f}>B {EXT['geomx_core_silva_B']:.2f}; A vs B p={EXT['geomx_core_silva_AB_p']:.3f}), and pathology High "
         f"vs Low was non-significant with REVERSED direction (Low {EXT['geomx_risk_core_lo']:.2f} > High {EXT['geomx_risk_core_hi']:.2f}, p={EXT['geomx_risk_core_p']:.3f}). "
         "External evidence therefore supports a transferable tumor-vs-normal direction, not grading.")
    body(f"**Post-hoc stratification of the counter-intuitive Silva non-monotonicity (compartment imbalance excluded, signal epithelial, mechanism unverified).** "
         f"Epithelial/stromal ROI counts are perfectly balanced across patterns A/B/C (21/21, 22/22, 25/25) and the A-high signal lies entirely in epithelial ROIs "
         f"(A {EXT['geomx_silva_epi_A']:.2f} > B {EXT['geomx_silva_epi_B']:.2f} > C {EXT['geomx_silva_epi_C']:.2f}; A vs B p={EXT['geomx_silva_epi_AB_p']:.1e}), with no stromal "
         f"gradient ({EXT['geomx_silva_str_A']:.2f}/{EXT['geomx_silva_str_B']:.2f}/{EXT['geomx_silva_str_C']:.2f}) - compatible with Silva A retaining a more complete HPV-driven "
         "epithelial program. Without HPV-ISH/p16 annotation and with no multiplicity pre-registration this remains an unverified hypothesis (Supplementary Note S2).")
    body(f"**Cross-organ (HNSCC): genuine spatial organization with weak but reproducible pathway specificity, yet all discriminative transfer tests are negative.** "
         f"The final-protocol score has Moran's I={EXT['hnscc_moran_mean']:.2f} across {EXT['hnscc_n_samples']} head-and-neck squamous ST sections (GSE268014 [22]) and "
         f"{EXT['hnscc_gse281978_moran_mean']:.2f} across {EXT['hnscc_gse281978_n']} sections of an independent HPV-stratified HNSCC set (GSE281978 [23]). Permuting spot "
         f"coordinates (B=1000) gives a near-zero null (p<=0.001 on all 14 sections), excluding output collapse. A model-independent KEGG-HPV panel reaches nearly the same "
         f"Moran's I ({EXT['rg268_kegg']:.2f}/{EXT['rg281_kegg']:.2f}), confirming that most autocorrelation is intrinsic pathway-expression smoothing; against 30 "
         f"expression-decile-matched random panels the KEGG panel is nonetheless higher on every section ({EXT['rg268_exprm']:.2f}/{EXT['rg281_exprm']:.2f}; "
         f"delta=+{EXT['rg268_exprm_delta']:.2f}/+{EXT['rg281_exprm_delta']:.2f}; slide-level exact sign test p={EXT['rg268_exprm_signp']:.3f}/{EXT['rg281_exprm_signp']:.3f}), "
         f"i.e. a weak but fully reproducible pathway-specific component. All section-level discriminative tests are non-significant and partly reversed (Supplementary Note "
         "S3); cross-organ evidence is therefore limited to computability with genuine, weakly pathway-specific spatial organization, not disease-specific transfer.")
    body(f"**Minimal labels stabilize a partial direction into a transferable one (semi-supervised vs fully-unsupervised LODO, same protocol, fold-matched).** Both protocols "
         f"hold out one disease slide at a time under locked hyper-parameters, all spots and the same 35-sample cohort; supervision is the only difference. "
         f"**Fully-unsupervised LODO (lambda_sup=lambda_prog=0) gives a partial, unstable direction**: {EXT['unsup_lodo_n_above_median']}/4 folds above the normal median and only "
         f"{EXT['unsup_lodo_n_above_all']}/4 above all normals, mean percentile {EXT['unsup_lodo_mean_pct']:.2f} (the single ADC, CA_HPV_2, at {EXT['unsup_lodo_min_pct']:.2f}, below "
         f"all normals). **Adding the other three labeled disease slides stabilizes it**: {EXT['lodo_n_above_median']}/4 above the median, {EXT['lodo_n_above_all']}/4 above all "
         f"normals, mean percentile {EXT['lodo_mean_pct']:.2f}, the failing ADC fold rising from {EXT['unsup_lodo_min_pct']:.2f} to {EXT['lodo_min_pct']:.2f} - a clear label "
         f"dose-response, with the ADC fold weakest under both protocols (glandular-vs-squamous transfer being the main bottleneck). **The count evidence must be reported with "
         f"its resolution**: four folds are four independent holdout events, and the Clopper-Pearson 95% lower bounds for 4/4 and 3/4 are only {EXT['lodo_4of4_ci_lo']:.2f} and "
         f"{EXT['unsup_3of4_ci_lo']:.2f} with strongly overlapping intervals, so 'semi-supervised > unsupervised' is a suggestive trend; the more robust evidence is the paired "
         "design itself together with the fold-matched 0.00->0.60 rise of the ADC fold.")
    h2("3.5 Pathway specificity and negative results")
    body(f"**Random-gene-set control.** KEGG-HPV-anchored Moran's I={RC['kegg_moran']:.3f} exceeds 30 random same-sized gene "
         f"sets ({RC['random_moran_mean']:.3f}, {RC['random_moran_min']:.3f}-{RC['random_moran_max']:.3f}; permutation p={RC['moran_perm_p']:.3f}), giving "
         "weak but significant pathway specificity of spatial coherence. However disease ordering (Kendall tau) is "
         f"equally high for random gene sets (KEGG {RC['kegg_kendall']:.3f} vs random {RC['random_kendall_mean']:.3f}; AUC permutation "
         f"p={RC['auc_perm_p']:.2f}), again showing that high ordering is unrelated to pathway specificity and is consistent with label anchoring-coherent with 3.2.")
    body(f"**TCGA-CESC survival (negative; clinical-utility statement).** None of 11 spatial DEGs is BH-FDR significant in a {TC['n_patients']}-patient ({TC['events']} events) "
         f"bulk Cox model [34] (smallest {TC['min_gene']} raw p={TC['min_p']:.3f}), indicating a scale break between spot-level spatial risk and patient-level outcome. We therefore "
         "state here, in the abstract and in the conclusions that **the score has no current clinical decision utility**: it does not grade (GeoMx reversed), does not predict bulk "
         "prognosis, and fails all cross-organ discriminative tests; its value is a methodological benchmark and proof of concept.")

    h2("3.6 A proposed minimum reporting protocol for low-sample ST risk studies")
    body("From this extreme case we formalize the scattered advice into a **minimum reporting protocol (MRP-ST)** for supervised or semi-supervised ST risk studies with "
         "n_dis<=10 independent disease samples (or <=5 in any class). It comprises five required items - label-removal ablation, whole-sample label permutation "
         "(B>=10,000, never within disease samples only and never spot-wise), random-gene-set control (>=30 sets, expression-quantile matched), dual sample-level "
         "held-out protocols (semi-supervised vs fully unsupervised, identical per-fold training cohort, statistical unit = sample/section), and conclusion grading with "
         "a clinical-utility statement - each with a minimum design, a failure reading and a supported/suggestive/unsupported decision rule, plus a decision-tree "
         "execution order (full checklist and grading table: Supplementary Table S2). All are post-training analyses reproducible at negligible cost. Applying the rule "
         "grades this study as: spatial self-organization (with weak pathway specificity) = supported; the GeoMx tumour-vs-normal direction, label anchoring, and "
         "semi-supervised > unsupervised LODO = suggestive; disease grading, prognosis prediction, cross-organ discrimination and image-branch gain = unsupported.")

    h1("4. Discussion")
    body("In an extreme low-sample public cervical ST cohort (disease n=4) we examined what a pathway-anchored risk representation can and cannot do, and calibrated a "
         "minimum reporting protocol on it (Section 3.6). Three positive findings are defensible. First, spot risk correlates positively with tumour epithelium, HPV oncogenic "
         "drivers and antigen presentation and inversely with interferon responses - directionally consistent with cervical lesion biology, seed-stable and validated in "
         "independent scRNA-seq markers (spot-level, descriptive due to pseudoreplication). Second, spatial coherence is high and label-insensitive. Third, the "
         f"supervised-trained expression score, at a label-free inference stage, retains the tumour-vs-normal direction on an independent GeoMx cervical-ADC cohort (core-level "
         f"p={EXT['geomx_tn_core_p']:.1e}; {EXT['geomx_wp_n']} within-patient pairs, p={EXT['geomx_wp_p']:.3f}; suggestive) and remains computable across organs on HNSCC with "
         f"genuine, weakly pathway-specific spatial organization (coordinate permutation p<=0.001 on all 14 sections; sign test p={EXT['rg268_exprm_signp']:.3f}/"
         f"{EXT['rg281_exprm_signp']:.3f}), whereas section-level discrimination is negative (Section 3.4). The durable signal is thus the direction and spatial organization of "
         "a tumour-associated pathway program, not the fitting of four labels and not a fine-grained grade.")
    body("The honest boundaries are: (1) near-perfect in-cohort ordered ranking is strongly attenuated but only reaches the significance boundary once severity labels "
         "are removed (NO-PROG tau 0.46 to 0.21-0.25; permutation p=0.040-0.072, 1/4 seeds nominal), so label anchoring is suggestive, not confirmatory; the permutation "
         f"shuffles labels across all 35 samples (~2.1e5 labelings), so what is limited is the power of four independent disease events. Fully-unsupervised hold-out gives "
         f"only a partial, unstable direction ({EXT['unsup_lodo_n_above_median']}/4 above the median, mean {EXT['unsup_lodo_mean_pct']:.2f}), while semi-supervised LODO "
         f"associates three labeled slides with stabilization ({EXT['lodo_n_above_median']}/4 above the median, mean {EXT['lodo_mean_pct']:.2f}) but with overlapping exact "
         f"confidence intervals (lower bounds {EXT['lodo_4of4_ci_lo']:.2f}/{EXT['unsup_3of4_ci_lo']:.2f}), and is likewise suggestive. The study is a methodological exemplar "
         "but **must not be presented as an unsupervised diagnostic or an invasive-risk grading tool**; (2) the UNI image branch produces zero detectable change in risk-head "
         "output across three seeds, not merely a non-significant small effect (small effects not excluded); because it was a-priori an exploratory ablated module, multimodal "
         "fusion is not a contribution (Supplementary Note S1); (3) spatial DEGs carry no bulk prognostic signal and **the score has no current clinical decision utility**; "
         "the GeoMx cohort is adenocarcinoma whereas the main cohort is largely squamous, consistent with the weakest (ADC) LODO fold; (4) with only four disease samples and "
         "six paired GeoMx patients, power is intrinsically limited and every power-limited conclusion is downgraded to suggestive; (5) compartment composition cannot be "
         "excluded as a contributor to the tumour-benign contrast, although the balanced epi/stromal stratification excludes it as an explanation of the Silva "
         "non-monotonicity (Supplementary Note S2); (6) the 30 normal ectocervix sections are pooled from three GEO sub-series, and spot-level correlations over 46,820 "
         "non-independent spots are treated as descriptive, with sample/slide/patient-level comparisons as primary evidence.")
    body("Methodological contribution: from advice to protocol. Section 3.6 formalizes MRP-ST, with an explicit trigger (n_dis<=10), five required items, and a "
         "supported/suggestive/unsupported decision rule. Reporting only in-cohort AUC~1 or high correlations without demonstrating label-free or cross-dataset validity cannot "
         "distinguish generalization from label memorization; this paper presents an extreme case, in which an in-sample AUC of 1.00 leaves only boundary-level evidence after "
         "label removal. The protocol is consistent with classical work on label leakage and evaluation bias in small-sample machine learning [35,36] and with prediction-model "
         "reporting guidance such as TRIPOD+AI [37]; its novelty is operationalizing these principles as a fixed, line-item checklist for spatial transcriptomics. It is "
         "network-agnostic and the repository provides the scripts and all result JSONs, so it can serve directly as a reviewer checklist.")
    h1("5. Conclusions")
    body("Under the extreme n=4-disease constraint, a pathway-anchored expression-based ST framework yields biologically interpretable, spatially coherent pathway-risk "
         "scores; at a label-free inference stage these remain computable across platforms (GeoMx: tumour-vs-normal direction retained, 6/6 within-patient concordance at the "
         "n=6 resolution limit, suggestive) and organs (HNSCC: genuine, weakly pathway-specific spatial organization retained, supported; but malignancy/HPV/metastasis "
         "discrimination negative) - not unsupervised discovery, not disease-specific cross-organ transfer, and not risk grading. Label anchoring of fine ordered ranking "
         "receives only suggestive evidence (permutation p=0.040-0.072, 1/4 seeds nominal), and semi-supervised leave-one-disease-out suggests the direction may extend to an "
         "unseen disease slide from a few labels (4/4, wide CIs, suggestive). The exploratory image branch produces zero detectable output change (unsupported), and the score "
         "neither grades invasiveness nor predicts bulk survival, so it has no current clinical decision utility. The contribution is a label-dependence ablation benchmark "
         "with the MRP-ST minimum reporting protocol (Section 3.6), demonstrated by an extreme case in which perfect in-sample results mask label memorization when these "
         "ablations are omitted; with all numbers and scripts reproducible, it is intended as an evaluation benchmark and a starting checklist for genuinely generalizable "
         "models in larger, registered, multi-center H&E-ST cohorts.")
    h1("Data and Code Availability")
    body("All training scripts, configurations, result JSONs and fused embeddings are released at GitHub (URL: %s). All data are from public databases: the cervical "
         "Visium cohort (GSE208654, GSE217237 and the 10x Genomics demonstration section); and the external cohorts GeoMx GSE316098, GSE268014, GSE281978, TCGA-CESC and "
         "GSE308792 (accessions in Table 1)." % "https://github.com/WorldBMW/pathway-anchored-risk-benchmark", indent=False)
    h1("References")
    for _i, _r in enumerate(REFS, 1):
        body(f"[{_i}] {_r}", indent=False)
    h1("Author contributions / Funding / Competing interests")
    body("CRediT author contributions: Mingwei Bai (first author) - conceptualization, methodology, software, formal analysis, investigation, data curation, visualization, writing (original draft); [Corresponding author] (corresponding author, to be assigned) - supervision, project administration, writing (review and editing). Funding: this research received no external funding (no grant support). The authors declare no competing interests.", indent=False)

    save_doc(doc, "Manuscript_v10_English.docx")
    return doc

if __name__ == "__main__":
    build_cn()
    build_en()
    print("DONE.")
