# -*- coding: utf-8 -*-
"""v6: reviewer round-2 fixes (evidence grading, unit/table numbers, refs, front matter).
Run from repo root or anywhere; paths are absolute.
"""
import io, os, sys

BASE = r"G:/project4_cervix_multimodal/papers/20_MRP-ST-Repair_Patterns"
SRC = os.path.join(BASE, "MRP-ST-Repair_manuscript_Patterns_v5.md")
DST = os.path.join(BASE, "MRP-ST-Repair_manuscript_Patterns_v6.md")

txt = io.open(SRC, encoding="utf-8").read()

REPS = []


def rep(old, new, expect=1):
    REPS.append((old, new, expect))


# ---------------------------------------------------------------- 1. contribution 6 typo
rep(
    "We report this as a boundary on claims, not as a defect: and, more importantly, "
    "as something the framework predicts in advance rather than discovers afterwards.",
    "We report this as a boundary on claims, not as a defect, and, more importantly, "
    "as something the framework predicts in advance rather than discovers afterwards.",
)

# ---------------------------------------------------------------- 2. Discussion: grade the positive repair evidence
rep(
    "Because the failure modes are diagnosable from the sign and direction of the cross-group "
    "statistic (gap down, LDI positive; invariance claimed, LDI up), the taxonomy is usable on "
    "any method, including ones not tested here.\n\n### Implications for fairness",
    "Because the failure modes are diagnosable from the sign and direction of the cross-group "
    "statistic (gap down, LDI positive; invariance claimed, LDI up), the taxonomy is usable on "
    "any method, including ones not tested here.\n\n"
    "**How far the positive repair evidence extends.** One more grading is worth stating "
    "explicitly, because it bounds how the operator should be read. Real-data cases in which "
    "repair removed leakage that the instrument had detected are confined to two small cohorts "
    "of the validation domain: head and neck (16 patients; baseline LDI 2.18 falling to "
    "1.13-1.37 at lambda = 0.5, all three seeds below the gate) and prostate (52 patients; 2.04 "
    "to 1.51 at lambda = 1.0, two of three seeds). Both are single-section-per-donor cohorts of "
    "modest size, and the prostate result is seed-fragile. The two non-biological cohorts, which "
    "do carry multi-unit identity channels, were used to test the instrument and the two "
    "boundaries only: they have no endpoint, so they say nothing about whether removing identity "
    "there pays. We therefore do not claim that repair has been shown to help on real multi-unit "
    "data; we claim that the instrument has been shown to work there, and that on the only "
    "cohorts where a downstream endpoint exists the instrument has so far returned a negative "
    "recommendation. The design that would settle the question is a cohort in which each donor "
    "contributes several sections and a usable endpoint exists, so that a sibling channel is "
    "present and its removal can be scored. We flag that as the next experiment rather than as "
    "something this paper has done.\n\n### Implications for fairness",
)

# ---------------------------------------------------------------- 3. Table 2: real numbers for lambda = 1, 2
OLD_T2 = (
    "| Head and neck (16) | 0 | 2.2 (1.88\u20132.49) | 0/3 | 0.34 | 0.69\u20130.94 | baseline above gate |\n"
    "| | 0.5 | 1.25 (1.13\u20131.37) | 3/3 | \u2248 0.32 | 0.38\u20130.59 | minimum LDI; all seeds accepted |\n"
    "| | 1 | \u2014 | 2/3 | \u2014 | 0.38\u20130.59 | accepted |\n"
    "| | 2 | \u2014 | 2/3 | \u2014 | 0.38\u20130.59 | accepted |\n"
    "| | 5 | rebound above gate | 0/3 | 0.64 (seed 1) | 0.90 (seed 1) | maximal-dose recovery point |\n"
)
NEW_T2 = (
    "| Head and neck (16) | 0 | 2.18 (1.88\u20132.49) | 0/3 | 0.59 (0.50\u20130.68) | 0.69\u20130.94 | baseline above gate |\n"
    "| | 0.5 | 1.22 (1.13\u20131.37) | 3/3 | 0.35 (0.32\u20130.39) | 0.44\u20130.53 | minimum LDI; all seeds accepted |\n"
    "| | 1 | 1.27 (0.95\u20131.82) | 2/3 | 0.37 (0.27\u20130.52) | 0.38\u20130.41 | accepted |\n"
    "| | 2 | 1.55 (1.32\u20131.73) | 2/3 | 0.44 (0.39\u20130.50) | 0.59 | accepted |\n"
    "| | 5 | 1.34 (0.33\u20132.19) | 2/3 | 0.37 (0.09\u20130.64) | 0.13\u20130.90 | rebounding, seed-unstable; excluded by the safety axis |\n"
)
rep(OLD_T2, NEW_T2)

# Table 2 legend: name the gate and the R convention
rep(
    "Primary runs are reported; the independent prostate re-run is noted. The last row shows a "
    "dose the gate rejects despite carrying the numerically best endpoint. Baseline (\u03bb = 0) LDI in "
    "this configuration is 2.2 for head and neck and 2.04 for prostate;",
    "Values are from the stability-hardened three-seed graph-attention run (300 epochs). "
    "\"Gate passes\" counts seeds whose LDI falls below 1.645, i.e. the leakage-reduction axis of "
    "the acceptance protocol; a dose can pass that axis and still be excluded by the safety axis, "
    "which is what happens at \u03bb = 5 on head and neck. R is reported over the seeds that pass at that "
    "dose; pooled over all seven accepted head-and-neck cells the range is 0.38\u20130.60, the figure "
    "quoted in the text. Primary runs are reported; the independent prostate re-run is noted. The "
    "last row shows a dose the gate rejects despite carrying the numerically best endpoint. "
    "Baseline (\u03bb = 0) LDI in this configuration is 2.18 for head and neck and 2.04 for prostate;",
)

# ---------------------------------------------------------------- 4. Table 1: HNSCC tau_base / sigma
rep(
    "| Head and neck (16 patients, GSE268014) | etiological (HPV) | 0.34 | \u2248 0.155 | \u2248 2.2 | non-empty |",
    "| Head and neck (16 patients, GSE268014) | etiological (HPV) | 0.59 | \u2248 0.27 | \u2248 2.2 | non-empty |",
)

# ---------------------------------------------------------------- 5. Table 3: cohort C sub-gate caveat (both copies)
C_CAVEAT = (
    " Cohort C's baseline LDI is +0.345, already below the 1.645 gate, so repair moves the index "
    "from a small positive to a small negative value: the confound is removed and the sign flips, "
    "but this is not a gate crossing and cannot be read as one, because no gate separated the two "
    "states."
)
rep(
    "**Table 3. Head-to-head comparison of deconfounding methods on matched simulation cohorts "
    "(three seeds).** Cohort A (safety): strong shared target program. Cohort C (leakage): "
    "identity-fingerprint confound only. LDI is the leakage-detection index (gate 1.645); "
    "R = \u03c4_LDO/\u03c4_in.",
    "**Table 3. Head-to-head comparison of deconfounding methods on matched simulation cohorts "
    "(three seeds).** Cohort A (safety): strong shared target program. Cohort C (leakage): "
    "identity-fingerprint confound only. LDI is the leakage-detection index (gate 1.645); "
    "R = \u03c4_LDO/\u03c4_in." + C_CAVEAT,
)
# the legend copy is hard-wrapped, so match it with a whitespace-tolerant regex
import re as _re
LEGEND_T3 = _re.compile(
    r"for each arm\. Adversarial repair \(MRP\) removes the cohort-C confound while leaving "
    r"cohort-A\s+signal at the\s+ceiling; Group-DRO reduces the in-sample gap but leaves or "
    r"increases\s+cross-group label dependence; IRM\s+amplifies the group fingerprint\."
)


def _legend_t3(m):
    return m.group(0) + C_CAVEAT


_txt2, _n = LEGEND_T3.subn(_legend_t3, txt)
if _n != 1:
    print("!! MISS legend Table 3 caveat:", _n)
    sys.exit(1)
txt = _txt2

# ---------------------------------------------------------------- 6. two shared-program configurations
rep(
    "at every dose (Figure 2A). This is the correct outcome, not a failure:",
    "at every dose (Figure 2A). The safety panel and the matched simulation cohorts of Table 3 are "
    "two different parameterisations of the same generator and should not be read as one cohort: "
    "the panel uses 50-versus-40 label classes and sits at LDI 5.6\u20136.1, whereas the matched "
    "cohorts of Table 3 use 32 donors in 18-versus-14 classes (800 units each) and sit at +3.54 on "
    "the safety arm; the difference in level is a difference of configuration. This is the correct "
    "outcome, not a failure:",
)

# ---------------------------------------------------------------- 7. reference [1] DOI
rep(
    "Companion study; preprint DOI to be added before submission (interim access: "
    "https://github.com/WorldBMW/cervix-st-multimodal).",
    "Companion study. Preprint DOI: TO BE INSERTED BEFORE SUBMISSION (a posted preprint must be "
    "live and linked at submission; interim access: "
    "https://github.com/WorldBMW/cervix-st-multimodal).",
)

# ---------------------------------------------------------------- apply
fail = 0
for old, new, expect in REPS:
    n = txt.count(old)
    if n != expect:
        print("!! MISS (%d, expected %d): %s" % (n, expect, old[:90].replace("\n", " ")))
        fail += 1
        continue
    txt = txt.replace(old, new)

if fail:
    print("ABORT: %d replacements failed" % fail)
    sys.exit(1)

io.open(DST, "w", encoding="utf-8").write(txt)
print("wrote", DST, len(txt), "chars")
