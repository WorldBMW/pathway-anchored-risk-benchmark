# -*- coding: utf-8 -*-
"""v19 -> v20: put the code release into the Key Resources Table.

The reviewer's desk-rejection checklist asks for the GitHub tag and the Zenodo
DOI inside the Key Resources Table. The table listed every package and script
path but no repository row, so a production editor checking code accessibility
would have to leave the table to find it. One row fixes that.

The Zenodo DOI travels as the same literal placeholder used elsewhere, so the
single --zenodo pass still fills every occurrence.
"""
from pathlib import Path

PAPERS = Path("papers/20_MRP-ST-Repair_Patterns")
SRC = PAPERS / "MRP-ST-Repair_manuscript_Patterns_v19.md"
DST = PAPERS / "MRP-ST-Repair_manuscript_Patterns_v20.md"

s = SRC.read_text(encoding="utf-8")
n0 = len(s)

ANCHOR = ("| Deposited data | Simulated cohorts (shared-program, identity-confounding, spurious, "
          "weak-signal arms) | this paper; released generator, fixed seeds | simulator in the tagged release |\n"
          "| Software | Python |")
assert s.count(ANCHOR) == 1, "KRT anchor"

ROW = ("| Deposited data | Simulated cohorts (shared-program, identity-confounding, spurious, "
       "weak-signal arms) | this paper; released generator, fixed seeds | simulator in the tagged release |\n"
       "| Software | Code repository: simulation, training, audit and figure scripts, configuration "
       "manifests and seeds | this paper | https://github.com/WorldBMW/cervix-st-multimodal (tag v1.0.0); "
       "Zenodo DOI: TO BE INSERTED BEFORE SUBMISSION |\n"
       "| Software | Python |")
s = s.replace(ANCHOR, ROW, 1)

DST.write_text(s, encoding="utf-8")
print("wrote", DST)
print("chars %d -> %d" % (n0, len(s)))
print("em-dash:", s.count("\u2014"))
print("placeholders:", s.count("TO BE INSERTED BEFORE SUBMISSION"))
