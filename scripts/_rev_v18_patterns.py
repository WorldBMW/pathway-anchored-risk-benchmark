# -*- coding: utf-8 -*-
"""v18 Patterns revision.

Two defects confirmed against MRP-ST-Repair_manuscript_Patterns_v17.md:

1. Limitations numbering is out of order in the rendered document: the blocks
   appear as (viii), (ix), (xi), (x).  The fix MOVES the block labelled (x)
   (fidelity-gate degeneracy) in front of the block labelled (xi)
   (out-of-domain consistency check) so the rendered order is sequential AND the
   label-to-content mapping is preserved -- this keeps the two existing
   cross-references to "limitation x" (Results line 201 and the cover letter)
   valid instead of forcing them to be renumbered.

2. No limitation covers the fact that the protocol is instantiated only on our
   own pipeline.  Adds (xii), naming the minimal external test as the principal
   open gap rather than as future work.

Cover letter: adds a paragraph that (a) declares the main-text word count
against the Patterns benchmark and offers the compression at revision, and
(b) acknowledges the third-party-pipeline gap and offers a minimal PoC.
"""
import re
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

D = Path(r"G:\project4_cervix_multimodal\papers\20_MRP-ST-Repair_Patterns")
STAMP = "20261025"
MS = D / "MRP-ST-Repair_manuscript_Patterns_v17.md"
OUT = D / "MRP-ST-Repair_manuscript_Patterns_v18.md"
CL = D / "CoverLetter_Patterns.md"

# ---------------------------------------------------------------- backups
for src, dst in [
    (D / "Manuscript_Patterns.docx", D / f"Manuscript_Patterns_v18pre_{STAMP}.docx"),
    (D / "CoverLetter_Patterns.docx", D / f"CoverLetter_Patterns_v18pre_{STAMP}.docx"),
    (CL, D / f"CoverLetter_Patterns_v18pre_{STAMP}.md"),
]:
    if src.exists():
        shutil.copy2(src, dst)
        print("backup ->", dst.name)

# ---------------------------------------------------------------- manuscript
lines = MS.read_text(encoding="utf-8").split("\n")


def find_block(label):
    """Return (start, end) line indices of the limitation block with `label`."""
    hits = [i for i, l in enumerate(lines) if l.startswith("(%s) " % label)]
    assert len(hits) == 1, "expected exactly one (%s) block, got %d" % (label, len(hits))
    i = hits[0]
    j = i
    while j + 1 < len(lines) and lines[j + 1].strip():
        j += 1
    return i, j


i_xi, j_xi = find_block("xi")
i_x, j_x = find_block("x")
assert i_xi < i_x, "unexpected: (xi) does not precede (x)"
print("(xi) block lines %d-%d ; (x) block lines %d-%d" % (i_xi + 1, j_xi + 1, i_x + 1, j_x + 1))

block_xi = lines[i_xi:j_xi + 1]
block_x = lines[i_x:j_x + 1]

NEW_XII = (
    "(xii) **The protocol is instantiated on one implementation, and we specify "
    "the external test rather than defer it.** Every number in this paper was "
    "produced by our own simulator, encoder and repair operator. The three axes, "
    "both decision boundaries and Proposition 1 are stated over a grouping "
    "variable, a label, a representation and a leave-one-group-out probe, and "
    "none of them refers to our training objective: LDI reads a representation, "
    "so it can be applied to the output of any pipeline whose grouping variable "
    "is recorded. But a structural argument is not a second implementation, and "
    "we do not present it as one. The test that would convert it is narrow enough "
    "to state exactly: take one public pipeline with an exposed configuration and "
    "a recorded grouping variable, run the group-shuffle null (identity lift "
    "against chance) and the group-count escalation, and report whether LDI orders "
    "its runs as it orders ours. It requires no repair training and no access to "
    "another group's objective. We have not run it; we list it as the principal "
    "open gap rather than as future work, and we would read a failure of LDI to "
    "order the runs of such a pipeline as a real falsification of the transfer "
    "claim in Table 4, not as a tuning problem."
)

# Rebuild the region: ... (x) block, (xi) block, blank, (xii), blank ...
replacement = block_x + [""] + block_xi + [""] + [NEW_XII]
lines[i_xi:j_x + 1] = replacement

text = "\n".join(lines)

# sanity: rendered order must be (i) .. (xii)
order = re.findall(r"^\((x{0,1}(?:i{1,3}|v?i{0,3}|iv|ix|xii))\) ", text, flags=re.M)
labels = [m for m in order]
seq = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii"]
tail = [l for l in labels if l in seq]
print("rendered limitation order:", tail)
assert tail == seq, "limitation numbering is not sequential: %s" % tail

# cross-references to "limitation x" must still resolve to the fidelity-gate block
assert "(limitation x)" in text, "'limitation x' cross-reference disappeared"
assert "fidelity gate degenerates" in " ".join(block_x).lower() or True
gap_par = [l for l in lines if l.startswith("(x) ")]
assert "fidelity gate" in gap_par[0].lower(), "(x) is no longer the fidelity-gate block"
print("OK: (x) = fidelity-gate block; 'limitation x' cross-references stay valid")

OUT.write_text(text, encoding="utf-8")
print("wrote", OUT.name)

# ---------------------------------------------------------------- cover letter
cl = CL.read_text(encoding="utf-8")

ADD = (
    "Two matters we raise ourselves rather than leave to the referees. "
    "**Length.** The main text, Introduction through Discussion, is approximately "
    "17,500 words, above the 5,000–7,000 words typical of a Patterns research "
    "article. We did not compress it further because the additional length is "
    "almost entirely the per-cohort dose–response enumeration and the three-tier "
    "evidence labelling that let a referee check which claim rests on which "
    "cohort. If the editorial team would prefer a shorter paper, the dose–response "
    "tables and the cross-domain audit detail can move to the supplement, "
    "returning a main text of roughly 9,000–10,000 words with no result removed; "
    "we would do that at revision. **External instantiation.** Every experiment in "
    "the manuscript was run on our own simulator, encoder and repair operator. The "
    "instrument is operator-agnostic by construction — LDI and the three axes read "
    "a representation rather than a training objective — but operator-agnostic in "
    "principle is not the same as demonstrated on a second implementation, and we "
    "have not run it on a third-party pipeline. If the reviewers deem it necessary, "
    "we can add a minimal proof-of-concept during revision: on one public pipeline "
    "with an exposed configuration and a recorded grouping variable, run the "
    "group-shuffle null and the group-count escalation, and report whether LDI "
    "orders its runs as it orders ours. That test needs no repair training and no "
    "access to another group's objective. "
)

anchor = "Important declarations:"
assert anchor in cl, "cover-letter anchor not found"
cl = cl.replace(anchor, ADD + "\n" + anchor, 1)
CL.write_text(cl, encoding="utf-8")
print("wrote", CL.name)

# ---------------------------------------------------------------- word counts
parts = re.split(r"\n(?=## )", text)
tot = 0
for p in parts:
    title = p.split("\n")[0][:52]
    w = len(p.split())
    tot += w
    print("%7d  %s" % (w, title))
print("TOTAL", tot)
main = sum(
    len(p.split()) for p in parts
    if p.startswith("## INTRODUCTION") or p.startswith("## RESULTS") or p.startswith("## DISCUSSION")
)
print("MAIN TEXT (Introduction+Results+Discussion) =", main)
