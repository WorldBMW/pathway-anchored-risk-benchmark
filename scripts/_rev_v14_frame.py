#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_rev_v14_frame.py — v14: 加入 GSE316098（GeoMx ROI 级真值）受控对照。

设计：同一特征矩阵 X、同一分组变量 g，只换标签 y，使 group-label 耦合
kappa 形成 0.000 / 0.225 / 0.273 的梯度；lambda=0 的三臂共享同一嵌入，
因此 encoded identity 不是「可比」而是**完全相同**（6.55x chance）。
结果：sibling inflation 由 kappa 决定（+0.0075 → +0.3736 → +0.3955），
去身份对可迁移信号的损伤也由 kappa 决定（0.989 → 0.806 → 0.717）。

改动清单
--------
1. Results 新增一段（control: coupling, not identifiability）
2. Table 1 增加三行（同一队列三个标签）
3. Table 1 caption 补一句说明三行是同一队列
4. 补 SI Table S16 caption（v13 遗漏）+ 新增 S17 caption
5. Data availability 加 GSE316098 与两个新脚本
6. References 加 [44]
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "papers" / "20_MRP-ST-Repair_Patterns"
SRC = D / "MRP-ST-Repair_manuscript_Patterns_v13.md"
DST = D / "MRP-ST-Repair_manuscript_Patterns_v14.md"

shutil.copyfile(SRC, DST)
md = DST.read_text(encoding="utf-8")
n0 = len(md)


def rep(old, new, tag):
    global md
    assert md.count(old) == 1, f"anchor not unique ({md.count(old)}): {tag}"
    md = md.replace(old, new)
    print(f"  ok: {tag}")


# ---------------------------------------------------------------- 1. 正文新段
NEW_PARA = (
    "**Control: the channel is opened by coupling, not by identifiability.** "
    "Boundary I attributes the sibling-unit channel to group-label coupling rather "
    "than to how identifiable the group is, but the comparison that supports it "
    "holds identifiability only comparable across two cohorts (10.4x versus 9.1x "
    "chance), not fixed. We repeated it in a design where identifiability cannot "
    "move. GSE316098[44] is a NanoString GeoMx cohort of HPV-associated "
    "endocervical adenocarcinoma: 186 regions of interest from 7 cases, each ROI "
    "carrying its own pathology annotation, and the source study deliberately "
    "selected cases containing two distinct Silva invasion patterns within the "
    "same tumour, so the label varies within a group rather than being a "
    "donor-level value broadcast to every unit. Holding the feature matrix and the "
    "grouping variable fixed and changing only the label gives three arms spanning "
    "the coupling range: patient risk stratum (kappa = 0.225), Silva invasion "
    "pattern annotated per ROI (kappa = 0.273), and ROI cell type, epithelium "
    "versus stroma, balanced within every case and therefore orthogonal to the "
    "group (kappa = 0.000). At lambda = 0 the three arms share one embedding, so "
    "encoded identity is not merely comparable but identical, 6.55x chance in all "
    "three. Inflation tracks coupling and nothing else: +0.0075 on cell type "
    "(per-seed +0.0016 to +0.0185), +0.3736 on risk (+0.3528 to +0.4031) and "
    "+0.3955 on Silva pattern (+0.3337 to +0.4730) at baseline, and over all 15 "
    "seed x dose cells of each arm the two distributions do not approach "
    "overlapping (cell type +0.0016 to +0.0267 against risk +0.3210 to +0.4131), "
    "a separation of more than an order of magnitude at constant identifiability. "
    "What repair costs exposes the mechanism directly: the group-transferable "
    "association retained under dose was 0.989 of baseline on cell type (minimum "
    "0.964), 0.806 on risk (0.613) and 0.717 on Silva pattern (0.605), so removing "
    "identity damaged the transferable signal in proportion to how much the label "
    "shared with the group, and did not damage it at all where the label carried "
    "no group information. Two consequences follow, and neither of them adds an "
    "accepted operating point. First, the trap is conditional: at kappa = 0 there "
    "is no channel to open and no repair to justify, which states the scope "
    "condition in positive form rather than as a boundary on our cohorts. Second, "
    "Proposition 1 held again, on a seventh cohort and against ROI-level rather "
    "than donor-derived truth: tau_base/sigma_hat was 8.49, 9.34 and 10.39 "
    "against the 2.35 threshold, the dual gate was predicted empty in all three "
    "arms, and 0 of 12 dosed seed x dose cells passed it in each. These arms also "
    "show most directly why it is empty. The labels are strong (tau_base 0.71 to "
    "0.80), and Remark 1 says that strength is exactly what makes "
    "remove-and-preserve infeasible, because the gate then demands a near-zero "
    "association from a signal the fidelity axis asks to retain. Read together "
    "with the degeneracy of the fidelity axis when the baseline association is "
    "near zero (limitation x), the dual gate fails at both ends and is informative "
    "only in the band between them, which is where the three accepted cells among "
    "our 18 dosed clinical cells sit; that is the structural answer to why the "
    "count is not larger, and it is a prediction about any cohort, not a "
    "description of ours (Table S17).\n\n"
)

ANCHOR = "### Cross-domain audit: what reproduces outside the validation domain, and what does not"
rep(ANCHOR, NEW_PARA + ANCHOR, "results paragraph inserted")

# ---------------------------------------------------------------- 2. Table 1 三行
T1_LAST = ("| Prostate (52 patients, GSE278936) | benign vs tumour | 0.288 | "
           "≈ 0.143 | ≈ 2.0 | 0.80 | narrow | λ = 1.0 only, 2 of 3 seeds on "
           "both axes (LDI 1.51; re-run 1.46 ± 0.86; R 0.60; retention "
           "0.74–0.76); single operating point with measured spread, see text |")
T1_NEW_ROWS = T1_LAST + "\n" + "\n".join([
    ("| Cervix ROI-level, GSE316098 (186 ROIs, 7 cases) — patient risk | ordinal "
     "risk stratum | 0.75 | ≈ 0.080 | 9.34 | 0.18 | empty | none (0 of 12 dosed "
     "cells on both axes; leakage axis also 0 of 12) |"),
    ("| — Silva invasion pattern, annotated per ROI | ordinal histologic pattern | "
     "0.80 | ≈ 0.077 | 10.39 | 0.16 | empty | none (0 of 12 on both axes; leakage "
     "axis also 0 of 12) |"),
    ("| — ROI cell type, epithelium versus stroma | nominal, orthogonal to group | "
     "0.71 | ≈ 0.084 | 8.49 | 0.19 | empty | none (0 of 12 on both axes; leakage "
     "axis also 0 of 12) |"),
])
rep(T1_LAST, T1_NEW_ROWS, "Table 1 rows added")

# ---------------------------------------------------------------- 3. Table 1 caption
T1_CAP = ("The ratio governs whether a feasible dose exists; the LDI grades whether "
          "a given run is acceptable.")
rep(T1_CAP, T1_CAP + " The three GSE316098 rows are one cohort carrying three "
    "labels, not three cohorts: the prediction attaches to a label, and the cohort "
    "is listed three times to make that visible (Table S17).",
    "Table 1 caption extended")

# ---------------------------------------------------------------- 4. SI captions
S15 = ("**Table S15.** Sensitivity of the feasibility threshold to the retained "
       "fraction c: threshold 1.645/c for c ∈ {0.5, 0.6, 0.7, 0.8, 0.9}, and for "
       "each cohort whether the dual gate is predicted feasible at that value, "
       "together with the realized retention τ_LDO/τ_base observed at "
       "leakage-passing cells.")
S16 = (
    "**Table S16.** Unit-resolution control: redefining the unit does not open a "
    "sibling channel. The cervical cohort, the spot embedding, the grouping "
    "variable and the donor-level severity label are held fixed and only the "
    "definition of the unit changes: at K = 1 the unit is the whole section "
    "mean-pooled over its spots, so every donor contributes one unit and "
    "leave-one-unit-out is identical to leave-one-group-out, making the sibling "
    "inflation zero by construction; at K = 3 and K = 8 the spots of each section "
    "are partitioned at random into K blocks and each block is mean-pooled into a "
    "unit, so each donor contributes K sibling units sharing its label. Reported "
    "per K, dose and seed: τ_LOO, τ_LGO, their difference Δ, σ̂, LDI, and the "
    "group-identity accuracy and lift of a classifier fitted on the same "
    "embedding, which is what shows that the absence of a channel is not explained "
    "by the embedding having lost donor identity. σ̂ is the null scale at the "
    "declared resolution and falls as the number of units rises, so LDI is "
    "comparable across cohorts at a fixed resolution and not across resolutions of "
    "the same data.\n\n"
)
S17 = (
    "**Table S17.** Within-group label variation: the same data, the same grouping, "
    "three labels. GSE316098[44] is a NanoString GeoMx cohort of HPV-associated "
    "endocervical adenocarcinoma: 186 regions of interest from 7 cases, each ROI "
    "carrying its own pathology annotation, so the label varies within a group "
    "rather than being a donor-level value broadcast to every unit. Counts were "
    "converted to CPM, log1p-transformed and restricted to the 2,000 most variable "
    "genes. The feature matrix and the grouping variable are held fixed and only "
    "the label changes, along a gradient of group-label coupling: patient risk "
    "stratum (κ = 0.225), Silva invasion pattern annotated per ROI (κ = 0.273), "
    "and ROI cell type, epithelium versus stroma, balanced within every case and "
    "therefore orthogonal to the group (κ = 0.000). At λ = 0 the three arms share "
    "one embedding, so encoded identity is identical rather than merely comparable "
    "across arms (group-identity lift 6.55x chance in all three), which is what "
    "makes this a cleaner test of boundary I than the cross-domain comparison, "
    "where identifiability was matched only approximately. Reported per arm, dose "
    "and seed: τ_LOO, τ_LGO, their difference Δ, σ̂, LDI, R, the retention of "
    "τ_LGO and τ_LOO relative to baseline, group-identity lift, and the verdict on "
    "the leakage axis and on both axes. Baseline Δ was +0.0075, +0.3736 and "
    "+0.3955 on the three arms and the per-cell distributions do not overlap; "
    "τ_base/σ̂ was 8.49, 9.34 and 10.39 against the 2.35 threshold, the dual gate "
    "was predicted empty on all three arms, and 0 of 12 dosed cells passed it on "
    "each. cell type is a nominal label, so the sign of its τ depends on the "
    "arbitrary epithelium/stroma coding and the magnitude is the interpretable "
    "quantity.\n\n"
)
rep(S15, S15 + "\n\n" + S16 + S17.rstrip("\n"), "SI captions S16/S17 added")

# ---------------------------------------------------------------- 5. Data availability
DA_OLD = ("The external Visium cohorts (GSE268014[17] and GSE278936[19]) are "
          "publicly available via GEO.")
DA_NEW = ("The external Visium cohorts (GSE268014[17] and GSE278936[19]) and the "
          "GeoMx cohort (GSE316098[44]) are publicly available via GEO.")
rep(DA_OLD, DA_NEW, "data availability: GSE316098")

SC_OLD = ("(including the domain-agnostic cohort simulator and the cross-domain "
          "runner `exp_crossdomain_audit.py`)")
SC_NEW = ("(including the domain-agnostic cohort simulator, the cross-domain runner "
          "`exp_crossdomain_audit.py`, the unit-resolution ladder "
          "`exp_unit_ladder_cervical.py` and the within-group-label control "
          "`exp_within_group_label_geomx.py`)")
rep(SC_OLD, SC_NEW, "data availability: scripts")

# ---------------------------------------------------------------- 6. Reference
REF43 = ("43. Yagis, E., Atnafu, S.W., García Seco de Herrera, A., Marzi, C., "
         "Scheda, R., Giannelli, M., Tessa, C., Citi, L., and Diciotti, S. Effect "
         "of data leakage in brain MRI classification using 2D convolutional "
         "neural networks. Sci. Rep. 11, 22544 (2021). "
         "https://doi.org/10.1038/s41598-021-01681-w.")
REF44 = ("44. [Dataset] Axelrod, M.L., Zhou, R., and Sun, L. Spatial "
         "transcriptomic landscape of invasion patterns in human "
         "papillomavirus-associated endocervical adenocarcinoma. Sci. Rep. 16, "
         "43717 (2026). https://doi.org/10.1038/s41598-026-43717-z. GSE316098.")
rep(REF43, REF43 + "\n" + REF44, "reference 44 added")

DST.write_text(md, encoding="utf-8")
print(f"\nv14 written: {DST.name}  ({n0} -> {len(md)} chars, +{len(md) - n0})")
