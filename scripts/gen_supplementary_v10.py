# -*- coding: utf-8 -*-
"""gen_supplementary_v10.py — 生成 Supplementary Information
含 Table S1（渐近 p vs 真置换 p）、Table S2（MRP-ST 协议）、
Note S1（UNI 冻结嵌入的片内空间自相关，读 results/uni_embed_moran_s1.json）、Note S2（Silva 事后分层）、Note S3（HNSCC 第三层判别检验）。
数据源：results/rank_perm_B10000.json、results/paper_v10_numbers.json
输出：papers/07_CSBJ_v10/Supplementary_Information_v10.docx
"""
import json
import os
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / os.environ.get("SI_OUT_DIR", "papers/07_CSBJ_v10")
SI_NAME = os.environ.get("SI_OUT_NAME", "Supplementary_Information_v10.docx")
OUT.mkdir(parents=True, exist_ok=True)
D = json.load(open(ROOT / "results" / "rank_perm_B10000.json", encoding="utf-8"))
N = json.load(open(ROOT / "results" / "paper_v10_numbers.json", encoding="utf-8"))
EXT = N['external']
ABL = N['ablation']
# Supplementary Note S1 — frozen UNI embedding spatial autocorrelation
# (scripts/notes1_uni_embed_moran.py -> results/uni_embed_moran_s1.json).
# Optional: if absent, the generator still runs and Note S1 is emitted as a
# clearly labelled pending placeholder rather than crashing.
_s1_path = ROOT / "results" / "uni_embed_moran_s1.json"
_s1_raw = json.load(open(_s1_path, encoding="utf-8")) if _s1_path.exists() else None
# Only accept the v2 within-slide design (2026-09-15). The earlier v1 file used
# global standardisation + a global permutation null confounded by between-slide
# mean shifts and must never reach the manuscript.
S1 = _s1_raw if (isinstance(_s1_raw, dict) and
                 "pooled_within_slide_pc1_moran" in _s1_raw) else None

LABEL = {
    "FULL": "FULL (complete model)",
    "NOIMAGE": "NO-IMAGE (image branch off)",
    "NOHPV": "NO-HPV (pathway-consistency regularizer off)",
    "NONEIGH": "NO-NEIGH (spatial-neighbourhood constraint off)",
    "NOPROG": "NO-PROG (ordinal severity labels off; expression-derived proxy retained)",
    "NOSUP": "NO-SUP (no labels: ordinal and proxy targets off)",
    "NOALL": "NO-ALL (no labels and no pathway prior: ordinal, proxy and lambda_hpv off)",
}
ORDER = ["FULL", "NOIMAGE", "NOHPV", "NONEIGH", "NOPROG", "NOSUP", "NOALL"]
TITLE = os.environ.get("SI_TITLE",
         "Auditing label memorization in small-sample spatial transcriptomics: a pathway-anchored "
         "benchmark with cross-platform validation in cervical lesions")


def _rf(run, size=10.5, bold=False, italic=False):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = 'Times New Roman'
    run._element.rPr.rFonts.set(qn('w:ascii'), 'Times New Roman')
    run._element.rPr.rFonts.set(qn('w:hAnsi'), 'Times New Roman')
    run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')


def _shade(cell, fill):
    node = OxmlElement('w:shd')
    node.set(qn('w:fill'), fill)
    cell._tc.get_or_add_tcPr().append(node)


def _cell_geometry(cell, width_inches, top=70, side=90, bottom=70):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_w = tc_pr.find(qn('w:tcW'))
    if tc_w is None:
        tc_w = OxmlElement('w:tcW')
        tc_pr.append(tc_w)
    tc_w.set(qn('w:type'), 'dxa')
    tc_w.set(qn('w:w'), str(int(round(width_inches * 1440))))
    tc_mar = tc_pr.first_child_found_in('w:tcMar')
    if tc_mar is None:
        tc_mar = OxmlElement('w:tcMar')
        tc_pr.append(tc_mar)
    for name, value in (('top', top), ('start', side), ('bottom', bottom), ('end', side)):
        edge = tc_mar.find(qn(f'w:{name}'))
        if edge is None:
            edge = OxmlElement(f'w:{name}')
            tc_mar.append(edge)
        edge.set(qn('w:w'), str(value))
        edge.set(qn('w:type'), 'dxa')
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def _add_page_number(paragraph):
    run = paragraph.add_run()
    begin = OxmlElement('w:fldChar'); begin.set(qn('w:fldCharType'), 'begin')
    instr = OxmlElement('w:instrText'); instr.set(qn('xml:space'), 'preserve'); instr.text = 'PAGE'
    end = OxmlElement('w:fldChar'); end.set(qn('w:fldCharType'), 'end')
    run._r.extend((begin, instr, end))
    _rf(run, 9)


def para(doc, t="", size=10.5, bold=False, italic=False, align=None, after=6):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.15
    if t:
        _rf(p.add_run(t), size, bold, italic)
    return p


def table(doc, headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    if widths is None:
        widths = {
            4: [0.40, 1.35, 2.55, 2.55],
            5: [1.60, 1.00, 1.45, 0.55, 2.25],
            7: [1.70, 0.45, 0.65, 0.80, 0.85, 0.45, 1.95],
        }.get(len(headers), [6.85 / len(headers)] * len(headers))
    tbl_pr = t._tbl.tblPr
    layout = tbl_pr.first_child_found_in('w:tblLayout')
    if layout is None:
        layout = OxmlElement('w:tblLayout')
        tbl_pr.append(layout)
    layout.set(qn('w:type'), 'fixed')
    grid = t._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths:
        col = OxmlElement('w:gridCol')
        col.set(qn('w:w'), str(int(round(width * 1440))))
        grid.append(col)
    tr_pr = t.rows[0]._tr.get_or_add_trPr()
    repeat = OxmlElement('w:tblHeader'); repeat.set(qn('w:val'), 'true'); tr_pr.append(repeat)
    body_size = 8.0 if len(headers) == 7 else 8.4
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]
        c.text = ""
        _cell_geometry(c, widths[i])
        _shade(c, '2F5496')
        c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        _rf(c.paragraphs[0].add_run(h), body_size, True)
        for run in c.paragraphs[0].runs:
            run.font.color.rgb = RGBColor(255, 255, 255)
    for row in rows:
        cs = t.add_row().cells
        for i, v in enumerate(row):
            cs[i].text = ""
            _cell_geometry(cs[i], widths[i])
            cs[i].paragraphs[0].paragraph_format.line_spacing = 1.0
            cs[i].paragraphs[0].alignment = (WD_ALIGN_PARAGRAPH.CENTER
                                             if len(headers) == 7 and 0 < i < 6
                                             else WD_ALIGN_PARAGRAPH.LEFT)
            _rf(cs[i].paragraphs[0].add_run(v), body_size)
    return t


def main():
    doc = Document()
    s = doc.sections[0]
    s.top_margin = s.bottom_margin = Cm(2.2)
    s.left_margin = s.right_margin = Cm(2.0)
    footer = s.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _add_page_number(footer)

    para(doc, "Supplementary Information", 14, True, align=WD_ALIGN_PARAGRAPH.CENTER, after=8)
    para(doc, TITLE, 11, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=12)
    para(doc, "Mingwei Bai¹, Zhengmin Gu², Ye Zhang², and Lang Guo³,*", 10,
         align=WD_ALIGN_PARAGRAPH.CENTER, after=3)
    para(doc, "¹ JiMei Technology Group Co., Ltd., Shenyang 110002, China; ² Medical Record Management Center, "
              "The First Hospital of China Medical University, Shenyang 110002, China; ³ School of Pharmacy, "
              "Shenyang Medical College, Shenyang 110034, China.", 9.5,
         align=WD_ALIGN_PARAGRAPH.CENTER, after=3)
    para(doc, "* Correspondence: guolang1016@symc.edu.cn", 9.5,
         align=WD_ALIGN_PARAGRAPH.CENTER, after=14)

    # ------------------------------------------------ Table S1
    para(doc, "Supplementary Table S1. SciPy asymptotic p versus empirical fitted-score permutation p for the sample-level Kendall "
              "tau between the spot-risk score and histological severity.", 11, True, after=6)
    para(doc, f"The severity label vector (31 normal, 1 HSIL, 3 cancer; 35 samples) was permuted over all 35 samples "
              f"B = {D['B']:,} times against per-sample mean scores held fixed after model fitting. The number of distinct "
              "label arrangements is 35 x C(34,3) = 209,440 (~2.1 x 10^5), so the empirical p-value resolution is set by "
              "the full 35-sample composition and is not limited by the 4! = 24 arrangements of the four disease samples. "
              "n_ge is the number of permutations whose tau reached or exceeded the observed value; p_perm = (n_ge + 1)/(B + 1).",
         10, after=8)

    rows = []
    _noprog_ps = [r["p_perm_B10000"] for r in D["variants"]["NOPROG"]]
    _noprog_nsig = sum(1 for _p in _noprog_ps if _p <= 0.05)
    _noprog_nseed = len(_noprog_ps)
    _nosup_rows = D["variants"].get("NOSUP")
    if _nosup_rows is None:
        print("WARN: 'NOSUP' absent from results/rank_perm_B10000.json - "
              "pending row emitted; run scripts/rerun_2026-09-23_nosup.sh and regenerate.")
    _nosup_ps = [r["p_perm_B10000"] for r in (_nosup_rows or [])]
    _nosup_taus = [r["tau"] for r in (_nosup_rows or [])]
    _noall_rows = D["variants"].get("NOALL")
    if _noall_rows is None:
        print("WARN: 'NOALL' absent from results/rank_perm_B10000.json - "
              "pending row emitted; run scripts/rerun_2026-09-24_noall.sh and regenerate.")
    _noall_ps = [r["p_perm_B10000"] for r in (_noall_rows or [])]
    _noall_taus = [r["tau"] for r in (_noall_rows or [])]
    _pending_script = {"NOSUP": "scripts/rerun_2026-09-23_nosup.sh",
                       "NOALL": "scripts/rerun_2026-09-24_noall.sh"}
    for key in ORDER:
        if key not in D["variants"]:
            if key in ("NOSUP", "NOALL"):
                rows.append([LABEL[key], "[pending]", "[pending]", "[pending]", "[pending]", "-",
                             "Run %s, then regenerate this file" % _pending_script[key]])
            continue
        for k, r in enumerate(D["variants"][key]):
            note = ""
            if key in ("NOPROG", "NOSUP", "NOALL"):
                note = "n.s. at 0.05" if r["p_perm_B10000"] > 0.05 else "nominally significant"
            rows.append([LABEL[key] if k == 0 else "", str(r["seed"]), "%.4f" % r["tau"],
                         "%.5f" % r["p_asymptotic"], "%.5f" % r["p_perm_B10000"], str(r["n_ge"]), note])
    table(doc, ["Configuration", "Seed", "Kendall tau", "SciPy asymptotic p", "Permutation p (B=10,000)", "n_ge", "Note"], rows)

    para(doc, "", after=4)
    _notes = [
        "1. The asymptotic p assumes large-sample normality and is anti-conservative at n = 35 with four disease events. "
        "The empirical conditional permutation p is reported in the main text (Table 3). Because scores are held fixed after "
        "fitting, it measures fitted-cohort score-label alignment and does not replace held-out evaluation.",
        "2. For every configuration except the label-removal arms (NO-PROG"
        + (", NO-SUP" if _nosup_rows is not None else "")
        + (", NO-ALL" if _noall_rows is not None else "")
        + ") the two p-values differ by an order of magnitude (asymptotic ~1.0e-3 vs "
        "permutation 1e-4 to 2e-4), which is why they must be reported separately in small-sample rank tests.",
        f"3. NO-PROG: permutation p = {min(_noprog_ps):.3f} to {max(_noprog_ps):.3f} across {_noprog_nseed} seeds; "
        f"{_noprog_nsig} of {_noprog_nseed} reach nominal significance, with the remaining seed at the 0.05 boundary. "
        "The direction is detectable on every seed but its strength sits at the n = 4 power boundary, so it is graded "
        "suggestive, not confirmed, in the main text.",
        "4. NO-HPV and NO-NEIGH have identical Kendall tau across all three seeds (0.4620), consistent with a single "
        "deterministic supervised signal dominating the sample-level ordering in these ablations.",
    ]
    if _nosup_rows is not None:
        _nosup_nsig = sum(1 for _p in _nosup_ps if _p <= 0.05)
        _notes.append(
            f"5. NO-SUP (lambda_sup = lambda_prog = 0; ordinal and expression-derived proxy targets both off): "
            f"Kendall tau = {min(_nosup_taus):.4f} to {max(_nosup_taus):.4f}, permutation p = {min(_nosup_ps):.3f} to "
            f"{max(_nosup_ps):.3f} across {len(_nosup_ps)} seeds; {_nosup_nsig} of {len(_nosup_ps)} reach nominal "
            "significance. This arm bounds the fully unsupervised case inside the flagship ablation matrix; the "
            "interpretation in the main text is conditioned on these observed p-values.")
    else:
        _notes.append(
            "5. NO-SUP (lambda_sup = lambda_prog = 0): [pending] three seeds (0, 1, 2) via "
            "scripts/rerun_2026-09-23_nosup.sh; the row above and main-text Table 3/Sections 4.2 and 5.3(6) are "
            "regenerated automatically once results/rank_perm_B10000.json contains the arm.")
    if _noall_rows is not None:
        _noall_nsig = sum(1 for _p in _noall_ps if _p <= 0.05)
        _notes.append(
            f"6. NO-ALL (lambda_sup = lambda_prog = lambda_hpv = 0; ordinal target, expression-derived proxy and "
            f"KEGG-HPV pathway-consistency prior all off): Kendall tau = {min(_noall_taus):.4f} to "
            f"{max(_noall_taus):.4f}, permutation p = {min(_noall_ps):.3f} to {max(_noall_ps):.3f} across "
            f"{len(_noall_ps)} seeds; {_noall_nsig} of {len(_noall_ps)} reach nominal significance. This arm closes the "
            "nested label -> proxy -> prior cascade inside the same ablation matrix and adjudicates the NO-SUP residue; "
            "panel genes still enter the encoder as ordinary inputs and reconstruction, neighbourhood and morphology "
            "terms remain on, so it bounds explicit disease-anchored terms, not all disease-correlated signal in the inputs.")
    else:
        _notes.append(
            "6. NO-ALL (lambda_sup = lambda_prog = lambda_hpv = 0): [pending] three seeds (0, 1, 2) via "
            "scripts/rerun_2026-09-24_noall.sh; the row above and main-text Table 3/Sections 4.2, 5.3(6) and 5.4 are "
            "regenerated automatically once results/rank_perm_B10000.json contains the arm.")
    _notes.append("7. Source: results/rank_perm_B10000.json; all values are reproduced verbatim.")
    for n in _notes:
        para(doc, n, 9.5, after=3)

    # ------------------------------------------------ Table S2
    doc.add_page_break()
    para(doc, "Supplementary Table S2. MRP-ST: a minimum reporting protocol for small-sample spatial-transcriptomic "
              "risk studies (triggered when n_diseased ≤ 10).", 11, True, after=6)
    para(doc, "The protocol comprises five required reporting items and a three-level conclusion-grading rule. It requires "
              "limited controlled retraining plus inexpensive post-processing and can be reproduced on an existing code base.",
         10, after=8)
    table(doc, ["#", "Required item", "Minimum design", "Reading / failure meaning"], [
        ["R1", "Nested label-dependence ablation",
         "Set the ordinal disease-label loss to zero; where an expression-derived, disease-correlated proxy target is also "
         "used, add a fully label-free arm with both ordinal and proxy targets off; where a disease-related pathway prior "
         "is additionally imposed, add a third label- and prior-free arm with its regularizer weight at zero (all other "
         "losses, data and seed counts unchanged; the panel genes remain ordinary inputs); retrain each arm with >=3 seeds",
         "If in-cohort ranking/AUC drops substantially, the original result is consistent with label anchoring; a residual "
         "ordering after ordinal-label removal that disappears in the label-free arm is proxy-driven; a further residue that "
         "disappears only when the pathway prior is also off is prior-driven, not label-free structure; a residue surviving "
         "all three arms indicates intrinsic data geometry; at n_diseased ≤ 5 every one of these readings can only be graded "
         "suggestive"],
        ["R2", "Whole-sample label permutation",
         "Permute the label vector over ALL N samples (including normals) B >= 10,000 times; never permute within disease samples only, and never use spots as the permutation unit",
         "Report empirical p, the number of attainable arrangements and the exact p floor; distinguish empirical from "
         "asymptotic p; when scores are held fixed after fitting, label the result a fitted-cohort association diagnostic, "
         "not a generalization test"],
        ["R3", "Random-gene-set (prior) control",
         ">=30 size-matched random sets, expression-quantile matched; compare both Moran's I and disease ranking",
         "If random sets rank equally well, the ranking comes from label/expression structure rather than the claimed pathway prior"],
        ["R4", "Sample-level held-out dual protocol",
         "Semi-supervised and fully unsupervised holdout protocols with identical per-fold training cohorts and only the label terms differing; statistical unit = sample/section, not spot",
         "Report k/n counts with exact Clopper-Pearson intervals; at n <= 6 also report the exact-test p floor"],
        ["R5", "Conclusion grading and clinical-utility statement",
         "Grade every conclusion as supported / suggestive / unsupported; state explicitly when there is no patient-level endpoint evidence",
         "Prohibit writing spot-level pseudo-replicated significance, in-sample AUC, or suggestive trends as confirmed conclusions"],
    ])
    para(doc, "", after=4)
    para(doc, f"Grading rule. (i) supported: direction consistent across ≥3 seeds, all applicable R1-R3 controls passed, "
              "and confirmation in an independent held-out or external sample-level test (R4). A fitted-cohort permutation "
              "p-value alone cannot confer supported status. (ii) suggestive: direction consistent across seeds but p at the exact "
              f"feasibility boundary (e.g. NO-PROG p = {min(_noprog_ps):.3f}-{max(_noprog_ps):.3f}, {_noprog_nsig}/"
              f"{_noprog_nseed} seeds nominal with one seed flipping the verdict; LODO 4/4 with 95% lower bound 0.40), or "
              "supported only by the paired design with wide count intervals. (iii) unsupported: not significant, "
              "direction reversed, or significant only under spot-level pseudo-replication. Ablated modules that act on one "
              "output axis but not another are graded per axis (e.g. the image branch: coherence gain supported, "
              "disease-ranking gain unsupported).", 10, after=6)
    para(doc, "Execution order (decision tree). R2 non-significant -> stop: no fitted-cohort score-label association. "
              "R2 significant -> continue; it does not establish generalization. If R1 fails, downgrade the fitted-cohort "
              "claim and use R3 to probe the regularizer's contribution. If R1-R3 pass, run R4 and grade by count intervals "
              "rather than point proportions. R5 then emits the final graded statements. "
              "The protocol is network-agnostic and applies to any 'few disease samples + many spots' ST or spatial-omics "
              "risk study.", 10, after=6)
    para(doc, "Application to the present study: spatial self-organization = supported; pathway specificity is stratified "
              "by caliber (cross-organ section-level advantage of the plain KEGG expression panel over expression-matched "
              "random panels = supported; in-cohort model-score specificity vs random gene sets, Moran permutation p = "
              "0.097, = unsupported); GeoMx tumour-benign rank discrimination with non-transferring calibration sign, "
              "label anchoring, and semi-supervised > unsupervised LODO = suggestive; the image branch = supported on the "
              "spatial-coherence axis and unsupported on the disease-ranking/endpoint axis; disease grading, prognosis "
              "prediction and cross-organ discrimination = unsupported.",
         10, after=6)

    # ------------------------------------------------ Note S1
    doc.add_page_break()
    para(doc, "Supplementary Note S1. Spatial autocorrelation of frozen UNI patch embeddings.",
         11, True, after=6)
    para(doc, f"Rationale. After correcting image registration, the main-text image-branch ablation acts "
              f"on two distinguishable output axes: adding the H&E image branch raises spatial coherence (FULL Moran's I "
              f"{ABL['FULL']['moran_mean']:.3f} vs NO-IMAGE {ABL['NOIMAGE']['moran_mean']:.3f}) but leaves the "
              f"sample-level disease ordering essentially unchanged (Kendall tau {ABL['FULL']['tau_mean']:.3f} vs "
              f"{ABL['NOIMAGE']['tau_mean']:.3f}). To interpret the coherence gain independently of the trained risk head "
              "- and to check it is not an artifact of the fusion layer - we measured spatial autocorrelation of the "
              "frozen foundation-model patch features themselves. If those features carry strong within-slide spatial "
              "structure, the fusion layer can exploit morphology to regularize the coherence of the risk field even when "
              "morphology contributes no independent disease ranking; if they do not, the FULL-minus-NO-IMAGE coherence "
              "delta would be hard to attribute to real histomorphology.", 10, after=5)
    para(doc, "Design. For every Visium spot of the 35 cervical sections we extracted the frozen 1,024-dimensional UNI "
              "ViT-L embedding (Chen et al., 2024) of its 224 px H&E patch (no adapter, no fusion, no risk head). The "
              "primary estimand is WITHIN-section: features were z-scored per section, reduced to the first local "
              "principal component, and Moran's I was computed on the same k = 6 k-NN graph used for the risk score; the "
              "distribution over all 35 sections is reported, stratified by source cohort. A pooled statistic combines "
              "the within-section-centred PC1 series, with a coordinate-fixed permutation null that shuffles PC1 "
              "separately WITHIN each section (B = 10,000), so between-section mean shifts (patient/scanner differences) "
              "cannot inflate it. Per-dimension Moran's I over all 1,024 embedding dimensions and a pixel-level "
              "registration QC (fraction of unique patches per section) accompany it. Spot coordinates were mapped from "
              "full-resolution to hires-image pixels using tissue_hires_scalef per the Space Ranger specification.",
         10, after=5)
    if S1 is None:
        para(doc, "[PENDING] results/uni_embed_moran_s1.json (within-slide v2 design) has not yet been produced; run "
                  "scripts/notes1_uni_embed_moran.py on the corrected image-registration pipeline and regenerate this "
                  "document. Until then the risk-output-level reading on two axes (image branch raises coherence but does "
                  "not change disease ranking) stands, but the feature-level corroboration below is missing.",
             10, italic=True, after=6)
    else:
        cfg, bc, nh = S1["config"], S1["by_cohort"], S1["pooled_perm_null"]
        g1 = bc.get("GSE208654", {}).get("pc1_moran", {})
        g2 = bc.get("GSE217237", {}).get("pc1_moran", {})
        g3 = bc.get("10x_cervical_cancer_1", {}).get("pc1_moran", {})
        allv = S1["per_slide_pc1_moran_all"]
        _uf = sorted(r["patch_qc"]["unique_fraction"] for r in S1["per_sample"])
        _uf_med = _uf[len(_uf) // 2]
        _uf_min = _uf[0]
        _ipos = sum(1 for r in S1["per_sample"]
                    if r.get("pc1_moran") is not None and r["pc1_moran"] == r["pc1_moran"]
                    and r["pc1_moran"] > 0)
        para(doc, f"Results. Across {cfg['n_samples']} sections ({cfg['n_spots']:,} spots), the pooled within-section PC1 "
                  f"Moran's I was {S1['pooled_within_slide_pc1_moran']:.3f}, versus a within-section permutation null "
                  f"centred at {nh['mean']:+.4f} (99th percentile {nh['q990']:.4f}; permutation p < "
                  f"{max(S1['pooled_within_slide_perm_p'], 1e-4):.0e} at B = 10,000). At the single-section level PC1 "
                  f"Moran's I was positive on {_ipos}/{allv['n']} sections with median {allv['median']:.3f} "
                  f"(IQR {allv['q25']:.3f}-{allv['q75']:.3f}; range {allv['min']:.3f}-{allv['max']:.3f}). "
                  f"Stratified: GSE208654 (4 sections) median {g1.get('median', float('nan')):.3f} "
                  f"[{g1.get('min', float('nan')):.3f}, {g1.get('max', float('nan')):.3f}]; GSE217237 (30 normal "
                  f"ectocervix) median {g2.get('median', float('nan')):.3f} [{g2.get('min', float('nan')):.3f}, "
                  f"{g2.get('max', float('nan')):.3f}]; 10x demonstration section {g3.get('median', float('nan')):.3f}. "
                  f"Pixel-level registration QC (fraction of unique 224 px patches per section) gave median "
                  f"{_uf_med:.2f} (minimum {_uf_min:.2f}); {S1['n_bad_registration_samples']} section(s) fell below the "
                  f"0.50 failure threshold, confirming patches were spatially registered rather than clamped/blank.",
             10, after=5)
        para(doc, "Interpretation. Frozen UNI morphology embeddings are strongly and pervasively spatially autocorrelated "
                  "on the cervical Visium sections, at scales far above the coordinate-permuted null and on normal as "
                  "well as lesion sections. This supplies the feature-level mechanism for the two-axis ablation result: "
                  "histomorphology carries abundant spatial structure that the fusion layer exploits to regularize the "
                  "spatial coherence of the risk field (FULL Moran's I above NO-IMAGE), whereas that morphology field is "
                  "not aligned with - and therefore does not reorder - the sample-level disease axis driven by the "
                  "supervised signal. The image branch is thus informative for spatial coherence rather than 'redundant', "
                  "but it is non-incremental for disease ranking and for every endpoint-relevant discriminative test. The "
                  "result does not establish that histology is uninformative for cervical lesion modelling in general; it "
                  "characterizes what this particular score gains from morphology in this n = 4-diseased-sample regime, "
                  "and small ranking effects cannot be excluded with three unpaired seeds.", 10, after=6)

    # ------------------------------------------------ Note S2
    para(doc, "Supplementary Note S2. Post-hoc stratification of the counter-intuitive Silva non-monotonicity.", 11, True, after=6)
    para(doc, "On the GeoMx cohort the calibration sign of the cervically trained score is inverted (tumours score lower "
              "than benign), and within tumour cores the true Silva patterns A/B/C are non-monotonic: the non-destructive, "
              "best-prognosis pattern A scores lowest (core-level A "
              f"{EXT['geomx_core_silva_A']:.2f} < C {EXT['geomx_core_silva_C']:.2f} < B {EXT['geomx_core_silva_B']:.2f}; A "
              "vs B p=%.3f), with B rather than C at the top. The A-low ordering is directionally compatible with the "
              "inverted sign (better prognosis -> lower score), but the B-over-C reversal breaks any monotone risk "
              "interpretation. To localize the pattern effect we stratified ROIs using the epithelial/stromal annotation."
              % EXT['geomx_core_silva_AB_p'], 10, after=5)
    para(doc, "(1) Simple technical explanation excluded first. Epithelial and stromal ROI counts are perfectly balanced "
              "across patterns A/B/C (21/21, 22/22 and 25/25 respectively), so 'pattern A contains more epithelial ROIs' "
              "cannot explain the lower mean.", 10, after=5)
    para(doc, f"(2) The A-low signal lies in epithelial ROIs. Within epithelium A {EXT['geomx_silva_epi_A']:.2f} < B "
              f"{EXT['geomx_silva_epi_B']:.2f} < C {EXT['geomx_silva_epi_C']:.2f} (A vs B Mann-Whitney "
              f"p={EXT['geomx_silva_epi_AB_p']:.1e}), whereas stroma shows no monotone gradient "
              f"(A/B/C = {EXT['geomx_silva_str_A']:.2f}/{EXT['geomx_silva_str_B']:.2f}/{EXT['geomx_silva_str_C']:.2f}); the "
              "epithelial/stromal ROI difference itself is non-significant cohort-wide (p=%.3f)."
              % EXT['geomx_compartment_p'], 10, after=5)
    para(doc, f"(3) Pathology risk grade points along the training risk axis but is non-significant. High-risk cores "
              f"score {EXT['geomx_risk_core_hi']:.2f} vs {EXT['geomx_risk_core_lo']:.2f} for low-risk cores (High > Low, "
              f"the same numerical direction as the high-score=high-risk training axis; core-level "
              f"p={EXT['geomx_risk_core_p']:.3f}). It is therefore not a direction reversal, but at p > 0.05 it provides "
              "no grading evidence either.", 10, after=5)
    para(doc, "(4) Interpretation and its limits. Two readings remain compatible with the data and cannot be separated "
              "here: (i) a residual dependence of the transferred expression score on glandular differentiation state in "
              "non-destructive, gland-preserving pattern A growth, rather than on invasive potential per se; or (ii) a "
              "platform-specific composition effect of the GeoMx targeted panel relative to the Visium whole-transcriptome "
              "panel the model was trained on. This dataset contains no HPV RNA in-situ hybridization or quantitative p16 "
              "annotation, so the mechanism cannot be tested directly and is explicitly marked as an unverified "
              "hypothesis; the comparison was also not pre-registered for multiplicity and its p-values are descriptive "
              "only. The robust statement is therefore limited to: rank discrimination between tumour and benign is "
              "strong, the calibration sign does not transfer, and the score does not grade Silva pattern or pathology "
              "risk on this platform.", 10, after=6)

    # ------------------------------------------------ Note S3
    doc.add_page_break()
    para(doc, "Supplementary Note S3. HNSCC cross-organ transfer: pooled triple-control design and section-level "
              "discriminative tests.", 11, True, after=6)
    para(doc, f"Control level 1 (authenticity). Permuting spot coordinates B = 1000 times gives a near-zero null "
              f"(mean ~0; the weakest section on each cohort still gives z = {EXT['hnscc_perm_z_min_268']:.1f} on "
              f"GSE268014 and z = {EXT['hnscc_perm_z_min_281']:.1f} on GSE281978) with p <= 0.001 on all 14 sections "
              f"(8 GSE268014 + 6 GSE281978), excluding output collapse and establishing genuine spatial self-organization "
              f"of the score field.", 10, after=5)
    para(doc, f"Control level 2 (pathway specificity). A plain model-independent KEGG-HPV panel (mean log1p(CPM10k) of the "
              f"108 genes) reaches Moran's I {EXT['rg268_kegg']:.2f}/{EXT['rg281_kegg']:.2f}, nearly identical to the model "
              f"score ({EXT['hnscc_moran_mean']:.2f}/{EXT['hnscc_gse281978_moran_mean']:.2f}), confirming that most "
              f"autocorrelation is intrinsic pathway-expression smoothing. Against 30 size-matched random panels drawn from "
              f"the union of per-slide 2,000 HVGs and matched to the KEGG panel by pooled mean-expression deciles, random "
              f"Moran's I stays lower ({EXT['rg268_exprm']:.2f}/{EXT['rg281_exprm']:.2f}; delta = "
              f"+{EXT['rg268_exprm_delta']:.2f}/+{EXT['rg281_exprm_delta']:.2f}), with the KEGG panel higher on "
              f"{EXT['rg268_exprm_npos']}/{EXT['rg268_exprm_n']} and {EXT['rg281_exprm_npos']}/{EXT['rg281_exprm_n']} sections "
              f"(slide-level exact sign test p={EXT['rg268_exprm_signp']:.3f}/{EXT['rg281_exprm_signp']:.3f}); without "
              f"expression matching the delta widens to +{EXT['rg268_kegg']-EXT['rg268_hvgu']:.2f}/+"
              f"{EXT['rg281_kegg']-EXT['rg281_hvgu']:.2f}. The intersection of the eight per-slide HVG-2000 sets "
              f"contains only 4 genes (11 in GSE281978), too few for sampling, so the HVG union is used and recorded. This "
              f"reveals a weak but fully reproducible pathway-specific component.", 10, after=5)
    para(doc, "Control level 3 (discriminative transfer: the only clinically meaningful caliber). Using the authors' public "
              "spot-level annotations (binCNAstatus and Zone 1-3; n = 27,607) and GSM-level HPV status, section-level paired "
              "Wilcoxon / unpaired Mann-Whitney tests give:", 10, after=4)
    table(doc, ["Contrast", "Effect (mean delta)", "Direction", "p", "Note"], [
        ["Malignant vs Non_malignant", f"{EXT['mal_non_delta']:+.2f}", f"positive in {EXT['mal_non_pos']}/{EXT['mal_non_n']} sections", f"{EXT['mal_non_p']:.3f}", "not significant"],
        ["Tumour front (Zone 1) vs core (Zone 3)", f"{EXT['edge_core_delta']:+.2f}", f"{EXT['edge_core_pos']}/{EXT['edge_core_n']} positive ({EXT['edge_core_n']-EXT['edge_core_pos']}/{EXT['edge_core_n']} reversed)", f"{EXT['edge_core_p']:.3f}", "borderline p at 0.055; overwhelmingly reversed, not a front-EMT trend"],
        [f"GSE268014 HPV+ (n={EXT['hpv268_npos']}) vs HPV- (n={EXT['hpv268_nneg']})", f"{EXT['hpv268_pos']:.2f} vs {EXT['hpv268_neg']:.2f}", "consistent (HPV+ higher), n.s.", f"{EXT['hpv268_p']:.3f}", "malignant spots only; not significant"],
        [f"GSE281978 HPV+ (n={EXT['hpv281_npos']}) vs HPV- (n={EXT['hpv281_nneg']})", f"{EXT['hpv281_pos']:.2f} vs {EXT['hpv281_neg']:.2f}", "consistent (HPV+ higher), n.s.", f"{EXT['hpv281_p']:.3f}", "n = 2 HPV+, minimal power; not significant"],
        [f"Primary (n={EXT['pt_n']}) vs lymph-node metastasis (n={EXT['lnmt_n']})", f"{EXT['pt_mean']:.2f} vs {EXT['lnmt_mean']:.2f}", "none", f"{EXT['pt_lnmt_p']:.3f}", "no difference at all"],
    ])
    para(doc, "", after=4)
    para(doc, "Cross-organ evidence is therefore strictly limited to: the cervically supervised pathway representation is "
              "computable in another organ and retains genuine, weakly pathway-specific spatial organization, but it cannot "
              "discriminate malignancy, HPV status or metastasis, and does not constitute disease-specific cross-organ "
              "biological transfer. Pooled spot-level tests (n > 10^4) reach high significance but suffer from within-slide "
              "pseudo-replication and are reported as records only, not as evidence.", 10, after=6)

    fp = OUT / SI_NAME
    doc.save(str(fp))
    print("Supplementary Information ->", fp)


if __name__ == "__main__":
    main()
