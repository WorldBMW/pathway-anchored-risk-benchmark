# Title Page (Patterns Submission)

**Article type:** Research Article (Patterns)

**Title:** An auditable instrument for identity leakage in group-structured data: the sibling-unit trap, decision boundaries, and validation in spatial transcriptomics

**Teaser (TOC, ≤120 characters):** Unit-level splits flatter models on group-structured data; an auditable index grades the leak and the repair.

**Authors:** Mingwei Bai¹, Zhengmin Gu², Ye Zhang², Zhiping Ni¹, Lang Guo³

**Affiliations:**
¹JiMei Technology Group Co., Ltd., Shenyang 110002, China
²Medical Record Management Center, The First Hospital of China Medical University, Shenyang 110002, China
³School of Pharmacy, Shenyang Medical College, Shenyang 110034, China

**Correspondence / Lead contact:** Lang Guo, School of Pharmacy, Shenyang Medical College, 146 Huanghe North Avenue, Shenyang 110034, China. Tel: +86 13555707001; E-mail: guolang1016@symc.edu.cn

**Manuscript statistics:** In brief, 49 words (limit 50); Summary, 138 words (limit 150); 5 highlights (all ≤85 characters, Cell Press maximum); bigger picture box, 295 words (limit 300); 1 graphical abstract; 5 main figures; 6 main tables (Tables 1–5 in the main text and the STAR-Methods Key Resources Table as Table 6); 17 supplemental tables (S1–S17; S13 carries the per-seed cross-domain inflation values behind the uncertainty interval reported in the text, S14 carries the per-cell dose-grid σ̂ drift and gate-robustness check behind the pre-computability scope condition, S15 carries the sensitivity of the feasibility threshold to the retained fraction c, S16 carries the unit-resolution ladder, and S17 carries the within-group-label control in which the data and the grouping are held fixed and only the label changes); 43 references.

**Graphical abstract:** `figures/graphical_abstract_1200.png` (1200 × 1200 px at 300 dpi, Arial; the TIFF accepted by Cell Press is `figures/graphical_abstract_300dpi.tif`, and the 16:9 `figures/graphical_abstract.png` is kept for slides only). Three bands: the failure mode and the split that hides it; the auditable loop, entered at the group level, with its two decision boundaries; and a third band that labels every claim in the paper by evidence level: validated end-to-end (one domain), audited on real data (two non-biological cohorts), or untested structural mapping (six further domains).

**Front-matter structure (checked against the Patterns article-type page).** Four items coexist deliberately and are not redundant. *Summary* (138 words, limit 150) is the author summary of what was done and found. *In brief* (49 words, limit 50) is the eTOC blurb, third person, aimed at a non-specialist. *Highlights* (5 bullets, each ≤85 characters, Cell Press maximum) are result fragments and are only requested at the final-files stage. *Bigger picture* (295 words, limit 300) is the box Patterns requires of all research articles; it is explicitly not a restatement of the summary and is written for a general scientific reader. All four are included here so the file is complete at first submission.

**Pre-submission checklist (must be cleared before upload).**
1. Reference 1 (companion study) and the Zenodo archive DOI are still placeholders, and both must be cleared before upload. The companion manuscript is complete and sits in the project tree at papers/19_ISCLS_20261016/Manuscript_ISCLS.md ("MRP-ST: calibrated label-dependence indexing and measured operating characteristics for auditing spatial transcriptomic models"); it needs to be posted to a preprint server and its DOI substituted for the placeholder in reference 1, in the Data availability statement, and in the cover letter. The Zenodo archive DOI is minted from the GitHub release. Both DOIs appear as the string TO BE INSERTED BEFORE SUBMISSION, which now occurs four times (reference 1, the Key Resources Table code row, Resource availability, and Data availability), so the same search finds every occurrence.
2. Main text is approximately 17,619 words (Introduction through Experimental Procedures; tables and figure legends excluded). Patterns applies no strict limit and states that a research article is *typically* 5,000–7,000 words but that longer articles may be considered where the length aligns with the science; there is also no strict limit on the number of figures, tables or references. The cover letter declares the count and offers to move the per-cohort dose–response tables and the cross-domain audit detail into the supplement at revision, which returns a main text of roughly 9,000–10,000 words with no result removed. Decide before upload whether to submit at this length with the declaration or to compress pre-emptively. (The figures of 6,000 words and 8 figures/tables are JBI limits and do not apply to Patterns.)
3. STAR Methods is complete as a framework: Resource availability is split into Lead contact, Materials availability and Data and code availability; a Key Resources Table (Table 6) lists every GEO accession, both UCI cohorts, the simulator and every package version actually run; “Quantification and statistical analysis” states what each n counts (groups versus units, simulation versus cohort), the two seed families, B = 2,000 with a B = 10,000 sensitivity check, the definition of the null scale, the source of the 1.645 gate, and that all dispersion is SD rather than SEM.
4. Graphical abstract: cleared. `figures/graphical_abstract_1200.png` is 1200 × 1200 px at exactly 300 dpi in Arial, rebuilt from `scripts/make_graphical_abstract_square.py`, which asserts that no label overflows its container. `figures/graphical_abstract_300dpi.tif` is the same artwork in the TIFF form Cell Press accepts.
5. Confirm every figure is supplied as vector PDF plus a high-resolution raster.
6. Clear the two DOIs with one command each: `python scripts/_fill_dois.py --companion <preprint DOI> --zenodo <Zenodo DOI> --build` rewrites all four placeholder strings and rebuilds the docx; `--check` lists what is still pending.
7. The GitHub repository named in the Key Resources Table, Resource availability and Data availability does not exist yet, and this working directory is not under version control. The release steps are in `SUBMISSION_READINESS.md` (section B2): initialise the repository with the data and cache directories excluded, tag v1.0.0, push, create the GitHub release, then enable Zenodo archiving for that tag. The tagged release must contain `REPRODUCE.md` and `requirements-patterns.txt`, which pin the environment that produced the reported numbers.

**Keywords:** identity leakage; group-structured data; model auditing; adversarial training; evaluation integrity; decision boundaries; reproducibility; spatial transcriptomics

**Declarations:** The authors declare no competing interests. Generative-AI use is declared in the manuscript (AI coding and writing assistants: Trae, Z.ai GLM; OpenAI Codex for editorial review; all content reviewed, verified, and edited by the authors, who take full responsibility).

**Author e-mails:** Mingwei Bai, baimingwei@jm360.cn; Zhengmin Gu, guzm@cmulh.com; Ye Zhang, 13332457636@163.com; Zhiping Ni, nizhiping@jm360.cn; Lang Guo, guolang1016@symc.edu.cn
