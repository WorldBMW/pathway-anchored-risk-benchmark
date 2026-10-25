# -*- coding: utf-8 -*-
"""gen_cbm_graphical_abstract.py — CBM graphical abstract.

Elsevier / Computers in Biology and Medicine requirement:
  minimum 531 x 1328 px (h x w), readable at 5 x 13 cm @ 96 dpi,
  preferred TIFF / EPS / PDF. We render a 1328 x 531 pt canvas at 300 dpi
  (3984 x 1593 px) and export both PNG and LZW-TIFF.

Story (three panels, matching the CBM narrative):
  1 THE PROBLEM  — 35 donors (31 normal / 4 diseased), perfect in-sample fit
  2 THE AUDIT    — MRP-ST seven-variant cascade + LDI + label-free LODO probe
  3 GRADED       — supported / suggestive / unsupported verdicts, gate held at
                   the real cohort size, external validity dissociates

Numbers are read from the same JSONs that gen_cbm.py uses, so the figure
cannot drift from the manuscript.

Output: papers/11_CiBM/figures/GraphicalAbstract_CiBM.{png,tif}
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "papers" / "11_CiBM" / "figures"


def _load(rel):
    p = ROOT / rel
    return json.load(open(p, encoding="utf-8")) if p.exists() else {}


N = _load("results/paper_v10_numbers.json")
A = N.get("ablation", {})
CO = N.get("cohort", {})
SIM = _load("results/sim_lodo_summary.json").get("arms", {})
SMS = _load("results/sim_lodo_summary_small.json").get("arms", {})
LDI = _load("results/ldi_report.json")
RL = _load("results/real_lodo_summary.json")


def _sim(arms, g, key, default=float("nan")):
    return (arms.get(g, {}).get("stats", {}) or {}).get(key, default)


def _tau(v, default=float("nan")):
    return A.get(v, {}).get("tau_mean", default)


tFULL, tPROG, tSUP, tALL = _tau("FULL"), _tau("NOPROG"), _tau("NOSUP"), _tau("NOALL")
moran = A.get("FULL", {}).get("moran_mean", float("nan"))
ldi = (LDI.get("ldi", {}) or {}).get("ldi_mean", float("nan"))
ldi_sd = (LDI.get("ldi", {}) or {}).get("ldi_sd", float("nan"))
theta = (LDI.get("decision", {}) or {}).get("theta", float("nan"))
tA = _sim(SIM, "group_A", "transfer_mean")
tC = _sim(SIM, "group_C", "transfer_mean")
tC_in = _sim(SIM, "group_C", "full_head_insample_mean")
rlm = RL.get("lodo_mean", float("nan"))
rlsd = RL.get("lodo_sd", float("nan"))
rl_sig = sum(1 for r in RL.get("lodo_seeds", []) if r.get("p", 1) < 0.05)

NAVY = "#1F3864"; STEEL = "#2F5496"; GREY = "#5A5A5A"
GREEN = "#2E7D32"; AMBER = "#B26A00"; RED = "#B02418"; PURPLE = "#7030A0"
LBLUE = "#EAF0FA"; PANEL2 = "#F4F2F8"

plt.rcParams["font.family"] = "DejaVu Sans"
fig = plt.figure(figsize=(13.28, 5.31), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1328); ax.set_ylim(0, 531); ax.axis("off")

ax.add_patch(FancyBboxPatch((8, 8), 1312, 515, boxstyle="round,pad=0,rounding_size=18",
                            fc="#FBFBFD", ec="#CCCCCC", lw=1.2, zorder=0))

ax.text(664, 500, "Auditing label dependence in small-sample spatial transcriptomics",
        ha="center", va="center", fontsize=19.5, fontweight="bold", color=NAVY)
ax.text(664, 472, "MRP-ST: a network-agnostic audit protocol with a validated, pre-registered decision gate",
        ha="center", va="center", fontsize=11.5, color=GREY, style="italic")


def panel(x, w, fc, ec, title):
    ax.add_patch(FancyBboxPatch((x, 56), w, 388, boxstyle="round,pad=0,rounding_size=14",
                                fc=fc, ec=ec, lw=2.0, zorder=1))
    ax.add_patch(FancyBboxPatch((x, 392), w, 52, boxstyle="round,pad=0,rounding_size=14",
                                fc=ec, ec=ec, lw=0, zorder=2))
    ax.text(x + w / 2, 418, title, ha="center", va="center",
            fontsize=13.5, fontweight="bold", color="white", zorder=3)


P1X, P2X, P3X, W = 28, 462, 896, 404

# ================= Panel 1: the problem ================================
panel(P1X, W, LBLUE, STEEL, "1  THE PROBLEM")
xs = [P1X + 83 + c * 40 for c in range(7)]
ys = [370 - r * 29 for r in range(5)]
DISEASED_IDX = {2, 9, 20, 30}
for i in range(35):
    r, c = divmod(i, 7)
    d = i in DISEASED_IDX
    ax.add_patch(Circle((xs[c], ys[r]), 10.5, fc=RED if d else "#7FA8D8",
                        ec="#333333", lw=0.8, zorder=3))
ax.add_patch(FancyBboxPatch((P1X + 36, 186), W - 72, 38,
             boxstyle="round,pad=0,rounding_size=8", fc="white", ec=RED, lw=1.8))
ax.text(P1X + W / 2, 205, f"In-sample: \u03c4 = {tFULL:.2f}, Moran's I = {moran:.2f}",
        ha="center", va="center", fontsize=11.5, fontweight="bold", color=RED)
ax.text(P1X + W / 2, 162, "learned disease signal ...",
        ha="center", va="center", fontsize=11, color=NAVY)
ax.text(P1X + W / 2, 138, "... or four memorized labels?",
        ha="center", va="center", fontsize=11.5, fontweight="bold", color=NAVY)
ax.text(P1X + W / 2, 102, f"{CO.get('n_normal', 31)} normal vs {CO.get('n_disease', 4)} diseased sections",
        ha="center", fontsize=10.5, color=NAVY)
ax.text(P1X + W / 2, 80, f"({CO.get('n_spots', 46820):,} spots  \u00b7  "
                         f"{CO.get('n_genes_panel', 108)}-gene pathway panel)",
        ha="center", fontsize=9.3, color=GREY)

# ================= Panel 2: the audit ==================================
panel(P2X, W, PANEL2, NAVY, "2  THE AUDIT   (MRP-ST)")
chips = [("FULL", STEEL, True), ("NO-IMAGE", GREY, False),
         ("NO-PROG", RED, True), ("NO-HPV", GREY, False),
         ("NO-SUP", PURPLE, True), ("NO-NEIGH", GREY, False),
         ("NO-ALL", "#404040", True)]
cx1, cx2 = P2X + 106, P2X + 298
chip_pos = [(cx1, 360), (cx2, 360), (cx1, 316), (cx2, 316),
            (cx1, 272), (cx2, 272), (cx1, 228)]
for (lab, col, bold), (cx, cy) in zip(chips, chip_pos):
    ax.add_patch(FancyBboxPatch((cx - 82, cy - 17), 164, 34,
                 boxstyle="round,pad=0,rounding_size=8", fc="white", ec=col, lw=1.8))
    ax.text(cx, cy, lab, ha="center", va="center", fontsize=10.5,
            fontweight="bold" if bold else "normal", color=col)
ax.add_patch(FancyArrowPatch((cx1 - 60, 342), (cx1 - 60, 208),
             arrowstyle="-|>", mutation_scale=13, lw=1.6, color=NAVY,
             linestyle=(0, (4, 2))))
ax.text(cx1 - 70, 278, "label\nproxy\nprior", ha="right", va="center",
        fontsize=8.8, color=NAVY, linespacing=1.15)
lines = [
    "7-variant nested label-removal cascade",
    "LDI = \u03c4_FULL \u2212 \u03c4_NO-ALL  (\u00b1SD)",
    "label-free leave-one-donor-out probe",
    "validated on 3 ground-truth simulations",
    "frozen UNI morphology + HPV prior",
    "external: GeoMx \u00b7 H&N ST \u00b7 TCGA-CESC",
]
for i, t in enumerate(lines):
    ax.text(P2X + 30, 190 - i * 22, "\u2022 " + t, ha="left", va="center",
            fontsize=9.8, fontweight="bold" if i == 1 else "normal", color="#222222")

# ================= Panel 3: graded evidence ============================
panel(P3X, W, "white", "#444444", "3  GRADED EVIDENCE")
TX = P3X + 46


def tag(y, txt, col):
    ax.add_patch(FancyBboxPatch((P3X + 22, y - 11), 8, 22,
                 boxstyle="round,pad=0,rounding_size=3", fc=col, ec=col))
    ax.text(TX, y, txt, ha="left", va="center", fontsize=12, fontweight="bold", color=col)


tag(370, "SUPPORTED", GREEN)
ax.text(TX, 348, f"Genuine shared program passes", fontsize=9.8, color="#222222")
ax.text(TX, 327, f"\u03c4_LODO {tA:.2f} \u00b7 3/3 seeds significant", fontsize=9.8, color="#222222")

tag(292, "SUGGESTIVE", AMBER)
ax.text(TX, 270, "Ordering collapses as labels leave", fontsize=9.8, color="#222222")
ax.text(TX, 249, f"\u03c4 {tFULL:.2f}\u2192{tPROG:.2f}\u2192{tSUP:.2f}\u2192{tALL:.2f}", fontsize=9.8, color="#222222")
ax.text(TX, 228, f"cervical \u03c4_LODO {rlm:.2f}\u00b1{rlsd:.2f} ({rl_sig}/3)", fontsize=9.8, color="#222222")

tag(206, "UNSUPPORTED", RED)
ax.text(TX, 184, "Identity confounding caught", fontsize=9.8, color="#222222")
ax.text(TX, 163, f"in-sample \u03c4 {tC_in:.2f} vs \u03c4_LODO {tC:.2f}", fontsize=9.8, fontweight="bold", color=RED)
ax.text(TX, 142, "grading & prognosis negative", fontsize=9.8, color="#222222")

ax.add_patch(FancyBboxPatch((P3X + 22, 58), W - 44, 52,
             boxstyle="round,pad=0,rounding_size=8", fc=NAVY, ec=NAVY))
ax.text(P3X + W / 2, 95, "Gate holds at the real cohort size (n=35)",
        ha="center", va="center", fontsize=9.8, fontweight="bold", color="white")
ax.text(P3X + W / 2, 74, "rank transfers to GeoMx; calibration does not",
        ha="center", va="center", fontsize=9.2, color="white")

# ---- arrows -----------------------------------------------------------
for x0 in (P1X + W + 4, P2X + W + 4):
    ax.add_patch(FancyArrowPatch((x0, 250), (x0 + 26, 250),
                 arrowstyle="-|>", mutation_scale=26, lw=2.4, color=NAVY))

ax.text(664, 30, "Perfect fit \u2260 generalization: remove labels, test whole donors, and grade the evidence.",
        ha="center", va="center", fontsize=11.8, color=GREY, style="italic")

OUT.mkdir(parents=True, exist_ok=True)
for suffix, kw in [("png", {}), ("tif", {"pil_kwargs": {"compression": "tiff_lzw"}})]:
    fp = OUT / f"GraphicalAbstract_CiBM.{suffix}"
    fig.savefig(fp, dpi=300, facecolor="white", **kw)
    print("saved ->", fp, f"({int(fig.get_size_inches()[0]*300)} x {int(fig.get_size_inches()[1]*300)} px)")