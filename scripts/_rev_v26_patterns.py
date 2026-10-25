"""v25 -> v26.

Bug found in v25: the renumber step used the regex r"\\[(\\d+)\\]", which matches
ONLY single-number citations. Every multi-number citation ([3,4], [8,40,41],
[27-29,36,37], ...) was therefore left at its old number after reference 1 was
deleted, so those citations now point at unrelated papers.

Fix: shift every number inside every bracketed citation down by one, preserving
the internal separators ("," and the en dash used for ranges), then renumber the
reference list the same way it was already done.

Only the citation tokens are touched; no prose changes.
"""
from __future__ import annotations

import re
from pathlib import Path

PAPERS = Path(__file__).resolve().parents[1] / "papers" / "20_MRP-ST-Repair_Patterns"
SRC = PAPERS / "MRP-ST-Repair_manuscript_Patterns_v25.md"
DST = PAPERS / "MRP-ST-Repair_manuscript_Patterns_v26.md"

# Any bracketed citation: [7], [3,4], [27-29], [27-29,36,37], [8,40,41]
CITE = re.compile(r"\[(\d+(?:\s*[,\u2013-]\s*\d+)+|\d+)\]")


def shift_token(inner: str) -> str:
    """'3,4' -> '2,3'; '27\u201329,36,37' -> '26\u201328,35,36'; '22' -> '21'."""
    def dec(m: re.Match) -> str:
        n = int(m.group(0))
        return str(n - 1) if n >= 2 else m.group(0)
    return re.sub(r"\d+", dec, inner)


def main() -> None:
    text = SRC.read_text(encoding="utf-8")
    head, sep, refblk = text.partition("## REFERENCES")
    assert sep, "no REFERENCES heading"

    before = sorted({m.group(1).replace(" ", "")
                     for m in CITE.finditer(head)
                     if re.search(r"[,\u2013-]", m.group(1))})
    n_before = sum(1 for m in CITE.finditer(head)
                   if re.search(r"[,\u2013-]", m.group(1)))

    # Only multi-number tokens are wrong: single-number ones were already shifted
    # correctly by v25, and the reference list is already numbered 1..43.
    def sub(m: re.Match) -> str:
        inner = m.group(1)
        if not re.search(r"[,\u2013-]", inner):
            return m.group(0)          # single number: already correct
        return "[" + shift_token(inner) + "]"

    head_new = CITE.sub(sub, head)
    refblk_new = refblk

    out = head_new + sep + refblk_new
    DST.write_text(out, encoding="utf-8")

    # ---- verification -------------------------------------------------
    cited = {int(x) for m in CITE.finditer(head_new)
             for x in re.findall(r"\d+", m.group(1))}
    nums = [int(m.group(1)) for m in re.finditer(r"^(\d+)\. ", refblk_new, re.M)]
    print("references:", len(nums), "| contiguous 1..N:", nums == list(range(1, len(nums) + 1)))
    print("max cited:", max(cited), "| min cited:", min(cited))
    print(f"multi-number citations fixed: {n_before} occurrence(s), "
          f"{len(before)} distinct token(s)")
    for b in before:
        print(f"    [{b}] -> [{shift_token(b)}]")
    if max(cited) > len(nums) or min(cited) < 1:
        raise SystemExit("citation out of range")
    after = [m.group(1).replace(" ", "") for m in CITE.finditer(head_new)
             if re.search(r"[,\u2013-]", m.group(1))]
    print("remaining multi tokens:", sorted(set(after)))
    print("\nwrote", DST.name)


if __name__ == "__main__":
    main()
