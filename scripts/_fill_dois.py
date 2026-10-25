"""Fill the two submission blockers that need an externally minted DOI.

The manuscript carries two placeholder strings while the DOIs do not yet exist:

  * the companion study (reference 1, plus the note in the Data availability
    statement) -- a preprint DOI minted by bioRxiv/medRxiv at posting time;
  * this paper's own code archive -- a Zenodo DOI minted from the tagged
    GitHub release.

Both are written as the literal string "TO BE INSERTED BEFORE SUBMISSION" so
they cannot be missed during proofing. This script replaces them and rebuilds
the docx, so that the swap is one command per DOI instead of a manual hunt
through five files.

Usage
-----
    # see what is still a placeholder and where
    python scripts/_fill_dois.py --check

    # fill the companion preprint DOI only
    python scripts/_fill_dois.py --companion 10.1101/2026.10.24.123456

    # fill both, and rebuild the docx files afterwards
    python scripts/_fill_dois.py \
        --companion 10.1101/2026.10.24.123456 \
        --zenodo 10.5281/zenodo.1234567 \
        --build

Nothing is written unless --build (or --write) is passed, so an accidental run
with a typo in the DOI cannot silently corrupt the manuscript. The script
prints every replacement it would make, then applies them.
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

PLACEHOLDER = "TO BE INSERTED BEFORE SUBMISSION"
PYTHON = r"C:/Users/jm/anaconda3/python.exe"

# Anchors are matched as regexes so a rewrap of the markdown cannot break them.
ZENODO_PATTERNS = [
    re.compile(r"(archived at Zenodo \(DOI:\s*)" + PLACEHOLDER),
    # Key Resources Table row, added in v20
    re.compile(r"(Zenodo DOI:\s*)" + PLACEHOLDER),
]
COVER_PATTERN = re.compile(
    r"its DOI will be inserted in place of the current placeholder, with the "
    r"GitHub repository serving as interim access"
)


def report(text: str, label: str) -> int:
    n = text.count(PLACEHOLDER)
    print(f"  {label:<34} {n} placeholder(s)")
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="only report placeholders")
    ap.add_argument("--companion", help="preprint DOI of the companion study")
    ap.add_argument("--zenodo", help="Zenodo DOI of the tagged code release")
    ap.add_argument("--write", action="store_true", help="apply the edits")
    ap.add_argument("--build", action="store_true", help="rebuild the docx files")
    args = ap.parse_args()

    ms = MANUSCRIPT.read_text(encoding="utf-8")
    cov = COVER.read_text(encoding="utf-8")

    print(f"manuscript: {MANUSCRIPT.name}")
    total = report(ms, "total")
    report(cov, "cover letter")

    if args.check or not (args.companion or args.zenodo):
        if total:
            for m in re.finditer(r"^.*" + PLACEHOLDER + r".*$", ms, flags=re.M):
                line = m.group(0)
                print("\n  ... " + (line[:150] + "..." if len(line) > 150 else line))
        else:
            print("  no placeholders left")
        return 0

    new = ms
    if args.companion:
        doi = args.companion.strip()
        assert doi.startswith("10."), "a DOI starts with 10."
        # reference 1
        new, n1 = re.subn(r"(Companion study\.\s*Preprint DOI:\s*)" + PLACEHOLDER,
                          lambda m: m.group(1) + doi, new)
        print(f"\ncompanion DOI {doi}")
        print(f"  reference 1: {n1} replacement(s)")
    if args.zenodo:
        doi = args.zenodo.strip()
        assert doi.startswith("10."), "a DOI starts with 10."
        n2 = 0
        for pat in ZENODO_PATTERNS:
            new, k = pat.subn(lambda m: m.group(1) + doi, new)
            n2 += k
        print(f"\nZenodo DOI {doi}")
        print(f"  Zenodo placeholder: {n2} replacement(s)")

    left = new.count(PLACEHOLDER)
    print(f"\nplaceholders remaining: {left}")
    if left:
        print("  (the other DOI is still pending; that string stays visible on purpose)")

    new_cov = cov
    if args.companion:
        new_cov = COVER_PATTERN.sub(
            f"its DOI is {args.companion.strip()} and the GitHub repository is "
            f"the archived source of the reported numbers", new_cov)

    if not (args.write or args.build):
        print("\ndry run: pass --write or --build to apply")
        return 0

    MANUSCRIPT.write_text(new, encoding="utf-8")
    if new_cov != cov:
        COVER.write_text(new_cov, encoding="utf-8")
        print(f"updated {COVER.name}")
    print(f"updated {MANUSCRIPT.name}")

    if args.build:
        md2docx = ROOT / "scripts" / "_md2docx.py"
        for src, dst in [(MANUSCRIPT, PAPERS / "Manuscript_Patterns.docx"),
                         (COVER, PAPERS / "CoverLetter_Patterns.docx")]:
            subprocess.run([PYTHON, str(md2docx), str(src), str(dst)], check=True)
        print("rebuilt Manuscript_Patterns.docx and CoverLetter_Patterns.docx")
        print("now re-run: python scripts/_qa_v15.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
