# -*- coding: utf-8 -*-
"""gen_word_v10.py — CSBJ/CMPB 重构版（v10）

定位（无硬伤，数据可辩护）：通路锚定的多模态空间转录组框架，在极端小样本(n=4 疾病)
宫颈病变队列中，(i) 给出生物学可解释、空间一致的通路风险表征；(ii) 通过多种子同队列
消融严格界定：疾病有序排序依赖少量标签锚定（NO-PROG 后 Kendall τ 0.46→0.25，
4 种子中 3 个名义显著、强度处于 n=4 功效边界）；图像分支提升空间一致性（Moran +0.07）
但不改变疾病排序（τ 不变），须按一致性/排序两个轴分别定级；(iii) 通路表达评分在推理
无标签下跨平台(GeoMx)保留肿瘤-良性秩判别，但评分符号相对宫颈训练队列反转（肿瘤更低），
属“秩判别迁移、校准符号不迁移”；跨器官(HNSCC)可计算并保留真实、含弱通路特异性的空间
自组织，但恶性/HPV/转移判别检验为阴性。
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
OUT = Path(os.environ.get("CMPB_OUT_DIR", ROOT / "papers" / "07_CSBJ_v10"))
FIG = Path(os.environ.get("CMPB_FIG_DIR", OUT / "Figures"))
CN_OUT_NAME = os.environ.get("CMPB_CN_NAME", "Manuscript_v10_中文.docx")
EN_OUT_NAME = os.environ.get("CMPB_EN_NAME", "Manuscript_v10_English.docx")
OUT.mkdir(parents=True, exist_ok=True)

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
# simplest pathway baseline: per-sample mean of the KEGG-HPV genes vs FULL model
# sample-level disease-vs-normal AUC (results/baseline_hpv_gene_mean_vs_model.json).
# The expression matrix is unchanged by the 2026-09-15 image-registration fix, so
# this artifact stays valid; the model AUC=1.00 was re-verified on all new FULL npz.
BGM = {}
_bgmp = ROOT / 'results' / 'baseline_hpv_gene_mean_vs_model.json'
if _bgmp.exists():
    BGM = json.load(open(_bgmp, encoding='utf-8'))
# weakest BH q across the 11 biology correlations (used in Fig. 4 caption)
WEAKEST_Q_SET = max(BIO, key=lambda k: BIO[k]['q_max'])
WEAKEST_Q = BIO[WEAKEST_Q_SET]['q_max']
# image-branch coherence delta (FULL - NOIMAGE), descriptive (seed sets differ)
IMG_DMORAN = A['FULL']['moran_mean'] - A['NOIMAGE']['moran_mean']
# per-fold percentile dicts (semi / fully-unsupervised LODO, final protocol)
LODO_F = {f['holdout']: f['percentile_vs_normal'] for f in EXT['lodo_folds']}
UNLODO_F = {f['holdout']: f['percentile_vs_normal'] for f in EXT.get('unsup_lodo_folds', [])}
# per-seed NO-PROG strings + simplest-baseline AUCs (module-level so build_cn/build_en share them)
_np = A['NOPROG']
_np_taus = "/".join(f"{t:.3f}" for t in _np.get('taus', []))
_np_pp = "/".join(f"{p:.3f}" for p in _np.get('tau_perm_ps', []))
_np_mwus = "/".join(f"{p:.3f}" for p in _np.get('mwu_ps', []))
_bgm_auc = BGM.get('baseline_hpv_gene_mean_auc', float('nan'))
_mra = BGM.get('model_risk_auc', float('nan'))

def f2(x): return f"{x:.2f}"
def f3(x): return f"{x:.3f}"
def pm(m, s): return f"{m:.3f} ± {s:.3f}"

# ---------- references (Vancouver; shared by CN/EN manuscripts) ----------
REFS = [
 "H. Sung, J. Ferlay, R. L. Siegel, M. Laversanne, I. Soerjomataram, A. Jemal, et al., Global cancer statistics 2020: GLOBOCAN estimates of incidence and mortality worldwide for 36 cancers in 185 countries, CA Cancer J. Clin. 71 (2021) 209–249. https://doi.org/10.3322/caac.21660.",
 "T. Malagón, E. L. Franco, R. Tejada, S. Vaccarella, Epidemiology of HPV-associated cancers past, present and future: towards prevention and elimination, Nat. Rev. Clin. Oncol. 21 (2024) 522–538. https://doi.org/10.1038/s41571-024-00904-z.",
 "Cancer Genome Atlas Research Network, Integrated genomic and molecular characterization of cervical cancer, Nature 543 (2017) 378–384. https://doi.org/10.1038/nature21386.",
 "N. Sinha, O. D. Lara, K. Dessources, E. P. Jones, L. H. Clark, R. Broaddus, et al., Identification of low-risk cases of invasive endocervical adenocarcinoma with Silva pattern-based classification: a systematic review and meta-analysis, Gynecol. Oncol. Rep. 59 (2025) 101764. https://doi.org/10.1016/j.gore.2025.101764.",
 "M. Chen, L. Han, Y. Wang, Y. Chen, A. Zheng, Association between Silva pattern-based classification and endocervical adenocarcinoma: a systematic review and meta-analysis, Int. J. Gynecol. Cancer 34 (2024) 1704–1710. https://doi.org/10.1136/ijgc-2024-005639.",
 "I. Alvarado-Cabrero, C. Parra-Herran, S. Stolnicu, A. Roma, E. Oliva, A. Malpica, The Silva pattern-based classification for HPV-associated invasive endocervical adenocarcinoma and the distinction between in situ and invasive adenocarcinoma: relevant issues and recommendations from the International Society of Gynecological Pathologists, Int. J. Gynecol. Pathol. 40 (2021) S48–S65. https://doi.org/10.1097/PGP.0000000000000735.",
 "A. Powell, A. Hodgson, P. A. Cohen, J. T. Rabban, K. J. Park, W. G. McCluggage, et al., Improved risk prediction in human papillomavirus-associated endocervical adenocarcinoma through assessment of binary Silva pattern-based classification: an international multicenter retrospective observational study led by the International Society of Gynecological Pathologists (ISGyP), Int. J. Gynecol. Pathol. 43 (2024) 436–446. https://doi.org/10.1097/PGP.0000000000001033.",
 "P. L. Ståhl, F. Salmén, S. Vickovic, A. Lundmark, J. F. Navarro, J. Magnusson, et al., Visualization and analysis of gene expression in tissue sections by spatial transcriptomics, Science 353 (2016) 78–82. https://doi.org/10.1126/science.aaf2403.",
 "L. Moses, L. Pachter, Museum of spatial transcriptomics, Nat. Methods 19 (2022) 534–546. https://doi.org/10.1038/s41592-022-01409-2.",
 "J. R. Moffitt, E. Lundberg, H. Heyn, The emerging landscape of spatial profiling technologies, Nat. Rev. Genet. 23 (2022) 741–759. https://doi.org/10.1038/s41576-022-00515-3.",
 "D. Bressan, G. Battistoni, G. J. Hannon, The dawn of spatial omics, Science 381 (2023) eabq4964. https://doi.org/10.1126/science.abq4964.",
 "R. J. Chen, T. Ding, M. Y. Lu, D. F. K. Williamson, G. Jaume, A. H. Song, et al., Towards a general-purpose foundation model for computational pathology, Nat. Med. 30 (2024) 850–862. https://doi.org/10.1038/s41591-024-02857-3.",
 "E. Vorontsov, A. Bozkurt, P. Cassonnet, G. Bontempi, P. Mangeol, C. Rémy, et al., A foundation model for clinical-grade computational pathology and rare cancers detection, Nat. Med. 30 (2024) 2924–2935. https://doi.org/10.1038/s41591-024-03141-0.",
 "H. Xu, N. Usuyama, J. Bagga, S. Zhang, W. Xu, U. Rao, et al., A whole-slide foundation model for digital pathology from real-world data, Nature 630 (2024) 181–188. https://doi.org/10.1038/s41586-024-07441-w.",
 "B. Schmauch, A. Romagnoni, E. Pronier, C. Saillard, P. Maillé, J. Calderaro, et al., A deep learning model to predict RNA-Seq expression of tumours from whole slide images, Nat. Commun. 11 (2020) 3877. https://doi.org/10.1038/s41467-020-17678-4.",
 "B. He, L. Bergenstråhle, L. Stenbeck, A. Abid, A. Andersson, Å. Borg, et al., Integrating spatial gene expression and breast tumour morphology via deep learning, Nat. Biomed. Eng. 4 (2020) 827–834. https://doi.org/10.1038/s41551-020-0578-x.",
 "W. Chen, P. Zhang, T. N. Tran, Y. Xiao, S. Li, V. V. Shah, et al., A visual-omics foundation model to bridge histopathology with spatial transcriptomics, Nat. Methods 22 (2025) 1568–1582. https://doi.org/10.1038/s41592-025-02707-1.",
 "E. Redekop, M. Pleasure, Z. Wang, V. Ivezic, K.E. Flores, B. Emert, A. Sisk, W. Speier, C.W. Arnold, SPADE: spatial transcriptomics and pathology alignment using a mixture of data experts for an expressive latent space, Med. Image Anal. 113 (2026) 104197. https://doi.org/10.1016/j.media.2026.104197.",
 "K. Hemker, A. H. Song, C. Almagro-Pérez, G. Jaume, S. J. Wagner, A. Vaidya, et al., Towards spatial transcriptomics-driven pathology foundation models, arXiv preprint arXiv:2602.14177 (2026). https://doi.org/10.48550/arXiv.2602.14177.",
 "M. Lee, J. Kim, J. Yun, S. Yu, J. Jang, MINT: molecularly informed training with spatial transcriptomics supervision for pathology foundation models, arXiv preprint arXiv:2603.07895 (2026). https://doi.org/10.48550/arXiv.2603.07895.",
 "Y. Lin, L. Luo, Y. Chen, X. Zhang, Z. Wang, W. Yang, et al., ST-Align: multi-scale image-gene foundation modeling for spatial transcriptomics via spot-niche alignment, in: Proc. International Conference on Learning Representations (ICLR), 2026. https://openreview.net/forum?id=EWzPy228cM.",
 "T. Huang, T. Liu, M. Babadi, R. Ying, W. Jin, STPath: a generative foundation model for integrating spatial transcriptomics and whole-slide images, npj Digit. Med. 8 (2025) 659. https://doi.org/10.1038/s41746-025-02020-3.",
 "H. Cui, C. Wang, H. Maan, K. Pang, F. Luo, N. Duan, et al., scGPT: toward building a foundation model for single-cell multi-omics using generative AI, Nat. Methods 21 (2024) 1470–1480. https://doi.org/10.1038/s41592-024-02201-0.",
 "Q. Blampey, H. Benkirane, N. Bercovici, K. Mulder, G. Gessain, F. Ginhoux, et al., Novae: a graph-based foundation model for spatial transcriptomics data, Nat. Methods 22 (2025) 2539–2550. https://doi.org/10.1038/s41592-025-02899-6.",
 "M. Varrone, D. Tavernari, A. Santamaria-Martínez, L. A. Walsh, G. Ciriello, CellCharter reveals spatial cell niches associated with tissue remodeling and cell plasticity, Nat. Genet. 56 (2024) 74–84. https://doi.org/10.1038/s41588-023-01588-4.",
 "B. Li, W. Zhang, C. Guo, H. Xu, L. Li, M. Fang, et al., Benchmarking spatial and single-cell transcriptomics integration methods for transcript distribution prediction and cell type deconvolution, Nat. Methods 19 (2022) 662–670. https://doi.org/10.1038/s41592-022-01480-9.",
 "C. R. Merritt, G. T. Ong, S. Church, K. Barker, P. Danaher, G. Geiss, et al., Multiplex digital spatial profiling of proteins and RNA in fixed tissue, Nat. Biotechnol. 38 (2020) 586–599. https://doi.org/10.1038/s41587-020-0472-9.",
 "M. L. Axelrod, R. Zhou, L. Sun, Spatial transcriptomic landscape of invasion patterns in human papillomavirus-associated endocervical adenocarcinoma, Sci. Rep. 16 (2026) 13246. https://doi.org/10.1038/s41598-026-43717-z.",
 "D. Simkin, T. F. Barrett, L. Zhang, M. J. Moore, A. C. Greenwald, N. Galili, et al., Spatial analysis of head and neck cancer identifies two ecosystems with distinct modes of epithelial-to-mesenchymal transition, Nat. Genet. (2026). https://doi.org/10.1038/s41588-026-02723-7.",
 "H. Lee, S. Park, J. H. Yun, C. Seo, J. M. Ahn, H. Y. Cha, et al., Deciphering head and neck cancer microenvironment: single-cell and spatial transcriptomics reveals human papillomavirus-associated differences, J. Med. Virol. 96 (2024) e29386. https://doi.org/10.1002/jmv.29386.",
 "Y. Yuan, D. Sun, M. Yang, Y. Xia, C. Yuan, X. Wang, Profiling of immune cell subsets and functional characteristics of cervical cancer based on single cell RNA sequencing, Front. Immunol. 16 (2025) 1658705. https://doi.org/10.3389/fimmu.2025.1658705.",
 "M. Kanehisa, M. Furumichi, Y. Sato, Y. Matsuura, M. Ishiguro-Watanabe, KEGG: biological systems database as a model of the real world, Nucleic Acids Res. 53 (2025) D672–D677. https://doi.org/10.1093/nar/gkae909.",
 "P. A. P. Moran, Notes on continuous stochastic phenomena, Biometrika 37 (1950) 17–23. https://doi.org/10.2307/2332142.",
 "M. G. Kendall, A new measure of rank correlation, Biometrika 30 (1938) 81–93. https://doi.org/10.2307/2332226.",
 "H. B. Mann, D. R. Whitney, On a test of whether one of two random variables is stochastically larger than the other, Ann. Math. Stat. 18 (1947) 50–60. https://doi.org/10.1214/aoms/1177730491.",
 "D. A. Barbie, P. Tamayo, J. S. Boehm, S. Y. Kim, S. E. Moody, I. F. Dunn, et al., Systematic RNA interference reveals that oncogenic KRAS-driven cancers require TBK1, Nature 462 (2009) 108–112. https://doi.org/10.1038/nature08460.",
 "C. R. Harris, K. J. Millman, S. J. van der Walt, R. Gommers, P. Virtanen, D. Cournapeau, et al., Array programming with NumPy, Nature 585 (2020) 357–362. https://doi.org/10.1038/s41586-020-2649-2.",
 "Y. Benjamini, Y. Hochberg, Controlling the false discovery rate: a practical and powerful approach to multiple testing, J. R. Stat. Soc. B 57 (1995) 289–300. https://doi.org/10.1111/j.2517-6161.1995.tb02031.x.",
 "F. Pedregosa, G. Varoquaux, A. Gramfort, V. Michel, B. Thirion, O. Grisel, et al., Scikit-learn: machine learning in Python, J. Mach. Learn. Res. 12 (2011) 2825–2830.",
 "P. Virtanen, R. Gommers, T. E. Oliphant, M. Haberland, T. Reddy, D. Cournapeau, et al., SciPy 1.0: fundamental algorithms for scientific computing in Python, Nat. Methods 17 (2020) 261–272. https://doi.org/10.1038/s41592-019-0686-2.",
 "D. Mo, H. Cao, S. Lai, J. Luo, W. Ye, Spatial transcriptomic landscape and cellular neighborhood heterogeneity in cervical cancer: integrative single-cell and spatial RNA sequencing analysis, Discov. Oncol. 16 (2025) 2040. https://doi.org/10.1007/s12672-025-03788-2.",
 "Y. Wu, B. Wei, Z. Wei, H. Wang, Y. Liu, D. Xu, et al., Single-cell and spatial transcriptomic profiling reveals distinct tumor microenvironment dynamics in cervical adenocarcinoma and squamous cell carcinoma, Commun. Biol. 9 (2025) 46. https://doi.org/10.1038/s42003-025-09310-2.",
 "D. R. Cox, Regression models and life-tables, J. R. Stat. Soc. B 34 (1972) 187–220. https://doi.org/10.1111/j.2517-6161.1972.tb00899.x.",
 "S. Steinert, V. Ruf, D. Dzsotjan, N. Großmann, A. Schmidt, J. Kuhn, et al., A refined approach for evaluating small datasets via binary classification using machine learning, PLoS ONE 19 (2024) e0301276. https://doi.org/10.1371/journal.pone.0301276.",
 "S. Whalen, J. Schreiber, W. S. Noble, K. S. Pollard, Navigating the pitfalls of applying machine learning in genomics, Nat. Rev. Genet. 23 (2022) 169–181. https://doi.org/10.1038/s41576-021-00434-9.",
 "S. Kapoor, A. Narayanan, Leakage and the reproducibility crisis in machine-learning-based science, Patterns 4 (2023) 100804. https://doi.org/10.1016/j.patter.2023.100804.",
 "G. Varoquaux, V. Cheplygina, Machine learning for medical imaging: methodological failures and recommendations for the future, npj Digit. Med. 5 (2022) 48. https://doi.org/10.1038/s41746-022-00592-y.",
 "G. S. Collins, K. G. M. Moons, P. Dhiman, R. D. Riley, A. L. Beam, B. Van Calster, et al., TRIPOD+AI statement: updated guidance for reporting clinical prediction models that use regression or machine learning methods, BMJ 385 (2024) e078378. https://doi.org/10.1136/bmj-2023-078378.",
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
        p.paragraph_format.keep_with_next = True
        _rf(p.add_run(caption), 10.5, True, '黑体' if cn else 'Times New Roman')
    t = doc.add_table(rows=1, cols=len(headers)); t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    tr_pr = t.rows[0]._tr.get_or_add_trPr()
    tbl_header = OxmlElement('w:tblHeader')
    tbl_header.set(qn('w:val'), 'true')
    tr_pr.append(tbl_header)
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
    p.paragraph_format.keep_with_next = True
    shape = p.add_run().add_picture(str(fp), width=Inches(w))
    shape._inline.docPr.set('title', name)
    shape._inline.docPr.set('descr', (caption or name)[:250])
    if caption:
        c = doc.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        c.paragraph_format.keep_together = True
        c.paragraph_format.line_spacing = 1.0
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
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.keep_together = True
    def h2(t):
        p = doc.add_paragraph(); r = p.add_run(t); _rf(r, 12.5, True, H1F)
        p.paragraph_format.space_before = Pt(8); p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.keep_together = True
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
    title("小样本空间转录组中通路锚定风险表征的标签依赖基准：\n宫颈病变跨平台研究",
          "Benchmarking label dependence of pathway-anchored risk representations in low-sample "
          "spatial transcriptomics: a cross-platform cervical study")
    doc.add_paragraph()

    h1("摘要")
    body(f"**背景与目的**：空间转录组（ST）与病理组学的多模态融合有望刻画宫颈病变微环境，但公开 ST 队列中疾病样本极少"
         f"（本研究可获得的宫颈 Visium 病变样本仅 {CO['n_disease']} 例），监督模型极易把少量疾病标签背下来，形成看似完美、实则不泛化的结果。"
         "本文既不构建诊断器、也不宣称新的生物学发现，而是检验三个问题：通路锚定的风险表征是否生物学可解释、并可在无标签推理下跨平台/跨器官计算；"
         "队列内的疾病区分究竟来自模型学习还是标签锚定；以及这些检验能否形式化为可复现的最低报告协议。")
    body(f"**方法**：在 {CO['n_samples']} 例宫颈 Visium 样本（{CO['n_normal']} 例正常、{CO['n_disease']} 例病变；共 {CO['n_spots']:,} 个 spot，"
         f"锚定 {CO['n_genes_panel']} 个 KEGG-HPV 通路基因）上，以表达-通路分支为核心、UNI 图像分支为探索性模块，"
         "施加 HPV 通路一致性正则、空间邻域约束与风险监督。所有比较共享同一队列与协议、多种子运行："
         "FULL、NO-IMAGE、NO-HPV、NO-NEIGH、NO-PROG。空间一致性用 Moran's I，疾病有序排序用样本级 Kendall τ，"
         "并将严重度标签向量在全部 35 个样本上整体置换 B=10,000 次。外部验证的推理阶段仅用表达分支、不读取任何宫颈标签，"
         "外部队列为 GeoMx DSP（GSE316098）、头颈部鳞癌 ST、TCGA-CESC 与宫颈 scRNA-seq（GSE308792）。")
    body(f"**结果**：FULL 的 Moran's I={A['FULL']['moran_mean']:.3f}±{A['FULL']['moran_sd']:.3f}、τ={A['FULL']['tau_mean']:.3f}"
         f"（置换 p={A['FULL']['tau_perm_p_min']:.0e}–{A['FULL']['tau_perm_p_max']:.0e}）。去除严重度标签（NO-PROG）后 "
         f"τ 降至 {A['NOPROG']['tau_mean']:.3f}±{A['NOPROG']['tau_sd']:.3f}、p={A['NOPROG']['tau_perm_p_min']:.3f}–"
         f"{A['NOPROG']['tau_perm_p_max']:.3f}（{A['NOPROG']['tau_perm_nsig']}/{A['NOPROG']['n_seeds']} 种子名义显著，强度处于 n=4 功效边界），"
         "标签锚定为提示性证据。空间一致性对标签与邻域正则不敏感；图像分支提升 Moran's I "
         f"+{IMG_DMORAN:.2f}（{A['NOIMAGE']['moran_mean']:.3f}→{A['FULL']['moran_mean']:.3f}），但 τ 不变"
         f"（{A['NOIMAGE']['tau_mean']:.3f} vs {A['FULL']['tau_mean']:.3f}）——形态学贡献空间平滑、不贡献疾病排序。"
         f"评分与肿瘤上皮（{BIO['CELL_tumor_epithelial']['rho']:+.2f}）、HPV 致癌驱动（{BIO['HPV_INTEGRATION_CANDIDATE']['rho']:+.2f}）、"
         f"抗原呈递（{BIO['ANTIGEN_PRESENTATION']['rho']:+.2f}）正相关，与干扰素-抗病毒（{BIO['INTERFERON_ANTIVIRAL']['rho']:+.2f}）负相关。"
         f"GeoMx 中肿瘤区评分**低于**良性（{EXT['geomx_tumor_mean']:.2f} vs {EXT['geomx_benign_mean']:.2f}，芯级 p={EXT['geomx_tn_core_p']:.1e}；"
         f"{EXT['geomx_wp_n']}/{EXT['geomx_wp_n']} 患者内配对方向一致，p={EXT['geomx_wp_p']:.3f}，已达 n=6 精确检验下限）——"
         "肿瘤-良性秩判别保留，但校准符号相对训练队列反转，评分不构成侵袭性分级轴；"
         "HNSCC 跨器官评分保持真实空间组织（坐标置换 p≤0.001），但恶性/HPV/转移判别全部阴性；"
         "TCGA 生存（302 例、72 事件）与留一样本基线（AUC 0.497±0.021）同样阴性。")
    body("**结论**：在仅 4 例疾病的条件下，该框架可给出可解释、空间一致的通路风险表征；无标签推理下跨平台秩判别可保留、"
         "但评分符号不迁移，精细的有序排序仅为提示性。我们将这些检验形式化为 MRP-ST 最低报告协议"
         "（含 supported/suggestive/unsupported 分级）；该评分当前不具有任何临床决策效用。")
    p = doc.add_paragraph(); _rf(p.add_run("关键词："), 11.5, True, '宋体')
    _rf(p.add_run("空间转录组；宫颈病变；HPV 通路；小样本学习；标签依赖消融；报告规范"), 11.5)

    h1("1 引言")
    body("宫颈癌是全球女性第四大恶性肿瘤[1]，主要病因是高危型 HPV 持续感染[2]；TCGA 多组学已刻画其分子图谱[3]，"
         "而宫颈腺癌的 Silva A/B/C 间质浸润模式是与淋巴结转移及预后直接相关的组织学分级体系[4-7]。随着空间转录组（如 10x Visium[8]，技术全景综述见[9-11]）"
         "与数字病理基础模型（如 UNI[12]、Virchow[13]、GigaPath[14]）成熟，将表达、图像与通路先验联合，有望在组织原位刻画上皮转化与微环境重塑。"
         "一个被普遍低估的方法学风险是：公开 ST 数据中疾病样本极少——本研究可聚合的宫颈 Visium 病变样本仅 4 例（1 例 HSIL、3 例鳞癌/腺癌）。"
         "在此规模下，任何带监督的风险模型都可能把 4 个标签背下来，给出看似完美、实为标签记忆而非泛化的队列内区分。")
    body("通路生物学提供了天然的归纳偏置：HPV 致癌是一条由 E6/E7 驱动、经 p53/Rb 失活、抗原呈递改变与免疫逃逸展开的保守程序。"
         "把表征锚定到这条通路，理论上应得到生物学可解释、空间平滑、并可迁移到其它 HPV/上皮转化背景的评分。这些预期是否成立，必须用对照检验，不能假设。")
    body("**相关工作与本文定位**：HE2RNA[15] 与 ST-Net[16] 率先从 H&E 预测（空间）表达；OmiCLIP[17] 将视觉-组学对齐扩展为病理-ST 基础模型；"
         "SPADE[18]、SEAL[19]、MINT[20] 在 10⁵–10⁶ 配准 spot 上以 ST 监督微调病理编码器；ST-Align[21] 在 spot/微龛层做图像-基因对齐；"
"STPath[22] 跨 17 个器官预测近 4 万基因；scGPT[23] 与 Novae[24] 把基础模型规模推到千万级细胞，CellCharter[25] 可跨平台识别细胞微龛。"
         "现有 ST 流程基准衡量的是整合精度[26]，而非标签依赖；这些工作均以大样本为前提，目标是表示学习或分子预测，既未覆盖疾病样本仅 4 例的极端场景，"
         "也不回答队列内完美区分究竟来自学习还是标签记忆。本文不与它们在规模或精度上竞争，而是把问题界定为**任务端可迁移的通路风险表征**与配套的去标签消融基准。")
    body("**本研究的贡献与定位（明确不作为诊断主张，亦不主张多模态融合为核心贡献）**：(1) 在 35 例宫颈 Visium 上以同队列、多种子、全量 spot 协议"
         "运行一套标签依赖消融基准，UNI 图像分支从一开始即被定位为预先纳入、接受消融检验的探索性模块（其对空间一致性的增益与对疾病排序的零增益分轴报告，见 3.2）；"
         "(2) 用 FULL/NO-IMAGE/NO-HPV/NO-NEIGH/NO-PROG 消融解耦“空间一致性”“可解释性”“疾病有序排序”三个属性的来源；"
         "(3) 在推理无标签条件下检验跨平台（GeoMx DSP[27]）与跨器官（HNSCC）迁移，并以正确的 GEO Silva 注释区分方向与分级；"
         "(4) 诚实报告阴性结果，并形式化为一套带结论分级的最低报告协议（§3.6）。")

    h1("2 材料与方法")
    h2("2.1 数据队列")
    add_table(doc,
        ["队列", "类型", "规模", "用途"],
        [["宫颈 Visium 聚合队列（GSE208654 + GSE217237 + 10x 公开示例）", "ST（10x Visium）", f"{CO['n_samples']} 例（{CO['n_normal']} 正常 / {CO['n_disease']} 病变）；{CO['n_spots']:,} spot", "主模型与同队列消融"],
         ["GSE316098 [28]", "GeoMx DSP（宫颈腺癌）[27]", f"{EXT['geomx_n_patients']} 例患者（WU-01~WU-07）/ {EXT['geomx_n_rois']} ROI（{EXT['geomx_n_cores']} 组织区）", "跨平台：肿瘤-良性秩判别（符号反转；非分级）"],
         ["GSE268014 [29]", "ST（头颈部鳞癌；Simkin 等）", f"{EXT['hnscc_n_samples']} 例", "跨器官空间自组织（判别检验阴性）"],
         ["GSE281978 [30]", "ST（HPV± HNSCC；Lee 等）", f"{EXT['hnscc_gse281978_n']} 例", "跨器官复制（HPV/转移判别阴性）"],
         ["TCGA-CESC [3]", "bulk RNA-seq", f"{TC['n_patients']} 例 / {TC['events']} 事件", "生存迁移（阴性）"],
         ["GSE308792 [31]", "scRNA-seq（宫颈）", f"{SCR['n_cells']:,} 细胞", "细胞 marker 有效性"]],
        caption="表1 数据队列总览")
    body("注：表中“例”指本研究实际分析的切片数。GSE268014 原研究共 26 例，本研究使用其中 8 张切片；GSE281978 的 ST 切片共 6 张，全部使用。", indent=False)
    body("宫颈 Visium 队列经符号链接聚合自三个公开来源，共 35 例（31 正常 + 4 病变）：①**GSE208654**（Guo 等，Clin Transl Med 2023;13(3):e1219）4 例——"
         "N_HPV（正常）、HSIL_HPV、CA_HPV_1（鳞癌）、CA_HPV_2（腺癌）；②**GSE217237** 超系列下的 30 例正常宫颈外口 Visium（P001–P030；"
         "分属 GSE290350/GSE299708/GSE300112 三个子系列，来自 HIV 感染、DMPA 避孕与微生物组研究，该异质性在局限性中说明）；"
         "③10x Genomics 公开的宫颈癌 FFPE Visium 示例切片（Visium_FFPE_Human_Cervical_Cancer；cervical_cancer_1，鳞癌）。组织学标签为正常/HSIL/癌（严重度 0/1/2）。"
         "本研究所有训练/消融均在同一 35 例、全量 46,820 spot、统一基因面板（4,991 基因，KEGG-HPV 通路子面板 108 基因，其中 107 个在该 Visium 面板中可检测）下进行。"
         "正常/HSIL/鳞癌/腺癌组织学谱的代表性 H&E 全片与高倍视野见图 1a。")
    h2("2.2 框架与损失")
    body("框架由三路构成：(a) **表达分支**：基因表达编码为潜变量并重构（l_rec，0.2）与潜变量正则（l_var，0.1）；"
         "(b) **图像分支（探索性、被检验模块）**：UNI[12] patch 特征编码后与表达潜变量融合，纳入目的正是检验形态信息在极端小样本下能否提供可检测增益；"
         "(c) **通路与空间先验**：KEGG-HPV（108 基因[32]）通路一致性正则 l_hpv（λ_hpv=1.0）与相邻 spot 邻域约束 l_neigh（0.3）。"
         "风险头输出 spot 级风险分，受 HPV 状态代理二分类 l_sup（5.0）与疾病严重度回归 l_prog（MSE 到 0/1/2，1.5）两项监督。")
    body("**消融定义（关键，避免误读）**：FULL 为完整配置；NO-IMAGE 关闭图像分支；NO-NEIGH 仅关闭 l_neigh、其余全部保留，用于检验高空间一致性是否来自邻域正则；"
         "NO-HPV 仅置 λ_hpv=0（HPV 代理监督 l_sup 仍开启，故只检验通路一致性正则项）；**NO-PROG 置 λ_prog=0，即训练时完全不使用疾病严重度标签**，"
         "但保留表达、图像、通路与 HPV 代理监督。留一疾病外推（LODO）在 4 个疾病样本上逐折进行，分两种协议：半监督 LODO（主报告协议）保留其余 3 个疾病的标签、"
         "仅留出目标片，报告其相对 31 个训练正常样本的风险百分位；全无监督 LODO 在该折同时置 λ_sup=λ_prog=0。"
         "**两协议在同一终协议下完成、可直接横比**：均不设 spot 上限、使用全部 spot（各折 44,039–46,241 个，两协议逐折相同），"
         "共同固定 λ_recon/λ_hpv/λ_neigh=0.2/1.0/0.3、训练队列逐折相同（各折 34 例）；唯一差别是监督项（5.0/1.5 vs 0/0），"
         "故二者差异可解释为标签的因果效应。")
    h2("2.3 评估与统计")
    body("空间一致性用 Moran's I[33]；疾病有序排序用样本级 Kendall τ[34]，其经验零分布由在全部 35 个样本上整体随机置换严重度标签向量"
         "（31 个 0、1 个 1、3 个 2）后重新聚合 spot 风险得到，B=10,000（对照见 Supplementary Table S1；秩效应仍仅由 4 个疾病事件驱动，功效低）。"
         "疾病 vs 正常用单尾 Mann-Whitney U[35]；GeoMx 患者内比较用双侧配对 Wilcoxon 符号秩检验（n=6 时最小可达 p=2/2⁶=0.031），"
         "并给出一致性比例的 Clopper-Pearson 精确 95% CI；LODO 的 k/4 计数同样报告该区间。下游评分用基于秩的 ssGSEA[36]（纯 NumPy[37]），"
         "每样本内 z 标准化后与风险做 Spearman 相关，BH 法[38]控制 FDR；分类指标由 scikit-learn[39] 计算、统计检验由 SciPy[40] 完成。"
         "**外部迁移的推理阶段仅用表达分支、不读取任何宫颈标签；权重仍来自宫颈队列的监督训练（λ_sup=5.0、λ_prog=1.5）**，"
         "故检验的是已学得表征的可迁移性，而非无监督发现——后者由全无监督 LODO 单独检验。外部推理统一使用 "
         "`results/checkpoint_FULL_DEPLOY_FAST_seed42.pt`（seed 42）。**GSE316098 的 Silva/风险分组以 GEO SOFT 元数据为准**（列名前缀 1A/1b-1 是 TMA 芯编号，"
         "非 Silva 分型）。ROI 在芯内为上皮/间质配对，主分析取芯级与患者内配对。每个变体在多种子下重复；全部数字可追溯至 results/*.json，"
         "NO-HPV 的 τ 在 3 个种子下相同（SD=0.000）反映同一确定性监督信号主导样本级排序，而非种子未生效。")

    h1("3 结果")
    h2("3.1 框架概览与队列内风险分层")
    add_fig(doc, "Fig1_Framework.png", 5.4,
            "图1 队列病理谱与风险框架设计。(a) 本研究所分析宫颈病变连续谱的代表性 H&E 染色 10x Visium 切片：正常宫颈外口（GSE217237，P020）"
            "示复层鳞状上皮规则分层、向表层有序成熟；高级别鳞状上皮内病变（HSIL/CIN，GSE208654，HSIL_HPV）示上皮增厚、排列紊乱、全层异型；"
            "浸润性鳞状细胞癌（10x Genomics 公开 FFPE 切片，cervical_cancer_1）示促纤维间质内浸润性癌巢；浸润性宫颈管腺癌（GSE208654，CA_HPV_2）"
            "示背靠背/筛状恶性腺体。上排为全片低倍视野（淡色点阵为 Visium 捕获阵列），下排为方框区域的高倍视野。(b) 方法框架：表达/图像双分支融合，"
            "以 HPV 通路先验与空间邻域约束产出 spot 级风险分。H&E 图像仅作组织学背景，未叠加任何模型输出。")
    add_fig(doc, "Fig2_risk_violin.png", 5.3,
            f"图2 spot 级风险随组织学严重度升高（FULL，seed 0；正常 {RV['normal_mean']:.2f} / HSIL {RV['hsil_mean']:.2f} / "
            f"癌 {RV['cancer_mean']:.2f}）。**该图为训练集内描述性结果，样本量疾病 n={CO['n_disease']}，不代表泛化。**")
    body("队列内 spot 风险均值随严重度单调升高（正常/HSIL/癌），样本级疾病 vs 正常 Mann-Whitney p≈1.9×10⁻⁵。"
         "但如图注所强调，这是监督训练集内的描述性现象；它能否代表“学到的疾病信号”，必须由去标签消融判定（见 3.2）。")

    h2("3.2 标签依赖消融：疾病有序排序的标签锚定检验（提示性证据）")
    add_fig(doc, "Fig3_ablation_multiseed.png", 6.5,
            "图3 同队列多种子消融。左：空间一致性 Moran's I；右：疾病有序排序 Kendall τ（点为各种子，柱为均值±SD）。"
            f"NO-PROG（去除疾病严重度标签）后 Kendall τ 降至显著性边界（B=10,000 全样本标签置换，{A['NOPROG']['n_seeds']} 种子 "
            f"p={A['NOPROG']['tau_perm_p_min']:.3f}–{A['NOPROG']['tau_perm_p_max']:.3f}，{A['NOPROG']['tau_perm_nsig']}/{A['NOPROG']['n_seeds']} 名义显著），"
            "而 Moran's I 仅轻度下降；去除图像分支后 Moran's I 下降但 τ 不变。")
    add_table(doc,
        ["配置", "种子数", "Moran's I（均值±SD）", "Kendall τ（均值±SD）", "τ 真置换 p（B=10,000）", "解释"],
        [["FULL", A['FULL']['n_seeds'], pm(A['FULL']['moran_mean'], A['FULL']['moran_sd']),
          pm(A['FULL']['tau_mean'], A['FULL']['tau_sd']),
          f"{A['FULL']['tau_perm_p_min']:.0e}–{A['FULL']['tau_perm_p_max']:.0e}", "完整模型"],
         ["NO-IMAGE", A['NOIMAGE']['n_seeds'], pm(A['NOIMAGE']['moran_mean'], A['NOIMAGE']['moran_sd']),
          pm(A['NOIMAGE']['tau_mean'], A['NOIMAGE']['tau_sd']),
          f"{A['NOIMAGE']['tau_perm_p_min']:.0e}–{A['NOIMAGE']['tau_perm_p_max']:.0e}",
          f"Moran −{abs(IMG_DMORAN):.2f}（一致性增益）；τ 不变（排序零增益）"],
         ["NO-HPV", A['NOHPV']['n_seeds'], pm(A['NOHPV']['moran_mean'], A['NOHPV']['moran_sd']),
          pm(A['NOHPV']['tau_mean'], A['NOHPV']['tau_sd']),
          f"≈{A['NOHPV']['tau_perm_p_min']:.0e}", "通路正则项不决定排序"],
         ["NO-NEIGH", A['NONEIGH']['n_seeds'], pm(A['NONEIGH']['moran_mean'], A['NONEIGH']['moran_sd']),
          pm(A['NONEIGH']['tau_mean'], A['NONEIGH']['tau_sd']),
          f"≈{A['NONEIGH']['tau_perm_p_min']:.0e}", "空间一致性非邻域所致"],
         ["NO-PROG", A['NOPROG']['n_seeds'], pm(A['NOPROG']['moran_mean'], A['NOPROG']['moran_sd']),
          pm(A['NOPROG']['tau_mean'], A['NOPROG']['tau_sd']),
          f"**{A['NOPROG']['tau_perm_p_min']:.3f}–{A['NOPROG']['tau_perm_p_max']:.3f}（边界；{A['NOPROG']['tau_perm_nsig']}/{A['NOPROG']['n_seeds']} 种子名义显著）**", "去标签后排序大幅减弱"]],
        caption="表2 同队列多种子消融（35 例 / 46,820 spot，统一协议）。置换 p 为 35 样本严重度标签向量整体置换 B=10,000 次的经验 p；SciPy 渐近 p 见 Supplementary Table S1，二者不一致时以真置换 p 为准。")
    body(f"**去除疾病严重度标签回归后（NO-PROG），Kendall τ 由 FULL 的 {A['FULL']['tau_mean']:.3f} 降至 "
         f"{A['NOPROG']['tau_mean']:.3f}±{A['NOPROG']['tau_sd']:.3f}（4 个种子 τ={_np_taus}），真置换 p={_np_pp}**："
         f"{A['NOPROG']['tau_perm_nsig']}/{A['NOPROG']['n_seeds']} 种子名义显著（p 介于 {A['NOPROG']['tau_perm_p_min']:.3f}–"
         f"{A['NOPROG']['tau_perm_p_max']:.3f}），另 1 个种子游走于 0.05 边界；方向在全部种子可检出但强度处于边界。"
         "逐片检查显示鳞癌示例片 cervical_cancer_1 在每一个种子均高于 31 个正常样本中的 30 个（最强），HSIL 片高于约 25–26 个，"
         "腺癌片 CA_HPV_2 仅高于 8–13 个、始终是弱点（与 3.4 腺癌 LODO 折最弱一致）；"
         f"疾病 vs 正常单侧 Mann-Whitney p={_np_mwus}（{A['NOPROG']['mwu_nsig']}/{A['NOPROG']['n_seeds']} 种子 <0.05，"
         f"区间 {A['NOPROG']['mwu_p_min']:.3f}–{A['NOPROG']['mwu_p_max']:.3f}）。"
         "功效边界须讲明：置换在全部 35 个样本的标签向量上进行（约 2.1×10⁵ 种排列，不受 4!=24 限制），但秩效应仅由 4 个独立疾病事件驱动，"
         "一个种子的翻转即可改变名义显著性，故该证据定级为 **suggestive（提示性）**——与“队列内排序主要由标签回归锚定”一致，但在 n=4 下不能确证。"
         "这不等同于模型仅死记这 4 张片：3.4 的半监督 LODO 显示保留另外 3 张疾病片标签即可把该方向推广到未见过的疾病片，零标签极限下方向仅部分且不稳定。")
    body(f"**空间一致性的来源须分轴报告：主要来自表达的内在平滑；图像贡献一致性、不贡献排序；邻域正则贡献更小**。"
         f"基线已经很高：去除图像后 Moran's I 仍有 {A['NOIMAGE']['moran_mean']:.3f}±{A['NOIMAGE']['moran_sd']:.3f}，"
         "说明高 Moran's I 的主体是相邻 Visium spot 共享组织/细胞所致的内在平滑，属数据属性而非模型贡献，不应单独作为模型性能宣称。"
         f"在此基线之上各模块的增量不同：(i) **图像分支提升空间一致性**——FULL 为 {A['FULL']['moran_mean']:.3f}，"
         f"NO-IMAGE 为 {A['NOIMAGE']['moran_mean']:.3f}，差值 +{IMG_DMORAN:.2f}（两组种子集不完全重合，该差值仅作描述性报告），"
         "与 Supplementary Note S1 中冻结 UNI patch 嵌入自身强片内自相关（池化 Moran's I=0.618）相吻合；"
         f"(ii) 邻域正则的增量更小（NO-NEIGH {A['NONEIGH']['moran_mean']:.3f}，−{A['FULL']['moran_mean']-A['NONEIGH']['moran_mean']:.3f}）；"
         f"(iii) **图像不改变风险头与临床相关的输出轴**：NO-IMAGE 的 τ={A['NOIMAGE']['tau_mean']:.3f} 与 FULL 的 {A['FULL']['tau_mean']:.3f} "
         "实质相同（置换 p 同处 10⁻⁴ 量级），疾病排序不依赖图像。受 3 个非配对种子与 35 例功效限制，不能排除 τ 上的小效应；"
         "故我们不把多模态融合列为框架贡献，图像分支是**预先纳入、被消融检验的探索性模块**，其结论按两轴定级："
         "对空间一致性的增益 supported，对疾病排序/终点判别的增益 unsupported（补充分析——不经风险头检验 UNI patch 嵌入自身的空间自相关——"
         "见 Supplementary Note S1）。")
    body(f"**最简通路基线（明确为队列内 in-sample 口径）**：不经任何学习、直接取 KEGG-HPV 基因（数据中可检测的 107 个）的样本平均表达作判分，"
         f"样本级疾病 vs 正常 AUC={_bgm_auc:.2f}，而 FULL 模型为 {_mra:.2f}（该 1.00 已在配准修复后的全部 3 个 FULL 种子 npz 上复核，"
         "为样本级口径，非 spot 级 HPV 代理 BCE）。"
         "二者同为 n=35 训练队列上的 in-sample 描述性指标，**不是外部验证**；AUC 增量同样可能来自标签锚定，故仅报告增量大小，不据此宣称泛化优势。")
    body(f"**留一样本（LOSO）跨样本基线：队列内高指标不可外推**。在同一 35 例上做两类 35 折 LOSO。①**形态→HPV 代理判分**：ridge LOSO AUC="
         f"{BSL.get('loso_hpv_ridge_auc', float('nan')):.3f}±{BSL.get('loso_hpv_ridge_auc_sd', float('nan')):.3f}"
         f"（仅 {BSL.get('loso_hpv_ridge_valid', 0)}/35 折可评估，其余折留出片标签单类或预测为常数，本身即说明跨片分布失配；MLP {BSL.get('loso_hpv_mlp_auc', float('nan')):.3f}，"
         f"{BSL.get('loso_hpv_mlp_valid', 0)}/35 折），处于随机水平；②**形态→表达跨样本重建**：以 UNI 特征 ridge 回归预测留出片 {BSL.get('loso35_n_target_genes', 1533)} 个基因表达，"
         f"平均逐基因 Pearson r={BSL.get('loso35_per_gene_pearson', float('nan')):.3f}、held-out MSE={BSL.get('loso35_recon_mse', float('nan')):.3f}，"
         f"不优于同样本内 80/20 内插参照（MSE={BSL.get('he2st_mse', float('nan')):.3f}）。对照 FULL 队列内 AUC=1.00，这两组基线直接证明**队列内指标与跨样本外推性能之间不存在可外推的对应关系**。")

    h2("3.3 通路锚定风险的生物学可解释性")
    add_fig(doc, "Fig4_biology_correlation.png", 6.0,
            "图4 spot 风险与通路/细胞状态评分的 Spearman 相关（within-sample z，3 个 FULL 种子均值，"
            f"11 项相关全部通过 BH 校正；最弱项为 {WEAKEST_Q_SET.replace('_', ' ')}，q={WEAKEST_Q:.1e}）。")
    body("风险高的 spot 富集肿瘤上皮与 HPV 致癌程序、并表现干扰素/增殖下调，方向与宫颈鳞癌上皮转化及免疫逃逸一致：")
    body(f"· 肿瘤上皮 marker（KRT5/14/17、EPCAM 等）：ρ=**{BIO['CELL_tumor_epithelial']['rho']:+.2f}**；"
         f"HPV 致癌驱动（CDKN2A/MYC/EGFR/PIK3CA 等）：ρ=**{BIO['HPV_INTEGRATION_CANDIDATE']['rho']:+.2f}**；"
         f"抗原呈递（B2M/HLA-A/PSMB8 等）：ρ=**{BIO['ANTIGEN_PRESENTATION']['rho']:+.2f}**。", indent=False)
    body(f"· 干扰素-抗病毒（STAT1/MX1/ISG15 等）：ρ=**{BIO['INTERFERON_ANTIVIRAL']['rho']:+.2f}**（高危区干扰素应答减弱，"
         "符合 HPV E6/E7 介导的免疫逃逸）；增殖：ρ="
         f"{BIO['PROLIFERATION']['rho']:+.2f}（负相关，说明该风险轴不等同于单纯增殖轴）、EMT：ρ={BIO['EMT']['rho']:+.2f}"
         "（均经 within-sample z，受基底/分化异质性影响，谨慎解读）。",
         indent=False)
    body(f"为确认这些 marker 不是任意基因组合，在独立宫颈 scRNA-seq（GSE308792[31]，{SCR['n_cells']:,} 个整合细胞；原始论文报告 14,441 个免疫细胞，"
         f"为不同细胞口径）上验证：同谱系内平均相关 +0.242、跨谱系 −0.037，肿瘤上皮与 T 细胞谱系评分相关 −0.57。")

    h2("3.4 无标签跨平台/跨器官迁移与少量标签留出外推")
    add_fig(doc, "Fig5_external_transfer.png", 6.4,
            f"图5 外部迁移与留出外推。A：HNSCC 的 Moran's I 四层对照——模型评分 {EXT['hnscc_moran_mean']:.2f}/{EXT['hnscc_gse281978_moran_mean']:.2f}、"
            f"KEGG-HPV 面板 {EXT['rg268_kegg']:.2f}/{EXT['rg281_kegg']:.2f}、表达量配对随机集 {EXT['rg268_exprm']:.2f}/{EXT['rg281_exprm']:.2f}、"
            "坐标置换零分布近零（14 张切片 p≤0.001）。"
            f"B：GeoMx 肿瘤区**低于**良性（{EXT['geomx_tumor_mean']:.2f} vs {EXT['geomx_benign_mean']:.2f}，符号相对训练队列反转，芯级 p={EXT['geomx_tn_core_p']:.1e}）。"
            f"C：Silva 非单调（A 最低，A vs B p={EXT['geomx_core_silva_AB_p']:.3f}）；病理 High/Low 不显著（p={EXT['geomx_risk_core_p']:.3f}）。"
            "D：终协议 LODO 各留出疾病片的百分位，半监督 vs 全无监督。")
    body(f"**跨平台保留肿瘤-良性秩判别，但校准符号不迁移，且不支持分级（GeoMx DSP，GSE316098[28]）**。推理阶段仅用表达分支、不读取任何宫颈标签"
         f"（权重来自宫颈监督训练；本节检验已学得表征的可迁移性，而非无监督发现）。分组以 GEO SOFT 原始注释为准（列名前缀 1A/1b-1 是 TMA 芯编号，已纠正）。"
         f"在 {EXT['geomx_n_patients']} 例患者、{EXT['geomx_n_rois']} 个 ROI（{EXT['geomx_n_cores']} 个上皮/间质配对芯）上，"
         f"肿瘤区（Silva A/B/C 合并）评分 {EXT['geomx_tumor_mean']:.2f}、**低于**良性 {EXT['geomx_benign_mean']:.2f}"
         f"（ROI 级 p={EXT['geomx_tn_roi_p']:.1e}，芯级 p={EXT['geomx_tn_core_p']:.1e}）；"
         f"{EXT['geomx_wp_n']}/{EXT['geomx_wp_n']} 例有配对的患者肿瘤一致低于自身良性（双侧配对 Wilcoxon p={EXT['geomx_wp_p']:.3f}）。"
         f"n=6 时双侧精确符号秩检验的最小可达 p 为 {EXT['geomx_wp_exact_two_sided_floor_n6']:.3f}，{EXT['geomx_wp_n']}/{EXT['geomx_wp_n']} 已是该样本量下数学上最强的结果、"
         f"不存在“更显著”的空间；但一致性比例的 Clopper-Pearson 95% 区间 [{EXT['geomx_wp_ci_lo']:.2f}, 1.00] 很宽，需在更大配对队列中复制。"
         f"解读的关键是区分秩判别与校准方向：肿瘤与良性在该平台上可被该评分强判别，但高分=高风险的符号**没有**跨平台迁移——"
         "在宫颈训练队列中疾病片评分高于正常，在 GeoMx 中肿瘤评分反而更低；这与平台/癌种差异（DSP 靶向面板 vs Visium 全转录组、腺癌 vs 以鳞癌为主的训练队列）"
         f"导致的尺度偏移相容，本数据无法进一步定位。上皮与基质 ROI 差异不显著（{EXT['geomx_compartment_epi']:.2f} vs {EXT['geomx_compartment_stroma']:.2f}，"
         f"p={EXT['geomx_compartment_p']:.3f}），区室组成既不能解释、也不能被排除为差异来源，故患者内配对是最可靠证据。"
         f"**该评分同样不是分级轴**：Silva A（非破坏性、预后最好）反而最低（芯级 A {EXT['geomx_core_silva_A']:.2f} < C {EXT['geomx_core_silva_C']:.2f} < "
         f"B {EXT['geomx_core_silva_B']:.2f}，非单调；A vs B p={EXT['geomx_core_silva_AB_p']:.3f}）；"
         f"病理 High vs Low 数值方向与风险轴一致但不显著（High {EXT['geomx_risk_core_hi']:.2f} > Low {EXT['geomx_risk_core_lo']:.2f}，"
         f"p={EXT['geomx_risk_core_p']:.3f}）。外部证据因此只支持“肿瘤-良性秩判别可跨平台计算”，不支持符号迁移或任何分级用途。")
    body(f"**Silva 排序的事后分层（已排除区室失衡；信号定位于上皮且 A 型最低；机制待验证）**。A/B/C 三型的上皮/基质 ROI 数量完全均衡（21/21、22/22、25/25），"
         f"“A 型含更多上皮 ROI”不能解释均值差异。信号定位于上皮 ROI，但方向是 A 最低："
         f"上皮内 A {EXT['geomx_silva_epi_A']:.2f} < B {EXT['geomx_silva_epi_B']:.2f} < C {EXT['geomx_silva_epi_C']:.2f}"
         f"（A vs B p={EXT['geomx_silva_epi_AB_p']:.1e}），基质内无单调梯度"
         f"（A/B/C={EXT['geomx_silva_str_A']:.2f}/{EXT['geomx_silva_str_B']:.2f}/{EXT['geomx_silva_str_C']:.2f}）。"
         "这一描述性结果与两种可能均相容：非破坏性、腺管保留的 A 型生长在该评分轴上得分最低，可能反映腺管分化状态对表达评分的残余依赖，"
         "也可能仅是平台特异的细胞组成效应；该数据集无 HPV RNA 原位杂交或定量 p16 注释，机制无法直接检验，"
         "且该比较未经多重性预注册，故只作为描述性记录与待验证假说报告（Supplementary Note S2）。")
    body(f"**跨器官（HNSCC）：真实空间自组织成立、含弱但可复现的通路特异性，但判别性迁移检验全部为阴性**。终协议评分在 {EXT['hnscc_n_samples']} 张头颈部鳞癌 ST 切片"
         f"（GSE268014[29]）上 Moran's I={EXT['hnscc_moran_mean']:.2f}，在独立 HPV 分层 HNSCC 集 GSE281978[30]（{EXT['hnscc_gse281978_n']} 张）上为 "
         f"{EXT['hnscc_gse281978_moran_mean']:.2f}。坐标置换（B=1000）零分布近零（14/14 张 p≤0.001），排除输出坍缩。"
         f"与模型无关的朴素 KEGG-HPV 面板 Moran's I 与之几乎相同（{EXT['rg268_kegg']:.2f}/{EXT['rg281_kegg']:.2f}），说明高自相关主要来自通路表达的内在平滑；"
         f"但在 30 个按表达量十分位配对的随机基因集对照下，KEGG 面板在全部切片上仍更高（{EXT['rg268_exprm']:.2f}/{EXT['rg281_exprm']:.2f}；"
         f"Δ=+{EXT['rg268_exprm_delta']:.2f}/+{EXT['rg281_exprm_delta']:.2f}；切片级精确符号检验 p={EXT['rg268_exprm_signp']:.3f}/{EXT['rg281_exprm_signp']:.3f}），"
         f"即含弱但跨全部切片可复现的通路特异性成分。切片级判别性检验则全部不显著：恶性 vs 非恶性仅 {EXT['mal_non_pos']}/{EXT['mal_non_n']} 张为正"
         f"（p={EXT['mal_non_p']:.3f}），肿瘤前缘 vs 核心仅 {EXT['edge_core_pos']}/{EXT['edge_core_n']} 张为正（7/8 反向，p={EXT['edge_core_p']:.3f}），"
         f"两队列 HPV+ vs HPV− 方向一致但不显著（p={EXT['hpv268_p']:.2f}/{EXT['hpv281_p']:.2f}），原发 vs 淋巴结转移无差异（p={EXT['pt_lnmt_p']:.2f}）"
         f"（Supplementary Note S3）；故跨器官证据仅限于“可计算并保留真实、弱通路特异性的空间组织”，不构成疾病特异性迁移。")
    body(f"**少量标签把部分方向稳定为可迁移方向（半监督 vs 全无监督 LODO，同一协议、逐折配对）**。两协议均逐折留出 1 个疾病片、锁定同一超参、使用全部 spot 与同一 35 例队列，"
         f"唯一差别是监督项。**全无监督 LODO（λ_sup=λ_prog=0）给出部分且不稳定的方向**：{EXT['unsup_lodo_n_above_median']}/4 折高于正常中位、仅 "
         f"{EXT['unsup_lodo_n_above_all']}/4 折高于全部正常，平均百分位 {EXT['unsup_lodo_mean_pct']:.2f}（最弱的腺癌 CA_HPV_2 仅 {EXT['unsup_lodo_min_pct']:.2f}，"
         "处于正常分布低端）。"
         f"**加入另外 3 张疾病片标签后该方向被稳定**：{EXT['lodo_n_above_median']}/4 折高于中位、{EXT['lodo_n_above_all']}/4 折高于全部正常，平均百分位 "
         f"{EXT['lodo_mean_pct']:.2f}，最弱的腺癌折由 {EXT['unsup_lodo_min_pct']:.2f} 升至 {EXT['lodo_min_pct']:.2f}——清晰的标签剂量效应；腺癌折两协议下均最弱，"
          f"提示腺 vs 鳞的组织学泛化是主要瓶颈（宫颈腺癌/鳞癌微环境差异见[41,42]）。**计数证据必须连同分辨力报告**："
         f"{EXT['lodo_4of4_ci_lo']:.2f} 与 {EXT['unsup_3of4_ci_lo']:.2f}、区间大幅重叠，故“半监督优于无监督”是提示性趋势；更稳健的证据是配对设计本身与腺癌折 "
         f"{EXT['unsup_lodo_min_pct']:.2f}→{EXT['lodo_min_pct']:.2f} 的逐折同向变化。")
    h2("3.5 通路特异性与阴性结果")
    body(f"**随机基因集对照：队列内模型评分的通路特异性不成立，疾病排序与通路先验无关**。KEGG-HPV 锚定评分 Moran's I={RC['kegg_moran']:.3f}，"
         f"30 个随机同规模基因集为 {RC['random_moran_mean']:.3f}（{RC['random_moran_min']:.3f}–{RC['random_moran_max']:.3f}），"
         f"差异不显著（置换 p={RC['moran_perm_p']:.3f}）；疾病排序 Kendall τ 在随机集上与 KEGG 完全相同"
         f"（{RC['kegg_kendall']:.3f} vs {RC['random_kendall_mean']:.3f}），样本级 AUC 置换 p={RC['auc_perm_p']:.2f}。"
         "因此队列内空间一致性与有序排序都不依赖 KEGG-HPV 通路特异性：自相关主要来自任意共表达基因集共享的内在平滑，"
         "排序则与标签锚定一致（3.2）。需要区分的是，跨器官 HNSCC 中**朴素 KEGG 面板相对表达量配对随机集**在切片级仍有可复现优势"
         f"（8/8、6/6，p={EXT['rg268_exprm_signp']:.3f}/{EXT['rg281_exprm_signp']:.3f}，见 3.4/Note S3）——该证据成立于跨器官的原始表达面板层，"
         "不成立于本队列的模型评分层，二者口径不同、不互相矛盾。")
    body(f"**TCGA-CESC 生存（阴性，临床效用声明）**：11 个空间 DEG 在 {TC['n_patients']} 例（{TC['events']} 事件）bulk 队列单因素 Cox 回归[43]中无一经 BH-FDR 显著"
         f"（最显著 {TC['min_gene']} 原始 p={TC['min_p']:.3f}），提示 spot 级空间风险与患者级结局之间存在尺度断裂。因此我们在摘要、结论与本节统一声明："
         "**该评分当前不具有任何临床决策效用**——不分级（GeoMx 符号反转）、不预测 bulk 预后、跨器官判别全部阴性；其价值是方法学基准与概念验证。")

    h2("3.6 小样本 ST 风险研究的最低报告协议（建议）")
    body("基于本极端案例，我们把散见于讨论的建议形式化为一套**最低报告协议（minimum reporting protocol, MRP-ST）**，"
         "适用于独立疾病样本数 n_dis≤10（或任一类别 ≤5）的监督/半监督 ST 风险表征研究。协议含 5 个必报项——"
         "去标签消融、全样本标签置换（B≥10,000，不得仅在疾病样本内置换、不得以 spot 为单位）、随机基因集对照（≥30 个、按表达量分位配对）、"
         "样本级留出双协议（半监督与全无监督，逐折训练队列相同，统计单位为样本/切片）、以及结论分级与临床效用声明——"
         "每项均给出最小设计、失败判读与 supported/suggestive/unsupported 判据，并配决策树执行顺序"
         "（完整清单与分级表见 Supplementary Table S2）。全部为训练后分析，可在既有代码库上以可忽略成本复现。"
         "按该规则，本研究的定级为：空间自组织=supported；通路特异性按口径分层——跨器官朴素 KEGG 面板相对表达配对随机集的切片级优势 "
         "supported，队列内模型评分相对随机基因集的特异性 unsupported（Moran p=0.097）；"
         "GeoMx 肿瘤-良性秩判别（符号不迁移）、标签锚定依赖、半监督优于无监督=suggestive；"
         "图像分支按两轴定级：空间一致性增益 suggestive（3 个非配对种子）、疾病排序/终点增益 unsupported；"
         "疾病分级、预后预测、跨器官判别=unsupported。")
    body("上述触发条件、最小重复次数与分级阈值是由本案例提出的实用性暂定规则，而非经多队列验证的共识界值；"
         "在将其用于规范性评价前，仍需在独立 ST 研究中进行外部验证与校准。")

    h1("4 讨论")
    body("本研究在一个极端小样本（疾病 n=4）的公开宫颈 ST 队列中，系统检验了通路锚定风险表征能与不能做什么，并据此标定了一套最低报告协议（§3.6）。"
         "可辩护的正面结论有三点。其一，spot 风险与肿瘤上皮、HPV 致癌驱动、抗原呈递正相关，与干扰素应答负相关——方向与宫颈病变生物学一致、跨种子稳定，"
         "并经独立 scRNA-seq 验证 marker（spot 级，因伪重复仅作描述）。其二，空间一致性高、对标签不敏感；修正图像配准后的消融进一步表明其主体是表达的内在平滑，"
         "形态学图像分支在此之上贡献可检测的一致性增量（Moran +0.07），但不贡献疾病排序。其三，由宫颈监督训练得到的评分在推理无标签阶段"
         f"在 GeoMx 独立宫颈腺癌队列保留强肿瘤-良性秩判别（芯级 p={EXT['geomx_tn_core_p']:.1e}；{EXT['geomx_wp_n']} 例患者内配对方向全部一致，"
         f"p={EXT['geomx_wp_p']:.3f}；suggestive），但评分符号相对训练队列反转（肿瘤更低），迁移的是秩判别而非校准方向；"
         f"在 HNSCC 上可计算、保留真实且弱通路特异性的空间组织（坐标置换 14/14 p≤0.001；符号检验 p={EXT['rg268_exprm_signp']:.3f}/{EXT['rg281_exprm_signp']:.3f}），"
         "而切片级判别为阴性（§3.4）。因此真正持久的信号是肿瘤相关通路程序的空间组织与跨平台可判别性，而非对 4 个标签的拟合，也不是精细分级或评分方向的可迁移性。")
    body("**必须诚实面对的边界**：(1) 队列内近乎完美的有序排序在去除严重度标签后大幅减弱、落在显著性边界（NO-PROG τ 0.46→0.25；"
         "置换 p=0.029–0.056，3/4 种子名义显著，一个种子翻转即越界），故标签锚定为提示性而非确证；置换在全部 35 个样本上进行（约 2.1×10⁵ 种排列），"
         "受限的是 4 个独立疾病事件带来的功效。全无监督留出只给出部分且不稳定的方向"
         f"（{EXT['unsup_lodo_n_above_median']}/4 折高于中位，平均 {EXT['unsup_lodo_mean_pct']:.2f}），半监督 LODO 与方向稳定相关"
         f"（{EXT['lodo_n_above_median']}/4 折高于中位，平均 {EXT['lodo_mean_pct']:.2f}），但精确 CI 重叠（下界 {EXT['lodo_4of4_ci_lo']:.2f}/{EXT['unsup_3of4_ci_lo']:.2f}），同样为提示性。"
         "本研究可作为方法学范例，但**不能被表述为无监督诊断或侵袭性分级工具**；"
         "(2) 图像分支的作用必须分轴表述：它对空间一致性有描述性增益（suggestive；3 个非配对种子），但对疾病排序无可测改变（τ 不变；不能排除小效应），"
         "故多模态融合不是本文贡献（Supplementary Note S1）；(3) 空间 DEG 不带 bulk 预后信号，**评分当前无任何临床决策效用**；"
         "GeoMx 为腺癌、主队列以鳞癌为主，平台/癌种差异与评分符号反转及最弱的腺癌留出折一致；"
         "(4) 仅 4 例疾病样本与 6 例配对患者，功效天然受限，所有受功效限制的结论均已降级为 suggestive；"
         "(5) 上皮/基质 ROI 差异不显著（p=0.18），区室组成既不能解释、也不能被排除为肿瘤-良性差异的来源；Silva 非单调的事后分层仅为描述性记录（Supplementary Note S2）；"
         "(6) 30 例正常外宫颈样本聚合自三个 GEO 子系列，且 46,820 个非独立 spot 的相关性存在伪重复，均按描述性处理，样本/切片/患者级比较为主要证据。")
    body("**对领域的方法学贡献：从建议到协议**。§3.6 将本研究的教训形式化为 MRP-ST，含明确的触发条件（n_dis≤10）、5 个必报项与 supported/suggestive/unsupported 判据。"
         "仅报告队列内 AUC≈1 或高相关、而不证明其在去标签/跨数据下成立，无法区分泛化与标签记忆；本文正是这一失效模式的极端案例——样本级 in-sample AUC=1.00 在去标签后仅余边界级证据。"
"该协议与机器学习中关于标签泄漏与评估偏差的既有讨论[44-47] 一致，也与 TRIPOD+AI[48] 等预测模型报告规范相容；其新意在于把既有原则操作化为空间转录组场景下"
         "固定、可逐行勾选的检查表。协议不依赖具体网络，仓库已提供脚本与全部结果 JSON，可作为可审计的起点清单，而非已确立的共识规范。")

    h1("5 结论")
    body("在 n=4 疾病的极端约束下，通路锚定的表达型 ST 框架能够给出生物学可解释、空间一致的通路风险评分；其监督训练所得评分在推理无标签下可跨平台"
         f"（GeoMx：肿瘤-良性秩判别保留，{EXT['geomx_wp_n']}/{EXT['geomx_wp_n']} 患者内方向一致、已达 n=6 分辨极限，但评分符号反转，suggestive）与跨器官"
         "（HNSCC：保留真实、弱通路特异性的空间组织，supported；但恶性/HPV/转移判别为阴性）计算——并非无监督发现，亦非疾病特异性跨器官迁移，"
         "更不支持评分方向迁移或风险分级。精细有序排序与标签锚定的关联仅获提示性证据"
         "（置换 p=0.029–0.056，3/4 种子名义显著）；半监督留一疾病外推提示少量标签下该方向或可推广到未见过的疾病片（4/4，CI 宽，suggestive）。"
         "探索性图像分支对空间一致性的增益为提示性（3 个非配对种子），且不改变疾病排序（unsupported）；评分不分级、不预测 bulk 预后，故当前无任何临床决策效用。"
         "本文的贡献不是生物学发现或诊断工具，"
         "而是一个标签依赖消融基准与 MRP-ST 最低报告协议（§3.6），并以一个极端案例展示了不执行这些消融时 in-sample 完美结果如何掩盖标签记忆；"
         "在全部数字与脚本均可复现的前提下，本文可作为评估基准与面向更大、配准的多中心 H&E-ST 队列的起点清单。")

    h1("数据与代码可得性")
    body("全部训练脚本、配置、结果 JSON 与融合嵌入均可在 GitHub 公开仓库获取（链接：https://github.com/WorldBMW/pathway-anchored-risk-benchmark）；"
         "数据全部来自公开数据库：宫颈 Visium 队列（GSE208654、GSE217237 及 10x Genomics 公开示例切片）；"
         "外部队列为 GeoMx GSE316098、GSE268014、GSE281978、TCGA-CESC、GSE308792（编号见表1）。", indent=False)
    h1("作者贡献 / 资助 / 利益冲突")
    body("作者贡献（CRediT）：白明威（第一作者）——概念化、方法学、软件、形式分析、调查、数据管理、可视化、原稿撰写；[通讯作者]（通讯作者，待定）——监督、项目管理、稿件审阅与编辑。**资助：本研究未获得任何外部资助（无基金资助）**。作者声明无利益冲突。", indent=False)
    h1("生成式 AI 与 AI 辅助技术在稿件准备过程中的声明")
    body("在本稿准备过程中，作者使用 OpenAI Codex 进行语言润色、结构整理与参考文献核查。作者随后对相关内容进行了审阅、验证和必要修改，并对论文全部内容承担完全责任。", indent=False)
    h1("参考文献")
    for _i, _r in enumerate(REFS, 1):
        body(f"[{_i}] {_r}", indent=False)

    save_doc(doc, CN_OUT_NAME)
    return doc

# =========================================================================
#  ENGLISH
# =========================================================================
def build_en():
    doc, h1, h2, body, title, ctr = make_doc(cn=False)
    title("Benchmarking label dependence of pathway-anchored risk representations in low-sample "
          "spatial transcriptomics: a cross-platform cervical study")
    doc.add_paragraph()

    h1("Abstract")
    body("**Background and Objective.** Public cervical spatial transcriptomics (ST) cohorts contain few diseased samples, making supervised risk models vulnerable to label memorization. "
         "Using four cervical lesions, we tested whether a pathway-anchored representation remains biologically interpretable and computable across platforms without inference-time labels, "
         "and whether near-perfect in-cohort separation reflects learning or label anchoring. This proof-of-concept is not a diagnostic study.")
    body("**Methods.** We analyzed 35 cervical Visium samples (31 normal, 4 diseased; 46,820 spots) using a 108-gene expression-pathway core and an exploratory UNI image branch. "
         "Matched multiseed ablations removed the image, HPV, neighborhood or severity-label terms. Outcomes were Moran's I and sample-level Kendall tau; severity labels were permuted "
         "over all 35 samples (B=10,000). Label-free inference used external GeoMx cervical tissue, head-and-neck ST, TCGA-CESC and cervical scRNA-seq.")
    body("**Results.** FULL achieved Moran's I=0.931±0.001 and tau=0.460 (permutation p=1×10−4–2×10−4). Removing severity labels reduced tau to 0.251±0.018 "
         "(p=0.029–0.056; 3/4 seeds nominally significant), providing suggestive, not confirmatory, evidence of label anchoring. The image branch increased Moran's I by 0.07 but not tau "
         "(0.457 vs 0.460). Scores correlated with tumour epithelium (+0.46), HPV oncogenic programmes (+0.41), antigen presentation (+0.40) and inversely with interferon responses (−0.45). "
         "In GeoMx, tumours scored below benign tissue (−12.98 vs −10.52; core-level p=2.0×10−6; 6/6 paired directions, p=0.031): rank discrimination persisted but calibration sign inverted, "
         "and invasive grade was not recovered. Head-and-neck scores retained non-random spatial organization (coordinate permutation p≤0.001), whereas malignancy, HPV and metastasis contrasts were null. "
         "TCGA survival (302 patients, 72 events) and leave-one-sample-out baselines (AUC 0.497±0.021) were also null.")
    body("**Conclusions.** Under an n=4 disease constraint, pathway-anchored risk was interpretable and spatially coherent, but fine ranking remained label-dependent and cross-platform calibration did not transfer. "
         "We propose a provisional minimum reporting protocol (MRP-ST); the score has no current clinical decision utility.")
    p = doc.add_paragraph(); _rf(p.add_run("Keywords: "), 11.5, True)
    _rf(p.add_run("spatial transcriptomics; cervical lesion; HPV pathway; small-sample learning; label-dependence ablation; "
                  "reporting protocol"), 11.5)

    h1("1. Introduction")
    body("Cervical cancer is the fourth most common malignancy in women worldwide [1], caused mainly by persistent high-risk HPV infection [2]; "
         "TCGA multi-omics has characterized its molecular landscape [3], and the Silva A/B/C pattern-based classification of endocervical adenocarcinoma "
         "is an established histologic grading system linked to lymph-node metastasis and prognosis [4-7]. As spatial transcriptomics (e.g., 10x Visium [8], reviewed in [9-11]) "
         "and digital-pathology foundation models (e.g., UNI [12], Virchow [13], GigaPath [14]) mature, combining expression, imaging and pathway priors could "
         "characterize epithelial transformation and microenvironment remodeling in situ. A widely under-estimated methodological risk is that diseased public "
         "ST samples are extremely few: only four diseased cervical Visium samples (one HSIL, three SCC/ADC) could be aggregated here - a scale at which any "
         "supervised risk model can memorize four labels and report near-perfect in-cohort separation that is memorization rather than generalization.")
    body("Pathway biology offers a natural inductive bias: HPV oncogenesis is a conserved E6/E7-driven program acting through p53/Rb loss, altered antigen "
         "presentation and immune evasion. Anchoring the representation to it should yield scores that are biologically interpretable, spatially smooth and "
         "transferable to other HPV/epithelial-transformation contexts. Whether these expectations hold must be tested with controls rather than assumed.")
    body("**Related work and positioning.** HE2RNA [15] and ST-Net [16] first predicted (spatial) expression from H&E; OmiCLIP [17] extended visual-omics "
         "alignment into a pathology-ST foundation model; SPADE [18], SEAL [19] and MINT [20] fine-tune pathology encoders with ST supervision on 10^5-10^6 "
         "spots; ST-Align [21] aligns images and genes at spot/niche level; STPath [22] predicts ~40,000 genes across 17 organs; scGPT [23], "
         "Novae [24] and CellCharter [25] scale representation learning to tens of millions of cells, and existing pipeline benchmarks score "
         "integration accuracy [26], not label dependence. All presuppose large "
         "multi-sample data and target representation learning or molecular prediction; none addresses four diseased samples, nor asks whether perfect in-cohort "
         "separation reflects learning or label memorization. We do not compete on scale or accuracy; we frame the problem as a **task-side transferable "
         "pathway-risk representation** with a label-removal ablation benchmark.")
    body("**Contributions and scope (explicitly neither a diagnostic nor a multimodal-fusion claim).** (1) A label-dependence ablation benchmark on 35 cervical "
         "Visium samples under a same-cohort, multi-seed, full-spot protocol, with the UNI image branch defined a priori as an exploratory, ablation-tested module "
         "(its coherence gain and its null ranking gain are reported on separate axes in 3.2); (2) FULL/NO-IMAGE/NO-HPV/NO-NEIGH/NO-PROG ablations that dissociate the sources of spatial coherence, interpretability and "
         "disease ordering; (3) label-free cross-platform (GeoMx DSP [27]) and cross-organ (HNSCC) transfer using the correct GEO Silva annotation; (4) honest "
         "reporting of negatives, formalized into a minimum reporting protocol with conclusion grading (Section 3.6).")

    h1("2. Materials and Methods")
    h2("2.1 Cohorts")
    add_table(doc,
        ["Cohort", "Type", "Scale", "Use"],
        [["Cervical Visium aggregate (GSE208654 + GSE217237 + 10x public demo)", "ST (10x Visium)", f"{CO['n_samples']} ({CO['n_normal']} normal / {CO['n_disease']} dis.); {CO['n_spots']:,} spots", "Main + ablation"],
         ["GSE316098 [28]", "GeoMx DSP (cervical ADC) [27]", f"{EXT['geomx_n_patients']} patients (WU-01-WU-07) / {EXT['geomx_n_rois']} ROI ({EXT['geomx_n_cores']} cores)", "Cross-platform: tumor-benign rank discrimination (sign inverted; not grade)"],
         ["GSE268014 [29]", "ST (head & neck; Simkin et al.)", f"{EXT['hnscc_n_samples']} sections", "Cross-organ spatial organization (discrimination n.s.)"],
         ["GSE281978 [30]", "ST (HPV-positive/negative HNSCC; Lee et al.)", f"{EXT['hnscc_gse281978_n']} sections", "Cross-organ replication (HPV/metastasis n.s.)"],
         ["TCGA-CESC [3]", "bulk RNA-seq", f"{TC['n_patients']} pts / {TC['events']} events", "Survival (negative)"],
         ["GSE308792 [31]", "scRNA-seq (cervix)", f"{SCR['n_cells']:,} cells", "Marker validity"]],
        caption="Table 1. Cohort overview", cn=False)
    body("Note: counts denote the sections actually analysed here. GSE268014 comprises 26 tumours in the source study and 8 sections were used; all 6 GSE281978 ST sections were used.", indent=False)
    body("The cervical Visium cohort aggregates three public sources, 35 samples in total (31 normal + 4 diseased): (i) **GSE208654** (Guo et al., Clin Transl Med "
         "2023;13(3):e1219), four sections - N_HPV (normal), HSIL_HPV, CA_HPV_1 (SCC) and CA_HPV_2 (adenocarcinoma); (ii) 30 normal ectocervix Visium sections "
         "(P001-P030) under the **GSE217237** SuperSeries (three sub-series GSE290350/GSE299708/GSE300112 from HIV-infection, DMPA-contraceptive and microbiome studies; "
         "this heterogeneity is addressed in the Limitations); (iii) the public 10x Genomics FFPE cervical-cancer demonstration section "
         "(Visium_FFPE_Human_Cervical_Cancer; cervical_cancer_1, SCC). Histologic labels are normal/HSIL/cancer (severity 0/1/2). Every run uses the same 35 samples, the "
         "full 46,820 spots and a unified 4,991-gene panel (a 108-gene KEGG-HPV pathway sub-panel, of which 107 are detected on this Visium panel).")
    h2("2.2 Framework and losses")
    body("The framework has three routes: (a) an expression branch encoding genes to a latent space with reconstruction (l_rec, 0.2) and a latent prior (l_var, 0.1); "
         "(b) an image branch (exploratory, ablation-tested) encoding UNI [12] patch features and fusing them with the latent expression vector, included precisely to "
         "test whether morphology adds anything detectable here; (c) pathway and spatial priors: a KEGG-HPV (108-gene [32]) consistency regularizer l_hpv "
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
    body("Spatial coherence is Moran's I [33]; disease ordering is sample-level Kendall tau [34] between per-sample risk and severity, with its empirical null "
         "obtained by permuting the severity-label vector across ALL 35 samples (31 zeros, one 1, three 2s) and recomputing spot-aggregated risk, B=10,000 "
         "(Supplementary Table S1; the rank effect is still driven by only four disease events, hence low power). Disease-vs-normal separation uses one-sided "
         "Mann-Whitney U [35]; the within-patient GeoMx comparison uses a two-sided paired Wilcoxon signed-rank test (smallest attainable p at n=6 is 2/2^6=0.031), "
         "reported with exact Clopper-Pearson 95% intervals, as are LODO k/4 counts. Downstream scores use rank-based ssGSEA [36] (pure NumPy [37]) with "
         "within-sample z-standardization, Spearman correlation and Benjamini-Hochberg FDR [38]; classification metrics use scikit-learn [39], tests use SciPy [40]. "
         "**At inference, external scoring uses the expression branch and reads no cervical labels; the weights nevertheless derive from supervised cervical training "
         "(lambda_sup=5.0, lambda_prog=1.5)**, so external experiments test transfer of a learned representation, not unsupervised discovery, which the fully-unsupervised "
         "LODO tests. All external inference uses one weight file, `results/checkpoint_FULL_DEPLOY_FAST_seed42.pt` (seed 42). **For GSE316098, Silva/risk groups follow "
         "the GEO SOFT metadata**; the 1A/1b-1 column prefixes are TMA core identifiers, not Silva patterns. ROIs are paired epithelial/stromal within a core, with "
         "core-level and within-patient tests primary. Each variant is run over multiple seeds.")

    h1("3. Results")
    h2("3.1 Framework and in-cohort risk stratification")
    add_fig(doc, "Fig1_Framework.png", 5.4,
            "Figure 1. Cohort histologic spectrum and risk-framework design. (a) Representative H&E-stained 10x Visium sections spanning the "
            "cervical-lesion continuum analysed in this study: normal ectocervix (GSE217237, P020) showing orderly stratified squamous epithelium with "
            "surface maturation; high-grade squamous intraepithelial lesion (HSIL/CIN, GSE208654, HSIL_HPV) showing thickened, disorganized epithelium with "
            "full-thickness atypia; invasive squamous-cell carcinoma (public 10x Genomics FFPE section, cervical_cancer_1) with infiltrating tumor nests in "
            "desmoplastic stroma; and invasive endocervical adenocarcinoma (GSE208654, CA_HPV_2) with back-to-back/cribriform malignant glands. The upper row "
            "shows whole-section low-power views (faint dots are the Visium capture array); the lower row shows high-power views of the boxed regions. "
            "(b) Framework: fused expression and image branches with an HPV-pathway prior and spatial-neighborhood constraint producing a per-spot risk score. "
            "H&E images provide histologic context only; no model output is overlaid.", cn=False)
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
            "(Kendall tau; dots are seeds, bars are mean ± SD). NO-PROG (no severity labels) drops Kendall tau to the "
            f"significance boundary (35-sample label permutation, B=10,000, {A['NOPROG']['n_seeds']}-seed p={A['NOPROG']['tau_perm_p_min']:.3f}-"
            f"{A['NOPROG']['tau_perm_p_max']:.3f}, {A['NOPROG']['tau_perm_nsig']}/{A['NOPROG']['n_seeds']} nominal), whereas Moran's I drops only slightly; "
            "removing the image branch lowers Moran's I but leaves tau unchanged.", cn=False)
    add_table(doc,
        ["Variant", "Seeds", "Moran's I (mean ± SD)", "Kendall tau (mean ± SD)", "tau true perm. p (B=10,000)", "Interpretation"],
        [["FULL", A['FULL']['n_seeds'], pm(A['FULL']['moran_mean'], A['FULL']['moran_sd']),
          pm(A['FULL']['tau_mean'], A['FULL']['tau_sd']),
          f"{A['FULL']['tau_perm_p_min']:.0e}-{A['FULL']['tau_perm_p_max']:.0e}", "Full model"],
         ["NO-IMAGE", A['NOIMAGE']['n_seeds'], pm(A['NOIMAGE']['moran_mean'], A['NOIMAGE']['moran_sd']),
          pm(A['NOIMAGE']['tau_mean'], A['NOIMAGE']['tau_sd']),
          f"{A['NOIMAGE']['tau_perm_p_min']:.0e}-{A['NOIMAGE']['tau_perm_p_max']:.0e}",
          f"Moran -{abs(IMG_DMORAN):.2f} (coherence gain); tau unchanged (null ranking gain)"],
         ["NO-HPV", A['NOHPV']['n_seeds'], pm(A['NOHPV']['moran_mean'], A['NOHPV']['moran_sd']),
          pm(A['NOHPV']['tau_mean'], A['NOHPV']['tau_sd']),
          f"~{A['NOHPV']['tau_perm_p_min']:.0e}", "Pathway term not decisive"],
         ["NO-NEIGH", A['NONEIGH']['n_seeds'], pm(A['NONEIGH']['moran_mean'], A['NONEIGH']['moran_sd']),
          pm(A['NONEIGH']['tau_mean'], A['NONEIGH']['tau_sd']),
          f"~{A['NONEIGH']['tau_perm_p_min']:.0e}", "Coherence not from neighbor term"],
         ["NO-PROG", A['NOPROG']['n_seeds'], pm(A['NOPROG']['moran_mean'], A['NOPROG']['moran_sd']),
          pm(A['NOPROG']['tau_mean'], A['NOPROG']['tau_sd']),
          f"**{A['NOPROG']['tau_perm_p_min']:.3f}-{A['NOPROG']['tau_perm_p_max']:.3f} (boundary; {A['NOPROG']['tau_perm_nsig']}/{A['NOPROG']['n_seeds']} seeds nominal)**", "Ranking strongly attenuated"]],
        caption="Table 2. Same-cohort multi-seed ablation (35 samples / 46,820 spots, unified protocol). Permutation p-values shuffle the severity-label vector across all 35 samples (B=10,000); SciPy asymptotic p-values are given in Supplementary Table S1, and where the two disagree at small n the permutation p governs.", cn=False)
    body(f"The direction is detectable in every seed but the strength sits at the power boundary: removing disease-severity-label regression (NO-PROG) lowers "
         f"Kendall tau from {A['FULL']['tau_mean']:.3f} to {A['NOPROG']['tau_mean']:.3f}±{A['NOPROG']['tau_sd']:.3f} (per-seed tau={_np_taus}), with true permutation "
         f"p={_np_pp}: {A['NOPROG']['tau_perm_nsig']}/{A['NOPROG']['n_seeds']} seeds reach nominal significance (range {A['NOPROG']['tau_perm_p_min']:.3f}-"
         f"{A['NOPROG']['tau_perm_p_max']:.3f}) and one straddles 0.05. Per-slide inspection shows the SCC demonstration slide cervical_cancer_1 ranks above 30 of 31 "
         "normals in every seed (strongest), the HSIL slide above ~25-26, while the ADC slide CA_HPV_2 exceeds only 8-13 normals and is consistently the weak case "
         "(matching the weakest ADC LODO fold in 3.4). One-sided disease-vs-normal Mann-Whitney gives "
         f"p={_np_mwus} ({A['NOPROG']['mwu_nsig']}/{A['NOPROG']['n_seeds']} seeds <0.05; range {A['NOPROG']['mwu_p_min']:.3f}-{A['NOPROG']['mwu_p_max']:.3f}). "
         "The power boundary must be explicit: the permutation operates on the 35-sample label vector (~2.1e5 labelings), but the rank effect is driven by only four "
         "independent disease events and one seed among four flips the nominal verdict. This evidence is therefore graded SUGGESTIVE: consistent with in-cohort ordering "
         "being anchored by the label regression rather than learned from unlabeled data, yet not confirmatory at n=4. It does not mean the model merely memorizes four "
         "slides - the semi-supervised LODO in 3.4 shows that three labeled disease slides suffice to transfer the direction, while at the zero-label limit it is "
         "partial and unstable.")
    body(f"**The sources of spatial coherence must be reported on separate axes: intrinsic expression smoothing dominates; the image branch adds coherence but no "
         f"ranking; the neighborhood term adds even less.** The baseline is already high: with the image branch off, Moran's I is still "
         f"{A['NOIMAGE']['moran_mean']:.3f}±{A['NOIMAGE']['moran_sd']:.3f}, showing that the bulk of the high Moran's I is intrinsic smoothing of adjacent Visium "
         "spots sharing tissue/cells - a data property, not a model contribution, and not to be claimed as model performance. On top of this baseline the modules "
         f"differ: (i) **the image branch raises spatial coherence** - FULL {A['FULL']['moran_mean']:.3f} vs NO-IMAGE {A['NOIMAGE']['moran_mean']:.3f}, a "
         f"+{IMG_DMORAN:.2f} difference (the seed sets do not fully overlap, so it is reported descriptively), in line with the strong within-slide autocorrelation of "
         "the frozen UNI patch embeddings themselves (pooled Moran's I=0.618, Supplementary Note S1); (ii) the neighborhood term contributes less "
         f"(NO-NEIGH {A['NONEIGH']['moran_mean']:.3f}, -{A['FULL']['moran_mean']-A['NONEIGH']['moran_mean']:.3f}); (iii) **the image branch does not alter the "
         f"clinically relevant output axis**: NO-IMAGE tau={A['NOIMAGE']['tau_mean']:.3f} is essentially identical to FULL {A['FULL']['tau_mean']:.3f} (permutation p "
         "both at the 1e-4 scale), so disease ranking does not depend on images. Small effects on tau cannot be excluded at three unpaired seeds and n=35. We "
         "therefore do not position multimodal fusion as a contribution: the image branch is an a-priori exploratory module under ablation, graded on two axes - its "
         "coherence gain is supported and its ranking/endpoint gain is unsupported (Supplementary Note S1).")
    body(f"**Simplest pathway baseline (explicitly in-sample).** A learning-free score - the per-sample mean expression of the KEGG-HPV genes (107 detected in this "
         f"data) - gives a sample-level disease-vs-normal AUC of {_bgm_auc:.2f} versus {_mra:.2f} for the FULL model (this 1.00 was re-verified on all three post-fix "
         "FULL-seed npz files at sample level; it is not the spot-level HPV-proxy BCE). Both are in-sample descriptive metrics on the n=35 training cohort, **not "
         "external validation**; the AUC gain can likewise reflect label anchoring, so we report its magnitude without claiming a generalization advantage.")
    body(f"**Leave-one-sample-out (LOSO) baselines: in-cohort performance does not extrapolate across samples.** Two 35-fold LOSO evaluations were run on the same 35 "
         f"samples. (1) **Morphology-to-HPV-proxy scoring**: ridge LOSO AUC={BSL.get('loso_hpv_ridge_auc', float('nan')):.3f}±{BSL.get('loso_hpv_ridge_auc_sd', float('nan')):.3f} "
         f"(only {BSL.get('loso_hpv_ridge_valid', 0)}/35 folds evaluable; the remainder have a single label class or a constant prediction, itself evidence of cross-slide "
         f"distribution shift; MLP {BSL.get('loso_hpv_mlp_auc', float('nan')):.3f}, {BSL.get('loso_hpv_mlp_valid', 0)}/35), i.e. chance level. (2) **Morphology-to-expression "
         f"reconstruction**: ridge from UNI features to {BSL.get('loso35_n_target_genes', 1533)} genes gives mean per-gene Pearson r={BSL.get('loso35_per_gene_pearson', float('nan')):.3f} "
         f"and held-out MSE={BSL.get('loso35_recon_mse', float('nan')):.3f}, no better than the in-sample 80/20 interpolation reference (MSE={BSL.get('he2st_mse', float('nan')):.3f}). "
         "Against the FULL in-cohort AUC of 1.00, these baselines show directly that **in-cohort metrics have no extrapolatable correspondence with cross-sample performance**.")
    h2("3.3 Biological interpretability of pathway-anchored risk")
    add_fig(doc, "Fig4_biology_correlation.png", 6.0,
            "Figure 4. Spearman correlation of spot risk with pathway/cell-state scores (within-sample z, mean of 3 "
            f"FULL seeds; all 11 correlations survive BH correction; weakest is {WEAKEST_Q_SET.replace('_', ' ')}, q={WEAKEST_Q:.1e}).", cn=False)
    body("High-risk spots are enriched for tumor epithelium and HPV oncogenic programs while showing down-regulated "
         "interferon and proliferation responses, consistent with squamous epithelial transformation and immune evasion:")
    body(f"- Tumor-epithelial markers (KRT5/14/17, EPCAM): rho=**{BIO['CELL_tumor_epithelial']['rho']:+.2f}**; HPV drivers "
         f"(CDKN2A/MYC/EGFR/PIK3CA): rho=**{BIO['HPV_INTEGRATION_CANDIDATE']['rho']:+.2f}**; antigen presentation "
         f"(B2M/HLA-A/PSMB8): rho=**{BIO['ANTIGEN_PRESENTATION']['rho']:+.2f}**.", indent=False)
    body(f"- Interferon-antiviral (STAT1/MX1/ISG15): rho=**{BIO['INTERFERON_ANTIVIRAL']['rho']:+.2f}** (attenuated in high-risk "
         f"regions, consistent with E6/E7 immune evasion); proliferation rho={BIO['PROLIFERATION']['rho']:+.2f} (negative: the risk "
         f"axis is not a simple proliferation axis), EMT rho={BIO['EMT']['rho']:+.2f} "
         "(within-sample z; interpreted cautiously given basal/differentiation heterogeneity).", indent=False)
    body(f"Marker validity was confirmed in independent cervical scRNA-seq (GSE308792 [31]; {SCR['n_cells']:,} integrated cells; the source paper reports 14,441 immune "
         f"cells, a different cell universe): mean within-lineage correlation +0.242 versus -0.037 across lineages, and tumour-epithelium versus T-cell lineage scores "
         "correlate -0.57.")
    h2("3.4 Label-free transfer and few-label held-out extrapolation")
    add_fig(doc, "Fig5_external_transfer.png", 6.6,
            "Figure 5. External transfer and held-out extrapolation. A: four-level Moran's I control in HNSCC ST "
            "(model score / plain KEGG-HPV panel mean / expression-decile-matched random 108-gene sets / "
            "coordinate-permutation null). The model score (%.2f/%.2f) is far above the null (p≤0.001 on all 14 "
            "sections), and the plain KEGG panel (%.2f/%.2f) exceeds the expression-matched random sets (%.2f/%.2f) on "
            "every section (sign test p=%.3f/%.3f): genuine spatial organization with weak but reproducible pathway "
            "specificity; sample-level malignancy/HPV/metastasis discrimination is nevertheless non-significant. "
            "B: on GeoMx, tumor cores (Silva A/B/C pooled) score BELOW benign " % (
                EXT['hnscc_moran_mean'], EXT['hnscc_gse281978_moran_mean'],
                EXT['rg268_kegg'], EXT['rg281_kegg'], EXT['rg268_exprm'], EXT['rg281_exprm'],
                EXT['rg268_exprm_signp'], EXT['rg281_exprm_signp']) +
            f"({EXT['geomx_tumor_mean']:.2f} vs {EXT['geomx_benign_mean']:.2f}; sign inverted vs training; core-level "
            f"Mann-Whitney p={EXT['geomx_tn_core_p']:.1e}). C: true Silva patterns A/B/C are non-monotonic with A lowest "
            f"(A vs B p={EXT['geomx_core_silva_AB_p']:.3f}) and pathology risk grades are non-significant in the "
            f"risk-axis direction (High {EXT['geomx_risk_core_hi']:.2f} > Low {EXT['geomx_risk_core_lo']:.2f}, core-level "
            f"p={EXT['geomx_risk_core_p']:.3f}), so the score does not grade invasiveness. D: final-protocol LODO percentile "
            "of each held-out disease vs the 31 normals, semi-supervised (3 diseases labeled) vs "
            "fully-unsupervised (lambda_sup=lambda_prog=0) side by side per fold.", cn=False)
    body(f"**Cross-platform tumour-benign rank discrimination is retained, but the calibration sign does not transfer, and grading does not (GeoMx DSP, GSE316098 "
         f"[28]).** Scoring used the expression branch at a label-free inference stage (weights from supervised cervical training; this tests transfer of a learned "
         f"representation, not unsupervised discovery). Groups follow the GEO SOFT annotation (1A/1b-1 prefixes are TMA core ids, corrected). Across "
         f"{EXT['geomx_n_patients']} patients and {EXT['geomx_n_rois']} ROIs ({EXT['geomx_n_cores']} paired epi/stromal cores), tumour cores (Silva A/B/C pooled) "
         f"scored {EXT['geomx_tumor_mean']:.2f}, **below** {EXT['geomx_benign_mean']:.2f} for benign (ROI-level p={EXT['geomx_tn_roi_p']:.1e}; core-level "
         f"p={EXT['geomx_tn_core_p']:.1e}); in all {EXT['geomx_wp_n']}/{EXT['geomx_wp_n']} patients with paired cores the tumour core was lower than the patient's "
         f"own benign core (two-sided paired Wilcoxon p={EXT['geomx_wp_p']:.3f}). At n=6 the smallest attainable two-sided signed-rank p is "
         f"{EXT['geomx_wp_exact_two_sided_floor_n6']:.3f}, so {EXT['geomx_wp_n']}/{EXT['geomx_wp_n']} is the strongest possible outcome and there is no 'more "
         f"significant' room, though the Clopper-Pearson 95% interval [{EXT['geomx_wp_ci_lo']:.2f}, 1.00] is wide and needs replication. The key reading is to "
         "separate rank discrimination from calibration direction: tumour and benign are strongly separable by this score on this platform, but the high-score=high-risk "
         "sign does **not** transfer - diseased slides score above normals in the cervical training cohort whereas tumours score lower on GeoMx; this is compatible "
         f"with a scale shift from platform/histology differences (DSP targeted panel vs Visium whole-transcriptome; ADC vs a largely SCC training cohort) and cannot "
         f"be localized further here. Epithelial and stromal ROIs do not differ significantly ({EXT['geomx_compartment_epi']:.2f} vs "
         f"{EXT['geomx_compartment_stroma']:.2f}, p={EXT['geomx_compartment_p']:.3f}): compartment composition can neither explain nor be excluded as a contributor, "
         f"so the within-patient pairing is the most reliable evidence. **Nor is it a risk-grade axis**: Silva A (non-destructive, best prognosis) is lowest "
         f"(core-level A {EXT['geomx_core_silva_A']:.2f} < C {EXT['geomx_core_silva_C']:.2f} < B {EXT['geomx_core_silva_B']:.2f}, non-monotonic; A vs B "
         f"p={EXT['geomx_core_silva_AB_p']:.3f}), while pathology High vs Low points in the risk-axis direction but is non-significant (High "
         f"{EXT['geomx_risk_core_hi']:.2f} > Low {EXT['geomx_risk_core_lo']:.2f}, p={EXT['geomx_risk_core_p']:.3f}). External evidence therefore supports only "
         "cross-platform computability of tumour-benign rank discrimination, not sign transfer or any grading use.")
    body(f"**Post-hoc stratification of the Silva ordering (compartment imbalance excluded; signal epithelial with pattern A lowest; mechanism unverified).** "
         f"Epithelial/stromal ROI counts are perfectly balanced across patterns A/B/C (21/21, 22/22, 25/25), so 'pattern A contains more epithelial ROIs' cannot "
         f"explain the means. The signal lies in epithelial ROIs, with A lowest: within epithelium A {EXT['geomx_silva_epi_A']:.2f} < B "
         f"{EXT['geomx_silva_epi_B']:.2f} < C {EXT['geomx_silva_epi_C']:.2f} (A vs B p={EXT['geomx_silva_epi_AB_p']:.1e}), with no monotone stromal gradient "
         f"(A/B/C={EXT['geomx_silva_str_A']:.2f}/{EXT['geomx_silva_str_B']:.2f}/{EXT['geomx_silva_str_C']:.2f}). This descriptive result is compatible with either a "
         "residual dependence of the expression score on glandular differentiation state in non-destructive, gland-preserving pattern A growth, or a platform-specific "
         "composition effect; the dataset has no HPV RNA in-situ hybridization or quantitative p16 annotation, the mechanism cannot be tested directly, and the "
         "comparison was not pre-registered for multiplicity, so it is reported as a descriptive record and an unverified hypothesis (Supplementary Note S2).")
    body(f"**Cross-organ (HNSCC): genuine spatial organization with weak but reproducible pathway specificity, yet all discriminative transfer tests are negative.** "
         f"The final-protocol score has Moran's I={EXT['hnscc_moran_mean']:.2f} across {EXT['hnscc_n_samples']} head-and-neck squamous ST sections (GSE268014 [29]) and "
         f"{EXT['hnscc_gse281978_moran_mean']:.2f} across {EXT['hnscc_gse281978_n']} sections of an independent HPV-stratified HNSCC set (GSE281978 [30]). Permuting spot "
         f"coordinates (B=1000) gives a near-zero null (p≤0.001 on all 14 sections), excluding output collapse. A model-independent KEGG-HPV panel reaches nearly the same "
         f"Moran's I ({EXT['rg268_kegg']:.2f}/{EXT['rg281_kegg']:.2f}), confirming that most autocorrelation is intrinsic pathway-expression smoothing; against 30 "
         f"expression-decile-matched random panels the KEGG panel is nonetheless higher on every section ({EXT['rg268_exprm']:.2f}/{EXT['rg281_exprm']:.2f}; "
         f"delta=+{EXT['rg268_exprm_delta']:.2f}/+{EXT['rg281_exprm_delta']:.2f}; slide-level exact sign test p={EXT['rg268_exprm_signp']:.3f}/{EXT['rg281_exprm_signp']:.3f}), "
         f"i.e. a weak but fully reproducible pathway-specific component. Section-level discriminative tests are all non-significant: malignant vs non-malignant is "
         f"positive in only {EXT['mal_non_pos']}/{EXT['mal_non_n']} sections (p={EXT['mal_non_p']:.3f}); tumour front vs core is positive in only "
         f"{EXT['edge_core_pos']}/{EXT['edge_core_n']} (7/8 reversed, p={EXT['edge_core_p']:.3f}); HPV+ vs HPV- points consistently but non-significantly in both "
         f"cohorts (p={EXT['hpv268_p']:.2f}/{EXT['hpv281_p']:.2f}); primary vs lymph-node metastasis shows no difference (p={EXT['pt_lnmt_p']:.2f}; Supplementary Note "
         "S3). Cross-organ evidence is therefore limited to computability with genuine, weakly pathway-specific spatial organization, not disease-specific transfer.")
    body(f"**Minimal labels stabilize a partial direction into a transferable one (semi-supervised vs fully-unsupervised LODO, same protocol, fold-matched).** Both protocols "
         f"hold out one disease slide at a time under locked hyper-parameters, all spots and the same 35-sample cohort; supervision is the only difference. "
         f"**Fully-unsupervised LODO (lambda_sup=lambda_prog=0) gives a partial, unstable direction**: {EXT['unsup_lodo_n_above_median']}/4 folds above the normal median and only "
         f"{EXT['unsup_lodo_n_above_all']}/4 above all normals, mean percentile {EXT['unsup_lodo_mean_pct']:.2f} (the weakest fold, the ADC CA_HPV_2, sits at "
         f"{EXT['unsup_lodo_min_pct']:.2f}, at the low end of the normal distribution). **Adding the other three labeled disease slides stabilizes it**: "
         f"{EXT['lodo_n_above_median']}/4 above the median, {EXT['lodo_n_above_all']}/4 above all "
         f"normals, mean percentile {EXT['lodo_mean_pct']:.2f}, the weakest ADC fold rising from {EXT['unsup_lodo_min_pct']:.2f} to {EXT['lodo_min_pct']:.2f} - a clear label "
          f"dose-response, with the ADC fold weakest under both protocols (glandular-vs-squamous transfer being the main bottleneck; adenocarcinoma-versus- "
          f"squamous microenvironments differ [41,42]). **Count evidence must be reported with "
         f"its resolution**: four folds are four independent holdout events, and the Clopper-Pearson 95% lower bounds for 4/4 and 3/4 are only {EXT['lodo_4of4_ci_lo']:.2f} and "
         f"{EXT['unsup_3of4_ci_lo']:.2f} with strongly overlapping intervals, so 'semi-supervised > unsupervised' is a suggestive trend; the more robust evidence is the paired "
         f"design itself together with the fold-matched {EXT['unsup_lodo_min_pct']:.2f}→{EXT['lodo_min_pct']:.2f} rise of the ADC fold.")
    h2("3.5 Pathway specificity and negative results")
    body(f"**Random-gene-set control: in-cohort pathway specificity of the model score is not supported, and disease ordering is independent of the pathway prior.** "
         f"KEGG-HPV-anchored Moran's I={RC['kegg_moran']:.3f} is not significantly above 30 random same-sized gene sets ({RC['random_moran_mean']:.3f}, "
         f"{RC['random_moran_min']:.3f}-{RC['random_moran_max']:.3f}; permutation p={RC['moran_perm_p']:.3f}); disease ordering (Kendall tau) is identical for random "
         f"sets (KEGG {RC['kegg_kendall']:.3f} vs random {RC['random_kendall_mean']:.3f}) and the AUC permutation p is {RC['auc_perm_p']:.2f}. Thus neither in-cohort "
         "spatial coherence nor ordered ranking depends on KEGG-HPV specificity: autocorrelation is largely intrinsic smoothing shared by any co-expressed gene set, and "
         "ranking is consistent with label anchoring (3.2). The distinction to note is that in cross-organ HNSCC the plain KEGG expression panel does retain a "
         f"reproducible section-level advantage over expression-matched random panels (8/8, 6/6, sign p={EXT['rg268_exprm_signp']:.3f}/"
         f"{EXT['rg281_exprm_signp']:.3f}, Section 3.4/Note S3): that evidence holds at the raw-expression-panel layer across organs, not at the model-score layer in "
         "this cohort; the two calibers differ and do not contradict each other.")
    body(f"**TCGA-CESC survival (negative; clinical-utility statement).** None of 11 spatial DEGs is BH-FDR significant in a {TC['n_patients']}-patient ({TC['events']} events) "
         f"bulk Cox model [43] (smallest {TC['min_gene']} raw p={TC['min_p']:.3f}), indicating a scale break between spot-level spatial risk and patient-level outcome. We therefore "
         "state here, in the abstract and in the conclusions that **the score has no current clinical decision utility**: it does not grade (GeoMx sign inverted), does not predict bulk "
         "prognosis, and fails all cross-organ discriminative tests; its value is a methodological benchmark and proof of concept.")

    h2("3.6 A proposed minimum reporting protocol for low-sample ST risk studies")
    body("From this extreme case we formalize the scattered advice into a **minimum reporting protocol (MRP-ST)** for supervised or semi-supervised ST risk studies with "
         "n_dis≤10 independent disease samples (or ≤5 in any class). It comprises five required items - label-removal ablation, whole-sample label permutation "
         "(B≥10,000, never within disease samples only and never spot-wise), random-gene-set control (≥30 sets, expression-quantile matched), dual sample-level "
         "held-out protocols (semi-supervised vs fully unsupervised, identical per-fold training cohort, statistical unit = sample/section), and conclusion grading with "
         "a clinical-utility statement - each with a minimum design, a failure reading and a supported/suggestive/unsupported decision rule, plus a decision-tree "
         "execution order (full checklist and grading table: Supplementary Table S2). All are post-training analyses reproducible at negligible cost. Applying the rule "
         "grades this study as: spatial self-organization = supported; pathway specificity is stratified by caliber - the cross-organ section-level advantage of the plain "
         "KEGG expression panel over expression-matched random panels is supported, whereas in-cohort model-score specificity vs random gene sets is unsupported "
         "(Moran p=0.097); GeoMx tumour-benign rank discrimination with non-transferring sign, label anchoring, and "
         "semi-supervised > unsupervised LODO = suggestive; the image branch is graded on two axes (coherence gain suggestive because the three runs are unpaired; disease-ranking/endpoint gain "
         "unsupported); disease grading, prognosis prediction and cross-organ discrimination = unsupported.")
    body("The trigger, minimum repetition counts and grading thresholds above are pragmatic, provisional rules proposed from this case, not consensus cut-offs validated across cohorts. "
         "External evaluation and calibration in independent ST studies are required before normative use.")

    h1("4. Discussion")
    body("In an extreme low-sample public cervical ST cohort (disease n=4) we examined what a pathway-anchored risk representation can and cannot do, and calibrated a "
         "minimum reporting protocol on it (Section 3.6). Three positive findings are defensible. First, spot risk correlates positively with tumour epithelium, HPV oncogenic "
         "drivers and antigen presentation and inversely with interferon responses - directionally consistent with cervical lesion biology, seed-stable and validated in "
         "independent scRNA-seq markers (spot-level, descriptive due to pseudoreplication). Second, spatial coherence is high and largely label-insensitive; after correcting "
         "image registration, the ablation shows its bulk is intrinsic expression smoothing, on top of which the morphology branch adds a detectable coherence increment "
         f"(Moran +{IMG_DMORAN:.2f}) but no disease ranking. Third, the "
         f"supervised-trained expression score, at a label-free inference stage, retains strong tumour-benign rank discrimination on an independent GeoMx cervical-ADC cohort "
         f"(core-level p={EXT['geomx_tn_core_p']:.1e}; concordant in all {EXT['geomx_wp_n']} within-patient pairs, p={EXT['geomx_wp_p']:.3f}; suggestive), but the score sign "
         f"is inverted relative to the training cohort (tumours lower): what transfers is rank discrimination, not calibration direction. It remains computable across organs "
         f"on HNSCC with genuine, weakly pathway-specific spatial organization (coordinate permutation p≤0.001 on all 14 sections; sign test "
         f"p={EXT['rg268_exprm_signp']:.3f}/{EXT['rg281_exprm_signp']:.3f}), whereas section-level discrimination is negative (Section 3.4). The durable signal is thus the "
         "spatial organization and cross-platform separability of a tumour-associated pathway program, not the fitting of four labels, not a fine-grained grade, and not "
         "transfer of the score direction.")
    body("The honest boundaries are: (1) near-perfect in-cohort ordered ranking is strongly attenuated once severity labels "
         f"are removed (NO-PROG tau 0.46 to {A['NOPROG']['tau_mean']:.2f}; permutation p={A['NOPROG']['tau_perm_p_min']:.3f}-{A['NOPROG']['tau_perm_p_max']:.3f}, "
         f"{A['NOPROG']['tau_perm_nsig']}/4 seeds nominal, one seed flipping the verdict), so label anchoring is suggestive, not confirmatory; the permutation "
         f"shuffles labels across all 35 samples (~2.1e5 labelings), so what is limited is the power of four independent disease events. Fully-unsupervised hold-out gives "
         f"only a partial, unstable direction ({EXT['unsup_lodo_n_above_median']}/4 above the median, mean {EXT['unsup_lodo_mean_pct']:.2f}), while semi-supervised LODO "
         f"associates three labeled slides with stabilization ({EXT['lodo_n_above_median']}/4 above the median, mean {EXT['lodo_mean_pct']:.2f}) but with overlapping exact "
         f"confidence intervals (lower bounds {EXT['lodo_4of4_ci_lo']:.2f}/{EXT['unsup_3of4_ci_lo']:.2f}), and is likewise suggestive. The study is a methodological exemplar "
         "but **must not be presented as an unsupervised diagnostic or an invasive-risk grading tool**; (2) the image branch must be described on two axes: it shows "
         "a descriptive spatial-coherence gain (suggestive because the three seeds are unpaired) but no detectable disease ranking (tau unchanged; small effects not excluded), so multimodal "
         "fusion is not a contribution (Supplementary Note S1); (3) spatial DEGs carry no bulk prognostic signal and **the score has no current clinical decision utility**; "
         "the GeoMx cohort is adenocarcinoma whereas the main cohort is largely squamous, consistent with both the sign inversion and the weakest (ADC) LODO fold; (4) with "
         "only four disease samples and six paired GeoMx patients, power is intrinsically limited and every power-limited conclusion is downgraded to suggestive; (5) the "
         "epithelial/stromal ROI difference is non-significant (p=0.18), so compartment composition can neither explain nor be excluded as a contributor to the "
         "tumour-benign contrast, and the post-hoc Silva stratification is a descriptive record only (Supplementary Note S2); (6) the 30 normal ectocervix sections are "
         "pooled from three GEO sub-series, and spot-level correlations over 46,820 non-independent spots are treated as descriptive, with "
         "sample/slide/patient-level comparisons as primary evidence.")
    body("Methodological contribution: from advice to protocol. Section 3.6 formalizes MRP-ST, with an explicit trigger (n_dis≤10), five required items, and a "
         "supported/suggestive/unsupported decision rule. Reporting only in-cohort AUC~1 or high correlations without demonstrating label-free or cross-dataset validity cannot "
         "distinguish generalization from label memorization; this paper presents an extreme case, in which a sample-level in-sample AUC of 1.00 leaves only boundary-level evidence after "
"label removal. The protocol is consistent with documented label leakage and evaluation bias in machine learning [44-47] and with prediction-model "
         "reporting guidance such as TRIPOD+AI [48]; its novelty is operationalizing these principles as a fixed, line-item checklist for spatial transcriptomics. It is "
         "network-agnostic and the repository provides the scripts and all result JSONs, so it offers an auditable starting checklist rather than an established consensus standard.")
    h1("5. Conclusions")
    body("Under the extreme n=4-disease constraint, a pathway-anchored expression-based ST framework yields biologically interpretable, spatially coherent pathway-risk "
         "scores; at a label-free inference stage these remain computable across platforms (GeoMx: strong tumour-benign rank discrimination retained with all 6/6 within-patient "
         "pairs concordant at the n=6 resolution limit, but the score sign is inverted - rank discrimination transfers, calibration direction does not; suggestive) and organs "
         "(HNSCC: genuine, weakly pathway-specific spatial organization retained, supported; but malignancy/HPV/metastasis "
         "discrimination negative) - not unsupervised discovery, not disease-specific cross-organ transfer, and not risk grading. Label anchoring of fine ordered ranking "
         f"receives only suggestive evidence (permutation p={A['NOPROG']['tau_perm_p_min']:.3f}-{A['NOPROG']['tau_perm_p_max']:.3f}, "
         f"{A['NOPROG']['tau_perm_nsig']}/4 seeds nominal), and semi-supervised leave-one-disease-out suggests the direction may extend to an "
         "unseen disease slide from a few labels (4/4, wide CIs, suggestive). The exploratory image branch shows a suggestive spatial-coherence gain across three unpaired seeds but no disease ranking "
         "(unsupported), and the score neither grades invasiveness nor predicts bulk survival, so it has no current clinical decision utility. The contribution is a "
         "label-dependence ablation benchmark "
         "with the MRP-ST minimum reporting protocol (Section 3.6), demonstrated by an extreme case in which perfect in-sample results mask label memorization when these "
         "ablations are omitted; with all numbers and scripts reproducible, it is intended as an evaluation benchmark and a starting checklist for genuinely generalizable "
         "models in larger, registered, multi-center H&E-ST cohorts.")
    h1("Data and Code Availability")
    body("All training scripts, configurations, result JSONs and fused embeddings are released at GitHub (URL: %s). All data are from public databases: the cervical "
         "Visium cohort (GSE208654, GSE217237 and the 10x Genomics demonstration section); and the external cohorts GeoMx GSE316098, GSE268014, GSE281978, TCGA-CESC and "
         "GSE308792 (accessions in Table 1)." % "https://github.com/WorldBMW/pathway-anchored-risk-benchmark", indent=False)
    h1("Author contributions / Funding / Competing interests")
    body("CRediT author contributions: Mingwei Bai (first author) - conceptualization, methodology, software, formal analysis, investigation, data curation, visualization, writing (original draft); [Corresponding author] (corresponding author, to be assigned) - supervision, project administration, writing (review and editing). Funding: this research received no external funding (no grant support). The authors declare no competing interests.", indent=False)
    h1("Declaration of generative AI and AI-assisted technologies in the manuscript preparation process")
    body("During the preparation of this work, the authors used OpenAI Codex for language editing, structural organization and reference checking. After using this tool, the authors reviewed, verified and edited the content as needed and take full responsibility for the content of the publication.", indent=False)
    h1("References")
    for _i, _r in enumerate(REFS, 1):
        body(f"[{_i}] {_r}", indent=False)

    save_doc(doc, EN_OUT_NAME)
    return doc

if __name__ == "__main__":
    build_cn()
    build_en()
    print("DONE.")
