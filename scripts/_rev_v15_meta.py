# -*- coding: utf-8 -*-
"""v15 补：摘要压到 <=150 词；投稿信同步。"""
from pathlib import Path

D = Path(r"G:\project4_cervix_multimodal\papers\20_MRP-ST-Repair_Patterns")

# ------------------------------------------------------------------ summary
p = D / "MRP-ST-Repair_manuscript_Patterns_v15.md"
t = p.read_text(encoding="utf-8")

OLD = ("When the same person, site, or device contributes many observations, a model can score well by "
       "recognising the group rather than the property it should predict. We call this identity leakage. "
       "Whenever a group contributes several units, unit-level cross-validation stays at ceiling while "
       "group-level holdout collapses: held-out units are re-identified through siblings. Around this we "
       "build an auditable instrument: a calibrated index of label dependence under leave-one-group-out, "
       "tested after repair on controls with known ground truth; a pre-computed condition saying whether "
       "any dose can remove identity and keep signal; and two boundaries saying which cohorts are repairable. "
       "The repair operator is deliberately standard and we claim no superiority for it. Validation is "
       "end-to-end in spatial transcriptomics only; two non-biological cohorts audit predictions, and the "
       "rest are untested mappings. Where each group contributes one unit, no accepted repair improved a "
       "downstream endpoint, a regime the framework predicts in advance.")

NEW = ("When one person, site, or device contributes many observations, a model can win by recognising the "
       "group, not the property it should predict. We call this identity leakage. Where a group contributes "
       "several units, unit-level cross-validation stays at ceiling while group-level holdout collapses: "
       "held-out units are re-identified through siblings. Around this sits an auditable instrument: a "
       "calibrated index of label dependence under leave-one-group-out, tested against planted controls "
       "after repair; a pre-computed condition saying whether any dose can remove identity and keep signal; "
       "and two boundaries saying which cohorts are repairable. The repair operator is standard and we claim "
       "no superiority for it. Validation is end-to-end in spatial transcriptomics alone; two non-biological "
       "cohorts audit predictions, the rest are untested mappings. Where each group contributes one unit, no "
       "accepted repair improved a downstream endpoint, which the framework predicts in advance.")

assert t.count(OLD) == 1
t = t.replace(OLD, NEW)
p.write_text(t, encoding="utf-8")

w = len(NEW.split())
print(f"summary words: {w}  (limit 150) -> {'OK' if w <= 150 else 'OVER'}")
assert w <= 150

# ------------------------------------------------------------------ cover letter
c = D / "CoverLetter_Patterns.md"
s = c.read_text(encoding="utf-8")

rep = [
    ("we have made it one of the four highlights",
     "we have made it one of the five highlights"),
    ("We claim that the instrument works there; we do not claim that repair has been shown to help on real multi-unit data.",
     "We claim that the instrument works there; we do not claim that repair has been shown to help on real multi-unit data. "
     "For the same reason we would ask the referees to read the head-to-head comparison as a demonstration of the instrument "
     "rather than as a ranking of removal methods: the operator inside our loop is a standard adversarial head, we benchmarked "
     "only Group-DRO and IRM alongside it, we did not benchmark null-space projection, contrastive or reweighting families, and "
     "we claim no superiority for it over any of them. The protocol (the calibrated index, the three axes and group-level "
     "acceptance) reads a representation rather than a training objective, so it can be run on the output of any deconfounding "
     "method a practitioner already uses, and we regard a study that does so across those families as a direct extension."),
]
for o, n in rep:
    assert s.count(o) == 1, (s.count(o), o[:50])
    s = s.replace(o, n)
c.write_text(s, encoding="utf-8")
print("cover letter updated")
