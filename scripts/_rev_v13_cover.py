#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_rev_v13_cover.py — 投稿信补单位分辨率对照。"""
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "papers" / "20_MRP-ST-Repair_Patterns" / "CoverLetter_Patterns.md"
c = io.open(P, encoding="utf-8").read()

old = ("Our framework predicts this in advance, and the correct action it prescribes "
       "for cohorts of that shape is group-disjoint splitting and the audit, not "
       "repair. We think stating that plainly is more useful to readers than burying "
       "it, and we have made it one of the four highlights.")
assert c.count(old) == 1, c.count(old)

new = old + """

One control bears on how that scope condition should be read, because the obvious objection is that our cohorts look free of a sibling channel only because we declared one section per donor to be the unit. We re-ran the cervical cohort with the embedding, the grouping variable and the donor-level label held fixed and the unit redefined as a block of spots inside a section, so that each donor contributes three or eight sibling units sharing its label. The channel still did not open (tau_LOO 0.455 to 0.458 at every resolution; sibling inflation within +0.0072 at every dose and seed), while an identity classifier fitted on the same embedding kept a lift of 16 to 28 times chance, so the embedding had not lost donor identity. The same control fixes a limit we would rather state than be told: sigma_hat is the null scale at the declared resolution, so LDI is comparable across cohorts and domains at a fixed number of units and not across resolutions of the same data, and the unit of analysis has to be declared before the audit is run (Table S16)."""

io.open(P, "w", encoding="utf-8").write(c.replace(old, new))
print("cover letter control added")
