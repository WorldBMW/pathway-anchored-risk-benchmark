# -*- coding: utf-8 -*-
"""v21: ref-1 author note out of the reference entry; cover letter gains the
companion division of labour and an explicit scope answer."""
from pathlib import Path

PAPERS = Path(__file__).resolve().parent.parent / "papers" / "20_MRP-ST-Repair_Patterns"
SRC = PAPERS / "MRP-ST-Repair_manuscript_Patterns_v20.md"
DST = PAPERS / "MRP-ST-Repair_manuscript_Patterns_v21.md"
COVER = PAPERS / "CoverLetter_Patterns.md"

s = SRC.read_text(encoding="utf-8")

# ---------------------------------------------------------------- manuscript
# Reference 1 carries an instruction to the author inside the reference entry,
# which would render in the published reference list. Keep the placeholder token
# (the DOI script matches on "Companion study. Preprint DOI: ") and keep the
# interim-access link, but drop the meta-instruction.
OLD_REF = ("Companion study. Preprint DOI: TO BE INSERTED BEFORE SUBMISSION "
           "(a posted preprint must be live and linked at submission; "
           "interim access: https://github.com/WorldBMW/cervix-st-multimodal).")
NEW_REF = ("Companion study. Preprint DOI: TO BE INSERTED BEFORE SUBMISSION. "
           "Interim access: https://github.com/WorldBMW/cervix-st-multimodal.")
assert s.count(OLD_REF) == 1, "ref-1 anchor not found exactly once"
s = s.replace(OLD_REF, NEW_REF, 1)

# Guard: no other author-to-self note should survive anywhere in the main text.
for bad in ("must be live", "TO BE INSERTED BEFORE SUBMISSION (a posted"):
    assert bad not in s, f"leftover author note: {bad}"

DST.write_text(s, encoding="utf-8")
print("manuscript -> v21")

# --------------------------------------------------------------- cover letter
c = COVER.read_text(encoding="utf-8")

# (a) division of labour with the companion study, asked for by the referee
OLD_C = ("its DOI will be inserted in place of the current placeholder, with the "
         "GitHub repository serving as interim access. No other unpublished "
         "manuscript from this group shares its aims, methods, or datasets.")
NEW_C = ("its DOI will be inserted in place of the current placeholder, with the "
         "GitHub repository serving as interim access. The division of labour "
         "between the two papers is as follows, and we state it because reference "
         "[1] is the only cited work that is not independently published. "
         "Reference [1] introduced the label-dependence index and reports the "
         "motivating cervical observation, in-sample AUROC 1.00 collapsing to "
         "0.497 under leave-one-donor-out evaluation; that observation is not one "
         "of this paper's results and is not used as evidence here. This paper "
         "re-derives the index, fixes the permutation depth and the gate, and "
         "re-measures its operating characteristics on its own planted controls, "
         "75 of 75 positive-control runs and 45 of 45 identity-confounding runs, "
         "both reported in the manuscript. Every cervical number that carries one "
         "of our findings, including the leave-one-out association of "
         "approximately 0.42 against a null scale of about 0.17 and the bistable "
         "dose response, was produced by our own runs on the public accession "
         "GSE217237 rather than taken from the companion study, and no result in "
         "this submission becomes unreproducible if reference [1] were withdrawn. "
         "No other unpublished manuscript from this group shares its aims, "
         "methods, or datasets.")
assert c.count(OLD_C) == 1, "cover anchor (a) not found exactly once"
c = c.replace(OLD_C, NEW_C, 1)

# (b) answer the scope objection head-on instead of leaving it to the referee
OLD_S = ("We also discuss the connection to group fairness: the feasibility "
         "algebra gives a way to recognise fairness\u2013utility conflicts as "
         "structural rather than as optimiser failures.")
NEW_S = ("One objection to scope deserves an answer rather than a deflection, "
         "because it is the one we would raise as a referee: the complete loop of "
         "repair, acceptance, endpoint, planted control and domain readout is "
         "closed in one application domain, two further domains are audited for "
         "predictions only, and six rows of Table 4 are untested mappings. We "
         "think that shape is correct for this contribution rather than a "
         "shortfall in it, for three reasons. First, the instrument is "
         "domain-agnostic by construction and not by assertion: its inputs are a "
         "grouping variable, an observation-level label, an encoder and a "
         "leave-one-group-out probe, and none of Proposition 1, the two decision "
         "boundaries or the acceptance protocol refers to anything that a "
         "transcriptomic cohort specifically supplies. Second, the cross-domain "
         "claims were falsification-tested rather than asserted: on two public "
         "non-biological cohorts, with the encoder swapped and nothing else "
         "changed, one prediction, an ordering between cohorts at comparable "
         "encoded identity, could have failed and did not, and the other, an "
         "empty dual gate, was confirmed in both. Third, and most to the point "
         "for a data-science journal, the readership for this work is defined by "
         "the failure mode and not by the modality: group structure is present "
         "wherever patients, sites, speakers, subjects or batches contribute more "
         "than one observation, which is most of applied machine learning, and "
         "the evaluation rule in our first finding costs nothing to adopt and "
         "errs in one direction only. In this respect the paper sits in the same "
         "genre as the cross-field leakage taxonomy of Kapoor and Narayanan "
         "(Patterns 4, 100804, 2023), which Patterns published and which remains "
         "among the journal's most-read articles: a measurement and reporting "
         "instrument for a failure that recurs across fields, validated "
         "rigorously where validation is possible and declared untested where it "
         "is not.\n\nWe also discuss the connection to group fairness: the "
         "feasibility algebra gives a way to recognise fairness\u2013utility "
         "conflicts as structural rather than as optimiser failures.")
assert c.count(OLD_S) == 1, "cover anchor (b) not found exactly once"
c = c.replace(OLD_S, NEW_S, 1)

assert "\u2014" not in c, "em-dash introduced into the cover letter"
COVER.write_text(c, encoding="utf-8")
print("cover letter updated")
