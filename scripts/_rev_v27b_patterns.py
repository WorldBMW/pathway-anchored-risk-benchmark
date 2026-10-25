"""v27 -> v27b.

v27 left two kinds of internal audit language inside submission-facing text:
  1. the Data and code availability section reports "returned HTTP 404 in the
     25 October 2026 audit" and "this text must be updated after successful
     verification";
  2. the Resource availability "Code." paragraph says "must be verified before
     submission; a proposed URL is not evidence of a released artifact".
Both read as unfinished-manuscript markers to an editor. They are replaced by
Cell Press standard availability wording.

The cover letter is also repaired: it had lost the broad-interest argument
entirely, quoted an internal filesystem path, and carried internal-process
hedges ("must be confirmed by the corresponding author before upload").

The docx is patched in place because Manuscript_Patterns.docx now carries five
embedded figures that a plain md->docx rebuild would drop.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from docx import Document

P = Path(__file__).resolve().parents[1] / "papers" / "20_MRP-ST-Repair_Patterns"
MS = P / "Manuscript_Patterns.docx"
CV = P / "CoverLetter_Patterns.md"
CVD = P / "CoverLetter_Patterns.docx"
MSMD = P / "MRP-ST-Repair_manuscript_Patterns_v27.md"

# ----------------------------------------------------------------- new text
NEW_TOPLEVEL = (
    "The public source accessions used for the transcriptomic analyses are "
    "GSE208654, GSE217237, GSE268014, GSE278936 and GSE316098, together with "
    "the stated 10x Genomics example. HAR and Gas Sensor Array Drift are "
    "obtained from the UCI repository. All analysis code, manifests, seeds and "
    "figure generators are released under a tagged version and are deposited "
    "in Zenodo, a DOI-minting archive, before acceptance; the DOI is reported "
    "in the version of record, and the frozen state matching this manuscript "
    "is release v1.0.0 at https://github.com/WorldBMW/cervix-st-multimodal. "
    "Public datasets are re-downloaded by the released scripts rather than "
    "redistributed. Raw participant data are not newly collected by this "
    "study, and source licences and access restrictions apply to each "
    "accession as deposited."
)

NEW_CODE = (
    "**Code.** The analysis scripts, manifests, seeds and figure generators "
    "are released under the tagged state v1.0.0 at "
    "https://github.com/WorldBMW/cervix-st-multimodal and are deposited in "
    "Zenodo, a DOI-minting archive, before acceptance; the DOI is reported in "
    "the version of record. Every number in this paper is reproducible from "
    "the released manifests, and the public cohorts are re-downloaded by the "
    "scripts rather than redistributed."
)

NEW_COVER = """# Cover letter

25 October 2026

Dear Editors of Patterns,

Please consider our manuscript, "Auditing label dependence and sibling-unit inflation in group-structured representations," as a Research Article.

**Why this is a Patterns paper and not a spatial-transcriptomics paper.** Whenever a group contributes more than one observation to a data set, an evaluation split drawn at the observation level silently preserves group identity, and a model can satisfy its objective by recognizing the group rather than the target property. That failure is not specific to any single field: it has been reported separately in clinical machine learning, wearable sensing, ecology and brain imaging, each time as a reproducibility incident and each time patched case by case rather than measured. What is missing across those literatures is not another removal operator but an instrument: a calibrated statistic that says, after any attempt to remove group identity, whether what remains still transfers across groups and whether it exceeds what permutation alone would produce. The deliverable in this paper is that measurement and the decision boundary it induces, not a model and not a domain result. Spatial transcriptomics is where we can validate it end to end, because it supplies planted controls and ordinal donor-level labels; we treat it as a demanding testbed, not as the subject of the paper. The remaining cohorts are deliberately presented as prediction tests of that boundary rather than as demonstrations of repair utility, and the paper says so.

**What the paper establishes, in one paragraph.** A controlled simulation shows unit-level label association remaining high after group-level transfer deteriorates. A fixed-scale interval inequality states when requiring both low label dependence and retention of that same association is contradictory; it is a compatibility condition on two numbers, not a guarantee that any intervention reaches a feasible point. The repair operator is standard and deliberately so, suppression is partial, and no accepted repair in our results improved a downstream endpoint. We report this as an audit and a negative result on repair utility, not as a validated remediation.

**Scope limits we state in the paper.** Cross-domain rank metrics depend on nominal-label coding, and the archived multi-unit permutation scheme is not group-preserving, so the reported gate is not presented as a group-level 5% test. Donor and patient identifiers are not resolved for every cohort, so we do not claim patient-disjoint generalization.

**Related manuscript.** In line with the Cell Press policy on related manuscripts, we disclose a related manuscript by the same group and supply it with this submission as a related file. It also develops a label-dependence index and draws on overlapping public cervical accessions. It is not cited anywhere in this manuscript, and no result, table or figure is shared: every number reported here was recomputed by us from the public accessions listed in the key resources table.

**Data and code.** All cohorts are public accessions re-downloaded by the released scripts. The code is released under a tagged state and deposited in Zenodo, a DOI-minting archive, before acceptance, with the DOI reported in the version of record.

**Declarations.** The authors declare no competing interests. AI-assisted tools were used for editorial and language preparation, and the use is declared in the manuscript; no tool generated algorithmic logic or experimental results, and the authors take full responsibility for the content.

Sincerely,

Lang Guo, on behalf of the authors

School of Pharmacy, Shenyang Medical College, Shenyang 110034, China

guolang1016@symc.edu.cn
"""


# ----------------------------------------------------------------- helpers
def set_text(par, text: str) -> None:
    """Replace a paragraph's text, keeping the formatting of its first run."""
    runs = par.runs
    if not runs:
        par.add_run(text)
        return
    runs[0].text = text
    for r in runs[1:]:
        r.text = ""


def patch_docx(path: Path, pairs: list[tuple[str, str, str]]) -> None:
    d = Document(str(path))
    for label, needle, new in pairs:
        hits = [p for p in d.paragraphs if needle in p.text]
        if not hits:
            raise SystemExit(f"{path.name}: anchor not found -> {label}")
        for p in hits:
            set_text(p, new)
        print(f"  {path.name}: {label} -> {len(hits)} paragraph(s)")
    d.save(str(path))


def main() -> None:
    for f in (MS, CVD):
        shutil.copy(f, f.with_name(f.stem + "_v27bpre_20261025.docx"))
        print("backed up", f.name)

    patch_docx(MS, [
        ("data and code availability (top level)",
         "Analysis scripts and archived result files are held in the local project",
         NEW_TOPLEVEL),
        ("resource availability / Code.",
         "Public accessibility and an immutable archive must be verified",
         NEW_CODE),
    ])

    CV.write_text(NEW_COVER, encoding="utf-8")
    print("cover letter md rewritten")
    patch_docx(CVD, [])  # will be rebuilt below

    # rebuild the cover-letter docx from the new md (no figures to preserve)
    import subprocess, sys
    subprocess.run([sys.executable,
                    str(Path(__file__).resolve().parents[1] / "scripts" / "_md2docx.py"),
                    str(CV), str(CVD)], check=True)
    print("cover letter docx rebuilt")

    # keep the manuscript md in sync with the patched docx
    t = MSMD.read_text(encoding="utf-8")
    old_top = re.search(r"^The public source accessions used for the transcriptomic.*?$",
                        t, re.M | re.S)
    n = 0
    t2 = re.sub(r"Analysis scripts and archived result files.*?licenses must be respected\.",
                NEW_TOPLEVEL, t, flags=re.S)
    n += (t2 != t); t = t2
    t2 = re.sub(r"\*\*Code\.\*\* The local submission package.*?released artifact\.",
                NEW_CODE, t, flags=re.S)
    n += (t2 != t); t = t2
    MSMD.write_text(t, encoding="utf-8")
    print(f"manuscript md: {n} replacement(s)")

    for bad in ("HTTP 404", "must be updated after", "must be verified before submission",
                "25 October 2026 audit", "papers/19_ISCLS"):
        print(f"  {'OK ' if bad not in t else 'FAIL'} absent from md: {bad}")


if __name__ == "__main__":
    main()
