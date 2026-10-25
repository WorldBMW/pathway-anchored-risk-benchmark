# -*- coding: utf-8 -*-
"""v15 元信息收口：In brief 压回 50 词内，TitlePage 统计按实测值同步。"""
import re
from pathlib import Path

D = Path(r"G:\project4_cervix_multimodal\papers\20_MRP-ST-Repair_Patterns")

# ---------------------------------------------------------- In brief (<=50 words)
p = D / "MRP-ST-Repair_manuscript_Patterns_v15.md"
t = p.read_text(encoding="utf-8")

OLD_IB = ("Many datasets are group-structured, so a model can win by recognising the group rather than the "
          "target property. Bai and colleagues show that unit-level cross-validation hides this and supply an "
          "auditable instrument: a calibrated index, a rule for the split, and boundaries saying in advance "
          "whether repair can pay. The loop is validated end to end in spatial transcriptomics alone; two "
          "non-biological cohorts audit its predictions only, six further domains are untested mappings, and "
          "no accepted repair improved a downstream endpoint.")
NEW_IB = ("Group-structured data let a model win by recognising the group. Bai and colleagues supply an "
          "auditable instrument: a calibrated index, a rule for the split, and boundaries saying in advance "
          "whether repair pays. Validated in one domain; elsewhere only predictions are audited, and no "
          "accepted repair improved an endpoint.")
if t.count(NEW_IB) == 0:
    assert t.count(OLD_IB) == 1, "in-brief anchor"
    t = t.replace(OLD_IB, NEW_IB)
    p.write_text(t, encoding="utf-8")
n_ib = len(NEW_IB.split())
print("in-brief words:", n_ib, "->", "OK" if n_ib <= 50 else "OVER")
assert n_ib <= 50

# ---------------------------------------------------------- measure front matter
lines = t.split("\n")
i = lines.index("## HIGHLIGHTS")
hl = [l.strip() for l in lines[i + 1:i + 12] if re.match(r"^\d+\. ", l.strip())]
j, k = lines.index("## IN BRIEF"), lines.index("## SUMMARY")
k2 = lines.index("## GRAPHICAL ABSTRACT")
s = " ".join(l for l in lines[k + 1:k2] if not l.startswith("**Keywords:**")).strip()
n_sum = len(s.split())
b0, b1 = lines.index("## BIGGER PICTURE"), lines.index("## INTRODUCTION")
bp = " ".join(lines[b0 + 1:b1]).strip()
n_bp = len(bp.split())

# Bigger picture 超限则压缩（保留"算子非贡献"的新增义）
if n_bp > 300:
    OLD_BP = bp
    NEW_BP = ("Most datasets scientists analyse are not collections of independent measurements. They are "
              "collections of clusters: one patient contributes several tissue sections, one hospital "
              "contributes many scans, one speaker contributes many utterances, one station contributes "
              "thousands of readings. Standard practice treats the measurements as exchangeable and splits "
              "them at random, keeping members of one cluster on both sides. A model can then score well by "
              "recognising the cluster a measurement came from rather than the property of interest, "
              "reporting excellent held-out performance while collapsing on any cluster it has not seen. We "
              "call this identity leakage. Three features make it worth naming. It is invisible to the "
              "metrics normally reported, so it is usually discovered as a reproducibility failure rather "
              "than a mechanism. It is a property of how the data were collected, not of any model, so no "
              "tuning removes it. And the cluster is frequently a person or an institution, so a model that "
              "reads it performs unevenly across the people it was trained on, which makes the failure a "
              "fairness problem as well as an accuracy one. This paper offers neither a better model nor a "
              "better deconfounding operator: the repair operator below is standard and we claim no "
              "superiority for it. What it offers is an instrument: a calibrated statistic asking how much "
              "of a model's reported performance survives removal of the cluster, together with a test of "
              "whether the instrument still works once a repair has been applied. With it come a feasibility "
              "condition and two decision boundaries that let a practitioner decide, before spending compute, "
              "whether attempting a repair is worth it at all, and one worked case in which the answer is "
              "that it is not. It needs only a recorded grouping variable, a label, and a linear probe.")
    OLD_BP = t[t.index("## BIGGER PICTURE") + len("## BIGGER PICTURE"):t.index("## INTRODUCTION")]
    assert OLD_BP.strip(), "bigger picture block empty"
    t = t.replace(OLD_BP, "\n\n" + NEW_BP + "\n\n")
    p.write_text(t, encoding="utf-8")
    n_bp = len(NEW_BP.split())
    print("bigger picture compressed ->", n_bp)
    assert n_bp <= 300

print(f"highlights: {len(hl)} | max len {max(len(h) for h in hl)}")
print(f"summary: {n_sum} | bigger picture: {n_bp}")
assert len(hl) == 5 and max(len(h) for h in hl) <= 85
assert n_sum <= 150 and n_bp <= 300

# ---------------------------------------------------------- TitlePage
tp = D / "TitlePage_Patterns.md"
s = tp.read_text(encoding="utf-8")
OLD18 = ("**Manuscript statistics:** In brief, 49 words (limit 50); Summary, 150 words (limit 150); "
         "4 highlights (all \u226485 characters, Cell Press maximum); bigger picture box, 299 words (limit 300);")
NEW18 = (f"**Manuscript statistics:** In brief, {n_ib} words (limit 50); Summary, {n_sum} words (limit 150); "
         f"{len(hl)} highlights (all \u226485 characters, Cell Press maximum); bigger picture box, {n_bp} words (limit 300);")
assert s.count(OLD18) == 1
s = s.replace(OLD18, NEW18)

OLD22a = "*Summary* (133 words, limit 150) is the author summary of what was done and found."
NEW22a = f"*Summary* ({n_sum} words, limit 150) is the author summary of what was done and found."
assert s.count(OLD22a) == 1
s = s.replace(OLD22a, NEW22a)

OLD22b = "*In brief* (45 words, limit 50) is the eTOC blurb, third person, aimed at a non-specialist."
NEW22b = f"*In brief* ({n_ib} words, limit 50) is the eTOC blurb, third person, aimed at a non-specialist."
assert s.count(OLD22b) == 1
s = s.replace(OLD22b, NEW22b)

OLD22c = "*Highlights* (4 bullets, each \u226485 characters, Cell Press maximum)"
NEW22c = f"*Highlights* ({len(hl)} bullets, each \u226485 characters, Cell Press maximum)"
assert s.count(OLD22c) == 1
s = s.replace(OLD22c, NEW22c)
tp.write_text(s, encoding="utf-8")
print("titlepage synced")
