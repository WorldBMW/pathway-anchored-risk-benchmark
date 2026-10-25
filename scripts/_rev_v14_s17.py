#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_rev_v14_s17.py — 把「标签组内变异」受控对照写成 SI Table S17。

Table S17. Within-group label variation: one dataset, one grouping, three labels.
GSE316098 (GeoMx DSP, cervix): 186 ROIs from 7 cases. X 与 g 完全不变，只有 y 变，
且 y 的组内变异程度形成梯度。读数差异只能来自标签的变异结构。
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from docx import Document
from docx.shared import Pt

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
D = ROOT / "papers" / "20_MRP-ST-Repair_Patterns"

payload = json.loads((RES / "within_group_label_geomx.json").read_text(encoding="utf-8"))
runs = payload["runs"]
summary = payload["summary"]
proto = payload["protocol"]

ARM_ORDER = ["risk", "silva", "cell_type"]
ARM_DESC = {
    "risk": "patient risk stratum (0 normal < 1 low < 2 high)",
    "silva": "Silva invasion pattern per ROI (0 normal < 1 A < 2 B < 3 C)",
    "cell_type": "ROI cell type (0 epithelium, 1 stroma; nominal)",
}

doc = Document(D / "Supplemental_Information_Patterns.docx")


def para(text, bold=False, italic=False):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = bold
    r.italic = italic
    return p


# ------------------------------------------------------------------ 标题
para("Table S17. Within-group label variation: the same data, the same grouping, "
     "three labels.", bold=True)

# ------------------------------------------------------------------ caption
s_risk = summary["risk"]
s_sil = summary["silva"]
s_cell = summary["cell_type"]


def infl_range(name):
    v = [r["inflation"] for r in runs if r["arm"] == name]
    return min(v), max(v)


def keep_mean(name):
    v = [r["safety_tau_lgo_kept"] for r in runs
         if r["arm"] == name and r["lam"] > 0]
    return float(np.mean(v))


infl_risk, infl_sil, infl_cell = (infl_range("risk"), infl_range("silva"),
                                  infl_range("cell_type"))
keep_risk, keep_sil, keep_cell = (keep_mean("risk"), keep_mean("silva"),
                                  keep_mean("cell_type"))

para(
    "GSE316098 is a NanoString GeoMx Digital Spatial Profiling cohort of cervical "
    "tissue: 186 regions of interest (ROIs) from 7 cases (8 to 44 ROIs per case), "
    "each ROI carrying its own pathology annotation, so the label varies within a "
    "group by construction rather than being a donor-level value broadcast to "
    "every unit. Counts were converted to CPM (1e4), log1p-transformed and "
    "restricted to the 2,000 most variable genes. The design holds the feature "
    "matrix and the grouping variable fixed and changes only the label, along a "
    "gradient of within-group variation, so any difference in the readouts can "
    "only come from the variation structure of the label and not from the data, "
    "the embedding or the grouping. Group is the case identifier (G = 7). The "
    "instrument, the dose grid, the seeds and the permutation protocol are those "
    "of Table S13. "
    f"Across the three arms the fraction of groups whose label varies within the "
    f"group rises from {s_risk['frac_groups_varying']:.2f} (risk) to "
    f"{s_sil['frac_groups_varying']:.2f} (Silva pattern) to "
    f"{s_cell['frac_groups_varying']:.2f} (cell type), and the group-label "
    f"coupling kappa falls from {s_risk['kappa_group_label']:.4f} to "
    f"{s_sil['kappa_group_label']:.4f} to {s_cell['kappa_group_label']:.4f}. "
    f"The baseline association tau_base is {s_risk['tau_base']:.3f}, "
    f"{s_sil['tau_base']:.3f} and {s_cell['tau_base']:.3f}; the null scale "
    f"sigma_hat is {s_risk['sigma_hat']:.4f}, {s_sil['sigma_hat']:.4f} and "
    f"{s_cell['sigma_hat']:.4f}; the critical retention c_crit = 1.645 sigma_hat "
    f"/ tau_base is {s_risk['c_crit']:.3f}, {s_sil['c_crit']:.3f} and "
    f"{s_cell['c_crit']:.3f}. "
    f"Baseline sibling-unit inflation (tau_LOO - tau_LGO at lambda = 0) is "
    f"{s_risk['inflation_base']:+.4f}, {s_sil['inflation_base']:+.4f} and "
    f"{s_cell['inflation_base']:+.4f}. The ordering of the arms is the point of "
    f"the control: encoded identity is identical across arms by construction "
    f"(group-identity lift {s_cell['group_id_lift_base']:.2f}x chance at "
    f"lambda = 0 in all three, because the baseline embedding does not depend on "
    f"the label), so the fifty-fold difference in inflation between the "
    f"kappa = 0 arm and the other two cannot be attributed to how identifiable "
    f"the group is. Across all 15 seed x dose cells of each arm the inflation "
    f"distributions do not overlap (cell type {infl_cell[0]:+.4f} to "
    f"{infl_cell[1]:+.4f} against risk {infl_risk[0]:+.4f} to {infl_risk[1]:+.4f}). "
    f"The same ordering appears in what repair costs: the group-transferable "
    f"association retained under dose, tau_LGO/tau_LGO(baseline), averages "
    f"{keep_cell:.3f} on cell type, {keep_risk:.3f} on risk and {keep_sil:.3f} on "
    f"Silva pattern, so removing identity damaged the transferable signal in "
    f"proportion to what the label shared with the group. "
    f"Of the {s_risk['dosed_cells']} dosed (lambda > 0) seed x dose cells per "
    f"arm, the dual gate admitted {s_risk['dual_gate_pass_dosed']} on risk, "
    f"{s_sil['dual_gate_pass_dosed']} on Silva pattern and "
    f"{s_cell['dual_gate_pass_dosed']} on cell type; the leakage axis alone "
    f"admitted {s_risk['ldi_gate_pass_dosed']}, {s_sil['ldi_gate_pass_dosed']} "
    f"and {s_cell['ldi_gate_pass_dosed']} respectively. "
    "cell_type is a nominal label, so the sign of its tau depends on the "
    "arbitrary epithelium/stroma coding and carries no meaning; the magnitude is "
    "the interpretable quantity."
)

# ------------------------------------------------------------------ 汇总表
para("(a) Arm-level summary.", italic=True)
hdr_a = ["Label (arm)", "Units", "G", "Groups with\nwithin-group\nvariation",
         "kappa\n(group, label)", "tau_base", "sigma_hat", "tau_base/sigma_hat",
         "c_crit", "LDI base", "Inflation\nbase", "Inflation\nrange (all cells)",
         "tau_LGO\nretained\n(dosed)", "Group-ID\nlift base",
         "Dosed\ncells", "Dual-gate\naccepted"]
tb = doc.add_table(rows=1, cols=len(hdr_a))
tb.style = "Table Grid"
for j, h in enumerate(hdr_a):
    tb.rows[0].cells[j].text = h
IR = {"risk": infl_risk, "silva": infl_sil, "cell_type": infl_cell}
KM = {"risk": keep_risk, "silva": keep_sil, "cell_type": keep_cell}
for name in ARM_ORDER:
    s = summary[name]
    row = tb.add_row()
    vals = [ARM_DESC[name], str(s["n_units"]), str(s["G"]),
            f"{s['frac_groups_varying']:.2f}", f"{s['kappa_group_label']:.4f}",
            f"{s['tau_base']:.4f}", f"{s['sigma_hat']:.4f}",
            f"{s['tau_base'] / s['sigma_hat']:.2f}", f"{s['c_crit']:.3f}",
            f"{s['ldi_base']:.3f}", f"{s['inflation_base']:+.4f}",
            f"{IR[name][0]:+.4f} to {IR[name][1]:+.4f}",
            f"{KM[name]:.3f}",
            f"{s['group_id_lift_base']:.2f}", str(s["dosed_cells"]),
            str(s["dual_gate_pass_dosed"])]
    for j, v in enumerate(vals):
        row.cells[j].text = v

# ------------------------------------------------------------------ 明细表
para("(b) All seed x dose cells.", italic=True)
hdr_b = ["Arm", "lambda", "seed", "tau_LOO", "tau_LGO",
         "Delta (tau_LOO - tau_LGO)", "tau_in", "sigma_hat", "LDI", "R",
         "tau_LGO\nretained", "tau_LOO\nretained", "Group-ID\nlift",
         "LDI gate", "Dual gate"]
tb = doc.add_table(rows=1, cols=len(hdr_b))
tb.style = "Table Grid"
for j, h in enumerate(hdr_b):
    tb.rows[0].cells[j].text = h
for name in ARM_ORDER:
    for r in sorted([x for x in runs if x["arm"] == name],
                    key=lambda z: (z["seed"], z["lam"])):
        row = tb.add_row()
        vals = [name, f"{r['lam']:g}", str(r["seed"]),
                f"{r['tau_loo']:+.4f}", f"{r['tau_lgo']:+.4f}",
                f"{r['inflation']:+.4f}", f"{r['tau_in']:+.4f}",
                f"{r['sigma']:.4f}", f"{r['ldi']:.3f}", f"{r['R']:.3f}",
                f"{r['safety_tau_lgo_kept']:.3f}",
                f"{r['safety_tau_loo_kept']:.3f}",
                f"{r['group_id_lift']:.2f}",
                "pass" if r["ldi_gate_pass"] else "fail",
                "pass" if r["dual_gate_pass"] else "fail"]
        for j, v in enumerate(vals):
            row.cells[j].text = v

for t in doc.tables[-2:]:
    for row in t.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(8)

doc.save(D / "Supplemental_Information_Patterns.docx")
print("S17 appended:", len(runs), "cells")
for name in ARM_ORDER:
    s = summary[name]
    print(f"  {name:10s} vary={s['frac_groups_varying']:.2f} "
          f"kappa={s['kappa_group_label']:.4f} tau_base={s['tau_base']:.4f} "
          f"sigma={s['sigma_hat']:.4f} c_crit={s['c_crit']:.3f} "
          f"dual={s['dual_gate_pass_dosed']}/{s['dosed_cells']}")
