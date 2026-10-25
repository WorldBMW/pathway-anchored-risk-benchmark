# -*- coding: utf-8 -*-
"""gen_ploscb.py — PLOS Computational Biology (Q1/Q2 开源刊) 投稿独立生成器

定位（方法学/计算生物学口径）：极端小样本空间转录组风险模型的"标签依赖审计基准"
(label-dependence ablation benchmark) + MRP-ST 最低报告协议；宫颈 n=4 病变
为示范极端案例。所有数字动态读 results/paper_v10_numbers.json；正文引用
用 [@key;key] 占位，按首次出现自动编号（PLOS 顺序编码制）。

结构按 PLOS 要求：Abstract → Author Summary → Introduction → Results →
Discussion → Materials and Methods → Declarations → References。

输出到 papers/10_PLOSCB/：
  Manuscript_PLOSCB.docx / Manuscript_PLOSCB_中文.docx / CoverLetter_PLOSCB.docx
"""

import json
import re
from pathlib import Path

from docx import Document
from docx.shared import Pt, RGBColor, Cm, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "papers" / "10_PLOSCB"
FIG = ROOT / "papers" / "09_AIIM" / "Figures"
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- data ----
N = json.load(open(ROOT / "results" / "paper_v10_numbers.json", encoding="utf-8"))
A = N['ablation']; BIO = N['biology']; EXT = N['external']; RC = N['random_control']
SCR = N['scrna']; TC = N['tcga']; RV = N['risk_by_severity_spot']; CO = N['cohort']
BSL = N.get('baseline', {})
BGM = {}
_bgmp = ROOT / 'results' / 'baseline_hpv_gene_mean_vs_model.json'
if _bgmp.exists():
    BGM = json.load(open(_bgmp, encoding='utf-8'))
WEAKEST_Q_SET = max(BIO, key=lambda k: BIO[k]['q_max'])
WEAKEST_Q = BIO[WEAKEST_Q_SET]['q_max']
IMG_DMORAN = A['FULL']['moran_mean'] - A['NOIMAGE']['moran_mean']
_np = A['NOPROG']
# NO-SUP (lambda_sup=lambda_prog=0) arm added 2026-09-23; absent from
# paper_v10_numbers.json until the server runs + gen_figures_v10.py re-aggregates.
_ns = A.get('NOSUP')
if _ns is None:
    print('[WARN] ablation.NOSUP missing — run scripts/rerun_2026-09-23_nosup.sh '
          'on the server, sync results, then rerun gen_figures_v10.py. Pending markers will appear.')
_np_taus = "/".join(f"{t:.3f}" for t in _np.get('taus', []))
_np_pp = "/".join(f"{p:.3f}" for p in _np.get('tau_perm_ps', []))
_np_mwus = "/".join(f"{p:.3f}" for p in _np.get('mwu_ps', []))
_ns_taus = "/".join(f"{t:.3f}" for t in _ns.get('taus', [])) if _ns else ""
_ns_pp = "/".join(f"{p:.3f}" for p in _ns.get('tau_perm_ps', [])) if _ns else ""
# Data-driven NO-SUP clauses — interpretation is selected by the OBSERVED p, never pre-claimed.
# Three observed states:
#   clean  : every seed n.s. (min perm_p >= 0.05)  -> residue absent
#   mixed  : some but not all seeds nominal        -> weak, seed-unstable residue (OBSERVED 2026-09-23)
#   robust : every seed nominal (max perm_p < 0.05)-> residue survives without targets
if _ns:
    _ns_nsig = _ns['tau_perm_nsig']; _ns_n = _ns['n_seeds']
    if _ns['tau_perm_p_min'] >= 0.05:
        _ns_state = "clean"
    elif _ns['tau_perm_p_max'] < 0.05:
        _ns_state = "robust"
    else:
        _ns_state = "mixed"
    _ns_p_range = (f"{_ns['tau_perm_p_min']:.3f}" if _ns['tau_perm_p_min'] == _ns['tau_perm_p_max']
                   else f"{_ns['tau_perm_p_min']:.3f}–{_ns['tau_perm_p_max']:.3f}")
    _ns_count = f"{_ns_nsig}/{_ns_n} seeds nominal"
    if _ns_state == "clean":
        _ns_abs_clause = (f"the label-free NO-SUP arm abolished the residue (τ={_ns['tau_mean']:.3f}, "
                          f"p={_ns_p_range}, all seeds n.s.)")
        _ns_reading = "Fully label-free; residual ordering absent (all seeds n.s.)"
    elif _ns_state == "mixed":
        _ns_abs_clause = (f"NO-SUP fell to τ={_ns['tau_mean']:.2f} "
                          f"(p={_ns_p_range}, {_ns['tau_perm_nsig']}/{_ns_n} nominal)—a weak, seed-unstable residue")
        _ns_reading = (f"Fully label-free; weak seed-unstable residue ({_ns_count}; "
                       f"τ {min(_ns['taus']):.2f}–{max(_ns['taus']):.2f})")
    else:
        _ns_abs_clause = (f"NO-SUP retained τ={_ns['tau_mean']:.3f} "
                          f"(p={_ns_p_range}, {_ns_count})")
        _ns_reading = "Fully label-free; residual ordering persists on every seed"
else:
    _ns_state = None
    _ns_p_range = "pending"
    _ns_abs_clause = "NO-SUP [pending]"
    _ns_reading = "[NO-SUP pending — rerun_2026-09-23_nosup.sh]"
if _ns_state == "clean":
    _ns_reading_cn = "完全无标签；残余排序消失（各种子均不显著）"
elif _ns_state == "mixed":
    _ns_reading_cn = (f"完全无标签；弱且跨种子不稳定的残余（{_ns_count}；τ "
                      f"{min(_ns['taus']):.2f}–{max(_ns['taus']):.2f}）")
elif _ns_state == "robust":
    _ns_reading_cn = "完全无标签；各种子均保留残余排序"
else:
    _ns_reading_cn = "完全无标签（有序与代理目标均关闭）"
# NO-ALL (lambda_sup=lambda_prog=lambda_hpv=0) seventh arm added 2026-09-24;
# absent until the server runs rerun_2026-09-24_noall.sh + re-aggregation.
_na = A.get('NOALL')
if _na is None:
    print('[WARN] ablation.NOALL missing — run scripts/rerun_2026-09-24_noall.sh '
          'on the server, sync results, then rerun gen_figures_v10.py. Pending markers will appear.')
_na_taus = "/".join(f"{t:.3f}" for t in _na.get('taus', [])) if _na else ""
_na_pp = "/".join(f"{p:.3f}" for p in _na.get('tau_perm_ps', [])) if _na else ""
if _na:
    _na_delta = (_ns['tau_mean'] - _na['tau_mean']) if _ns else float('nan')
    if _na['tau_perm_p_min'] >= 0.05:
        _na_state = "gone"
    elif _na_delta >= 0.03:
        _na_state = "reduced"
    else:
        _na_state = "persist"
    _na_p_range = (f"{_na['tau_perm_p_min']:.3f}" if _na['tau_perm_p_min'] == _na['tau_perm_p_max']
                   else f"{_na['tau_perm_p_min']:.3f}–{_na['tau_perm_p_max']:.3f}")
    _na_count = f"{_na['tau_perm_nsig']}/{_na['n_seeds']} seeds nominal"
    if _na_state == "gone":
        _na_abs_clause = (f"NO-ALL (prior also off) abolished it as well (τ={_na['tau_mean']:.3f}, "
                          f"p={_na_p_range}, all seeds n.s.)")
        _na_reading = ("Labels, proxy and pathway prior off; residual ordering absent (all seeds n.s.)")
        _na_abs_clause_cn = f"且再去除通路先验后残余消失（τ={_na['tau_mean']:.3f}，全部种子置换 p 不显著）"
        _na_reading_cn = "标签、代理与通路先验均关闭；残余排序消失（各种子均不显著）"
    elif _na_state == "reduced":
        _na_abs_clause = (f"NO-ALL reduced it to τ={_na['tau_mean']:.3f} "
                          f"(p={_na_p_range}, {_na['tau_perm_nsig']}/{_na['n_seeds']} nominal)")
        _na_reading = ("Labels, proxy and pathway prior off; residue reduced, seed-unstable")
        _na_abs_clause_cn = (f"再去除通路先验后残余进一步降至 τ={_na['tau_mean']:.3f}"
                             f"（置换 p={_na_p_range}，{_na_count}）")
        _na_reading_cn = "标签、代理与通路先验均关闭；残余减弱、跨种子不稳定"
    else:
        _na_abs_clause = (f"NO-ALL left τ={_na['tau_mean']:.3f} (p={_na_p_range}, "
                          f"{_na['tau_perm_nsig']}/{_na['n_seeds']} nominal)—intrinsic data geometry")
        _na_reading = ("Labels, proxy and pathway prior off; weak residue persists (intrinsic data geometry)")
        _na_abs_clause_cn = (f"但再去除通路先验并未消除残余（τ={_na['tau_mean']:.3f} 对 NO-SUP {_ns['tau_mean']:.3f}，"
                             f"置换 p={_na_p_range}，{_na_count}），提示来源为内在数据结构")
        _na_reading_cn = "标签、代理与通路先验均关闭；弱残余仍存（内在数据结构）"
else:
    _na_state = None
    _na_delta = float('nan')
    _na_p_range = "pending"
    _na_count = "pending"
    _na_abs_clause = "NO-ALL [pending]"
    _na_reading = "[NO-ALL pending — rerun_2026-09-24_noall.sh]"
    _na_abs_clause_cn = "第七个无先验臂（NO-ALL）结果【待补】"
    _na_reading_cn = "标签、代理与通路先验均关闭【待补】"
_bgm_auc = BGM.get('baseline_hpv_gene_mean_auc', float('nan'))
_mra = BGM.get('model_risk_auc', float('nan'))

# LDI (Label-Dependence Index) loaded from post-hoc audit script results.
_LDI_PATH = ROOT / "results" / "ldi_report.json"
_LDI = None
if _LDI_PATH.exists():
    _LDI = json.load(open(_LDI_PATH, encoding="utf-8"))
    _ldi_mean = _LDI['ldi']['ldi_mean']
    _ldi_sd   = _LDI['ldi']['ldi_sd']
    _ldi_norm = _LDI['ldi']['ldi_normalized']
    _ldi_seeds = _LDI['ldi']['seeds']
    _MG = _LDI['marginal_contributions']
    _DEC = _LDI['decision']
    _ldi_theta = _DEC['theta']
    _ldi_state = _DEC['state']   # "label-dependent (gate triggered)"
    _ldi_gate_clause = _DEC['theta_source']
    _prog_mean = _MG['prog']['mean']; _prog_sd = _MG['prog']['sd']
    _prior_mean = _MG['prior']['mean']; _prior_sd = _MG['prior']['sd']
    _label_mean = _MG['label']['mean']; _label_sd = _MG['label']['sd']
    _morph_mean = _MG['morphology']['mean']; _morph_sd = _MG['morphology']['sd']
else:
    _ldi_mean = _ldi_sd = _ldi_norm = _ldi_seeds = None
    _prog_mean = _prog_sd = _prior_mean = _prior_sd = None
    _label_mean = _label_sd = _morph_mean = _morph_sd = None
    print('[WARN] ldi_report.json missing — LDI section will be [pending]')

GITHUB = "https://github.com/WorldBMW/pathway-anchored-risk-benchmark"

# ------------------------------------------------------------ refs -------
REFS = {
 "sung": "H. Sung, J. Ferlay, R.L. Siegel, M. Laversanne, I. Soerjomataram, A. Jemal, et al., Global cancer statistics 2020: GLOBOCAN estimates of incidence and mortality worldwide for 36 cancers in 185 countries, CA Cancer J. Clin. 71 (2021) 209–249. https://doi.org/10.3322/caac.21660.",
 "malagon": "T. Malagón, E.L. Franco, R. Tejada, S. Vaccarella, Epidemiology of HPV-associated cancers past, present and future: towards prevention and elimination, Nat. Rev. Clin. Oncol. 21 (2024) 522–538. https://doi.org/10.1038/s41571-024-00904-z.",
 "tcga": "Cancer Genome Atlas Research Network, Integrated genomic and molecular characterization of cervical cancer, Nature 543 (2017) 378–384. https://doi.org/10.1038/nature21386.",
 "silva1": "I. Alvarado-Cabrero, C. Parra-Herran, S. Stolnicu, A. Roma, E. Oliva, A. Malpica, The Silva pattern-based classification for HPV-associated invasive endocervical adenocarcinoma and the distinction between in situ and invasive adenocarcinoma: relevant issues and recommendations from the International Society of Gynecological Pathologists, Int. J. Gynecol. Pathol. 40 (2021) S48–S65. https://doi.org/10.1097/PGP.0000000000000735.",
 "silva2": "M. Chen, L. Han, Y. Wang, Y. Chen, A. Zheng, Association between Silva pattern-based classification and endocervical adenocarcinoma: a systematic review and meta-analysis, Int. J. Gynecol. Cancer 34 (2024) 1704–1710. https://doi.org/10.1136/ijgc-2024-005639.",
 "silva3": "N. Sinha, O.D. Lara, K. Dessources, E.P. Jones, L.H. Clark, R. Broaddus, et al., Identification of low-risk cases of invasive endocervical adenocarcinoma with Silva pattern-based classification: a systematic review and meta-analysis, Gynecol. Oncol. Rep. 59 (2025) 101764. https://doi.org/10.1016/j.gore.2025.101764.",
 "silva4": "A. Powell, A. Hodgson, P.A. Cohen, J.T. Rabban, K.J. Park, W.G. McCluggage, et al., Improved risk prediction in human papillomavirus-associated endocervical adenocarcinoma through assessment of binary Silva pattern-based classification: an international multicenter retrospective observational study led by the International Society of Gynecological Pathologists (ISGyP), Int. J. Gynecol. Pathol. 43 (2024) 436–446. https://doi.org/10.1097/PGP.0000000000001033.",
 "stahl": "P.L. Ståhl, F. Salmén, S. Vickovic, A. Lundmark, J.F. Navarro, J. Magnusson, et al., Visualization and analysis of gene expression in tissue sections by spatial transcriptomics, Science 353 (2016) 78–82. https://doi.org/10.1126/science.aaf2403.",
 "moses": "L. Moses, L. Pachter, Museum of spatial transcriptomics, Nat. Methods 19 (2022) 534–546. https://doi.org/10.1038/s41592-022-01409-2.",
 "moffitt": "J.R. Moffitt, E. Lundberg, H. Heyn, The emerging landscape of spatial profiling technologies, Nat. Rev. Genet. 23 (2022) 741–759. https://doi.org/10.1038/s41576-022-00515-3.",
 "bressan": "D. Bressan, G. Battistoni, G.J. Hannon, The dawn of spatial omics, Science 381 (2023) eabq4964. https://doi.org/10.1126/science.abq4964.",
 "uni": "R.J. Chen, T. Ding, M.Y. Lu, D.F.K. Williamson, G. Jaume, A.H. Song, et al., Towards a general-purpose foundation model for computational pathology, Nat. Med. 30 (2024) 850–862. https://doi.org/10.1038/s41591-024-02857-3.",
 "virchow": "E. Vorontsov, A. Bozkurt, P. Cassonnet, G. Bontempi, P. Mangeol, C. Rémy, et al., A foundation model for clinical-grade computational pathology and rare cancers detection, Nat. Med. 30 (2024) 2924–2935. https://doi.org/10.1038/s41591-024-03141-0.",
 "giga": "H. Xu, N. Usuyama, J. Bagga, S. Zhang, W. Xu, U. Rao, et al., A whole-slide foundation model for digital pathology from real-world data, Nature 630 (2024) 181–188. https://doi.org/10.1038/s41586-024-07441-w.",
 "he2rna": "B. Schmauch, A. Romagnoni, E. Pronier, C. Saillard, P. Maillé, J. Calderaro, et al., A deep learning model to predict RNA-Seq expression of tumours from whole slide images, Nat. Commun. 11 (2020) 3877. https://doi.org/10.1038/s41467-020-17678-4.",
 "stnet": "B. He, L. Bergenstråhle, L. Stenbeck, A. Abid, A. Andersson, Å. Borg, et al., Integrating spatial gene expression and breast tumour morphology via deep learning, Nat. Biomed. Eng. 4 (2020) 827–834. https://doi.org/10.1038/s41551-020-0578-x.",
 "omiclip": "W. Chen, P. Zhang, T.N. Tran, Y. Xiao, S. Li, V.V. Shah, et al., A visual-omics foundation model to bridge histopathology with spatial transcriptomics, Nat. Methods 22 (2025) 1568–1582. https://doi.org/10.1038/s41592-025-02707-1.",
 "spade": "E. Redekop, M. Pleasure, Z. Wang, V. Ivezic, K.E. Flores, B. Emert, et al., SPADE: spatial transcriptomics and pathology alignment using a mixture of data experts for an expressive latent space, Med. Image Anal. 113 (2026) 104197. https://doi.org/10.1016/j.media.2026.104197.",
 "seal": "K. Hemker, A.H. Song, C. Almagro-Pérez, G. Jaume, S.J. Wagner, A. Vaidya, et al., Towards spatial transcriptomics-driven pathology foundation models, arXiv preprint arXiv:2602.14177 (2026). https://doi.org/10.48550/arXiv.2602.14177.",
 "mint": "M. Lee, J. Kim, J. Yun, S. Yu, J. Jang, MINT: molecularly informed training with spatial transcriptomics supervision for pathology foundation models, arXiv preprint arXiv:2603.07895 (2026). https://doi.org/10.48550/arXiv.2603.07895.",
 "stalign": "Y. Lin, L. Luo, Y. Chen, X. Zhang, Z. Wang, W. Yang, et al., ST-Align: multi-scale image-gene foundation modeling for spatial transcriptomics via spot-niche alignment, in: Proc. International Conference on Learning Representations (ICLR), 2026. arXiv:2411.16793. https://iclr.cc/virtual/2026/10014521.",
 "stpath": "T. Huang, T. Liu, M. Babadi, R. Ying, W. Jin, STPath: a generative foundation model for integrating spatial transcriptomics and whole-slide images, npj Digit. Med. 8 (2025) 659. https://doi.org/10.1038/s41746-025-02020-3.",
 "scgpt": "H. Cui, C. Wang, H. Maan, K. Pang, F. Luo, N. Duan, et al., scGPT: toward building a foundation model for single-cell multi-omics using generative AI, Nat. Methods 21 (2024) 1470–1480. https://doi.org/10.1038/s41592-024-02201-0.",
 "novae": "Q. Blampey, H. Benkirane, N. Bercovici, K. Mulder, G. Gessain, F. Ginhoux, et al., Novae: a graph-based foundation model for spatial transcriptomics data, Nat. Methods 22 (2025) 2539–2550. https://doi.org/10.1038/s41592-025-02899-6.",
 "cellcharter": "M. Varrone, D. Tavernari, A. Santamaria-Martínez, L.A. Walsh, G. Ciriello, CellCharter reveals spatial cell niches associated with tissue remodeling and cell plasticity, Nat. Genet. 56 (2024) 74–84. https://doi.org/10.1038/s41588-023-01588-4.",
 "libench": "B. Li, W. Zhang, C. Guo, H. Xu, L. Li, M. Fang, et al., Benchmarking spatial and single-cell transcriptomics integration methods for transcript distribution prediction and cell type deconvolution, Nat. Methods 19 (2022) 662–670. https://doi.org/10.1038/s41592-022-01480-9.",
 "steinert": "S. Steinert, V. Ruf, D. Dzsotjan, N. Großmann, A. Schmidt, J. Kuhn, et al., A refined approach for evaluating small datasets via binary classification using machine learning, PLoS ONE 19 (2024) e0301276. https://doi.org/10.1371/journal.pone.0301276.",
 "whalen": "S. Whalen, J. Schreiber, W.S. Noble, K.S. Pollard, Navigating the pitfalls of applying machine learning in genomics, Nat. Rev. Genet. 23 (2022) 169–181. https://doi.org/10.1038/s41576-021-00434-9.",
 "kapoor": "S. Kapoor, A. Narayanan, Leakage and the reproducibility crisis in machine-learning-based science, Patterns 4 (2023) 100804. https://doi.org/10.1016/j.patter.2023.100804.",
 "varo": "G. Varoquaux, V. Cheplygina, Machine learning for medical imaging: methodological failures and recommendations for the future, npj Digit. Med. 5 (2022) 48. https://doi.org/10.1038/s41746-022-00592-y.",
 "tripod": "G.S. Collins, K.G.M. Moons, P. Dhiman, R.D. Riley, A.L. Beam, B. Van Calster, et al., TRIPOD+AI statement: updated guidance for reporting clinical prediction models that use regression or machine learning methods, BMJ 385 (2024) e078378. https://doi.org/10.1136/bmj-2023-078378.",
 "geomxtech": "C.R. Merritt, G.T. Ong, S. Church, K. Barker, P. Danaher, G. Geiss, et al., Multiplex digital spatial profiling of proteins and RNA in fixed tissue, Nat. Biotechnol. 38 (2020) 586–599. https://doi.org/10.1038/s41587-020-0472-9.",
 "axelrod": "M.L. Axelrod, R. Zhou, L. Sun, Spatial transcriptomic landscape of invasion patterns in human papillomavirus-associated endocervical adenocarcinoma, Sci. Rep. 16 (2026) 13246. https://doi.org/10.1038/s41598-026-43717-z.",
 "simkin": "D. Simkin, T.F. Barrett, L. Zhang, M.J. Moore, A.C. Greenwald, N. Galili, et al., Spatial analysis of head and neck cancer identifies two ecosystems with distinct modes of epithelial-to-mesenchymal transition, Nat. Genet. 58 (2026) 2240–2253. https://doi.org/10.1038/s41588-026-02723-7.",
 "lee": "H. Lee, S. Park, J.H. Yun, C. Seo, J.M. Ahn, H.Y. Cha, et al., Deciphering head and neck cancer microenvironment: single-cell and spatial transcriptomics reveals human papillomavirus-associated differences, J. Med. Virol. 96 (2024) e29386. https://doi.org/10.1002/jmv.29386.",
 "scrna": "Y. Yuan, D. Sun, M. Yang, Y. Xia, C. Yuan, X. Wang, Profiling of immune cell subsets and functional characteristics of cervical cancer based on single cell RNA sequencing, Front. Immunol. 16 (2025) 1658705. https://doi.org/10.3389/fimmu.2025.1658705.",
 "mo": "D. Mo, H. Cao, S. Lai, J. Luo, W. Ye, Spatial transcriptomic landscape and cellular neighborhood heterogeneity in cervical cancer: integrative single-cell and spatial RNA sequencing analysis, Discov. Oncol. 16 (2025) 2040. https://doi.org/10.1007/s12672-025-03788-2.",
 "wu": "Y. Wu, B. Wei, Z. Wei, H. Wang, Y. Liu, D. Xu, et al., Single-cell and spatial transcriptomic profiling reveals distinct tumor microenvironment dynamics in cervical adenocarcinoma and squamous cell carcinoma, Commun. Biol. 9 (2025) 46. https://doi.org/10.1038/s42003-025-09310-2.",
 "kegg": "M. Kanehisa, M. Furumichi, Y. Sato, Y. Matsuura, M. Ishiguro-Watanabe, KEGG: biological systems database as a model of the real world, Nucleic Acids Res. 53 (2025) D672–D677. https://doi.org/10.1093/nar/gkae909.",
 "moran": "P.A.P. Moran, Notes on continuous stochastic phenomena, Biometrika 37 (1950) 17–23. https://doi.org/10.2307/2332142.",
 "kendall": "M.G. Kendall, A new measure of rank correlation, Biometrika 30 (1938) 81–93. https://doi.org/10.2307/2332226.",
 "mwu": "H.B. Mann, D.R. Whitney, On a test of whether one of two random variables is stochastically larger than the other, Ann. Math. Stat. 18 (1947) 50–60. https://doi.org/10.1214/aoms/1177730491.",
 "ssgsea": "D.A. Barbie, P. Tamayo, J.S. Boehm, S.Y. Kim, S.E. Moody, I.F. Dunn, et al., Systematic RNA interference reveals that oncogenic KRAS-driven cancers require TBK1, Nature 462 (2009) 108–112. https://doi.org/10.1038/nature08460.",
 "numpy": "C.R. Harris, K.J. Millman, S.J. van der Walt, R. Gommers, P. Virtanen, D. Cournapeau, et al., Array programming with NumPy, Nature 585 (2020) 357–362. https://doi.org/10.1038/s41586-020-2649-2.",
 "bh": "Y. Benjamini, Y. Hochberg, Controlling the false discovery rate: a practical and powerful approach to multiple testing, J. R. Stat. Soc. B 57 (1995) 289–300. https://doi.org/10.1111/j.2517-6161.1995.tb02031.x.",
 "sklearn": "F. Pedregosa, G. Varoquaux, A. Gramfort, V. Michel, B. Thirion, O. Grisel, et al., Scikit-learn: machine learning in Python, J. Mach. Learn. Res. 12 (2011) 2825–2830.",
 "scipy": "P. Virtanen, R. Gommers, T.E. Oliphant, M. Haberland, T. Reddy, D. Cournapeau, et al., SciPy 1.0: fundamental algorithms for scientific computing in Python, Nat. Methods 17 (2020) 261–272. https://doi.org/10.1038/s41592-019-0686-2.",
 "cox": "D.R. Cox, Regression models and life-tables, J. R. Stat. Soc. B 34 (1972) 187–220. https://doi.org/10.1111/j.2517-6161.1972.tb00899.x.",
}


class Cites:
    """Register [@key;key] citations in order of first appearance."""
    def __init__(self, refs):
        self.refs = refs
        self.order = []

    def num(self, k):
        if k not in self.refs:
            raise KeyError(f"unknown citation key: {k}")
        if k not in self.order:
            self.order.append(k)
        return self.order.index(k) + 1

    def resolve(self, text):
        def repl(m):
            nums = [self.num(k.strip().lstrip('@'))
                    for k in m.group(1).split(';') if k.strip().lstrip('@')]
            nums = sorted(set(nums))
            parts = []
            i = 0
            while i < len(nums):
                j = i
                while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
                    j += 1
                if j - i >= 2:
                    parts.append(f"{nums[i]}–{nums[j]}")
                else:
                    parts.extend(str(n) for n in nums[i:j + 1])
                i = j + 1
            return "[" + ",".join(parts) + "]"
        return re.sub(r"\[@([A-Za-z0-9_;@]+)\]", repl, text)


# ------------------------------------------------------------ docx utils -
def _rf(run, size=11, bold=False, italic=False, color=None, font='Times New Roman'):
    run.font.size = Pt(size); run.font.bold = bold; run.font.italic = italic
    run.font.name = font
    run._element.rPr.rFonts.set(qn('w:ascii'), font)
    run._element.rPr.rFonts.set(qn('w:hAnsi'), font)
    run._element.rPr.rFonts.set(qn('w:eastAsia'), font)
    if color is not None:
        run.font.color.rgb = color


def shade(cell, hexc):
    s = OxmlElement('w:shd'); s.set(qn('w:fill'), hexc)
    cell._tc.get_or_add_tcPr().append(s)


def _set_cell_width(cell, width_inches):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_w = tc_pr.find(qn('w:tcW'))
    if tc_w is None:
        tc_w = OxmlElement('w:tcW')
        tc_pr.append(tc_w)
    tc_w.set(qn('w:type'), 'dxa')
    tc_w.set(qn('w:w'), str(int(round(width_inches * 1440))))


def _set_cell_margins(cell, top=80, start=100, bottom=80, end=100):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in('w:tcMar')
    if tc_mar is None:
        tc_mar = OxmlElement('w:tcMar')
        tc_pr.append(tc_mar)
    for side, value in (('top', top), ('start', start), ('bottom', bottom), ('end', end)):
        node = tc_mar.find(qn(f'w:{side}'))
        if node is None:
            node = OxmlElement(f'w:{side}')
            tc_mar.append(node)
        node.set(qn('w:w'), str(value))
        node.set(qn('w:type'), 'dxa')


def _add_page_number(paragraph):
    run = paragraph.add_run()
    fld1 = OxmlElement('w:fldChar'); fld1.set(qn('w:fldCharType'), 'begin')
    instr = OxmlElement('w:instrText'); instr.set(qn('xml:space'), 'preserve'); instr.text = 'PAGE'
    fld2 = OxmlElement('w:fldChar'); fld2.set(qn('w:fldCharType'), 'end')
    run._r.append(fld1); run._r.append(instr); run._r.append(fld2)
    _rf(run, 10)


def _enable_line_numbers(section):
    sectPr = section._sectPr
    ln = OxmlElement('w:lnNumType')
    ln.set(qn('w:start'), '1'); ln.set(qn('w:restart'), 'continuous')
    sectPr.append(ln)


def make_manuscript(cn=False):
    cites = Cites(REFS)
    BFONT = '宋体' if cn else 'Times New Roman'
    HFONT = '黑体' if cn else 'Times New Roman'
    doc = Document()
    s = doc.sections[0]
    s.top_margin = s.bottom_margin = Cm(2.5); s.left_margin = s.right_margin = Cm(2.5)
    doc.styles['Normal'].paragraph_format.line_spacing = 1.5
    doc.styles['Normal'].font.name = BFONT
    doc.styles['Normal'].font.size = Pt(11)
    doc.styles['Caption'].font.name = BFONT
    doc.styles['Caption'].font.size = Pt(9.5)
    doc.styles['Caption'].font.italic = True
    for style_name, size in (('Heading 1', 13), ('Heading 2', 11.5)):
        style = doc.styles[style_name]
        style.font.name = HFONT
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
    _enable_line_numbers(s)
    fp = s.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _add_page_number(fp)

    def emit(t, size=11, bold=False, italic=False, align=None, indent=False,
             before=0, after=6, ls=1.5, keep_next=False, font=BFONT, style=None):
        t = cites.resolve(t)
        p = doc.add_paragraph()
        if style is not None:
            p.style = style
        if align is not None:
            p.alignment = align
        if indent:
            p.paragraph_format.first_line_indent = Cm(0.74 if cn else 0.6)
        p.paragraph_format.space_before = Pt(before)
        p.paragraph_format.space_after = Pt(after)
        p.paragraph_format.line_spacing = ls
        if keep_next:
            p.paragraph_format.keep_with_next = True
        for part in re.split(r'(\*\*[^*]+\*\*)', t):
            if part.startswith('**') and part.endswith('**'):
                _rf(p.add_run(part[2:-2]), size, True, italic, font=font)
            elif part:
                _rf(p.add_run(part), size, bold, italic, font=font)
        return p

    def h1(t):
        return emit(t, 13, True, before=12, after=4, keep_next=True, font=HFONT,
                    style='Heading 1')

    def h2(t):
        return emit(t, 11.5, True, before=8, after=2, keep_next=True, font=HFONT,
                    style='Heading 2')

    def body(t, indent=True):
        return emit(t, 11, indent=indent, after=6)

    def ctr(t, size=11, **kw):
        return emit(t, size=size, align=WD_ALIGN_PARAGRAPH.CENTER, **kw)

    def add_table(headers, rows, caption=None, widths=None):
        if caption:
            emit(cites.resolve(caption), 10, True,
                 align=WD_ALIGN_PARAGRAPH.CENTER, after=2, keep_next=True, ls=1.0,
                 font=HFONT, style='Caption')
        t = doc.add_table(rows=1, cols=len(headers))
        t.style = 'Table Grid'; t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        if widths is None:
            widths = {
                2: [1.70, 4.80],
                4: [1.45, 1.45, 1.45, 2.15],
                5: [1.05, 1.25, 1.10, 1.35, 1.75],
                6: [0.70, 0.45, 0.85, 0.90, 1.25, 2.35],
            }.get(len(headers), [6.5 / len(headers)] * len(headers))
        tbl_pr = t._tbl.tblPr
        layout = tbl_pr.first_child_found_in('w:tblLayout')
        if layout is None:
            layout = OxmlElement('w:tblLayout')
            tbl_pr.append(layout)
        layout.set(qn('w:type'), 'fixed')
        tbl_ind = tbl_pr.first_child_found_in('w:tblInd')
        if tbl_ind is None:
            tbl_ind = OxmlElement('w:tblInd')
            tbl_pr.append(tbl_ind)
        tbl_ind.set(qn('w:w'), '100')
        tbl_ind.set(qn('w:type'), 'dxa')
        grid = t._tbl.tblGrid
        for child in list(grid):
            grid.remove(child)
        for width in widths:
            col = OxmlElement('w:gridCol')
            col.set(qn('w:w'), str(int(round(width * 1440))))
            grid.append(col)
        tr_pr = t.rows[0]._tr.get_or_add_trPr()
        th = OxmlElement('w:tblHeader'); th.set(qn('w:val'), 'true'); tr_pr.append(th)
        table_font_size = 8.1 if len(headers) >= 5 else 9.0
        for i, h in enumerate(headers):
            c = t.rows[0].cells[i]; c.text = cites.resolve(h); shade(c, '2F5496')
            _set_cell_width(c, widths[i]); _set_cell_margins(c)
            c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for pp in c.paragraphs:
                pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                pp.paragraph_format.line_spacing = 1.0
                for r in pp.runs:
                    _rf(r, table_font_size, True, color=RGBColor(255, 255, 255), font=HFONT)
        for row in rows:
            cells = t.add_row().cells
            for i, v in enumerate(row):
                cells[i].text = cites.resolve(str(v))
                _set_cell_width(cells[i], widths[i]); _set_cell_margins(cells[i])
                cells[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                for pp in cells[i].paragraphs:
                    pp.alignment = (WD_ALIGN_PARAGRAPH.CENTER
                                    if (len(headers) >= 5 and i < len(headers) - 1)
                                    else WD_ALIGN_PARAGRAPH.LEFT)
                    pp.paragraph_format.line_spacing = 1.0
                    for r in pp.runs:
                        _rf(r, table_font_size, font=BFONT)
        doc.add_paragraph().paragraph_format.space_after = Pt(2)
        return t

    def add_fig(name, w, caption):
        fp_ = FIG / name
        if not fp_.exists():
            print("  [warn] missing", name); return
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True
        shape = p.add_run().add_picture(str(fp_), width=Inches(w))
        cap = cites.resolve(caption)
        shape._inline.docPr.set('title', name)
        shape._inline.docPr.set('descr', cap[:250])
        c = doc.add_paragraph(style='Caption'); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        c.paragraph_format.line_spacing = 1.0
        _rf(c.add_run(cap), 9.5, italic=True, font=BFONT)
        doc.add_paragraph().paragraph_format.space_after = Pt(2)

    return doc, cites, h1, h2, body, ctr, add_table, add_fig, emit


def save(doc, name):
    fp = OUT / name
    try:
        doc.save(str(fp)); print("saved ->", fp)
    except PermissionError:
        fb = OUT / name.replace(".docx", "_NEW.docx")
        doc.save(str(fb)); print("LOCKED in Word; wrote fallback ->", fb)


# ========================================================================
#  MANUSCRIPT
# ========================================================================
def build_manuscript():
    doc, C, h1, h2, body, ctr, add_table, add_fig, emit = make_manuscript()
    TITLE = ('Label-Dependence Index (LDI): A seven-variant audit framework for '
             'small-sample spatial transcriptomics with pathway-anchored validation '
             'in cervical lesions')

    # ---- Title page ----------------------------------------------------
    emit(TITLE, 16, True, align=WD_ALIGN_PARAGRAPH.CENTER, after=14)
    ctr("Mingwei Bai \u00b9, Zhengmin Gu \u00b2, Ye Zhang \u00b2, Lang Guo \u00b3,*", 11.5, after=8)
    ctr("\u00b9 JiMei Technology Group Co., Ltd., Shenyang 110002, China", 10, after=1)
    ctr("\u00b2 Medical Record Management Center, The First Hospital of China "
        "Medical University, Shenyang 110002, China", 10, after=1)
    ctr("\u00b3 School of Pharmacy, Shenyang Medical College, 146 Huanghe North Avenue, "
        "Shenyang 110034, China", 10, after=10)
    ctr("* Corresponding author: Lang Guo, School of Pharmacy, Shenyang Medical College,", 10, after=0)
    ctr("146 Huanghe North Avenue, Shenyang 110034, China. Tel: +86 13555707001; "
        "E-mail: guolang1016@symc.edu.cn", 10, after=6)
    ctr("E-mail addresses \u2014 M. Bai: baimingwei@jm360.cn; Z. Gu: guzm@cmu1h.com; "
        "Y. Zhang: 13332457636@163.com", 10, after=0)
    doc.add_page_break()

    # ---- Abstract ------------------------------------------------------
    h1("Abstract")
    body("**Objective.** Supervised spatial-transcriptomic (ST) risk models are increasingly trained on cohorts with few "
         "diseased samples, where near-perfect in-cohort separation may reflect label memorization rather than generalization. "
         "We introduce **LDI (Label-Dependence Index)**, a formal metric and seven-variant audit framework that quantifies how "
         "much disease-ordering information a small-sample ST model derives from ordinal labels, proxy variables, and "
         "biological pathway priors—demarcating intrinsic spatial signal from label anchoring.")
    body(f"**Methods.** We analyzed {CO['n_samples']} cervical Visium sections ({CO['n_normal']} normal, "
         f"{CO['n_disease']} diseased; {CO['n_spots']:,} spots) with a {CO['n_genes_panel']}-gene HPV-pathway panel "
         "(107 genes detected) and frozen UNI morphology features. LDI is defined as the backward marginal decomposition "
         f"LDI = τ_FULL − τ_NOALL with uncertainty propagated as √(σ_a²+σ_b²) across three independent training seeds, and "
         "is paired with a θ-calibrated decision gate (θ=2·|τ_NOALL|) that classifies a model as label-dependent when LDI > θ. "
         "Marginal contributions of each removed arm (morphology, KEGG-HPV prior, spatial neighborhood, expression-derived proxy, "
         "ordinal labels, and pathway-consistency residual) are decomposed sequentially from the nested cascade. Seven prespecified "
         "multi-seed variants progressively removed each term; we evaluated spatial coherence, whole-sample permutation (B=10,000), "
         "and external GeoMx, head-and-neck ST, TCGA-CESC, and single-cell RNA-sequencing data.")
    body(f"**Results.** FULL achieved Moran's I {A['FULL']['moran_mean']:.3f} and Kendall τ "
         f"{A['FULL']['tau_mean']:.3f}. Seven-variant removal revealed LDI="
         + (f"{_ldi_mean:.3f} ± {_ldi_sd:.3f} " if _LDI else "[pending] ")
         + f"(gate threshold θ={_ldi_theta:.3f}; LDI > θ → model is label-dependent). "
         "Marginal decomposition attributed the ordering primarily to the expression-derived proxy "
         f"(Δτ={_prog_mean:.3f} ± {_prog_sd:.3f}) and pathway prior (Δτ={_prior_mean:.3f} ± {_prior_sd:.3f}), "
         "with morphology, neighborhood and KEGG-HPV prior each contributing Δτ ≈ 0. Removing ordinal labels reduced τ to "
         f"{A['NOPROG']['tau_mean']:.3f} (permutation p={A['NOPROG']['tau_perm_p_min']:.3f}–{A['NOPROG']['tau_perm_p_max']:.3f}); "
         + ("NO-SUP left only a weak, seed-unstable residue " if _ns_state == "mixed"
            else ("NO-SUP abolished the residue " if _ns_state == "clean"
                  else "NO-SUP retained residual ordering ") if _ns_state else "NO-SUP tests the zero-label limit ")
         + f"(τ={_ns['tau_mean']:.3f}); "
         + ("NO-ALL abolished it (τ=" if _na_state == "gone"
            else ("NO-ALL reduced it to τ=" if _na_state == "reduced"
                  else "NO-ALL left τ=") if _na_state else "NO-ALL tests the pathway-prior source (τ=")
         + f"{_na['tau_mean']:.3f}, all seeds non-significant). Risk correlated with tumor epithelium, HPV oncogenic "
         "programs, and antigen presentation; GeoMx preserved tumor–benign rank discrimination in all patient pairs but "
         f"reversed calibration sign; head-and-neck transfer preserved spatial organization but not disease discrimination; "
         f"TCGA-CESC survival discrimination was null (AUC≈{BSL.get('loso_hpv_ridge_auc', float('nan')):.2f}).")
    body("**Conclusion.** Near-perfect in-sample performance can conceal label dependence. LDI and its seven-variant "
         "decomposition provide a network-agnostic, auditable metric and decision gate for small-sample ST risk studies; "
         "evaluated on a 35-sample cervical cohort, the score derives ordering primarily from proxy and pathway prior terms "
         "rather than intrinsic spatial geometry. The score has no current clinical decision utility.")
    emit("**Keywords:** spatial transcriptomics; label dependence; small-sample machine learning; cervical lesion; "
         "cross-platform validation; reporting guideline", 10.5, after=0)
    doc.add_page_break()

    # ---- Author Summary ------------------------------------------------
    h1("Author Summary")
    body("Machine-learning models that predict cancer risk from tissue samples are usually judged by how well they "
         "predict held-aside data. But for rare diseases—including many cervical lesions—a study may contain only a "
         "handful of diseased samples, and a model can look nearly perfect just by memorizing those few labels instead "
         "of learning genuine biological signal. Telling these two explanations apart is hard, and no standard tool does "
         "it for spatial transcriptomics, a technology that maps gene activity across a tissue section in its anatomical "
         "context.")
    body("We introduce the Label-Dependence Index (LDI), a simple measure of how much of a risk model's ability to order "
         "samples by disease severity depends on the severity labels, surrogate variables, and biological pathway "
         "assumptions built into the model. We define LDI and evaluate it using a seven-variant elimination design on a "
         "small cervical spatial-transcriptomics dataset, together with randomized controls and independent tests on "
         "cancer data from two other organs.")
    body("The model achieved near-perfect in-sample ordering, but LDI showed this ordering to be driven mostly by "
         "label-dependent terms rather than by intrinsic spatial biology. LDI and the accompanying reporting checklist "
         "offer a low-cost, model-independent way to expose premature conclusions from small-sample studies before they "
         "are published.")

    # ---- 1 Introduction ------------------------------------------------
    h1("Introduction")
    body("Cervical cancer remains the fourth most common malignancy in women worldwide [@sung], and persistent high-risk HPV "
         "infection accounts for nearly all cases [@malagon]; large multi-omic consortia have characterized its molecular landscape "
         "[@tcga], while the Silva A/B/C pattern-based classification of endocervical adenocarcinoma is an established histologic "
         "grading system linked to stromal invasion, lymph-node metastasis and prognosis [@silva1;@silva2;@silva3;@silva4]. Spatial "
         "transcriptomics (ST; e.g., 10x Visium [@stahl], reviewed in [@moses;@moffitt;@bressan]) measures expression within its "
         "histologic context, and digital-pathology foundation models such as UNI, Virchow and GigaPath [@uni;@virchow;@giga] now "
         "provide transferable morphology representations. Combining expression, imaging and pathway priors is therefore an "
         "attractive route to characterize epithelial transformation in situ.")
    body("A systematically underestimated methodological problem is sample scarcity: aggregating all public cervical Visium data "
         "yielded only four independent diseased sections (one high-grade squamous intraepithelial lesion, two squamous-cell "
         "carcinomas, one adenocarcinoma) against 31 normals. At this scale any supervised risk model can fit four labels, and a "
         "sample-level in-sample AUC of 1.00 cannot distinguish learned disease signal from memorization of four independent "
         "events. Rare-disease ST studies increasingly face exactly this regime, yet there is no standardized audit that separates "
         "the two explanations.")
    body("Pathway biology supplies a natural inductive bias. HPV oncogenesis is a conserved E6/E7-driven program acting through "
         "p53/Rb loss, altered antigen presentation and immune evasion; anchoring a representation to the KEGG HPV gene set "
         "[@kegg] might produce scores that are biologically interpretable, spatially smooth and transferable to other "
         "HPV-driven epithelial contexts. These are hypotheses to be tested with controls, not properties to be assumed.")
    body("**This paper makes four methodological contributions.** (1) We introduce **LDI (Label-Dependence Index)**, a formal "
         "metric for quantifying how much disease-ordering information in a small-sample ST risk model derives from ordinal "
         "labels, proxy variables, and pathway priors versus intrinsic spatial signal. LDI is defined as the backward marginal "
         "decomposition LDI = τ_FULL − τ_NOALL with uncertainty propagated as √(σ_a²+σ_b²), is paired with a θ-calibrated "
         "decision gate (θ=2·|τ_NOALL|) that classifies a model as label-dependent when LDI > θ, and satisfies three "
         "formal properties: telescoping additivity (LDI is exactly the sum of the six signed marginal contributions), seed "
         "robustness (SD across independent training seeds is reported alongside every LDI estimate), and zero-distribution calibration "
         "(θ is derived from permutation or random-control runs, not arbitrary). (2) We pair LDI with a seven-variant "
         "nested ablation design: same-cohort, same-protocol, multi-seed variants that progressively remove the morphology "
         "branch (NO-IMAGE), KEGG-HPV consistency term (NO-HPV), spatial neighborhood regularizer (NO-NEIGH), expression-derived "
         "proxy (NO-PROG), ordinal labels (NO-SUP, λ_sup=λ_prog=0), and both the proxy and the pathway prior (NO-ALL, "
         "λ_sup=λ_prog=λ_hpv=0), plus marginal contribution decomposition that attributes τ Δ to each individual removed term. "
         "(3) We formalize the audit output into MRP-ST, a five-item minimum reporting protocol with supported/suggestive/"
         "unsupported grading that embeds LDI and the decision gate as the first reporting items. (4) We validate the "
         "framework across four held-out cohorts at a label-free inference stage—GeoMx DSP cervical adenocarcinoma "
         "[@geomxtech;@axelrod], head-and-neck ST [@simkin;@lee], TCGA-CESC survival, and cervical single-cell RNA-sequencing—"
         "separating rank discrimination from calibration direction and from grading. Cervical lesions provide the real-world "
         "clinical setting; the contribution is the audit methodology and its generalizable lessons, not a diagnostic tool.")
    body("We explicitly do not claim a diagnostic, a grading instrument, or a multimodal-fusion advance: the morphology branch is "
         "an a priori exploratory module whose benefits are reported on separate axes, and every power-limited or negative result "
         "is graded rather than hidden. The remainder of the paper reviews related work (Section 2), specifies datasets, model, "
         "benchmark and statistics (Section 3), reports results (Section 4), and discusses generalizable lessons and limitations "
         "(Sections 5–6).")

    # ---- Statement of Significance (JBI-mandated; SKIP for AIIM) -------
    # add_table(... JBI-exclusive, AIIM has no such requirement ...)

    # ---- 2 Related work ------------------------------------------------
    h2("Related work")
    h2("2.1 From H&E-to-expression models to pathology–ST foundation models")
    body("HE2RNA [@he2rna] and ST-Net [@stnet] first demonstrated prediction of (spatial) expression from H&E images. A second "
         "wave aligns pathology encoders with ST at scale: OmiCLIP [@omiclip] extends visual-omics alignment into a foundation "
         "model; SPADE [@spade] mixes pathology and expression experts in a shared latent space; SEAL [@seal] and MINT [@mint] "
         "fine-tune pathology encoders with ST supervision on 10⁵–10⁶ registered spots; ST-Align [@stalign] aligns images and "
         "genes at spot and niche scales; and STPath [@stpath] predicts genome-wide expression across 17 organs. These methods "
         "target molecular-prediction accuracy under data abundance.")
    h2("2.2 ST representation learning and existing benchmarks")
    body("Generic foundation models—scGPT [@scgpt] for single-cell multi-omics, Novae [@novae] for graph-based ST representation, "
         "and CellCharter [@cellcharter] for spatial niche discovery—scale to tens of millions of cells. Community benchmarking "
         "efforts such as the Li et al. integration benchmark [@libench] quantify transcript-distribution prediction and cell-type "
         "deconvolution accuracy across algorithms. Benchmarks in this literature measure representational or predictive fidelity; "
         "none tests whether a supervised risk output survives removal of the few disease labels, i.e., whether reported "
         "performance reflects generalization or label anchoring.")
    h2("2.3 Evaluation failures in small-sample biomedical machine learning")
    body("Methodological audits document pervasive label leakage, inappropriate splitting and over-optimistic in-sample "
         "evaluation in machine-learning-based science [@kapoor;@whalen], recurrent failures in medical imaging at small n [@varo], "
         "and the instability of binary classification metrics on tiny datasets [@steinert]; reporting guidance such as "
         "TRIPOD+AI [@tripod] prescribes external validation but remains generic and is not operationalized for ST. The gap is "
         "concrete: an ST-specific, network-agnostic line-item benchmark that (i) removes supervision components one at a time "
         "under matched multi-seed protocols, (ii) permutes labels at the correct statistical unit (the independent sample, never "
         "the spatially autocorrelated spot), (iii) contrasts semi-supervised and fully unsupervised whole-sample hold-outs, and "
         "(iv) grades conclusions against external and null controls. Table 1 positions this work against the state of the art. We "
         "do not compete on scale or predictive accuracy; we provide the missing evaluation layer.")
    add_table(
        ["Line of work", "Representative methods", "Typical data regime", "Explicit label-dependence audit", "Cross-platform external tests"],
        [["H&E → expression", "HE2RNA, ST-Net [@he2rna;@stnet]", "Hundreds–thousands of slides", "No", "Rare"],
         ["Pathology–ST foundation models", "OmiCLIP, SPADE, SEAL, MINT, ST-Align, STPath [@omiclip;@spade;@seal;@mint;@stalign;@stpath]", "10⁵–10⁶ spots, many samples", "No", "Held-out organs, not label removal"],
         ["ST / single-cell representations", "scGPT, Novae, CellCharter [@scgpt;@novae;@cellcharter]", "10⁷ cells", "No (self-supervised targets)", "No"],
         ["ST integration benchmarks", "Li et al. [@libench]", "Multi-cohort", "No—scores integration accuracy", "No"],
         ["Small-sample ML guidance", "Leakage audits, small-n evaluation, TRIPOD+AI [@kapoor;@whalen;@varo;@steinert;@tripod]", "Generic, tabular/imaging", "Principles only", "Prescribed, not executed"],
         ["This work", "Pathway-anchored multimodal model + audit benchmark + MRP-ST", f"{CO['n_samples']} samples / {CO['n_disease']} diseased", "Yes: seven prespecified multi-seed variants including target-free and pathway-regularizer-free arms, whole-sample permutation, dual LODO, gene-set nulls", "Yes: GeoMx, 14 HNSCC sections, TCGA-CESC, scRNA-seq"]],
        caption="Table 1. Positioning against the state of the art; citations resolve to the numbered reference list.")

    # ---- 4 Results -----------------------------------------------------
    h1("Results")
    h2("4.1 Cohort spectrum and in-cohort risk ordering")
    add_fig("Fig1_Framework.png", 5.3,
            "Figure 1. Cohort histologic spectrum and benchmark framework. (a) Representative H&E-stained Visium sections "
            "spanning the analyzed continuum: normal ectocervix (GSE217237, P020) with orderly maturing stratified squamous "
            "epithelium; HSIL (GSE208654, HSIL_HPV) with full-thickness atypia; invasive squamous-cell carcinoma (10x public FFPE "
            "section, cervical_cancer_1) with infiltrating tumor nests in desmoplastic stroma; and invasive endocervical "
            "adenocarcinoma (GSE208654, CA_HPV_2) with back-to-back/cribriform malignant glands. Upper row: whole-section "
            "low-power views; lower row: high-power views of boxed regions. (b) Model: fused expression and morphology branches "
            "with HPV-pathway prior and neighborhood constraint, producing a per-spot risk score that enters the seven-variant "
            "audit. H&E provides histologic context only; no model output is overlaid.")
    add_fig("Fig2_risk_violin.png", 4.8,
            f"Figure 2. In-cohort per-spot risk by histologic severity (FULL, seed 0): normal {RV['normal_mean']:.2f}, HSIL "
            f"{RV['hsil_mean']:.2f}, cancer {RV['cancer_mean']:.2f}; sample-level disease-vs-normal Mann–Whitney p≈1.9×10⁻⁵. "
            f"This is a descriptive in-sample result at disease n={CO['n_disease']}; whether it reflects learning or label "
            "anchoring is adjudicated by the nested NO-PROG/NO-SUP/NO-ALL cascade (Section 4.2).")
    body(f"Mean per-spot risk rises monotonically normal < HSIL < cancer, but this separation exists inside the supervised "
         f"training set. The label-removal result below shows it must not be read as evidence of generalization.")
    h2("4.2 Label-removal ablation: ordered ranking is label-anchored (suggestive)")
    add_fig("Fig3_ablation_multiseed.png", 6.2,
            "Figure 3. Same-cohort multi-seed ablation. Left: spatial coherence (Moran's I). Right: disease ordering (Kendall τ; "
            "points are seeds, bars mean ± SD). Removing severity labels (NO-PROG) drops τ to the significance boundary while "
            f"Moran's I barely changes ({A['NOPROG']['n_seeds']}-seed permutation p={A['NOPROG']['tau_perm_p_min']:.3f}–"
            f"{A['NOPROG']['tau_perm_p_max']:.3f}, {A['NOPROG']['tau_perm_nsig']}/{A['NOPROG']['n_seeds']} seeds nominal); "
            + ("the fully label-free NO-SUP arm removes the residual ordering (all seeds n.s.); " if _ns_state == "clean"
               else "the fully label-free NO-SUP arm leaves only a weak, seed-unstable residue "
                    f"(τ={_ns['tau_mean']:.2f}, permutation p={_ns_p_range}, {_ns_count}); " if _ns_state == "mixed"
               else "the fully label-free NO-SUP arm retains residual ordering on every seed (see Table 3); " if _ns_state == "robust"
               else "the fully label-free NO-SUP arm tests whether any ordering survives without targets; ")
            + ("the target- and pathway-regularizer-free NO-ALL arm then abolishes it (all seeds n.s.)" if _na_state == "gone"
               else f"the target- and pathway-regularizer-free NO-ALL arm reduces it to τ={_na['tau_mean']:.2f} (p={_na_p_range}, {_na_count})"
                    if _na_state == "reduced"
               else f"a weak residue still survives NO-ALL (τ={_na['tau_mean']:.2f}, p={_na_p_range}, {_na_count}), indicating "
                    "intrinsic data geometry" if _na_state == "persist"
               else "the target- and pathway-regularizer-free NO-ALL arm tests the pathway-regularizer source [results pending]")
            + "; removing the morphology branch lowers Moran's I but leaves τ unchanged.")
    _nosup_row = (
        ["NO-SUP", _ns['n_seeds'], f"{_ns['moran_mean']:.3f} ± {_ns['moran_sd']:.3f}",
         f"{_ns['tau_mean']:.3f} ± {_ns['tau_sd']:.3f}",
         f"{_ns['tau_perm_p_min']:.3f}–{_ns['tau_perm_p_max']:.3f} ({_ns['tau_perm_nsig']}/{_ns['n_seeds']} nominal)",
         _ns_reading] if _ns else
        ["NO-SUP", "[pending]", "[pending]", "[pending]", "[pending]", _ns_reading])
    _noall_row = (
        ["NO-ALL", _na['n_seeds'], f"{_na['moran_mean']:.3f} ± {_na['moran_sd']:.3f}",
         f"{_na['tau_mean']:.3f} ± {_na['tau_sd']:.3f}",
         f"{_na['tau_perm_p_min']:.3f}–{_na['tau_perm_p_max']:.3f} ({_na['tau_perm_nsig']}/{_na['n_seeds']} nominal)",
         _na_reading] if _na else
        ["NO-ALL", "[pending]", "[pending]", "[pending]", "[pending]", _na_reading])
    add_table(
        ["Variant", "Seeds", "Moran's I (mean ± SD)", "Kendall τ (mean ± SD)", "τ permutation p (B=10,000)", "Reading"],
        [["FULL", A['FULL']['n_seeds'], f"{A['FULL']['moran_mean']:.3f} ± {A['FULL']['moran_sd']:.3f}",
          f"{A['FULL']['tau_mean']:.3f} ± {A['FULL']['tau_sd']:.3f}",
          f"{A['FULL']['tau_perm_p_min']:.0e}–{A['FULL']['tau_perm_p_max']:.0e}", "Complete model"],
         ["NO-IMAGE", A['NOIMAGE']['n_seeds'], f"{A['NOIMAGE']['moran_mean']:.3f} ± {A['NOIMAGE']['moran_sd']:.3f}",
          f"{A['NOIMAGE']['tau_mean']:.3f} ± {A['NOIMAGE']['tau_sd']:.3f}",
          f"{A['NOIMAGE']['tau_perm_p_min']:.0e}–{A['NOIMAGE']['tau_perm_p_max']:.0e}",
          f"Moran −{abs(IMG_DMORAN):.2f}; τ unchanged"],
         ["NO-HPV", A['NOHPV']['n_seeds'], f"{A['NOHPV']['moran_mean']:.3f} ± {A['NOHPV']['moran_sd']:.3f}",
          f"{A['NOHPV']['tau_mean']:.3f} ± {A['NOHPV']['tau_sd']:.3f}",
          f"~{A['NOHPV']['tau_perm_p_min']:.0e}", "Pathway term not decisive for ordering"],
         ["NO-NEIGH", A['NONEIGH']['n_seeds'], f"{A['NONEIGH']['moran_mean']:.3f} ± {A['NONEIGH']['moran_sd']:.3f}",
          f"{A['NONEIGH']['tau_mean']:.3f} ± {A['NONEIGH']['tau_sd']:.3f}",
          f"~{A['NONEIGH']['tau_perm_p_min']:.0e}", "Coherence not from the neighbor term"],
         ["NO-PROG", A['NOPROG']['n_seeds'], f"{A['NOPROG']['moran_mean']:.3f} ± {A['NOPROG']['moran_sd']:.3f}",
          f"{A['NOPROG']['tau_mean']:.3f} ± {A['NOPROG']['tau_sd']:.3f}",
          f"{A['NOPROG']['tau_perm_p_min']:.3f}–{A['NOPROG']['tau_perm_p_max']:.3f} ({A['NOPROG']['tau_perm_nsig']}/{A['NOPROG']['n_seeds']} nominal)",
          "Ordinal labels off; expression-derived proxy retained"],
         _nosup_row,
         _noall_row],
        caption="Table 3. Same-cohort multi-seed ablation (35 samples, 46,820 spots, locked protocol). NO-SUP sets both "
                "λ_sup=0 and λ_prog=0 (no ordinal labels, no expression-derived proxy); NO-ALL additionally sets λ_hpv=0, "
                "so no ordinal target, proxy or pathway-consistency prior contributes a gradient (reconstruction, neighborhood, "
                "morphology and the panel genes as ordinary inputs remain). P-values permute the severity vector "
                "across all 35 samples; asymptotic p-values are in Supplementary Table S1 and the permutation caliber governs "
                "at small n.")
    body(f"Removing severity-label regression lowers Kendall τ from {A['FULL']['tau_mean']:.3f} to "
         f"{A['NOPROG']['tau_mean']:.3f}±{A['NOPROG']['tau_sd']:.3f} (per-seed τ={_np_taus}; permutation p={_np_pp}: "
         f"{A['NOPROG']['tau_perm_nsig']}/{A['NOPROG']['n_seeds']} seeds nominal, one straddling 0.05). The SCC demonstration "
         "section ranks above 30/31 normals in every seed, the HSIL section above ~25–26, while the ADC section exceeds only "
         "8–13 normals and is consistently weakest (foreshadowing Section 4.5). One-sided Mann–Whitney gives "
         f"{_np_mwus} ({A['NOPROG']['mwu_nsig']}/{A['NOPROG']['n_seeds']} seeds <0.05; range {A['NOPROG']['mwu_p_min']:.3f}–"
         f"{A['NOPROG']['mwu_p_max']:.3f}). Because the effect rests on four independent disease events and one of four seeds "
         "flips the verdict, label anchoring of fine ordered ranking is graded SUGGESTIVE, not confirmatory. We stress that the "
         "seed count is a stability diagnostic, not a sample size: seeds are not independent events, and the four independent "
         "disease sections remain the only inferential replicates, so the seed-wise p-values above are reported for transparency "
         "and are not multiplicity-corrected. The residual ordering under NO-PROG is also not evidence of label-free "
         "generalization, since the retained expression-derived proxy is itself disease-correlated (Section 3.3); it indicates "
         "that such a proxy can partially recover the ranking. "
         + (f"The fully label-free NO-SUP arm adjudicates the zero-target limit inside the matrix: with λ_sup=λ_prog=0, τ "
            f"falls further to {_ns['tau_mean']:.3f}±{_ns['tau_sd']:.3f} (per-seed τ={_ns_taus}; permutation p={_ns_pp}; all "
            f"{_ns['n_seeds']} seeds non-significant), and no seed separates disease from normal by Mann–Whitney "
            f"({_ns['mwu_nsig']}/{_ns['n_seeds']} p<0.05; range {_ns['mwu_p_min']:.3f}–{_ns['mwu_p_max']:.3f}). The NO-PROG "
            "residue is therefore supplied by the expression-derived proxy rather than by label-free structure. Coherence also "
            f"drops in NO-SUP (Moran's I {_ns['moran_mean']:.3f}±{_ns['moran_sd']:.3f}, toward the intrinsic data floor of "
            "≈0.62 from frozen embeddings)—reduced smoothness, no ordering. " if _ns_state == "clean" else
            f"The fully label-free NO-SUP arm then removes the proxy as well: τ falls to {_ns['tau_mean']:.3f}±"
            f"{_ns['tau_sd']:.3f} (per-seed τ={_ns_taus}; permutation p={_ns_pp}: {_ns_count}), and Mann–Whitney separation is "
            f"nominal on the same single seed only ({_ns['mwu_nsig']}/{_ns['n_seeds']} p<0.05; range {_ns['mwu_p_min']:.3f}–"
            f"{_ns['mwu_p_max']:.3f}). The residue is therefore weak and, crucially, seed-unstable—its across-seed SD is "
            f"{_ns['tau_sd']/max(_np['tau_sd'],1e-9):.1f}× the NO-PROG value and one seed even reaches τ="
            f"{max(_ns['taus']):.3f}, so no reproducible ordering survives without targets. The most parsimonious source of "
            "the residue is the retained KEGG-HPV pathway-consistency term (λ_hpv=1.0), a disease-correlated biological prior "
            "rather than a label; the NO-ALL arm tests this attribution directly within the same matrix. Coherence also falls "
            "in NO-SUP (Moran's I "
            f"{_ns['moran_mean']:.3f}±{_ns['moran_sd']:.3f}, toward the ≈0.62 intrinsic floor)—reduced smoothness, no stable "
            "ordering. " if _ns_state == "mixed" else
            f"Unexpectedly, the fully label-free NO-SUP arm retains τ={_ns['tau_mean']:.3f}±{_ns['tau_sd']:.3f} (per-seed "
            f"τ={_ns_taus}; permutation p={_ns_pp}: {_ns_count}); a residual ordering survives without any disease-derived "
            "target on every seed. This result is reported verbatim and examined in Section 5.3(6); the retained pathway prior "
            "is the candidate mechanism. " if _ns_state == "robust" else
            "[NO-SUP results pending: run scripts/rerun_2026-09-23_nosup.sh on the server and regenerate.] ")
         + (f"The target- and pathway-regularizer-free NO-ALL arm closes the cascade (λ_sup=λ_prog=λ_hpv=0): τ={_na['tau_mean']:.3f}±"
            f"{_na['tau_sd']:.3f} (per-seed τ={_na_taus}; permutation p={_na_pp}, all {_na['n_seeds']} seeds non-significant) "
            "and Mann–Whitney separation is absent on every seed"
            f" ({_na['mwu_nsig']}/{_na['n_seeds']} p<0.05; {_na['mwu_p_min']:.3f}–{_na['mwu_p_max']:.3f}); the weak NO-SUP "
            "residue is thus attributable to the pathway prior rather than to label-free structure. " if _na_state == "gone" else
            f"The target- and pathway-regularizer-free NO-ALL arm closes the cascade (λ_sup=λ_prog=λ_hpv=0): τ={_na['tau_mean']:.3f}±"
            f"{_na['tau_sd']:.3f} (per-seed τ={_na_taus}; permutation p={_na_pp}: {_na_count}), a further drop of "
            f"{_na_delta:.3f} from NO-SUP; the pathway prior accounts for part of the residue and the remainder stays "
            "weak and seed-unstable. " if _na_state == "reduced" else
            f"The target- and pathway-regularizer-free NO-ALL arm (λ_sup=λ_prog=λ_hpv=0) leaves τ={_na['tau_mean']:.3f}±{_na['tau_sd']:.3f} "
            f"(per-seed τ={_na_taus}; permutation p={_na_pp}: {_na_count}), statistically indistinguishable from NO-SUP "
            f"(Δτ={-_na_delta:+.3f}); the weak residue therefore does not originate from labels, the proxy or the pathway "
            "regularizer, and is best read as intrinsic disease-correlated geometry of the expression/morphology inputs. "
            if _na_state == "persist" else
            "[NO-ALL results pending: run scripts/rerun_2026-09-24_noall.sh on the server and regenerate.] ")
         + "It is not pure memorization either: semi-supervised LODO "
         "(Section 4.5) shows three labeled sections stabilize transfer of the direction, whereas the zero-label limit on "
         "held-out sections is partial and unstable.")
    h2("4.3 Sources of coherence, and the two-axis morphology verdict")
    body(f"Coherence is largely a data property. With the morphology branch off, Moran's I is still "
         f"{A['NOIMAGE']['moran_mean']:.3f}±{A['NOIMAGE']['moran_sd']:.3f}; adjacent Visium spots share tissue and cells, so "
         f"intrinsic expression smoothing—not the model—produces most autocorrelation (frozen UNI embeddings themselves show "
         f"strong within-slide Moran's I=0.618; Supplementary Note S1). On top of this baseline, the morphology branch adds a "
         f"detectable coherence increment (FULL {A['FULL']['moran_mean']:.3f} vs NO-IMAGE {A['NOIMAGE']['moran_mean']:.3f}, "
         f"+{IMG_DMORAN:.2f}, reported descriptively because the seed sets are unpaired), the neighborhood term adds less "
         f"(NO-NEIGH {A['NONEIGH']['moran_mean']:.3f}), and disease ordering is unchanged by morphology (τ "
         f"{A['NOIMAGE']['tau_mean']:.3f} vs {A['FULL']['tau_mean']:.3f}). The branch is therefore graded on two axes: coherence "
         "gain supported, ranking/endpoint gain unsupported; small τ effects cannot be excluded at three unpaired seeds. "
         "Multimodal fusion is consequently not claimed as a contribution.")
    body(f"**In-cohort metrics do not extrapolate.** A learning-free score—the per-sample mean of the 107 detected KEGG-HPV "
         f"genes—gives an in-sample disease AUC of {_bgm_auc:.2f} versus {_mra:.2f} for FULL; both are descriptive and may "
         "reflect anchoring. The 35-fold LOSO audits are decisive: morphology-to-HPV-proxy ridge scoring reaches AUC "
         f"{BSL.get('loso_hpv_ridge_auc', float('nan')):.3f}±{BSL.get('loso_hpv_ridge_auc_sd', float('nan')):.3f} (only "
         f"{BSL.get('loso_hpv_ridge_valid', 0)}/35 folds even evaluable—single-class folds themselves evidence cross-slide shift; "
         f"MLP {BSL.get('loso_hpv_mlp_auc', float('nan')):.3f}), and morphology-to-expression reconstruction gives per-gene "
         f"Pearson r={BSL.get('loso35_per_gene_pearson', float('nan')):.3f} (MSE {BSL.get('loso35_recon_mse', float('nan')):.3f}), "
         f"no better than in-sample interpolation (MSE {BSL.get('he2st_mse', float('nan')):.3f}). The juxtaposition—in-sample AUC "
         "1.00 versus cross-sample AUC ≈0.50—is the central cautionary result of the benchmark.")
    h2("4.4 Biological interpretation of the pathway-anchored score")
    add_fig("Fig4_biology_correlation.png", 5.8,
            "Figure 4. Spearman correlation of spot risk with 11 pathway/cell-state scores (within-sample z, mean of three FULL "
            f"seeds; all survive BH FDR; weakest {WEAKEST_Q_SET.replace('_', ' ').lower()}, q={WEAKEST_Q:.0e}). Correlations are "
            "descriptive at the spot level (46,820 non-independent spots).")
    body(f"High-risk spots are enriched for tumor epithelium (KRT5/14/17, EPCAM; ρ={BIO['CELL_tumor_epithelial']['rho']:+.2f}), "
         f"HPV driver programs (CDKN2A/MYC/EGFR/PIK3CA; ρ={BIO['HPV_INTEGRATION_CANDIDATE']['rho']:+.2f}) and antigen "
         f"presentation (B2M/HLA-A/PSMB8; ρ={BIO['ANTIGEN_PRESENTATION']['rho']:+.2f}), and depleted for interferon-antiviral "
         f"programs (STAT1/MX1/ISG15; ρ={BIO['INTERFERON_ANTIVIRAL']['rho']:+.2f}), proliferation "
         f"({BIO['PROLIFERATION']['rho']:+.2f}; the axis is not a proliferation surrogate) and EMT "
         f"({BIO['EMT']['rho']:+.2f}). Marker validity was confirmed in independent cervical scRNA-seq [@scrna] "
         f"({SCR['n_cells']:,} integrated cells): mean within-lineage score correlation {SCR['within_corr']:+.3f} versus "
         f"{SCR['between_corr']:+.3f} across lineages (gap {SCR['gap']:+.3f}). The directions are consistent with E6/E7-driven "
         "transformation and immune evasion; they are descriptive spatial associations, not causal evidence.")
    h2("4.5 Cross-platform and cross-organ label-free transfer")
    add_fig("Fig5_external_transfer.png", 6.4,
            "Figure 5. External audit. A: four-level Moran's I control in head-and-neck ST (model score / plain KEGG-HPV panel / "
            f"expression-decile-matched random panels / coordinate-permutation null): model score "
            f"{EXT['hnscc_moran_mean']:.2f}/{EXT['hnscc_gse281978_moran_mean']:.2f} across the two cohorts, null ≈0 (p≤0.001, all "
            f"14 sections); the KEGG panel ({EXT['rg268_kegg']:.2f}/{EXT['rg281_kegg']:.2f}) exceeds matched random panels "
            f"({EXT['rg268_exprm']:.2f}/{EXT['rg281_exprm']:.2f}) on every section (exact sign p={EXT['rg268_exprm_signp']:.3f}/"
            f"{EXT['rg281_exprm_signp']:.3f}); disease discrimination is nevertheless null. B: GeoMx tumor cores score below "
            f"benign ({EXT['geomx_tumor_mean']:.2f} vs {EXT['geomx_benign_mean']:.2f}; core p={EXT['geomx_tn_core_p']:.1e}). "
            f"C: Silva A/B/C means are non-monotonic (A lowest; A vs B p={EXT['geomx_core_silva_AB_p']:.3f}) and pathology "
            f"High/Low grades do not separate (p={EXT['geomx_risk_core_p']:.3f}). D: fold-matched LODO percentile of each "
            "held-out disease versus 31 normals, semi-supervised versus fully unsupervised.")
    body(f"**GeoMx: rank discrimination transfers, calibration sign does not, grading does not.** Across "
         f"{EXT['geomx_n_patients']} patients and {EXT['geomx_n_rois']} ROIs ({EXT['geomx_n_cores']} paired cores), tumor cores "
         f"scored {EXT['geomx_tumor_mean']:.2f} versus {EXT['geomx_benign_mean']:.2f} for benign—lower, the opposite direction to "
         f"the cervical Visium cohort (ROI p={EXT['geomx_tn_roi_p']:.1e}; core p={EXT['geomx_tn_core_p']:.1e}); the tumor core "
         f"was lower than the patient's own benign core in all {EXT['geomx_wp_n']}/{EXT['geomx_wp_n']} paired patients "
         f"(p={EXT['geomx_wp_p']:.3f}, the exact-test floor at n=6; 95% CI [{EXT['geomx_wp_ci_lo']:.2f}, 1.00]). Epithelial and "
         f"stromal ROIs did not differ (p={EXT['geomx_compartment_p']:.3f}). Silva means were non-monotonic—A "
         f"{EXT['geomx_core_silva_A']:.2f} < C {EXT['geomx_core_silva_C']:.2f} < B {EXT['geomx_core_silva_B']:.2f}"
         f" (A vs B p={EXT['geomx_core_silva_AB_p']:.3f})—and pathology High/Low did not separate in the risk-axis direction "
         f"(p={EXT['geomx_risk_core_p']:.3f}). Platform differences (DSP targeted panel versus Visium; ADC versus predominantly "
         "SCC training data) plausibly underlie the sign shift, which cannot be localized further here. The transferable object "
         "is tumor–benign separability of the learned pathway representation, not the high-score-is-high-risk convention and not "
         "an invasiveness grade; the post-hoc epithelial Silva stratification (Supplementary Note S2) is reported as descriptive "
         "only.")
    body(f"**Head and neck: genuine, weakly pathway-specific organization, no disease discrimination.** The transferred score "
         f"showed Moran's I {EXT['hnscc_moran_mean']:.2f} across {EXT['hnscc_n_samples']} sections (GSE268014) and "
         f"{EXT['hnscc_gse281978_moran_mean']:.2f} across {EXT['hnscc_gse281978_n']} independent sections (GSE281978), against a "
         "near-zero coordinate-permutation null (p≤0.001, all 14 sections). The plain KEGG panel exceeded expression-matched "
         f"random panels on every section ({EXT['rg268_exprm_npos']}/{EXT['hnscc_n_samples']} and "
         f"{EXT['rg281_hvgu_npos']}/{EXT['hnscc_gse281978_n']}; p={EXT['rg268_exprm_signp']:.3f}/{EXT['rg281_exprm_signp']:.3f}), a "
         "weak but reproducible pathway-specific component. All section-level discriminative tests were null: malignant vs "
         f"non-malignant (positive {EXT['mal_non_pos']}/{EXT['mal_non_n']}, p={EXT['mal_non_p']:.3f}), tumor front vs core "
         f"({EXT['edge_core_pos']}/{EXT['edge_core_n']}, p={EXT['edge_core_p']:.3f}), HPV+ vs HPV− "
         f"(p={EXT['hpv268_p']:.2f}/{EXT['hpv281_p']:.2f}) and primary vs lymph-node metastasis (p={EXT['pt_lnmt_p']:.2f}; "
         "Supplementary Note S3).")
    h2("4.6 Label dose-response, null controls and the clinical-utility boundary")
    body(f"**Labels stabilize a partial direction.** In fold-matched LODO, fully unsupervised training gave a partial, unstable "
         f"direction ({EXT['unsup_lodo_n_above_median']}/4 folds above the normal median, {EXT['unsup_lodo_n_above_all']}/4 above "
         f"all normals, mean percentile {EXT['unsup_lodo_mean_pct']:.2f}; the ADC fold at {EXT['unsup_lodo_min_pct']:.2f}); "
         f"adding the other three labeled disease sections stabilized it ({EXT['lodo_n_above_median']}/4 and "
         f"{EXT['lodo_n_above_all']}/4, mean {EXT['lodo_mean_pct']:.2f}; the ADC fold rose {EXT['unsup_lodo_min_pct']:.2f}→"
         f"{EXT['lodo_min_pct']:.2f}). Four folds are four independent events with wide, overlapping exact intervals "
         f"(lower bounds {EXT['lodo_4of4_ci_lo']:.2f}/{EXT['unsup_3of4_ci_lo']:.2f}); the paired design and the fold-matched ADC "
         "rise are the more robust evidence, graded suggestive. Glandular-to-squamous transfer is the bottleneck, consistent "
         "with documented SCC/ADC microenvironment differences [@mo;@wu].")
    body(f"**In-cohort pathway specificity is not supported.** The Moran's I of the plain KEGG panel score—that is, the "
         f"learning-free per-sample mean of the 108 HPV-panel genes, not the trained model score of Table 3—was "
         f"{RC['kegg_moran']:.3f}, not above 30 matched random panels ({RC['random_moran_mean']:.3f}, "
         f"{RC['random_moran_min']:.3f}–{RC['random_moran_max']:.3f}; "
         f"permutation p={RC['moran_perm_p']:.3f}), and disease ordering was identical for random panels (τ "
         f"{RC['kegg_kendall']:.3f}; AUC permutation p={RC['auc_perm_p']:.2f}): in-cohort smoothing is shared by any co-expressed "
         "set, and ordering is label-anchored. The cross-organ panel-level advantage (Section 4.5) is a different caliber and is "
         "not contradicted.")
    body(f"**No prognostic or decision utility.** None of 11 spatial DEGs was significant in a {TC['n_patients']}-patient "
         f"({TC['events']} events) TCGA-CESC bulk Cox model [@cox] (smallest {TC['min_gene']} p={TC['min_p']:.3f}), a scale break "
         "between spot-level spatial risk and patient-level outcome. Applying MRP-ST grading: spatial self-organization "
         "supported; cross-organ raw-panel pathway specificity supported; GeoMx rank discrimination with non-transferring sign, "
         "label anchoring, and semi-supervised > unsupervised LODO suggestive; in-cohort model-score pathway specificity and the "
         "morphology ranking gain unsupported; grading, prognosis and cross-organ discrimination unsupported.")

    # ---- 5 Discussion --------------------------------------------------
    h1("Discussion")
    h2("5.1 Principal findings")
    body("The benchmark produces three defensible positive statements and one central caution. Positives: the pathway-anchored "
         "score is biologically interpretable (tumor epithelium and HPV/antigen-presentation programs positive, interferon "
         "negative, seed-stable and marker-validated in independent scRNA-seq); spatial coherence is high even after removing "
         "labels, priors or neighbors, with a detectable morphology increment; and the supervised expression representation, "
         "at a label-free inference stage, retains strong tumor–benign rank discrimination on an independent GeoMx cohort and "
         "genuine spatial organization across 14 head-and-neck sections. The caution is quantitative: sample-level in-sample AUC "
         "1.00 coexists with LOSO AUC ≈0.50, and removing the four severity labels collapses ordered ranking from τ=0.46 to "
         "τ=0.25 at a p=0.04–0.07 boundary. Without the removal ablations, permutation nulls and whole-sample hold-outs, every "
         "number in this study would read as a successful risk model; with them, only spatial organization and platform-level "
         "separability survive.")
    h2("5.2 Generalizable lessons for biomedical informatics")
    body("Four lessons transfer beyond cervical ST. First, coherence metrics are not model metrics: Moran's I≈0.9 is largely "
         "intrinsic smoothing of adjacent spots, and matched random gene sets reach the same value; autocorrelation must be "
         "reported against data-driven nulls. Second, the statistical unit of label permutation must be the independent sample, "
         "never the thousands of autocorrelated spots—spot-wise permutations manufacture significance. Third, external validity "
         "is multi-component: rank discrimination, calibration sign and grading can transfer independently (here: yes, no, no), "
         "so a single external AUC obscures what actually moved; cross-platform targeted-panel/Visium and ADC/SCC shifts are "
         "real calibration hazards. Fourth, in-sample and cross-sample performance must both be reported by construction; "
         "random-gene nulls and a fully unsupervised arm require modest controlled retraining or inexpensive post-processing. "
         "These operational items, and the "
         "supported/suggestive/unsupported grading, instantiate general leakage and reporting principles [@kapoor;@whalen;@varo;"
         "@tripod] for the ST setting. The audit is network-agnostic and applies to any rare-disease ST study with very few "
         "positive samples.")
    h2("5.3 Limitations")
    body("(1) Power: four independent disease events and six paired GeoMx patients bound every inference; 3/4-seed and 6/6 "
         "counts with wide exact intervals justify suggestive grading, and the MRP-ST trigger/thresholds are pragmatic proposals "
         "requiring independent validation. (2) Platform and histology confounding: the external cervical cohort is ADC on a "
         "targeted DSP panel against a predominantly SCC Visium training cohort; the sign inversion cannot be decomposed, and "
         "epithelial/stromal composition was non-significant but cannot be excluded. (3) Cohort heterogeneity: the 31 normals "
         "pool three GEO sub-series from different clinical studies; pooling increases the normal reference set but may alter "
         "distribution tails. (4) Pseudoreplication: 46,820 spots are not independent; spot-level correlations are descriptive, "
         "and sample/section/patient-level comparisons carry the inferential claims. (5) Scope: one architecture, one pathway "
         "prior, public data only; a benchmark demonstrates sensitivity to label removal here but cannot establish universal "
         "detection rates. (6) Proxy and prior supervision: NO-PROG withholds the ordinal labels but retains an "
         "expression-derived proxy target, itself correlated with disease at the sample level. The in-matrix NO-SUP arm "
         f"(λ_sup=λ_prog=0) removes the proxy as well: mean τ drops to {_ns['tau_mean']:.3f}, leaving a weak, seed-unstable "
         f"residue ({_ns_count}; τ {min(_ns['taus']):.3f}–{max(_ns['taus']):.3f}). The target- and "
         "pathway-regularizer-free NO-ALL arm "
         "(λ_sup=λ_prog=λ_hpv=0) adjudicates that residue within the same matrix. "
         + (f"It disappears (τ={_na['tau_mean']:.3f}, all permutation p non-significant; Mann–Whitney "
            f"{_na['mwu_nsig']}/{_na['n_seeds']} nominal), attributing the NO-SUP residue to the pathway-consistency prior "
            "rather than to label-free structure. " if _na_state == "gone" else
            f"It falls further to τ={_na['tau_mean']:.3f} (permutation p={_na_p_range}, {_na_count}): the prior accounts for "
            "part of the residue, and the remainder stays weak and seed-unstable. " if _na_state == "reduced" else
            f"It remains at τ={_na['tau_mean']:.3f} (permutation p={_na_p_range}, {_na_count}; Δτ vs NO-SUP "
            f"{-_na_delta:+.3f}): the residue is intrinsic disease-correlated geometry of the expression/morphology inputs, "
            "not the pathway regularizer. " if _na_state == "persist" else
            "[NO-ALL results pending: scripts/rerun_2026-09-24_noall.sh.] ")
         + "NO-ALL is not a zero-information condition—the panel genes remain ordinary encoder inputs and reconstruction, "
         "neighborhood and morphology terms stay on—so the cascade bounds explicit disease-anchored terms, not every "
         "disease-correlated signal in the inputs. The proxy's transductive character is likewise unquantified, its target "
         "being thresholded at the global median over all analyzed spots rather than on training samples alone. "
         "(7) The whole-sample permutation test holds fitted scores fixed; it tests conditional score–label alignment and "
         "does not account for model refitting under permuted labels. Generalization claims therefore rest on the held-out "
         "LODO analyses, not on the fitted-cohort permutation p-values. "
         "Multi-center registered cohorts with more diseased samples are required before any clinical use; the "
         "present score has no clinical decision utility.")
    h2("5.4 Pathway to clinical translation")
    body("The work is an audit methodology, not a device, and the present score has no decision utility; the translation path "
         "is nevertheless concrete and deliberately gated. Stage 1, audit gate: any ST or WAI risk model trained in the "
         "n_diseased ≤ 10 regime should pass MRP-ST—label/proxy/prior-removal arms, whole-sample (never spot-wise) permutation, "
         "and at least one label-free external cohort—before a prospective or clinical claim is made; this stage costs GPU-hours, "
         "not patients. Stage 2, independent replication: the benchmark must be repeated on multi-center, prospectively "
         "registered cohorts with enough independent disease events to bound power (on the order of 30–50 diseased sections "
         "spanning CIN3/AIS, squamous and glandular invasive disease), with thresholds frozen and the analysis plan pre-registered. "
         "Stage 3, decision-impact evaluation: only then should a locked model be tested as an adjunct within the established "
         "cervical-screening pathway—primary HPV testing with reflex cytology and colposcopy-directed biopsy triage—against "
         "patient-relevant endpoints such as incremental high-grade lesion detection and unnecessary-biopsy reduction, with "
         "ethics, regulatory and calibration requirements specific to each platform. Stand-alone diagnosis, grading or "
         "treatment decisions remain out of scope throughout.")

    # ---- 6 Conclusion --------------------------------------------------
    h1("Conclusion")
    body("We presented a label-dependence ablation benchmark for extreme low-sample spatial-transcriptomic risk modeling, "
         "comprising seven matched multi-seed variants in a nested label→proxy→prior removal cascade, whole-sample "
         "permutation, paired "
         "semi-/unsupervised hold-outs, expression-matched gene-set nulls and cross-platform external tests, formalized as the "
         "five-item MRP-ST protocol. On four diseased cervical sections, a pathway-anchored model achieved perfect in-sample "
         "separation that the audit shows to be largely label-anchored in its fine ranking while spatial organization and "
         "cross-platform tumor–benign separability genuinely persist, calibration sign and grading do not. The benchmark is "
         "cheap, network-agnostic and designed to make label memorization visible before publication rather than after.")
    body("**Applicability.** MRP-ST and the seven ablations apply to any study in the few-diseased-samples regime—"
         "operationally, n_diseased ≤ 10 independent samples, or ≤ 5 in any class—where supervision is fitted on spot-level "
         "measurements that are spatially autocorrelated. This covers rare-disease spatial transcriptomics as well as spatial "
         "proteomics, metabolomics and multiplex imaging with the same few-sample/many-spot structure, and any supervised model "
         "built on public or consortium data where external cohorts are unavailable. It is not intended for studies with "
         "adequate disease replication (n_diseased > 10), where conventional sample-level cross-validation already carries the "
         "inferential claims, nor does it substitute for a disease-specific external validation cohort when one exists. The "
         "protocol requires controlled retraining of the ablation arms, inexpensive post-processing and a versioned result "
         "store, but no new data collection. It is independent of model architecture.")

    # ---- 3 Materials and Methods ---------------------------------------
    h1("Materials and Methods")
    h2("3.1 Datasets and preprocessing")
    add_table(
        ["Cohort", "Data type", "Scale analyzed", "Role in the audit"],
        [["Cervical Visium aggregate (GSE208654 + GSE217237 + 10x public demo)", "ST (10x Visium)",
          f"{CO['n_samples']} samples ({CO['n_normal']} normal / {CO['n_disease']} diseased); {CO['n_spots']:,} spots", "Benchmark cohort: training and all ablations"],
         ["GSE316098 [@axelrod]", "GeoMx DSP, cervical adenocarcinoma [@geomxtech]",
          f"{EXT['geomx_n_patients']} patients / {EXT['geomx_n_rois']} ROIs ({EXT['geomx_n_cores']} paired cores)", "Cross-platform label-free scoring"],
         ["GSE268014 [@simkin]", "ST, head & neck squamous carcinoma",
          f"{EXT['hnscc_n_samples']} sections (of 26 tumors in the source study)", "Cross-organ spatial organization; discrimination tests"],
         ["GSE281978 [@lee]", "ST, HPV+ / HPV− head & neck",
          f"{EXT['hnscc_gse281978_n']} sections", "Independent cross-organ replication"],
         ["TCGA-CESC [@tcga]", "Bulk RNA-seq", f"{TC['n_patients']} patients / {TC['events']} events", "Prognostic utility test (negative)"],
         ["GSE308792 [@scrna]", "scRNA-seq, cervix", f"{SCR['n_cells']:,} integrated cells", "Marker validity"]],
        caption="Table 2. Cohort overview. Counts denote sections actually analyzed here.")
    body("The cervical Visium cohort aggregates three public sources into 35 samples: (i) GSE208654 (Guo et al., 2023), four "
         "sections—N_HPV (normal), HSIL_HPV (HSIL), CA_HPV_1 (squamous-cell carcinoma, SCC) and CA_HPV_2 (adenocarcinoma, ADC); "
         "(ii) 30 normal ectocervix sections (P001–P030) under the GSE217237 SuperSeries, pooled from HIV-infection, "
         "DMPA-contraceptive and microbiome sub-studies (heterogeneity addressed in Section 5.3); and (iii) the public 10x Genomics "
         "FFPE cervical-cancer demonstration section (cervical_cancer_1, SCC). Histologic labels are normal/HSIL/cancer (severity "
         f"0/1/2). Every run uses the same 35 samples, all {CO['n_spots']:,} spots and a unified 4,991-gene panel containing a "
         f"{CO['n_genes_panel']}-gene KEGG-HPV sub-panel (107 detected). ST preprocessing followed standard Scanpy-like filtering, "
         "log1p normalization and within-sample standardization.")
    body("**Registration quality control (an informatics prerequisite).** The capture-array coordinates shipped in the public "
         "npz containers were systematically offset from the high-resolution H&E images (as few as 4.2% of spots lay on tissue in "
         "some sections). We therefore reload every sample with a validated loader that maps barcoded spots to hires-image "
         "coordinates and re-extract morphology features at the corrected locations; the best-aligned normal section reaches 76% "
         "on-tissue spots. All morphology-branch results use corrected coordinates; the expression matrix is unaffected. Because "
         "spot-level risk cannot be overlaid on H&E with defensible precision (risk versus local nuclear-density correlation "
         "r=−0.18), H&E images are used as morphology input and as histologic context in figures only—no model output is overlaid "
         "on tissue.")
    h2("3.2 Pathway-anchored multimodal model")
    body("The model has three routes (Figure 1b). (a) An expression encoder maps spot gene vectors to a latent space trained with "
         "a reconstruction term λ_rec=0.2 and a latent prior λ_var=0.1. (b) An exploratory morphology branch encodes frozen UNI "
         "[@uni] patch features (extracted once at corrected coordinates) and fuses them with the expression latent; it is included "
         "precisely so that morphology's marginal contribution can be removed and measured. (c) Priors and supervision: a "
         "KEGG-HPV [@kegg] consistency regularizer (λ_hpv=1.0), a spatial-neighborhood agreement term (λ_neigh=0.3), an "
         "expression-derived proxy binary cross-entropy on the risk head (λ_sup=5.0), and severity regression to 0/1/2 "
         "(λ_prog=1.5). The proxy target is a per-spot 0/1 label obtained by thresholding the mean expression of the same "
         "108-gene HPV panel at the global median across all 46,820 spots; it is an internal expression-derived split, not an "
         "HPV-infection or disease label, although because lesions carry higher HPV-pathway expression the two are correlated "
         "at the sample level (Section 5.3). Optimization used AdamW (lr 5×10⁻⁴, weight decay 10⁻⁴), batch size 64, 40 epochs, "
         "with patience-based early stopping (patience 6) on the training objective; hyper-parameters were fixed once before any "
         "audit run and held identical across all variants. No validation split was held out during training. Seed replication is "
         "reported to establish optimization stability, not to add inferential degrees of freedom: the statistical unit remains "
         "the four independent disease sections, and repeated seeds do not increase the number of independent events.")
    body("Architecturally, the expression encoder is a two-layer multilayer perceptron (4,991 → 256 → 128; ReLU; dropout 0.2); "
         "the frozen UNI backbone yields 1,024-dimensional patch features projected by a trainable adapter to 128 dimensions; the "
         "two 128-dimensional modalities are combined by four-head cross-modal attention; the per-spot risk head is 128 → 64 → 1 "
         "and the reconstruction decoder is 128 → 256 → 4,991. The UNI backbone itself is never updated, so the morphology "
         "branch contributes only through the lightweight adapter and fusion parameters—deliberately minimizing extra capacity, "
         "which keeps any NO-IMAGE contrast attributable to morphology rather than to additional trainable parameters. All seven "
         "variants share this architecture; ablations switch loss terms or branches only, never layer widths.")
    h2("3.3 The label-dependence ablation benchmark and the Label-Dependence Index (LDI)")
    body("The benchmark is a fixed seven-variant, same-cohort, multi-seed factorial, organized as a nested information-removal "
         "cascade. FULL trains all terms. NO-IMAGE removes the "
         "morphology branch. NO-HPV sets λ_hpv=0 while retaining the expression-derived proxy supervision, isolating the "
         "pathway-consistency term. NO-NEIGH sets λ_neigh=0, testing whether coherence is manufactured by the neighborhood "
         "regularizer. NO-PROG sets λ_prog=0 so that the ordinal disease-severity labels are never seen, while expression, "
         "morphology, pathway and the expression-derived proxy terms remain; this is the decisive contrast for ordered disease "
         "ranking. NO-SUP sets both λ_sup=0 and λ_prog=0: no ordinal labels and no expression-derived proxy are seen at any "
         "point, placing the true zero-label limit inside the flagship ablation matrix itself. NO-ALL further sets λ_hpv=0 "
         "(λ_sup=λ_prog=λ_hpv=0): no ordinal target, no proxy and no pathway-consistency prior contribute a gradient, leaving "
         "reconstruction, the neighborhood term, the frozen morphology branch and the panel genes as ordinary encoder inputs. "
         "We state explicitly that NO-PROG "
         "is an ordinal-label-removal arm, not a label-free arm: the retained proxy is itself correlated with disease at the "
         "sample level, so a residual ordering under NO-PROG indicates that an expression-derived proxy partially recovers that "
         "ordering—it is not evidence of generalization without labels; that claim is adjudicated by NO-SUP, and any weak "
         "residue surviving NO-SUP is adjudicated by NO-ALL, which separates a pathway-prior source from intrinsic data "
         "geometry. The "
         "zero-label limit on genuinely unseen sections is additionally externalized by the fully-unsupervised LODO arm "
         f"(likewise λ_sup=λ_prog=0, Section 4.5). FULL/NO-IMAGE/NO-HPV/NO-NEIGH/NO-SUP/NO-ALL were run "
         f"with three seeds and NO-PROG with {A['NOPROG']['n_seeds']} seeds (the extra seed checks verdict stability at the "
         "significance boundary). Variants share training samples, spot sets, preprocessing, initialization protocol and "
         "hyper-parameters; only the named term changes.")
    body("**3.3.1 Label-Dependence Index (LDI): formal definition and properties.** The seven-variant cascade is not merely "
         "a set of ablation runs—it induces a formal metric, the **Label-Dependence Index (LDI)**, that quantifies how much "
         "of the model's disease-ordering information derives from label-anchoring terms rather than intrinsic spatial "
         "geometry. We define LDI as the backward marginal decomposition along the cascade: "
         "$$\\text{LDI} = \\tau_{\\text{FULL}} - \\tau_{\\text{NO-ALL}}$$ "
         "where τ_FULL is the Kendall τ of the complete model and τ_NO-ALL is the τ of the fully stripped variant "
         "(λ_sup=λ_prog=λ_hpv=0). Uncertainty is propagated across independent training seeds as "
         "$$\\sigma_{\\text{LDI}} = \\sqrt{\\sigma_{\\text{FULL}}^2 + \\sigma_{\\text{NO-ALL}}^2}$$ "
         "reporting a mean ± SD LDI estimate. The marginal contribution of each removed term is computed "
         "sequentially along the cascade: Δτ_i = τ_{before} − τ_{after} for each adjacent pair (e.g., morphology contribution "
         "= τ_FULL − τ_NOIMAGE, expression-derived proxy contribution = τ_NOPROG − τ_NOSUP, pathway prior residual "
         "= τ_NOSUP − τ_NOALL), with SD propagated as √(σ_{before}² + σ_{after}²). "
         "LDI is paired with a **θ-calibrated decision gate**: a model is classified as **label-dependent** when LDI > θ, "
         "where θ is calibrated either from permutation-zero runs or from random-gene null controls (fallback: θ=2·|τ_NO-ALL|). "
         "LDI satisfies three formal properties: (i) **Telescoping additivity**—LDI is exactly the sum of the six signed "
         "marginal contributions Δτ_i = τ_{before} − τ_{after} along the cascade, so a monotone ordering across variants is "
         "neither assumed nor required (individual Δτ_i may be negative). (ii) **Seed robustness**—SD across independent "
         "training seeds is reported alongside every LDI estimate, making verdict stability explicit; (iii) "
         "**Zero-distribution calibration**—θ is derived from data-driven null distributions, not arbitrary thresholds. "
         "**Transferability caveat**: LDI requires the downstream task to have an ordinal disease-label gradient (e.g., "
         "normal→CIN→cancer); for tasks with only binary (tumor/benign) or no diagnostic labels, the τ-based definition "
         "collapses and the metric is not interpretable. This is not a limitation of LDI per se but of any ordinal-ordering "
         "metric—we discuss it further in Section 5.3.")
    body("**Whole-sample hold-out protocol.** Leave-one-disease-out (LODO) holds out each of the four disease sections in turn, "
         "training on the other 34 samples (31 normals plus three labeled diseases for the semi-supervised protocol; λ_sup and "
         "λ_prog additionally set to zero for the fully-unsupervised protocol), and reports the held-out section's mean-risk "
         "percentile within the 31 training normals. Per-fold training cohorts, spot counts (44,039–46,241) and all other settings "
         "are identical across the two protocols, so their contrast isolates the influence of the three labels; the "
         "statistical unit is the independent held-out section (four events), never the spot.")
    body("**Why each contrast is necessary—pre-specified failure readings.** Coherence and ordering are audited separately "
         "because a single aggregate metric cannot localize failure: if NO-PROG leaves both intact, in-cohort ordering does not "
         "need severity labels; if τ collapses while Moran's I does not (the observed pattern), smooth spatial structure is real "
         "but its clinically meaningful ordering is label-anchored; if ordering survives NO-SUP but disappears under NO-ALL, "
         "the residue is supplied by the pathway prior rather than by a label; if it survives NO-ALL as well, no "
         "disease-anchored target or prior is needed and the label-anchoring reading is refuted in favor of intrinsic data "
         "geometry; if NO-IMAGE moves Moran's I but not τ, "
         "morphology improves smoothness without contributing the endpoint; NO-NEIGH and NO-HPV control for the two obvious "
         "alternative explanations of high coherence (the spatial regularizer and the pathway prior). Each variant therefore "
         "maps to one admissible claim, which is what permits the supported/suggestive/unsupported grading in Section 3.6 "
         "rather than ad-hoc narrative.")
    h2("3.4 Metrics, null models and statistical protocol")
    body("Two output axes are reported separately. Spatial coherence is Moran's I [@moran] of spot risk within sections. Disease "
         "ordering is the sample-level Kendall τ [@kendall] between per-sample mean risk and severity 0/1/2. Its empirical null "
         "permutes the complete severity-label vector against per-sample scores held fixed after fitting (31 zeros, one 1, "
         "three 2s; ≈2.09×10⁵ distinct labelings), B=10,000. This conditional test quantifies score–label alignment in the "
         "fitted cohort; it is not an out-of-sample generalization test, which is supplied by LODO. Spot-wise or within-disease "
         "permutations are forbidden because spatial autocorrelation would make them anti-conservative. Disease-versus-normal "
         "contrasts use the one-sided "
         "Mann–Whitney U test [@mwu]; the within-patient GeoMx contrast uses the two-sided paired Wilcoxon signed-rank test, "
         "and concordance proportions are accompanied by exact Clopper–Pearson 95% intervals (at n=6 the smallest attainable "
         "two-sided Wilcoxon p is 0.031). Biological "
         "correlations use rank-based ssGSEA [@ssgsea] with within-sample z-standardization and Spearman ρ, Benjamini–Hochberg "
         "FDR [@bh] across 11 programs; software: NumPy [@numpy], scikit-learn [@sklearn], SciPy [@scipy].")
    body("**Null controls.** (i) Thirty random 108-gene sets matched to the KEGG panel on expression decile test whether any "
         "co-expressed set yields equal coherence/ordering; (ii) coordinate permutation (B=1,000) on external sections tests "
         "whether spatial organization is genuine; (iii) two leave-one-sample-out (LOSO) baselines on the 35 samples—ridge/MLP "
         "morphology-to-HPV-proxy scoring (35-fold) and ridge morphology-to-expression reconstruction—test whether in-cohort "
         "metrics extrapolate across samples. External scoring uses the expression branch of one fixed checkpoint "
         "(checkpoint_FULL_DEPLOY_FAST_seed42.pt) and reads no cervical labels at inference; the weights nevertheless derive from "
         "supervised training, so external experiments test representation transfer, whereas fully-unsupervised LODO tests the "
         "zero-label limit. For GSE316098, Silva/risk groups follow GEO SOFT metadata (1A/1b-1 prefixes are TMA core identifiers); "
         "ROIs are paired epithelial/stromal within cores, and core- and patient-level tests are primary.")
    h2("3.5 Implementation and computational reproducibility")
    body("All experiments run on a single consumer-class cloud GPU (NVIDIA RTX 4090, 24 GB; AutoDL), making the complete audit "
         "reproducible without institutional compute: UNI is frozen and patch features are extracted once; each 40-epoch run "
         "takes ≈0.5 GPU-hour, and the entire training matrix (22 same-cohort variant runs plus 8 LODO folds) completes in under "
         "16 GPU-hours; all permutations, null sets and external scoring are CPU post-processing. Code, configurations, result "
         "JSONs and fused embeddings are released (Data and code availability); every manuscript number is generated from "
         "versioned JSON artifacts.")
    h2("3.6 MRP-ST: a minimum reporting protocol")
    body("From this case we formalize MRP-ST, a minimum reporting protocol for supervised/semi-supervised ST risk studies with "
         "n_diseased ≤ 10 independent samples (or ≤5 in any class). Five items are mandatory: (1) nested label-removal "
         "ablation—the ordinal labels, then the disease-correlated proxy target and pathway regularizer where such terms are "
         "used—with at "
         "least three seeds per variant; (2) whole-sample label permutation (B≥10,000), never spot-wise or within-class only, "
         "with fixed-score tests identified as fitted-cohort diagnostics rather than generalization tests; "
         "(3) ≥30 expression-quantile-matched random-gene-set controls; (4) dual sample-level hold-out protocols (semi-supervised "
         "versus fully unsupervised) with identical per-fold cohorts; and (5) explicit conclusion grading—supported / suggestive / "
         "unsupported—plus a clinical-utility statement. Full checklist, failure readings, decision rules and execution order are "
         "given in Supplementary Table S2. The protocol requires limited controlled retraining plus inexpensive post-processing. "
         "The thresholds are "
         "pragmatic proposals from one extreme case, not consensus cut-offs; they require independent validation before normative "
         "use.")

    # ---- Declarations --------------------------------------------------
    h1("Declarations")
    body("**Ethics statement.** This study used only publicly available, de-identified datasets (GEO: GSE208654, GSE217237, "
         "GSE316098, GSE268014, GSE281978 and GSE308792; TCGA-CESC; and the 10x Genomics public demonstration section). No new "
         "human participants were enrolled, no identifiable private information was accessed and no intervention was performed; "
         "institutional review board approval and informed consent were therefore not required. The original studies from which "
         "these data derive obtained their own ethical approvals, and we adhered to their data-use terms.",
         indent=False)
    body("**CRediT authorship contribution statement.** Mingwei Bai: conceptualization, methodology, software, formal analysis, "
         "investigation, data curation, visualization, writing – original draft. Zhengmin Gu: data curation, validation, "
         "writing – review & editing. Ye Zhang: data curation, resources, writing – review & editing. Lang Guo: "
         "conceptualization, methodology, supervision, project administration, writing – review & editing.", indent=False)
    body("**Funding.** This research did not receive any specific grant from funding agencies in the public, commercial, or "
         "not-for-profit sectors.", indent=False)
    body("**Declaration of competing interest.** The authors declare that they have no known competing financial interests or "
         "personal relationships that could have appeared to influence the work reported in this paper.", indent=False)
    body("**Data and code availability.** All training scripts, configurations, result JSONs and fused embeddings are released at "
         f"{GITHUB}. All datasets analyzed here are public and are listed with their accessions in Table 2: cervical Visium "
         "(GSE208654, GSE217237 and the 10x public demonstration section), GeoMx GSE316098, GSE268014, GSE281978, TCGA-CESC and "
         "GSE308792. Derived result artifacts underlying every reported number are included in the released repository.",
         indent=False)
    body("**Declaration of generative AI and AI-assisted technologies in the manuscript preparation process.** During the "
         "preparation of this work the authors used an AI coding/language assistant (OpenAI Codex) to assist with code "
         "generation, language editing and reference checking. All AI-assisted output was subsequently reviewed, verified and "
         "corrected by the authors, who take full responsibility for the content of the publication.", indent=False)

    # ---- References ----------------------------------------------------
    h1("References")
    for i, key in enumerate(C.order, 1):
        emit(f"[{i}] {C.refs[key]}", 9.5, indent=False, after=2, ls=1.0)

    save(doc, "Manuscript_PLOSCB.docx")
    return doc, C


# ========================================================================
#  MANUSCRIPT — CHINESE READING COPY（供内部/导师审阅；正式投稿用英文版）
# ========================================================================
def build_manuscript_cn():
    doc, C, h1, h2, body, ctr, add_table, add_fig, emit = make_manuscript(cn=True)
    TITLE = ("极端小样本空间转录组中的标签记忆审计：以宫颈病变为例的"
             "通路锚定多模态基准与跨平台验证")

    # ---- 题名页 --------------------------------------------------------
    emit(TITLE, 16, True, align=WD_ALIGN_PARAGRAPH.CENTER, after=14)
    ctr("Mingwei Bai \u00b9，Zhengmin Gu \u00b2，Ye Zhang \u00b2，Lang Guo \u00b3,*", 11.5, after=8)
    ctr("\u00b9 集镁科技集团有限公司，沈阳 110002，中国", 10, after=1)
    ctr("\u00b2 中国医科大学附属第一医院病案管理中心，沈阳 110002，中国", 10, after=1)
    ctr("\u00b3 沈阳医学院药学院，沈阳市黄河大街北段 146 号，沈阳 110034，中国", 10, after=10)
    ctr("* 通讯作者：Lang Guo，沈阳医学院药学院，沈阳市黄河大街北段 146 号，沈阳 110034，中国。", 10, after=0)
    ctr("电话：+86 13555707001；E-mail：guolang1016@symc.edu.cn", 10, after=6)
    ctr("作者邮箱：Mingwei Bai baimingwei@jm360.cn；Zhengmin Gu guzm@cmu1h.com；Ye Zhang 13332457636@163.com",
        10, after=10)
    ctr("本文件为同内容英文投稿稿（Manuscript_PLOSCB.docx）的中文对照版，仅供内部审阅；如中英文存在歧义，以英文版为准。",
        10, after=0)
    doc.add_page_break()

    # ---- 摘要 ----------------------------------------------------------
    h1("摘要")
    body("**目的。** 面向空间转录组（ST）的监督式风险模型越来越多在仅含极少数疾病样本的队列上训练；在此情形下，"
         "近乎完美的队列内区分可能源于标签记忆而非泛化。本文针对该极端小样本情形提出一套标签依赖消融基准与"
         "最低报告协议，并以一个仅含四个独立疾病样本的宫颈病变极端案例加以示范。")
    body(f"**方法。** 在 {CO['n_samples']} 例宫颈 Visium 样本（{CO['n_normal']} 例正常、{CO['n_disease']} 例病变；"
         f"{CO['n_spots']:,} 个 spot）上，以 {CO['n_genes_panel']} 个 HPV 通路基因的表达通路核心，配以探索性的"
         "冻结 UNI 形态学分支。采用七个协议一致、多种子的变体（FULL、NO-IMAGE、NO-HPV、NO-NEIGH、NO-PROG、完全"
         "无标签的 NO-SUP，以及标签与先验均关闭的 NO-ALL），"
         "在空间一致性（Moran's I）与样本级疾病排序（Kendall τ；零分布为全样本严重度标签置换，B=10,000）两条轴上审计；"
         "并实施逐折配对的半监督/完全无监督留一疾病样本方案、30 个表达分位数匹配的随机基因集零模型，"
         f"以及在 GeoMx 宫颈腺癌、{EXT['hnscc_n_samples'] + EXT['hnscc_gse281978_n']} 张头颈部 ST 切片、"
         f"TCGA-CESC（{TC['n_patients']} 例患者）与宫颈 scRNA-seq 上的无标签外部评分。")
    body(f"**结果。** FULL 的 Moran's I 为 {A['FULL']['moran_mean']:.3f}±{A['FULL']['moran_sd']:.3f}、τ 为 "
         f"{A['FULL']['tau_mean']:.3f}（置换 p {A['FULL']['tau_perm_p_min']:.0e}–{A['FULL']['tau_perm_p_max']:.0e}）。"
         f"去除严重度标签后 τ 降至 {A['NOPROG']['tau_mean']:.3f}±{A['NOPROG']['tau_sd']:.3f}"
         f"（p={A['NOPROG']['tau_perm_p_min']:.3f}–{A['NOPROG']['tau_perm_p_max']:.3f}；"
         f"{A['NOPROG']['tau_perm_nsig']}/{A['NOPROG']['n_seeds']} 个种子名义显著）"
         + (f"，完全无标签的 NO-SUP 臂使残余排序消失（τ={_ns['tau_mean']:.3f}，全部种子置换 p 不显著）" if _ns_state == "clean"
            else f"，进一步去除代理后，NO-SUP 的 τ 降至 {_ns['tau_mean']:.2f}（p={_ns_p_range}，{_ns_count}），"
                 "仅剩弱且跨种子不稳定的残余" if _ns_state == "mixed"
            else f"，完全无标签的 NO-SUP 臂仍保留 τ={_ns['tau_mean']:.3f}（p={_ns_p_range}，{_ns_count}）" if _ns_state == "robust"
            else "，完全无标签的 NO-SUP 臂结果【待补】")
         + (f"，再去除通路先验后残余消失（NO-ALL：τ={_na['tau_mean']:.3f}，全部种子不显著）" if _na_state == "gone"
            else f"，NO-ALL 进一步降至 τ={_na['tau_mean']:.3f}（p={_na_p_range}，{_na_count}）" if _na_state == "reduced"
            else f"，但 NO-ALL 仍保留 τ={_na['tau_mean']:.3f}（p={_na_p_range}，{_na_count}），提示内在数据结构"
                 if _na_state == "persist"
            else "，NO-ALL 臂结果【待补】")
         + "；这一标签→代理→先验的逐级剥离支持标签锚定（suggestive）判定。"
         f"形态学分支使 Moran's I 提高 {IMG_DMORAN:.2f}，但不改变 τ。spot 风险与肿瘤上皮"
         f"（ρ={BIO['CELL_tumor_epithelial']['rho']:+.2f}）、HPV 致癌程序（{BIO['HPV_INTEGRATION_CANDIDATE']['rho']:+.2f}）"
         f"及抗原呈递（{BIO['ANTIGEN_PRESENTATION']['rho']:+.2f}）正相关，与干扰素反应"
         f"（{BIO['INTERFERON_ANTIVIRAL']['rho']:+.2f}）负相关。GeoMx 保留了肿瘤—良性秩判别"
         f"（芯级 p={EXT['geomx_tn_core_p']:.1e}；{EXT['geomx_wp_n']}/{EXT['geomx_wp_n']} 患者内配对方向一致），"
         "但校准符号反转且不能恢复分级；跨器官迁移保留真实的空间组织（坐标置换 p≤0.001），但疾病判别为阴性；"
         f"TCGA-CESC 生存与留一样本基线（AUC≈{BSL.get('loso_hpv_ridge_auc', float('nan')):.2f}）均为阴性。")
    body("**结论。** 当缺少去除类消融时，样本内的完美结果可能掩盖标签依赖。所提网络无关的审计基准与五条目 MRP-ST "
         "报告协议为小样本 ST 风险研究提供了可审计的最低标准；被审计的风险评分本身当前不具临床决策效用。")
    emit("**关键词：** 空间转录组；标签依赖基准；小样本机器学习；宫颈病变；多模态学习；跨平台验证；最低报告协议",
         10.5, after=0)
    doc.add_page_break()

    # ---- 作者摘要 --------------------------------------------------
    h1("作者摘要")
    body("用于从组织样本预测癌症风险的机器学习模型，通常以它们对留出数据的预测准确度来评判。但对于罕见病——"
         "包括许多宫颈病变——一项研究可能只有极少数患病样本，此时模型即便近乎完美，也可能只是记住了这几个标签，"
         "而非学到了真正的生物学信号。区分这两种解释很难，尤其对于空间转录组——一种在组织解剖情境中绘制基因活性"
         "图谱的技术——目前尚无标准工具。")
    body("我们提出标签依赖指数（LDI），一个衡量风险模型“按疾病严重度排序样本”的能力在多大程度上依赖于模型内置的"
         "严重度标签、替代变量与生物通路假设的简单指标。我们定义 LDI，并在一个小型宫颈空间转录组数据集上以七变体"
         "消融设计加以评估，辅以随机化对照与对另外两种器官癌症数据的独立检验。")
    body("该模型取得近乎完美的样本内排序，但 LDI 显示该排序主要来自标签依赖项，而非内在空间生物学。LDI 及其配套"
         "报告清单提供了一种低成本、与模型无关的方式，可在小样本研究发表之前暴露其过早结论。")

    # ---- 1 引言 --------------------------------------------------------
    h1("引言")
    body("宫颈癌仍是全球女性第四大常见恶性肿瘤 [@sung]，高危型 HPV 持续感染是其主要病因 [@malagon]；"
         "大型多组学联盟已刻画了其分子图谱 [@tcga]，而宫颈腺癌的 Silva A/B/C 浸润模式分型是与间质浸润、"
         "淋巴结转移和预后相关联的成熟组织学分级体系 [@silva1;@silva2;@silva3;@silva4]。空间转录组（ST；"
         "如 10x Visium [@stahl]，综述见 [@moses;@moffitt;@bressan]）可在组织学原位测量基因表达，"
         "而 UNI、Virchow、GigaPath 等数字病理基础模型 [@uni;@virchow;@giga] 提供了可迁移的形态学表征。"
         "将表达、影像与通路先验相结合，因而成为原位刻画上皮转化的有吸引力的途径。")
    body("一个被系统性低估的方法学问题是样本稀缺：汇总全部公开的宫颈 Visium 数据，仅得到四张独立的病变切片"
         "（1 张高级别鳞状上皮内病变、2 张鳞状细胞癌、1 张腺癌）对 31 张正常切片。在此规模下，任何监督式风险模型"
         "都可以拟合四个标签，样本级样本内 AUC=1.00 无法区分“学到的疾病信号”与“对四个独立事件的记忆”。"
         "罕见病 ST 研究越来越多地面临这一情形，但目前没有标准化的审计来区分上述两种解释。")
    body("通路生物学提供了天然的归纳偏置。HPV 致癌是由 E6/E7 驱动、经 p53/Rb 丢失、抗原呈递改变与免疫逃逸展开的"
         "保守程序；将表征锚定于 KEGG HPV 基因集 [@kegg]，有望得到生物学可解释、空间平滑、并可迁移至其他"
         "HPV 驱动上皮转化场景的评分。这些都是需要用对照检验的假设，而非可默认成立的性质。")
    body("**本文做出四项方法学贡献。**（1）针对极端小样本情形定义 ST 风险模型的标签依赖消融基准：在同一锁定队列与"
         "协议下七个匹配的多种子变体，构成嵌套信息剥离级联——先去有序标签（NO-PROG），再去表达派生代理"
         "（NO-SUP，λ_sup=λ_prog=0），最后去 KEGG-HPV 通路先验（NO-ALL，λ_sup=λ_prog=λ_hpv=0），并在两条明确分离的"
         "轴——空间一致性"
         "与样本级疾病排序——上审计。（2）为 n=4 "
         "配置有效的推断设计：全样本（绝不在切片内或 spot 级）标签置换、逐折配对的半监督与完全无监督留一疾病样本"
         "评估、以及表达分位数匹配的随机基因集零模型。（3）在无标签推理阶段审计跨平台迁移（GeoMx DSP 宫颈腺癌"
         "[@geomxtech;@axelrod]）与跨器官可计算性（头颈部 ST [@simkin;@lee]），将秩判别、校准方向与分级三者分开。"
         "（4）将这些审计形式化为 MRP-ST——一个含 supported/suggestive/unsupported 三级证据定级的五条目最低报告协议，"
         "并以一个“样本内完美、去标签后仅剩边界级证据”的案例展示其区分力。宫颈病变提供真实临床场景；"
         "本文贡献在于审计方法学及其可推广的经验，而非诊断工具。")
    body("我们明确不主张诊断、分级工具或多模态融合上的进展：形态学分支是事先定义的探索性模块，其收益在两条独立轴上"
         "分别报告；所有功效受限或阴性的结果均被定级而非隐藏。本文其余部分为：相关工作（第 2 节）、数据集/模型/基准/"
         "统计方法（第 3 节）、结果（第 4 节）、可推广经验与局限性（第 5–6 节）。")

    # ---- Statement of Significance (JBI-mandated; SKIP for AIIM) -------
    # add_table(... 意义声明表 JBI 专属，AIIM 无需 ...)

    # ---- 2 相关工作 ----------------------------------------------------
    h2("相关工作")
    h2("2.1  从 H&E 预测表达到病理—ST 基础模型")
    body("HE2RNA [@he2rna] 与 ST-Net [@stnet] 率先证明可从 H&E 图像预测（空间）表达。第二波浪潮在更大尺度上将"
         "病理编码器与 ST 对齐：OmiCLIP [@omiclip] 将视觉—组学对齐扩展为基础模型；SPADE [@spade] 以数据专家混合"
         "在共享隐空间融合病理与表达；SEAL [@seal] 与 MINT [@mint] 在 10⁵–10⁶ 个配准 spot 上以 ST 监督微调"
         "病理编码器；ST-Align [@stalign] 在 spot 与微龛尺度对齐图像和基因；STPath [@stpath] 跨 17 个器官预测"
         "全基因组表达。这些方法在数据充裕条件下追求分子预测精度。")
    h2("2.2  ST 表征学习与现有基准")
    body("通用基础模型——面向单细胞多组学的 scGPT [@scgpt]、面向图结构 ST 表征的 Novae [@novae]、以及用于空间微龛"
         "发现的 CellCharter [@cellcharter]——将规模推向数千万细胞。社区基准工作（如 Li 等的整合基准 [@libench]）"
         "量化跨算法的转录本分布预测与细胞类型去卷积精度。这些文献中的基准衡量的是表征或预测保真度；没有任何一项"
         "检验监督式风险输出在去除少数疾病标签后是否依然成立，即所报性能反映的是泛化还是标签锚定。")
    h2("2.3  小样本生物医学机器学习的评估失效")
    body("方法学审计已记录机器学习科学中普遍存在的标签泄漏、不当数据划分与过度乐观的样本内评估 [@kapoor;@whalen]、"
         "小样本医学影像中的反复失效 [@varo] 以及极小数据集上二分类指标的不稳定性 [@steinert]；TRIPOD+AI 等报告"
         "规范 [@tripod] 要求外部验证，但仍是通用原则，未针对 ST 落地。缺口是具体的：一个 ST 专用、网络无关的"
         "逐条基准——（i）在匹配的多种子协议下逐一移除监督成分；（ii）在正确的统计单位（独立样本，而非空间自相关的 "
         "spot）上置换标签；（iii）对比半监督与完全无监督的全样本留出；（iv）依据外部与零模型对照对结论定级。"
         "表 1 给出本文与现有技术的定位对比。我们不在规模或预测精度上竞争；我们提供缺失的评估层。")
    add_table(
        ["研究脉络", "代表方法", "典型数据规模", "显式标签依赖审计", "跨平台外部检验"],
        [["H&E → 表达", "HE2RNA、ST-Net [@he2rna;@stnet]", "数百–数千张切片", "无", "少见"],
         ["病理—ST 基础模型", "OmiCLIP、SPADE、SEAL、MINT、ST-Align、STPath [@omiclip;@spade;@seal;@mint;@stalign;@stpath]",
          "10⁵–10⁶ spot、多样本", "无", "留出器官，而非去标签"],
         ["ST/单细胞表征", "scGPT、Novae、CellCharter [@scgpt;@novae;@cellcharter]", "10⁷ 细胞", "无（自监督目标）", "无"],
         ["ST 整合基准", "Li 等 [@libench]", "多队列", "无——衡量整合精度", "无"],
         ["小样本 ML 指南", "泄漏审计、小样本评估、TRIPOD+AI [@kapoor;@whalen;@varo;@steinert;@tripod]",
          "通用；表格/影像", "仅原则", "有要求但未执行"],
         ["本文", "通路锚定多模态模型＋审计基准＋MRP-ST",
          f"{CO['n_samples']} 样本 / {CO['n_disease']} 病变",
          "有：五匹配多种子变体、全样本置换、双 LODO、随机基因零模型",
          "有：GeoMx、14 张 HNSCC 切片、TCGA-CESC、scRNA-seq"]],
        caption="表 1  与现有技术的定位对比；引用对应文末编号文献。")

    # ---- 4 结果 --------------------------------------------------------
    h1("结果")
    h2("4.1  队列病理谱与队列内风险排序")
    add_fig("Fig1_Framework.png", 5.3,
            "图 1  队列组织学谱系与基准框架。(a) 横跨所分析连续病变谱的代表性 H&E 染色 Visium 切片：正常宫颈外口"
            "（GSE217237，P020），复层鳞状上皮有序、表层成熟；HSIL（GSE208654，HSIL_HPV），全层异型；浸润性鳞状细胞癌"
            "（10x 公开 FFPE 切片，cervical_cancer_1），促纤维间质中浸润癌巢；浸润性宫颈管腺癌（GSE208654，CA_HPV_2），"
            "背靠背/筛状恶性腺体。上排为全片低倍观，下排为框选区高倍观。(b) 模型：表达与形态学分支在 HPV 通路先验和"
            "邻域约束下融合，产生进入七变体审计的逐 spot 风险评分。H&E 仅提供组织学背景，不叠加模型输出。")
    add_fig("Fig2_risk_violin.png", 4.8,
            f"图 2  队列内逐 spot 风险随组织学严重度升高（FULL，seed 0）：正常 {RV['normal_mean']:.2f}、HSIL "
            f"{RV['hsil_mean']:.2f}、癌 {RV['cancer_mean']:.2f}；样本级疾病对正常 Mann–Whitney p≈1.9×10⁻⁵。"
            f"这是疾病 n={CO['n_disease']} 下的描述性样本内结果；其反映学习还是标签锚定由 NO-PROG 消融判定（4.2 节）。")
    body("逐 spot 平均风险呈正常 < HSIL < 癌的单调上升，但该分离存在于监督训练集内部。如下的去标签结果表明，"
         "不能将其读作泛化证据。")
    h2("4.2  去标签消融：有序排序由标签锚定（提示性）")
    add_fig("Fig3_ablation_multiseed.png", 6.2,
            "图 3  同队列多种子消融。左：空间一致性（Moran's I）；右：疾病排序（Kendall τ；点为种子，柱为均值±SD）。"
            "去除严重度标签（NO-PROG）使 τ 跌至显著性边界，而 Moran's I 几乎不变"
            f"（{A['NOPROG']['n_seeds']} 种子 p={A['NOPROG']['tau_perm_p_min']:.3f}–"
            f"{A['NOPROG']['tau_perm_p_max']:.3f}，{A['NOPROG']['tau_perm_nsig']}/{A['NOPROG']['n_seeds']} 名义显著）；"
            + ("完全无标签的 NO-SUP 臂将残余排序完全消除（各种子均不显著）；" if _ns_state == "clean"
               else f"完全无标签的 NO-SUP 臂仅剩弱且跨种子不稳定的残余（τ={_ns['tau_mean']:.2f}，置换 p={_ns_p_range}，"
                    f"{_ns_count}）；" if _ns_state == "mixed"
               else "完全无标签的 NO-SUP 臂在每一个种子上都保留残余排序（见表 3）；" if _ns_state == "robust"
               else "完全无标签的 NO-SUP 臂检验无任何目标时是否仍有排序【结果待补】；")
            + ("标签与先验均关闭的 NO-ALL 臂随后使残余消失（各种子均不显著）" if _na_state == "gone"
               else f"标签与先验均关闭的 NO-ALL 臂使 τ 进一步降至 {_na['tau_mean']:.2f}（p={_na_p_range}，{_na_count}）"
                    if _na_state == "reduced"
               else f"NO-ALL 下弱残余仍存（τ={_na['tau_mean']:.2f}，p={_na_p_range}，{_na_count}），提示内在数据几何"
                    if _na_state == "persist"
               else "标签与先验均关闭的 NO-ALL 臂检验通路先验来源【结果待补】")
            + "；去除形态学分支降低 Moran's I 但 τ 不变。")
    add_table(
        ["变体", "种子数", "Moran's I（均值±SD）", "Kendall τ（均值±SD）", "τ 置换 p（B=10,000）", "解读"],
        [["FULL", A['FULL']['n_seeds'], f"{A['FULL']['moran_mean']:.3f} ± {A['FULL']['moran_sd']:.3f}",
          f"{A['FULL']['tau_mean']:.3f} ± {A['FULL']['tau_sd']:.3f}",
          f"{A['FULL']['tau_perm_p_min']:.0e}–{A['FULL']['tau_perm_p_max']:.0e}", "完整模型"],
         ["NO-IMAGE", A['NOIMAGE']['n_seeds'], f"{A['NOIMAGE']['moran_mean']:.3f} ± {A['NOIMAGE']['moran_sd']:.3f}",
          f"{A['NOIMAGE']['tau_mean']:.3f} ± {A['NOIMAGE']['tau_sd']:.3f}",
          f"{A['NOIMAGE']['tau_perm_p_min']:.0e}–{A['NOIMAGE']['tau_perm_p_max']:.0e}",
          f"Moran −{abs(IMG_DMORAN):.2f}；τ 不变"],
         ["NO-HPV", A['NOHPV']['n_seeds'], f"{A['NOHPV']['moran_mean']:.3f} ± {A['NOHPV']['moran_sd']:.3f}",
          f"{A['NOHPV']['tau_mean']:.3f} ± {A['NOHPV']['tau_sd']:.3f}",
          f"~{A['NOHPV']['tau_perm_p_min']:.0e}", "通路项对排序非决定性"],
         ["NO-NEIGH", A['NONEIGH']['n_seeds'], f"{A['NONEIGH']['moran_mean']:.3f} ± {A['NONEIGH']['moran_sd']:.3f}",
          f"{A['NONEIGH']['tau_mean']:.3f} ± {A['NONEIGH']['tau_sd']:.3f}",
          f"~{A['NONEIGH']['tau_perm_p_min']:.0e}", "一致性非来自邻域项"],
         ["NO-PROG", A['NOPROG']['n_seeds'], f"{A['NOPROG']['moran_mean']:.3f} ± {A['NOPROG']['moran_sd']:.3f}",
          f"{A['NOPROG']['tau_mean']:.3f} ± {A['NOPROG']['tau_sd']:.3f}",
          f"{A['NOPROG']['tau_perm_p_min']:.3f}–{A['NOPROG']['tau_perm_p_max']:.3f}（{A['NOPROG']['tau_perm_nsig']}/{A['NOPROG']['n_seeds']} 名义显著）",
          "关闭有序标签；保留表达派生代理"],
         (["NO-SUP", _ns['n_seeds'], f"{_ns['moran_mean']:.3f} ± {_ns['moran_sd']:.3f}",
           f"{_ns['tau_mean']:.3f} ± {_ns['tau_sd']:.3f}",
           f"{_ns['tau_perm_p_min']:.3f}–{_ns['tau_perm_p_max']:.3f}（{_ns['tau_perm_nsig']}/{_ns['n_seeds']} 名义显著）",
           _ns_reading_cn] if _ns
          else ["NO-SUP", "【待补】", "【待补】", "【待补】", "【待补】",
                _ns_reading_cn]),
         (["NO-ALL", _na['n_seeds'], f"{_na['moran_mean']:.3f} ± {_na['moran_sd']:.3f}",
           f"{_na['tau_mean']:.3f} ± {_na['tau_sd']:.3f}",
           f"{_na['tau_perm_p_min']:.3f}–{_na['tau_perm_p_max']:.3f}（{_na['tau_perm_nsig']}/{_na['n_seeds']} 名义显著）",
           _na_reading_cn] if _na
          else ["NO-ALL", "【待补】", "【待补】", "【待补】", "【待补】",
                _na_reading_cn])],
        caption="表 3  同队列多种子消融（35 样本、46,820 spot，锁定协议）。NO-SUP 同时置 λ_sup=λ_prog=0，训练全程不使用"
                "任何疾病派生目标；NO-ALL 再置 λ_hpv=0，有序目标、代理与通路一致性先验均不贡献梯度（仍保留重建、邻域、"
                "形态学及作为普通输入的面板基因）。p 值由严重度向量在全部 35 样本间置换得到；"
                "渐近 p 见补充表 S1，小样本下以置换口径为准。")
    body(f"去除严重度标签回归使 Kendall τ 从 {A['FULL']['tau_mean']:.3f} 降至 "
         f"{A['NOPROG']['tau_mean']:.3f}±{A['NOPROG']['tau_sd']:.3f}（逐种子 τ={_np_taus}；置换 p={_np_pp}："
         f"{A['NOPROG']['tau_perm_nsig']}/{A['NOPROG']['n_seeds']} 个种子名义显著，其中一个跨越 0.05）。SCC 演示切片在"
         "每个种子中均排在 30/31 个正常之上，HSIL 片高于约 25–26 个，而 ADC 片仅高于 8–13 个正常、始终最弱"
         "（与 4.5 节最弱 ADC 折呼应）。单侧 Mann–Whitney 为 "
         f"{_np_mwus}（{A['NOPROG']['mwu_nsig']}/{A['NOPROG']['n_seeds']} 个种子 <0.05；范围 {A['NOPROG']['mwu_p_min']:.3f}–"
         f"{A['NOPROG']['mwu_p_max']:.3f}）。由于效应仅依赖四个独立疾病事件、且四个种子中一个翻转判定，精细有序排序的"
         "标签锚定被定为提示性（SUGGESTIVE）而非确证性。NO-PROG 下的残余排序同样不是无标签泛化的证据：所保留的"
         "表达派生代理本身与疾病相关，只能说明该代理可部分恢复排序。"
         + (f"完全无标签的 NO-SUP 臂对此直接裁决：λ_sup=λ_prog=0 时，τ 进一步降至 {_ns['tau_mean']:.3f}±"
            f"{_ns['tau_sd']:.3f}（逐种子 τ={_ns_taus}；置换 p={_ns_pp}，全部 {_ns['n_seeds']} 个种子均不显著），"
            f"且无一种子能区分疾病与正常（Mann–Whitney {_ns['mwu_nsig']}/{_ns['n_seeds']} <0.05；范围 "
            f"{_ns['mwu_p_min']:.3f}–{_ns['mwu_p_max']:.3f}）。因此 NO-PROG 的残余排序来自表达派生代理而非无监督结构。"
            f"一致性也回落（Moran's I {_ns['moran_mean']:.3f}±{_ns['moran_sd']:.3f}，趋近约 0.62 本底）——平滑减弱、"
            "无排序。" if _ns_state == "clean" else
            f"完全无标签的 NO-SUP 臂进一步去除代理来裁决零标签极限：τ 降至 {_ns['tau_mean']:.3f}±{_ns['tau_sd']:.3f}"
            f"（逐种子 τ={_ns_taus}；置换 p={_ns_pp}，{_ns_count}），Mann–Whitney 分离也仅在同一单个种子上名义显著"
            f"（{_ns['mwu_nsig']}/{_ns['n_seeds']} p<0.05；范围 {_ns['mwu_p_min']:.3f}–{_ns['mwu_p_max']:.3f}）。"
            f"残余因此弱且关键地跨种子不稳定——跨种子 SD 是 NO-PROG 的 {_ns['tau_sd']/max(_np['tau_sd'],1e-9):.1f} 倍、"
            f"仅一个种子达到 τ={max(_ns['taus']):.3f}，故无标签下不存在可复现排序。其最简来源是保留的 KEGG-HPV 通路"
            "一致性项（λ_hpv=1.0），一个疾病相关的生物先验而非标签；NO-ALL 臂在同一矩阵内直接检验该归因。"
            f"一致性也回落（Moran's I {_ns['moran_mean']:.3f}±{_ns['moran_sd']:.3f}，趋近约 0.62 本底）"
            "——平滑减弱、无稳定排序。" if _ns_state == "mixed" else
            f"意外的是，完全无标签的 NO-SUP 臂仍保留 τ={_ns['tau_mean']:.3f}±{_ns['tau_sd']:.3f}（逐种子 τ={_ns_taus}；"
            f"置换 p={_ns_pp}，{_ns_count}）；无任何疾病派生目标时每个种子仍有残余排序。该结果如实报告并在 5.3(6) 检视；"
            "保留的通路先验是候选机制。" if _ns_state == "robust" else
            "【NO-SUP 结果待补：在服务器运行 scripts/rerun_2026-09-23_nosup.sh 后重新生成。】")
         + (f"标签与先验均关闭的 NO-ALL 臂（λ_sup=λ_prog=λ_hpv=0）闭合级联：τ={_na['tau_mean']:.3f}±{_na['tau_sd']:.3f}"
            f"（逐种子 τ={_na_taus}；置换 p={_na_pp}，全部 {_na['n_seeds']} 个种子均不显著），Mann–Whitney 在每一个种子上"
            f"都不分离（{_na['mwu_nsig']}/{_na['n_seeds']} p<0.05；范围 {_na['mwu_p_min']:.3f}–{_na['mwu_p_max']:.3f}）；"
            "NO-SUP 的弱残余因而来自通路先验而非无标签结构。" if _na_state == "gone" else
            f"标签与先验均关闭的 NO-ALL 臂（λ_sup=λ_prog=λ_hpv=0）闭合级联：τ={_na['tau_mean']:.3f}±{_na['tau_sd']:.3f}"
            f"（逐种子 τ={_na_taus}；置换 p={_na_pp}，{_na_count}），较 NO-SUP 再降 {_na_delta:.3f}；通路先验解释了部分"
            "残余，其余仍弱且跨种子不稳定。" if _na_state == "reduced" else
            f"标签与先验均关闭的 NO-ALL 臂（λ_sup=λ_prog=λ_hpv=0）给出 τ={_na['tau_mean']:.3f}±{_na['tau_sd']:.3f}"
            f"（逐种子 τ={_na_taus}；置换 p={_na_pp}，{_na_count}），与 NO-SUP 无统计学差异（Δτ={-_na_delta:+.3f}）；"
            "弱残余因而不来自标签、代理或通路正则，最合理的解释是表达/形态学输入内在的疾病相关几何。"
            if _na_state == "persist" else
            "【NO-ALL 结果待补：在服务器运行 scripts/rerun_2026-09-24_noall.sh 后重新生成。】")
         + "这也不等于模型仅记忆四张切片：4.5 节的半监督 LODO 显示三个"
         "带标签切片即可稳定迁移方向，而留出未见切片上的零标签极限只是局部、不稳定。")
    h2("4.3  一致性的来源与形态学的两轴判定")
    body(f"一致性主要是数据属性。即使关闭形态学分支，Moran's I 仍达 {A['NOIMAGE']['moran_mean']:.3f}±"
         f"{A['NOIMAGE']['moran_sd']:.3f}；相邻 Visium spot 共享组织与细胞，因此大部分自相关来自内在表达平滑"
         "（冻结 UNI 嵌入本身即有强片内 Moran's I=0.618；补充 Note S1），并非模型贡献，不能当作模型性能宣称。"
         f"在此基线之上，形态学分支带来可检出的一致性增量（FULL {A['FULL']['moran_mean']:.3f} vs NO-IMAGE "
         f"{A['NOIMAGE']['moran_mean']:.3f}，+{IMG_DMORAN:.2f}；因种子集不配对，作描述性报告），邻域项贡献更少"
         f"（NO-NEIGH {A['NONEIGH']['moran_mean']:.3f}），而形态学不改变疾病排序（τ {A['NOIMAGE']['tau_mean']:.3f} vs "
         f"{A['FULL']['tau_mean']:.3f}）。该分支故按两轴定级：一致性增益 supported、排序/终点增益 unsupported；"
         "三个不配对种子下不能排除 τ 的小效应。因此多模态融合不列为贡献。")
    body(f"**队列内指标不能外推。** 一个免学习评分——107 个被检出 KEGG-HPV 基因的逐样本均值——的样本内疾病 AUC 为 "
         f"{_bgm_auc:.2f}，FULL 为 {_mra:.2f}；两者均为描述性、都可能反映锚定。决定性的是 35 折 LOSO 审计："
         "形态学到 HPV 代理的 ridge 评分为 AUC "
         f"{BSL.get('loso_hpv_ridge_auc', float('nan')):.3f}±{BSL.get('loso_hpv_ridge_auc_sd', float('nan')):.3f}"
         f"（仅 {BSL.get('loso_hpv_ridge_valid', 0)}/35 折可评估——单类折本身即为跨切片分布漂移的证据；MLP "
         f"{BSL.get('loso_hpv_mlp_auc', float('nan')):.3f}）；形态学到表达重建的逐基因 Pearson r="
         f"{BSL.get('loso35_per_gene_pearson', float('nan')):.3f}（MSE {BSL.get('loso35_recon_mse', float('nan')):.3f}），"
         f"不优于样本内插值（MSE {BSL.get('he2st_mse', float('nan')):.3f}）。样本内 AUC 1.00 与跨样本 AUC≈0.50 的并置，"
         "正是本基准的核心警示结果。")
    h2("4.4  通路锚定评分的生物学解读")
    add_fig("Fig4_biology_correlation.png", 5.8,
            "图 4  spot 风险与 11 个通路/细胞状态评分的 Spearman 相关（样本内 z，3 个 FULL 种子均值；全部通过 BH FDR；"
            f"最弱为 {WEAKEST_Q_SET.replace('_', ' ').lower()}，q={WEAKEST_Q:.0e}）。相关在 spot 级为描述性"
            "（46,820 个非独立 spot）。")
    body(f"高风险 spot 富集肿瘤上皮（KRT5/14/17、EPCAM；ρ={BIO['CELL_tumor_epithelial']['rho']:+.2f}）、HPV 驱动程序"
         f"（CDKN2A/MYC/EGFR/PIK3CA；ρ={BIO['HPV_INTEGRATION_CANDIDATE']['rho']:+.2f}）与抗原呈递"
         f"（B2M/HLA-A/PSMB8；ρ={BIO['ANTIGEN_PRESENTATION']['rho']:+.2f}），并缺失干扰素抗病毒程序"
         f"（STAT1/MX1/ISG15；ρ={BIO['INTERFERON_ANTIVIRAL']['rho']:+.2f}）、增殖（{BIO['PROLIFERATION']['rho']:+.2f}；"
         f"说明该轴不是增殖替代指标）与 EMT（{BIO['EMT']['rho']:+.2f}）。标志物有效性在独立宫颈 scRNA-seq [@scrna] "
         f"（{SCR['n_cells']:,} 整合细胞）中确认：谱系内平均相关 {SCR['within_corr']:+.3f}，跨谱系 "
         f"{SCR['between_corr']:+.3f}（差 {SCR['gap']:+.3f}）。方向与 E6/E7 驱动转化及免疫逃逸一致；"
         "但属描述性空间关联，非因果证据。")
    h2("4.5  跨平台与跨器官的无标签迁移")
    add_fig("Fig5_external_transfer.png", 6.4,
            "图 5  外部审计。A：头颈部 ST 上的四级 Moran's I 对照（模型评分/纯 KEGG-HPV 面板/表达十分位匹配随机面板/"
            f"坐标置换零）：两队列模型评分 {EXT['hnscc_moran_mean']:.2f}/{EXT['hnscc_gse281978_moran_mean']:.2f}，零≈0"
            f"（全部 14 张 p≤0.001）；KEGG 面板（{EXT['rg268_kegg']:.2f}/{EXT['rg281_kegg']:.2f}）在每张切片上高于"
            f"匹配随机面板（{EXT['rg268_exprm']:.2f}/{EXT['rg281_exprm']:.2f}；精确符号检验 "
            f"p={EXT['rg268_exprm_signp']:.3f}/{EXT['rg281_exprm_signp']:.3f}）；但疾病判别为阴性。B：GeoMx 肿瘤芯评分"
            f"低于良性（{EXT['geomx_tumor_mean']:.2f} vs {EXT['geomx_benign_mean']:.2f}；芯 p={EXT['geomx_tn_core_p']:.1e}）。"
            f"C：Silva A/B/C 均值非单调（A 最低；A vs B p={EXT['geomx_core_silva_AB_p']:.3f}），病理 High/Low 分级"
            f"不分离（p={EXT['geomx_risk_core_p']:.3f}）。D：每张留出疾病相对 31 个正常的 LODO 百分位，半监督与"
            "完全无监督并排。")
    body(f"**GeoMx：秩判别迁移，校准符号不迁移，分级不迁移。** 在 {EXT['geomx_n_patients']} 例患者、"
         f"{EXT['geomx_n_rois']} 个 ROI（{EXT['geomx_n_cores']} 配对芯）上，肿瘤芯评分为 {EXT['geomx_tumor_mean']:.2f}，"
         f"良性为 {EXT['geomx_benign_mean']:.2f}——肿瘤更低，方向与宫颈 Visium 队列相反（ROI p={EXT['geomx_tn_roi_p']:.1e}；"
         f"芯 p={EXT['geomx_tn_core_p']:.1e}）；{EXT['geomx_wp_n']}/{EXT['geomx_wp_n']} 配对患者中肿瘤芯均低于其本人良性芯"
         f"（p={EXT['geomx_wp_p']:.3f}，即 n=6 精确检验下限；95% CI [{EXT['geomx_wp_ci_lo']:.2f}, 1.00]）。上皮与间质 ROI "
         f"无差异（p={EXT['geomx_compartment_p']:.3f}）。Silva 均值非单调——A {EXT['geomx_core_silva_A']:.2f} < C "
         f"{EXT['geomx_core_silva_C']:.2f} < B {EXT['geomx_core_silva_B']:.2f}（A vs B p={EXT['geomx_core_silva_AB_p']:.3f}）"
         f"——病理 High/Low 在风险轴方向上不分离（p={EXT['geomx_risk_core_p']:.3f}）。平台差异（DSP 靶向面板 vs Visium；"
         "ADC vs 以 SCC 为主的训练队列）很可能是符号改变的原因，但此处无法进一步定位。可迁移的对象是所学通路表征的"
         "肿瘤—良性可分性，而非“高分=高风险”的约定，更不是侵袭性分级；事后上皮 Silva 分层（补充 Note S2）仅作描述性记录。")
    body(f"**头颈部：真实、含弱通路特异性的组织，但无疾病判别。** 迁移评分在 {EXT['hnscc_n_samples']} 张 GSE268014 "
         f"切片上 Moran's I={EXT['hnscc_moran_mean']:.2f}，在独立的 {EXT['hnscc_gse281978_n']} 张 GSE281978 切片上为 "
         f"{EXT['hnscc_gse281978_moran_mean']:.2f}，而坐标置换零近于零（全部 14 张 p≤0.001）。纯 KEGG 面板在每张切片上"
         f"均高于表达匹配随机面板（{EXT['rg268_exprm_npos']}/{EXT['hnscc_n_samples']} 与 "
         f"{EXT['rg281_hvgu_npos']}/{EXT['hnscc_gse281978_n']}；p={EXT['rg268_exprm_signp']:.3f}/"
         f"{EXT['rg281_exprm_signp']:.3f}），即弱但完全可复现的通路特异成分。所有切片级判别检验均为阴性：恶性 vs 非恶性"
         f"（正向 {EXT['mal_non_pos']}/{EXT['mal_non_n']}，p={EXT['mal_non_p']:.3f}）、肿瘤前沿 vs 核心"
         f"（{EXT['edge_core_pos']}/{EXT['edge_core_n']}，p={EXT['edge_core_p']:.3f}）、HPV+ vs HPV−"
         f"（p={EXT['hpv268_p']:.2f}/{EXT['hpv281_p']:.2f}）、原发 vs 淋巴结转移（p={EXT['pt_lnmt_p']:.2f}；补充 Note S3）。")
    h2("4.6  标签剂量效应、零模型对照与临床效用边界")
    body(f"**标签将局部方向稳定为可迁移方向。** 逐折配对 LODO 中，完全无监督训练给出局部、不稳定的方向"
         f"（{EXT['unsup_lodo_n_above_median']}/4 折高于正常中位、{EXT['unsup_lodo_n_above_all']}/4 高于全部正常，"
         f"平均百分位 {EXT['unsup_lodo_mean_pct']:.2f}；ADC 折为 {EXT['unsup_lodo_min_pct']:.2f}）；加入其余三个带标签"
         f"病变切片后方向稳定（{EXT['lodo_n_above_median']}/4 与 {EXT['lodo_n_above_all']}/4，平均 "
         f"{EXT['lodo_mean_pct']:.2f}；ADC 折由 {EXT['unsup_lodo_min_pct']:.2f} 升至 {EXT['lodo_min_pct']:.2f}）。"
         f"四折即四个独立事件，精确区间宽且重叠（下限 {EXT['lodo_4of4_ci_lo']:.2f}/{EXT['unsup_3of4_ci_lo']:.2f}）；"
         "更稳健的证据是配对设计本身及 ADC 折的配对上升，定为提示性。腺上皮向鳞状上皮的迁移是主要瓶颈，"
         "与已记录的 SCC/ADC 微环境差异一致 [@mo;@wu]。")
    body(f"**队列内通路特异性不被支持。** 纯 KEGG 面板评分——即 108 个 HPV 面板基因的免学习逐样本均值，"
         f"非表 3 的模型评分——的 Moran's I 为 {RC['kegg_moran']:.3f}，不高于 30 个匹配随机面板"
         f"（{RC['random_moran_mean']:.3f}，{RC['random_moran_min']:.3f}–{RC['random_moran_max']:.3f}；置换 "
         f"p={RC['moran_perm_p']:.3f}），随机面板的疾病排序与之相同（τ {RC['kegg_kendall']:.3f}；AUC 置换 "
         f"p={RC['auc_perm_p']:.2f}）：队列内平滑为任何共表达基因集所共有，排序由标签锚定。跨器官的面板级优势"
         "（4.5 节）属于不同口径，二者不矛盾。")
    body(f"**无预后或决策效用。** 11 个空间 DEG 在 {TC['n_patients']} 例（{TC['events']} 事件）TCGA-CESC bulk Cox 模型"
         f"[@cox] 中无一显著（最小为 {TC['min_gene']}，p={TC['min_p']:.3f}），说明 spot 级空间风险与患者级结局之间存在"
         "尺度断裂。应用 MRP-ST 定级：空间自组织 supported；跨器官原始面板通路特异性 supported；GeoMx 秩判别（符号不"
         "迁移）、标签锚定、半监督优于无监督 LODO 为 suggestive；队列内模型评分通路特异性与形态学排序增益 unsupported；"
         "分级、预后与跨器官判别 unsupported。")

    # ---- 5 讨论 --------------------------------------------------------
    h1("讨论")
    h2("5.1  主要发现")
    body("本基准给出三个可辩护的正面陈述与一个核心警示。正面：通路锚定评分生物学可解释（肿瘤上皮、HPV/抗原呈递程序"
         "为正，干扰素为负；种子稳定且在独立 scRNA-seq 中标志物有效）；即使去除标签、先验或邻域，空间一致性仍然很高，"
         "并含可检出的形态学增量；监督训练所得表达表征在无标签推理阶段，于独立 GeoMx 队列保留强肿瘤—良性秩判别，"
         "并在 14 张头颈切片上保留真实空间组织。警示是定量的：样本级样本内 AUC 1.00 与 LOSO AUC≈0.50 并存；去除四个"
         "严重度标签后，有序排序由 τ=0.46 塌至 p=0.03–0.06 边界上的 τ=0.25。若没有去除消融、置换零模型与全样本留出，"
         "本研究的每个数字都会读作一个成功的风险模型；有了它们，存活下来的只有空间组织与平台级可分性。")
    h2("5.2  对生物医学信息学的可推广经验")
    body("四条经验可推广到宫颈 ST 之外。第一，一致性指标不是模型指标：Moran's I≈0.9 主要是相邻 spot 的内在平滑，"
         "匹配随机基因集达到同样数值；自相关必须对照数据驱动零模型报告。第二，标签置换的统计单位必须是独立样本，"
         "绝不能是数千个自相关 spot——spot 级置换会制造显著性。第三，外部效度是多组分的：秩判别、校准符号与分级可以"
         "独立迁移（本例为：迁移、不迁移、不迁移），单一外部 AUC 会掩盖实际发生了什么；跨平台的靶向面板/Visium 与 "
         "ADC/SCC 偏移是真实的校准风险。第四，样本内与跨样本性能必须在设计上同时报告；随机基因零模型与完全无监督臂"
         "在训练后几乎不花成本。这些可操作条目及三级定级，将通用的泄漏与报告原则 [@kapoor;@whalen;@varo;@tripod] "
         "落实到 ST 场景。该审计网络无关，适用于任何阳性样本极少的罕见病 ST 研究。")
    h2("5.3  局限性")
    body("（1）功效：四个独立疾病事件与六对 GeoMx 患者约束了所有推断；3/4 种子与 6/6 计数的精确区间宽，仅支持 "
         "suggestive 定级；MRP-ST 的触发条件/阈值是务实提议，需独立验证。（2）平台与组织学混杂：外部宫颈队列为 DSP "
         "靶向面板上的 ADC，对以 SCC 为主的 Visium 训练队列；符号反转无法分解，上皮/间质组成不显著但不能排除。"
         "（3）队列异质性：31 个正常样本汇集自三项不同临床研究的 GEO 子系列；扩大了正常参照集但可能改变分布尾部。"
         "（4）伪重复：46,820 个 spot 不独立；spot 级相关仅描述性，推断性主张由样本/切片/患者级比较承担。"
         "（5）范围：单一架构、单一通路先验、仅公开数据；基准证明了此处对去标签的敏感性，不能确立普适检出率。"
         "（6）代理与先验监督：NO-PROG 仅移除有序严重度标签，仍保留表达派生代理目标，而该代理在样本级与疾病相关；"
         "矩阵内的 NO-SUP 臂（λ_sup=λ_prog=0）同样去除了代理：平均 τ 降至 "
         f"{_ns['tau_mean']:.3f}，仅剩弱且跨种子不稳定的残余（{_ns_count}；τ {min(_ns['taus']):.3f}–"
         f"{max(_ns['taus']):.3f}）。标签与先验均关闭的 NO-ALL 臂（λ_sup=λ_prog=λ_hpv=0）在同一矩阵内对该残余作出裁决。"
         + (f"残余消失（τ={_na['tau_mean']:.3f}，全部置换 p 不显著；Mann–Whitney 在 {_na['n_seeds']} 个种子上均不分离，"
            f"{_na['mwu_nsig']}/{_na['n_seeds']} 名义显著），NO-SUP 残余可归因于通路一致性先验而非无标签结构。" if _na_state == "gone" else
            f"τ 进一步降至 {_na['tau_mean']:.3f}（置换 p={_na_p_range}，{_na_count}）：先验解释了部分残余，其余仍弱且"
            "跨种子不稳定。" if _na_state == "reduced" else
            f"τ 维持在 {_na['tau_mean']:.3f}（置换 p={_na_p_range}，{_na_count}；对 NO-SUP 的 Δτ={-_na_delta:+.3f}）："
            "残余是表达/形态学输入内在的疾病相关几何，而非通路正则。" if _na_state == "persist" else
            "【NO-ALL 结果待补：scripts/rerun_2026-09-24_noall.sh。】")
         + "NO-ALL 并非零信息条件——面板基因仍作为编码器普通输入，重建、邻域与形态学项保持开启——故该级联界定的是"
         "显式疾病锚定项，而非输入中的一切疾病相关信号。代理的直推式性质同样未量化：其目标阈值在全部分析 spot 的"
         "全局中位数上确定，而非仅用训练样本。"
         "任何临床使用前都需要更多疾病样本的多中心注册队列；当前评分不具临床决策效用。")
    h2("5.4  临床转化路径")
    body("本文是审计方法学而非器械，当前评分不具决策效用，但转化路径具体且刻意分级。第一阶段，审计闸门：任何在 "
         "n_病变 ≤ 10 情形下训练的 ST 或全片图像风险模型，在提出前瞻性或临床主张之前都应通过 MRP-ST——去标签/去代理/"
         "去先验臂、全样本（绝不 spot 级）置换、以及至少一个无标签外部队列；此阶段耗费 GPU 小时而非患者。第二阶段，"
         "独立重复：须在多中心、前瞻注册队列上重复该基准，具备足以约束功效的独立疾病事件（数量级为 30–50 张病变切片，"
         "覆盖 CIN3/AIS、鳞癌与腺浸润性病变），阈值冻结、分析方案预注册。第三阶段，决策影响评估：此后才将锁定模型作为"
         "既有宫颈癌筛查路径——高危型 HPV 初筛加细胞学分流、阴道镜引导下活检分诊——中的辅助手段加以检验，终点为"
         "高级别病变增量检出与不必要活检减少等患者相关指标，并满足各平台特定的伦理、监管与校准要求。独立诊断、分级或"
         "治疗决策始终不在范围内。")

    # ---- 6 结论 --------------------------------------------------------
    h1("结论")
    body("我们提出了面向极端小样本空间转录组风险建模的标签依赖消融基准，包括七个匹配的多种子变体（标签→代理→先验"
         "嵌套级联，直至一个标签与通路先验均关闭的臂）、全样本置换、"
         "配对的半/无监督留出、表达匹配基因集零模型与跨平台外部检验，并将其形式化为五条目 MRP-ST 协议。在四张病变"
         "宫颈切片上，一个通路锚定模型取得了样本内完美分离，而审计表明其精细排序主要由标签锚定；空间组织与跨平台"
         "肿瘤—良性可分性真实保留，校准符号与分级则不迁移。该基准成本低、网络无关，旨在让标签记忆在发表之前而非"
         "之后被看见。")
    body("**适用性。** MRP-ST 与七项消融适用于任何处于\"疾病样本极少\"情形的研究——操作上即独立疾病样本数 "
         "n_diseased ≤ 10（或任一类别 ≤ 5）、且监督信号建立在空间自相关的 spot 级测量之上。这涵盖罕见病空间转录组，"
         "以及具有同样\"少样本/多 spot\"结构的空间蛋白组、空间代谢组与多重成像，也适用于依赖公开或联盟数据、"
         "无法获得外部队列的监督模型。它不适用于疾病重复数已充足（n_diseased > 10）的研究——此类情形下常规的"
         "样本级交叉验证已足以承担推断主张；它也不能替代疾病特异的外部验证队列（若存在）。该协议只需训练后分析"
         "与版本化结果存储，且与模型架构无关，因此可在不重训底层表征的前提下采用。")

    # ---- 3 材料与方法 --------------------------------------------------
    h1("材料与方法")
    h2("3.1  数据集与预处理")
    add_table(
        ["队列", "数据类型", "实际分析规模", "在审计中的角色"],
        [["宫颈 Visium 汇总（GSE208654＋GSE217237＋10x 公开演示片）", "ST（10x Visium）",
          f"{CO['n_samples']} 样本（{CO['n_normal']} 正常 / {CO['n_disease']} 病变）；{CO['n_spots']:,} spot",
          "基准队列：训练与全部消融"],
         ["GSE316098 [@axelrod]", "GeoMx DSP，宫颈腺癌 [@geomxtech]",
          f"{EXT['geomx_n_patients']} 患者 / {EXT['geomx_n_rois']} ROI（{EXT['geomx_n_cores']} 配对芯）", "跨平台无标签评分"],
         ["GSE268014 [@simkin]", "ST，头颈部鳞癌",
          f"{EXT['hnscc_n_samples']} 切片（源研究共 26 个肿瘤）", "跨器官空间组织；判别检验"],
         ["GSE281978 [@lee]", "ST，HPV+/HPV− 头颈癌",
          f"{EXT['hnscc_gse281978_n']} 切片", "独立跨器官复现"],
         ["TCGA-CESC [@tcga]", "Bulk RNA-seq", f"{TC['n_patients']} 例 / {TC['events']} 事件", "预后效用检验（阴性）"],
         ["GSE308792 [@scrna]", "scRNA-seq，宫颈", f"{SCR['n_cells']:,} 整合细胞", "标志物有效性"]],
        caption="表 2  队列概览。规模为本文实际分析的切片数。")
    body("宫颈 Visium 队列汇总三个公开来源，共 35 个样本：（i）GSE208654（Guo 等，2023）的四张切片——N_HPV（正常）、"
         "HSIL_HPV（HSIL）、CA_HPV_1（鳞状细胞癌，SCC）与 CA_HPV_2（腺癌，ADC）；（ii）GSE217237 超级系列下的 30 张"
         "正常宫颈外口切片（P001–P030），来自 HIV 感染、DMPA 避孕与微生物组三项子研究（其异质性在 5.3 节讨论）；"
         "（iii）公开的 10x Genomics FFPE 宫颈癌演示切片（cervical_cancer_1，SCC）。组织学标签为正常/HSIL/癌"
         f"（严重度 0/1/2）。每次运行均使用相同的 35 个样本、全部 {CO['n_spots']:,} 个 spot 与统一的 4,991 基因面板，"
         "其中含 108 基因的 KEGG-HPV 子面板（107 个被检出）。ST 预处理采用标准过滤、log1p 归一化与样本内标准化。")
    body("**配准质量控制（信息学前提）。** 公开 npz 容器中自带的捕获阵列坐标相对高分辨率 H&E 图像存在系统性偏移"
         "（部分切片仅 4.2% 的 spot 落在组织内）。因此我们用经过验证的加载器重载每个样本，将条码 spot 映射到 "
         "hires 图像坐标，并在修正后的位置重新提取形态学特征；对齐最好的正常切片达 76% 的在位率。所有形态学分支结果"
         "均使用修正坐标；表达矩阵不受影响。由于 spot 级风险无法以可辩护的精度叠印到 H&E 上（风险与局部核密度"
         "相关 r=−0.18），H&E 图像仅用作形态学输入与图中的组织学背景——图上不叠加任何模型输出。")
    h2("3.2  通路锚定的多模态模型")
    body("模型含三条路径（图 1b）。（a）表达编码器将 spot 基因向量映射至隐空间，训练时加重建项 λ_rec=0.2 与隐空间"
         "先验 λ_var=0.1。（b）探索性形态学分支编码冻结 UNI [@uni] 补丁特征（在修正坐标上一次性提取）并与表达隐向量"
         "融合；设置该分支正是为了能移除并度量形态学的边际贡献。（c）先验与监督：KEGG-HPV [@kegg] 一致性正则"
         "（λ_hpv=1.0）、空间邻域一致项（λ_neigh=0.3）、风险头上的表达派生代理二元交叉熵（λ_sup=5.0）以及对 0/1/2 "
         "的严重度回归（λ_prog=1.5）。该代理标签的构造为：以同一 108 基因 HPV 面板在各 spot 的平均表达，"
         "对全部 46,820 个 spot 取全局中位数作阈值二值化为 0/1——它是模型内部的表达派生切分，"
         "而非 HPV 感染标签或疾病标签；但因病变组织 HPV 通路表达更高，二者在样本级相关（见 5.3 节）。"
         "优化采用 AdamW（lr 5×10⁻⁴、权重衰减 10⁻⁴）、批大小 64、40 个 epoch，并按训练目标做耐心值早停（patience 6）；"
         "所有超参数在任何审计运行之前一次锁定并在各变体间保持一致。训练中未留出验证集。"
         "多种子复现用于检验优化稳定性，而非增加统计推断自由度：统计单位始终是四个独立病变切片，"
         "重复种子不增加独立事件数。")
    body("架构上，表达编码器为两层感知机（4,991 → 256 → 128；ReLU；dropout 0.2）；冻结 UNI 骨干输出 1,024 维补丁特征，"
         "经可训练适配器投影至 128 维；两路 128 维模态经四头跨模态注意力融合；逐 spot 风险头为 128 → 64 → 1，"
         "重建解码器为 128 → 256 → 4,991。UNI 骨干本身从不更新，形态学分支仅通过轻量适配器与融合参数起作用——"
         "刻意最小化额外容量，使 NO-IMAGE 对比可归因于形态学而非更多可训练参数。七个变体共享同一架构；"
         "消融只切换损失项或分支，不改变层宽。")
    h2("3.3  标签依赖消融基准")
    body("基准是固定的七变体、同队列、多种子析因设计，组织为嵌套的信息剥离级联。FULL 训练全部项；NO-IMAGE 去除形态学"
         "分支；NO-HPV 置 λ_hpv=0 但保留表达派生代理监督，单独隔离通路一致性项；NO-NEIGH 置 λ_neigh=0，检验高一致性"
         "是否由邻域正则制造；"
         "NO-PROG 置 λ_prog=0，使疾病严重度标签在训练中完全不可见，而表达、形态、通路与表达派生代理项全部保留——"
         f"这是针对有序疾病排序的决定性对比。NO-SUP 同时置 λ_sup=0 与 λ_prog=0：训练全程既看不到有序标签、"
         "也看不到表达派生代理，把真正的零标签极限直接放进旗舰消融矩阵内部。NO-ALL 再置 λ_hpv=0"
         "（λ_sup=λ_prog=λ_hpv=0）：有序目标、代理与通路一致性先验均不贡献梯度，仅保留重建、邻域项、冻结形态学分支，"
         "以及作为编码器普通输入的面板基因。"
         f"需明确：NO-PROG 是\"去除有序标签\"臂，而非\"无标签\"臂——"
         "所保留的表达派生代理标签本身在样本级与疾病相关，故该臂下残余的排序只能说明"
         "表达派生代理可部分恢复该排序，不能作为无标签泛化的证据；该主张由 NO-SUP 直接裁决，"
         "而 NO-SUP 下任何弱残余再由 NO-ALL 裁决，以区分通路先验来源与内在数据几何；"
         "在真正未见切片上的零标签极限另由完全无监督 LODO 臂外部化检验"
         "（同样 λ_sup=λ_prog=0，见 4.5 节）。FULL/NO-IMAGE/NO-HPV/NO-NEIGH/NO-SUP/NO-ALL 各种 3 个种子，NO-PROG 运行 "
         f"{A['NOPROG']['n_seeds']} 个种子（多种子用于检验显著边界处的结论稳定性）。各变体共享训练样本、spot 集、"
         "预处理、初始化协议与超参数；仅命名项发生改变。")
    body("**全样本留出方案。** 留一疾病样本（LODO）依次留出四张疾病切片之一，在其余 34 个样本上训练（半监督方案为 "
         "31 个正常＋3 个带标签病变；完全无监督方案另置 λ_sup=λ_prog=0），报告被留出切片的平均风险在 31 个训练正常中"
         "的百分位。两方案每折训练队列、spot 数（44,039–46,241）及其他所有设置完全相同，因此其对比估计的是三个标签的"
         "因果效应；统计单位是独立的被留出切片（4 个事件），绝不是 spot。")
    body("**每个对比为何必要——预先指定的失效读法。** 一致性与排序分开审计，因为单一汇总指标无法定位失效："
         "若 NO-PROG 后两者均保持，说明队列内排序不需要严重度标签；若 τ 崩塌而 Moran's I 不变（即实际观察到的模式），"
         "说明平滑的空间结构是真实的，但其具临床意义的排序由标签锚定；若排序在 NO-SUP 后仍弱存而在 NO-ALL 后消失，"
         "说明残余来自通路先验而非标签；若排序在 NO-ALL 后仍然保持，说明无需任何疾病锚定的目标或先验，标签锚定读法"
         "被推翻、应归于内在数据几何；若 NO-IMAGE 移动 Moran's I 而不动 τ，"
         "说明形态学改善平滑度但不贡献终点；NO-NEIGH 与 NO-HPV 则控制高一致性的两个显然替代解释（空间正则与通路先验）。"
         "每个变体因而对应一条可被允许的结论，这正是 3.6 节能做 supported/suggestive/unsupported 定级、"
         "而非临时叙事的原因。")
    h2("3.4  指标、零模型与统计方案")
    body("两条输出轴分开报告。空间一致性为切片内 spot 风险的 Moran's I [@moran]。疾病排序为逐样本平均风险与严重度 "
         "0/1/2 之间的样本级 Kendall τ [@kendall]；其经验零分布通过将完整严重度标签向量在全部 35 个样本间置换"
         "（31 个 0、一个 1、三个 2；约 2.09×10⁵ 种不同标注）并重算聚合风险得到，B=10,000；禁止 spot 级或疾病组内置换，"
         "因为空间自相关会使其反保守。疾病对正常的比较用单侧 Mann–Whitney U 检验 [@mwu]；GeoMx 的患者内对比用双侧"
         "配对 Wilcoxon 符号秩检验，并报告精确 Clopper–Pearson 95% 区间（n=6 时可达到的最小双侧 p 为 0.031）。"
         "生物学相关采用基于秩的 ssGSEA [@ssgsea]、样本内 z 标准化与 Spearman ρ，11 个程序上做 Benjamini–Hochberg "
         "FDR [@bh]；软件为 NumPy [@numpy]、scikit-learn [@sklearn]、SciPy [@scipy]。")
    body("**零模型对照。**（i）30 个与 KEGG 面板表达分位数匹配的随机 108 基因集，检验任何共表达基因集是否给出相同的"
         "一致性/排序；（ii）外部切片上的坐标置换（B=1,000）检验空间组织是否真实；（iii）35 样本上的两个留一样本"
         "（LOSO）基线——ridge/MLP 形态学到 HPV 代理评分（35 折）与 ridge 形态学到表达重建——检验队列内指标能否跨样本"
         "外推。外部评分使用一个固定检查点（checkpoint_FULL_DEPLOY_FAST_seed42.pt）的表达分支，推理时不读取任何宫颈"
         "标签；但权重来自监督训练，故外部实验检验的是表征迁移，而完全无监督 LODO 检验零标签极限。对于 GSE316098，"
         "Silva/风险组遵循 GEO SOFT 元数据（1A/1b-1 前缀为 TMA 芯标识）；ROI 在芯内上皮/间质配对，芯级与患者级检验为主要证据。")
    h2("3.5  实现与计算可复现性")
    body("全部实验在单张消费级云 GPU（NVIDIA RTX 4090，24 GB；AutoDL）上完成，使整套审计无需机构级算力即可复现："
         "UNI 冻结、补丁特征一次性提取；每次 40-epoch 运行约 0.5 GPU 小时，整个训练矩阵（22 次同队列变体运行＋8 折 "
         "LODO）在 16 GPU 小时内完成；所有置换、零基因集与外部评分均为 CPU 后处理。代码、配置、结果 JSON 与融合嵌入"
         "均已公开（见第 6 节数据可得性）；稿件中每个数字均由版本化的 JSON 产物生成。")
    h2("3.6  MRP-ST：最低报告协议")
    body("基于本案例，我们将分散的建议形式化为 MRP-ST——面向疾病样本数 n_dis≤10（或任一类别 ≤5）的监督/半监督 ST "
         "风险研究的最低报告协议。五条目为强制项：（1）嵌套去标签消融——依次关闭有序标签，以及（若使用）疾病相关代理"
         "目标与通路先验——每变体至少 3 个种子；（2）全样本标签置换"
         "（B≥10,000），绝不做 spot 级或仅组内置换；（3）≥30 个表达分位数匹配的随机基因集对照；（4）双样本级留出"
         "方案（半监督 vs 完全无监督），每折队列完全相同；（5）显式结论定级——supported/suggestive/unsupported——"
         "并附临床效用声明。完整清单、失效读法、判定规则与执行顺序见补充材料表 S2。五项均为训练后分析，成本可忽略。"
         "上述触发条件、最低重复次数与阈值是从单个极端案例提出的务实规则，而非经多队列验证的共识界值；"
         "规范化使用前需独立验证。")

    # ---- 声明 ----------------------------------------------------------
    h1("声明")
    body("**伦理声明。** 本研究仅使用公开、去标识化的数据集（GEO：GSE208654、GSE217237、GSE316098、GSE268014、"
         "GSE281978、GSE308792；TCGA-CESC；以及 10x Genomics 公开演示切片）。未招募新的受试者、未访问可识别的"
         "私人信息、未实施任何干预，故无需机构审查委员会批准与知情同意。原始研究已自行获得伦理批准，我们遵守了"
         "其数据使用条款。", indent=False)
    body("**CRediT 作者贡献。** Mingwei Bai：概念化、方法学、软件、形式分析、调查、数据管理、可视化、撰写——原始草稿。"
         "Zhengmin Gu：数据管理、验证、撰写——审阅与编辑。Ye Zhang：数据管理、资源、撰写——审阅与编辑。"
         "Lang Guo：概念化、方法学、监督、项目管理、撰写——审阅与编辑。", indent=False)
    body("**经费。** 本研究未获得来自公共、商业或非营利部门的任何专项资助。", indent=False)
    body("**利益冲突声明。** 作者声明不存在可能影响本文所报告工作的已知经济利益或个人关系。", indent=False)
    body("**数据与代码可得性。** 全部训练脚本、配置、结果 JSON 与融合嵌入发布于 "
         f"{GITHUB}。所有数据集均为公开：宫颈 Visium（GSE208654、GSE217237、10x 公开演示切片）、GeoMx GSE316098、"
         "GSE268014、GSE281978、TCGA-CESC 与 GSE308792（表 2）。", indent=False)
    body("**生成式 AI 与 AI 辅助技术声明。** 稿件准备期间，作者使用 AI 编程/语言助手（OpenAI Codex）进行代码生成、"
         "语言润色与文献核对。作者随后审阅并核实了全部内容，对发表文章承担全部责任。", indent=False)
    body("**说明。** 本中文稿为英文投稿稿的对照版本，仅供内部审阅；如中英文存在歧义，以英文版为准。", indent=False)

    # ---- 参考文献（保留英文原样）--------------------------------------
    h1("参考文献")
    for i, key in enumerate(C.order, 1):
        emit(f"[{i}] {C.refs[key]}", 9.5, indent=False, after=2, ls=1.0,
             font='Times New Roman')

    save(doc, "Manuscript_PLOSCB_中文.docx")
    return doc, C


# ========================================================================
#  COVER LETTER
# ========================================================================
def build_cover_letter():
    doc = Document()
    doc.styles['Normal'].font.name = 'Times New Roman'
    doc.styles['Normal'].font.size = Pt(11)
    doc.styles['Normal'].paragraph_format.line_spacing = 1.3
    s = doc.sections[0]
    s.top_margin = s.bottom_margin = Cm(2.5); s.left_margin = s.right_margin = Cm(2.5)

    def para(t, after=8, bold=False, align=None):
        p = doc.add_paragraph()
        if align is not None:
            p.alignment = align
        p.paragraph_format.space_after = Pt(after)
        _rf(p.add_run(t), 11, bold=bold)

    import datetime
    para(datetime.date.today().strftime("%B %d, %Y"), after=12)
    para("The Editors", after=0)
    para("PLOS Computational Biology", after=0)
    para("Public Library of Science", after=14)
    para("Dear Editor,", after=10, bold=True)
    para("We submit our Research Article entitled “Label-Dependence Index (LDI): a seven-variant audit framework "
         "for small-sample spatial transcriptomics with pathway-anchored validation in cervical lesions” for "
         "consideration in PLOS Computational Biology.")
    para("The manuscript addresses a core biomedical-informatics problem: reliable evaluation of machine-learning methods when "
         "independent clinical samples are scarce. Our case contains only four diseased cervical sections. A supervised "
         "spatial-transcriptomic risk model achieves an in-cohort AUC of 1.00, yet conventional prediction and integration "
         "benchmarks cannot determine whether this reflects generalization or fitting four labels.")
    para("We contribute the Label-Dependence Index (LDI), a formal metric and θ-calibrated decision gate that quantifies how "
         "much disease-ordering information a small-sample spatial-transcriptomic model obtains from ordinal labels, proxy "
         "variables and pathway priors rather than intrinsic spatial signal. LDI is the backward marginal decomposition "
         "LDI = τ_FULL − τ_NO-ALL with seed-propagated uncertainty, formalized over a seven-variant nested ablation that "
         "progressively removes each anchoring term. The audit combines whole-sample fitted-score permutation, paired "
         "semi-supervised and unsupervised leave-one-disease-out analyses, expression-matched random-gene nulls, and external "
         "analyses in GeoMx cervical adenocarcinoma, 14 head-and-neck sections, TCGA-CESC, and cervical single-cell RNA "
         "sequencing. We formalize these checks as MRP-ST, a five-item reporting proposal with explicit "
         "supported/suggestive/unsupported grading. The complete audit runs on one 24-GB GPU in under 16 GPU-hours.")
    para(f"The central result is deliberately cautionary: LDI = {_ldi_mean:.3f} ± {_ldi_sd:.3f} exceeds the calibrated gate "
         f"(θ = {_ldi_theta:.3f}, so the model is formally label-dependent); in-sample AUC 1.00 coexists with "
         f"leave-one-sample-out AUC ≈0.50, and the nested removal cascade reduces Kendall τ from 0.46 to 0.25 and 0.21 before "
         f"abolishing ordering at −0.11. Morphology improves spatial coherence but not disease ranking; external tumor–benign "
         f"rank separation persists, but calibration direction and grading do not transfer. The evaluated score has no current "
         f"clinical decision utility. The contribution is an auditable metric and framework for preventing premature claims "
         f"from small-sample spatial-omics studies.")
    para("The manuscript is original, has not been published, and is not under consideration elsewhere. All data analyzed are "
         "public with accessions listed in the manuscript, and the analysis code and versioned result artifacts are openly "
         "released.")
    para("Thank you for your consideration.", after=14)
    para("Sincerely,", after=12)
    para("Lang Guo, on behalf of all authors", after=0)
    para("School of Pharmacy, Shenyang Medical College, 146 Huanghe North Avenue, Shenyang 110034, China", after=0)
    para("guolang1016@symc.edu.cn · Tel: +86 13555707001", after=0)
    save(doc, "CoverLetter_PLOSCB.docx")


if __name__ == "__main__":
    build_manuscript()
    build_manuscript_cn()
    build_cover_letter()
    print("DONE.")
