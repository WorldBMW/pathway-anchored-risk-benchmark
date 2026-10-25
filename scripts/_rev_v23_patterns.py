"""v22 -> v23: clear the placeholder strings and front-load the scope argument.

Three reviewer points were actioned, one was rejected with evidence.

1. Placeholders. The literal string "TO BE INSERTED BEFORE SUBMISSION" appears
   four times in v22 (Code, Key Resources Table, Data and Code Availability,
   reference 1). It is replaced by text that states the Cell Press timing
   truthfully: a DOI-minting archive is required *before publication*, and the
   tagged release is the frozen, citable state in the meantime. That removes the
   template-leftover signal without asserting a DOI that does not exist.

2. Companion study. No preprint DOI can be minted from here, so reference 1 is
   rewritten as what it actually is: a related manuscript, declared under
   "related manuscripts" in the cover letter, with the tagged release as
   verifiable interim access. Reference numbering is deliberately left alone;
   renumbering 42 references would desynchronise the Supplemental Information,
   which is cumulative and cannot be regenerated from the markdown.

3. Cover letter. The scope argument is moved to the front under its own heading,
   a duplicated sentence is removed, and two further "to be inserted" strings
   that the reviewer did not spot are cleared.

Rejected: the Data Science Maturity Scale. The live Patterns Information for
Authors page (fetched 2026-10-25) lists no DSML requirement anywhere - not
under Policies, not under Components to include, not under Final file
requirements - and the journal has been phasing the scale out since 2024.
Adding a retired badge would date the submission.

Anchors are matched as exact substrings, and every replacement is asserted, so
a rewrap of the markdown cannot silently drop an edit.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPERS = ROOT / "papers" / "20_MRP-ST-Repair_Patterns"

SRC = PAPERS / "MRP-ST-Repair_manuscript_Patterns_v22.md"
DST = PAPERS / "MRP-ST-Repair_manuscript_Patterns_v23.md"
COVER = PAPERS / "CoverLetter_Patterns.md"

PLACEHOLDER = "TO BE INSERTED BEFORE SUBMISSION"

MS_EDITS = [
    # ---- Code (Resource availability) -------------------------------------
    (
        "and archived at Zenodo (DOI: "
        + PLACEHOLDER
        + "). The release follows the FAIR principles[22]",
        "and deposited in Zenodo before publication, whose DOI is reported in "
        "the version of record; the tagged release above is the frozen state "
        "against which every number in this paper was produced and is the "
        "accessible interim location. The release follows the FAIR "
        "principles[22]",
    ),
    # ---- Key resources table ----------------------------------------------
    (
        "https://github.com/WorldBMW/cervix-st-multimodal (tag v1.0.0); "
        "Zenodo DOI: " + PLACEHOLDER,
        "https://github.com/WorldBMW/cervix-st-multimodal (tag v1.0.0); "
        "Zenodo archive of the same state, DOI reported in the version of record",
    ),
    # ---- Data and code availability ---------------------------------------
    (
        "and archived at Zenodo (DOI: "
        + PLACEHOLDER
        + "; the tagged GitHub release is the accessible interim location). "
        "Both the tag and the DOI are frozen before submission so that the "
        "archived state matches the reported numbers exactly.",
        "and deposited in Zenodo before publication, whose DOI is reported in "
        "the version of record; the tagged release is the accessible interim "
        "location. The tag and the archive are cut from the same commit, so "
        "the archived state matches the reported numbers exactly.",
    ),
    # ---- Reference 1 -------------------------------------------------------
    (
        "Companion study. Preprint DOI: "
        + PLACEHOLDER
        + ". Interim access: https://github.com/WorldBMW/cervix-st-multimodal.",
        "Companion manuscript (related submission); the cervical cohort "
        "definition is restated in Experimental Procedures and every number in "
        "this paper was produced here from the public accessions. Interim "
        "access: https://github.com/WorldBMW/cervix-st-multimodal/releases/tag/v1.0.0.",
    ),
]

COVER_EDITS = [
    # a duplicated sentence, concatenated without a space in v22
    (
        "reproducible from a manifest.In keeping with Patterns' emphasis on "
        "open, reproducible science, all code, the domain-agnostic cohort "
        "simulator, configuration manifests, and seeds are released (GitHub "
        "and Zenodo), and every reported number is reproducible from a manifest.",
        "reproducible from a manifest.",
    ),
    # Unicode rather than ASCII, per the house convention
    ("sigma_hat is the null scale", "\u03c3\u0302 is the null scale"),
    ("critical retention c* (the largest retention requirement",
     "critical retention c_crit (the largest retention requirement"),
    # two further "to be inserted" strings the review did not list
    (
        "it is being posted to a preprint server before submission and its DOI "
        "will be inserted in place of the current placeholder, with the GitHub "
        "repository serving as interim access",
        "it is being posted to a preprint server; reference [1] records the "
        "tagged code release as interim access, so the cohort definition behind "
        "it is verifiable from this submission alone",
    ),
    (
        "our companion audit study is cited within the manuscript [status to be "
        "inserted: under review elsewhere]",
        "our companion audit study is cited within the manuscript as reference "
        "[1], and its status is stated in the paragraph above",
    ),
    (
        "The division of labour between the two papers is as follows, and we "
        "state it because reference [1] is the only cited work that is not "
        "independently published.",
        "**Division of labour.** The division of labour between the two papers "
        "is as follows, and we state it in this much detail because reference "
        "[1] is the only cited work that is not independently published and "
        "because a question about salami slicing is better pre-empted than "
        "answered. The two papers share no result, table or figure.",
    ),
]

WHY_PATTERNS = """**Why this is a Patterns paper and not a spatial-transcriptomics paper.** We put this first, because the answer to "is this broadly interesting" is not a list of results. First, the object of the paper is a failure of *evaluation*, not a result in a field. Group structure is present wherever patients, sites, speakers, subjects or batches contribute more than one observation, which is most of applied machine learning; what we measure is a property of the split rather than of the modality, and what we prescribe is a rule about where acceptance is measured, which a practitioner can adopt at no cost and which errs in one direction only. Second, the deliverable is a measurement rather than a model. It takes a representation, a grouping variable, a label and a leave-one-group-out probe, and returns a number in permutation-null units; nothing in the index, in either decision boundary or in the acceptance protocol refers to anything that a transcriptomic cohort specifically supplies. In that respect the paper sits with the cross-field leakage taxonomy of Kapoor and Narayanan (Patterns 4, 100804, 2023), which Patterns published and which remains among the journal's most-read articles: an instrument for measuring and reporting a failure that recurs across fields. Third, spatial transcriptomics is the testbed we chose and not the subject we studied. It offers clean group structure, labels whose coupling to identity varies in kind, public cohorts for external replication, and a simulator with known ground truth, which is what an instrument needs in order to be calibrated rather than merely demonstrated. What that buys, and what it does not, is stated in tiers below: validated end to end in one domain, audited against real data in two non-biological domains that carry no endpoint, and declared untested in the six remaining rows of Table 4.

"""


def apply(text: str, edits: list[tuple[str, str]], label: str) -> str:
    for old, new in edits:
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{label}: anchor matched {n} times:\n  {old[:120]}")
        text = text.replace(old, new)
    return text


def main() -> int:
    ms = SRC.read_text(encoding="utf-8")
    cov = COVER.read_text(encoding="utf-8")

    ms = apply(ms, MS_EDITS, "manuscript")
    cov = apply(cov, COVER_EDITS, "cover letter")

    anchor = (
        "We believe this framing, and what it lets us prove, is what makes the "
        "work a fit for Patterns rather than for a domain journal.\n"
    )
    if cov.count(anchor) != 1:
        raise SystemExit("cover letter: opening-paragraph anchor not unique")
    cov = cov.replace(anchor, anchor + "\n" + WHY_PATTERNS)

    assert PLACEHOLDER not in ms, "a manuscript placeholder survived"
    assert PLACEHOLDER not in cov, "a cover-letter placeholder survived"

    DST.write_text(ms, encoding="utf-8")
    COVER.write_text(cov, encoding="utf-8")

    words = len(re.findall(r"\b[\w'-]+\b", ms))
    print(f"wrote {DST.name} ({words:,} whitespace tokens in the whole file)")
    print("wrote CoverLetter_Patterns.md")
    print("placeholders remaining: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
