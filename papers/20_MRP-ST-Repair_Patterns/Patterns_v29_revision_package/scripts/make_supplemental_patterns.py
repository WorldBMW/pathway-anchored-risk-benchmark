#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build Supplemental_Information_Patterns.docx: real data tables S1-S9
generated directly from results/*.json (no hand-typed numbers)."""
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import numpy as np
from docx import Document
from docx.shared import Pt, Inches, RGBColor

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
BASE = (ROOT / "papers" / "20_MRP-ST-Repair_Patterns")
OUT = BASE / "Supplemental_Information_Patterns.docx"

LAMS = ["0.0", "0.5", "1.0", "2.0", "5.0"]


def f3(x):
    """Format to 3 decimals with round-half-up, matching the manuscript text
    (Python's default format uses round-half-even and would render the exact
    0.0625 as 0.062 where the text reports 0.063)."""
    return str(Decimal(repr(float(x))).quantize(Decimal("0.001"),
                                                rounding=ROUND_HALF_UP))


def jload(name):
    return json.loads((RES / name).read_text(encoding="utf-8"))


def scan(name):
    return jload(name)["scan"]


def R(v):
    t = v["tau_insample"]
    return v["tau_lodo"] / t if abs(t) > 1e-9 else float("nan")


doc = Document()
st = doc.styles["Normal"]
st.font.name = "Arial"
st.font.size = Pt(9)
for sec in doc.sections:
    sec.left_margin = sec.right_margin = Inches(0.8)
    sec.orientation = 1  # keep portrait; tables sized to fit


def h(text, level=1):
    p = doc.add_heading("", level=level)
    r = p.add_run(text)
    r.font.color.rgb = RGBColor(0, 0, 0)


def caption(text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = True


def table(rows, widths=None, fontsize=8):
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = t.cell(i, j)
            cell.text = ""
            p = cell.paragraphs[0]
            r = p.add_row = p.add_run(str(val))
            r.font.size = Pt(fontsize)
            if i == 0:
                r.bold = True
    doc.add_paragraph()
    return t


# ------------------------------------------------ S1 weak-signal arm
h("Table S1. Weak-signal arm (simulation B): baseline detectability and the λ = 0.5 effect (three seeds)")
sc = scan("repair_e3_sim_B.json")
rows = [["seed", "λ", "τ_LOO", "τ_in", "LDI", "gate (LDI < 1.645)"]]
for i in range(3):
    for lam in LAMS:
        v = sc[f"s{i}_lam{lam}"]
        rows.append([f"s{i}", lam, f"{v['tau_lodo']:+.3f}",
                     f"{v['tau_insample']:+.3f}", f"{v['ldi']:.2f}",
                     "pass" if v["ldi"] < 1.645 else "fail"])
caption("Only one of three seeds is detectable at baseline (λ = 0); moderate repair (λ = 0.5) raises the association in all three seeds while none crosses the gate.")
table(rows)

# ------------------------------------------------ S2 identity-confounding
h("Table S2. Identity-confounding arm (simulation C) across variants: non-blindness and fingerprint clearance (45 runs)")
rows = [["variant", "runs", "max LDI", "gate (1.645)",
         "mean τ_in λ=0", "mean τ_in λ=5", "fingerprint clearance"]]
for name, f in [("GAT", "repair_e3_sim_C.json"),
                ("GAT (stability)", "repair_e3_simC_stable.json"),
                ("GCN", "repair_gcn_simC.json")]:
    s = scan(f)
    ldis = [v["ldi"] for k, v in s.items() if isinstance(v, dict)]
    t0 = np.mean([s[f"s{i}_lam0.0"]["tau_insample"] for i in range(3)])
    t5 = np.mean([s[f"s{i}_lam5.0"]["tau_insample"] for i in range(3)])
    rows.append([name, 15, f"{max(ldis):.3f}",
                 "all below" if max(ldis) < 1.645 else "ABOVE",
                 f"{t0:.3f}", f"{t5:.3f}", f"{1 - t5 / t0:.1%}"])
caption("The repaired audit stays non-blind in all 45 runs (LDI never crosses the 1.645 gate); the in-sample identity fingerprint is partially cleared (≈12% for the stability variant).")
table(rows)

# ------------------------------------------------ S3 cervical
h("Table S3. Cervical cohort dose–response (stability variant): bistability across seeds")
sc = scan("repair_e3_cervix_stable.json")
rows = [["seed", "λ", "τ_LOO", "τ_in", "LDI", "gate", "retention vs λ=0"]]
for i in range(3):
    base = sc[f"s{i}_lam0.0"]["tau_lodo"]
    for lam in LAMS:
        v = sc[f"s{i}_lam{lam}"]
        ret = v["tau_lodo"] / base if base else float("nan")
        rows.append([f"s{i}", lam, f"{v['tau_lodo']:+.3f}",
                     f"{v['tau_insample']:+.3f}", f"{v['ldi']:.2f}",
                     "pass" if v["ldi"] < 1.645 else "fail",
                     f"{ret:.0%}"])
caption("Low doses (λ ≤ 1) leave LDI above the gate (2.00–2.52); at high doses (λ ∈ {2, 5}) every seed produces below-gate runs retaining 27–50% of the transferable association, and the response is non-monotone — no stable operating point exists.")
table(rows)

# ------------------------------------------------ S4 external + recheck
h("Table S4. External HNSCC cohort: non-hardened replication and permutation-depth recheck")
sc = scan("repair_e4_hnscc.json")
rows = [["seed", "λ", "τ_LOO (non-hardened)", "τ_in", "R", "LDI",
         "gate"]]
for i in range(3):
    for lam in LAMS:
        v = sc[f"s{i}_lam{lam}"]
        rows.append([f"s{i}", lam, f"{v['tau_lodo']:+.3f}",
                     f"{v['tau_insample']:+.3f}", f"{R(v):.3f}",
                     f"{v['ldi']:.2f}", "pass" if v["ldi"] < 1.645 else "fail"])
caption("The independent non-hardened replication reproduces the dose–response shape; the λ = 5 seed-1 run reaches the analytic ceiling (τ_LOO = τ_in = 0.7303, R = 1.00), the perfect-donor-transferable generalization point.")
table(rows)
rc = jload("perm10k_recheck.json")
rows = [["run", "LDI (B=2,000)", "LDI (B=10,000)", "σ̂ change (vs. B=2,000)",
         "gate flip?", "τ_LOO bit-identical"]]
nflip = 0
maxchg = 0.0
for k, v in rc.items():
    dsig = abs(v["sigma_10k"] - v["sigma_2k"]) / v["sigma_2k"]
    maxchg = max(maxchg, dsig)
    flip = (v["ldi_2k"] < 1.645) != (v["ldi_10k"] < 1.645)
    nflip += flip
    ident = v["tau_lodo_recheck"] == v["tau_lodo_stored"]
    rows.append([k, f"{v['ldi_2k']:.3f}", f"{v['ldi_10k']:.3f}",
                 f"{dsig:.1%}", "YES" if flip else "no",
                 "yes" if ident else "NO"])
caption(f"Permutation-depth recheck of all 15 external-cohort (stability variant) runs: {nflip}/15 gate flips; maximum σ̂ change {maxchg:.1%} relative to the B = 2,000 estimate; the LOO statistic recomputes bit-identically.")
table(rows)

# ------------------------------------------------ S5 GCN backbone
h("Table S5. GCN backbone replication: safety, non-blindness, external-cohort dose–response")
rows = [["panel", "metric", "λ = 0", "λ = 0.5", "λ = 1", "λ = 2", "λ = 5"]]
s = scan("repair_gcn_simA.json")
rows.append(["safety (shared program, amp 2.5)",
             "R (3-seed mean)",
             *[f"{np.mean([R(s[f's{i}_lam{lam}']) for i in range(3)]):.3f}"
               for lam in LAMS]])
s = scan("repair_gcn_simC.json")
rows.append(["non-blindness (identity control)", "max LDI",
             *[f"{max(s[f's{i}_lam{lam}']['ldi'] for i in range(3)):.3f}"
               for lam in LAMS]])
s = scan("repair_gcn_e4.json")
rows.append(["external cohort", "τ_LOO (3-seed mean)",
             *[f"{np.mean([s[f's{i}_lam{lam}']['tau_lodo'] for i in range(3)]):+.3f}"
               for lam in LAMS]])
rows.append(["external cohort", "R (3-seed mean)",
             *[f"{np.mean([R(s[f's{i}_lam{lam}']) for i in range(3)]):.3f}"
               for lam in LAMS]])
caption("The GCN backbone reproduces the GAT results: 15/15 safety runs at the analytic ceiling, 15/15 non-blindness runs under the gate, and the same external-cohort dose–response shape.")
table(rows)

# ------------------------------------------------ S6 boundary 5 seeds
h("Table S6. Boundary robustness: five seeds at n ∈ {16, 32} (both signals)")
rows = [["signal", "n", "λ = 0.5", "λ = 1", "λ = 2", "λ = 5",
         "worst cell", "verdict"]]
groups = [("1.0", 16, "e2_phase_ax1", "e2r"),
          ("1.0", 32, "e2_phase_ax1", "e2r"),
          ("0.3", 16, "e2b_ax1", "e2br"),
          ("0.3", 32, "e2b_ax1", "e2br")]
for sig, n, pre, rpre in groups:
    per = {lam: [] for lam in LAMS[1:]}
    for i in (0, 1, 2, 3, 4):
        fname = (f"{pre}_n{n}_s{i}.json" if i < 3
                 else f"{rpre}_n{n}_s{i}.json")
        s = scan(fname)
        for lam in LAMS[1:]:
            per[lam].append(R(s[f"s{i}_lam{lam}"]))
    means = {lam: np.mean(v) for lam, v in per.items()}
    worst = min(means, key=means.get)
    verdict = "damaged" if means[worst] < 0.86 else "intact"
    rows.append([sig, n,
                 *[f"{means[lam]:.2f}" for lam in LAMS[1:]],
                 f"{means[worst]:.2f} (λ={float(worst):g})", verdict])
caption("Boundary placement unchanged with five seeds: signal 1.0 — n = 16 damaged vs n = 32 intact, boundary in (16, 32]; signal 0.3 — both n = 16 and n = 32 damaged, boundary in (32, 64].")
table(rows)

# ------------------------------------------------ S7 C3-lite pairs
h("Table S7. C3-lite multi-seed strict pairs: enrichment of the surviving HPV direction")
c3 = jload("c3lite_multiseed.json")
rows = [["pair", "marker hits in top-100", "hits", "p (hypergeometric)",
         "p (permutation)", "keratinization-family genes in top-100"]]
for tag, v in c3["pairs"].items():
    rows.append([tag, v["n_hits"], ", ".join(v["hits"]),
                 f"{v['p_hypergeom']:.4f}", f"{v['p_empirical']:.4f}",
                 ", ".join(v["keratinization"])])
caption(f"Reference panel: {c3['panel_unique']} unique genes, {c3['markers_in_panel']}/15 HPV-positive markers present; permutation-null expectation {c3['null_mean']:.2f} marker hits per 100 genes. The enrichment holds at every seed at λ = 2 and is strongest at the maximal-dose recovery point (λ = 5: six markers, incl. CDKN2A).")
table(rows)

# ------------------------------------------------ S8 phase-grid source data
h("Table S8. Per-seed phase-grid values for all Figure 3 panels (source data)")
rows = [["panel", "signal", "n or k", "λ", "s0", "s1", "s2", "s3", "s4",
         "mean"]]
NS = [4, 8, 16, 32, 64]
for sig, pre, rpre in [("1.0", "e2_phase_ax1", "e2r"),
                       ("0.3", "e2b_ax1", "e2br")]:
    for n in NS:
        for lam in LAMS:
            vals = []
            for i in (0, 1, 2):
                vals.append(R(scan(f"{pre}_n{n}_s{i}.json")[f"s{i}_lam{lam}"]))
            row = [f"R", sig, n, lam] + [f"{v:+.3f}" for v in vals]
            if n in (16, 32):
                for i in (3, 4):
                    vals.append(R(scan(f"{rpre}_n{n}_s{i}.json")[f"s{i}_lam{lam}"]))
                row += [f"{vals[3]:+.3f}", f"{vals[4]:+.3f}"]
            else:
                row += ["–", "–"]
            row.append(f"{np.mean(vals):+.3f}")
            rows.append(row)
for k in (2, 4, 8):
    for lam in LAMS:
        sl, do = [], []
        for i in range(3):
            v = scan(f"e2_phase2_ax2_k{k}_s{i}.json")[f"s{i}_lam{lam}"]
            sl.append(v["tau_lodo"])
            do.append(v["tau_ldo"])
        rows.append(["slice-LOO τ", "–", f"k={k}", lam,
                     *[f"{v:+.3f}" for v in sl], "–", "–",
                     f"{np.mean(sl):+.3f}"])
        rows.append(["donor-LDO τ", "–", f"k={k}", lam,
                     *[f"{v:+.3f}" for v in do], "–", "–",
                     f"{np.mean(do):+.3f}"])
caption("R = τ_LOO/τ_in per run; s3/s4 are the reseed runs (only n ∈ {16, 32} were reseeded). Slice-level LOO stays at its class-size ceiling for every k, while donor-level LDO collapses after repair — the sibling-slice inflation effect.")
table(rows, fontsize=7)

# ------------------------------------------------ S9 downstream clinical endpoint
h("Table S9. Downstream clinical endpoint under repair: leave-one-donor-out HPV AUROC (external cohort)")
cj = jload("repair_c_lodo_auroc.json")["E4_HNSCC"]
st = scan("repair_e4_hnscc_stable.json")
rows = [["λ", "s0", "s1", "s2", "mean", "SD", "same-run LDI (s0/s1/s2)"]]
for lam in LAMS:
    vals = [r["lodo_auroc"] for r in cj[lam]]
    ldi = [f"{st[f's{i}_lam{lam}']['ldi']:.2f}" for i in range(3)]
    rows.append([lam, *[f3(v) for v in vals],
                 f3(np.mean(vals)), f3(np.std(vals, ddof=1)),
                 "/".join(ldi)])
caption("Leave-one-donor-out ridge classification of HPV status from slice-mean embeddings (16 donors, one slide each; 16 folds). The baseline (λ = 0) is already well above chance (0.906 ± 0.063, all three seeds above the 1.645 LDI gate); repair does not improve the endpoint — every λ > 0 lowers the mean (0.766–0.813), a fidelity cost consistent with the accepted-cell R = 0.38–0.59 and with the absence of a sibling-slice leakage channel in this one-slide-per-donor cohort.")
table(rows)

doc.save(OUT)
print(f"[saved] {OUT.name}")
print(f"tables: S1-S9, rows S9: {len(rows)}")
