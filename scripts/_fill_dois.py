"""Fill the two externally minted DOIs, then rebuild the docx files.

v23 removed the literal string "TO BE INSERTED BEFORE SUBMISSION" from the
manuscript: an editor reading a template leftover has every reason to conclude
the submission is not ready, and the honest Cell Press timing is that a
DOI-minting archive is required *before publication*, with the tagged release
as the frozen, citable state in the meantime. So the manuscript now carries
status text rather than a placeholder, and this script rewrites that status
text into a real DOI.

  * companion study -- reference 1, currently "Companion manuscript (related
    submission)", plus the matching sentence in the cover letter;
  * this paper's own code archive -- one sentence in Resource availability, one
    in Data and code availability, and one cell of the Key Resources Table.

Usage
-----
    # see what still needs a DOI
    python scripts/_fill_dois.py --check

    # fill the companion preprint DOI only
    python scripts/_fill_dois.py --companion 10.1101/2026.10.24.123456

    # fill both and rebuild the docx files
    python scripts/_fill_dois.py \
        --companion 10.1101/2026.10.24.123456 \
        --zenodo 10.5281/zenodo.1234567 \
        --build

Nothing is written unless --build (or --write) is passed, so an accidental run
with a typo in the DOI cannot silently corrupt the manuscript.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPERS = ROOT / "papers" / "20_MRP-ST-Repair_Patterns"


def latest_manuscript() -> Path:
    """Highest-numbered manuscript version present.

    Hard-coding the version here silently rebuilt the docx from a stale md and
    would have reverted later revisions, so the path is resolved instead.
    """
    cands = []
    for p in PAPERS.glob("MRP-ST-Repair_manuscript_Patterns_v*.md"):
        m = re.fullmatch(r"MRP-ST-Repair_manuscript_Patterns_v(\d+)\.md", p.name)
        if m:
            cands.append((int(m.group(1)), p))
    if not cands:
        raise SystemExit("no versioned manuscript found in " + str(PAPERS))
    return max(cands)[1]


MANUSCRIPT = latest_manuscript()
COVER = PAPERS / "CoverLetter_Patterns.md"
PYTHON = r"C:/Users/jm/anaconda3/python.exe"

# (label, regex with one capture group, replacement built from the group + DOI)
ZENODO_PATTERNS = [
    ("Resource availability / Data availability",
     re.compile(r"(deposited in Zenodo) before publication, whose DOI is "
                r"reported in the version of record"),
     lambda g, doi: g + " under DOI " + doi),
    ("Key resources table",
     re.compile(r"(Zenodo archive of the same state), DOI reported in the "
                r"version of record"),
     lambda g, doi: g + ": https://doi.org/" + doi),
]
COMPANION_PATTERN = (
    "reference 1",
    re.compile(r"Manuscript in preparation, declared as a related manuscript in "
               r"the cover letter and supplied with this submission as a related "
               r"file;"),
    lambda g, doi: "Preprint, https://doi.org/" + doi + ";",
)
COVER_PATTERN = (
    "cover letter",
    re.compile(r"No DOI is recorded for it yet"),
    lambda g, doi: "Its preprint DOI is " + doi,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="only report what is pending")
    ap.add_argument("--companion", help="preprint DOI of the companion study")
    ap.add_argument("--zenodo", help="Zenodo DOI of the tagged code release")
    ap.add_argument("--write", action="store_true", help="apply the edits")
    ap.add_argument("--build", action="store_true", help="rebuild the docx files")
    args = ap.parse_args()

    ms = MANUSCRIPT.read_text(encoding="utf-8")
    cov = COVER.read_text(encoding="utf-8")

    print(f"manuscript: {MANUSCRIPT.name}")
    pending = 0
    for label, pat, _ in ZENODO_PATTERNS:
        n = len(pat.findall(ms))
        pending += n
        print(f"  {label:<42} {n} Zenodo anchor(s)")
    n = len(COMPANION_PATTERN[1].findall(ms))
    pending += n
    print(f"  {COMPANION_PATTERN[0]:<42} {n} companion anchor(s)")
    print(f"  {'cover letter':<42} "
          f"{len(COVER_PATTERN[1].findall(cov))} companion anchor(s)")

    if args.check or not (args.companion or args.zenodo):
        print("\n  (no placeholder string remains; these are the fill points)")
        return 0

    new = ms
    if args.zenodo:
        doi = args.zenodo.strip()
        assert doi.startswith("10."), "a DOI starts with 10."
        print(f"\nZenodo DOI {doi}")
        for label, pat, repl in ZENODO_PATTERNS:
            new, k = pat.subn(lambda m: repl(m.group(1), doi), new)
            print(f"  {label}: {k} replacement(s)")
    if args.companion:
        doi = args.companion.strip()
        assert doi.startswith("10."), "a DOI starts with 10."
        print(f"\ncompanion DOI {doi}")
        _, pat, repl = COMPANION_PATTERN
        new, k = pat.subn(lambda m: repl(m.group(1), doi), new)
        print(f"  reference 1: {k} replacement(s)")

    new_cov = cov
    if args.companion:
        _, pat, repl = COVER_PATTERN
        new_cov = pat.sub(lambda m: repl(m.group(0), args.companion.strip()), cov)

    if not (args.write or args.build):
        print("\ndry run: pass --write or --build to apply")
        return 0

    MANUSCRIPT.write_text(new, encoding="utf-8")
    print(f"updated {MANUSCRIPT.name}")
    if new_cov != cov:
        COVER.write_text(new_cov, encoding="utf-8")
        print(f"updated {COVER.name}")

    if args.build:
        md2docx = ROOT / "scripts" / "_md2docx.py"
        for src, dst in [(MANUSCRIPT, PAPERS / "Manuscript_Patterns.docx"),
                         (COVER, PAPERS / "CoverLetter_Patterns.docx")]:
            subprocess.run([PYTHON, str(md2docx), str(src), str(dst)], check=True)
        print("rebuilt Manuscript_Patterns.docx and CoverLetter_Patterns.docx")
        print("now re-run: python scripts/_qa_v23.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
