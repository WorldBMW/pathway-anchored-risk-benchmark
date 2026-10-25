# -*- coding: utf-8 -*-
"""v18 -> v19 for the Patterns manuscript.

Changes, all in the legend apparatus (no numbers touched):

1. Symbols block: add what n counts (donors vs simulated groups, never mixed)
   and what every error bar / +- value / band is (SD across training seeds,
   never SEM). This is the one thing the reviewer asked for that was genuinely
   absent: the definitions existed in Experimental Procedures but not where a
   reader meets a figure.
2. Figure 3A: n is simulated group count, say so at the panel.
3. Figure 5: the caption promised "mean +- spread" while the old figure drew
   means only. The figure now draws each seed and SD bars, so the caption is
   rewritten to match.
4. Figure 2A/B: state that each point is one run.
"""
from pathlib import Path

SRC = Path("papers/20_MRP-ST-Repair_Patterns/MRP-ST-Repair_manuscript_Patterns_v18.md")
DST = Path("papers/20_MRP-ST-Repair_Patterns/MRP-ST-Repair_manuscript_Patterns_v19.md")

s = SRC.read_text(encoding="utf-8")
n0 = len(s)

# ---------------------------------------------------------------- 1. symbols
head = "**G** is the number of groups."
tail = "Every figure and table below is readable without reference to the main text."
i = s.index(head) + len(head)
END = "readable without reference to the main text."
j = s.index(END, i) + len(END)
assert j - i < 200, "unexpected span in the symbols block"

NEW = ("\n\n"
       "**What n counts, and what the bars are.** In the real-cohort figures n counts independent donors, "
       "patients or cases, never units; in the simulation figures n counts simulated groups and is a design "
       "parameter rather than a sample size; the two are never combined in a reported statistic, and the "
       "distinction is set out cohort by cohort under Experimental Procedures (\"What each n counts\"). Where a "
       "panel varies the dose, each faint marker is one training seed, the line joins the seed means, and every "
       "error bar, \u00b1 value and shaded band is the standard deviation across those seeds, except where a band "
       "is described as a range, in which case it spans the minimum to the maximum seed. No standard error of the "
       "mean is used as a dispersion measure in any figure or table; the single standard error quoted in the text "
       "(prostate AUROC) appears only to show that a difference is unresolved at that n.\n\n"
       + tail)
s = s[:i] + NEW + s[j:]

# ------------------------------------------------------------------ 2. fig 3A
OLD = "group count n and dose \u03bb, at planted signal amplitude 1.0 and 0.3 (three seeds per cell)"
NEW = ("group count n and dose \u03bb, at planted signal amplitude 1.0 and 0.3 (three seeds per cell; n here "
       "counts simulated groups, not donors)")
assert s.count(OLD) == 1, "fig3 anchor"
s = s.replace(OLD, NEW)

# ------------------------------------------------------------------ 3. fig 5
OLD = ("three seeds per point, mean \u00b1 spread across the dose\nschedule.")
NEW = ("three training seeds per dose and per domain, each drawn as a faint marker, with the line at the seed "
       "mean and the error bars at the standard deviation across those three seeds.")
assert s.count(OLD) == 1, "fig5 anchor"
s = s.replace(OLD, NEW)

# --------------------------------------------------------------- 4. fig 2 A/B
OLD = ("across planted-program amplitudes, doses and seeds\n(graph-attention encoder; graph-convolutional "
       "replication at the reference amplitude)")
NEW = ("across planted-program amplitudes, doses and seeds, each point one run\n(graph-attention encoder; "
       "graph-convolutional replication at the reference amplitude)")
assert s.count(OLD) == 1, "fig2A anchor"
s = s.replace(OLD, NEW)

OLD = "(36 of 36 among dosed runs, no false alarms)"
NEW = "(36 of 36 among dosed runs, no false alarms; each point is one run)"
assert s.count(OLD) == 1, "fig2B anchor"
s = s.replace(OLD, NEW)

DST.write_text(s, encoding="utf-8")
print("wrote", DST)
print("chars %d -> %d (+%d)" % (n0, len(s), len(s) - n0))
for tag in ("\u2014", "**What n counts", "each point one run", "each point is one run",
            "n here \ncounts simulated groups"):
    print("  %-28r %d" % (tag, s.count(tag)))
