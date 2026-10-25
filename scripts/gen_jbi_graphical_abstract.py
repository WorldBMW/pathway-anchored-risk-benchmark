# -*- coding: utf-8 -*-
"""gen_jbi_graphical_abstract.py — JBI graphical abstract (Elsevier 2.5:1, 1328x531 px)

Three-panel audit story; numbers read from results/paper_v10_numbers.json.
Output: papers/08_JBI/GraphicalAbstract_JBI.png
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "papers" / "08_JBI"
N = json.load(open(ROOT / "results" / "paper_v10_numbers.json", encoding="utf-8"))
A = N['ablation']; EXT = N['external']
_ns = A.get('NOSUP')
if _ns is None:
    print("WARN: 'NOSUP' absent from results/paper_v10_numbers.json - graphical "
          "abstract renders without the label-free arm value; rerun gen_figures_v10.py "
          "after the NO-SUP runs and regenerate.")
_na = A.get('NOALL')
if _na is None:
    print("WARN: 'NOALL' absent from results/paper_v10_numbers.json - graphical "
          "abstract renders without the label-/prior-free arm value; rerun "
          "gen_figures_v10.py after the NO-ALL runs and regenerate.")

NAVY = "#1F3864"; STEEL = "#2F5496"; GREY = "#5A5A5A"
GREEN = "#2E7D32"; AMBER = "#B26A00"; RED = "#B02418"; PURPLE = "#7030A0"
LBLUE = "#EAF0FA"; PANEL2 = "#F4F2F8"

plt.rcParams['font.family'] = 'DejaVu Sans'
fig = plt.figure(figsize=(13.28, 5.31), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1328); ax.set_ylim(0, 531); ax.axis('off')

ax.add_patch(FancyBboxPatch((8, 8), 1312, 515, boxstyle="round,pad=0,rounding_size=18",
                            fc="#FBFBFD", ec="#CCCCCC", lw=1.2, zorder=0))

ax.text(664, 500, "Auditing label memorization in small-sample spatial transcriptomics",
        ha="center", va="center", fontsize=20, fontweight="bold", color=NAVY)
ax.text(664, 472, "A pathway-anchored benchmark with cross-platform validation in cervical lesions",
        ha="center", va="center", fontsize=12.5, color=GREY, style="italic")


def panel(x, w, fc, ec, title):
    ax.add_patch(FancyBboxPatch((x, 56), w, 388, boxstyle="round,pad=0,rounding_size=14",
                                fc=fc, ec=ec, lw=2.0, zorder=1))
    ax.add_patch(FancyBboxPatch((x, 392), w, 52, boxstyle="round,pad=0,rounding_size=14",
                                fc=ec, ec=ec, lw=0, zorder=2))
    ax.text(x + w / 2, 418, title, ha="center", va="center",
            fontsize=14, fontweight="bold", color="white", zorder=3)


P1X, P2X, P3X, W = 28, 462, 896, 404

# ================= Panel 1: problem ====================================
panel(P1X, W, LBLUE, STEEL, "1  THE PROBLEM")
# 35 dots: 7 cols x 5 rows, centered in panel
xs = [P1X + 83 + c * 40 for c in range(7)]
ys = [370 - r * 29 for r in range(5)]
DISEASED_IDX = {2, 9, 20, 30}
for i in range(35):
    r, c = divmod(i, 7)
    d = i in DISEASED_IDX
    ax.add_patch(Circle((xs[c], ys[r]), 10.5, fc=RED if d else "#7FA8D8",
                        ec="#333333", lw=0.8, zorder=3))
# AUC badge
ax.add_patch(FancyBboxPatch((P1X + 36, 186), W - 72, 38,
             boxstyle="round,pad=0,rounding_size=8", fc="white", ec=RED, lw=1.8))
ax.text(P1X + W / 2, 205, "In-sample sample-level AUC = 1.00",
        ha="center", va="center", fontsize=11.5, fontweight="bold", color=RED)
ax.text(P1X + W / 2, 162, "learned disease signal ...",
        ha="center", va="center", fontsize=11, color=NAVY)
ax.text(P1X + W / 2, 138, "... or four memorized labels?",
        ha="center", va="center", fontsize=11.5, fontweight="bold", color=NAVY)
ax.text(P1X + W / 2, 102, "31 normal vs 4 diseased sections",
        ha="center", fontsize=10.5, color=NAVY)
ax.text(P1X + W / 2, 80, "(1 HSIL  ·  2 SCC  ·  1 adenocarcinoma)",
        ha="center", fontsize=9.5, color=GREY)

# ================= Panel 2: audit ======================================
panel(P2X, W, PANEL2, NAVY, "2  THE AUDIT")
# col 1 = nested label -> proxy -> prior cascade; col 2 = mechanism ablations
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
# cascade spine connecting the four col-1 chips
ax.add_patch(FancyArrowPatch((cx1 - 60, 342), (cx1 - 60, 208),
             arrowstyle="-|>", mutation_scale=13, lw=1.6, color=NAVY,
                             linestyle=(0, (4, 2))))
ax.text(cx1 - 70, 278, "label\nproxy\nprior", ha="right", va="center",
        fontsize=8.8, color=NAVY, linespacing=1.15)
lines = [
    "prespecified multi-seed ablations",
    "whole-sample fitted-score permutation",
    "paired hold-out: semi-supervised vs zero-target",
    "30 expression-matched random-gene nulls",
    "external inference without target labels",
    "GeoMx · 14 head-and-neck sections · TCGA-CESC",
]
for i, t in enumerate(lines):
    ax.text(P2X + 30, 193 - i * 22, "\u2022 " + t,
            ha="left", va="center", fontsize=10.5,
            fontweight="bold" if i == 4 else "normal", color="#222222")

# ================= Panel 3: graded verdict ============================
panel(P3X, W, "white", "#444444", "3  GRADED EVIDENCE")
TX = P3X + 46


def tag(y, txt, col):
    ax.add_patch(FancyBboxPatch((P3X + 22, y - 11), 8, 22,
                 boxstyle="round,pad=0,rounding_size=3", fc=col, ec=col))
    ax.text(TX, y, txt, ha="left", va="center", fontsize=12.5, fontweight="bold", color=col)


tag(362, "SUPPORTED", GREEN)
ax.text(TX, 337, "Spatial structure survives label removal", fontsize=11.2, color="#222222")
ax.text(TX, 316, "and coordinate permutation (p\u22640.001)", fontsize=11.2, color="#222222")
ax.text(TX, 295, "Pathway panel > random panels (14/14)", fontsize=11.2, color="#222222")

tag(259, "SUGGESTIVE", AMBER)
_ns_tau = _ns['tau_mean'] if _ns is not None else float('nan')
_na_tau = _na['tau_mean'] if _na is not None else float('nan')
ax.text(TX, 234, f"Ordering: \u03c4 {A['FULL']['tau_mean']:.2f} \u2192 {A['NOPROG']['tau_mean']:.2f} "
        f"\u2192 {_ns_tau:.2f} \u2192 {_na_tau:.2f}", fontsize=11.2, color="#222222")
ax.text(TX, 213, "labels \u2192 proxy \u2192 regularizer removed", fontsize=11.2, color="#222222")
ax.text(TX, 192, "GeoMx rank preserved; direction reversed", fontsize=11.2, color="#222222")

tag(158, "UNSUPPORTED", RED)
ax.text(TX, 133, "Grading \u00b7 prognosis \u00b7 cross-organ discrimination", fontsize=10.8, color="#222222")
ax.text(TX, 111, "LOSO AUC \u22480.50 vs in-sample AUC 1.00",
        fontsize=11.2, fontweight="bold", color=RED)

ax.add_patch(FancyBboxPatch((P3X + 22, 58), W - 44, 42,
             boxstyle="round,pad=0,rounding_size=8", fc=NAVY, ec=NAVY))
ax.text(P3X + W / 2, 89, "MRP-ST: five checks before clinical claims",
        ha="center", va="center", fontsize=11.2, fontweight="bold", color="white")
ax.text(P3X + W / 2, 71, "for studies with \u226410 independent disease samples",
        ha="center", va="center", fontsize=10.5, color="white")

# ---- arrows -----------------------------------------------------------
for x0 in (P1X + W + 4, P2X + W + 4):
    ax.add_patch(FancyArrowPatch((x0, 250), (x0 + 26, 250),
                 arrowstyle="-|>", mutation_scale=26, lw=2.4, color=NAVY))

ax.text(664, 30, "Perfect fit \u2260 generalization: remove labels, test whole samples, and grade the evidence.",
        ha="center", va="center", fontsize=12, color=GREY, style="italic")

fp = OUT / "GraphicalAbstract_JBI.png"
fig.savefig(fp, dpi=300, facecolor='white')
tiff = OUT / "GraphicalAbstract_JBI.tiff"
fig.savefig(tiff, dpi=300, facecolor='white', pil_kwargs={'compression': 'tiff_lzw'})
print("saved ->", fp)
print("saved ->", tiff)
