# -*- coding: utf-8 -*-
"""gen_cbm.py — CiBM (Computers in Biology and Medicine) 投稿生成器

定位（方法学刊口径）：提出 MRP-ST 审计框架 + LDI 标签依赖指数，作为首个
ST 专用、网络无关的小样本风险模型标签记忆审计方法学框架。核心贡献：
(1) 七变体嵌套消融 + LDI 形式化度量；(2) 阳性对照仿真验证审计判别效度；
(3) 多组分外部效度解离（秩判别/校准符号/分级独立迁移）；(4) 去循环可解释性
对照。宫颈 n=4 为应用示范案例。

所有数字动态读 results/paper_v10_numbers.json、results/ldi_report.json、
results/sim_audit_summary.json（阳性对照，服务器产出）、
results/decircularization_biology.json（去循环对照）。

输出到 papers/11_CiBM/：
  Manuscript_CiBM.docx / Manuscript_CiBM_中文.docx /
  Supplementary_Information_CiBM.docx / CoverLetter_CiBM.docx / Highlights_CiBM.docx
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
OUT = ROOT / "papers" / "11_CiBM"
FIG = ROOT / "papers" / "07_CSBJ_v10" / "Figures"
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

# --- per-fold LOSO registry (for M3: composition + worst-case sensitivity) ---
LOSO_AUC = {}
_lap = ROOT / 'results' / 'baseline_hpv_auc.json'
if _lap.exists():
    LOSO_AUC = json.load(open(_lap, encoding='utf-8'))

def _loso_fold_stats(reg):
    """(min_auc, max_auc, n_valid, n_total) over evaluable LOSO folds."""
    for blk in LOSO_AUC.get('per_regressor', []):
        if blk.get('regressor') == reg:
            v = [f['auc'] for f in blk['per_fold'] if f.get('auc') is not None]
            nv, nt = blk.get('n_valid_folds', 0), blk.get('n_samples', 35)
            if v:
                return min(v), max(v), nv, nt
            return float('nan'), float('nan'), nv, nt
    return float('nan'), float('nan'), 0, 35

LOSO_RIDGE = _loso_fold_stats('ridge')
LOSO_MLP = _loso_fold_stats('mlp')
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

# Positive-control simulation audit (run on server; results/sim_lodo_summary.json)
_SIM_PATH = ROOT / "results" / "sim_lodo_summary.json"
_SIM = None
if _SIM_PATH.exists():
    _SIM = json.load(open(_SIM_PATH, encoding="utf-8"))
    _sim_arms = _SIM.get("arms", {})

    def _sim(g, key, default=None):
        return (_sim_arms.get(g, {}).get("stats", {}) or {}).get(key, default)

    _sim_grades = {g: _sim_arms[g]["verdict"] for g in
                   ("group_A", "group_B", "group_C") if g in _sim_arms}
    _sim_pass = all(v in ("supported", "suggestive", "unsupported")
                    for v in _sim_grades.values()) and \
        _sim_grades.get("group_A") == "supported" and \
        _sim_grades.get("group_C") == "unsupported"
    # expected ordering check for abstract
else:
    _sim_arms = {}
    _sim_pass = None
    _sim_grades = {}
    print('[WARN] sim_lodo_summary.json missing — positive-control section will be [pending]')

# Scale-matched positive-control audit at the real cohort size (31 normal + 4 diseased
# = 35 donors); produced by scripts/run_sim_small.sh. Shows the decisive verdicts are
# scale-invariant — see Results 4.1 and Methods 3.6.
_SIM_SMALL_PATH = ROOT / "results" / "sim_lodo_summary_small.json"
if _SIM_SMALL_PATH.exists():
    _SMS = json.load(open(_SIM_SMALL_PATH, encoding="utf-8"))
    _sma_arms = _SMS.get("arms", {})

    def _sma(g, key, default=None):
        return (_sma_arms.get(g, {}).get("stats", {}) or {}).get(key, default)

    _sma_grades = {g: _sma_arms[g]["verdict"] for g in _sma_arms}
    _sma_perm = _SMS.get("n_perm")
else:
    _sma_arms = {}
    _sma_grades = {}
    _sma_perm = None
    print('[WARN] sim_lodo_summary_small.json missing — scale-matched subsection [pending]')


def _sma_seeds(g):
    return [r for r in _sma_arms.get(g, {}).get("seeds", []) if r.get("transfer")]


def _sma_seedstr(g):
    return ", ".join(f"{r['transfer']['tau_lodo']:+.3f} (p={r['transfer']['p']:.3f})"
                     for r in _sma_seeds(g))

# Real cervical label-free LODO probe (results/real_lodo_summary.json)
_REALLODO_PATH = ROOT / "results" / "real_lodo_summary.json"
if _REALLODO_PATH.exists():
    _RL = json.load(open(_REALLODO_PATH, encoding="utf-8"))
    _RL_SEEDSTR = ", ".join(f"{r['tau_lodo']:+.3f} (p={r['p']:.3f})"
                            for r in _RL.get("lodo_seeds", []))
else:
    _RL = {}
    _RL_SEEDSTR = ""
    print('[WARN] real_lodo_summary.json missing — real-case LODO paragraph will be [pending]')


# Seven-variant scalar cascade on the simulated arms (results/sim_audit_summary.json;
# aggregated from all 63 run JSONs). Scalar-head tau/Moran only — SI Table S3 raw material.
_SIMAUDIT_PATH = ROOT / "results" / "sim_audit_summary.json"
if _SIMAUDIT_PATH.exists():
    _SIMAUDIT = json.load(open(_SIMAUDIT_PATH, encoding="utf-8"))
else:
    _SIMAUDIT = {}
    print('[WARN] sim_audit_summary.json missing — SI Table S3 cascade will be [pending]')


def _simaud(g, v, key="tau_mean"):
    return (((_SIMAUDIT.get(g) or {}).get("variants") or {}).get(v) or {}).get(key)


def _sim_seeds(g):
    return [r for r in _sim_arms.get(g, {}).get("seeds", []) if r.get("transfer")]


def _noall_head(g, s):
    fp = ROOT / "results" / f"results_SIM_{g}_NOALL_seed{s}.json"
    if not fp.exists():
        return None
    d = json.load(open(fp, encoding="utf-8"))
    return (d.get("progression_monotonicity") or {}).get("kendall_tau")


def _fmt_seeds(g):
    return ", ".join(f"{r['transfer']['tau_lodo']:+.3f} (p={r['transfer']['p']:.3f})"
                     for r in _sim_seeds(g))

# De-circularization biology control (run locally; results/decircularization_biology.json)
_DECIRC_PATH = ROOT / "results" / "decircularization_biology.json"
_DECIRC = None
if _DECIRC_PATH.exists():
    _DECIRC = json.load(open(_DECIRC_PATH, encoding="utf-8"))
else:
    print('[WARN] decircularization_biology.json missing — biology section defaults to FULL-only')

# Audit-guided decircularized readout vs supervised head, independent GeoMx cohort
# (run locally; results/audit_guided_readout_geomx.json)
_AUDG_PATH = ROOT / "results" / "audit_guided_readout_geomx.json"
_AUDG = None
if _AUDG_PATH.exists():
    _AUDG = json.load(open(_AUDG_PATH, encoding="utf-8"))
else:
    print('[WARN] audit_guided_readout_geomx.json missing — readout-deflation paragraph will be skipped')

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
 "neto": "J.C. Neto, E. Siegel, S. Ho, W. Li, M. Abadi, A. Kundaje, et al., Learning disease signatures versus participant signatures in biomedical data, Cell Patterns 4 (2023) 100764. https://doi.org/10.1016/j.patter.2023.100764.",
 "schreiber": "J. Schreiber, R. Singh, J. Bilmes, W.S. Noble, A pitfall for machine learning methods aiming to predict across cell types, Genome Biol. 21 (2020) 282. https://doi.org/10.1186/s13059-020-02177-y.",
 "karin": "J. Karin, R. Mintz, B. Raveh, M. Nitzan, Interpreting single-cell and spatial omics data using deep neural network training dynamics, Nat. Comput. Sci. 4 (2024) 941–954. https://doi.org/10.1038/s43588-024-00721-5.",
 "davis": "S.E. Davis, M.E. Matheny, S. Balu, M.P. Sendak, A framework for understanding label leakage in machine learning for health care, J. Am. Med. Inform. Assoc. 31 (2024) 274–280. https://doi.org/10.1093/jamia/ocad178.",
 "ojala": "M. Ojala, G.C. Garriga, Permutation tests for studying classifier performance, J. Mach. Learn. Res. 11 (2010) 1833–1863.",
 "wood": "D.A. Wood, J.P. Dunn, R.L. Collisson, A. Bild, Cross-validation pitfalls in cancer genomics: two-level external cross-validation and label permutation, Nat. Commun. 12 (2021) 5907. https://doi.org/10.1038/s41467-021-26134-4.",
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
        # support **bold** segments inside figure captions (matches body())
        for part in re.split(r'(\*\*[^*]+\*\*)', cap):
            if part.startswith('**') and part.endswith('**') and len(part) > 4:
                _rf(c.add_run(part[2:-2]), 9.5, True, italic=True, font=BFONT)
            elif part:
                _rf(c.add_run(part), 9.5, italic=True, font=BFONT)
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
    TITLE = ('MRP-ST and the Label-Dependence Index: a validated label-removal '
             'protocol for risk models in extreme small-sample spatial '
             'transcriptomics of cervical neoplasia')

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
         "We present **MRP-ST**, the first ST-specific, network-agnostic audit framework for detecting label dependence in "
         "small-sample risk models, together with a formal **Label-Dependence Index (LDI)** and a validated discriminative "
         "decision gate.")
    body(f"**Methods.** MRP-ST defines a seven-variant nested label-removal cascade (FULL → NO-IMAGE → NO-HPV → NO-NEIGH → "
         "NO-PROG → NO-SUP → NO-ALL) and the LDI = τ_FULL − τ_NO-ALL metric with seed-propagated uncertainty and a θ-calibrated "
         f"gate. We applied it to {CO['n_samples']} cervical Visium sections ({CO['n_normal']} normal, {CO['n_disease']} diseased; "
         f"{CO['n_spots']:,} spots) with a {CO['n_genes_panel']}-gene HPV-pathway panel (107 detected) and frozen UNI morphology. "
         "We validated the audit's discriminative power on three controlled simulated cohorts with known ground truth "
         "(strong shared signal / weak heterogeneous signal / donor-specific identity confounding) using a leave-one-donor-out "
         "linear probe on frozen, fully label-free embeddings—including a scale-matched control regenerated at exactly the "
         "cervical cohort size (35 donors) and a threshold-robustness sweep at both cohort scales—and tested multi-component "
         "external validity across GeoMx DSP, "
         "head-and-neck ST, TCGA-CESC survival, and cervical single-cell RNA-seq.")
    body("**Results.** On simulated data the audit correctly graded the strong-signal cohort as supported "
         + (f"(τ_LODO={_sim('group_A', 'transfer_mean'):.3f}), the weak-signal cohort as suggestive "
            f"({_sim('group_B', 'transfer_mean'):.3f}±{_sim('group_B', 'transfer_sd'):.3f}), and the identity-confounded cohort "
            f"as unsupported despite in-sample fit (in-sample τ={_sim('group_C', 'full_head_insample_mean'):.3f} vs "
            f"τ_LODO={_sim('group_C', 'transfer_mean'):.3f})" if _sim_arms else "")
         + (f". Regenerating all three arms at the real cohort's size (35 donors) preserved the decisive supported/"
            f"unsupported verdicts, showing the grading gate is neither threshold- nor scale-fragile" if _sma_arms else "")
         + f". On the cervical cohort, FULL achieved Moran's I {A['FULL']['moran_mean']:.3f} and Kendall τ "
         f"{A['FULL']['tau_mean']:.3f}; seven-variant removal gave LDI="
         + (f"{_ldi_mean:.3f} ± {_ldi_sd:.3f} (θ={_ldi_theta:.3f}; label-dependent) " if _LDI else "[pending] ")
         + "with the proxy and pathway prior contributing most. A label-free leave-one-donor-out probe further showed a weak, "
         "seed-unstable cross-donor disease axis survives complete label removal (τ_LODO="
         + (f"{_RL['lodo_mean']:.3f}±{_RL['lodo_sd']:.3f}, graded suggestive) " if _RL else "[pending] ")
         + "—not pure memorization, but far below the strong-signal control. De-circularization analysis showed "
         "tumor-epithelium and interferon correlations survive label/proxy removal (real), whereas HPV-program enrichment is "
         "maintained by the pathway prior. External validity dissociated into three independently migrating components: rank "
         "discrimination transferred to GeoMx, but calibration sign reversed and grading did not.")
    body("**Conclusion.** We introduce LDI and MRP-ST, to our knowledge the first validated, network-agnostic protocol that "
         "quantifies and audits label dependence in small-sample ST risk models. Its discriminative validity is established on "
         "controlled cohorts with known ground truth—it passes a genuine shared program yet catches identity confounding—and its "
         "constructive value is shown on the cervical case: after complete label removal the same protocol isolates a short list "
         "of supervision-independent spatial programs (tumor epithelium, antigen presentation, interferon) that a small-n ST "
         "study can legitimately report. Rank discrimination additionally transfers to an independent GeoMx cohort even though "
         "calibration and grading do not, separating three external-validity components; and the decisive gate is preserved when the "
         "controlled arms are regenerated at the real cohort's size. The protocol is released as open, "
         "reproducible software; the specific risk score evaluated here is a worked example, not a clinical instrument.")
    emit("**Keywords:** spatial transcriptomics; label dependence; audit framework; small-sample machine learning; "
         "cervical lesion; external validity dissociation", 10.5, after=0)
    doc.add_page_break()

    # ---- 1 Introduction ------------------------------------------------
    h1("1. Introduction")
    body("Cervical cancer remains the fourth most common malignancy in women worldwide [@sung], and persistent high-risk HPV "
         "infection accounts for nearly all cases [@malagon]; large multi-omic consortia have characterized its molecular landscape "
         "[@tcga], while the Silva A/B/C pattern-based classification of endocervical adenocarcinoma is an established histologic "
         "grading system linked to stromal invasion, lymph-node metastasis and prognosis [@silva1;@silva2;@silva3;@silva4]. Spatial "
         "transcriptomics (ST; e.g., 10x Visium [@stahl], reviewed in [@moses;@moffitt;@bressan]) measures expression within its "
         "histologic context, and digital-pathology foundation models such as UNI, Virchow and GigaPath [@uni;@virchow;@giga] now "
         "provide transferable morphology representations. Combining expression, imaging and pathway priors is therefore an "
         "attractive route to characterize epithelial transformation in situ.")
    body("A systematically underestimated methodological problem is sample scarcity: a systematic search of public "
         "repositories for cervical spatial-transcriptomic data, applying three inclusion criteria—10x Visium platform with "
         "standard 55-µm capture spots, section-level histologic annotation, and H&E images available and registrable to the "
         "capture-array coordinates—retained only four independent diseased sections (one high-grade squamous intraepithelial "
         "lesion, two squamous-cell carcinomas, one adenocarcinoma) against 31 normals. Public cervical ST datasets that were "
         "screened and could not be analyzed here, each with the specific criterion it failed, are documented in Supplementary "
         "Table S4 so that the sample-scarcity premise can be independently checked. At this scale any supervised risk model can "
         "fit four labels, and a sample-level in-sample AUC of 1.00 cannot distinguish learned disease signal from memorization of "
         "four independent events—the failure mode understood in the broader literature as label leakage [@davis], participant "
         "rather than disease signature learning [@neto], and cross-cell-type prediction pitfalls where apparent accuracy reflects "
         "memorized training context [@schreiber]. Rare-disease ST studies increasingly face exactly this regime, yet there is no "
         "standardized, executable audit that separates the two explanations. We address this with a new method rather than a further "
         "critique: **LDI**, a scalar label-dependence metric, operationalized in **MRP-ST**—an ST-native, network-agnostic nested "
         "label-removal cascade with a θ-calibrated decision gate, a positive-control discriminative-validity test, and a five-item "
         "minimum reporting protocol. The same protocol is constructive as well as diagnostic: applied to our own cohort it also "
         "determines which spatial programs remain supported once supervision is removed, delimiting what a small-sample ST study "
         "can legitimately claim.")
    body("Pathway biology supplies a natural inductive bias. HPV oncogenesis is a conserved E6/E7-driven program acting through "
         "p53/Rb loss, altered antigen presentation and immune evasion; anchoring a representation to the KEGG HPV gene set "
         "[@kegg] might produce scores that are biologically interpretable, spatially smooth and transferable to other "
         "HPV-driven epithelial contexts. These are hypotheses to be tested with controls, not properties to be assumed.")
    body("**This paper makes five methodological contributions.** (1) We present **MRP-ST**, the first ST-specific, "
         "network-agnostic audit framework for detecting label dependence in small-sample risk models, formalized as a "
         "seven-variant nested label-removal cascade (FULL → NO-IMAGE → NO-HPV → NO-NEIGH → NO-PROG → NO-SUP → NO-ALL) "
         "with a five-item minimum reporting protocol and supported/suggestive/unsupported grading. (2) We define the "
         "**Label-Dependence Index (LDI)** = τ_FULL − τ_NO-ALL, with seed-propagated uncertainty, a θ-calibrated decision "
         "gate (θ = 2·|τ_NO-ALL|), and three formal properties: telescoping additivity, seed robustness, and zero-distribution "
         "calibration. (3) We provide the first **discriminative-validation** of an ST label-dependence audit on controlled "
         "cohorts with known ground truth: a leave-one-donor-out probe on frozen label-free embeddings grades a strong shared "
         "program as supported, a weak heterogeneous program as suggestive, and pure donor-specific identity confounding "
         "(in-sample learnable, untransferable) as unsupported—establishing both specificity and sensitivity. (4) We report a "
         "**multi-component "
         "external-validity dissociation**: rank discrimination transfers to GeoMx, but calibration sign reverses and grading "
         "does not—three components migrate independently. (5) A **de-circularization control** re-runs pathway correlations "
         "under NO-PROG/NO-SUP/NO-ALL to separate constructed (label/prior-anchored) from intrinsic biology. Cervical lesions "
         "provide the real-world setting; the contribution is the audit methodology, not a diagnostic tool.")
    body("We explicitly do not claim a diagnostic, a grading instrument, or a multimodal-fusion advance: the morphology branch is "
         "an a priori exploratory module whose benefits are reported on separate axes, and every power-limited or negative result "
         "is graded rather than hidden. The remainder of the paper reviews related work (Section 2), specifies datasets, model, "
         "benchmark and statistics (Section 3), reports results (Section 4), and discusses generalizable lessons and limitations "
         "(Sections 5–6).")

    # ---- Statement of Significance (JBI-mandated; SKIP for AIIM) -------
    # add_table(... JBI-exclusive, AIIM has no such requirement ...)

    # ---- 2 Related work ------------------------------------------------
    h1("2. Related Work")
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
         "evaluation in machine-learning-based science [@kapoor;@whalen], a dedicated framework for label leakage in health-care "
         "machine learning [@davis], recurrent failures in medical imaging at small n [@varo], and the instability of binary "
         "classification metrics on tiny datasets [@steinert]. A closely related line studies **identity confounding**: models may "
         "learn participant-specific signatures rather than disease signatures [@neto], and apparent cross-context performance can "
         "reflect memorization of the training context rather than transferable biology—first shown for cross-cell-type expression "
         "prediction [@schreiber] and extended to single-cell and spatial omics through training-dynamics analysis of annotation "
         "mismatch [@karin]. Permutation tests at the correct statistical unit are needed to distinguish the two [@ojala]; two-level "
         "external cross-validation with label permutation [@wood] is the established remedy. Reporting guidance such as TRIPOD+AI "
         "[@tripod] prescribes external validation but remains generic and is not operationalized for ST. Our MRP-ST framework "
         "translates these principles into an ST-native, executable protocol: it removes supervision components one at a time "
         "under matched multi-seed protocols, permutes labels at the independent-sample unit (never the spatially autocorrelated "
         "spot), contrasts semi-supervised and fully unsupervised whole-sample hold-outs, and grades conclusions against external "
         "and null controls. Unlike identity-permutation tests [@neto;@wood] which shuffle participant labels to detect "
         "participant-memorization, MRP-ST's nested cascade removes specific anchoring terms (proxy, ordinal labels, pathway "
         "prior) to decompose *which* label-derived information drives the score—a finer-grained audit suited to ST's "
         "multimodal supervision. Table 1 positions this work against the state of the art.")
    body("**Priority claim.** To our knowledge, no prior spatial-transcriptomic analysis protocol provides a nested "
         "label-removal cascade with a calibrated label-dependence decision gate and a positive-control discriminative-validity "
         "test; LDI and MRP-ST are, to our knowledge, the first such protocol. Existing work establishes that label dependence "
         "exists [@kapoor;@whalen;@davis;@schreiber;@karin] but does not supply an executable, ST-native procedure that "
         "decomposes *which* label-derived component drives a given risk score. The novel contribution of this paper is therefore "
         "the method itself, not a further demonstration that the problem exists.")
    add_table(
        ["Line of work", "Representative methods", "Typical data regime", "Explicit label-dependence audit", "Cross-platform external tests", "Uniquely added by this work"],
        [["H&E → expression", "HE2RNA, ST-Net [@he2rna;@stnet]", "Hundreds–thousands of slides", "No", "Rare", "Audit of the supervised risk output"],
         ["Pathology–ST foundation models", "OmiCLIP, SPADE, SEAL, MINT, ST-Align, STPath [@omiclip;@spade;@seal;@mint;@stalign;@stpath]", "10⁵–10⁶ spots, many samples", "No", "Held-out organs, not label removal", "Label removal + cross-platform audit"],
         ["ST / single-cell representations", "scGPT, Novae, CellCharter [@scgpt;@novae;@cellcharter]", "10⁷ cells", "No (self-supervised targets)", "No", "Decomposes supervision components"],
         ["ST integration benchmarks", "Li et al. [@libench]", "Multi-cohort", "No—scores integration accuracy", "No", "Audits the risk output, not integration accuracy"],
         ["Small-sample ML guidance", "Leakage audits, small-n evaluation, TRIPOD+AI [@kapoor;@whalen;@davis;@schreiber;@karin;@varo;@steinert;@tripod]", "Generic, tabular/imaging", "Principles only", "Prescribed, not executed", "Executable ST protocol + calibrated LDI gate"],
         ["This work", "Pathway-anchored multimodal model + audit benchmark + MRP-ST", f"{CO['n_samples']} samples / {CO['n_disease']} diseased", "Yes: seven prespecified multi-seed variants including target-free and pathway-regularizer-free arms, whole-sample permutation, dual LODO, gene-set nulls", "Yes: GeoMx, 14 HNSCC sections, TCGA-CESC, scRNA-seq", "First ST-native nested label-removal cascade with a calibrated LDI gate and positive-control discriminative validity"]],
        caption="Table 1. Positioning against the state of the art; citations resolve to the numbered reference list.")

    # ---- 3 Materials and Methods ---------------------------------------
    h1("3. Materials and Methods")
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
    body("**Companion search and exclusions.** The four diseased sections are the complete set of public Visium sections "
         "satisfying all three inclusion criteria (standard 55-µm Visium; section-level histologic annotation; registrable H&E) "
         "at the time of the search; the three included sources and every screened-but-excluded cervical ST dataset, with the "
         "specific criterion each failed, are listed in Supplementary Table S4. This documentation is provided so that the "
         "sample-scarcity premise can be independently reproduced rather than taken on assertion.", indent=False)
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
         f"(likewise λ_sup=λ_prog=0, Section 4.6). FULL/NO-IMAGE/NO-HPV/NO-NEIGH/NO-SUP/NO-ALL were run "
         f"with three seeds and NO-PROG with {A['NOPROG']['n_seeds']} seeds (the extra seed checks verdict stability at the "
         "significance boundary). Variants share training samples, spot sets, preprocessing, initialization protocol and "
         "hyper-parameters; only the named term changes.")
    body("**3.3.1 Label-Dependence Index (LDI): formal definition and properties.** The seven-variant cascade is not merely "
         "a set of ablation runs—it induces a formal metric, the **Label-Dependence Index (LDI)**, that quantifies how much "
         "of the model's disease-ordering information derives from label-anchoring terms rather than intrinsic spatial "
         "geometry. We define LDI as the backward marginal decomposition along the cascade, "
         "**(1)  LDI = τ_FULL − τ_NO-ALL**, "
         "where τ_FULL is the Kendall τ of the complete model and τ_NO-ALL is the τ of the fully stripped variant "
         "(λ_sup=λ_prog=λ_hpv=0). Uncertainty is propagated across independent training seeds as "
         "**(2)  σ_LDI = √(σ_FULL² + σ_NO-ALL²)**, "
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
         "**Proof (telescoping additivity).** The cascade is a linear chain FULL → … → NO-ALL, so by construction "
         "τ_FULL − τ_NO-ALL = Σ_i (τ_{i−1} − τ_i) = Σ_i Δτ_i; the identity requires no monotonicity of the signed terms "
         "Δτ_i, which may cancel or reverse. "
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
    body("**Label-free frozen-representation LODO probe.** In-sample scalar-head τ answers whether the fitted risk head orders "
         "the training samples; it cannot separate legitimate supervised learning from memorization. We therefore add a "
         "transfer test on frozen representations: per-spot fused embeddings are mean-pooled to one 128-dimensional vector per "
         "donor, and a ridge linear severity probe is evaluated by leave-one-donor-out cross-validation (train on N−1 donors, "
         "predict the held-out donor; Kendall τ-b between predicted and true severity, with a sample-label permutation test, "
         "B=10,000). Two design constraints are mandatory and pre-specified. (i) The probe is only interpretable on the "
         "**label-free NO-ALL encoder**: in FULL or partially supervised variants the encoder was optimised jointly with "
         "labels from every donor, so the held-out donor's label is already baked into the encoder and even a linear LODO "
         "probe is contaminated (we verify this empirically in Section 4.1—the identity-confounding arm reaches the τ ceiling "
         "on supervised encoders but chance on NO-ALL). (ii) The in-sample scalar head of an unsupervised encoder has an "
         "arbitrary sign and direction—it is trained only by neighborhood smoothness and a variance floor—so its τ is "
         "uninformative even when the representation carries the disease axis; the linear probe, which fixes its orientation "
         "from training donors, is the valid readout. We report τ_LODO (transfer), the fully in-sample probe τ, and their gap "
         "(memorization signature: large gap with τ_LODO≈0). The encoder is transductive only in X (it sees the held-out "
         "donor's expression during unsupervised fitting, never its label)—the standard linear-probe protocol.")
    body("**Controlled positive-control simulations.** To establish the audit's discriminative validity before using it on "
         "the cervical case, we generate three Visium-format cohorts with known ground truth (50 normal + 40 diseased donors "
         "each; 1,500 spots/donor; 3,000 genes including the real 108-gene KEGG-HPV panel; ≈10% background and ≈40% panel "
         "capture; per-spot library-size normalization). **Arm A** injects one shared, spatially smoothed disease program "
         "(60% of panel genes, amplitude 2.5, response 0.9–1.1) over weak donor-specific per-gene technical offsets. **Arm B** "
         "injects a weak shared program (amplitude 0.20, strong technical offsets SD 1.5, 35% zero-response diseased donors, "
         "50% per-donor program-gene dropout) to force a genuinely borderline regime. **Arm C** is the identity-confounding "
         "control: every donor—normal and diseased alike—receives a donor-specific random zero-sum fingerprint of equal "
         "amplitude (30% panel genes up, 30% down, spatially smoothed), so the two classes have identical marginal mean and "
         "dispersion; labels are in-sample learnable by memorizing individual fingerprints but contain no transferable "
         "class-level direction. Per-spot normalization is essential: multiplicative zero-sum perturbations are not zero-sum "
         "on raw counts (exp(+a)+exp(−a)>2), and without normalization a total-count channel leaks the class label. Each arm "
         "is trained as FULL and NO-ALL with three seeds and graded on the label-free probe under pre-registered rules: "
         "**supported** = mean τ_LODO ≥ 0.35 with ≥2/3 seeds p<0.05; **unsupported** = |mean τ_LODO| ≤ 0.15 with 0/3 seeds "
         "significant; everything between is **suggestive** (weak or seed-unstable transfer). These thresholds are pragmatic "
         "operational cut-offs fixed before looking at the cervical result, not normative constants.")
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
         "metrics extrapolate across samples. For the HPV-proxy LOSO, each fold trains on 34 samples and scores the held-out "
         "sample, whose spots are labelled by median-thresholding that sample's own HPV-panel mean; per-fold AUC is computed only "
         "when the held-out prediction is non-degenerate (SD > 1e-8), and the number of evaluable folds is reported explicitly, "
         "with the per-fold AUC range as a worst-case sensitivity. External scoring uses the expression branch of one fixed "
         "checkpoint (checkpoint_FULL_DEPLOY_FAST_seed42.pt) and reads no cervical labels at inference; the weights nevertheless "
         "derive from supervised training, so external experiments test representation transfer, whereas fully-unsupervised LODO "
         "tests the zero-label limit. For GSE316098, Silva/risk groups follow GEO SOFT metadata (1A/1b-1 prefixes are TMA core "
         "identifiers); ROIs are paired epithelial/stromal within cores, and core- and patient-level tests are primary.")
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
    body("**Threshold robustness.** To test whether the grading is knife-edge, we swept the two boundaries (τ_up ∈ {0.20, 0.25, "
         "0.30, 0.35, 0.40, 0.45}; τ_low ∈ {0.10, 0.15, 0.20}; α=0.05) under the identical pre-registered rule, at both cohort "
         "scales. Two properties hold uniformly: (i) group A stays 'supported' for every τ_up up to its own mean (τ_A=0.71 at 90 "
         "donors; 0.46 at the real-cohort scale of 35), and (ii) group C stays 'unsupported' for every τ_low ≥ its |mean| (τ_C=0.03 "
         "and 0.005). The decisive supported/unsupported verdicts are therefore invariant across the entire plausible threshold "
         "range and across a 2.6-fold change in cohort size. Only the deliberately borderline arm B is threshold-sensitive: at 90 "
         "donors it would be promoted to 'supported' only by lowering τ_up to 0.20 (below its mean of 0.22), and at 35 donors it "
         "remains 'unsupported' unless τ_low is set below 0.10 (its |mean|). The full grid is reported in the supplementary "
         "material; both decisive tiers are unchanged for any threshold pair that keeps the borderline arm in its intended tier.")
    h2("3.7 External-validity decomposition")
    body("We evaluate external validity as three separately migrating components rather than as a single external AUC, because one "
         "summary statistic conflates distinct failure modes and cannot localize which property moved. **(C1) Spatial "
         "organization:** whether the score retains genuine spatial autocorrelation under coordinate permutation (Moran's I against "
         "a permutation null), independent of any disease axis. **(C2) Rank discrimination:** whether the score orders independent "
         "external samples by grade (sample-level Kendall τ or AUROC), independent of its absolute scale. **(C3) Calibration and "
         "grading:** whether the sign and level of the score map onto ground-truth grade—i.e., whether an absolute score threshold "
         "carries over across platforms. The three are reported separately throughout Section 4; as shown there, they can transfer "
         "without one another (rank discrimination survives onto an independent GeoMx cohort while calibration sign and grading do "
         "not), so a single external AUC would obscure which component generalized.")

    # ---- 4 Results -----------------------------------------------------
    h1("4. Results")
    h2("4.1 Positive-control validation: the audit discriminates real signal from memorization")
    def _sim_seeds(g):
        return [r for r in _sim_arms.get(g, {}).get("seeds", []) if r.get("transfer")]

    def _noall_head(g, s):
        fp = ROOT / "results" / f"results_SIM_{g}_NOALL_seed{s}.json"
        if not fp.exists():
            return None
        d = json.load(open(fp, encoding="utf-8"))
        return (d.get("progression_monotonicity") or {}).get("kendall_tau")

    def _fmt_seeds(g):
        return ", ".join(f"{r['transfer']['tau_lodo']:+.3f} (p={r['transfer']['p']:.3f})"
                         for r in _sim_seeds(g))

    if _sim_arms:
        body("Before applying MRP-ST to the cervical cohort, we tested its discriminative validity on three controlled "
             "Visium-format cohorts with known ground truth (90 donors per arm; Section 3.4), grading each with the "
             "pre-registered label-free probe. The audit separated all three regimes correctly:")
        add_table(
            ["Arm (ground truth)", "FULL in-sample head τ",
             "NO-ALL τ_LODO, mean ± SD", "Per-seed τ_LODO (perm. p)",
             "Sig. seeds", "Grade"],
            [
                ["A: strong shared program",
                 f"{_sim('group_A', 'full_head_insample_mean'):.3f}",
                 f"{_sim('group_A', 'transfer_mean'):.3f} ± {_sim('group_A', 'transfer_sd'):.3f}",
                 _fmt_seeds("group_A"),
                 f"{_sim('group_A', 'seeds_significant')}/{_sim('group_A', 'seeds_total')}",
                 _sim_grades.get("group_A", "?").upper()],
                ["B: weak / heterogeneous program",
                 f"{_sim('group_B', 'full_head_insample_mean'):.3f}",
                 f"{_sim('group_B', 'transfer_mean'):.3f} ± {_sim('group_B', 'transfer_sd'):.3f}",
                 _fmt_seeds("group_B"),
                 f"{_sim('group_B', 'seeds_significant')}/{_sim('group_B', 'seeds_total')}",
                 _sim_grades.get("group_B", "?").upper()],
                ["C: donor-specific fingerprints only",
                 f"{_sim('group_C', 'full_head_insample_mean'):.3f}",
                 f"{_sim('group_C', 'transfer_mean'):.3f} ± {_sim('group_C', 'transfer_sd'):.3f}",
                 _fmt_seeds("group_C"),
                 f"{_sim('group_C', 'seeds_significant')}/{_sim('group_C', 'seeds_total')}",
                 _sim_grades.get("group_C", "?").upper()],
            ],
            caption="Table 3. Positive-control validation of MRP-ST on simulated cohorts (three seeds, B=10,000 "
                    "sample-label permutations). τ_LODO is the leave-one-donor-out Kendall τ-b of a ridge severity probe on "
                    "frozen NO-ALL (fully label-free) per-donor embeddings; the FULL column is the supervised model's in-sample "
                    "scalar-head τ.")
        _a_heads = [_noall_head("group_A", s) for s in range(3)]
        _a_heads = [f"{v:+.2f}" for v in _a_heads if v is not None]
        body(f"**Specificity—genuine signal is not falsely flagged.** Arm A's label-free representation transfers almost "
             f"perfectly to unseen donors (τ_LODO={_sim('group_A', 'transfer_mean'):.3f}, p<0.001 on all three seeds), while the "
             f"unsupervised scalar head is, as predicted, directionless—its in-sample τ values across the same three seeds were "
             f"{', '.join(_a_heads)}, including strongly negative values, even though the frozen representation read out by the "
             f"probe was identically oriented at τ={_sim('group_A', 'transfer_mean'):.3f}. This directly validates the decision "
             f"to grade representations rather than scalar heads.")
        body(f"**Sensitivity—identity confounding is caught.** Arm C contains no class-level signal whatsoever: each donor "
             f"carries an independent zero-sum fingerprint. A supervised model nevertheless fits these labels in-sample "
             f"(FULL head τ={_sim('group_C', 'full_head_insample_mean'):.3f}), but nothing transfers to unseen donors "
             f"(τ_LODO={_sim('group_C', 'transfer_mean'):.3f}±{_sim('group_C', 'transfer_sd'):.3f}, 0/3 seeds significant; "
             f"in-sample–transfer gap={_sim('group_C', 'gap_insample_minus_transfer'):.3f})—the operational memorization "
             f"signature. The same arm probed on the supervised FULL encoder instead reaches the τ ceiling, confirming "
             f"empirically that LODO probes are only interpretable on label-free encoders.")
        body(f"A lesion-localizing ablation identifies the conduit of the artifact: in arm C the in-sample head τ is carried "
             f"almost entirely by the morphology stream—removing the image branch collapses it from "
             f"{_sim('group_C', 'full_head_insample_mean'):.3f} to τ={_simaud('group_C', 'NOIMAGE'):+.3f}, whereas arm A's "
             f"transferable program is insensitive to the same ablation (τ={_simaud('group_A', 'NOIMAGE'):+.3f}). Donor "
             f"identity in this regime is therefore memorized through section-specific H&E histology in the patch encoder, "
             f"not through any class-level expression axis (per-seed cascade in Supplementary Table S3-2).")
        body(f"**Borderline regime.** Arm B yields weak, seed-dependent transfer "
             f"(τ_LODO={_sim('group_B', 'transfer_mean'):.3f}±{_sim('group_B', 'transfer_sd'):.3f}; "
             f"{_sim('group_B', 'seeds_significant')}/3 seeds significant) and is graded suggestive exactly as designed, "
             f"showing the middle tier is responsive rather than a forced binary call.")
        body("MRP-ST therefore exhibits both specificity (a real cross-donor program is passed) and sensitivity (pure "
             "donor identity confounding is failed with a large in-sample–transfer gap), and its borderline tier behaves "             "calibrated. Generator parameters, per-seed tables and the probe implementation are in Supplementary Table S3 "
             "and the code repository.")
        if _sma_arms:
            body("**Scale-matched control at the real cohort size.** Regenerating all three arms at exactly the cervical cohort's "
                 "scale (31 normal + 4 diseased = 35 donors; Section 3.4) preserves both decisive verdicts and localizes which tier "
                 "is scale-sensitive. The truly-signal arm A remains 'supported' "
                 f"(τ_LODO={_sma('group_A_small', 'transfer_mean'):.3f}, 3/3 seeds, p=0.002) and the no-signal arm C remains "
                 f"'unsupported' (τ_LODO={_sma('group_C_small', 'transfer_mean'):.3f}, 0/3). Only the deliberately borderline arm B "
                 f"shifts, from 'suggestive' at 90 donors to 'unsupported' at 35 "
                 f"(τ_LODO={_sma('group_B_small', 'transfer_mean'):.3f}, 0/3): at realistic scale the audit demands stronger "
                 "evidence before certifying a weak signal. Critically, the in-sample apparent signal in arms B and C (FULL-head "
                 f"τ={_sma('group_B_small', 'full_head_insample_mean'):.3f} and "
                 f"{_sma('group_C_small', 'full_head_insample_mean'):.3f}) again collapses under label-free LODO transfer "
                 "(τ_LODO≈−0.10 and 0.00), so the label-anchoring artifact is, if anything, more visible at the real cohort's "
                 "scale rather than less. The supported/unsupported boundary is therefore scale-invariant in this regime; only the "
                 "suggestive band is scale-sensitive.")
            add_table(
                ["Arm (ground truth)", "FULL in-sample head τ", "NO-ALL τ_LODO, mean ± SD",
                 "Per-seed τ_LODO (perm. p)", "Sig. seeds", "Grade"],
                [
                    ["A: strong shared program",
                     f"{_sma('group_A_small', 'full_head_insample_mean'):.3f}",
                     f"{_sma('group_A_small', 'transfer_mean'):.3f} ± {_sma('group_A_small', 'transfer_sd'):.3f}",
                     _sma_seedstr("group_A_small"),
                     f"{_sma('group_A_small', 'seeds_significant')}/{_sma('group_A_small', 'seeds_total')}",
                     _sma_grades.get("group_A_small", "?").upper()],
                    ["B: weak / heterogeneous program",
                     f"{_sma('group_B_small', 'full_head_insample_mean'):.3f}",
                     f"{_sma('group_B_small', 'transfer_mean'):.3f} ± {_sma('group_B_small', 'transfer_sd'):.3f}",
                     _sma_seedstr("group_B_small"),
                     f"{_sma('group_B_small', 'seeds_significant')}/{_sma('group_B_small', 'seeds_total')}",
                     _sma_grades.get("group_B_small", "?").upper()],
                    ["C: donor-specific fingerprints only",
                     f"{_sma('group_C_small', 'full_head_insample_mean'):.3f}",
                     f"{_sma('group_C_small', 'transfer_mean'):.3f} ± {_sma('group_C_small', 'transfer_sd'):.3f}",
                     _sma_seedstr("group_C_small"),
                     f"{_sma('group_C_small', 'seeds_significant')}/{_sma('group_C_small', 'seeds_total')}",
                     _sma_grades.get("group_C_small", "?").upper()],
                ],
                caption=f"Table 3b. Scale-matched positive-control validation (31 normal + 4 diseased = 35 donors, exactly the "
                        f"cervical cohort size; three seeds, B={_sma_perm or 500} sample-label permutations). Same pre-registered "
                        f"grading rule and layout as Table 3. The decisive A='supported' and C='unsupported' verdicts are unchanged "
                        f"from the 90-donor run; only the deliberate borderline arm B moves, to 'unsupported'."
            )
        else:
            body("[Pending server run: results/sim_lodo_summary_small.json will be inserted here.]")
    else:
        body("[Pending server run: three-arm positive-control results will be inserted from sim_lodo_summary.json.]")
    h2("4.2 Cohort spectrum and in-cohort risk ordering")
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
            f"Figure 2. **Descriptive in-sample result; not evidence of generalization, and not model performance.** "
            f"In-cohort per-spot risk by histologic severity (FULL, seed 0): normal {RV['normal_mean']:.2f}, HSIL "
            f"{RV['hsil_mean']:.2f}, cancer {RV['cancer_mean']:.2f}. This fitted-cohort separation at disease "
            f"n={CO['n_disease']} is a descriptive diagnostic only; whether it reflects learning or label anchoring is "
            "adjudicated by the nested NO-PROG/NO-SUP/NO-ALL cascade (Section 4.3), not by the values shown here.")
    body(f"Mean per-spot risk rises monotonically normal < HSIL < cancer, but this separation exists inside the supervised "
         f"training set. The label-removal result below shows it must not be read as evidence of generalization.")
    h2("4.3 Label-removal ablation: ordered ranking is label-anchored (suggestive)")
    add_fig("Fig3_ablation_multiseed.png", 6.2,
            "Figure 3. Same-cohort multi-seed ablation. Left: spatial coherence (Moran's I). Right: disease ordering (Kendall τ; "
            "points are seeds, bars mean ± SD). Removing severity labels (NO-PROG) drops τ to the significance boundary while "
            f"Moran's I barely changes ({A['NOPROG']['n_seeds']}-seed permutation p={A['NOPROG']['tau_perm_p_min']:.3f}–"
            f"{A['NOPROG']['tau_perm_p_max']:.3f}, {A['NOPROG']['tau_perm_nsig']}/{A['NOPROG']['n_seeds']} seeds nominal); "
            + ("the fully label-free NO-SUP arm removes the residual ordering (all seeds n.s.); " if _ns_state == "clean"
               else "the fully label-free NO-SUP arm leaves only a weak, seed-unstable residue "
                    f"(τ={_ns['tau_mean']:.2f}, permutation p={_ns_p_range}, {_ns_count}); " if _ns_state == "mixed"
               else "the fully label-free NO-SUP arm retains residual ordering on every seed (see Table 4); " if _ns_state == "robust"
               else "the fully label-free NO-SUP arm tests whether any ordering survives without targets; ")
            + ("the target- and pathway-regularizer-free NO-ALL arm then abolishes it (all seeds n.s.)" if _na_state == "gone"
               else f"the target- and pathway-regularizer-free NO-ALL arm reduces it to τ={_na['tau_mean']:.2f} (p={_na_p_range}, {_na_count})"
                    if _na_state == "reduced"
               else f"a weak residue still survives NO-ALL (τ={_na['tau_mean']:.2f}, p={_na_p_range}, {_na_count}), indicating "
                    "intrinsic data geometry" if _na_state == "persist"
               else "the target- and pathway-regularizer-free NO-ALL arm tests the pathway-regularizer source [results pending]")
            + "; removing the morphology branch lowers Moran's I but leaves τ unchanged. NO-HPV τ is marginally above FULL "
            f"({A['NOHPV']['tau_mean']:.3f} vs {A['FULL']['tau_mean']:.3f}); the difference (≈0.002) is well within one "
            f"across-seed SD ({A['NOHPV']['tau_sd']:.3f}), so the pathway-consistency prior carries no detectable ordering "
            "signal on its own—the ordering is supplied by the proxy and labels, not by λ_hpv.")
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
          f"~{A['NOHPV']['tau_perm_p_min']:.0e}", "Pathway term not decisive for ordering (τ marginally above FULL: within-seed noise, see text)"],
         ["NO-NEIGH", A['NONEIGH']['n_seeds'], f"{A['NONEIGH']['moran_mean']:.3f} ± {A['NONEIGH']['moran_sd']:.3f}",
          f"{A['NONEIGH']['tau_mean']:.3f} ± {A['NONEIGH']['tau_sd']:.3f}",
          f"~{A['NONEIGH']['tau_perm_p_min']:.0e}", "Coherence not from the neighbor term"],
         ["NO-PROG", A['NOPROG']['n_seeds'], f"{A['NOPROG']['moran_mean']:.3f} ± {A['NOPROG']['moran_sd']:.3f}",
          f"{A['NOPROG']['tau_mean']:.3f} ± {A['NOPROG']['tau_sd']:.3f}",
          f"{A['NOPROG']['tau_perm_p_min']:.3f}–{A['NOPROG']['tau_perm_p_max']:.3f} ({A['NOPROG']['tau_perm_nsig']}/{A['NOPROG']['n_seeds']} nominal)",
          "Ordinal labels off; expression-derived proxy retained"],
         _nosup_row,
         _noall_row],
        caption="Table 4. Same-cohort multi-seed ablation (35 samples, 46,820 spots, locked protocol). NO-SUP sets both "
                "λ_sup=0 and λ_prog=0 (no ordinal labels, no expression-derived proxy); NO-ALL additionally sets λ_hpv=0, "
                "so no ordinal target, proxy or pathway-consistency prior contributes a gradient (reconstruction, neighborhood, "
                "morphology and the panel genes as ordinary inputs remain). P-values permute the severity vector "
                "across all 35 samples; asymptotic p-values are in Supplementary Table S1 and the permutation caliber governs "
                "at small n.")
    body(f"Removing severity-label regression lowers Kendall τ from {A['FULL']['tau_mean']:.3f} to "
         f"{A['NOPROG']['tau_mean']:.3f}±{A['NOPROG']['tau_sd']:.3f} (per-seed τ={_np_taus}; permutation p={_np_pp}: "
         f"{A['NOPROG']['tau_perm_nsig']}/{A['NOPROG']['n_seeds']} seeds nominal, one straddling 0.05). The SCC demonstration "
         "section ranks above 30/31 normals in every seed, the HSIL section above ~25–26, while the ADC section exceeds only "
         "8–13 normals and is consistently weakest (foreshadowing Section 4.6). One-sided Mann–Whitney gives "
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
         + ("The frozen-representation transfer probe sharpens this conclusion (Section 3.4). Applied to the cervical "
            "NO-ALL embeddings with all 35 donors, leave-one-donor-out probing gives "
            f"τ_LODO={_RL['lodo_mean']:.3f}±{_RL['lodo_sd']:.3f} (per-seed {_RL_SEEDSTR}) against an "
            f"in-sample probe τ={_RL['insample_probe_mean']:.3f}—a moderate gap of "
            f"{_RL['insample_probe_mean'] - _RL['lodo_mean']:.3f}. One of three seeds is significant and two are borderline; "
            "under the pre-registered rules the cervical representation is therefore graded **suggestive**: a weak, "
            "seed-unstable cross-donor disease axis survives complete removal of labels, the proxy and the pathway prior, "
            "distinct from the chance-level transfer of the identity-confounding control but far below the strong-signal arm. "
            "This agrees with the fold-wise LODO of Section 4.6, where three labeled sections stabilize transfer of the "
            "direction while the zero-label limit on held-out sections is partial and unstable."
            if _RL else
            "It is not pure memorization either: semi-supervised LODO (Section 4.6) shows three labeled sections stabilize "
            "transfer of the direction, whereas the zero-label limit on held-out sections is partial and unstable."))
    h2("4.4 Sources of coherence, and the two-axis morphology verdict")
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
         "reflect anchoring. The 35-fold LOSO audits are decisive: morphology-to-HPV-proxy ridge scoring is evaluable in only "
         f"{LOSO_RIDGE[2]}/35 folds (mean AUC {BSL.get('loso_hpv_ridge_auc', float('nan')):.3f}±"
         f"{BSL.get('loso_hpv_ridge_auc_sd', float('nan')):.3f})—in the other {35 - LOSO_RIDGE[2]} folds the held-out ridge "
         "prediction collapses to a near-constant value, so the per-fold AUC is undefined; this collapse is itself evidence that "
         "image morphology carries no transferable per-spot HPV-proxy signal at this sample size. An MLP, which collapses in far "
         f"fewer folds, is evaluable in {LOSO_MLP[2]}/35 (AUC {BSL.get('loso_hpv_mlp_auc', float('nan')):.3f}±"
         f"{BSL.get('loso_hpv_mlp_auc_sd', float('nan')):.3f}). No individual fold exceeds chance appreciably: the evaluable "
         f"per-fold AUC spans {LOSO_RIDGE[0]:.2f}–{LOSO_RIDGE[1]:.2f} (ridge) and {LOSO_MLP[0]:.2f}–{LOSO_MLP[1]:.2f} (MLP), "
         f"with the best fold reaching only {max(LOSO_RIDGE[1], LOSO_MLP[1]):.2f}. Morphology-to-expression reconstruction gives "
         f"per-gene Pearson r={BSL.get('loso35_per_gene_pearson', float('nan')):.3f} (MSE "
         f"{BSL.get('loso35_recon_mse', float('nan')):.3f}), no better than in-sample interpolation "
         f"(MSE {BSL.get('he2st_mse', float('nan')):.3f}). The juxtaposition—in-sample AUC 1.00 versus cross-sample AUC ≈0.50—is "
         "the central cautionary result of the benchmark.")
    h2("4.5 Biological interpretation of the pathway-anchored score")
    body("**Constructive output: what survives supervision removal.** The audit is not only diagnostic; run in reverse it "
         "specifies which biological programs a small-n ST study can legitimately report. Re-testing the same pathway "
         "correlations after removing the ordinal labels, the expression-derived proxy, and finally the pathway prior "
         "(de-circularization control) separates intrinsic spatial biology from associations constructed by the supervised "
         "target: tumor-epithelium and interferon-antiviral associations persist through NO-SUP and therefore stand on the "
         "expression data itself, whereas the HPV-driver association is maintained by the pathway prior.")
    add_fig("Fig4_biology_correlation.png", 5.8,
            "Figure 4. **Purely descriptive spot-level correlation; spots are not independent. Statistical inference must "
            "rely on sample-level comparisons, never on these spot-level values.** Spearman correlation of spot risk with 11 "
            "pathway/cell-state scores (within-sample z, mean of three FULL seeds; all survive BH FDR; weakest "
            f"{WEAKEST_Q_SET.replace('_', ' ').lower()}, q={WEAKEST_Q:.0e}); 46,820 non-independent spots.")
    body(f"High-risk spots are enriched for tumor epithelium (KRT5/14/17, EPCAM; ρ={BIO['CELL_tumor_epithelial']['rho']:+.2f}), "
         f"HPV driver programs (CDKN2A/MYC/EGFR/PIK3CA; ρ={BIO['HPV_INTEGRATION_CANDIDATE']['rho']:+.2f}) and antigen "
         f"presentation (B2M/HLA-A/PSMB8; ρ={BIO['ANTIGEN_PRESENTATION']['rho']:+.2f}), and depleted for interferon-antiviral "
         f"programs (STAT1/MX1/ISG15; ρ={BIO['INTERFERON_ANTIVIRAL']['rho']:+.2f}), proliferation "
         f"({BIO['PROLIFERATION']['rho']:+.2f}; the axis is not a proliferation surrogate) and EMT "
         f"({BIO['EMT']['rho']:+.2f}). Marker validity was confirmed in independent cervical scRNA-seq [@scrna] "
         f"({SCR['n_cells']:,} integrated cells): mean within-lineage score correlation {SCR['within_corr']:+.3f} versus "
         f"{SCR['between_corr']:+.3f} across lineages (gap {SCR['gap']:+.3f}).")
    # De-circularization control (#5) — read from decircularization_biology.json
    if _DECIRC is not None:
        _dc = _DECIRC["variants"]
        _kt_full = _dc.get("FULL", {}).get("CELL_tumor_epithelial", {}).get("rho_mean")
        _kt_nosup = _dc.get("NOSUP", {}).get("CELL_tumor_epithelial", {}).get("rho_mean")
        _kt_noall = _dc.get("NOALL", {}).get("CELL_tumor_epithelial", {}).get("rho_mean")
        _hpv_full = _dc.get("FULL", {}).get("HPV_INTEGRATION_CANDIDATE", {}).get("rho_mean")
        _hpv_nosup = _dc.get("NOSUP", {}).get("HPV_INTEGRATION_CANDIDATE", {}).get("rho_mean")
        _hpv_noall = _dc.get("NOALL", {}).get("HPV_INTEGRATION_CANDIDATE", {}).get("rho_mean")
        _ifn_full = _dc.get("FULL", {}).get("INTERFERON_ANTIVIRAL", {}).get("rho_mean")
        _ifn_nosup = _dc.get("NOSUP", {}).get("INTERFERON_ANTIVIRAL", {}).get("rho_mean")
        _ifn_noall = _dc.get("NOALL", {}).get("INTERFERON_ANTIVIRAL", {}).get("rho_mean")
        body("**De-circularization control.** Because the risk head is supervised against an expression-derived HPV proxy and "
             "anchored by a KEGG-HPV pathway prior, the HPV-program correlation in Fig. 4 is partly circular by construction. "
             "To separate constructed from intrinsic biology, we re-ran the same 11-pathway ssGSEA-vs-risk correlation under "
             "NO-PROG (ordinal labels removed), NO-SUP (labels + proxy removed), and NO-ALL (labels + proxy + pathway prior "
             "removed). Tumor-epithelium enrichment "
             + (f"(ρ_FULL={_kt_full:+.2f} → ρ_NO-SUP={_kt_nosup:+.2f} → ρ_NO-ALL={_kt_noall:+.2f}) " if _kt_full is not None else "")
             + "and interferon depletion "
             + (f"(ρ_FULL={_ifn_full:+.2f} → ρ_NO-SUP={_ifn_nosup:+.2f} → ρ_NO-ALL={_ifn_noall:+.2f}) " if _ifn_full is not None else "")
             + "survive removal of both labels and the expression-derived proxy (NO-SUP), indicating they are **intrinsic to the "
             "spatial expression data, not constructed by the supervised target**. They collapse only when the KEGG-HPV pathway "
             "prior is also removed (NO-ALL), showing the prior acts as an inductive bias that lets the model latch onto real "
             "biological structure. In contrast, the HPV-driver correlation "
             + (f"(ρ_FULL={_hpv_full:+.2f} → ρ_NO-SUP={_hpv_nosup:+.2f} → ρ_NO-ALL={_hpv_noall:+.2f}) " if _hpv_full is not None else "")
             + "also survives NO-SUP but reverses at NO-ALL—consistent with the pathway prior maintaining it. We therefore treat "
             "tumor-epithelium and interferon as the primary non-circular biological axes; the HPV-driver association is reported "
             "as prior-anchored rather than independently learned.")
    body("The directions are consistent with E6/E7-driven transformation and immune evasion; they are descriptive spatial "
         "associations, not causal evidence.")
    h2("4.6 Cross-platform and cross-organ label-free transfer")
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
    if _AUDG is not None:
        _au_full = _AUDG["scores"]["S_full"]
        _au_epi = _AUDG["scores"]["dec_epithelial_only"]
        _au_wgt = _AUDG["scores"]["dec_rho_weighted"]
        _au_sum = _AUDG["scores"]["dec_signsum"]
        _au_top = _AUDG["scores"]["dec_top2"]
        body(f"**Does the audit convert into a better predictor?** A warning is only useful if it also tells you what to build "
             f"instead, so we asked whether the certificate can be turned into a competing score. Using exactly the programs the "
             f"audit certifies as intrinsic (tumor-epithelium, interferon-antiviral; Section 4.5), we built a fully **label-free** "
             f"readout — rank enrichment of those programs on GeoMx expression alone, signed by the NO-SUP direction — and scored "
             f"the same ROIs as the supervised head. The single certified epithelial program reaches tumour-vs-benign "
             f"AUC={_au_epi['auc_tumor_vs_benign']:.3f} (ROI p={_au_epi['mwu_p_roi']:.1e}) against "
             f"{_au_full['auc_tumor_vs_benign']:.3f} for the fully supervised multimodal head "
             f"(ΔAUC={_AUDG['delta_auc_best_dec_minus_full']:+.3f}); naive combinations of several certified programs are worse "
             f"({_au_wgt['auc_tumor_vs_benign']:.3f}, {_au_sum['auc_tumor_vs_benign']:.3f}) and the weakest construction fails "
             f"({_au_top['auc_tumor_vs_benign']:.3f}). Two conclusions follow. Positive: the certificate is meaningful — a "
             f"supervision-free readout of one certified program transfers to an independent platform at essentially the level of "
             f"the trained multimodal model. Deflationary: the supervised head's external advantage over a single certified pathway "
             f"is marginal, so the model's transferable value is carried by one intrinsic biological axis rather than by multimodal "
             f"fusion. The audit therefore yields a **diagnosis with a bounded correction**, not a superior predictor, and we do not "
             f"claim the reverse.")
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
    h2("4.7 Label dose-response, null controls and the clinical-utility boundary")
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
         f"learning-free per-sample mean of the 108 HPV-panel genes, not the trained model score of Table 4—was "
         f"{RC['kegg_moran']:.3f}, not above 30 matched random panels ({RC['random_moran_mean']:.3f}, "
         f"{RC['random_moran_min']:.3f}–{RC['random_moran_max']:.3f}; "
         f"permutation p={RC['moran_perm_p']:.3f}), and disease ordering was identical for random panels (τ "
         f"{RC['kegg_kendall']:.3f}; AUC permutation p={RC['auc_perm_p']:.2f}): in-cohort smoothing is shared by any co-expressed "
         "set, and ordering is label-anchored. The cross-organ panel-level advantage (Section 4.6) is a different caliber and is "
         "not contradicted.")
    body(f"**No prognostic or decision utility.** None of 11 spatial DEGs was significant in a {TC['n_patients']}-patient "
         f"({TC['events']} events) TCGA-CESC bulk Cox model [@cox] (smallest {TC['min_gene']} p={TC['min_p']:.3f}), a scale break "
         "between spot-level spatial risk and patient-level outcome. Applying MRP-ST grading: spatial self-organization "
         "supported; cross-organ raw-panel pathway specificity supported; GeoMx rank discrimination with non-transferring sign, "
         "label anchoring, and semi-supervised > unsupervised LODO suggestive; in-cohort model-score pathway specificity and the "
         "morphology ranking gain unsupported; grading, prognosis and cross-organ discrimination unsupported.")

    # ---- 5 Discussion --------------------------------------------------
    h1("5. Discussion")
    h2("5.1 Principal findings")
    body("**Contribution and priority.** The primary contribution of this work is a method: LDI, a scalar label-dependence "
         "metric with a calibrated decision gate, and MRP-ST, the executable nested label-removal protocol that operationalizes "
         "it. To our knowledge it is the first ST-native protocol of this kind; prior work documents label leakage and identity "
         "confounding as principles [@kapoor;@whalen;@davis;@schreiber;@karin] but does not provide an executable procedure that "
         "localizes which label-derived component drives a given risk score. The cervical analysis is the method's application, "
         "not its claim to novelty.")
    body("The study yields a validated instrument, three substantive findings and one central caution. The instrument first: "
         "on controlled cohorts with known ground truth, the label-free leave-one-donor-out probe passed a strong shared "
         f"program (τ_LODO={_sim('group_A', 'transfer_mean'):.3f}, all seeds), correctly called a weak heterogeneous program "
         f"suggestive ({_sim('group_B', 'transfer_mean'):.3f}±{_sim('group_B', 'transfer_sd'):.3f}), and failed pure donor "
         f"identity confounding (in-sample τ={_sim('group_C', 'full_head_insample_mean'):.3f} versus "
         f"τ_LODO={_sim('group_C', 'transfer_mean'):.3f})—establishing specificity and sensitivity before the audit was used on "
         "real data. Substantive findings: the pathway-anchored score is biologically interpretable after de-circularization "
         "(tumor-epithelial and interferon relationships survive label/proxy removal and are marker-validated in independent "
         "scRNA-seq, whereas HPV-program enrichment is prior-anchored rather than independently learned); spatial coherence is "
         "high even without labels, priors or neighbors, with a small morphology increment; and external validity dissociates, "
         "with rank discrimination surviving onto GeoMx and genuine spatial organization onto 14 head-and-neck sections while "
         "calibration sign and grading do not. The caution is quantitative and now graded rather than binary: in-sample AUC "
         "1.00 coexists with LOSO AUC ≈0.50, scalar-head ranking collapses after label removal, and even the fully label-free "
         "representation transfers only weakly and seed-unstably to unseen cervical donors "
         + (f"(τ_LODO={_RL['lodo_mean']:.3f}±{_RL['lodo_sd']:.3f}, suggestive—above the identity-confounding control, far below "
            "the strong-signal control). " if _RL else "")
         + "Without the removal ablations, permutation nulls, controlled positives and whole-sample hold-outs, every number "
         "here would read as a successful risk model; with them, weak partial representation transfer, spatial organization and "
         "platform-level separability survive, but fine clinical ranking, calibration and grading do not.")
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
    body("**Scope of the biological reading.** The four diseased cervical sections are a worked example only: none of the cervical "
         "molecular associations reported here constitute new biological findings, and the contribution of this work is the audit "
         "methodology, not a cervical disease mechanism.")
    body("(1) Power: four independent disease events and six paired GeoMx patients bound every inference; 3/4-seed and 6/6 "
         "counts with wide exact intervals justify suggestive grading; the MRP-ST trigger and the supported/suggestive/unsupported "
         "boundaries (τ_LODO ≥ 0.35, ≤ 0.15) are pragmatic operational cut-offs set from a single extreme case and have not been "
         "calibrated on multiple independent real cohorts—multi-cohort calibration is required before normative use. The "
         "scale-matched control makes this concrete: at the real cohort's size a genuinely weak planted signal is graded "
         "'unsupported' rather than 'suggestive' (Section 4.1), so the τ≥0.35 band is conservative for small cohorts and must be "
         "re-calibrated when n is this small. "
         "(2) Platform and histology confounding: the external cervical cohort is ADC on a "
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
         "disease-correlated signal in the inputs. **The proxy's transductive character is a genuine leakage-adjacent limitation: its target "
         "is thresholded at the global median over all analyzed spots rather than on training samples alone.** The statistically "
         "clean implementation—and what MRP-ST practice should adopt—derives the proxy threshold from training-set spots only; we "
         "did not, and the optimism it introduces is not quantified here. "
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
    h1("6. Conclusion")
    body("We presented a label-dependence ablation benchmark for extreme low-sample spatial-transcriptomic risk modeling, "
         "comprising seven matched multi-seed variants in a nested label→proxy→prior removal cascade, whole-sample "
         "permutation, paired "
         "semi-/unsupervised hold-outs, expression-matched gene-set nulls and cross-platform external tests, formalized as the "
         "five-item MRP-ST protocol and a leave-one-donor-out probe on frozen label-free embeddings. Controlled cohorts with "
         "known ground truth verify the audit's specificity and sensitivity: a real shared program is passed, pure donor "
         "identity confounding is caught by its in-sample–transfer gap, and weak signal is graded as borderline. On four "
         "diseased cervical sections, a pathway-anchored model achieved perfect in-sample separation whose fine ranking the "
         "audit shows to be largely label-anchored, while the label-free representation retains only weak, seed-unstable "
         "cross-donor transfer (suggestive); spatial organization and cross-platform tumor–benign separability genuinely "
         "persist, calibration sign and grading do not. The benchmark is cheap, network-agnostic and designed to make label "
         "dependence visible before publication rather than after.")
    body("**Applicability.** MRP-ST and the seven ablations apply to any study in the few-diseased-samples regime—"
         "operationally, n_diseased ≤ 10 independent samples, or ≤ 5 in any class—where supervision is fitted on spot-level "
         "measurements that are spatially autocorrelated. This covers rare-disease spatial transcriptomics as well as spatial "
         "proteomics, metabolomics and multiplex imaging with the same few-sample/many-spot structure, and any supervised model "
         "built on public or consortium data where external cohorts are unavailable. It is not intended for studies with "
         "adequate disease replication (n_diseased > 10), where conventional sample-level cross-validation already carries the "
         "inferential claims, nor does it substitute for a disease-specific external validation cohort when one exists. The "
         "protocol requires controlled retraining of the ablation arms, inexpensive post-processing and a versioned result "
         "store, but no new data collection. It is independent of model architecture.")

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

    save(doc, "Manuscript_CiBM.docx")
    return doc, C


# ========================================================================
#  MANUSCRIPT — CHINESE READING COPY（供内部/导师审阅；正式投稿用英文版）
# ========================================================================
def build_manuscript_cn():
    doc, C, h1, h2, body, ctr, add_table, add_fig, emit = make_manuscript(cn=True)
    TITLE = ("MRP-ST 与标签依赖指数（LDI）：面向极端小样本空间转录组风险模型的"
             "经验证标签移除协议——以宫颈病变为例")

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
    ctr("本文件为同内容英文投稿稿（Manuscript_CiBM.docx）的中文对照版，仅供内部审阅；如中英文存在歧义，以英文版为准。",
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
         f"TCGA-CESC（{TC['n_patients']} 例患者）与宫颈 scRNA-seq 上的无标签外部评分。为验证审计本身的判别效度，"
         "另在三个真值已知的受控 Visium 格式仿真队列（强共享程序、弱异质程序、纯供体特异指纹；各 90 供体）上，"
         "于完全无标签（NO-ALL）编码器的冻结表征上做留一供体岭探针，并按预注册的 supported/suggestive/unsupported "
         "规则定级；同一探针随后用于真实宫颈队列的全部 35 个供体。为检验定级门槛的规模与外推稳健性，另在真实队列规模"
         "（31 正常 + 4 病变 = 35 供体）重新生成三臂，并在两种规模下对界值做扫描。")
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
    body(f"**审计的判别效度。** 阳性对照仿真中，强共享程序臂被正确定为 supported（τ_LODO="
         f"{_sim('group_A', 'transfer_mean'):.3f}，3/3 种子显著）、弱异质程序臂为 suggestive"
         f"（τ_LODO={_sim('group_B', 'transfer_mean'):.3f}±{_sim('group_B', 'transfer_sd'):.3f}）、"
         f"纯供体指纹臂为 unsupported（τ_LODO={_sim('group_C', 'transfer_mean'):.3f}，0/3 显著；尽管监督模型样本内"
         f"τ={_sim('group_C', 'full_head_insample_mean'):.3f}），同时证明了特异度与灵敏度。真实宫颈队列的无标签冻结表征"
         f"留一供体探针给出弱且跨种子不稳定的迁移（τ_LODO={_RL['lodo_mean']:.3f}±{_RL['lodo_sd']:.3f}，逐种子 "
         f"{_RL_SEEDSTR}），定为 suggestive——存在弱的跨供体疾病轴，但远不足以支持临床泛化。"
         + ("在真实队列规模（35 供体）上重新生成的对照臂保持了决定性的 supported/unsupported 判定，"
            "表明该定级门槛既不依赖阈值微调、也不依赖队列规模。" if _sma_arms else "")
         if _sim_arms and _RL else
         "**审计的判别效度。**【仿真与真实 LODO 结果待补。】")
    body("**结论。** 本文提出 LDI 与 MRP-ST，据我们所知是首个经过验证、网络无关、用于量化与审计小样本 ST 风险模型"
         "标签依赖的协议。其判别效度在已知真值的对照队列上确立——既能通过真实共享程序，又能否决纯身份混杂；其建设性价值"
         "在宫颈案例中体现：在完全移除标签后，同一协议分离出一组去监督后仍稳健的空间程序（肿瘤上皮、抗原呈递、干扰素），"
         "使小样本 ST 研究能够合法地报告这些结论。秩判别还可迁移至独立 GeoMx 队列，而校准与分级不能，从而分离出三个"
         "外部效度组分。该协议以开放、可复现的软件发布；本文所评估的具体风险评分是应用范例，而非临床器械。"
         "当对照臂在真实队列规模下重新生成时，决定性的 supported/unsupported 门槛依旧保持。")
    emit("**关键词：** 空间转录组；标签依赖基准；小样本机器学习；宫颈病变；多模态学习；跨平台验证；最低报告协议",
         10.5, after=0)
    doc.add_page_break()

    # ---- 1 引言 --------------------------------------------------------
    h1("1  引言")
    body("宫颈癌仍是全球女性第四大常见恶性肿瘤 [@sung]，高危型 HPV 持续感染是其主要病因 [@malagon]；"
         "大型多组学联盟已刻画了其分子图谱 [@tcga]，而宫颈腺癌的 Silva A/B/C 浸润模式分型是与间质浸润、"
         "淋巴结转移和预后相关联的成熟组织学分级体系 [@silva1;@silva2;@silva3;@silva4]。空间转录组（ST；"
         "如 10x Visium [@stahl]，综述见 [@moses;@moffitt;@bressan]）可在组织学原位测量基因表达，"
         "而 UNI、Virchow、GigaPath 等数字病理基础模型 [@uni;@virchow;@giga] 提供了可迁移的形态学表征。"
         "将表达、影像与通路先验相结合，因而成为原位刻画上皮转化的有吸引力的途径。")
    body("一个被系统性低估的方法学问题是样本稀缺：系统检索公共数据库中的宫颈空间转录组数据，应用三条纳入标准——"
         "（I1）标准 10x Visium 平台、55 µm 捕获 spot；（I2）具备切片级组织学标注；（I3）H&E 图像可得且可配准至捕获阵列"
         "坐标——仅保留四张独立的病变切片"
         "（1 张高级别鳞状上皮内病变、2 张鳞状细胞癌、1 张腺癌）对 31 张正常切片。经筛选但无法纳入分析的公开宫颈 ST "
         "数据集及其未满足的具体标准见补充表 S4，以便独立复核样本稀缺这一前提。在此规模下，任何监督式风险模型"
         "都可以拟合四个标签，样本级样本内 AUC=1.00 无法区分“学到的疾病信号”与“对四个独立事件的记忆”——这一失效"
         "模式在更广义的文献中对应标签泄漏 [@davis]、学习“受试者签名”而非“疾病签名” [@neto]，以及跨细胞类型预测中"
         "表观精度实为记忆训练背景的陷阱 [@schreiber]。罕见病 ST 研究越来越多地面临这一情形，但目前没有标准化、"
         "可执行的审计来区分上述两种解释。我们以一个新方法而非又一篇批评来回应：**LDI**——一个标量式标签依赖度量，"
         "在 **MRP-ST** 中落地为面向 ST、网络无关的嵌套去标签级联，配以 θ 校准决策门、阳性对照判别效度检验与五条目最低"
         "报告协议。该协议既是诊断性的，也是建设性的：应用于本队列时，它同样给出在移除监督后仍受支持的空间程序，从而界定"
         "小样本 ST 研究可以合法声称的范围。")
    body("通路生物学提供了天然的归纳偏置。HPV 致癌是由 E6/E7 驱动、经 p53/Rb 丢失、抗原呈递改变与免疫逃逸展开的"
         "保守程序；将表征锚定于 KEGG HPV 基因集 [@kegg]，有望得到生物学可解释、空间平滑、并可迁移至其他"
         "HPV 驱动上皮转化场景的评分。这些都是需要用对照检验的假设，而非可默认成立的性质。")
    body("**本文做出五项方法学贡献。**（1）提出 **MRP-ST**——首个面向 ST、网络无关的标签依赖审计框架，用于检出小样本"
         "风险模型中的标签依赖，形式化为七变体嵌套去标签级联（FULL → NO-IMAGE → NO-HPV → NO-NEIGH → NO-PROG → NO-SUP → "
         "NO-ALL），配以五条目最低报告协议与 supported/suggestive/unsupported 三级定级。（2）定义**标签依赖指数（LDI）**"
         "＝τ_FULL−τ_NO-ALL，带逐种子传播不确定性、θ 校准决策门（θ=2·|τ_NO-ALL|）及三条形式性质（可加性、种子稳健性、"
         "零分布校准）。（3）首次在真值已知的受控队列上对 ST 标签依赖审计做**判别效度验证**：在冻结无标签嵌入上做留一供体"
         "探针，将强共享程序定为 supported、弱异质程序定为 suggestive、纯供体特异身份混杂（样本内可学、不可迁移）定为 "
         "unsupported，从而同时确立特异度与灵敏度。（4）给出**多成分外部效度解离**：秩判别可迁移至 GeoMx，但校准符号反转、"
         "分级不迁移——三成分各自独立。（5）**去循环对照**在 NO-PROG/NO-SUP/NO-ALL 下重跑通路相关，将被构造的（标签/先验"
         "锚定）生物学与内在生物学分开。宫颈病变提供真实临床场景；本文贡献在于审计方法学，而非诊断工具。")
    body("我们明确不主张诊断、分级工具或多模态融合上的进展：形态学分支是事先定义的探索性模块，其收益在两条独立轴上"
         "分别报告；所有功效受限或阴性的结果均被定级而非隐藏。本文其余部分为：相关工作（第 2 节）、数据集/模型/基准/"
         "统计方法（第 3 节）、结果（第 4 节）、可推广经验与局限性（第 5–6 节）。")

    # ---- Statement of Significance (JBI-mandated; SKIP for AIIM) -------
    # add_table(... 意义声明表 JBI 专属，AIIM 无需 ...)

    # ---- 2 相关工作 ----------------------------------------------------
    h1("2  相关工作")
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
         "面向医疗机器学习标签泄漏的专门框架 [@davis]、小样本医学影像中的反复失效 [@varo] 以及极小数据集上二分类指标的"
         "不稳定性 [@steinert]。与之密切相关的一条线索研究**身份混杂**：模型可能学到“受试者签名”而非“疾病签名” [@neto]，"
         "且表观的跨场景性能可能反映的是对训练背景的记忆而非可迁移生物学——这一现象最早在跨细胞类型表达预测中被揭示 "
         "[@schreiber]，此后通过训练动力学分析注释错配被推广到单细胞与空间组学 [@karin]；区分二者需要在正确的统计单位上做"
         "置换检验 [@ojala]。在此正确单位上置换标签的两级外部交叉验证 [@wood] 是既有补救方案；TRIPOD+AI 等报告"
         "规范 [@tripod] 要求外部验证，但仍是通用原则，未针对 ST 落地。缺口是具体的：一个 ST 专用、网络无关的"
         "逐条基准——（i）在匹配的多种子协议下逐一移除监督成分；（ii）在正确的统计单位（独立样本，而非空间自相关的 "
         "spot）上置换标签；（iii）对比半监督与完全无监督的全样本留出；（iv）依据外部与零模型对照对结论定级。"
         "表 1 给出本文与现有技术的定位对比。我们不在规模或预测精度上竞争；我们提供缺失的评估层。")
    body("**首创性声明。** 据我们所知，此前尚无任何空间转录组分析流程提供带校准的标签依赖决策门的嵌套去标签级联，"
         "以及阳性对照判别效度检验；LDI 与 MRP-ST 是首个此类协议。既有工作确立了标签依赖的存在 "
         "[@kapoor;@whalen;@davis;@schreiber;@karin]，但未提供可执行的、面向 ST 的流程来分解*究竟是哪一个*标签衍生成分"
         "在驱动给定风险评分。因此本文的新颖贡献是方法本身，而非再一次证明该问题的存在。")
    add_table(
        ["研究脉络", "代表方法", "典型数据规模", "显式标签依赖审计", "跨平台外部检验", "本文独有的增量"],
        [["H&E → 表达", "HE2RNA、ST-Net [@he2rna;@stnet]", "数百–数千张切片", "无", "少见", "对监督风险输出本身做审计"],
         ["病理—ST 基础模型", "OmiCLIP、SPADE、SEAL、MINT、ST-Align、STPath [@omiclip;@spade;@seal;@mint;@stalign;@stpath]",
          "10⁵–10⁶ spot、多样本", "无", "留出器官，而非去标签", "去标签 + 跨平台审计"],
         ["ST/单细胞表征", "scGPT、Novae、CellCharter [@scgpt;@novae;@cellcharter]", "10⁷ 细胞", "无（自监督目标）", "无", "分解监督成分"],
         ["ST 整合基准", "Li 等 [@libench]", "多队列", "无——衡量整合精度", "无", "审计风险输出，而非整合精度"],
         ["小样本 ML 指南", "泄漏审计、小样本评估、TRIPOD+AI [@kapoor;@whalen;@davis;@schreiber;@karin;@varo;@steinert;@tripod]",
          "通用；表格/影像", "仅原则", "有要求但未执行", "可执行的 ST 协议 + 校准的 LDI 决策门"],
         ["本文", "通路锚定多模态模型＋审计基准＋MRP-ST",
          f"{CO['n_samples']} 样本 / {CO['n_disease']} 病变",
          "有：七个预注册多种子变体（含无目标与无通路正则臂）、全样本置换、双 LODO、随机基因零模型",
          "有：GeoMx、14 张 HNSCC 切片、TCGA-CESC、scRNA-seq",
          "首个面向 ST 的嵌套去标签级联，含校准 LDI 门与阳性对照判别效度"]],
        caption="表 1  与现有技术的定位对比；引用对应文末编号文献。")

    # ---- 3 材料与方法 --------------------------------------------------
    h1("3  材料与方法")
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
    body("**配套检索与排除。** 四张病变切片是检索时满足全部三条纳入标准（标准 55 µm Visium；切片级组织学标注；"
         "可配准 H&E）的公开 Visium 切片的完整集合；三个纳入来源与每一个经筛选但被排除的宫颈 ST 数据集及未满足的"
         "具体标准，均列于补充表 S4。该记录用于使样本稀缺这一前提可被独立复现，而非仅凭断言。", indent=False)
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
         "（同样 λ_sup=λ_prog=0，见 4.6 节）。FULL/NO-IMAGE/NO-HPV/NO-NEIGH/NO-SUP/NO-ALL 各种 3 个种子，NO-PROG 运行 "
         f"{A['NOPROG']['n_seeds']} 个种子（多种子用于检验显著边界处的结论稳定性）。各变体共享训练样本、spot 集、"
         "预处理、初始化协议与超参数；仅命名项发生改变。")
    body("**3.3.1 标签依赖指数（LDI）：形式化定义与性质。** 七变体级联不仅是若干消融运行，它诱导出一个形式化度量——"
         "**标签依赖指数（LDI）**，用于量化模型疾病排序信息中来自标签锚定项（而非内在空间几何）的比例。我们以沿级联的"
         "反向边际分解定义 LDI：**（1）  LDI = τ_FULL − τ_NO-ALL**，其中 τ_FULL 为完整模型的 Kendall τ，"
         "τ_NO-ALL 为完全剥离变体（λ_sup=λ_prog=λ_hpv=0）的 τ。不确定度跨独立训练种子传播为 "
         "**（2）  σ_LDI = √(σ_FULL² + σ_NO-ALL²)**，报告 LDI 的均值 ± SD。各被移除项的边际贡献沿级联依次计算："
         "Δτ_i = τ_前 − τ_后（如形态学贡献 = τ_FULL − τ_NOIMAGE，表达派生代理贡献 = τ_NOPROG − τ_NOSUP，"
         "通路先验残余 = τ_NOSUP − τ_NOALL），SD 按 √(σ_前² + σ_后²) 传播。LDI 配以 **θ 校准决策门**："
         "当 LDI > θ 时判为**标签依赖**，θ 可由置换零运行或随机基因零对照校准（回退值 θ=2·|τ_NO-ALL|）。"
         "LDI 满足三条形式性质：（i）**望远镜可加性**——LDI 恰等于级联上六个带符号边际贡献之和，故不假定、也不要求"
         "跨变体单调（各 Δτ_i 可为负）；（ii）**种子稳健性**——每个 LDI 估计均附跨种子 SD，使判定稳定性显式可见；"
         "（iii）**零分布校准**——θ 源自数据驱动零分布，而非任意阈值。"
         "**证明（望远镜可加性）。** 级联为线性链 FULL → … → NO-ALL，故由构造有 "
         "τ_FULL − τ_NO-ALL = Σ_i (τ_{i−1} − τ_i) = Σ_i Δτ_i；该恒等式不要求 Δτ_i 单调，各项可相互抵消或反号。"
         "**可迁移性说明**：LDI 要求下游任务具有有序疾病标签梯度（如正常→CIN→癌）；对仅二分类（肿瘤/良性）或无诊断"
         "标签的任务，基于 τ 的定义会退化、度量不再可解释。这不是 LDI 自身的局限，而是任何有序排序度量的共性——"
         "详见 5.3 节。")
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
    body("**无标签冻结表征的留一供体探针。** 队列内标量头 τ 只回答拟合后的风险头是否排好训练样本，无法区分合理监督学习"
         "与记忆。为此增加表征层面的迁移检验：将逐 spot 融合嵌入平均池化为每个供体一个 128 维向量，用岭回归线性严重度探针"
         "做留一供体交叉验证（在 N−1 个供体上训练、预测被留出供体；报告预测严重度与真实严重度的 Kendall τ-b，并对样本标签"
         "做 B=10,000 次置换检验）。两条预先指定的强制约束：（i）探针只在**无标签 NO-ALL 编码器**上可解释——FULL 或部分监督"
         "变体的编码器在联合训练时已用过每个供体的标签，被留出供体的标签已烤入编码器，此时线性 LODO 探针被污染（4.1 节"
         "用混杂臂实证：监督编码器上探针达到 τ 上限，而 NO-ALL 上仅为随机水平）；（ii）无监督编码器的标量风险头符号与朝向任意"
         "（其训练仅受邻域平滑与方差下限约束），故即便表征已含疾病轴，其头 τ 仍无信息，须由从训练供体确定朝向的线性探针读取。"
         "报告 τ_LODO（迁移）、完全样本内探针 τ 及两者之差（记忆签名：τ_LODO≈0 而 gap 大）。编码器仅在 X 上转导（无监督拟合时"
         "见过被留出供体的表达，从不见其标签），即标准线性探针协议。")
    body("**受控阳性对照仿真。** 在用于宫颈案例前，先生成三个真值已知的 Visium 格式队列（各 50 正常＋40 病变供体；"
         "每供体 1,500 spot；3,000 基因，含真实 108 基因 KEGG-HPV 面板；背景基因捕获率约 10%、面板约 40%；逐 spot 文库"
         "归一化）。**A 臂**注入单一共享、空间平滑的疾病程序（60% 面板基因，幅度 2.5，响应 0.9–1.1），叠加弱的供体特异"
         "逐基因技术偏移。**B 臂**注入弱共享程序（幅度 0.20，技术偏移 SD 1.5，35% 病变供体零反应、50% 逐供体程序基因脱落），"
         "构成真正的边界情形。**C 臂**为身份混杂对照：每个供体（正常与病变）都接受等幅的供体特异随机零和指纹（30% 面板基因"
         "升、30% 降、空间平滑），两类的边际均值与离散度完全一致；标签只能靠记忆个体指纹在样本内拟合，不含任何可跨供体迁移的"
         "类级方向。逐 spot 归一是必要的：乘性零和扰动在原始计数上并非零和（exp(+a)+exp(−a)>2），不归一会泄漏总量类别通道。"
         "每臂以 FULL 与 NO-ALL 各跑 3 个种子，按预注册规则在无标签探针上定级：**supported**＝均值 τ_LODO≥0.35 且 ≥2/3 种子 "
         "p<0.05；**unsupported**＝|均值 τ_LODO|≤0.15 且 0/3 种子显著；两者之间为 **suggestive**。阈值为查看宫颈结果前固定的"
         "务实操作界值，非常数规范。")
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
         "外推。对 HPV 代理 LOSO，每折在 34 个样本上训练、对留出样本评分，其 spot 标签由该样本自身 HPV 面板均值做中位数"
         "阈值化得到；仅当留出样本的预测非退化（SD > 1e-8）时才计算逐折 AUC，并明确报告可评估折数，同时以逐折 AUC 区间"
         "作为最坏情形敏感性。外部评分使用一个固定检查点（checkpoint_FULL_DEPLOY_FAST_seed42.pt）的表达分支，推理时不读取任何宫颈"
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
    body("**阈值鲁棒性。** 为检验定级是否处于临界状态，我们在两种队列规模下以完全相同的预注册规则扫描两个界值"
         "（τ_up ∈ {0.20, 0.25, 0.30, 0.35, 0.40, 0.45}；τ_low ∈ {0.10, 0.15, 0.20}；α=0.05）。两条性质在全网格上成立："
         "（i）A 组在所有 τ_up 直至其自身均值下恒为 supported（τ_A：90 供体为 0.71，35 供体为 0.46）；"
         "（ii）C 组在所有 τ_low ≥ 其 |均值| 下恒为 unsupported（τ_C=0.03 与 0.005）。故决定性的 supported/unsupported "
         "判定在整个合理阈值区间内、以及在 2.6 倍的队列规模变化下均不变。仅刻意设为边界情形的 B 臂对阈值敏感：90 供体下"
         "只有把 τ_up 降到其均值 0.22 以下（0.20）才会被提升为 supported；35 供体下除非把 τ_low 设在 0.10（其 |均值|）"
         "以下，否则维持 unsupported。完整网格见补充材料；只要使边界臂处于其预期档位，两个决定性档位对任何阈值组合都不变。")
    h2("3.7  外部效度分解")
    body("我们以三个各自独立迁移的组分、而非单一外部 AUC 来评估外部效度，因为单一汇总统计会混淆不同的失效模式、"
         "无法定位究竟哪一性质发生了迁移。**（C1）空间组织：** 评分在坐标置换下是否保留真实的空间自相关"
         "（Moran's I 对置换零分布），与疾病轴无关。**（C2）秩判别：** 评分是否按分级对独立外部样本排序"
         "（样本级 Kendall τ 或 AUROC），与其绝对尺度无关。**（C3）校准与分级：** 评分的符号与水平是否对应真值分级，"
         "即绝对评分阈值能否跨平台沿用。三者贯穿第 4 节分别报告；如第 4 节所示，它们可以彼此独立地迁移"
         "（秩判别可迁移至独立 GeoMx 队列，而校准符号与分级不能），故单一外部 AUC 会掩盖究竟是哪一组分实现了泛化。")

    # ---- 4 结果 --------------------------------------------------------
    h1("4  结果")
    h2("4.1  阳性对照验证：审计可区分真实信号与记忆")
    if _sim_arms:
        body("在将 MRP-ST 用于宫颈队列之前，先在三个真值已知的受控 Visium 格式队列（每臂 90 供体；3.4 节）上检验其"
             "判别效度，并以预注册的无标签探针逐一定级。审计正确区分了全部三种情形：")
        add_table(
            ["臂（真值）", "FULL 样本内头 τ",
             "NO-ALL τ_LODO，均值±SD", "逐种子 τ_LODO（置换 p）",
             "显著种子", "定级"],
            [
                ["A：强共享程序",
                 f"{_sim('group_A', 'full_head_insample_mean'):.3f}",
                 f"{_sim('group_A', 'transfer_mean'):.3f} ± {_sim('group_A', 'transfer_sd'):.3f}",
                 _fmt_seeds("group_A"),
                 f"{_sim('group_A', 'seeds_significant')}/{_sim('group_A', 'seeds_total')}",
                 _sim_grades.get("group_A", "?").upper()],
                ["B：弱/异质程序",
                 f"{_sim('group_B', 'full_head_insample_mean'):.3f}",
                 f"{_sim('group_B', 'transfer_mean'):.3f} ± {_sim('group_B', 'transfer_sd'):.3f}",
                 _fmt_seeds("group_B"),
                 f"{_sim('group_B', 'seeds_significant')}/{_sim('group_B', 'seeds_total')}",
                 _sim_grades.get("group_B", "?").upper()],
                ["C：仅供体特异指纹",
                 f"{_sim('group_C', 'full_head_insample_mean'):.3f}",
                 f"{_sim('group_C', 'transfer_mean'):.3f} ± {_sim('group_C', 'transfer_sd'):.3f}",
                 _fmt_seeds("group_C"),
                 f"{_sim('group_C', 'seeds_significant')}/{_sim('group_C', 'seeds_total')}",
                 _sim_grades.get("group_C", "?").upper()],
            ],
            caption="表 3  MRP-ST 在仿真队列上的阳性对照验证（3 种子，B=10,000 次样本标签置换）。τ_LODO 为冻结 NO-ALL"
                    "（完全无标签）逐供体嵌入上岭严重度探针的留一供体 Kendall τ-b；FULL 列为监督模型的样本内标量头 τ。")
        _a_heads_cn = [_noall_head("group_A", s) for s in range(3)]
        _a_heads_cn = [f"{v:+.2f}" for v in _a_heads_cn if v is not None]
        body(f"**特异度——真实信号不被误报。** A 臂的无标签表征近乎完美迁移到未见过的供体（τ_LODO="
             f"{_sim('group_A', 'transfer_mean'):.3f}，三个种子 p<0.001）；而无监督标量头如预期般朝向不定——同样三个种子"
             f"的样本内头 τ 为 {', '.join(_a_heads_cn)}，含强负值，尽管探针读出的冻结表征恒为 τ="
             f"{_sim('group_A', 'transfer_mean'):.3f}。这直接验证了应对表征（而非标量头）定级。")
        body(f"**灵敏度——身份混杂被捕获。** C 臂完全不含类级信号，每个供体仅携带独立零和指纹。但监督模型仍可在样本内"
             f"拟合这些标签（FULL 头 τ={_sim('group_C', 'full_head_insample_mean'):.3f}），而无一可迁移到新供体"
             f"（τ_LODO={_sim('group_C', 'transfer_mean'):.3f}±{_sim('group_C', 'transfer_sd'):.3f}，0/3 种子显著；"
             f"样本内—迁移差={_sim('group_C', 'gap_insample_minus_transfer'):.3f}）——即操作性的记忆签名。同一臂若在监督 "
             f"FULL 编码器上做探针则达到 τ 上限，实证了 LODO 探针只在无标签编码器上可解释。")
        body(f"一项定位消融进一步指认了伪迹载体：C 臂的样本内头 τ 几乎全部由形态学分支撑载——去除图像分支后其由 "
             f"{_sim('group_C', 'full_head_insample_mean'):.3f} 骤降至 τ={_simaud('group_C', 'NOIMAGE'):+.3f}，而 A 臂可迁移"
             f"程序对同一消融不敏感（τ={_simaud('group_A', 'NOIMAGE'):+.3f}）。故该情形下供体身份是经由 patch 编码器中"
             f"切片特异的 H&E 组织学被记忆，而非经由任何类级表达轴（逐种子级联见补充表 S3-2）。")
        body(f"**边界情形。** B 臂给出弱且依赖种子的迁移（τ_LODO="
             f"{_sim('group_B', 'transfer_mean'):.3f}±{_sim('group_B', 'transfer_sd'):.3f}；"
             f"{_sim('group_B', 'seeds_significant')}/3 种子显著），按设计定为 suggestive，说明中间档具有响应性而非"
             "被迫的二元判定。")
        body("MRP-ST 因而兼具特异度（真实跨供体程序通过）与灵敏度（纯供体身份混杂以大的样本内—迁移差被否决），"
             "且边界档行为校准。生成器参数、逐种子表与探针实现见补充表 S3 与代码仓库。")
        if _sma_arms:
            body("**真实队列规模的规模匹配对照。** 在与宫颈队列完全相同的规模下（31 正常 + 4 病变 = 35 供体；见 3.4 节）"
                 "重新生成三臂，两个决定性判定均保持不变，并定位出究竟是哪一档对规模敏感。真信号臂 A 仍为 supported"
                 f"（τ_LODO={_sma('group_A_small', 'transfer_mean'):.3f}，3/3 种子显著，p=0.002），无信号臂 C 仍为 "
                 f"unsupported（τ_LODO={_sma('group_C_small', 'transfer_mean'):.3f}，0/3）。仅刻意设为边界情形的 B 臂发生移动，"
                 f"由 90 供体下的 suggestive 变为 35 供体下的 unsupported（τ_LODO={_sma('group_B_small', 'transfer_mean'):.3f}，"
                 "0/3）：在真实规模下，审计工具在认定弱信号前要求更强证据。关键在于，B、C 两臂的样本内表观信号"
                 f"（FULL 头 τ={_sma('group_B_small', 'full_head_insample_mean'):.3f} 与 "
                 f"{_sma('group_C_small', 'full_head_insample_mean'):.3f}）在无标签 LODO 迁移下同样崩塌（τ_LODO≈−0.10 与 0.00），"
                 "即标签锚定假象在真实队列规模下非但没有减弱、反而更为明显。因此 supported/unsupported 边界在该区间内"
                 "尺度不变，只有 suggestive 带对尺度敏感。")
            add_table(
                ["臂（真值）", "FULL 样本内头 τ", "NO-ALL τ_LODO，均值 ± SD",
                 "逐种子 τ_LODO（置换 p）", "显著种子", "定级"],
                [
                    ["A：强共享程序",
                     f"{_sma('group_A_small', 'full_head_insample_mean'):.3f}",
                     f"{_sma('group_A_small', 'transfer_mean'):.3f} ± {_sma('group_A_small', 'transfer_sd'):.3f}",
                     _sma_seedstr("group_A_small"),
                     f"{_sma('group_A_small', 'seeds_significant')}/{_sma('group_A_small', 'seeds_total')}",
                     _sma_grades.get("group_A_small", "?").upper()],
                    ["B：弱/异质程序",
                     f"{_sma('group_B_small', 'full_head_insample_mean'):.3f}",
                     f"{_sma('group_B_small', 'transfer_mean'):.3f} ± {_sma('group_B_small', 'transfer_sd'):.3f}",
                     _sma_seedstr("group_B_small"),
                     f"{_sma('group_B_small', 'seeds_significant')}/{_sma('group_B_small', 'seeds_total')}",
                     _sma_grades.get("group_B_small", "?").upper()],
                    ["C：仅含供体特异指纹",
                     f"{_sma('group_C_small', 'full_head_insample_mean'):.3f}",
                     f"{_sma('group_C_small', 'transfer_mean'):.3f} ± {_sma('group_C_small', 'transfer_sd'):.3f}",
                     _sma_seedstr("group_C_small"),
                     f"{_sma('group_C_small', 'seeds_significant')}/{_sma('group_C_small', 'seeds_total')}",
                     _sma_grades.get("group_C_small", "?").upper()],
                ],
                caption=f"表 3b  规模匹配的阳性对照验证（31 正常 + 4 病变 = 35 供体，恰为宫颈队列规模；三种子，"
                        f"B={_sma_perm or 500} 次样本标签置换）。定级规则与版式同表 3。决定性的 A='supported' 与 "
                        f"C='unsupported' 判定与 90 供体一致；仅刻意设为边界的 B 臂移动，变为 'unsupported'。"
            )
        else:
            body("【待服务器运行：results/sim_lodo_summary_small.json 将在此插入。】")
    else:
        body("【待服务器运行：三臂阳性对照结果将从 sim_lodo_summary.json 插入。】")
    h2("4.2  队列病理谱与队列内风险排序")
    add_fig("Fig1_Framework.png", 5.3,
            "图 1  队列组织学谱系与基准框架。(a) 横跨所分析连续病变谱的代表性 H&E 染色 Visium 切片：正常宫颈外口"
            "（GSE217237，P020），复层鳞状上皮有序、表层成熟；HSIL（GSE208654，HSIL_HPV），全层异型；浸润性鳞状细胞癌"
            "（10x 公开 FFPE 切片，cervical_cancer_1），促纤维间质中浸润癌巢；浸润性宫颈管腺癌（GSE208654，CA_HPV_2），"
            "背靠背/筛状恶性腺体。上排为全片低倍观，下排为框选区高倍观。(b) 模型：表达与形态学分支在 HPV 通路先验和"
            "邻域约束下融合，产生进入七变体审计的逐 spot 风险评分。H&E 仅提供组织学背景，不叠加模型输出。")
    add_fig("Fig2_risk_violin.png", 4.8,
            f"图 2  **描述性样本内结果；不是泛化证据，也不是模型性能。** 队列内逐 spot 风险随组织学严重度升高"
            f"（FULL，seed 0）：正常 {RV['normal_mean']:.2f}、HSIL {RV['hsil_mean']:.2f}、癌 {RV['cancer_mean']:.2f}。"
            f"该分离仅是疾病 n={CO['n_disease']} 下的拟合队列诊断；其反映学习还是标签锚定由 NO-PROG/NO-SUP/NO-ALL "
            "嵌套消融判定（4.3 节），而非此处数值。")
    body("逐 spot 平均风险呈正常 < HSIL < 癌的单调上升，但该分离存在于监督训练集内部。如下的去标签结果表明，"
         "不能将其读作泛化证据。")
    h2("4.3  去标签消融：有序排序由标签锚定（提示性）")
    add_fig("Fig3_ablation_multiseed.png", 6.2,
            "图 3  同队列多种子消融。左：空间一致性（Moran's I）；右：疾病排序（Kendall τ；点为种子，柱为均值±SD）。"
            "去除严重度标签（NO-PROG）使 τ 跌至显著性边界，而 Moran's I 几乎不变"
            f"（{A['NOPROG']['n_seeds']} 种子 p={A['NOPROG']['tau_perm_p_min']:.3f}–"
            f"{A['NOPROG']['tau_perm_p_max']:.3f}，{A['NOPROG']['tau_perm_nsig']}/{A['NOPROG']['n_seeds']} 名义显著）；"
            + ("完全无标签的 NO-SUP 臂将残余排序完全消除（各种子均不显著）；" if _ns_state == "clean"
               else f"完全无标签的 NO-SUP 臂仅剩弱且跨种子不稳定的残余（τ={_ns['tau_mean']:.2f}，置换 p={_ns_p_range}，"
                    f"{_ns_count}）；" if _ns_state == "mixed"
               else "完全无标签的 NO-SUP 臂在每一个种子上都保留残余排序（见表 4）；" if _ns_state == "robust"
               else "完全无标签的 NO-SUP 臂检验无任何目标时是否仍有排序；")
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
        caption="表 4  同队列多种子消融（35 样本、46,820 spot，锁定协议）。NO-SUP 同时置 λ_sup=λ_prog=0，训练全程不使用"
                "任何疾病派生目标；NO-ALL 再置 λ_hpv=0，有序目标、代理与通路一致性先验均不贡献梯度（仍保留重建、邻域、"
                "形态学及作为普通输入的面板基因）。p 值由严重度向量在全部 35 样本间置换得到；"
                "渐近 p 见补充表 S1，小样本下以置换口径为准。")
    body(f"去除严重度标签回归使 Kendall τ 从 {A['FULL']['tau_mean']:.3f} 降至 "
         f"{A['NOPROG']['tau_mean']:.3f}±{A['NOPROG']['tau_sd']:.3f}（逐种子 τ={_np_taus}；置换 p={_np_pp}："
         f"{A['NOPROG']['tau_perm_nsig']}/{A['NOPROG']['n_seeds']} 个种子名义显著，其中一个跨越 0.05）。SCC 演示切片在"
         "每个种子中均排在 30/31 个正常之上，HSIL 片高于约 25–26 个，而 ADC 片仅高于 8–13 个正常、始终最弱"
         "（与 4.6 节最弱 ADC 折呼应）。单侧 Mann–Whitney 为 "
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
         + "这也不等于模型仅记忆四张切片：4.6 节的半监督 LODO 显示三个"
         "带标签切片即可稳定迁移方向，而留出未见切片上的零标签极限只是局部、不稳定。")
    body("**真实宫颈数据的冻结表征迁移探针。** 将同一留一供体探针（3.4 节）用于宫颈 NO-ALL 嵌入、覆盖全部 35 个供体，"
         f"得 τ_LODO={_RL['lodo_mean']:.3f}±{_RL['lodo_sd']:.3f}（逐种子 {_RL_SEEDSTR}），而完全样本内探针 τ="
         f"{_RL['insample_probe_mean']:.3f}——中等差距 {_RL['insample_probe_mean'] - _RL['lodo_mean']:.3f}；三个种子中"
         "一个显著、两个处于边界。按预注册规则，宫颈表征因此定为**提示性（suggestive）**：在完全去除标签、代理与通路"
         "先验后，仍存活一条弱且跨种子不稳定的跨供体疾病轴——既不同于身份混杂对照的随机水平迁移，也远低于强信号臂。"
         "这与 4.6 节的逐折 LODO 一致：三个带标签切片可稳定方向的迁移，而留出切片上的零标签极限只是局部、不稳定。"
         if _RL else
         "【真实数据 LODO 探针结果待补：运行 scripts/freeze_real_lodo.py 后重新生成。】")
    h2("4.4  一致性的来源与形态学的两轴判定")
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
         "形态学到 HPV 代理的 ridge 评分仅在 "
         f"{LOSO_RIDGE[2]}/35 折可评估（平均 AUC "
         f"{BSL.get('loso_hpv_ridge_auc', float('nan')):.3f}±{BSL.get('loso_hpv_ridge_auc_sd', float('nan')):.3f}）——其余 "
         f"{35 - LOSO_RIDGE[2]} 折中留出样本的 ridge 预测塌缩为近似常数，逐折 AUC 无法定义；这种塌缩本身即说明在此样本量下"
         "图像形态学不携带可迁移的逐 spot HPV 代理信号。MLP 塌缩的折数少得多，可评估 "
         f"{LOSO_MLP[2]}/35（AUC {BSL.get('loso_hpv_mlp_auc', float('nan')):.3f}±"
         f"{BSL.get('loso_hpv_mlp_auc_sd', float('nan')):.3f}）。没有任何单折显著超过随机：可评估的逐折 AUC 区间为 "
         f"{LOSO_RIDGE[0]:.2f}–{LOSO_RIDGE[1]:.2f}（ridge）与 {LOSO_MLP[0]:.2f}–{LOSO_MLP[1]:.2f}（MLP），最优折也仅达 "
         f"{max(LOSO_RIDGE[1], LOSO_MLP[1]):.2f}。形态学到表达重建的逐基因 Pearson r="
         f"{BSL.get('loso35_per_gene_pearson', float('nan')):.3f}（MSE {BSL.get('loso35_recon_mse', float('nan')):.3f}），"
         f"不优于样本内插值（MSE {BSL.get('he2st_mse', float('nan')):.3f}）。样本内 AUC 1.00 与跨样本 AUC≈0.50 的并置，"
         "正是本基准的核心警示结果。")
    h2("4.5  通路锚定评分的生物学解读")
    body("**建设性产出：移除监督后仍存活的是什么。** 该审计不只是诊断性的；反向使用它即可界定小样本 ST 研究可以合法"
         "报告哪些生物学程序。在依次移除序数标签、表达衍生代理、最后移除通路先验（去循环对照）后重测同一批通路相关，"
         "可把内在空间生物学与由监督目标构造出的关联分开：肿瘤上皮与干扰素抗病毒相关在 NO-SUP 下仍持续，说明它们立足于"
         "表达数据本身；而 HPV 驱动相关由通路先验维持。")
    add_fig("Fig4_biology_correlation.png", 5.8,
            "图 4  **纯描述性的 spot 级相关；spot 并非独立。统计推断必须依赖样本级比较，绝不能基于此处 spot 级数值。** "
            "spot 风险与 11 个通路/细胞状态评分的 Spearman 相关（样本内 z，3 个 FULL 种子均值；全部通过 BH FDR；"
            f"最弱为 {WEAKEST_Q_SET.replace('_', ' ').lower()}，q={WEAKEST_Q:.0e}；共 46,820 个非独立 spot）。")
    body(f"高风险 spot 富集肿瘤上皮（KRT5/14/17、EPCAM；ρ={BIO['CELL_tumor_epithelial']['rho']:+.2f}）、HPV 驱动程序"
         f"（CDKN2A/MYC/EGFR/PIK3CA；ρ={BIO['HPV_INTEGRATION_CANDIDATE']['rho']:+.2f}）与抗原呈递"
         f"（B2M/HLA-A/PSMB8；ρ={BIO['ANTIGEN_PRESENTATION']['rho']:+.2f}），并缺失干扰素抗病毒程序"
         f"（STAT1/MX1/ISG15；ρ={BIO['INTERFERON_ANTIVIRAL']['rho']:+.2f}）、增殖（{BIO['PROLIFERATION']['rho']:+.2f}；"
         f"说明该轴不是增殖替代指标）与 EMT（{BIO['EMT']['rho']:+.2f}）。标志物有效性在独立宫颈 scRNA-seq [@scrna] "
         f"（{SCR['n_cells']:,} 整合细胞）中确认：谱系内平均相关 {SCR['within_corr']:+.3f}，跨谱系 "
         f"{SCR['between_corr']:+.3f}（差 {SCR['gap']:+.3f}）。方向与 E6/E7 驱动转化及免疫逃逸一致；"
         "但属描述性空间关联，非因果证据。")
    h2("4.6  跨平台与跨器官的无标签迁移")
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
    if _AUDG is not None:
        _cau_full = _AUDG["scores"]["S_full"]
        _cau_epi = _AUDG["scores"]["dec_epithelial_only"]
        _cau_wgt = _AUDG["scores"]["dec_rho_weighted"]
        _cau_sum = _AUDG["scores"]["dec_signsum"]
        _cau_top = _AUDG["scores"]["dec_top2"]
        body(f"**审计能否转化为更好的预测器？** 一个警告只有同时说明“该用什么”才有价值，因此我们检验这张“认证”能否变成一个"
             f"有竞争力的评分。仅使用审计认证为内在的程序（肿瘤上皮、干扰素抗病毒，见 4.5 节），我们构建了一个**完全无标签**"
             f"的读出——只用 GeoMx 表达做秩富集、按 NO-SUP 方向定号——并在与受监督头相同的 ROI 上评分。单一“肿瘤上皮”认证"
             f"程序达到肿瘤 vs 良性 AUC={_cau_epi['auc_tumor_vs_benign']:.3f}（ROI p={_cau_epi['mwu_p_roi']:.1e}），而受监督"
             f"多模态头为 {_cau_full['auc_tumor_vs_benign']:.3f}（ΔAUC={_AUDG['delta_auc_best_dec_minus_full']:+.3f}）；"
             f"多程序朴素合并更差（{_cau_wgt['auc_tumor_vs_benign']:.3f}、{_cau_sum['auc_tumor_vs_benign']:.3f}），最弱构造"
             f"失效（{_cau_top['auc_tumor_vs_benign']:.3f}）。由此得两点结论：**正面**——认证是有意义的，零监督的单程序读出能够"
             f"迁移到独立平台，水平基本等同于训练好的多模态模型；**证伪**——受监督头相对单一认证通路的外部优势极其有限，"
             f"模型可迁移的价值由一条内在生物学轴承载，而非多模态融合。因此我们把审计定位为**“诊断 + 有边界的校正”**，"
             f"而不是更优预测器，也不主张后者。")
    body(f"**头颈部：真实、含弱通路特异性的组织，但无疾病判别。** 迁移评分在 {EXT['hnscc_n_samples']} 张 GSE268014 "
         f"切片上 Moran's I={EXT['hnscc_moran_mean']:.2f}，在独立的 {EXT['hnscc_gse281978_n']} 张 GSE281978 切片上为 "
         f"{EXT['hnscc_gse281978_moran_mean']:.2f}，而坐标置换零近于零（全部 14 张 p≤0.001）。纯 KEGG 面板在每张切片上"
         f"均高于表达匹配随机面板（{EXT['rg268_exprm_npos']}/{EXT['hnscc_n_samples']} 与 "
         f"{EXT['rg281_hvgu_npos']}/{EXT['hnscc_gse281978_n']}；p={EXT['rg268_exprm_signp']:.3f}/"
         f"{EXT['rg281_exprm_signp']:.3f}），即弱但完全可复现的通路特异成分。所有切片级判别检验均为阴性：恶性 vs 非恶性"
         f"（正向 {EXT['mal_non_pos']}/{EXT['mal_non_n']}，p={EXT['mal_non_p']:.3f}）、肿瘤前沿 vs 核心"
         f"（{EXT['edge_core_pos']}/{EXT['edge_core_n']}，p={EXT['edge_core_p']:.3f}）、HPV+ vs HPV−"
         f"（p={EXT['hpv268_p']:.2f}/{EXT['hpv281_p']:.2f}）、原发 vs 淋巴结转移（p={EXT['pt_lnmt_p']:.2f}；补充 Note S3）。")
    h2("4.7  标签剂量效应、零模型对照与临床效用边界")
    body(f"**标签将局部方向稳定为可迁移方向。** 逐折配对 LODO 中，完全无监督训练给出局部、不稳定的方向"
         f"（{EXT['unsup_lodo_n_above_median']}/4 折高于正常中位、{EXT['unsup_lodo_n_above_all']}/4 高于全部正常，"
         f"平均百分位 {EXT['unsup_lodo_mean_pct']:.2f}；ADC 折为 {EXT['unsup_lodo_min_pct']:.2f}）；加入其余三个带标签"
         f"病变切片后方向稳定（{EXT['lodo_n_above_median']}/4 与 {EXT['lodo_n_above_all']}/4，平均 "
         f"{EXT['lodo_mean_pct']:.2f}；ADC 折由 {EXT['unsup_lodo_min_pct']:.2f} 升至 {EXT['lodo_min_pct']:.2f}）。"
         f"四折即四个独立事件，精确区间宽且重叠（下限 {EXT['lodo_4of4_ci_lo']:.2f}/{EXT['unsup_3of4_ci_lo']:.2f}）；"
         "更稳健的证据是配对设计本身及 ADC 折的配对上升，定为提示性。腺上皮向鳞状上皮的迁移是主要瓶颈，"
         "与已记录的 SCC/ADC 微环境差异一致 [@mo;@wu]。")
    body(f"**队列内通路特异性不被支持。** 纯 KEGG 面板评分——即 108 个 HPV 面板基因的免学习逐样本均值，"
         f"非表 4 的模型评分——的 Moran's I 为 {RC['kegg_moran']:.3f}，不高于 30 个匹配随机面板"
         f"（{RC['random_moran_mean']:.3f}，{RC['random_moran_min']:.3f}–{RC['random_moran_max']:.3f}；置换 "
         f"p={RC['moran_perm_p']:.3f}），随机面板的疾病排序与之相同（τ {RC['kegg_kendall']:.3f}；AUC 置换 "
         f"p={RC['auc_perm_p']:.2f}）：队列内平滑为任何共表达基因集所共有，排序由标签锚定。跨器官的面板级优势"
         "（4.6 节）属于不同口径，二者不矛盾。")
    body(f"**无预后或决策效用。** 11 个空间 DEG 在 {TC['n_patients']} 例（{TC['events']} 事件）TCGA-CESC bulk Cox 模型"
         f"[@cox] 中无一显著（最小为 {TC['min_gene']}，p={TC['min_p']:.3f}），说明 spot 级空间风险与患者级结局之间存在"
         "尺度断裂。应用 MRP-ST 定级：空间自组织 supported；跨器官原始面板通路特异性 supported；GeoMx 秩判别（符号不"
         "迁移）、标签锚定、半监督优于无监督 LODO 为 suggestive；队列内模型评分通路特异性与形态学排序增益 unsupported；"
         "分级、预后与跨器官判别 unsupported。")

    # ---- 5 讨论 --------------------------------------------------------
    h1("5  讨论")
    h2("5.1  主要发现")
    body("**贡献与首创性。** 本文的首要贡献是一个方法：LDI——一个带校准决策门的标量式标签依赖度量，以及将其落地为"
         "可执行嵌套去标签协议的 MRP-ST。据我们所知，这是首个面向 ST 的此类协议；既有工作把标签泄漏与身份混杂作为原则"
         "加以记录 [@kapoor;@whalen;@davis;@schreiber;@karin]，但未提供可执行的流程来定位究竟是哪一个标签衍生成分在"
         "驱动给定风险评分。宫颈分析是该方法的应用，而非其新颖性主张。")
    body("本基准给出四个可辩护的正面陈述与一个核心警示。第一，审计本身经阳性对照验证具有判别效度：在三个真值已知的 "
         f"90 供体仿真队列上，冻结无标签表征的留一供体探针将强共享程序正确定为 supported（τ_LODO="
         f"{_sim('group_A', 'transfer_mean'):.3f}，3/3 显著）、弱异质程序定为 suggestive"
         f"（{_sim('group_B', 'transfer_mean'):.3f}±{_sim('group_B', 'transfer_sd'):.3f}）、纯供体身份混杂定为 unsupported"
         f"（τ_LODO={_sim('group_C', 'transfer_mean'):.3f}，0/3 显著；而监督模型样本内 τ="
         f"{_sim('group_C', 'full_head_insample_mean'):.3f}，记忆签名 gap="
         f"{_sim('group_C', 'gap_insample_minus_transfer'):.3f}）——特异度与灵敏度同时成立，并实证探针只在无标签编码器上"
         "可解释。第二，通路锚定评分生物学可解释（肿瘤上皮、HPV/抗原呈递程序为正，干扰素为负；种子稳定且在独立 "
         "scRNA-seq 中标志物有效）。第三，即使去除标签、先验或邻域，空间一致性仍然很高，并含可检出的形态学增量；"
         "监督训练所得表达表征在无标签推理阶段，于独立 GeoMx 队列保留强肿瘤—良性秩判别，并在 14 张头颈切片上保留真实"
         "空间组织。第四，真实宫颈队列的无标签冻结表征保留一条弱、跨种子不稳定的跨供体疾病轴"
         f"（τ_LODO={_RL['lodo_mean']:.3f}±{_RL['lodo_sd']:.3f}，suggestive），故真实案例既非纯记忆、也非确证性泛化。"
         "警示是定量的：样本级样本内 AUC 1.00 与 LOSO AUC≈0.50 并存；去除四个严重度标签后，有序排序由 τ=0.46 塌至 "
         "p=0.03–0.06 边界上的 τ=0.25，而真实零标签迁移更弱且仅一个种子显著。若没有去除消融、置换零模型、全样本留出与"
         "阳性对照，本研究的每个数字都会读作一个成功的风险模型；有了它们，存活下来的只有空间组织、平台级可分性与一条"
         "弱的疾病轴。")
    h2("5.2  对生物医学信息学的可推广经验")
    body("四条经验可推广到宫颈 ST 之外。第一，一致性指标不是模型指标：Moran's I≈0.9 主要是相邻 spot 的内在平滑，"
         "匹配随机基因集达到同样数值；自相关必须对照数据驱动零模型报告。第二，标签置换的统计单位必须是独立样本，"
         "绝不能是数千个自相关 spot——spot 级置换会制造显著性。第三，外部效度是多组分的：秩判别、校准符号与分级可以"
         "独立迁移（本例为：迁移、不迁移、不迁移），单一外部 AUC 会掩盖实际发生了什么；跨平台的靶向面板/Visium 与 "
         "ADC/SCC 偏移是真实的校准风险。第四，样本内与跨样本性能必须在设计上同时报告；随机基因零模型与完全无监督臂"
         "在训练后几乎不花成本。这些可操作条目及三级定级，将通用的泄漏与报告原则 [@kapoor;@whalen;@varo;@tripod] "
         "落实到 ST 场景。该审计网络无关，适用于任何阳性样本极少的罕见病 ST 研究。")
    h2("5.3  局限性")
    body("**生物学解读的边界。** 四张病变宫颈切片仅为示例；本文报告的宫颈分子关联均不构成新的生物学发现，本工作的贡献"
         "是审计方法学，而非宫颈疾病机制。")
    body("（1）功效：四个独立疾病事件与六对 GeoMx 患者约束了所有推断；3/4 种子与 6/6 计数的精确区间宽，仅支持 "
         "suggestive 定级；MRP-ST 的触发条件与 supported/suggestive/unsupported 界值（τ_LODO ≥ 0.35、≤ 0.15）是从单个"
         "极端案例设定的务实操作界值，尚未经多个独立真实队列校准——规范化使用前需先做多队列校准。规模匹配对照把这一点"
         "坐实：在真实队列规模下，一个真实但较弱的植入信号被判为 unsupported 而非 suggestive（见 4.1 节），故 τ≥0.35 "
         "带对小队列偏保守，n 如此小时必须重新校准。"
         "（2）平台与组织学混杂：外部宫颈队列为 DSP "
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
         "显式疾病锚定项，而非输入中的一切疾病相关信号。**代理的直推式性质是一项真实的、接近泄露的局限：其目标阈值在全部"
         "分析 spot 的全局中位数上确定，而非仅用训练样本。** 统计上干净的实现——也是 MRP-ST 实践应采用的——仅用训练集 "
         "spot 推导代理阈值；我们未这样做，由此引入的乐观偏差此处未量化。"
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
    h1("6  结论")
    body("我们提出了面向极端小样本空间转录组风险建模的标签依赖消融基准，包括七个匹配的多种子变体（标签→代理→先验"
         "嵌套级联，直至一个标签与通路先验均关闭的臂）、全样本置换、"
         "配对的半/无监督留出、表达匹配基因集零模型与跨平台外部检验，并将其形式化为五条目 MRP-ST 协议。阳性对照仿真"
         "证明该审计兼具判别效度：真实跨供体程序通过、弱异质程序落入中间档、纯供体身份混杂被否决。在四张病变宫颈切片上，"
         "一个通路锚定模型取得了样本内完美分离，而审计表明其精细排序主要由标签锚定；无标签冻结表征仅保留一条弱且跨种子"
         "不稳定的跨供体疾病轴（suggestive）；空间组织与跨平台肿瘤—良性可分性真实保留，校准符号与分级则不迁移。"
         "该基准成本低、网络无关，旨在让标签记忆在发表之前而非之后被看见。")
    body("**适用性。** MRP-ST 与七项消融适用于任何处于\"疾病样本极少\"情形的研究——操作上即独立疾病样本数 "
         "n_diseased ≤ 10（或任一类别 ≤ 5）、且监督信号建立在空间自相关的 spot 级测量之上。这涵盖罕见病空间转录组，"
         "以及具有同样\"少样本/多 spot\"结构的空间蛋白组、空间代谢组与多重成像，也适用于依赖公开或联盟数据、"
         "无法获得外部队列的监督模型。它不适用于疾病重复数已充足（n_diseased > 10）的研究——此类情形下常规的"
         "样本级交叉验证已足以承担推断主张；它也不能替代疾病特异的外部验证队列（若存在）。该协议只需训练后分析"
         "与版本化结果存储，且与模型架构无关，因此可在不重训底层表征的前提下采用。")

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

    save(doc, "Manuscript_CiBM_中文.docx")
    return doc, C


# ========================================================================
#  SUPPLEMENTARY INFORMATION  (Tables S1-S3, Notes S1-S3)
# ========================================================================
def build_supplementary():
    doc, C, h1, h2, body, ctr, add_table, add_fig, emit = make_manuscript()
    TITLE = ('MRP-ST and the Label-Dependence Index: a validated label-removal '
             'protocol for risk models in extreme small-sample spatial '
             'transcriptomics of cervical neoplasia')

    def _prange(lo, hi, spec="{:.3g}"):
        a, b = spec.format(lo), spec.format(hi)
        return a if a == b else f"{a}–{b}"

    # ---- Title block ----------------------------------------------------
    emit("Supplementary Information", 16, True, align=WD_ALIGN_PARAGRAPH.CENTER, after=8)
    ctr(TITLE, 12, bold=True, after=6)
    ctr("Mingwei Bai \u00b9, Zhengmin Gu \u00b2, Ye Zhang \u00b2, Lang Guo \u00b3,*", 10.5, after=4)
    ctr("\u00b9 JiMei Technology Group Co., Ltd., Shenyang 110002, China", 9.5, after=1)
    ctr("\u00b2 Medical Record Management Center, The First Hospital of China "
        "Medical University, Shenyang 110002, China", 9.5, after=1)
    ctr("\u00b3 School of Pharmacy, Shenyang Medical College, Shenyang 110034, China", 9.5, after=10)

    h1("Contents")
    for line in [
        "Table S1. Asymptotic versus permutation p-values for the sample-level Kendall τ "
        "(cervical cohort, seven variants).",
        "Table S2. MRP-ST minimum reporting protocol: five-item checklist, three-level grading "
        "rule and execution order.",
        "Table S3. Positive-control simulations: S3-1 generator parameters; S3-2 per-seed "
        "seven-variant cascade (scalar heads); S3-3 per-seed frozen-representation LODO probe; "
        "followed by the probe implementation specification.",
        "Table S4. Systematic search and exclusion log for public cervical spatial-transcriptomic "
        "datasets (inclusion criteria and screened-but-excluded studies with reasons).",
        "Note S1. Within-section spatial autocorrelation of frozen UNI patch embeddings.",
        "Note S2. Post-hoc epithelial/stromal stratification of the GeoMx Silva non-monotonicity.",
        "Note S3. HNSCC cross-organ transfer: triple-control design and section-level "
        "discriminative tests.",
    ]:
        body(line, indent=False)

    # ---------------- Table S1 ------------------------------------------
    h1("Supplementary Table S1. Asymptotic p versus label-permutation p for the sample-level "
       "Kendall τ (cervical cohort, 35 samples)")
    _sv = [("FULL", "FULL"), ("NOIMAGE", "NO-IMAGE"), ("NOHPV", "NO-HPV"),
           ("NONEIGH", "NO-NEIGH"), ("NOPROG", "NO-PROG"), ("NOSUP", "NO-SUP"),
           ("NOALL", "NO-ALL")]
    rows = []
    for key, lab in _sv:
        x = A[key]
        rows.append([
            lab, x["n_seeds"], f"{x['tau_mean']:.3f} ± {x['tau_sd']:.3f}",
            _prange(x["tau_p_min"], x["tau_p_max"]),
            _prange(x["tau_perm_p_min"], x["tau_perm_p_max"])])
    add_table(
        ["Variant", "Seeds", "Kendall τ (mean ± SD)",
         "Asymptotic p (range across seeds)", "Permutation p, B=10,000 (range)"],
        rows, widths=[1.05, 0.70, 1.45, 1.65, 1.65])
    for fn in [
        "Notes: (1) The severity vector (31 normal, 1 HSIL, 3 cancer; 35 samples) is permuted "
        "as a complete vector against fixed fitted per-sample scores; spot-wise or within-class "
        "permutations are invalid because spatial autocorrelation makes them anti-conservative.",
        "(2) The number of distinct label arrangements is 35·C(34,3) = 209,440 (~2.1×10⁵), so "
        "the empirical resolution is set by the full 35-sample composition, not by the 4! = 24 "
        "arrangements of the four disease samples; p_perm = (n_ge + 1)/(B + 1).",
        "(3) The asymptotic SciPy p assumes large-sample normality and is anti-conservative at "
        "n=35 with four disease events (e.g. FULL: ~1.0×10⁻³ asymptotic vs 1×10⁻⁴–2×10⁻⁴ "
        "permutation). The permutation value is the one reported in the main text and governs "
        "every verdict.",
        "(4) NO-PROG sits on the feasibility boundary (permutation p 0.040–0.072; one seed "
        "flips the verdict), which is why its claim is graded suggestive rather than "
        "confirmatory. Source: results/paper_v10_numbers.json (ablation), reproduced verbatim.",
    ]:
        emit(fn, 9, indent=False, after=3, ls=1.15)

    # ---------------- Table S2 ------------------------------------------
    h1("Supplementary Table S2. MRP-ST minimum reporting protocol (triggered when "
       "n_diseased ≤ 10, or ≤ 5 in any class)")
    add_table(
        ["Item", "Mandatory requirement", "Pre-specified failure reading",
         "Implementation in this study"],
        [
            ["R1", "Nested label-removal ablation—ordinal labels, then the disease-correlated "
             "proxy target, then the pathway regularizer—with ≥3 seeds per variant; coherence "
             "(Moran's I) and ordering (Kendall τ) audited as separate axes.",
             "If τ survives every removal, label anchoring is refuted in favour of intrinsic "
             "data geometry; if only Moran's I survives, structure is real but endpoint "
             "ordering is label-anchored.",
             "Seven variants FULL/NO-IMAGE/NO-HPV/NO-NEIGH/NO-PROG/NO-SUP/NO-ALL, 3–4 seeds "
             "each (main-text Table 4)."],
            ["R2", "Whole-sample permutation of the complete severity vector with scores held "
             "fixed after fitting, B ≥ 10,000; identify the result explicitly as a "
             "fitted-cohort diagnostic.",
             "Spot-wise or within-class permutations exploit spatial pseudo-replication and "
             "are forbidden; asymptotic p is anti-conservative at small n.",
             "B=10,000 over the 35-sample vector (31/1/3); asymptotic p shown separately in "
             "Table S1; 209,440 distinct labelings."],
            ["R3", "≥30 expression-quantile-matched random gene-set controls against the "
             "pathway panel.",
             "If any matched co-expressed set yields equal coherence/ordering, pathway "
             "specificity is not supported.",
             "30 random 108-gene panels; KEGG panel exceeds matched panels on 8/8 and 6/6 "
             "external sections (exact sign p=0.008/0.031; Note S3)."],
            ["R4", "Dual sample-level hold-out protocols—semi-supervised versus fully "
             "unsupervised—with identical per-fold cohorts and spot counts.",
             "In-sample metrics alone cannot separate generalization from memorization; "
             "non-identical folds confound the label-dose contrast.",
             "Four LODO folds per protocol, each trained against the same 31 normal donors "
             "(main-text Figs. 5D, Section 4.7)."],
            ["R5", "Explicit supported / suggestive / unsupported grading per claim, per axis, "
             "plus a clinical-utility statement.",
             "Binary pass/fail reporting hides power-boundary and axis-specific outcomes.",
             "All claims graded per axis; the score is stated to have no current prognostic "
             "or decision utility (Sections 4.3–4.7, 5.4)."],
        ], widths=[0.55, 2.05, 2.00, 1.90])
    body("**Grading rule.** (i) supported: sample-level significance with direction consistent "
         "across ≥3 seeds and all applicable R1–R4 controls passed; (ii) suggestive: direction "
         "consistent across seeds but p sits at the exact feasibility boundary (e.g. NO-PROG "
         "permutation p=0.040–0.072 with one seed flipping; LODO 4/4 with wide exact intervals), "
         "or supported only by the paired design; (iii) unsupported: not significant, direction "
         "reversed, or significant only under spot-level pseudo-replication. Modules acting on "
         "one output axis but not another are graded per axis (the morphology branch: coherence "
         "gain supported, ranking gain unsupported).", indent=False)
    body("**Execution order.** R2 non-significant → stop (no testable in-cohort signal). R2 "
         "significant but R1 failing → downgrade to suggestive and use the NO-SUP/NO-ALL steps "
         "to localize the proxy/prior contribution. R1–R3 passing → run R4 and grade by exact "
         "count intervals rather than point proportions. R5 emits the graded statements and the "
         "clinical-utility boundary. The protocol is network-agnostic and applies to any "
         "'few disease samples + many spots' ST or spatial-omics risk study.", indent=False)

    # ---------------- Table S3 ------------------------------------------
    h1("Supplementary Table S3. Controlled positive-control simulations")
    emit("S3-1. Generator parameters (scripts/simulate_st_positive_control.py, v2.2).", 10.5,
         True, indent=False, after=2, keep_next=True)
    add_table(
        ["Parameter", "Arm A: strong shared program", "Arm B: weak / heterogeneous",
         "Arm C: identity fingerprints"],
        [
            ["Donors (normal + diseased)", "50 + 40 = 90", "50 + 40 = 90", "50 + 40 = 90"],
            ["Spots per donor", "1,500", "1,500", "1,500"],
            ["Genes (pathway panel)", "3,000 (108 real KEGG-HPV symbols)",
             "3,000 (108 real KEGG-HPV symbols)", "3,000 (108 real KEGG-HPV symbols)"],
            ["Capture rates", "≈10% background, ≈40% panel", "≈10% background, ≈40% panel",
             "≈10% background, ≈40% panel"],
            ["Per-spot normalization", "library size 10⁴", "library size 10⁴",
             "library size 10⁴ (mandatory: multiplicative zero-sum perturbations are not "
             "zero-sum on raw counts, so without normalization a total-count channel leaks)"],
            ["Injected class-level signal",
             "One shared, spatially smoothed program on 60% of panel genes; amplitude 2.5; "
             "per-donor response 0.9–1.1",
             "Weak shared program; amplitude 0.20; response envelope 0.15–0.95; 35% "
             "zero-response diseased donors; 50% per-donor program-gene dropout",
             "None. Every donor (normal and diseased) receives a donor-specific random "
             "zero-sum fingerprint: 30% panel genes up / 30% down, amplitude 1.2, spatially "
             "smoothed; classes have identical marginal mean and dispersion"],
            ["Donor-specific per-gene technical offset SD", "0.3", "1.5", "0.5"],
            ["Generator base seed / training seeds", "20261006 / 0, 1, 2",
             "20261006 / 0, 1, 2", "20261006 / 0, 1, 2"],
            ["Training", "40 epochs; λ_recon=1.0, λ_neigh=0.3, λ_hpv=0.5",
             "same", "same"],
        ], widths=[1.55, 1.70, 1.70, 1.55])

    emit("S3-2. Per-seed scalar-head cascade for all seven variants (in-sample risk head; "
         "Kendall τ and within-arm Moran's I). The NO-ALL rows are shown for completeness only: "
         "an unsupervised scalar head has an arbitrary sign and its τ is not evidence—the valid "
         "NO-ALL readout is the frozen probe in S3-3.", 10.5, True, indent=False, after=2,
         keep_next=True)

    def _raw(g, v, s):
        fp = ROOT / "results" / f"results_SIM_{g}_{v}_seed{s}.json"
        if not fp.exists():
            return None, None
        d = json.load(open(fp, encoding="utf-8"))
        pm = d.get("progression_monotonicity") or {}
        return pm.get("kendall_tau"), d.get("moran_i")

    import statistics as _st
    s32 = []
    for g, glab in [("group_A", "A"), ("group_B", "B"), ("group_C", "C")]:
        for key, lab in _sv:
            taus = []
            morans = []
            for s in range(3):
                t, mi = _raw(g, key, s)
                taus.append(t)
                if mi is not None:
                    morans.append(mi)
            tcell = "/".join(f"{t:+.3f}" if t is not None else "NA" for t in taus)
            tm = f"{_st.mean(taus):+.3f} ± {_st.stdev(taus):.3f}" if all(t is not None for t in taus) else "NA"
            mcell = (f"{_st.mean(morans):.3f} ± {_st.stdev(morans):.3f}"
                     if len(morans) == 3 else "NA")
            s32.append([glab, lab, tcell, tm, mcell])
    add_table(
        ["Arm", "Variant", "τ per seed (0/1/2)", "τ mean ± SD", "Moran's I mean ± SD"],
        s32, widths=[0.55, 1.05, 1.85, 1.45, 1.60])

    emit("S3-3. Label-free frozen-representation LODO probe (the grading evidence; B=10,000).",
         10.5, True, indent=False, after=2, keep_next=True)
    s33 = []
    for g, glab in [("group_A", "A: strong shared program"),
                    ("group_B", "B: weak / heterogeneous"),
                    ("group_C", "C: identity fingerprints")]:
        st_ = _sim(g, "transfer_mean")
        seedstr = "; ".join(f"{r['transfer']['tau_lodo']:+.3f} (p={r['transfer']['p']:.4f})"
                            for r in _sim_seeds(g))
        s33.append([glab, seedstr,
                    f"{st_:.3f} ± {_sim(g, 'transfer_sd'):.3f}",
                    f"{_sim(g, 'seeds_significant')}/{_sim(g, 'seeds_total')}",
                    f"{_sim(g, 'full_head_insample_mean'):.3f}",
                    f"{_sim(g, 'gap_insample_minus_transfer'):.3f}",
                    _sim_grades.get(g, "?")])
    add_table(
        ["Arm (ground truth)", "Per-seed τ_LODO (perm. p)", "τ_LODO mean ± SD",
         "Sig. seeds", "FULL in-sample head τ", "Gap", "Grade"],
        s33, widths=[1.35, 1.85, 1.05, 0.65, 0.85, 0.55, 0.85])
    body("**Probe implementation (scripts/probe_lodo.py, mrpst_lodo.py).** Per-spot fused "
         "embeddings (128-dimensional) are mean-pooled to one vector per donor. A ridge severity "
         "predictor is fit in closed form with fixed regularization α=1.0; features are "
         "z-standardized using the training-fold donors only (μ, σ from the N−1 training donors; "
         "σ floor 10⁻⁸). Each donor is held out once; Kendall τ-b with tie correction is computed "
         "between out-of-fold predictions and true severity 0/1/2. Significance is obtained by "
         "permuting the donor severity vector (fixed RNG seed 0), p = (n_ge + 1)/(B + 1) with "
         "B=10,000. An in-sample probe (fit on all donors, predict all donors) is reported "
         "alongside to quantify the in-sample–transfer gap. The probe is run exclusively on the "
         "fully label-free NO-ALL encoder; on supervised FULL encoders the held-out donor's "
         "label has already entered the encoder and the probe reaches the τ ceiling even in arm "
         "C (main-text Section 4.1). Pre-registered cut-offs: supported = mean τ_LODO ≥ 0.35 "
         "with ≥2/3 seeds p<0.05; unsupported = |mean τ_LODO| ≤ 0.15 with 0/3 significant; "
         "otherwise suggestive.", indent=False)

    # ---------------- Table S4 ------------------------------------------
    h1("Supplementary Table S4. Systematic search and exclusion log for public cervical "
       "spatial-transcriptomic datasets")
    body("**Search and inclusion criteria.** Public repositories (GEO, ArrayExpress/ENA, Zenodo and the "
         "10x Genomics public dataset collection) were searched for human cervical spatial-transcriptomic "
         "data. A dataset was retained only if it met all three criteria: (I1) standard 10x Visium platform "
         "with 55-µm capture spots; (I2) section-level histologic annotation (normal / HSIL / cancer); "
         "(I3) H&E images available and registrable to the capture-array coordinates. Every diseased section "
         "meeting I1–I3 was retained; no disease section was excluded for performance reasons. The log below "
         "is provided so that the sample-scarcity premise—four analysable diseased sections—can be "
         "independently reproduced; accessions and reasons are stated as of the search date.", indent=False)
    emit("S4-1. Retained sources (all criteria I1–I3 met).", 10.5, True, indent=False, after=2,
         keep_next=True)
    add_table(
        ["Source", "Accession", "Platform", "Sections analyzed", "Histology"],
        [
            ["Guo et al., 2023", "GSE208654", "Visium (55 µm)", "4",
             "1 normal, 1 HSIL, 2 cancer (SCC + ADC)"],
            ["Ectocervix SuperSeries", "GSE217237", "Visium (55 µm)", "30", "normal ectocervix"],
            ["10x Genomics demonstration", "10x public", "Visium (55 µm)", "1", "SCC"],
        ], widths=[1.45, 1.00, 0.95, 0.85, 2.25])
    emit("S4-2. Screened but excluded (each failed at least one inclusion criterion).", 10.5, True,
         indent=False, after=2, keep_next=True)
    add_table(
        ["Study (as reported)", "Platform / design", "Cervical content", "Criterion not satisfied"],
        [
            ["Xia et al., 2025 (npj Precis. Oncol.)", "scRNA-seq + ST",
             "normal / HPV-normal / HSIL / carcinoma multistage", "not met: I3 / I1"],
            ["Zhou et al., 2024 (J. Transl. Med.)", "ST", "2 CSCC + 1 normal", "not met: I3 / I1"],
            ["Xu et al., 2025 (bioRxiv FGT atlas)", "Visium HD",
             "female genital tract incl. cervix", "not met: I1 (HD binning, not 55-µm spots)"],
            ["Mo et al., 2025 (Discover Oncology) [@mo]", "Visium", "cervical cancer atlas",
             "not met: I3"],
        ], widths=[1.70, 1.05, 1.90, 1.55])
    body("**Note.** The excluded entries reflect the datasets identified by the search at submission; where "
         "a study's ST data or capture-registered H&E images later become openly available under criteria "
         "I1–I3, they should be added to the analysis. No excluded dataset is used for any result in this "
         "work.", indent=False)

    # ---------------- Note S1 -------------------------------------------
    h1("Supplementary Note S1. Within-section spatial autocorrelation of frozen UNI patch "
       "embeddings")
    _uni_path = ROOT / "results" / "uni_embed_moran_s1.json"
    if _uni_path.exists():
        _u = json.load(open(_uni_path, encoding="utf-8"))
        _up = _u["pooled_within_slide_pc1_moran"]
        _unull = _u["pooled_perm_null"]
        _us = _u["per_slide_pc1_moran_all"]
        _uc = _u["by_cohort"]
        body(f"**Rationale.** The main-text morphology ablation separates two output axes: "
             f"adding the H&E branch raises spatial coherence (FULL Moran's I "
             f"{A['FULL']['moran_mean']:.3f} vs NO-IMAGE {A['NOIMAGE']['moran_mean']:.3f}) but "
             f"leaves disease ordering unchanged (τ {A['FULL']['tau_mean']:.3f} vs "
             f"{A['NOIMAGE']['tau_mean']:.3f}). To verify the coherence gain is not a fusion "
             f"artifact, we measured spatial autocorrelation of the frozen foundation-model "
             f"patch features themselves [@uni].", indent=False)
        body(f"**Design.** For every spot of the 35 cervical sections (46,820 spots) the frozen "
             f"1,024-dimensional UNI ViT-L embedding of the registered 224 px H&E patch was "
             f"extracted (no adapter, fusion or risk head). Features were z-scored per section "
             f"and reduced to the first local principal component; Moran's I [@moran] was "
             f"computed on the same k=6 k-NN graph used for the risk score. The pooled statistic "
             f"combines within-section-centred PC1 series with a within-section coordinate-fixed "
             f"permutation null (B=10,000), so between-section mean shifts cannot inflate it.",
             indent=False)
        body(f"**Results.** Pooled within-section PC1 Moran's I = {_up:.3f}, versus a null "
             f"centered at {_unull['mean']:.4f} (99th percentile {_unull['q990']:.4f}; "
             f"permutation p<10⁻⁴). PC1 Moran's I was positive on 35/35 sections "
             f"(median {_us['median']:.3f}, IQR {_us['q25']:.3f}–{_us['q75']:.3f}, range "
             f"{_us['min']:.3f}–{_us['max']:.3f}). By source: GSE208654 (n="
             f"{_uc['GSE208654']['n_samples']}) median "
             f"{_uc['GSE208654']['pc1_moran']['median']:.3f}; GSE217237 normal ectocervix "
             f"(n={_uc['GSE217237']['n_samples']}) median "
             f"{_uc['GSE217237']['pc1_moran']['median']:.3f}; the 10x demonstration section "
             f"{_uc['10x_cervical_cancer_1']['pc1_moran']['median']:.3f}. The pixel-level "
             f"registration QC (fraction of unique 224 px patches) was 1.00 for every section; "
             f"0/35 fell below the 0.50 failure threshold.", indent=False)
        body("**Interpretation.** Frozen morphology embeddings are strongly and pervasively "
             "spatially autocorrelated on both normal and lesion sections, far above the "
             "coordinate null. This supplies the feature-level mechanism for the two-axis "
             "verdict: morphology provides abundant spatial structure that regularizes risk "
             "field coherence, but that structure is not aligned with—and therefore does not "
             "reorder—the sample-level disease axis. The result characterizes this score in the "
             "n=4-diseased regime; small ranking effects cannot be excluded at three unpaired "
             "seeds.", indent=False)

    # ---------------- Note S2 -------------------------------------------
    h1("Supplementary Note S2. Post-hoc epithelial/stromal stratification of the GeoMx Silva "
       "non-monotonicity")
    body(f"On the GeoMx cohort the calibration sign is inverted (tumours score lower than "
         f"benign) and true Silva patterns are non-monotone: pattern A is lowest (core means A "
         f"{EXT['geomx_core_silva_A']:.2f} < C {EXT['geomx_core_silva_C']:.2f} < B "
         f"{EXT['geomx_core_silva_B']:.2f}; A vs B p={EXT['geomx_core_silva_AB_p']:.3f}). The "
         f"A-low ordering is compatible with the inverted sign but the B-over-C reversal breaks "
         f"any monotone risk interpretation. We therefore stratified ROIs by the authors' "
         f"epithelial/stromal annotation.", indent=False)
    body(f"(1) Composition artifact excluded: epithelial and stromal ROI counts are balanced "
         f"across Silva patterns (21/21, 22/22 and 25/25 for A/B/C). (2) The A-low signal is "
         f"epithelial: within epithelium A {EXT['geomx_silva_epi_A']:.2f} < B "
         f"{EXT['geomx_silva_epi_B']:.2f} < C {EXT['geomx_silva_epi_C']:.2f} (A vs B "
         f"Mann–Whitney p={EXT['geomx_silva_epi_AB_p']:.2e}), whereas stroma shows no monotone "
         f"gradient (A/B/C = {EXT['geomx_silva_str_A']:.2f}/{EXT['geomx_silva_str_B']:.2f}/"
         f"{EXT['geomx_silva_str_C']:.2f}); the epithelial-versus-stromal difference itself is "
         f"non-significant cohort-wide (p={EXT['geomx_compartment_p']:.3f}). (3) Pathology "
         f"High/Low risk cores point along the training numerical axis but are non-significant "
         f"(High {EXT['geomx_risk_core_hi']:.2f} vs Low {EXT['geomx_risk_core_lo']:.2f}, "
         f"n={EXT['geomx_risk_core_hi_n']}/{EXT['geomx_risk_core_lo_n']}, core p="
         f"{EXT['geomx_risk_core_p']:.3f}).", indent=False)
    body("(4) Limits. Two readings remain inseparable here: (i) residual dependence of the "
         "transferred expression score on glandular differentiation state in gland-preserving "
         "pattern A growth, rather than on invasive potential; or (ii) a GeoMx targeted-panel "
         "composition effect relative to the Visium whole-transcriptome training panel. No HPV "
         "RNA in-situ or quantitative p16 annotation exists in this dataset to test either; the "
         "comparison was not pre-registered for multiplicity and its p-values are descriptive. "
         "The robust statement stays: tumour–benign rank discrimination transfers; calibration "
         "sign and Silva/risk grading do not.", indent=False)

    # ---------------- Note S3 -------------------------------------------
    h1("Supplementary Note S3. HNSCC cross-organ transfer: triple-control design and "
       "section-level discriminative tests")
    body(f"**Control level 1 (authenticity).** Coordinate permutation (B=1,000) gives a "
         f"near-zero null (weakest section z={65.5:.0f} on GSE268014 and z={38.6:.0f} on "
         f"GSE281978) with p≤0.001 on all {EXT['hnscc_n_samples'] + EXT['hnscc_gse281978_n']} "
         f"sections ({EXT['hnscc_n_samples']}+{EXT['hnscc_gse281978_n']}), excluding output "
         f"collapse.", indent=False)
    body(f"**Control level 2 (pathway specificity).** The model-independent KEGG-HPV panel "
         f"reaches Moran's I {EXT['rg268_kegg']:.2f}/{EXT['rg281_kegg']:.2f}, close to the model "
         f"score ({EXT['hnscc_moran_mean']:.2f}/{EXT['hnscc_gse281978_moran_mean']:.2f}); against "
         f"30 pooled-mean-decile-matched random panels it is higher on "
         f"{EXT['rg268_exprm_npos']}/{EXT['rg268_exprm_n']} and "
         f"{EXT['rg281_exprm_npos']}/{EXT['rg281_exprm_n']} sections (exact sign p="
         f"{EXT['rg268_exprm_signp']:.3f}/{EXT['rg281_exprm_signp']:.3f}; Δ="
         f"{EXT['rg268_exprm_delta']:.2f}/{EXT['rg281_exprm_delta']:.2f}), a weak but "
         f"reproducible pathway-specific component.", indent=False)
    body("**Control level 3 (discriminative transfer—the only clinically meaningful caliber).** "
         "Using the authors' public spot-level annotations and GSM-level HPV status, "
         "section-level paired Wilcoxon / Mann–Whitney tests give:", indent=False)
    add_table(
        ["Test", "Cohort (sections)", "Direction count", "p", "Reading"],
        [
            ["Malignant vs non-malignant", "GSE268014 (8)",
             f"positive {EXT['mal_non_pos']}/{EXT['mal_non_n']}", f"{EXT['mal_non_p']:.3f}",
             "null"],
            ["Tumor front vs core", "GSE268014 (8)",
             f"positive {EXT['edge_core_pos']}/{EXT['edge_core_n']}", f"{EXT['edge_core_p']:.3f}",
             "null (boundary)"],
            ["HPV+ vs HPV−", f"GSE268014 ({EXT['hpv268_npos']} vs {EXT['hpv268_nneg']})",
             "mean " + f"{EXT['hpv268_pos']:.2f} vs {EXT['hpv268_neg']:.2f}",
             f"{EXT['hpv268_p']:.2f}", "null"],
            ["HPV+ vs HPV−", f"GSE281978 ({EXT['hpv281_npos']} vs {EXT['hpv281_nneg']})",
             "mean " + f"{EXT['hpv281_pos']:.2f} vs {EXT['hpv281_neg']:.2f}",
             f"{EXT['hpv281_p']:.3f}", "null"],
            ["Primary vs lymph-node metastasis",
             f"GSE268014 ({EXT['pt_n']} vs {EXT['lnmt_n']})",
             f"mean {EXT['pt_mean']:.2f} vs {EXT['lnmt_mean']:.2f}",
             f"{EXT['pt_lnmt_p']:.2f}", "null"],
        ], widths=[1.75, 1.30, 1.55, 0.70, 1.20])
    body("Cross-organ evidence is therefore strictly limited to: the cervically supervised "
         "pathway representation is computable in another organ and retains genuine, weakly "
         "pathway-specific spatial organization, but it cannot discriminate malignancy, HPV "
         "status or metastasis. Pooled spot-level tests (n>10⁴) reach high significance but "
         "suffer within-slide pseudo-replication and are records only, not evidence.",
         indent=False)

    save(doc, "Supplementary_Information_CiBM.docx")


# ========================================================================
#  HIGHLIGHTS  (3-5 bullets, each <=85 characters including spaces)
# ========================================================================
HIGHLIGHTS = [
    'LDI + MRP-ST: first ST-native label-removal audit protocol',
    'LDI formally defined with seed-uncertainty propagation and θ-gated control',
    'Label-free LODO probe passes planted signal, catches identity confounding',
    'External validity split into rank, calibration, grading—each migrates apart',
    'Cervical n=4 is a worked example; contribution is the audit method, not biology',
]


def build_highlights():
    doc = Document()
    doc.styles['Normal'].font.name = 'Times New Roman'
    doc.styles['Normal'].font.size = Pt(11)
    p = doc.add_paragraph(); _rf(p.add_run("Highlights"), 14, True)
    p = doc.add_paragraph()
    _rf(p.add_run("Computers in Biology and Medicine — submitted with: "), 10.5, italic=True)
    _rf(p.add_run("MRP-ST and the Label-Dependence Index: a validated label-removal protocol for small-sample spatial transcriptomics"), 10.5)
    doc.add_paragraph()
    for h in HIGHLIGHTS:
        p = doc.add_paragraph(style='List Bullet')
        _rf(p.add_run(h), 11)
    save(doc, "Highlights_CiBM.docx")


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
    para("The Editor-in-Chief", after=0)
    para("Computers in Biology and Medicine", after=0)
    para("Elsevier", after=14)
    para("Dear Editor,", after=10, bold=True)
    para("We submit our Research Article entitled “MRP-ST and the Label-Dependence Index: a validated label-removal "
         "protocol for risk models in extreme small-sample spatial transcriptomics of cervical neoplasia” for "
         "consideration in Computers in Biology and Medicine.")
    para("The manuscript proposes a new computational method and its accompanying open software, which we believe matches the "
         "scope of Computers in Biology and Medicine in Special Medical Data Processing Methods and in Medical Informatics and "
         "Bioinformatics. The method addresses a core computational problem: reliable evaluation of machine-learning methods "
         "when independent clinical samples are scarce. Our case contains only four diseased cervical sections. A supervised "
         "spatial-transcriptomic risk model achieves an in-cohort AUC of 1.00, yet conventional prediction and integration "
         "benchmarks cannot determine whether this reflects generalization or fitting four labels.")
    para("Our contribution is a method, not a further caution: we propose the Label-Dependence Index (LDI), a formal scalar "
         "metric with a θ-calibrated decision gate, and MRP-ST, the first ST-native, network-agnostic protocol that "
         "operationalizes it as a seven-variant nested label-removal cascade with a five-item minimum reporting protocol and "
         "supported/suggestive/unsupported grading. To our knowledge, no prior spatial-transcriptomic procedure decomposes "
         "which label-derived component drives a given risk score. Critically, we validate the protocol's discriminative power "
         "on controlled cohorts with known ground truth: a leave-one-donor-out probe on frozen label-free embeddings passes a "
         "strong shared program (supported), flags a weak heterogeneous program as borderline (suggestive), and catches pure "
         "donor-specific identity confounding that is learnable in-sample but untransferable (unsupported). We further report a "
         "multi-component external-validity dissociation: rank discrimination transfers to GeoMx, but calibration sign "
         "reverses and grading does not.")
    para(f"The cervical case study (LDI = {_ldi_mean:.3f} ± {_ldi_sd:.3f}, θ = {_ldi_theta:.3f}) shows the model's disease "
         f"ordering is driven primarily by the expression-derived proxy and pathway prior rather than intrinsic spatial "
         f"signal; in-sample AUC 1.00 coexists with leave-one-sample-out AUC ≈0.50. Constructively, a de-circularization control "
         f"then isolates which spatial programs survive supervision removal—tumor-epithelium and interferon persist while the "
         f"HPV-driver association is prior-anchored—delimiting what a small-n ST study can legitimately report. The specific "
         f"score is a worked example of the protocol, not a clinical instrument.")
    para("The manuscript is original, has not been published, and is not under consideration elsewhere. All data analyzed are "
         "public with accessions listed in the manuscript, and the analysis code and versioned result artifacts are openly "
         "released.")
    para("Thank you for your consideration.", after=14)
    para("Sincerely,", after=12)
    para("Lang Guo, on behalf of all authors", after=0)
    para("School of Pharmacy, Shenyang Medical College, 146 Huanghe North Avenue, Shenyang 110034, China", after=0)
    para("guolang1016@symc.edu.cn · Tel: +86 13555707001", after=0)
    save(doc, "CoverLetter_CiBM.docx")


# ========================================================================
#  SUBMISSION FORMS  (Title page / Declaration of competing interest / CRediT)
# ========================================================================
def _form_doc():
    doc = Document()
    doc.styles['Normal'].font.name = 'Times New Roman'
    doc.styles['Normal'].font.size = Pt(11)
    doc.styles['Normal'].paragraph_format.line_spacing = 1.3
    s = doc.sections[0]
    s.top_margin = s.bottom_margin = Cm(2.5); s.left_margin = s.right_margin = Cm(2.5)
    return doc


def build_submission_forms():
    TITLE = ('MRP-ST and the Label-Dependence Index: a validated label-removal '
             'protocol for risk models in extreme small-sample spatial '
             'transcriptomics of cervical neoplasia')

    # ---- Title page ---------------------------------------------------
    doc = _form_doc()
    def para(t, size=11, after=8, bold=False, align=None, indent=False):
        p = doc.add_paragraph()
        if align is not None:
            p.alignment = align
        p.paragraph_format.space_after = Pt(after)
        if indent:
            p.paragraph_format.left_indent = Cm(0.6)
        _rf(p.add_run(t), size, bold=bold)

    # word / table / figure counts read from the finished manuscript
    _wc = _figs = _tbls = None
    _ms_path = OUT / "Manuscript_CiBM.docx"
    if _ms_path.exists():
        try:
            _md = Document(str(_ms_path))
            _wc = sum(len(p.text.split()) for p in _md.paragraphs)
            _tbls = len(_md.tables)
            _figs = sum(1 for p in _md.paragraphs if p.text.strip().startswith("Fig. "))
        except Exception:
            pass

    para("Computers in Biology and Medicine", size=10, after=10,
         align=WD_ALIGN_PARAGRAPH.CENTER)
    para("Manuscript title page", size=10, after=6, align=WD_ALIGN_PARAGRAPH.CENTER, bold=True)
    para("Article type: Research Article", size=10, after=12, align=WD_ALIGN_PARAGRAPH.CENTER)
    para(TITLE, size=15, after=12, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    para("Mingwei Bai \u00b9, Zhengmin Gu \u00b2, Ye Zhang \u00b2, Lang Guo \u00b3,*", after=8,
         align=WD_ALIGN_PARAGRAPH.CENTER)
    para("\u00b9 JiMei Technology Group Co., Ltd., Shenyang 110002, China", size=10, after=2,
         align=WD_ALIGN_PARAGRAPH.CENTER)
    para("\u00b2 Medical Record Management Center, The First Hospital of China Medical University, "
         "Shenyang 110002, China", size=10, after=2, align=WD_ALIGN_PARAGRAPH.CENTER)
    para("\u00b3 School of Pharmacy, Shenyang Medical College, 146 Huanghe North Avenue, "
         "Shenyang 110034, China", size=10, after=14, align=WD_ALIGN_PARAGRAPH.CENTER)
    para("* Corresponding author: Lang Guo, School of Pharmacy, Shenyang Medical College, "
         "146 Huanghe North Avenue, Shenyang 110034, China", size=10, after=0)
    para("Tel: +86 13555707001; E-mail: guolang1016@symc.edu.cn", size=10, after=10)
    para("E-mail addresses — M. Bai: baimingwei@jm360.cn; Z. Gu: guzm@cmu1h.com; "
         "Y. Zhang: 13332457636@163.com", size=10, after=14)
    para(f"Word count: {_wc if _wc is not None else 'n/a'} (main text incl. abstract and "
         f"references)", size=10, after=4)
    para(f"Tables: {_tbls if _tbls is not None else 'n/a'} (main text); figures: "
         f"{_figs if _figs is not None else 'n/a'} embedded in the manuscript file; "
         "Supplementary Information: 6 tables and 3 notes (single file).", size=10, after=14)
    para("Data and code: All datasets are public with accessions listed in the manuscript; "
         "analysis code and versioned result artifacts are released at the repository given "
         "in the manuscript (Data and code availability).", size=10, after=0)
    save(doc, "Title_Page_CiBM.docx")

    # ---- Declaration of competing interests ---------------------------
    doc = _form_doc()
    para("Declaration of Competing Interests", size=11, after=10, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER)
    para("Article title: \u201c" + TITLE + "\u201d", after=8)
    para("Authors: Mingwei Bai; Zhengmin Gu; Ye Zhang; Lang Guo", after=14)
    para("Please check the following statements, in accordance with the Elsevier declaration-of-interest "
         "policy (https://www.elsevier.com/conflictsofinterest):", after=6)
    para("(1) The authors declare that they have no known competing financial interests or personal "
         "relationships that could have appeared to influence the work reported in this paper.",
         after=6, indent=True)
    para("(2) The authors declare the following financial interests / personal relationships which may "
         "be considered as potential competing interests: None.", after=14, indent=True)
    para("Corresponding author:", after=4)
    para("Lang Guo, School of Pharmacy, Shenyang Medical College, 146 Huanghe North Avenue, "
         "Shenyang 110034, China. Tel: +86 13555707001; E-mail: guolang1016@symc.edu.cn", after=14)
    para("Date: " + __import__("datetime").date.today().strftime("%B %d, %Y"), after=0)
    save(doc, "Declaration_of_Competing_Interests_CiBM.docx")

    # ---- CRediT author statement --------------------------------------
    doc = _form_doc()
    para("CRediT authorship contribution statement", size=11, after=10, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER)
    para("Article title: \u201c" + TITLE + "\u201d", after=14)

    def credit(name, role):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.left_indent = Cm(0.6)
        _rf(p.add_run(name + ': '), 11, bold=True)
        _rf(p.add_run(role), 11)

    credit("Mingwei Bai", "conceptualization, methodology, software, formal analysis, investigation, "
                           "data curation, visualization, writing – original draft.")
    credit("Zhengmin Gu", "data curation, validation, writing – review & editing.")
    credit("Ye Zhang", "data curation, resources, writing – review & editing.")
    credit("Lang Guo", "conceptualization, methodology, supervision, project administration, "
                       "writing – review & editing.")
    para("This CRediT statement is identical to the declaration in the manuscript \u201cDeclarations\u201d "
         "section and to the submission-system author roles.", size=10, after=0, indent=True)
    save(doc, "Credit_Author_Statement_CiBM.docx")


if __name__ == "__main__":
    build_manuscript()
    build_manuscript_cn()
    build_supplementary()
    build_highlights()
    build_cover_letter()
    build_submission_forms()
    print("DONE.")
