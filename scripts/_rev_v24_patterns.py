"""v24 revisions to the Patterns manuscript and cover letter.

Three changes, each responding to a checked external fact:

1. Highlights: Cell Press allows at most 4 highlights (85 chars each). The
   manuscript had 5. Old #4 (gate semantics) and #5 (validation scope) are
   merged into one line that keeps both.

2. Reference 1: "Companion manuscript (related submission)" is replaced by
   "Manuscript in preparation, declared as a related manuscript in the cover
   letter and supplied with this submission as a related file".
   Rationale: Cell Press journal policies require authors to DECLARE related
   papers in the cover letter, indicate how they are related, and supply them
   as related files at initial submission; failure to supply them "may be
   grounds for rejection". Deleting the reference (the alternative suggested)
   would remove the disclosure the policy requires, and would force the
   renumbering of 42 references against a cumulatively-built SI.

3. Cover letter: the related-work paragraph is rewritten to satisfy the
   policy verbatim (declaration + relationship + related file), and adds the
   fact that the cervical data are public accessions, which is the direct
   answer to the "data submitted elsewhere" clause.
"""

from pathlib import Path

PAPERS = Path(__file__).resolve().parents[1] / "papers" / "20_MRP-ST-Repair_Patterns"
SRC = PAPERS / "MRP-ST-Repair_manuscript_Patterns_v23.md"
DST = PAPERS / "MRP-ST-Repair_manuscript_Patterns_v24.md"
COVER = PAPERS / "CoverLetter_Patterns.md"

EDITS = [
    # ---- 1. Highlights: 5 -> 4 -------------------------------------------
    (
        "highlights 4+5 merged",
        "4. Passing the gate means leakage is below threshold, not that group is gone\n"
        "5. Validated in one domain; two cohorts test predictions, not repair utility",
        "4. One domain is validated end to end; the gate bounds leakage, never erasure",
    ),
    # ---- 2. Reference 1 --------------------------------------------------
    (
        "reference 1 wording",
        "Companion manuscript (related submission); the cervical cohort definition is "
        "restated in Experimental Procedures and every number in this paper was produced "
        "here from the public accessions. Interim access: "
        "https://github.com/WorldBMW/cervix-st-multimodal/releases/tag/v1.0.0.",
        "Manuscript in preparation, declared as a related manuscript in the cover letter "
        "and supplied with this submission as a related file; the cervical cohort "
        "definition is restated in Experimental Procedures, and every number in this "
        "paper was produced here from the public accessions.",
    ),
]

COVER_EDITS = [
    (
        "related-work paragraph",
        "Preprints and related work. Consistent with your instructions, we list the "
        "preprint status of everything connected to this submission. The manuscript "
        "itself will be posted as a preprint before or at submission; the link will be "
        "added to this letter and to the manuscript metadata. The companion audit study "
        "on which the detection statistic's operating characteristics partly rest is "
        "cited as reference [1]; it is being posted to a preprint server; reference [1] "
        "records the tagged code release as interim access, so the cohort definition "
        "behind it is verifiable from this submission alone.",
        "Preprints and related work. **This manuscript** will be posted as a preprint "
        "before or at submission; the link will be added to this letter and to the "
        "manuscript metadata. **Related manuscript.** One related paper is declared. "
        "Cell Press asks authors to declare related papers in preparation, submitted, or "
        "in press elsewhere, to indicate how they are related, and to supply them with "
        "the initial submission as related files; we do so here. The related paper is "
        "the companion audit study that introduced the label-dependence index and first "
        "reported the cervical observation, cited in the manuscript as reference [1]. It "
        "is currently a manuscript in preparation, and it is supplied with this "
        "submission as a related file. No DOI is recorded for it yet. The manuscript "
        "entry for reference [1] will be updated to match. Its relationship to this "
        "submission is set out in the next paragraph, and the manuscript itself repeats "
        "the part that matters: the cervical cohort definition is restated in "
        "Experimental Procedures, so nothing here becomes unverifiable if reference [1] "
        "were withdrawn. The cervical data behind both papers are public accessions "
        "(10x Genomics public datasets and GSE217237), so no dataset is proprietary to "
        "either manuscript; what the two papers do not share is any result.",
    ),
]


def apply(text: str, edits, label: str) -> str:
    for name, old, new in edits:
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{label}: '{name}' matched {n} times, expected 1")
        text = text.replace(old, new)
        print(f"  {label}: {name} -> ok")
    return text


def main() -> None:
    ms = apply(SRC.read_text(encoding="utf-8"), EDITS, "manuscript")
    DST.write_text(ms, encoding="utf-8")
    print(f"wrote {DST.name}")

    cov = apply(COVER.read_text(encoding="utf-8"), COVER_EDITS, "cover")
    COVER.write_text(cov, encoding="utf-8")
    print(f"updated {COVER.name}")


if __name__ == "__main__":
    main()
