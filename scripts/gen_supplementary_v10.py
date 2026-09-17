# -*- coding: utf-8 -*-
"""gen_supplementary_v10.py — 生成 Supplementary Information
含 Table S1（渐近 p vs 真置换 p）、Table S2（MRP-ST 协议）、
Note S1（UNI 嵌入级空间自相关，待完成）、Note S2（Silva 事后分层）、Note S3（HNSCC 第三层判别检验）。
数据源：results/rank_perm_B10000.json、results/paper_v10_numbers.json
输出：papers/07_CSBJ_v10/Supplementary_Information_v10.docx
"""
import json
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from pathlib import Path

ROOT = Path(r"f:\project4_cervix_multimodal")
OUT = ROOT / "papers" / "07_CSBJ_v10"
D = json.load(open(ROOT / "results" / "rank_perm_B10000.json", encoding="utf-8"))
N = json.load(open(ROOT / "results" / "paper_v10_numbers.json", encoding="utf-8"))
EXT = N['external']

LABEL = {
    "FULL": "FULL (complete model)",
    "NOIMAGE": "NO-IMAGE (image branch off)",
    "NOHPV": "NO-HPV (pathway-consistency regularizer off)",
    "NONEIGH": "NO-NEIGH (spatial-neighbourhood constraint off)",
    "NOPROG": "NO-PROG (disease-severity labels off)",
}
ORDER = ["FULL", "NOIMAGE", "NOHPV", "NONEIGH", "NOPROG"]
TITLE = ("A label-dependence ablation benchmark for pathway-anchored risk representation in extreme "
         "low-sample spatial transcriptomics: a cervical-lesion label-free validation protocol and "
         "cross-platform transfer case study")


def _rf(run, size=10.5, bold=False, italic=False):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = 'Times New Roman'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')


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
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]
        c.text = ""
        _rf(c.paragraphs[0].add_run(h), 9, True)
    for row in rows:
        cs = t.add_row().cells
        for i, v in enumerate(row):
            cs[i].text = ""
            _rf(cs[i].paragraphs[0].add_run(v), 9)
    return t


def main():
    doc = Document()
    s = doc.sections[0]
    s.top_margin = s.bottom_margin = Cm(2.2)
    s.left_margin = s.right_margin = Cm(2.0)

    para(doc, "Supplementary Information", 14, True, align=WD_ALIGN_PARAGRAPH.CENTER, after=8)
    para(doc, TITLE, 11, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=12)
    para(doc, "Mingwei Bai (first author); corresponding author to be assigned.", 10, after=14)

    # ------------------------------------------------ Table S1
    para(doc, "Supplementary Table S1. SciPy asymptotic p versus true permutation p for the sample-level Kendall "
              "tau between the spot-risk score and histological severity.", 11, True, after=6)
    para(doc, f"The severity label vector (31 normal, 1 HSIL, 3 cancer; 35 samples) was permuted over all 35 samples "
              f"B = {D['B']:,} times, re-aggregating spot risk per sample for each permutation. The number of distinct "
              "label arrangements is 35 x C(34,3) = 209,440 (~2.1 x 10^5), so the empirical p-value resolution is set by "
              "the full 35-sample composition and is not limited by the 4! = 24 arrangements of the four disease samples. "
              "n_ge is the number of permutations whose tau reached or exceeded the observed value; p_perm = (n_ge + 1)/(B + 1).",
         10, after=8)

    rows = []
    for key in ORDER:
        for k, r in enumerate(D["variants"][key]):
            note = ""
            if key == "NOPROG":
                note = "n.s. at 0.05" if r["p_perm_B10000"] > 0.05 else "nominally significant"
            rows.append([LABEL[key] if k == 0 else "", str(r["seed"]), "%.4f" % r["tau"],
                         "%.5f" % r["p_asymptotic"], "%.5f" % r["p_perm_B10000"], str(r["n_ge"]), note])
    table(doc, ["Configuration", "Seed", "Kendall tau", "SciPy asymptotic p", "Permutation p (B=10,000)", "n_ge", "Note"], rows)

    para(doc, "", after=4)
    for n in [
        "1. The asymptotic p assumes large-sample normality and is anti-conservative at n = 35 with four disease events. "
        "The true permutation p is the value reported in the main text (Table 2) and is the one to be used.",
        "2. For every configuration except NO-PROG the two p-values differ by an order of magnitude (asymptotic ~1.0e-3 vs "
        "permutation 1e-4 to 2e-4), which is why they must be reported separately in small-sample rank tests.",
        "3. NO-PROG: permutation p = 0.040 to 0.072 across four seeds; only one of four reaches nominal significance. "
        "This is graded suggestive, not confirmed, in the main text.",
        "4. NO-HPV and NO-NEIGH have identical Kendall tau across all three seeds (0.4620), consistent with a single "
        "deterministic supervised signal dominating the sample-level ordering in these ablations.",
        "5. Source: results/rank_perm_B10000.json; all values are reproduced verbatim.",
    ]:
        para(doc, n, 9.5, after=3)

    # ------------------------------------------------ Table S2
    doc.add_page_break()
    para(doc, "Supplementary Table S2. MRP-ST: a minimum reporting protocol for low-sample spatial-transcriptomics "
              "risk studies (triggered when n_dis <= 10).", 11, True, after=6)
    para(doc, "The protocol comprises five required reporting items and a three-level conclusion-grading rule. All items "
              "are post-training analyses that can be reproduced on an existing code base at negligible computational cost.",
         10, after=8)
    table(doc, ["#", "Required item", "Minimum design", "Reading / failure meaning"], [
        ["R1", "Label-dependence ablation",
         "Set the disease-label loss to zero (all other losses, data and seed count unchanged); retrain with >=3 seeds",
         "If in-cohort ranking/AUC drops substantially, the original result is consistent with label anchoring; at n_dis <= 5 it can only be graded suggestive"],
        ["R2", "Whole-sample label permutation",
         "Permute the label vector over ALL N samples (including normals) B >= 10,000 times; never permute within disease samples only, and never use spots as the permutation unit",
         "Report empirical p, the number of attainable arrangements and the exact p floor; distinguish empirical from asymptotic p"],
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
    para(doc, "Grading rule. (i) supported: sample-level significance, direction consistent across >=3 seeds, and all "
              "applicable R1-R4 controls passed. (ii) suggestive: direction consistent across seeds but p at the exact "
              "feasibility boundary (e.g. NO-PROG p = 0.040-0.072; LODO 4/4 with 95% lower bound 0.40), or supported only "
              "by the paired design with wide count intervals. (iii) unsupported: not significant, direction reversed, or "
              "significant only under spot-level pseudo-replication.", 10, after=6)
    para(doc, "Execution order (decision tree). R2 non-significant -> stop, no testable in-cohort signal. R2 significant "
              "but R1 failing -> downgrade to suggestive and use R3 to probe the prior's contribution. R1-R3 passing -> run "
              "R4 and grade by count intervals rather than point proportions. R5 then emits the final graded statements. "
              "The protocol is network-agnostic and applies to any 'few disease samples + many spots' ST or spatial-omics "
              "risk study.", 10, after=6)
    para(doc, "Application to the present study: spatial self-organization with weak pathway specificity = supported; "
              "the GeoMx tumour-vs-normal direction, label anchoring, and semi-supervised > unsupervised LODO = suggestive; "
              "disease grading, prognosis prediction, cross-organ discrimination and image-branch gain = unsupported.",
         10, after=6)

    # ------------------------------------------------ Note S1
    doc.add_page_break()
    para(doc, "Supplementary Note S1. Spatial autocorrelation of UNI patch embeddings (analysis not yet completed).",
         11, True, after=6)
    para(doc, "In the main text the image branch is reported as producing zero detectable change in the risk-head output "
              "across three seeds (NO-IMAGE Moran's I marginally higher than FULL, 0.859 vs 0.849; identical Kendall tau "
              "0.457 vs 0.457). Two distinct nulls must be separated: (a) the image branch carries no usable information, "
              "and (b) the image carries spatial information that is already subsumed by the intrinsic smoothing of the "
              "expression branch. The test that separates them does not involve the risk head: compute Moran's I of the UNI "
              "patch embeddings themselves on the cervical Visium sections. A clearly positive value would support (b) and "
              "would allow the main-text statement to be reframed accordingly; a near-zero value would support (a). Until "
              "this analysis is run, only the risk-output-level reading ('zero detectable change') is supported, and no "
              "further inference is made in the main text.", 10, after=6)

    # ------------------------------------------------ Note S2
    para(doc, "Supplementary Note S2. Post-hoc stratification of the counter-intuitive Silva non-monotonicity.", 11, True, after=6)
    para(doc, "The main-text observation that the non-destructive, best-prognosis Silva pattern A scores highest on the "
              "GeoMx cohort is counter-intuitive for a risk score. To investigate it we stratified ROIs using the "
              "epithelial/stromal annotation.", 10, after=5)
    para(doc, "(1) Simple technical explanation excluded first. Epithelial and stromal ROI counts are perfectly balanced "
              "across patterns A/B/C (21/21, 22/22 and 25/25 respectively), so 'pattern A contains more epithelial ROIs' "
              "cannot explain the higher mean.", 10, after=5)
    para(doc, f"(2) The A-high signal lies entirely in epithelial ROIs. Epithelial A {EXT['geomx_silva_epi_A']:.2f} > "
              f"B {EXT['geomx_silva_epi_B']:.2f} > C {EXT['geomx_silva_epi_C']:.2f} (A vs B Mann-Whitney "
              f"p={EXT['geomx_silva_epi_AB_p']:.1e}), whereas stroma shows no gradient "
              f"(A/B/C = {EXT['geomx_silva_str_A']:.2f}/{EXT['geomx_silva_str_B']:.2f}/{EXT['geomx_silva_str_C']:.2f}).",
         10, after=5)
    para(doc, "(3) Interpretation and its limits. The result is compatible with a biological reading: non-destructive, "
              "gland-preserving Silva A growth may retain a more complete HPV-driven epithelial transcriptional program, "
              "whereas destructive pattern C disrupts it through stromal remodeling and dedifferentiation; in other words "
              "the score may track 'HPV epithelial-program completeness' rather than invasive potential, which also coheres "
              "with the reversed pathology High/Low result. However, this dataset contains no HPV RNA in-situ hybridization "
              "or quantitative p16 annotation, so the mechanism cannot be tested directly and is explicitly marked as an "
              "unverified hypothesis; the comparison was also not pre-registered for multiplicity and its p-values are "
              "descriptive only.", 10, after=6)

    # ------------------------------------------------ Note S3
    doc.add_page_break()
    para(doc, "Supplementary Note S3. HNSCC cross-organ transfer: pooled triple-control design and section-level "
              "discriminative tests.", 11, True, after=6)
    para(doc, f"Control level 1 (authenticity). Permuting spot coordinates B = 1000 times gives a near-zero null "
              f"(mean ~0; z = 38.8-95.7) with p <= 0.001 on all 14 sections (8 GSE268014 + 6 GSE281978), excluding output "
              f"collapse and establishing genuine spatial self-organization of the score field.", 10, after=5)
    para(doc, f"Control level 2 (pathway specificity). A plain model-independent KEGG-HPV panel (mean log1p(CPM10k) of the "
              f"108 genes) reaches Moran's I {EXT['rg268_kegg']:.2f}/{EXT['rg281_kegg']:.2f}, nearly identical to the model "
              f"score ({EXT['hnscc_moran_mean']:.2f}/{EXT['hnscc_gse281978_moran_mean']:.2f}), confirming that most "
              f"autocorrelation is intrinsic pathway-expression smoothing. Against 30 size-matched random panels drawn from "
              f"the union of per-slide 2,000 HVGs and matched to the KEGG panel by pooled mean-expression deciles, random "
              f"Moran's I stays lower ({EXT['rg268_exprm']:.2f}/{EXT['rg281_exprm']:.2f}; delta = "
              f"+{EXT['rg268_exprm_delta']:.2f}/+{EXT['rg281_exprm_delta']:.2f}), with the KEGG panel higher on "
              f"{EXT['rg268_exprm_npos']}/{EXT['rg268_exprm_n']} and {EXT['rg281_exprm_npos']}/{EXT['rg281_exprm_n']} sections "
              f"(slide-level exact sign test p={EXT['rg268_exprm_signp']:.3f}/{EXT['rg281_exprm_signp']:.3f}); without "
              f"expression matching the delta widens to +0.31/+0.32. The intersection of the eight per-slide HVG-2000 sets "
              f"contains only 4 genes (11 in GSE281978), too few for sampling, so the HVG union is used and recorded. This "
              f"reveals a weak but fully reproducible pathway-specific component.", 10, after=5)
    para(doc, "Control level 3 (discriminative transfer: the only clinically meaningful caliber). Using the authors' public "
              "spot-level annotations (binCNAstatus and Zone 1-3; n = 27,607) and GSM-level HPV status, section-level paired "
              "Wilcoxon / unpaired Mann-Whitney tests give:", 10, after=4)
    table(doc, ["Contrast", "Effect (mean delta)", "Direction", "p", "Note"], [
        ["Malignant vs Non_malignant", f"{EXT['mal_non_delta']:+.2f}", f"positive in {EXT['mal_non_pos']}/{EXT['mal_non_n']} sections", f"{EXT['mal_non_p']:.3f}", "not significant"],
        ["Tumour front (Zone 1) vs core (Zone 3)", f"{EXT['edge_core_delta']:+.2f}", f"{EXT['edge_core_pos']}/{EXT['edge_core_n']} positive", f"{EXT['edge_core_p']:.3f}", "borderline trend in the front-EMT direction, not below 0.05"],
        ["GSE268014 HPV+ (n=4) vs HPV- (n=4)", f"{EXT['hpv268_pos']:.2f} vs {EXT['hpv268_neg']:.2f}", "REVERSED", f"{EXT['hpv268_p']:.3f}", "malignant spots only: p = 0.34"],
        ["GSE281978 HPV+ (n=2) vs HPV- (n=4)", f"{EXT['hpv281_pos']:.2f} vs {EXT['hpv281_neg']:.2f}", "REVERSED", f"{EXT['hpv281_p']:.3f}", "n = 2, minimal power"],
        ["Primary (n=3) vs lymph-node metastasis (n=3)", f"{EXT['pt_mean']:.2f} vs {EXT['lnmt_mean']:.2f}", "none", f"{EXT['pt_lnmt_p']:.3f}", "no difference at all"],
    ])
    para(doc, "", after=4)
    para(doc, "Cross-organ evidence is therefore strictly limited to: the cervically supervised pathway representation is "
              "computable in another organ and retains genuine, weakly pathway-specific spatial organization, but it cannot "
              "discriminate malignancy, HPV status or metastasis, and does not constitute disease-specific cross-organ "
              "biological transfer. Pooled spot-level tests (n > 10^4) reach high significance but suffer from within-slide "
              "pseudo-replication and are reported as records only, not as evidence.", 10, after=6)

    fp = OUT / "Supplementary_Information_v10.docx"
    doc.save(str(fp))
    print("Supplementary Information ->", fp)


if __name__ == "__main__":
    main()
