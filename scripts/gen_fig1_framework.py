# -*- coding: utf-8 -*-
"""
Fig. 1 -- Pathway-anchored multimodal spatial risk framework.

Publication-quality architecture diagram for CMPB:
  * clean left-to-right 4-column flow (inputs -> encoders -> fusion -> heads)
  * no overlapping text, no crossed arrows, no canvas overflow
  * vector-grade raster (600 dpi) + PDF vector output
Output: papers/07_CSBJ_v10/Figures/Fig1_Framework.{png,pdf}
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "mathtext.fontset": "dejavusans",
    "savefig.dpi": 600,
    "figure.dpi": 200,
})

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "papers", "07_CSBJ_v10", "Figures")
os.makedirs(OUT, exist_ok=True)

C = {                                  # fill, edge
    "in":  ("#EAF1F8", "#4A7EBB"),
    "enc": ("#E7F1E3", "#5B8C4A"),
    "fus": ("#FDF4DC", "#C79A2E"),
    "hd":  ("#FCEBE0", "#C4622D"),
    "obj": ("#F2F2F5", "#7A7A85"),
}
INK, GREY, DIM = "#1B1B1B", "#555555", "#6B6B6B"

W, H = 100.0, 63.0


def box(ax, x0, y0, w, h, title, lines=(), fill="#fff", edge="#000",
        tsize=9.6, lsize=8.3):
    ax.add_patch(FancyBboxPatch(
        (x0, y0), w, h, boxstyle="round,pad=0,rounding_size=1.5",
        linewidth=1.5, edgecolor=edge, facecolor=fill, zorder=2))
    cx = x0 + w / 2.0
    gap = h / (len(lines) + 2)
    ax.text(cx, y0 + h - gap, title, ha="center", va="center",
            fontsize=tsize, fontweight="bold", color=INK, zorder=3)
    for i, ln in enumerate(lines):
        ax.text(cx, y0 + h - gap * (i + 2), ln, ha="center", va="center",
                fontsize=lsize, color=GREY, zorder=3)


def arrow(ax, p, q, color=DIM, lw=1.5, ls="-"):
    ax.add_patch(FancyArrowPatch(
        p, q, arrowstyle="-|>", mutation_scale=13, linewidth=lw,
        color=color, linestyle=ls, shrinkA=1, shrinkB=1, zorder=1))


def hexicon(ax, cx, cy, r=2.7):
    ax.add_patch(Circle((cx, cy), r * 0.30, facecolor="#7A7A85",
                        edgecolor="none", zorder=4))
    for k in range(6):
        a = np.deg2rad(60 * k - 90)
        x, y = cx + r * np.cos(a), cy + r * np.sin(a)
        ax.plot([cx, x], [cy, y], color="#BCBCC4", lw=0.9, zorder=3)
        ax.add_patch(Circle((x, y), r * 0.20, facecolor="#C79A2E",
                            edgecolor="none", zorder=4))


fig, ax = plt.subplots(figsize=(7.4, 4.66))
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")

# ------------------------------------------------------------- geometry
X_IN,  W_IN  = 1.2, 16.5
X_ENC, W_ENC = 21.5, 22.0
X_FUS, W_FUS = 48.0, 18.0
X_HD,  W_HD  = 70.5, 20.5
YBIG, YSMALL, BH = 49.0, 24.6, 11.6
YFUS0, YFUS1 = 18.6, 54.8
YMID = (YBIG + YSMALL) / 2.0

# --------------------------------------------------------------- inputs
box(ax, X_IN, YBIG - BH / 2, W_IN, BH, "10x Visium",
    ["expression profile", "4,991 genes / spot"], *C["in"])
box(ax, X_IN, YSMALL - BH / 2, W_IN, BH, "H&E image",
    ["224 x 224 px patch", "per Visium spot"], *C["in"])

# ------------------------------------------------------------- encoders
box(ax, X_ENC, YBIG - BH / 2, W_ENC, BH, "Expression encoder",
    ["2-layer MLP", r"$\rightarrow\ z_{g}\ \in\ \mathbb{R}^{128}$"], *C["enc"])
box(ax, X_ENC, YSMALL - BH / 2, W_ENC, BH, "Image encoder",
    ["frozen UNI (Nat Med 2024)",
     r"$\rightarrow\ z_{i}\ \in\ \mathbb{R}^{128}$"], *C["enc"])

# --------------------------------------------------------------- fusion
box(ax, X_FUS, YFUS0, W_FUS, YFUS1 - YFUS0, "Cross-modal\nattention",
    ["4 attention heads", r"$z_{g},\ z_{i}\ \rightarrow\ z_{m}$",
     r"$z_{m}\ \in\ \mathbb{R}^{128}$"], *C["fus"], tsize=10.4, lsize=8.2)

# ---------------------------------------------------------------- heads
box(ax, X_HD, YBIG - BH / 2, W_HD, BH, "Risk head",
    ["per-spot linear", r"output $r$  (risk score)"], *C["hd"])
box(ax, X_HD, YMID - BH / 2, W_HD, BH, "HPV-pathway head",
    ["alignment to the", "108 KEGG-HPV genes"], *C["hd"])
box(ax, X_HD, YSMALL - BH / 2, W_HD, BH, "Reconstruction head",
    ["linear", r"$\rightarrow\ \hat{x}$"], *C["hd"])

# --------------------------------------------------------------- arrows
arrow(ax, (X_IN + W_IN, YBIG), (X_ENC, YBIG))
arrow(ax, (X_IN + W_IN, YSMALL), (X_ENC, YSMALL))
arrow(ax, (X_ENC + W_ENC, YBIG), (X_FUS, YBIG - 3.2))
arrow(ax, (X_ENC + W_ENC, YSMALL), (X_FUS, YSMALL + 3.2))
for yy in (YBIG, YMID, YSMALL):
    arrow(ax, (X_FUS + W_FUS, yy), (X_HD, yy))

# ------------------------------------------------ NO-IMAGE call-out note
ax.text(X_ENC + W_ENC / 2, YSMALL - BH / 2 - 3.6,
        "NO-IMAGE ablation: image-encoder output set to zero",
        ha="center", va="center", fontsize=7.6, color="#B0492A",
        style="italic", zorder=4)

# --------------------------------------------- training-objective band
BY0, BY1 = 1.3, 14.8
ax.add_patch(FancyBboxPatch(
    (1.2, BY0), 97.6, BY1 - BY0,
    boxstyle="round,pad=0,rounding_size=1.5",
    linewidth=1.5, edgecolor=C["obj"][1], facecolor=C["obj"][0], zorder=2))

hexicon(ax, 9.0, 10.4, r=2.7)
ax.text(9.0, 5.4, "6-NN", ha="center", va="center",
        fontsize=8.0, color=GREY, fontweight="bold", zorder=4)

ax.text(17.0, 11.7, "Training objective", ha="left", va="center",
        fontsize=9.2, fontweight="bold", color=INK, zorder=4)

terms = ["recon", "var", "hpv", "sup", "prog", "neigh"]
eq = r"$L\;=\;$" + r"$\;+\;$".join(
    r"$\lambda_{%s}\cdot L_{%s}$" % (t, t) for t in terms)
ax.text(17.0, 7.4, eq, ha="left", va="center", fontsize=9.4,
        color=INK, zorder=4)

ax.text(17.0, 3.7,
        r"$\lambda_{neigh}$ = agreement with the 6 nearest neighbours "
        r"on the Visium hexagonal lattice",
        ha="left", va="center", fontsize=7.4, color=GREY, zorder=4)

# heads -> objective band
arrow(ax, (X_HD + W_HD / 2, YSMALL - BH / 2), (X_HD + W_HD / 2, BY1 + 0.4),
      color="#A8A8B0", lw=1.2, ls=(0, (4, 3)))

fig.subplots_adjust(left=0.004, right=0.996, top=0.996, bottom=0.004)
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(OUT, f"Fig1_Framework.{ext}"),
                dpi=600, facecolor="white")
plt.close(fig)
print("saved Fig1_Framework.png / .pdf")
