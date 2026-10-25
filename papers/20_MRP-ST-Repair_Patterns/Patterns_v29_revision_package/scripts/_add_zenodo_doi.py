#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_add_zenodo_doi.py — 把新仓库的 Zenodo DOI 写回稿件与投稿信（md 侧）。

只改 md；docx 由随后的两步同步（见下），因为 Manuscript_Patterns.docx 内嵌
五幅图，必须就地 patch 而不能重建。

用法：
    python scripts/_add_zenodo_doi.py --doi 10.5281/zenodo.xxxxxxxx
    python scripts/_fill_doi_v28.py                       # 同步正文 docx 三处
    python scripts/_md2docx.py papers/20_MRP-ST-Repair_Patterns/CoverLetter_Patterns.md \
                               papers/20_MRP-ST-Repair_Patterns/CoverLetter_Patterns.docx
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "papers" / "20_MRP-ST-Repair_Patterns"
MANUSCRIPT = P / "MRP-ST-Repair_manuscript_Patterns_v28.md"
COVER = P / "CoverLetter_Patterns.md"

REPO = "https://github.com/WorldBMW/mrp-st-audit"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doi", required=True, help="e.g. 10.5281/zenodo.23640980")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    doi = args.doi.strip()
    if not re.fullmatch(r"10\.\d{4,9}/\S+", doi):
        raise SystemExit(f"not a DOI: {doi}")
    url = f"https://doi.org/{doi}"

    md = MANUSCRIPT.read_text(encoding="utf-8")
    if doi in md:
        raise SystemExit("DOI already present in the manuscript md; nothing to do")

    edits = [
        # Code paragraph
        (f"at {REPO}. Every number in this paper",
         f"at {REPO} and are archived in Zenodo at {url}. Every number in this paper"),
        # data and code availability
        (f"at {REPO}; the frozen state",
         f"at {REPO} and are archived in Zenodo at {url}; the frozen state"),
        # key resources table row
        (f"| {REPO} (tag v1.0.0) |",
         f"| {REPO} (tag v1.0.0); Zenodo archive {url} |"),
    ]
    cov = COVER.read_text(encoding="utf-8")
    cedit = (f"at {REPO}.", f"at {REPO} and is archived in Zenodo at {url}.")

    for old, new in edits:
        n = md.count(old)
        if n != 1:
            raise SystemExit(f"manuscript anchor matched {n} times: {old[:60]}")
        md = md.replace(old, new)
    n = cov.count(cedit[0])
    if n != 1:
        raise SystemExit(f"cover-letter anchor matched {n} times")
    cov = cov.replace(*cedit)

    if args.dry:
        print("would insert", doi, "at 3 manuscript sites and 1 cover-letter site")
        return

    MANUSCRIPT.write_text(md, encoding="utf-8")
    COVER.write_text(cov, encoding="utf-8")
    print(f"inserted {doi} -> manuscript x3, cover letter x1")
    print("next: python scripts/_fill_doi_v28.py")
    print("next: python scripts/_md2docx.py "
          "papers/20_MRP-ST-Repair_Patterns/CoverLetter_Patterns.md "
          "papers/20_MRP-ST-Repair_Patterns/CoverLetter_Patterns.docx")


if __name__ == "__main__":
    main()
