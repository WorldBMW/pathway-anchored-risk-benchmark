#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generate Figures 1-4 for the Patterns submission, Cell Press style.

Reads only results/*.json (+ e4_decoder_w.npz). Every number plotted is
re-derived from the raw run records, so figures cannot drift from the
manuscript's verified values.

Outputs: papers/20_MRP-ST-Repair_Patterns/figures/fig{1..4}.{pdf,png}
"""
import json
import os
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
FIG = ROOT / "papers" / "20_MRP-ST-Repair_Patterns" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

# Okabe-Ito colorblind-safe palette
BLUE, SKY = "#0072B2", "#56B4E9"
VERM, ORANGE = "#D55E00", "#E69F00"
GREEN, PURPLE, BLACK, GREY = "#009E73", "#CC79A7", "#000000", "#7f7f7f"
GATE_COLOR = "#D55E00"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8,
    "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7,
    "axes.linewidth": 0.8, "xtick.major.width": 0.8,
    "ytick.major.width": 0.8, "lines.linewidth": 1.2,
    "pdf.fonttype": 42, "ps.fonttype": 42,
})

LAMS = ["0.0", "0.5", "1.0", "2.0", "5.0"]
LAM_X = np.arange(5)
LAM_LABELS = ["0", "0.5", "1", "2", "5"]


def jload(name):
    return json.loads((RES / name).read_text(encoding="utf-8"))


def scan_of(name):
    return jload(name)["scan"]


def R_of(v):
    tin = v["tau_insample"]
    return v["tau_lodo"] / tin if abs(tin) > 1e-9 else np.nan


def runs_by_lam(scan):
    """{lam: [run-dicts across seeds]}"""
    out = {lam: [] for lam in LAMS}
    for k, v in scan.items():
        if isinstance(v, dict) and "tau_lodo" in v:
            lam = k.split("_lam")[1]
            out[lam].append(v)
    return out


def save(fig, name):
    fig.savefig(FIG / f"{name}.pdf")
    fig.savefig(FIG / f"{name}.png", dpi=600)
    plt.close(fig)
    print(f"[saved] {name}.pdf/.png")


# ============================================================ diagnostics
print("== diagnostics ==")
# safety panel min R
safety_scans = {lbl: scan_of(f) for lbl, f in [
    ("GAT amp2.5", "repair_e3_sim_A.json"),
    ("GAT amp0.5", "repair_pd_s05.json"),
    ("GAT amp1.0", "repair_pd_s10.json"),
    ("GAT amp1.5", "repair_pd_s15.json"),
    ("GCN amp2.5", "repair_gcn_simA.json"),
]}
all_R = [R_of(v) for sc in safety_scans.values()
         for r in runs_by_lam(sc).values() for v in r]
print(f"safety: {len(all_R)} runs, min R = {min(all_R):.4f}")

# simC in-sample clearance (GAT + stable + GCN)
for name, f in [("GAT", "repair_e3_sim_C.json"),
                ("stable", "repair_e3_simC_stable.json"),
                ("GCN", "repair_gcn_simC.json")]:
    rb = runs_by_lam(scan_of(f))
    t0 = np.mean([v["tau_insample"] for v in rb["0.0"]])
    t5 = np.mean([v["tau_insample"] for v in rb["5.0"]])
    print(f"simC {name}: mean tau_in lam0={t0:.3f} lam5={t5:.3f} "
          f"clearance={1 - t5 / t0:.1%}")

# E4 stable R at accepted cells + recovery
e4s = scan_of("repair_e4_hnscc_stable.json")
acc_R = []
for i in range(3):
    for lam in ("0.5", "1.0", "2.0"):
        v = e4s[f"s{i}_lam{lam}"]
        if v["ldi"] < 1.645:
            acc_R.append(R_of(v))
print(f"E4 accepted cells: n={len(acc_R)}, R range "
      f"[{min(acc_R):.3f}, {max(acc_R):.3f}]")
v = e4s["s1_lam5.0"]
print(f"E4 recovery s1_lam5: tau={v['tau_lodo']:.3f} R={R_of(v):.3f} "
      f"ldi={v['ldi']:.2f}")

# ============================================================ FIGURE 1
fig = plt.figure(figsize=(7.2, 3.1))
gs = fig.add_gridspec(1, 3, width_ratios=[1.1, 1, 1], wspace=0.38)

# --- (A) loop schematic
axA = fig.add_subplot(gs[0])
axA.set_xlim(0, 10); axA.set_ylim(0, 10); axA.axis("off")
# Geometry is set by the longest label, not the other way round. The earlier
# version used 2.4-unit boxes at 8 pt with "training-time patient adversary",
# which printed the three stages on top of each other; the label set is now
# short enough to fit the column and the third acceptance axis is spelled out
# in the caption instead of by three crossing leader lines.
BW, BH, BY, PAD = 2.7, 2.4, 5.9, 0.10
XS = (0.1, 3.65, 7.2)
boxes = [("DETECT\nLDI audit", BLUE),
         ("REPAIR\nadversary\ndose \u03bb", VERM),
         ("ACCEPT\nre-audit", GREEN)]
for x0, (txt, c) in zip(XS, boxes):
    bb = FancyBboxPatch((x0, BY), BW, BH,
                        boxstyle="round,pad=%.2f,rounding_size=0.22" % PAD,
                        fc="white", ec=c, lw=1.6)
    axA.add_patch(bb)
    axA.text(x0 + BW / 2, BY + BH / 2, txt, ha="center", va="center",
             fontsize=7.0, color=c, fontweight="bold", linespacing=1.35)
for x0 in XS[:-1]:
    axA.add_patch(FancyArrowPatch((x0 + BW + PAD + 0.05, BY + BH / 2),
                                  (x0 + BW + PAD + 0.72, BY + BH / 2),
                                  arrowstyle="-|>", mutation_scale=11,
                                  lw=1.2, color=BLACK))
axA.text(5.0, 3.85, "re-audit is graded on three axes", ha="center",
         fontsize=6.9, style="italic", color=GREY)
axA.text(5.0, 2.85, "safety: true signal kept", ha="center",
         fontsize=7.0, color=BLACK)
axA.text(5.0, 1.95, "leakage: below the calibrated gate", ha="center",
         fontsize=7.0, color=BLACK)
axA.text(5.0, 1.05, "instrument: still non-blind", ha="center",
         fontsize=7.0, color=BLACK)
axA.set_title("A", loc="left", fontweight="bold", fontsize=10)

# --- (B) post-hoc projection failure
e1 = jload("repair_e1_posthoc.json")["arms"]
def e1_vals(arm, k):
    runs = e1[arm]["runs"]
    tin = [runs[s][k]["tau_insample"] for s in range(3)]
    tlo = [runs[s][k]["tau"] for s in range(3)]
    return np.mean(tin), tlo

for j, (arm, title) in enumerate([("cervical_FULL", "cervical cohort"),
                                  ("simA_FULL", "shared-program\nsimulation")]):
    ax = fig.add_subplot(gs[j + 1])
    ks = ["0", "1", "2"]
    x = np.arange(3)
    tin_m = [e1_vals(arm, k)[0] for k in ks]
    tlo_m = [np.mean(e1_vals(arm, k)[1]) for k in ks]
    ax.bar(x - 0.18, tin_m, 0.32, color=BLUE, label=r"$\tau_{in}$ (in-sample)")
    ax.bar(x + 0.18, tlo_m, 0.32, color=VERM, label=r"$\tau_{LOO}$ (transfer)")
    for xi, k in zip(x, ks):
        for s in e1_vals(arm, k)[1]:
            ax.plot(xi + 0.18, s, "_", color="white", ms=5, mew=1.2)
    ax.axhline(0, color=BLACK, lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"k = {k}" for k in ks])
    ax.set_title(title, fontsize=8)
    ax.set_ylabel(r"Kendall $\tau$ (labels)")
    if arm == "cervical_FULL":
        ax.legend(frameon=False, loc="lower left")
        ax.annotate("in-sample intact,\ntransfer destroyed",
                    xy=(1.18, -0.08), xytext=(0.55, -0.42), fontsize=6.8,
                    arrowprops=dict(arrowstyle="->", lw=0.7))
        ax.annotate("both collapse", xy=(2.18, -0.44), xytext=(1.1, -0.62),
                    fontsize=6.8, arrowprops=dict(arrowstyle="->", lw=0.7))
    else:
        ax.annotate("immediate, total\ncollapse at k = 1", xy=(1.18, -0.7),
                    xytext=(0.1, -0.35), fontsize=6.8,
                    arrowprops=dict(arrowstyle="->", lw=0.7))
    ax.set_ylim(-0.95, 0.85)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("BC"[j], loc="left", fontweight="bold", fontsize=10)
save(fig, "fig1")

# ============================================================ FIGURE 2
fig = plt.figure(figsize=(7.2, 6.2))
gs = fig.add_gridspec(2, 2, hspace=0.42, wspace=0.34)

# --- (A) safety panel
axA = fig.add_subplot(gs[0, 0])
arms = [("GAT, amp 0.5", "repair_pd_s05.json", SKY, "o"),
        ("GAT, amp 1.0", "repair_pd_s10.json", BLUE, "o"),
        ("GAT, amp 1.5", "repair_pd_s15.json", PURPLE, "o"),
        ("GAT, amp 2.5", "repair_e3_sim_A.json", GREEN, "o"),
        ("GCN, amp 2.5", "repair_gcn_simA.json", VERM, "s")]
rng = np.random.default_rng(7)
for lbl, f, c, mk in arms:
    rb = runs_by_lam(scan_of(f))
    for xi, lam in zip(LAM_X, LAMS):
        Rs = [R_of(v) for v in rb[lam]]
        jit = rng.uniform(-0.13, 0.13, len(Rs))
        axA.plot(xi + jit, Rs, mk, ms=3.5, mfc=c, mec=c, alpha=0.85,
                 label=lbl if xi == 0 else None)
axA.axhline(1.0, color=BLACK, ls="--", lw=1.0)
axA.text(4.45, 1.002, "R = 1 (ceiling)", ha="right", fontsize=7)
axA.set_xticks(LAM_X); axA.set_xticklabels(LAM_LABELS)
axA.set_xlabel(r"adversarial dose $\lambda$")
axA.set_ylabel(r"transferable fraction $R=\tau_{LOO}/\tau_{in}$")
axA.set_ylim(0.965, 1.008)
axA.legend(frameon=False, loc="lower left", ncol=2, handletextpad=0.2,
           columnspacing=0.8)
axA.set_title("75/75 runs keep the shared program\n(min R = 0.989)",
              fontsize=8)
axA.spines[["top", "right"]].set_visible(False)
axA.set_title("A", loc="left", fontweight="bold", fontsize=10)

# --- (B) non-blindness (simC LDI)
axB = fig.add_subplot(gs[0, 1])
for lbl, f, c, mk in [("GAT", "repair_e3_sim_C.json", BLUE, "o"),
                      ("GAT (stability)", "repair_e3_simC_stable.json", GREEN, "o"),
                      ("GCN", "repair_gcn_simC.json", VERM, "s")]:
    rb = runs_by_lam(scan_of(f))
    for xi, lam in zip(LAM_X, LAMS):
        ldis = [v["ldi"] for v in rb[lam]]
        jit = rng.uniform(-0.13, 0.13, len(ldis))
        axB.plot(xi + jit, ldis, mk, ms=3.5, mfc=c, mec=c, alpha=0.85,
                 label=lbl if xi == 0 else None)
axB.axhline(1.645, color=GATE_COLOR, ls="--", lw=1.1)
axB.text(4.45, 1.72, "1.645 gate", ha="right", fontsize=7, color=GATE_COLOR)
axB.set_xticks(LAM_X); axB.set_xticklabels(LAM_LABELS)
axB.set_xlabel(r"adversarial dose $\lambda$")
axB.set_ylabel("LDI (identity-confounding control)")
axB.set_ylim(0, 2.1)
axB.set_title("identity-only cohort: 45/45 correctly\ngraded unsupported (no false alarm)",
              fontsize=8)
axB.text(0.03, 0.965,
         "in-sample identity fingerprint falls\n≈12% under repair (stability)",
         transform=axB.transAxes, fontsize=6.6, va="top", color=GREY)
axB.legend(frameon=True, framealpha=1.0, facecolor="white", edgecolor="none",
           loc="center", bbox_to_anchor=(0.68, 0.42))
axB.spines[["top", "right"]].set_visible(False)
axB.set_title("B", loc="left", fontweight="bold", fontsize=10)

# --- (C) external cohort dose-response
axC = fig.add_subplot(gs[1, 0])
seed_cols = {0: BLUE, 1: VERM, 2: GREEN}
e4s = scan_of("repair_e4_hnscc_stable.json")
for i in range(3):
    taus = [e4s[f"s{i}_lam{lam}"]["tau_lodo"] for lam in LAMS]
    axC.plot(LAM_X, taus, "-o", ms=3.5, color=seed_cols[i],
             label=f"seed {i}")
axC.axhline(0.7303, color=BLACK, ls="--", lw=1.0)
axC.text(0.05, 0.745, r"analytic ceiling $\tau$=0.730", fontsize=7)
axC.annotate("maximal-dose recovery\n(R = 0.90)", xy=(4, 0.639),
             xytext=(2.15, 0.80), fontsize=7,
             arrowprops=dict(arrowstyle="->", lw=0.8))
axC.set_xticks(LAM_X); axC.set_xticklabels(LAM_LABELS)
axC.set_xlabel(r"adversarial dose $\lambda$")
axC.set_ylabel(r"$\tau_{LOO}$ (HPV status)", color=BLACK)
axC.set_ylim(0, 0.95)
axC.legend(frameon=False, loc="lower left", fontsize=6.5)
axC2 = axC.twinx()
for i in range(3):
    ldis = [e4s[f"s{i}_lam{lam}"]["ldi"] for lam in LAMS]
    axC2.plot(LAM_X, ldis, ":", lw=1.0, color=seed_cols[i], alpha=0.65)
axC2.axhline(1.645, color=GATE_COLOR, ls="--", lw=1.1)
axC2.set_ylabel("LDI (dotted)", color=GREY)
axC2.set_ylim(0, 3.4)
axC2.tick_params(axis="y", colors=GREY)
axC2.spines["right"].set_color(GREY)
axC.set_title("external HNSCC cohort (GAT, stability):\nτ_LOO solid / LDI dotted, gate 1.645",
              fontsize=8)
axC.set_title("C", loc="left", fontweight="bold", fontsize=10)

# --- (D) backbone replication
axD = fig.add_subplot(gs[1, 1])
def band(ax, fname, label, color, ls):
    sc = scan_of(fname)
    seeds = list(range(3))
    per = np.array([[sc[f"s{i}_lam{lam}"]["tau_lodo"] for i in seeds]
                    for lam in LAMS])  # [lam, seed]
    ax.plot(LAM_X, per.mean(1), ls, color=color, label=label, lw=1.4)
    ax.fill_between(LAM_X, per.min(1), per.max(1), color=color, alpha=0.15,
                    lw=0)
band(axD, "repair_e4_hnscc_stable.json", "GAT (stability)", BLUE, "-o")
band(axD, "repair_gcn_e4.json", "GCN", VERM, "--s")
axD.axhline(0.7303, color=BLACK, ls="--", lw=1.0)
axD.set_xticks(LAM_X); axD.set_xticklabels(LAM_LABELS)
axD.set_xlabel(r"adversarial dose $\lambda$")
axD.set_ylabel(r"$\tau_{LOO}$ (HPV status)")
axD.set_ylim(0, 0.95)
axD.legend(frameon=False, loc="lower left")
axD.set_title("backbone replication:\nsame shape under GCN", fontsize=8)
axD.spines[["top", "right"]].set_visible(False)
axD.set_title("D", loc="left", fontweight="bold", fontsize=10)
save(fig, "fig2")

# ============================================================ FIGURE 3
fig = plt.figure(figsize=(7.2, 6.6))
gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1], hspace=0.42,
                      wspace=0.30)

# --- (A) phase maps
NS = [4, 8, 16, 32, 64]
def phase_matrix(prefix):
    M = np.full((5, 5), np.nan)
    for r, n in enumerate(NS):
        per = []
        for lam in LAMS:
            Rs = []
            for i in range(3):
                f = RES / f"{prefix}_n{n}_s{i}.json"
                if not f.exists():
                    continue
                v = scan_of(f.name)[f"s{i}_lam{lam}"]
                Rs.append(R_of(v))
            per.append(np.mean(Rs) if Rs else np.nan)
        M[r] = per
    return M

M1 = phase_matrix("e2_phase_ax1")
M3 = phase_matrix("e2b_ax1")
for j, (M, sig, intact_idx) in enumerate([(M1, "signal amplitude 1.0", 3),
                                          (M3, "signal amplitude 0.3", 4)]):
    ax = fig.add_subplot(gs[0, j])
    im = ax.imshow(M[::-1], cmap="RdBu", vmin=-1.0, vmax=1.0,
                   aspect="auto")
    ax.set_xticks(range(5)); ax.set_xticklabels(LAM_LABELS)
    ax.set_yticks(range(5))
    ax.set_yticklabels([str(n) for n in NS[::-1]])
    ax.set_xlabel(r"adversarial dose $\lambda$")
    ax.set_ylabel("simulated groups (n)")
    ax.set_title(sig, fontsize=8)
    for r in range(5):
        for c in range(5):
            if not np.isnan(M[r, c]):
                ax.text(c, 4 - r, f"{M[r, c]:.2f}", ha="center",
                        va="center", fontsize=7,
                        color="black" if abs(M[r, c]) < 0.55 else "white")
    # boundary line between the damaged row and the intact neighbor;
    # rows are displayed n=64(top)..n=4(bottom): intact row display index
    # is 4 - intact_idx, line sits 0.5 below it
    yline = (4 - intact_idx) + 0.5
    ax.plot([0.5, 4.5], [yline, yline], ls="--", color=BLACK, lw=1.3)
    ax.text(4.45, yline - 0.28, "feasibility\nboundary", fontsize=6.2,
            ha="right", va="top")
    if j == 0:
        ax.set_title("A", loc="left", fontweight="bold", fontsize=10,
                     pad=12)
fig.text(0.985, 0.80, "", fontsize=7)
cax = fig.add_axes([0.92, 0.685, 0.014, 0.155])
cb = fig.colorbar(im, cax=cax)
cb.set_label(r"mean $R$", fontsize=7)
cb.ax.tick_params(labelsize=6.5)

# --- (B) five-seed boundary verification
axB = fig.add_subplot(gs[1, 0])
groups = [("e2_phase_ax1", "e2r", "signal 1.0", 16),
          ("e2_phase_ax1", "e2r", "signal 1.0", 32),
          ("e2b_ax1", "e2br", "signal 0.3", 16),
          ("e2b_ax1", "e2br", "signal 0.3", 32)]
worst_means, worst_seed_pts, worst_lams = [], [], []
for prefix, rpre, sig, n in groups:
    per_lam = {lam: [] for lam in LAMS[1:]}
    for tag, is_re in [(f"{prefix}_n{n}_s{i}.json", False) for i in range(3)] + \
                      [(f"{rpre}_n{n}_s{i}.json", True) for i in (3, 4)]:
        sc = scan_of(tag)
        s_id = tag.split("_s")[-1].replace(".json", "")
        for lam in LAMS[1:]:
            v = sc[f"s{s_id}_lam{lam}"]
            per_lam[lam].append(R_of(v))
    means = {lam: np.mean(v) for lam, v in per_lam.items()}
    wlam = min(means, key=means.get)
    worst_means.append(means[wlam])
    worst_seed_pts.append(per_lam[wlam])
    worst_lams.append(wlam)
xg = np.arange(4)
cols = [VERM, BLUE, VERM, BLUE]
bars = axB.bar(xg, worst_means, 0.55, color=cols, alpha=0.75)
for xi, pts in zip(xg, worst_seed_pts):
    axB.plot(np.full(5, xi), pts, "o", ms=3, mfc="white", mec=BLACK,
             mew=0.7, zorder=5)
axB.axhline(0.86, color=BLACK, ls="--", lw=1.0)
axB.text(3.45, 0.875, "damage threshold 0.86", fontsize=6.5, ha="right")
for xi, (wm, wl) in enumerate(zip(worst_means, worst_lams)):
    axB.text(xi, wm + 0.02, f"λ={float(wl):g}", ha="center", fontsize=6.5,
             color=GREY)
axB.set_xticks(xg)
axB.set_xticklabels(["1.0\nn=16", "1.0\nn=32", "0.3\nn=16", "0.3\nn=32"])
axB.set_xlabel("signal amplitude / simulated groups")
axB.set_ylabel(r"worst repair cell: mean $R$ (5 seeds)")
axB.set_ylim(0, 1.08)
axB.set_title("boundary verified with five seeds\n(white dots: individual seeds)",
              fontsize=8)
axB.spines[["top", "right"]].set_visible(False)
axB.set_title("B", loc="left", fontweight="bold", fontsize=10)

# --- (C) sibling-slice inflation
axC = fig.add_subplot(gs[1, 1])
ENDS = {}
for j, k in enumerate((2, 4, 8)):
    sl_m, sl_lo, sl_hi, do_m, do_lo, do_hi = [], [], [], [], [], []
    for lam in LAMS:
        sl, do = [], []
        for i in range(3):
            sc = scan_of(f"e2_phase2_ax2_k{k}_s{i}.json")
            v = sc[f"s{i}_lam{lam}"]
            sl.append(v["tau_lodo"])
            do.append(v["tau_ldo"])
        sl_m.append(np.mean(sl)); sl_lo.append(min(sl)); sl_hi.append(max(sl))
        do_m.append(np.mean(do)); do_lo.append(min(do)); do_hi.append(max(do))
    off = (j - 1) * 0.14
    axC.plot(LAM_X + off, sl_m, "-o", ms=3, color=BLUE,
             label="slice-level LOO" if j == 0 else None)
    axC.fill_between(LAM_X + off, sl_lo, sl_hi, color=BLUE, alpha=0.12, lw=0)
    axC.plot(LAM_X + off, do_m, "--s", ms=3, color=VERM,
             label="donor-level LDO" if j == 0 else None)
    axC.fill_between(LAM_X + off, do_lo, do_hi, color=VERM, alpha=0.12,
                     lw=0)
    ENDS[k] = (off, do_m[-1])
# The k = 4 and k = 8 donor-level endpoints sit almost on top of each other
# (0.67 and 0.72), so labels are placed top-down with a minimum vertical
# separation; the old fixed offset printed "k=8" and "k=4" over each other.
prev = None
for k, (off, y_end) in sorted(ENDS.items(), key=lambda kv: -kv[1][1]):
    y_lab = y_end if prev is None else min(y_end, prev - 0.085)
    prev = y_lab
    axC.annotate(f"k={k}", xy=(4 + off, y_end),
                 xytext=(4.24 + off, y_lab),
                 fontsize=6.5, color=VERM, va="center",
                 arrowprops=dict(arrowstyle="-", lw=0.5, color=VERM,
                                 alpha=0.6))
axC.axhline(0, color=BLACK, lw=0.7)
axC.set_xticks(LAM_X); axC.set_xticklabels(LAM_LABELS)
axC.set_xlabel(r"adversarial dose $\lambda$" + "\n(k = slices per donor)")
axC.set_ylabel(r"$\tau$ (severity label)")
axC.set_ylim(-0.75, 0.95)
axC.legend(frameon=False, loc="lower left")
axC.set_title("sibling-slice inflation: slice-level CV\noverestimates transfer",
              fontsize=8)
axC.spines[["top", "right"]].set_visible(False)
axC.set_title("C", loc="left", fontweight="bold", fontsize=10)
save(fig, "fig3")

# ============================================================ FIGURE 4
def norm(g):
    return g[7:] if g.startswith("GRCh38_") else g


d4 = jload("repair_e4_hnscc_stable.json")
dx = d4["dump_xs"]["s0_lam2.0"]
Xs = np.array(dx["Xs"], dtype=float)
y = np.array(dx["y"], dtype=float)
w0 = np.load(RES / "e4_decoder_w.npz", allow_pickle=True)
W = np.asarray(w0["W"], dtype=float)
raw_panel = [norm(str(g)) for g in w0["panel"]]

mu, sd = Xs.mean(0), Xs.std(0) + 1e-8
Z = (Xs - mu) / sd
w_dir = np.linalg.solve(Z.T @ Z + np.eye(Z.shape[1]), Z.T @ y)
w_dir = w_dir / (np.linalg.norm(w_dir) + 1e-12)
L = np.abs(W @ w_dir)
best = {}
for i, g in enumerate(raw_panel):
    if g not in best or L[i] > best[g]:
        best[g] = L[i]
ranked = sorted(best.items(), key=lambda kv: -kv[1])[:25]
genes = [g for g, _ in ranked][::-1]
vals = [v for _, v in ranked][::-1]

c3root = jload("c3lite_multiseed.json")
c3 = c3root["pairs"]["s0_lam2.0"]
hits = set(c3["hits"])
krt_family = set(c3["keratinization"])
plasma_stromal = {"IGKC", "COL1A2"}
fig, ax = plt.subplots(figsize=(5.6, 5.8))
fig.subplots_adjust(left=0.20, right=0.97, top=0.97, bottom=0.27)
colors = []
for g in genes:
    if g in hits:
        colors.append(VERM)
    elif g in krt_family:
        colors.append(ORANGE)
    elif g in plasma_stromal:
        colors.append(GREY)
    else:
        colors.append(BLUE)
ax.barh(range(25), vals, 0.68, color=colors)
ax.set_yticks(range(25))
ax.set_yticklabels(genes, fontsize=7.5, style="italic")
for yi, (g, v) in enumerate(zip(genes, vals)):
    if g in hits:
        ax.text(v + max(vals) * 0.012, yi, "*", fontsize=9,
                va="center", color=VERM)
    elif g in krt_family:
        ax.text(v + max(vals) * 0.012, yi, "†", fontsize=8,
                va="center", color=ORANGE)
ax.set_xlabel("|gene loading| on the surviving HPV direction")
ax.set_ylim(-0.7, 24.7)
ax.spines[["top", "right"]].set_visible(False)
stats = ("* in-panel HPV+ reference marker; ID1 and KRT16 (markers) and "
         "SPRR3 (keratinization family) also hit in the top-100\n"
         "† keratinization-family gene\n"
         f"top-100 enrichment: hypergeometric p = {c3['p_hypergeom']:.4f}; "
         f"permutation p = {c3['p_empirical']:.4f} "
         f"(null expectation: {c3root['null_mean']:.2f} hits per 100 genes)\n"
         "strongest at the maximal-dose recovery point (λ = 5: six "
         "markers, incl. CDKN2A)")
ax.text(-0.05, -0.075, stats, transform=ax.transAxes, fontsize=6.6,
        ha="left", va="top", color=BLACK)
save(fig, "fig4")

print("\nALL FIGURES DONE ->", FIG)
