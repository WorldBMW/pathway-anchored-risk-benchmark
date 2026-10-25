"""Graphical abstract for the Patterns submission.

Design rule: the figure must read as a general data-science contribution.
Spatial transcriptomics appears only in the bottom band, as the validated
instance among three explicitly labelled evidence tiers.
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Rectangle

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "papers" / "20_MRP-ST-Repair_Patterns" / "figures" / "graphical_abstract.png"

INK = "#1f2933"
MUTED = "#5b6775"
BLUE = "#2563eb"
TEAL = "#0d9488"
AMBER = "#c2740a"
RED = "#c0392b"
GREEN = "#0f7b52"
FILL = "#f4f6f9"
FILL2 = "#e8eef7"
BORDER = "#b9c4d1"
GRID = "#dde3ea"

fig = plt.figure(figsize=(16, 9), dpi=200, facecolor="white")
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 16)
ax.set_ylim(0, 9)
ax.axis("off")


def box(x, y, w, h, text, fc=FILL, ec=BORDER, fs=10.5, tc=INK, lw=1.3, bold=False, pad=0.09, va="center"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad={pad},rounding_size=0.12",
                                linewidth=lw, edgecolor=ec, facecolor=fc, zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va=va, fontsize=fs, color=tc,
            zorder=3, linespacing=1.35,
            fontweight="bold" if bold else "normal", fontfamily="DejaVu Sans")


def arrow(x1, y1, x2, y2, color=INK, lw=1.6, style="-|>", ms=11, ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=ms,
                                 linewidth=lw, color=color, linestyle=ls,
                                 shrinkA=1, shrinkB=1, zorder=4))


def band(y0, y1, label, color):
    ax.add_patch(Rectangle((0.35, y0), 15.3, y1 - y0, facecolor=color,
                           edgecolor="none", zorder=0, alpha=0.55))
    ax.text(0.55, y1 - 0.30, label, ha="left", va="center", fontsize=11.5,
            color=INK, fontweight="bold", zorder=5)


# ---------------------------------------------------------------- title
ax.text(0.55, 8.55, "Auditable repair of identity leakage in group-structured data",
        ha="left", va="center", fontsize=21, color=INK, fontweight="bold")
ax.text(0.55, 8.13, "A general data-science failure mode \u2014 and a repair loop that can be audited, with its feasibility decided before repair is attempted",
        ha="left", va="center", fontsize=11.5, color=MUTED)

# ================================================================ BAND 1
band(5.50, 8.00, "1  \u00b7  THE PROBLEM", FILL2)

# generic group clusters: deliberately domain-neutral, labelled only as groups G
groups = [("person", 1.35), ("site", 3.05), ("speaker", 4.75), ("subject", 6.45)]
for name, gx in groups:
    ax.add_patch(Circle((gx, 6.95), 0.30, facecolor="white", edgecolor=BLUE, linewidth=1.6, zorder=3))
    ax.text(gx, 6.95, "G", ha="center", va="center", fontsize=9.5,
            color=BLUE, fontweight="bold", zorder=4)
    for k, (dx, dy) in enumerate([(-0.52, 0.30), (0.55, 0.24), (0.0, -0.52), (-0.62, -0.20), (0.62, -0.36)]):
        ax.add_patch(Circle((gx + dx, 6.95 + dy), 0.105, facecolor=BLUE, edgecolor="none", zorder=3, alpha=0.75))
        ax.plot([gx, gx + dx], [6.95, 6.95 + dy], color=GRID, linewidth=0.9, zorder=2)
    ax.text(gx, 6.12, name, ha="center", va="center", fontsize=9, color=MUTED)
ax.text(3.95, 5.78, "each group contributes many observations \u2192 observations are not exchangeable",
        ha="center", va="center", fontsize=10, color=MUTED, style="italic")

arrow(6.95, 6.95, 7.65, 6.95, INK, 1.5)
box(7.72, 6.56, 1.62, 0.78, "MODEL", FILL, INK, 12, INK, bold=True)
arrow(9.40, 6.95, 10.05, 6.95, INK, 1.5)

box(10.10, 7.02, 2.42, 0.68, "in-sample fit\nlooks excellent", "#fdecec", RED, 9.6, RED)
box(10.10, 6.20, 2.42, 0.68, "leave-one-group-out\ncollapses", "#fdecec", RED, 9.6, RED)
ax.text(12.85, 6.95, "the model recognised\nthe group, not the\ntarget property",
        ha="left", va="center", fontsize=10.5, color=RED, fontweight="bold", linespacing=1.35)

# ================================================================ BAND 2
band(2.42, 5.42, "2  \u00b7  THE AUDITABLE LOOP", "#eef3f8")

Y_LOOP = 3.52
H_LOOP = 1.22
steps = [
    (0.55, "DETECT", "LDI under\nleave-one-group-out", BLUE),
    (3.10, "PRE-COMPUTE", "\u03c4_base / \u03c3\u0302  vs  2.35\n(Proposition 1)", AMBER),
    (5.70, "REPAIR", "training-time\nadversarial, dose \u03bb", TEAL),
    (8.30, "RE-AUDIT", "three axes: safety,\nleakage, non-blindness", BLUE),
]
for x, title, body, col in steps:
    box(x, Y_LOOP, 2.28, H_LOOP, "", "white", col, lw=1.8)
    ax.text(x + 1.14, Y_LOOP + 0.98, title, ha="center", va="center", fontsize=10.5,
            color=col, fontweight="bold")
    ax.text(x + 1.14, Y_LOOP + 0.42, body, ha="center", va="center", fontsize=9.6,
            color=INK, linespacing=1.35)

for x0 in (2.83, 5.43, 8.03):
    arrow(x0, Y_LOOP + 0.61, x0 + 0.27, Y_LOOP + 0.61, INK, 1.5)

YC = Y_LOOP + 0.61
arrow(10.58, YC, 11.00, YC, INK, 1.5)
box(11.05, 3.72, 1.42, 0.86, "ACCEPT\n(group level)", "#e7f5ee", GREEN, 8.8, GREEN, bold=True)
box(11.05, 2.62, 1.42, 0.72, "REJECT", "#fdecec", RED, 9.4, RED, bold=True)
arrow(12.52, 4.15, 12.90, 4.15, GREEN, 1.5)
arrow(12.52, 2.98, 12.90, 2.98, RED, 1.5)

box(12.95, 3.72, 2.72, 0.86, "signal survives, group dependence\nis gone, instrument not blinded",
    "#e7f5ee", GREEN, 9.0, INK)
box(12.95, 2.62, 2.72, 0.72, "no feasible operating point \u2014\npredicted before any dose is chosen",
    "#fdecec", RED, 9.0, INK)

# decision-boundary callouts, sitting under the loop and tied to their stages
box(0.55, 2.60, 3.20, 0.72, "Boundary I   label\u2013identity coupling\ndecides whether repair is possible at all",
    "#fff6e6", AMBER, 9.0, INK)
box(4.05, 2.60, 3.20, 0.72, "Boundary II   group count\ndecides whether the signal survives the dose",
    "#fff6e6", AMBER, 9.0, INK)
arrow(2.15, 3.35, 2.15, Y_LOOP, AMBER, 1.2, ls=(0, (3, 2)))
arrow(5.65, 3.35, 5.65, Y_LOOP, AMBER, 1.2, ls=(0, (3, 2)))
ax.text(9.55, 2.96, "post-hoc removal fails: after training,\nidentity and signal share directions",
        ha="center", va="center", fontsize=9.2, color=RED, style="italic", linespacing=1.3)

# ================================================================ BAND 3
band(0.28, 2.32, "3  \u00b7  WHERE EACH CLAIM IS VALIDATED", FILL2)

tiers = [
    (0.55, "VALIDATED", "end-to-end: repair, acceptance,\nendpoint, planted controls, readout",
     GREEN, "#e7f5ee", "spatial transcriptomics\n(3 cohorts + simulator)"),
    (5.40, "AUDITED", "instrument and both boundaries\ntested on real data; no endpoint",
     AMBER, "#fff6e6", "wearables (30 subjects)\nchemical sensing (10 batches)"),
    (10.25, "NOT TESTED", "structural mapping of the\nsame objects \u2014 no experiment",
     MUTED, "#eef1f5", "imaging \u00b7 speech \u00b7 EHR \u00b7 remote\nsensing \u00b7 recommender \u00b7 trials"),
]
for x, tag, body, col, fc, dom in tiers:
    ax.add_patch(FancyBboxPatch((x, 0.44), 4.55, 1.42, boxstyle="round,pad=0.05,rounding_size=0.10",
                                linewidth=1.5, edgecolor=col, facecolor=fc, zorder=2))
    ax.add_patch(FancyBboxPatch((x + 0.14, 1.50), 1.46, 0.26, boxstyle="round,pad=0.02,rounding_size=0.06",
                                linewidth=0, edgecolor="none", facecolor=col, zorder=3))
    ax.text(x + 0.87, 1.63, tag, ha="center", va="center", fontsize=8.6, color="white",
            fontweight="bold", zorder=4)
    ax.text(x + 0.18, 1.10, body, ha="left", va="center", fontsize=8.6, color=INK, linespacing=1.32, zorder=4)
    ax.text(x + 0.18, 0.70, dom, ha="left", va="center", fontsize=9.0, color=col,
            fontweight="bold", linespacing=1.32, zorder=4)

fig.savefig(OUT, dpi=200, facecolor="white", bbox_inches="tight", pad_inches=0.06)
plt.close(fig)
print("saved", OUT)
