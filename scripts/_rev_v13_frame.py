#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_rev_v13_frame.py — v12 -> v13

三类改动，全部针对编辑初审视角：

A. 把「prior work 没做 measurement」换成「prior work 测量了，但单位不可迁移」，
   并给 post-hoc 场景的普遍性补实证（不再是断言）。
   - 新增 ref 43: Yagis et al. Sci. Rep. 11, 22544 (2021)
     脑 MRI slice 级 vs subject 级分裂：准确率虚高 30/29/48/55 个百分点；
     随机标签下 slice 级 ~96% vs subject 级 ~50%。
   - post-hoc 普遍性：直接引用 [42] 自己统计的 294 篇已发表论文
     —— 每一篇的设计期补救都是追溯性不可用的。

B. tier 1 重框为「一个对象，两个组件」而非「两个 findings」，
   并贯彻到 Highlights / 编号列表 / 投稿信。

C. 投稿信加一句可读懂的具体反事实场景。
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "papers" / "20_MRP-ST-Repair_Patterns"
SRC = D / "MRP-ST-Repair_manuscript_Patterns_v12.md"
DST = D / "MRP-ST-Repair_manuscript_Patterns_v13.md"

s = io.open(SRC, encoding="utf-8").read()
n_ok = 0


def rep(old, new, cnt=1):
    global s, n_ok
    c = s.count(old)
    if c != cnt:
        for v in (old.replace("\u2019", "'"), old.replace("'", "\u2019"),
                  old.replace("\u201c", '"'), old.replace("\u201d", '"')):
            if s.count(v) == cnt:
                old, c = v, cnt
                break
    assert c == cnt, "count=%d for %r" % (c, old[:80])
    s = s.replace(old, new)
    n_ok += 1


# ---------------------------------------------------------------- A1 Yagis
YAGIS_ANCHOR = (
    "construct the split so that no group straddles it,[8,40,41] and disclose "
    "what you did.[42] Both are design-time remedies"
)
rep(YAGIS_ANCHOR,
    "construct the split so that no group straddles it,[8,40,41] and disclose "
    "what you did.[42] The size of the effect has been measured too, field by "
    "field: on brain MRI, splitting a volume at slice level rather than subject "
    "level raised reported accuracy by 30, 29, 48 and 55 percentage points on "
    "four datasets, and a randomly relabelled dataset still returned about 96% "
    "accuracy under the slice-level split against about 50% under the "
    "subject-level one.[43] Both are design-time remedies")

# ------------------------------------------------- A2 不可迁移 + post-hoc 普遍性
rep("The case this paper addresses is the one they do not cover, and in practice "
    "it is the common one: the representation already exists.",
    "What none of them supplies is a number that travels: the inflation is "
    "reported in each dataset's own accuracy units, against a null specific to "
    "that model and that split, so the 30 and the 55 cannot be compared with "
    "each other, carried into a new cohort, or set against a threshold that "
    "decides anything. The case this paper addresses is the one they do not "
    "cover, and it is not a rare one: the representation already exists. The "
    "taxonomy of ref [42] documents leakage in 294 papers that had already been "
    "published when it was compiled, and for every one of them the design-time "
    "remedy is retroactively inapplicable, because the split that produced a "
    "number cannot be redesigned once the number is in print; the reassessments "
    "that do get published, ref [41] among them, re-evaluate the model under a "
    "corrected protocol rather than measuring the figure that was reported.")

# ------------------------------------------------------------- B1 Highlights
rep("1. Sibling units let held-out units be re-identified, so unit-level splits overstate\n"
    "2. Blocked splits prevent group leakage; this grades it after training, no retraining\n"
    "3. A calibrated index grades leakage and stays non-blind after de-identification\n",
    "1. Sibling units let held-out units be re-identified, so unit-level splits overstate\n"
    "2. One post-hoc audit grades the leak after training, with no new split or retraining\n"
    "3. The index is itself tested after repair against controls with known ground truth\n")

# --------------------------------------------------------------- B2 tier 结构
rep("The contribution has two tiers. Two findings carry it, and neither of them is "
    "the repair operator. Five further findings are the diagnostics and the "
    "intervention that make the two usable:",
    "The contribution has two tiers. The first tier is one object with two "
    "components rather than two independent results: a post-hoc audit needs both "
    "a reason to measure and a measurement, and neither component is the repair "
    "operator. Five further findings are the diagnostics and the intervention "
    "that make the audit usable:")

# ------------------------------------------------------------------ A3 ref 43
REF42 = "42. Kapoor, S., and Narayanan, A. Leakage and the reproducibility crisis in machine-learning-based science. Patterns 4, 100804 (2023). https://doi.org/10.1016/j.patter.2023.100804."
REF43 = ("43. Yagis, E., Atnafu, S.W., Garc\u00eda Seco de Herrera, A., Marzi, C., "
         "Scheda, R., Giannelli, M., Tessa, C., Citi, L., and Diciotti, S. Effect "
         "of data leakage in brain MRI classification using 2D convolutional neural "
         "networks. Sci. Rep. 11, 22544 (2021). "
         "https://doi.org/10.1038/s41598-021-01681-w.")
assert REF42 in s
s = s.replace(REF42, REF42 + "\n" + REF43)
n_ok += 1

# 校验：Highlights 每条 ≤85 字符
for line in s.split("\n"):
    m = re.match(r"^([1-4])\. (.+)$", line)
    if m and line.startswith(("1. Sibling", "2. One post", "3. The index",
                              "4. Where each")):
        assert len(m.group(2)) <= 85, "highlight %s too long: %d" % (m.group(1), len(m.group(2)))

io.open(DST, "w", encoding="utf-8").write(s)
print("manuscript v13 written; replacements =", n_ok)

# ===================================================================== 投稿信
P = D / "CoverLetter_Patterns.md"
c = io.open(P, encoding="utf-8").read()
m_ok = 0


def crep(old, new, cnt=1):
    global c, m_ok
    k = c.count(old)
    if k != cnt:
        for v in (old.replace("\u2019", "'"), old.replace("'", "\u2019")):
            if c.count(v) == cnt:
                old, k = v, cnt
                break
    assert k == cnt, "cover count=%d for %r" % (k, old[:70])
    c = c.replace(old, new)
    m_ok += 1


crep("blocked or group-disjoint cross-validation is the established prescription "
     "wherever data carry temporal, spatial or hierarchical structure.",
     "blocked or group-disjoint cross-validation is the established prescription "
     "wherever data carry temporal, spatial or hierarchical structure. The "
     "magnitude is not in dispute either: on brain MRI, splitting at slice level "
     "rather than subject level raised reported accuracy by 29 to 55 percentage "
     "points across four datasets (Yagis et al., Sci. Rep. 11, 22544, 2021).")

crep("The case we address is the one they do not cover, and in practice it is the "
     "common one: the representation already exists.",
     "The case we address is the one they do not cover, and it is not a rare one: "
     "the representation already exists. That taxonomy documents leakage in 294 "
     "papers that had already been published when it was compiled, and for every "
     "one of them the design-time remedy is retroactively inapplicable, because "
     "the split that produced a number cannot be redesigned once the number is in "
     "print.")

# C. 具体反事实场景
SCENARIO = (
    "\nOne sentence is worth making concrete, because it is the whole argument. "
    "A clinical researcher inherits an imaging model trained on data from ten "
    "hospitals that reports a high held-out AUROC. The training pipeline is gone, "
    "the compute budget is spent, and the split that produced the number was at "
    "image level. Group-disjoint splitting cannot help her: it is an instruction "
    "for a training run she is not going to perform. A checklist cannot help her "
    "either: it would have her disclose something she does not yet know. What she "
    "needs is a number, namely of the AUROC she is looking at, how much would "
    "survive if whole hospitals were held out, expressed against what permutation "
    "alone would have produced. That is the quantity the label-dependence index "
    "returns, and the sibling-unit trap is the reason to expect the published "
    "figure to be optimistic in the first place.\n"
)
ANCHOR = ("The label-dependence index is the counterfactual measurement taken on "
          "the representation as it stands, and the sibling-unit trap is the "
          "effect it exists to detect.")
assert c.count(ANCHOR) == 1
c = c.replace(ANCHOR, ANCHOR + SCENARIO)
m_ok += 1

# 投稿信：tier 也写成「一个对象两个组件」
crep("The second is the instrument itself: a calibrated index with operating "
     "characteristics measured on controls with known ground truth, an acceptance "
     "protocol, and two decision boundaries that say in advance whether repair is "
     "even coherent for a given cohort.",
     "The second is the instrument itself: a calibrated index with operating "
     "characteristics measured on controls with known ground truth, an acceptance "
     "protocol, and two decision boundaries that say in advance whether repair is "
     "even coherent for a given cohort. Those first two are halves of one object "
     "rather than two results: a post-hoc audit needs both a reason to measure "
     "after training and a measurement that can be shown still to work, and "
     "neither half is the operator.")

io.open(P, "w", encoding="utf-8").write(c)
print("cover letter updated; replacements =", m_ok)
