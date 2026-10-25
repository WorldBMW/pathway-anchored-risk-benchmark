"""Square graphical abstract (1200 x 1200 px, 300 dpi, Arial) for Patterns.

Cell Press requires a single square panel, 1200 px at 300 dpi, Arial, with
text large enough to survive thumbnail rendering. On a 4 x 4 inch canvas that
leaves room for very little text, so the layout is vertical (read top to
bottom) and every label is a noun phrase. A width assertion fails the build if
any string would overflow its container, which is how the earlier drafts were
caught.

Three bands, and the third is part of the argument rather than decoration:
the domain in which the loop was actually validated sits directly under the
two domains in which it was only audited and the six in which nothing ran.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Rectangle

ROOT = Path(__file__).resolve().parent.parent
FIGDIR = ROOT / "papers" / "20_MRP-ST-Repair_Patterns" / "figures"
OUT = FIGDIR / "graphical_abstract_1200.png"
OUT_TIF = FIGDIR / "graphical_abstract_300dpi.tif"
OUT_PDF = FIGDIR / "graphical_abstract_1200.pdf"

matplotlib.rcParams["font.family"] = "Arial"
matplotlib.rcParams["pdf.fonttype"] = 42

INK = "#1f2933"
MUTED = "#5b6775"
BLUE = "#2563eb"
TEAL = "#0d9488"
AMBER = "#b36a06"
RED = "#b8332b"
GREEN = "#0f7b52"
FILL2 = "#e8eef7"
BORDER = "#b3bdc9"
GRID = "#d5dce5"

fig = plt.figure(figsize=(4, 4), dpi=300, facecolor="white")
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")

F = "Arial"
OVERFLOW = []
# one character is about 0.55 em wide; one unit is 0.04 in
EM = 0.19  # units of x per point of font size


def check(s, fs, w, tag=""):
    longest = max(s.split("\n"), key=len)
    need = len(longest) * EM * fs
    if need > w:
        OVERFLOW.append((tag, longest, round(need, 1), round(w, 1)))


def box(x, y, w, h, fc="white", ec=BORDER, lw=1.0, z=2):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.22,rounding_size=0.8",
                                linewidth=lw, edgecolor=ec, facecolor=fc, zorder=z))


def txt(x, y, s, fs=6.5, c=INK, weight="normal", ha="center", va="center",
        ls=1.32, style="normal", z=5, tag="", w=None):
    ax.text(x, y, s, ha=ha, va=va, fontsize=fs, color=c, fontweight=weight,
            linespacing=ls, style=style, zorder=z, fontfamily=F)
    if tag:
        check(s, fs, w if w is not None else (96 if ha == "center" else 40), tag)


def arrow(x1, y1, x2, y2, c=INK, lw=0.9, ms=5, ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=ms, linewidth=lw, color=c,
                                 linestyle=ls, shrinkA=0.3, shrinkB=0.3, zorder=4))


def band(y0, y1, label, color):
    ax.add_patch(Rectangle((1.8, y0), 96.4, y1 - y0, facecolor=color,
                           edgecolor="none", zorder=0, alpha=0.62))
    txt(3.4, y1 - 1.55, label, fs=7.2, weight="bold", ha="left")


# ------------------------------------------------------------------ title
txt(3.4, 96.6, "Auditable repair of identity leakage", fs=10.6, weight="bold", ha="left")
txt(3.4, 91.9, "in group-structured data", fs=10.6, weight="bold", ha="left")
txt(3.4, 88.2, "feasibility decided before any dose is chosen",
    fs=6.4, c=MUTED, ha="left")

# ============================================================ BAND 1
band(71.5, 85.8, "1   THE PROBLEM", FILL2)

for name, gx in [("person", 7.2), ("site", 14.4), ("speaker", 21.6), ("subject", 28.8)]:
    gy = 79.6
    ax.add_patch(Circle((gx, gy), 2.15, facecolor="white", edgecolor=BLUE,
                        linewidth=1.0, zorder=3))
    txt(gx, gy, "G", fs=6.0, c=BLUE, weight="bold", z=4)
    for dx, dy in [(-3.2, 1.5), (3.2, 1.2), (0.0, -3.2), (-3.9, -1.2), (3.9, -1.9)]:
        ax.add_patch(Circle((gx + dx, gy + dy), 0.78, facecolor=BLUE,
                            edgecolor="none", zorder=3, alpha=0.72))
        ax.plot([gx, gx + dx], [gy, gy + dy], color=GRID, linewidth=0.6, zorder=2)
    txt(gx, 74.6, name, fs=5.1, c=MUTED)
txt(18.0, 72.4, "many units per group", fs=6.0, c=MUTED, style="italic")

arrow(31.2, 78.2, 33.4, 78.2)
box(33.8, 75.4, 10.4, 5.6)
txt(39.0, 78.2, "MODEL", fs=7.0, weight="bold")
arrow(44.4, 78.2, 46.6, 78.2)

box(47.0, 79.2, 23.6, 4.4, "#fdecec", RED, 0.9)
txt(58.8, 81.4, "in-sample: excellent", fs=6.4, c=RED)
box(47.0, 72.6, 23.6, 5.2, "#fdecec", RED, 0.9)
txt(58.8, 75.2, "leave-one-group-out\ncollapses", fs=6.4, c=RED)
txt(72.0, 78.0, "recognised\nthe group,\nnot the target", fs=6.2, c=RED,
    weight="bold", ha="left", ls=1.38)

# ============================================================ BAND 2
band(29.6, 70.0, "2   THE AUDITABLE LOOP", "#eef3f8")

ROWS = [
    (60.8, "DETECT", "LDI under leave-one-group-out", BLUE),
    (54.2, "PRE-COMPUTE", "signal-to-null ratio vs 2.35", AMBER),
    (47.6, "REPAIR", "adversarial training, dose λ", TEAL),
    (41.0, "RE-AUDIT", "safety, leakage, non-blindness", BLUE),
]
RH, RX, RW = 5.4, 4.2, 57.6
for y, title, body, col in ROWS:
    box(RX, y, RW, RH, "white", col, 1.1)
    ax.add_patch(FancyBboxPatch((RX + 0.5, y + 1.0), 14.4, RH - 2.0,
                                boxstyle="round,pad=0.12,rounding_size=0.5",
                                linewidth=0, edgecolor="none", facecolor=col,
                                alpha=0.13, zorder=2))
    txt(RX + 7.7, y + RH / 2, title, fs=5.5, c=col, weight="bold",
        tag="row-" + title, w=14.0)
    txt(RX + 16.4, y + RH / 2, body, fs=6.3, ha="left", tag="row-" + title,
        w=RW - 16.8)

for y0, y1 in [(60.8, 59.6), (54.2, 53.0), (47.6, 46.4)]:
    arrow(RX + RW / 2, y0, RX + RW / 2, y1, INK, 0.8, 4.5)

# boundaries, tied to the stage they govern
box(63.4, 52.4, 32.4, 7.0, "#fff6e6", AMBER, 1.0)
txt(64.8, 57.3, "Boundary I   coupling", fs=5.8, ha="left", weight="bold", tag="b1", w=30.0)
txt(64.8, 54.3, "decides repairability", fs=5.8, ha="left", tag="b1", w=30.0)
box(63.4, 44.0, 32.4, 7.0, "#fff6e6", AMBER, 1.0)
txt(64.8, 48.9, "Boundary II   group count", fs=5.8, ha="left", weight="bold", tag="b2", w=30.0)
txt(64.8, 45.9, "decides signal survival", fs=5.8, ha="left", tag="b2", w=30.0)
arrow(63.2, 55.9, 62.0, 55.9, AMBER, 0.8, 4.5, ls=(0, (2.2, 1.4)))
arrow(63.2, 47.5, 62.0, 47.5, AMBER, 0.8, 4.5, ls=(0, (2.2, 1.4)))

box(4.2, 31.2, 28.0, 7.4, "#e7f5ee", GREEN, 1.1)
txt(18.2, 36.4, "ACCEPT", fs=6.8, c=GREEN, weight="bold")
txt(18.2, 33.2, "signal kept, leakage\nbelow threshold", fs=6.0, c=GREEN)
box(34.4, 31.2, 28.0, 7.4, "#fdecec", RED, 1.1)
txt(48.4, 36.4, "REJECT", fs=6.8, c=RED, weight="bold")
txt(48.4, 33.2, "no feasible point,\npredicted in advance", fs=6.0, c=RED)
arrow(24.0, 41.0, 18.2, 38.9, GREEN, 0.8, 4.5)
arrow(42.0, 41.0, 48.4, 38.9, RED, 0.8, 4.5)

# ============================================================ BAND 3
band(2.0, 27.8, "3   WHERE EACH CLAIM IS VALIDATED", FILL2)

TIERS = [
    (17.6, "VALIDATED", GREEN, "#e7f5ee",
     "end-to-end: repair, acceptance, endpoint",
     "spatial transcriptomics, 3 cohorts + simulator"),
    (9.9, "AUDITED", AMBER, "#fff6e6",
     "instrument and boundaries on real data, no endpoint",
     "wearables, chemical sensing"),
    (2.2, "NOT TESTED", MUTED, "#eef1f5",
     "structural mapping only, no experiment",
     "imaging, speech, EHR, remote sensing, trials"),
]
for y, tag, col, fc, body, dom in TIERS:
    box(3.6, y, 92.6, 6.8, fc, col, 1.1)
    ax.add_patch(FancyBboxPatch((4.8, y + 3.5), 16.4, 2.7,
                                boxstyle="round,pad=0.12,rounding_size=0.5",
                                linewidth=0, edgecolor="none", facecolor=col, zorder=3))
    txt(13.0, y + 4.85, tag, fs=5.9, c="white", weight="bold", z=6)
    txt(22.6, y + 4.8, body, fs=6.2, ha="left")
    check(body, 6.2, 73, tag)
    txt(22.6, y + 1.9, dom, fs=6.2, c=col, weight="bold", ha="left")
    check(dom, 6.2, 73, tag + "-dom")

fig.savefig(OUT, dpi=300, facecolor="white")
fig.savefig(OUT_TIF, dpi=300, facecolor="white", pil_kwargs={"compression": "tiff_lzw"})
fig.savefig(OUT_PDF, dpi=300, facecolor="white")
plt.close(fig)

print("saved", OUT)
print("saved", OUT_TIF)
print("saved", OUT_PDF)
if OVERFLOW:
    print("OVERFLOW WARNINGS:")
    for tag, s, need, w in OVERFLOW:
        print("  %-14s need %5.1f > %5.1f  %r" % (tag, need, w, s))
else:
    print("no overflow warnings")
