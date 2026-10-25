"""v17: fix the two defects found by an independent re-read of v16.

1. References 23 and 42 are the same paper (Kapoor & Narayanan, Patterns 4,
   100804 (2023)) listed twice. Merge: every in-text [42] becomes [23],
   entry 42 is dropped, and 43/44 shift down to 42/43.
2. One paragraph says "seven of seven cohorts" and then "across six cohorts
   and two domains" in the next sentence. GSE316098 makes it seven.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "papers/20_MRP-ST-Repair_Patterns/MRP-ST-Repair_manuscript_Patterns_v16.md"
OUT = ROOT / "papers/20_MRP-ST-Repair_Patterns/MRP-ST-Repair_manuscript_Patterns_v17.md"

import re

t = MD.read_text(encoding="utf-8")


def rep(old, new, n=1):
    global t
    assert t.count(old) == n, "anchor count %d (want %d): %s" % (t.count(old), n, old[:70])
    t = t.replace(old, new)


# ---------------------------------------------------------------- 1. numbering
# Old 42 (duplicate of 23) is removed; old 43 -> 42; old 44 -> 43.
MAP = {"42": "23", "43": "42", "44": "43"}

# guard: make sure no range/en-dash citation would be silently mangled
for m in re.finditer(r"\[([0-9–\-,\s]+)\]", t):
    inner = m.group(1)
    if "–" in inner or "-" in inner:
        nums = [x for x in re.split(r"[–\-,]", inner) if x.strip().isdigit()]
        clash = [x for x in nums if x in MAP]
        if clash:
            raise SystemExit("range citation needs manual handling: [%s]" % inner)


def shift(m):
    parts = re.split(r"(\d+)", m.group(1))
    return "[" + "".join(MAP.get(p, p) if p.isdigit() else p for p in parts) + "]"


before = len(re.findall(r"\[[0-9][0-9–\-,\s]*\]", t))
t = re.sub(r"\[([0-9][0-9–\-,\s]*)\]", shift, t)
print("citation blocks rewritten:", before)

# drop the duplicated entry
dup = (
    "42. Kapoor, S., and Narayanan, A. Leakage and the reproducibility crisis in "
    "machine-learning-based science. Patterns 4, 100804 (2023). "
    "https://doi.org/10.1016/j.patter.2023.100804.\n"
)
assert t.count(dup) == 1, "duplicate ref 42 entry not found verbatim"
t = t.replace(dup, "")

# renumber the two entries after it
rep(
    "43. Yagis, E., Atnafu, S.W.,",
    "42. Yagis, E., Atnafu, S.W.,",
)
rep(
    "44. [Dataset] Axelrod, M.L., Zhou, R., and Sun, L.",
    "43. [Dataset] Axelrod, M.L., Zhou, R., and Sun, L.",
)

# ---------------------------------------------------------------- 2. cohort count
rep(
    "A diagnostic whose verdicts agree with the outcomes it predicts, "
    "across six cohorts and two domains, is calibrated;",
    "A diagnostic whose verdicts agree with the outcomes it predicts, "
    "across seven cohorts and three domains, is calibrated;",
)

OUT.write_text(t, encoding="utf-8")
print("wrote", OUT.name)

# ---------------------------------------------------------------- verification
nums = [int(m.group(1)) for m in re.finditer(r"^(\d+)\. ", t[t.index("## REFERENCES"):], flags=re.M)]
print("ref entries:", len(nums), "max", max(nums), "contiguous:", nums == list(range(1, len(nums) + 1)))
body = t[: t.index("## REFERENCES")]
cited = set()
for m in re.finditer(r"\[([0-9][0-9–\-,\s]*)\]", body):
    for n in re.split(r"[–\-,]", m.group(1)):
        if n.strip().isdigit():
            cited.add(int(n))
print("cited but out of range:", sorted(n for n in cited if not 1 <= n <= 43))
print("never cited:", sorted(set(range(1, 44)) - cited))
print("duplicate ref 42 text left:", t.count("10.1016/j.patter.2023.100804"))
