"""v25 revisions: remove reference 1 entirely and make the cervical cohort self-contained.

Why this version exists
-----------------------
v24 replaced the placeholder with "Manuscript in preparation, declared as a related
manuscript ...".  The concern raised is fair: a numbered reference to an unpublished
manuscript is awkward, and three passages in the paper were leaning on the number
1.00 -> 0.497, which is not reproducible from anything in this paper (our own runs on
the cervical cohort give LODO AUROC 0.73-0.97 and a retention of 0.92, not a collapse
to chance).  So:

  * reference 1 is deleted; references 2..43 become 1..42, and GSE208654 is added as
    the new 43 (the SI carries no numbered citations, so the renumber is safe);
  * every one of the seven "[1]" citations is removed, and the three passages that used
    the companion as evidence are rewritten or dropped;
  * the cervical cohort is now defined in full in Experimental Procedures - sources,
    section names, the donor-level severity rule, the resulting class counts, the
    preprocessing and the unit of analysis - so the sentence that used to claim
    "the cervical cohort definition is restated in Experimental Procedures" is now
    actually true (it was not: the string "inclusion" did not occur anywhere).

What is deliberately NOT done: the related-manuscript disclosure is not removed.
Cell Press journal policies require it in the cover letter and as a related file;
"failure to provide copies of related manuscripts ... may be grounds for rejection".
It simply moves out of the manuscript, where the policy never asked for it.
"""

from pathlib import Path
import re

PAPERS = Path(__file__).resolve().parents[1] / "papers" / "20_MRP-ST-Repair_Patterns"
SRC = PAPERS / "MRP-ST-Repair_manuscript_Patterns_v24.md"
DST = PAPERS / "MRP-ST-Repair_manuscript_Patterns_v25.md"
COVER = PAPERS / "CoverLetter_Patterns.md"

GUO_REF = (
    "44. [Dataset] Guo, C. Spatiotemporally deciphering the unknown role of persistent "
    "HPV infection in precancer to cervical cancer progression: integrating "
    "single-cell RNA-sequencing landscape and spatial transcriptomics atlas. Gene "
    "Expression Omnibus GSE208654 (2023)."
)

EDITS = [
    # ---- Introduction: define the index here, drop the unreproducible number ----
    (
        "introduction",
        "Detection of this failure mode has recently become quantitative. In a companion "
        "study[1] we introduced a calibrated label-dependence index (LDI), a "
        "permutation-refit statistic that detects group-block leakage and, in a cervical "
        "neoplasia cohort, showed that a model with in-sample AUROC 1.00 collapses to "
        "chance (0.497) under leave-one-donor-out evaluation. That observation is where "
        "the problem we take up comes from and it carries no result below: every number "
        "reported in this paper is recomputed by our own runs on the public accessions "
        "listed in the resource table, and reference [1] is cited only here and in that "
        "table.",
        "Detection of this failure mode has recently become quantitative. This paper "
        "defines a calibrated label-dependence index (LDI): a permutation-refit statistic "
        "that measures how much of a group's identity a linear readout can still recover "
        "from a representation, evaluated under leave-one-group-out and calibrated "
        "against a null obtained by refitting the same probe on permuted labels. Its "
        "operating characteristics are measured here, on controls with known ground "
        "truth, and the cervical cohort on which the phenomenon is easiest to see is "
        "defined in full in Experimental Procedures from public accessions alone, so "
        "that no step of this paper depends on a source a reader cannot fetch.",
    ),
    # ---- sibling-unit trap: drop the "same effect in the wild" companion claim ----
    (
        "trap support 1",
        "Table 5, Table S13). The companion study’s leave-one-donor-out AUROC collapse "
        "from 1.00 to 0.497 is the same effect in the wild.[1] The remedy is a rule "
        "rather than a method:",
        "Table 5, Table S13). The remedy is a rule rather than a method:",
    ),
    (
        "trap support 1b",
        "The companion study's leave-one-donor-out AUROC collapse is exactly this effect "
        "in the wild; here it is produced and controlled with a single knob.",
        "Here the same effect is produced and controlled with a single knob.",
    ),
    (
        "trap support 2",
        "The trap therefore rests on three independent supports: 45 of 45 simulated "
        "runs, 30 of 30 real cross-domain cells, and a clinical cohort in the companion "
        "study.[1] None of them is one of the two small cohorts that carry the repair "
        "result, which is why we separate this claim from the question of how far the "
        "positive repair evidence extends.",
        "The trap therefore rests on two independent supports: 45 of 45 simulated runs "
        "and 30 of 30 real cross-domain cells. Neither of them is one of the two small "
        "cohorts that carry the repair result, which is why we separate this claim from "
        "the question of how far the positive repair evidence extends.",
    ),
    # ---- cervical results: drop the commensurability passage ----
    (
        "cervical results",
        "The companion study reports the motivating collapse in different units, and the "
        "two are not commensurable, so we cite it as the origin of the observation rather "
        "than as corroboration of a measurement made here: there, a model that separated "
        "its cohort perfectly in sample (AUROC 1.00) fell to chance under "
        "leave-one-donor-out evaluation (0.497);[1] here, the in-sample association is "
        "almost entirely retained under donor holdout (τ_in = 0.462 against τ_LOO of "
        "about 0.42, a retention of 0.92; Table S3), so what is large on this cohort is "
        "the level of the held-out association relative to the permutation null (about "
        "0.17), not the drop away from the in-sample fit. The mechanistic reading above "
        "rests on the dose response and on the random-label control of the next "
        "paragraph, not on reference [1].",
        "What is large on this cohort is the level of the held-out association relative "
        "to the permutation null (about 0.17), not the drop away from the in-sample fit: "
        "the in-sample association is almost entirely retained under donor holdout "
        "(τ_in = 0.462 against a τ_LOO of about 0.42, a retention of 0.92; Table S3). "
        "The mechanistic reading above rests on the dose response and on the random-label "
        "control of the next paragraph.",
    ),
    # ---- Experimental Procedures: the cohort, defined ----
    (
        "cohort definition",
        "The cervical cohort (35 Visium sections with ordinal severity labels) is as "
        "described in the companion study[1] (10x Genomics public datasets and "
        "GSE217237[18]).",
        "The cervical cohort is 35 Visium sections from 34 donors, assembled from public "
        "sources only and reconstructed by the released script "
        "`download_and_prepare_cervix.py`: four sections of the HPV-stratified cervical "
        "lesion series GSE208654[44] (N_HPV normal cervix, HSIL_HPV high-grade "
        "intraepithelial lesion, CA_HPV_1 squamous carcinoma, CA_HPV_2 adenocarcinoma), "
        "one cervical carcinoma section from the 10x Genomics public Visium dataset "
        "(cervical_cancer_1), and 30 normal ectocervical mucosa sections from "
        "GSE217237[18] (GSM8811056–GSM8811065, GSM9044528–GSM9044535, "
        "GSM9053839–GSM9053850). Two of the sections come from one donor, which is why "
        "the section count exceeds the donor count by one. The label is donor-level "
        "ordinal severity, parsed from the section name by a fixed rule that the released "
        "code reproduces verbatim: normal cervix or ectocervical mucosa 0, HSIL, CIN or "
        "dysplasia 1, carcinoma 2. This gives 31 normal, 1 high-grade and 3 carcinoma "
        "sections and 46,820 spots in total. Counts were converted to CPM, "
        "log1p-transformed and restricted to the 2,000 most variable genes, every section "
        "was mean-pooled over its spots to give one embedding per section, and the unit "
        "of analysis is the section, so each donor contributes one unit.",
    ),
    # ---- Key resources table ----
    (
        "key resources table",
        "| Deposited data | Cervical Visium, ordinal severity (35 sections, 34 donors) "
        "| companion study [1]; 10x Genomics public data; GEO | GSE217237 |",
        "| Deposited data | Cervical Visium, ordinal severity (35 sections, 34 donors) "
        "| 10x Genomics public data; GEO | GSE208654; GSE217237 |",
    ),
    # ---- Data and code availability ----
    (
        "data availability",
        "The cervical cohort is as described in the companion study.[1]",
        "The cervical cohort is assembled from GSE208654[44] and GSE217237[18] together "
        "with the 10x Genomics public Visium datasets, and its composition, severity "
        "labelling and preprocessing are stated in Experimental Procedures, so it is "
        "reproducible from public sources alone.",
    ),
]

COVER_EDITS = [
    (
        "related manuscript",
        "The related paper is the companion audit study that introduced the "
        "label-dependence index and first reported the cervical observation, cited in the "
        "manuscript as reference [1]. It is currently a manuscript in preparation, and it "
        "is supplied with this submission as a related file. No DOI is recorded for it "
        "yet. The manuscript entry for reference [1] will be updated to match. Its "
        "relationship to this submission is set out in the next paragraph, and the "
        "manuscript itself repeats the part that matters: the cervical cohort definition "
        "is restated in Experimental Procedures, so nothing here becomes unverifiable if "
        "reference [1] were withdrawn. The cervical data behind both papers are public "
        "accessions (10x Genomics public datasets and GSE217237), so no dataset is "
        "proprietary to either manuscript; what the two papers do not share is any "
        "result.",
        "The related paper is a companion audit study by the same group that also "
        "formulates the label-dependence index and reports an earlier cervical "
        "observation. It is currently a manuscript in preparation and is supplied with "
        "this submission as a related file. No DOI is recorded for it yet. It is not "
        "cited anywhere in the manuscript: the cervical cohort is defined in full in "
        "Experimental Procedures from public accessions, the index is re-derived there, "
        "and every number below was produced by our own runs, so no result in this "
        "submission depends on it. The cervical data behind both papers are public "
        "accessions (10x Genomics public datasets, GSE208654 and GSE217237), so no "
        "dataset is proprietary to either manuscript; what the two papers do not share is "
        "any result, table or figure.",
    ),
    (
        "division of labour",
        "**Division of labour.** The division of labour between the two papers is as "
        "follows, and we state it in this much detail because reference [1] is the only "
        "cited work that is not independently published and because a question about "
        "salami slicing is better pre-empted than answered. The two papers share no "
        "result, table or figure. Reference [1] introduced the label-dependence index and "
        "reports the motivating cervical observation, in-sample AUROC 1.00 collapsing to "
        "0.497 under leave-one-donor-out evaluation; that observation is not one of this "
        "paper's results and is not used as evidence here, and it is reported in units "
        "that are not commensurable with the rank statistics used throughout: on the "
        "cohort we analyse, the in-sample association is almost entirely retained under "
        "donor holdout (τ_in = 0.462 against τ_LOO of about 0.42), so the manuscript now "
        "cites reference [1] as the origin of the phenomenon and not as corroboration of "
        "a measurement made here. This paper re-derives the index, fixes the permutation "
        "depth and the gate, and re-measures its operating characteristics on its own "
        "planted controls, 75 of 75 positive-control runs and 45 of 45 "
        "identity-confounding runs, both reported in the manuscript. Every cervical number "
        "that carries one of our findings, including the leave-one-out association of "
        "approximately 0.42 against a null scale of about 0.17 and the bistable dose "
        "response, was produced by our own runs on the public accession GSE217237 rather "
        "than taken from the companion study, and no result in this submission becomes "
        "unreproducible if reference [1] were withdrawn. No other unpublished manuscript "
        "from this group shares its aims, methods, or datasets.",
        "**Division of labour.** The division of labour between the two papers is as "
        "follows, and we state it in this much detail because a question about salami "
        "slicing is better pre-empted than answered. The two papers share no result, "
        "table or figure. The related paper formulates the label-dependence index and "
        "reports an earlier cervical observation, in units that are not commensurable "
        "with the rank statistics used throughout; that observation is not one of this "
        "paper's results and does not appear in it. This paper re-derives the index, "
        "fixes the permutation depth and the gate, and re-measures its operating "
        "characteristics on its own planted controls, 75 of 75 positive-control runs and "
        "45 of 45 identity-confounding runs, both reported in the manuscript. Every "
        "cervical number that carries one of our findings, including the leave-one-out "
        "association of approximately 0.42 against a null scale of about 0.17 and the "
        "bistable dose response, was produced by our own runs on the public accessions "
        "(GSE208654 and GSE217237) rather than taken from the related paper, and no "
        "result in this submission becomes unreproducible if that paper were withdrawn. "
        "No other unpublished manuscript from this group shares its aims, methods, or "
        "datasets.",
    ),
    (
        "declarations",
        "our companion audit study is cited within the manuscript as reference [1], and "
        "its status is stated in the paragraph above.",
        "our companion audit study is declared in the paragraph above and is supplied as "
        "a related file; it is not cited in the manuscript, which is self-contained.",
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


def renumber(text: str, top: int) -> str:
    """Delete reference 1 and shift 2..top down by one, inline and in the list."""
    text = re.sub(r"\[(\d+)\]",
                  lambda m: f"[{int(m.group(1)) - 1}]"
                  if 2 <= int(m.group(1)) <= top else m.group(0),
                  text)
    lines = text.split("\n")
    out, inblock = [], False
    for line in lines:
        if line.strip().upper() == "## REFERENCES":
            inblock = True
            out.append(line)
            continue
        if inblock:
            m = re.match(r"^(\d+)\. ", line)
            if m:
                n = int(m.group(1))
                if n == 1:
                    continue          # drop the Bai entry
                line = re.sub(r"^(\d+)\. ",
                              lambda mm: f"{int(mm.group(1)) - 1}. ", line)
        out.append(line)
    return "\n".join(out)


def main() -> None:
    ms = apply(SRC.read_text(encoding="utf-8"), EDITS, "manuscript")
    ms = ms.rstrip("\n") + "\n" + GUO_REF + "\n"
    ms = renumber(ms, top=44)

    # ---- post-checks -----------------------------------------------------
    cited = sorted({int(x) for x in re.findall(r"\[(\d+)\]", ms)})
    refs = [l for l in ms.split("\n")
            if re.match(r"^\d+\. ", l) and "REFERENCES" not in l]
    nrefs = len([l for l in ms.split("\n")[ms.split("\n").index("## REFERENCES") + 1:]
                 if re.match(r"^\d+\. ", l)])
    print(f"  inline citations: max {max(cited)}, {len(cited)} distinct")
    print(f"  reference entries: {nrefs}")
    for bad in ("[1] Bai", "companion study", "companion manuscript", "in preparation",
                "related submission", "reference [1]"):
        if bad in ms:
            raise SystemExit(f"manuscript still contains {bad!r}")
    if nrefs != 43 or max(cited) > 43:
        raise SystemExit(f"renumber inconsistent: {nrefs} refs, max citation {max(cited)}")
    print("  manuscript: no companion wording, 43 references, self-contained")

    DST.write_text(ms, encoding="utf-8")
    print(f"wrote {DST.name}")

    cov = apply(COVER.read_text(encoding="utf-8"), COVER_EDITS, "cover")
    COVER.write_text(cov, encoding="utf-8")
    print(f"updated {COVER.name}")


if __name__ == "__main__":
    main()
