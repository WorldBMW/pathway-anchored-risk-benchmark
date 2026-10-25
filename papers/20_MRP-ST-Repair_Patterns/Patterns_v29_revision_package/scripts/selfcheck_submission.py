#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Final submission-package self-check for the Patterns submission.

Checks: (1) package inventory; (2) figure numbers vs manuscript anchors;
(3) supplemental docx spot-checks against raw JSONs; (4) reference format;
(5) remaining placeholders the user must fill; (6) word counts.
"""
import json
import re
from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "papers" / "20_MRP-ST-Repair_Patterns"
RES = ROOT / "results"

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append((name, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


print("== 1. package inventory ==")
required = {
    "Manuscript_Patterns.docx": "main text (Word)",
    "TitlePage_Patterns.docx": "title page (Word)",
    "CoverLetter_Patterns.docx": "cover letter (Word)",
    "Supplemental_Information_Patterns.docx": "supplemental tables S1-S9",
    "figures/fig1.pdf": "Figure 1 (vector)",
    "figures/fig2.pdf": "Figure 2 (vector)",
    "figures/fig3.pdf": "Figure 3 (vector)",
    "figures/fig4.pdf": "Figure 4 (vector)",
    "figures/fig1.png": "Figure 1 (600 dpi)",
    "figures/fig2.png": "Figure 2 (600 dpi)",
    "figures/fig3.png": "Figure 3 (600 dpi)",
    "figures/fig4.png": "Figure 4 (600 dpi)",
    "MRP-ST-Repair_manuscript_Patterns_v1.md": "source of truth (md)",
}
for f, what in required.items():
    check(f"exists: {f}", (BASE / f).exists(), what)

print("== 2. manuscript anchors (md source) ==")
md = (BASE / "MRP-ST-Repair_manuscript_Patterns_v1.md").read_text(encoding="utf-8")
anchors = [
    ("75 of 75", "75/75 safety runs"),
    ("45 of 45", "45/45 non-blindness runs"),
    ("seven of nine", "7/9 accepted cells"),
    ("R = 0.90", "recovery point"),
    ("R ≥ 0.989", "safety min R"),
    ("0.38–0.59", "accepted R range"),
    ("0.7303", "analytic ceiling"),
    ("(16, 32]", "boundary sig 1.0"),
    ("(32, 64]", "boundary sig 0.3"),
    ("2.35", "Prop 1 threshold"),
    ("≤ 4.4%", "sigma-hat recheck"),
    ("2.2", "HNSCC ratio"),
    ("27–50%", "cervical retention range"),
    ("p = 0.0014", "C3 hypergeometric"),
    ("≈ 12%", "fingerprint clearance (Fig 2B)"),
    ("RTX 4080 SUPER", "hardware"),
    ("0.86", "damage threshold"),
    ("five seeds", "boundary verification"),
    ("0.56 at n = 16 (damaged) vs. 0.90 at n = 32", "Table S6 verdict"),
    ("causal-type labels", "abstract scope qualifier"),
    ("0.906", "clinical endpoint baseline AUROC"),
    ("0.766–0.813", "clinical endpoint under repair"),
    ("fidelity cost", "clinical-endpoint caliber"),
    ("Table S9", "downstream clinical endpoint table"),
]
for a, what in anchors:
    check(f"anchor: {a!r}", a in md, what)
# stale anchors that must be gone
stale = ["within 1%", "two of three seeds pressed", "≈ 2.1",
         "RTX 4080 (32 GB)", "ITGB4, DSG3", "EGFR-driven",
         "acceptance region shaded", "R ≥ 0.38"]
for s in stale:
    check(f"stale removed: {s!r}", s not in md)

print("== 3. raw-JSON cross-check of key claims ==")
e4s = json.loads((RES / "repair_e4_hnscc_stable.json").read_text())["scan"]
v = e4s["s1_lam5.0"]
check("recovery tau=0.639", abs(v["tau_lodo"] - 0.639) < 5e-4)
check("recovery R=0.903", abs(v["tau_lodo"] / v["tau_insample"] - 0.903) < 5e-4)
e4n = json.loads((RES / "repair_e4_hnscc.json").read_text())["scan"]
vn = e4n["s1_lam5.0"]
check("non-hardened ceiling tau=0.7303",
      abs(vn["tau_lodo"] - 0.7303) < 5e-4,
      f"tau_loo={vn['tau_lodo']:.4f}")
check("non-hardened ceiling R=1.0",
      abs(vn["tau_lodo"] - vn["tau_insample"]) < 1e-9,
      f"tau_in={vn['tau_insample']:.4f}")
c3 = json.loads((RES / "c3lite_multiseed.json").read_text())
check("C3 p_hg=0.0014",
      abs(c3["pairs"]["s0_lam2.0"]["p_hypergeom"] - 0.0014) < 5e-5)
check("C3 p_emp=0.0015",
      abs(c3["pairs"]["s0_lam2.0"]["p_empirical"] - 0.0015) < 5e-5)
check("C3 null mean 0.23", abs(c3["null_mean"] - 0.23) < 5e-3,
      f"null_mean={c3['null_mean']:.3f}")

print("== 4. supplemental docx spot checks ==")
sup = Document(BASE / "Supplemental_Information_Patterns.docx")
alltext = []
for t in sup.tables:
    for row in t.rows:
        alltext.append(" | ".join(c.text for c in row.cells))
joined = "\n".join(alltext)
s6_row = [r for r in alltext if r.startswith("1.0 | 16")]
check("S6 sig1.0 n16 worst 0.56", any("0.56" in r for r in s6_row),
      s6_row[0] if s6_row else "row missing")
check("S6 intact 0.90", "0.90" in joined)
check("S2 clearance ~11.6%", "11.6%" in joined or "11.6" in joined)
check("S4 recheck 4.4%", "4.4%" in joined)
check("S4 non-hardened R=1.000 at s1 lam5",
      any("s1 | 5.0" in r and "1.000" in r for r in alltext))
check("S7 six markers at lam5 recovery",
      "s1_lam5.0" in joined and "CDKN2A" in joined)
s9_row = [r for r in alltext if r.startswith("0.0 | ")]
check("S9 baseline mean 0.906", any("0.906" in r for r in s9_row),
      s9_row[0] if s9_row else "row missing")
check("S9 repair not improving (0.766–0.813 present)",
      any(r.startswith("0.5 |") and "0.781" in r for r in alltext))

print("== 5. references (Cell Press numbered style) ==")
refs = re.findall(r"\n(\d{1,2})\. ", md.split("## REFERENCES")[1])
check("14 references", len(refs) == 14, f"found {len(refs)}")
ref_section = md.split("## REFERENCES")[1]
check("refs contain journal + year",
      all(y in ref_section for y in ["2024", "2026"]))
check("GSE268014 cited", "GSE268014" in md)

print("== 6. placeholders the user must fill before submission ==")
ph = re.findall(r"\[[A-Za-z][^\]]{2,40}\]", md)
ph += re.findall(r"\[[A-Za-z][^\]]{2,40}\]",
                 (BASE / "CoverLetter_Patterns.md").read_text(encoding="utf-8"))
ph += re.findall(r"\[[A-Za-z][^\]]{2,40}\]",
                 (BASE / "TitlePage_Patterns.md").read_text(encoding="utf-8"))
uniq = sorted(set(p for p in ph if "repository URL" in p or
                  any(k in p for k in ("Lead", "Second", "Third", "Date",
                                      "lead.email", "Department",
                                      "status to be", "Corresponding",
                                      "Phone", "Email", "Affiliation"))))
for p in uniq:
    print(f"  [TODO] fill placeholder {p}")

print()
print(f"TOTAL: {len(PASS)} PASS, {len(FAIL)} FAIL")
for name, det in FAIL:
    print(f"  FAILED: {name} {det}")
