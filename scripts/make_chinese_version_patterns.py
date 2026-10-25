#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Render the Chinese manuscript of the Patterns package to .docx.

Uses Times New Roman for Latin glyphs and SimSun (宋体) for CJK glyphs so the
translated text renders correctly in Word.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from md_to_docx_patterns import convert  # noqa: E402

BASE = Path(__file__).resolve().parents[1] / "papers" / "20_MRP-ST-Repair_Patterns"


def main():
    convert(BASE / "MRP-ST-Repair_manuscript_Patterns_v1_zh.md",
            BASE / "Manuscript_Patterns_zh.docx",
            latin="Times New Roman", cjk="宋体")


if __name__ == "__main__":
    main()
