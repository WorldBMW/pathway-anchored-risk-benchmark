#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build the JBI and CBM submission packages for MRP-ST-Repair (Elsevier).

The scientific content is identical to the Patterns package; only the Elsevier-
specific conventions differ: SUMMARY -> Abstract, EXPERIMENTAL PROCEDURES ->
Methods, plus Highlights, a journal-specific cover letter and title page. Figures
and supplemental tables are copied verbatim.

Outputs:
  papers/21_MRP-ST-Repair_JBI/    {Manuscript,TitlePage,CoverLetter,Highlights}_JBI.{md,docx}
  papers/22_MRP-ST-Repair_CBM/    {Manuscript,TitlePage,CoverLetter,Highlights}_CBM.{md,docx}
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from md_to_docx_patterns import convert  # noqa: E402

PAPERS = ROOT / "papers"
SRC = PAPERS / "20_MRP-ST-Repair_Patterns"
SRC_MD = SRC / "MRP-ST-Repair_manuscript_Patterns_v1.md"

TITLE = ("MRP-ST-Repair: training-time adversarial repair of patient-identity "
         "leakage in spatial transcriptomics")

HIGHLIGHTS = [
    "Training-time adversarial repair removes patient-identity leakage from ST models",
    "Repair preserves shared disease programs in 75 of 75 positive controls",
    "A proposition separates detection from acceptance and yields a three-axis protocol",
    "Repairability is set by label-identity coupling, donor count, and surviving biology",
]

# journal-specific metadata
JOURNALS = {
    "JBI": {
        "dir": PAPERS / "21_MRP-ST-Repair_JBI",
        "name": "Journal of Biomedical Informatics",
        "article_type": "Research Article",
        "scope": ("We believe this work fits JBI's scope well: it is a reusable "
                  "biomedical-informatics method that closes a quality-assurance "
                  "loop for machine-learning models trained on spatially resolved "
                  "biological cohort data, with a formal statistical core (a "
                  "feasibility proposition separating detection from acceptance "
                  "statistics), negative- and positive-control experimental design, "
                  "external validation on public data, and a ready-to-run protocol "
                  "for the small-cohort regime that dominates biomedical and "
                  "clinical informatics studies."),
    },
    "CBM": {
        "dir": PAPERS / "22_MRP-ST-Repair_CBM",
        "name": "Computers in Biology and Medicine",
        "article_type": "Research Article",
        "scope": ("We believe this work fits CBM's scope well: it is a new "
                  "computational method for spatial transcriptomics with direct "
                  "biomedical application, demonstrated on real cervical and "
                  "head-and-neck cancer cohorts (the HPV-status signal mapping onto "
                  "the keratinization program). It addresses a reproducibility "
                  "failure — patient-block label leakage — that silently inflates "
                  "model evaluation in cancer biology, and it does so with a formal "
                  "statistical core, controlled simulations, and external "
                  "validation."),
    },
}

MANUSCRIPT_TRANSFORMS = [
    ("## SUMMARY", "## ABSTRACT"),
    ("## EXPERIMENTAL PROCEDURES", "## METHODS"),
    ("Experimental Procedures", "Methods"),
    ("*Manuscript type: original research article. "
     "Lang Guo is the corresponding author.*",
     "*Original research article. Lang Guo is the corresponding author.*"),
    # Elsevier rear-matter section naming
    ("## AUTHOR CONTRIBUTIONS", "## CRediT authorship contribution statement"),
    ("## DECLARATION OF INTERESTS", "## Declaration of competing interest"),
    ("## DECLARATION OF GENERATIVE AI USE",
     "## Declaration of generative AI and AI-assisted technologies in the writing process"),
    ("## ACKNOWLEDGMENTS", "## Acknowledgements"),
    # CRediT-conformant author contributions (full names + standard roles)
    ("M.B.: conceptualization, methodology, software, experiments, writing (original draft). Z.G.: data curation, validation. Y.Z.: investigation, review. Z.N.: resources, review. L.G.: supervision, project administration, writing (review and editing). All authors read and approved the final manuscript.",
     "Mingwei Bai: Conceptualization, Methodology, Software, Investigation, Writing – original draft. Zhengmin Gu: Data curation, Validation. Ye Zhang: Investigation, Writing – review & editing. Zhiping Ni: Resources, Writing – review & editing. Lang Guo: Supervision, Project administration, Writing – review & editing. All authors read and approved the final manuscript."),
]

AUTHOR_BLOCK = (
    "**Authors:** Mingwei Bai¹, Zhengmin Gu², Ye Zhang², Zhiping Ni¹, Lang Guo³\n"
    "**Affiliations:** ¹JiMei Technology Group Co., Ltd., Shenyang 110002, China; "
    "²Medical Record Management Center, The First Hospital of China Medical "
    "University, Shenyang 110002, China; ³School of Pharmacy, Shenyang Medical "
    "College, Shenyang 110034, China\n"
    "**Correspondence:** Lang Guo, School of Pharmacy, Shenyang Medical College, "
    "146 Huanghe North Avenue, Shenyang 110034, China. Tel: +86 13555707001; "
    "E-mail: guolang1016@symc.edu.cn\n"
    "**Author e-mails:** Mingwei Bai, baimingwei@jm360.cn; Zhengmin Gu, "
    "guzm@cmulh.com; Ye Zhang, 13332457636@163.com; Zhiping Ni, "
    "nizhiping@jm360.cn; Lang Guo, guolang1016@symc.edu.cn"
)


def build_manuscript_md(journal):
    text = SRC_MD.read_text(encoding="utf-8")
    for old, new in MANUSCRIPT_TRANSFORMS:
        assert old in text, f"manuscript transform anchor not found: {old!r}"
        text = text.replace(old, new)
    hl = "## HIGHLIGHTS\n\n" + "\n".join(f"- {h}" for h in HIGHLIGHTS) + "\n\n"
    assert "## INTRODUCTION" in text
    text = text.replace("## INTRODUCTION", hl + "## INTRODUCTION", 1)
    return text


def cover_letter(journal):
    return f"""[Date]

Dear Editors of {journal['name']},

We are pleased to submit our manuscript, "{TITLE}," for consideration as a {journal['article_type']} in {journal['name']}.

Spatial-transcriptomic models are routinely trained on cohorts of a few dozen patients. When patients contribute multiple spots or slides, models can succeed by recognizing which patient a spot came from rather than which disease state it represents — a patient-block label-leakage failure mode our previous audit work detects with a calibrated label-dependence index (LDI). Detection alone, however, leaves the practitioner without a remedy, and we show here that the natural post-hoc fix (projecting out patient-mean subspaces) destroys the transferable disease signal together with the leak. The present manuscript closes that gap with, to our knowledge, the first training-time repair method for patient-identity leakage in spatial transcriptomics, paired with a calibrated acceptance protocol.

Key results:

1. Training-time patient-adversarial repair preserves shared disease programs in 75 of 75 positive-control runs across program amplitudes, adversarial doses, seeds, and graph backbones (GAT and GCN), while the audit stays non-blind in 45 of 45 identity-confounding control runs (no false alarms).
2. A formal proposition separates detection from acceptance statistics: a naive dual "detect-then-accept" gate is feasible only when the pre-repair association is small relative to the null scale (τ_base/σ̂ < 1.645/c), which we resolve with a three-axis acceptance protocol (safety, leakage reduction, instrument non-blindness).
3. Repairability is a property of cohort structure, not of the method: etiological labels (HPV status) retain a transferable fraction R = 0.38–0.59 at accepted operating points in an external head-and-neck cancer cohort (GSE268014), with a maximal-dose recovery point of R = 0.90; ordinal severity labels admit no stable operating point at any dose. A donor-count feasibility boundary (n* between 16 and 32 donors per class at reference signal, shifting rightward as signal weakens; verified over five seeds) and a sibling-slice inflation effect that disqualifies slice-level cross-validation complete the characterization.
4. What survives repair is known biology: the post-repair HPV direction recovers the canonical HPV-status contrast (keratinization/differentiation markers; hypergeometric p = 0.0014), demonstrating at the molecular level what audited repair preserves.

{journal['scope']}

All code, configurations, seeds, and evidence artifacts are being released with the manuscript.

Important declarations: (i) This manuscript is a new methods paper and is not a resubmission of any previously rejected manuscript; our companion audit study is cited within the manuscript [status to be inserted: under review elsewhere]. (ii) This manuscript is not under consideration by any other journal, and all authors have approved the submission. (iii) During manuscript preparation we used an AI coding and writing assistant (Trae, Z.ai GLM), as declared in the manuscript; all content was reviewed, verified, and edited by the authors, who take full responsibility for the content.

Thank you for your consideration.

Sincerely,

Lang Guo, on behalf of all authors
School of Pharmacy, Shenyang Medical College, Shenyang 110034, China
guolang1016@symc.edu.cn | +86 13555707001
"""


def title_page(journal):
    return f"""# Title Page — {journal['name']}

**Article type:** {journal['article_type']}

**Title:** {TITLE}

{AUTHOR_BLOCK}

**Keywords:** spatial transcriptomics; information leakage; model auditing; adversarial training; reproducibility; head and neck cancer; HPV

**Declarations:** The authors declare no competing interests. Generative-AI use is declared in the manuscript (AI coding and writing assistant: Trae, Z.ai GLM; all content reviewed, verified, and edited by the authors, who take full responsibility).
"""


def highlights_md():
    return "# Highlights\n\n" + "\n".join(f"- {h}" for h in HIGHLIGHTS) + "\n"


def main():
    for tag, journal in JOURNALS.items():
        d = journal["dir"]
        d.mkdir(parents=True, exist_ok=True)

        # manuscript
        (d / f"Manuscript_{tag}.md").write_text(build_manuscript_md(journal),
                                                 encoding="utf-8")
        (d / f"TitlePage_{tag}.md").write_text(title_page(journal), encoding="utf-8")
        (d / f"CoverLetter_{tag}.md").write_text(cover_letter(journal),
                                                 encoding="utf-8")
        (d / f"Highlights_{tag}.md").write_text(highlights_md(), encoding="utf-8")

        for name in ["Manuscript", "TitlePage", "CoverLetter", "Highlights"]:
            convert(d / f"{name}_{tag}.md", d / f"{name}_{tag}.docx")

        # copy figures
        fdst = d / "figures"
        fdst.mkdir(exist_ok=True)
        for f in (SRC / "figures").glob("fig*.pdf"):
            shutil.copy2(f, fdst / f.name)
        for f in (SRC / "figures").glob("fig*.png"):
            shutil.copy2(f, fdst / f.name)

        # copy supplemental tables
        shutil.copy2(SRC / "Supplemental_Information_Patterns.docx",
                     d / f"Supplemental_Information_{tag}.docx")

        print(f"[package] {tag} -> {d.name}")

    for h in HIGHLIGHTS:
        assert len(h) <= 85, f"highlight exceeds 85 chars: {len(h)}"


if __name__ == "__main__":
    main()