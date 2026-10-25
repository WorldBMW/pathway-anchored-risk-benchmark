#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_rev_v14_cover.py — v14 投稿信 + 正文计数同步（GSE316098 受控对照）。"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "papers" / "20_MRP-ST-Repair_Patterns"


def patch(path, reps, tag):
    p = D / path
    t = p.read_text(encoding="utf-8")
    for old, new in reps:
        assert t.count(old) == 1, f"{tag}: anchor count={t.count(old)}"
        t = t.replace(old, new)
    p.write_text(t, encoding="utf-8")
    print(f"  ok: {tag}")


# ---------------------------------------------------------------- 正文计数
patch("MRP-ST-Repair_manuscript_Patterns_v14.md", [(
    "the verdict matched what was subsequently observed in six of six cohorts "
    "(Table 1)",
    "the verdict matched what was subsequently observed in seven of seven cohorts "
    "(Table 1; the GeoMx cohort enters once, carrying the three labels of the "
    "control below)",
)], "manuscript: six -> seven cohorts")

# ---------------------------------------------------------------- 投稿信
NEW_CONTROL = (
    "A second control asks what actually opens the channel, because the "
    "cross-domain comparison that supports boundary I holds identifiability only "
    "approximately (10.4x versus 9.1x chance) and an identifiability-based account "
    "would have predicted no ordering there. We ran it on a NanoString GeoMx "
    "cohort of HPV-associated endocervical adenocarcinoma (GSE316098: 186 regions "
    "of interest from 7 cases) in which each ROI carries its own pathology "
    "annotation and the source study deliberately selected cases containing two "
    "distinct invasion patterns inside the same tumour, so the label is not a "
    "donor-level value broadcast to every unit of a donor. Holding the data and "
    "the grouping fixed and changing only the label gives three arms whose "
    "group-label coupling is kappa = 0.000, 0.225 and 0.273 and which share one "
    "and the same baseline embedding, so encoded identity is identical rather "
    "than merely matched (6.55x chance in all three). Sibling inflation then "
    "tracked coupling and nothing else: +0.0075, +0.3736 and +0.3955 at baseline, "
    "with no overlap between the per-cell distributions of the arms, and the "
    "transferable association that repair preserved fell from 0.989 to 0.806 to "
    "0.717 of baseline in the same order. Two consequences follow that we prefer "
    "to state up front. The trap is conditional rather than universal: where the "
    "label carries no information about the group there is no channel to open and "
    "no repair to justify, which is the scope condition in positive form. And the "
    "dual gate is uninformative at both ends, empty where the pre-repair signal is "
    "strong and vacuous where it is indistinguishable from the null, so a small "
    "accepted set on strong-signal clinical labels is a predicted outcome rather "
    "than a shortfall of the experiment (Table S17).\n"
)

CL_ANCHOR = ("In keeping with Patterns' emphasis on open, reproducible science, "
             "all code, the domain-agnostic cohort simulator, configuration "
             "manifests, and seeds are released")
patch("CoverLetter_Patterns.md", [
    (CL_ANCHOR, NEW_CONTROL + "\n" + CL_ANCHOR),
    ("the verdict matched what was subsequently observed in six of six cohorts;",
     "the verdict matched what was subsequently observed in seven of seven "
     "cohorts;"),
    ("which is what the framework predicts in advance for "
     "single-section-per-donor cohorts.",
     "which is what the framework predicts in advance for "
     "single-section-per-donor cohorts. The count is explained and not merely "
     "reported: Proposition 1 makes the dual gate empty wherever the pre-repair "
     "association exceeds about 2.35 null scales, the control above shows that "
     "repair damages the transferable signal in proportion to how much the label "
     "shares with the group (0.989 of baseline retained where coupling is zero, "
     "0.717 where it is highest), and the fidelity axis is satisfied almost "
     "automatically when the baseline association is itself indistinguishable "
     "from the null, so the band in which an accepted cell carries information is "
     "narrow by construction."),
], "cover letter: control + counts")

print("done")
