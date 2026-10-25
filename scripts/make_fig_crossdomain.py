#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""make_fig_crossdomain.py — Figure 5 for the Patterns manuscript.

Cross-domain (non-biological) validation of the audit instrument and the repair
operator on UCI HAR (wearable activity recognition, G = 30 subjects) and UCI Gas
Sensor Array Drift (chemical sensing, G = 10 measurement batches).

Panels
  A  LDI vs dose λ (gate 1.645)                       — acceptance axis
  B  τ_LOO (solid) vs τ_LGO (open) vs λ               — sibling-unit inflation
  C  group-identity lift (probe accuracy / chance)    — the operator works
  D  inflation τ_LOO − τ_LGO vs λ                     — leakage channel closes

Presentation. Every dose carries three training seeds, and all three are drawn:
faint markers are the individual seeds, the line joins the seed means, and the
error bar is the standard deviation across those three seeds (never the standard
error of the mean). The audit's whole claim is about seed spread, so hiding it
behind a mean-only line would misrepresent what the figure is evidence for.

Usage:  python scripts/make_fig_crossdomain.py
"""
import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results" / "crossdomain_audit.json"
OUT = ROOT / "papers" / "20_MRP-ST-Repair_Patterns" / "figures"

d = json.loads(RES.read_text(encoding="utf-8"))
S = d["summary"]
RUNS = d["runs"]
DOMS = ["HAR", "GASDRIFT"]
NAME = {"HAR": "HAR (wearable activity)\nG = 30 subjects",
        "GASDRIFT": "Gas sensor drift (chemical)\nG = 10 batches"}
COL = {"HAR": "#1f4e79", "GASDRIFT": "#b45309"}
SHORT = {"HAR": "HAR", "GASDRIFT": "gas drift"}
LDI_GATE = 1.645

# --- per-seed records, indexed by domain and dose --------------------------
PER = defaultdict(lambda: defaultdict(list))
for r in RUNS:
    PER[r["domain"]][float(r["lam"])].append(r)

LAMS = sorted(PER["HAR"])


def series(dom, key):
    """Mean and SD (ddof=1) across the training seeds at each dose."""
    m = np.array([np.mean([x[key] for x in PER[dom][lam]]) for lam in LAMS])
    s = np.array([np.std([x[key] for x in PER[dom][lam]], ddof=1) for lam in LAMS])
    return m, s


def raw(dom, key):
    return [[x[key] for x in PER[dom][lam]] for lam in LAMS]


def draw(ax, dom, key, fmt, alpha_line=1.0, jitter=0.075, seed_jitter=0.055):
    """Mean line + SD bars + one marker per training seed."""
    m, s = series(dom, key)
    c = COL[dom]
    ax.errorbar(LAMS, m, yerr=s, fmt=fmt, color=c, lw=1.6, ms=5,
                capsize=3, elinewidth=1.0, capthick=1.0,
                alpha=alpha_line, zorder=3)
    rng = np.random.default_rng(0)
    for i, vals in enumerate(raw(dom, key)):
        jx = LAMS[i] + rng.uniform(-seed_jitter, seed_jitter, len(vals))
        mk = fmt[-1]
        ax.plot(jx, vals, mk, ms=3.0, color=c, alpha=0.40,
                mfc="none" if mk == "s" else c, mec=c, zorder=2)


fig, axes = plt.subplots(2, 2, figsize=(9.2, 6.6))
ax = axes.ravel()

for dom in DOMS:
    lb = NAME[dom].replace("\n", " ")
    draw(ax[0], dom, "ldi", "o-")
    draw(ax[1], dom, "tau_loo", "o-")
    draw(ax[1], dom, "tau_lgo", "s--")
    draw(ax[2], dom, "group_id_lift", "o-")
    draw(ax[3], dom, "inflation", "o-")
    ax[0].plot([], [], "o-", color=COL[dom], lw=1.6, ms=5, label=lb)
    ax[1].plot([], [], "o-", color=COL[dom], lw=1.6, ms=5, label=SHORT[dom] + "  τ_LOO")
    ax[1].plot([], [], "s--", color=COL[dom], lw=1.4, ms=4.5, mfc="white",
               label=SHORT[dom] + "  τ_LGO")
    ax[2].plot([], [], "o-", color=COL[dom], lw=1.6, ms=5, label=lb)
    ax[3].plot([], [], "o-", color=COL[dom], lw=1.6, ms=5, label=lb)

ax[0].axhline(LDI_GATE, color="#555555", ls=":", lw=1.2)
ax[0].text(5.35, LDI_GATE + 1.9, "detection gate  LDI = 1.645",
           fontsize=8, color="#555555", ha="right")
ax[0].set_ylim(0, 15.8)
ax[3].axhline(0.0, color="#555555", ls=":", lw=1.0)

titles = ["A  Calibrated label dependence (LDI)",
          "B  Unit-level τ_LOO vs group-level τ_LGO",
          "C  Group-identity lift (probe accuracy ÷ chance)",
          "D  Sibling-unit inflation  τ_LOO − τ_LGO"]
ylabs = ["LDI", "Kendall τ", "lift over chance", "Δτ"]
LEGLOC = {0: "lower left", 1: "center right", 2: "upper right", 3: "upper right"}
LEGNCOL = {1: 1}
for i in range(4):
    ax[i].set_title(titles[i], fontsize=9.5, loc="left")
    ax[i].set_ylabel(ylabs[i], fontsize=9)
    ax[i].legend(fontsize=7.5, loc=LEGLOC[i], frameon=True, framealpha=1.0,
                 facecolor="white", edgecolor="none")
    ax[i].tick_params(labelsize=8)
    ax[i].spines["top"].set_visible(False)
    ax[i].spines["right"].set_visible(False)
    ax[i].grid(alpha=0.25, lw=0.6)
    ax[i].set_xlabel("adversarial dose λ")
    ax[i].set_xticks(LAMS)

# one statement of what the error bars are, in the figure itself
fig.text(0.5, 0.005,
         "Faint markers: individual training seeds (three per dose). "
         "Line: seed mean. Error bar: SD across seeds, not SEM.",
         ha="center", fontsize=8, color="#333333")

fig.tight_layout(rect=(0, 0.025, 1, 1))
OUT.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT / "fig5_crossdomain.png", dpi=300, bbox_inches="tight")
fig.savefig(OUT / "fig5_crossdomain.pdf", bbox_inches="tight")
print("saved", OUT / "fig5_crossdomain.png/.pdf")
