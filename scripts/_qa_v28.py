#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_qa_v28.py — v28 稿件 QA（v26 的继承版，随 v27/v28 重写更新锚点）。

相对 _qa_v26.py 的变化：
  1. 主表 6 -> 7（v28 新增 Table 7：单位级零分布 vs 组保持零分布）。
  2. v27 重写后已不存在的旧锚点移入 RETIRED：只打印、不计失败（它们被 v27 的
     Discussion/Results 重写取代，逐条核对过语义仍由现文覆盖）。
  3. 两处因 v28 改写而换措辞的锚点更新为 v28 原文。
  4. 新增 v28 检查项：新增小节与表、补充表引用、组保持零分布措辞、ASCII 统计量
     漏网（正文必须用 σ̂ / τ_LOO / κ / Δ / λ）、内部核查语。
"""
import re
from pathlib import Path

from docx import Document

D = Path(__file__).resolve().parent.parent / "papers" / "20_MRP-ST-Repair_Patterns"
d = Document(D / "Manuscript_Patterns.docx")
ps = [p.text for p in d.paragraphs]
full = "\n".join(ps)
for t in d.tables:
    for r in t.rows:
        full += "\n" + " | ".join(c.text for c in r.cells)

WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'+/-]*")
fails = []

n_tbl = len(d.tables)
print("em-dash", full.count("\u2014"), "| literal **", full.count("**"),
      "| main tables", n_tbl)
if full.count("\u2014") or full.count("**"):
    fails.append("forbidden character present")
if n_tbl != 7:
    fails.append(f"main table count {n_tbl} != 7")

print("words(all):", len(WORD.findall(full)))
ii = [i for i, x in enumerate(ps) if x.strip().upper() == "INTRODUCTION"][0]
jj = [i for i, x in enumerate(ps)
      if x.strip().upper().startswith("EXPERIMENTAL PROCEDURES")][0]
body = "\n".join(ps[ii:jj])
print("main text words (Introduction -> Experimental Procedures):",
      len(WORD.findall(body)))

# ---- Highlights: Cell Press 最多 4 条，每条 <= 85 字符
hl = [x.strip() for x in ps[ps.index("HIGHLIGHTS") + 1:ps.index("IN BRIEF")]
      if x.strip()]
print(f"highlights: {len(hl)} (Cell Press 上限 4)")
for h in hl:
    flag = "OK " if len(h) <= 85 else "FAIL"
    if len(h) > 85:
        fails.append(f"highlight too long ({len(h)}): {h}")
    print(f"  {flag} {len(h):3d}  {h}")
if not 3 <= len(hl) <= 4:
    fails.append(f"highlight count {len(hl)} outside 3-4 (Cell Press max 4)")

# ---- In brief <= 50 words, Summary <= 150 words
ib = "\n".join(ps[ps.index("IN BRIEF") + 1:ps.index("SUMMARY")]).strip()
sm = "\n".join(x for x in ps[ps.index("SUMMARY") + 1:ps.index("GRAPHICAL ABSTRACT")]
               if not x.strip().startswith("Keywords:")).strip()
print("in brief words:", len(ib.split()), "| summary words:", len(sm.split()))
if len(ib.split()) > 50:
    fails.append(f"in brief {len(ib.split())} > 50")
if len(sm.split()) > 150:
    fails.append(f"summary {len(sm.split())} > 150")

checks = [
    # ---- 保留：v26 中当前仍然存在的锚点
    "Table S17", "Table S16", "42. [Dataset] Axelrod", "GSE316098",
    "Not tested",
    "The deliverable of this paper is the auditing protocol, not the repair operator",
    "Do not read acceptance as erasure",
    "Degenerate regime, to be read before any accept verdict is used",
    "placements for this configuration, not transferable cut-offs",
    "Lead contact. Requests for further information, resources, or code",
    "Materials availability. This study did not generate new unique reagents",
    "Quantification and statistical analysis",
    "Key resources table",
    "What each n counts",
    "B = 10,000",
    "standard errors of the mean",
    "we report no dose optimum",
    "requirements-patterns.txt",
    "it does not mean group identity is fully unrecoverable",
    # v25: ref [1] 已删除，宫颈队列改为自包含重述
    "The cervical cohort is 35 Visium sections from 34 donors",
    "GSE208654[43]",
    "download_and_prepare_cervix.py",
    "46,820 spots",
    # ---- v28 改写后的锚点（语义不变，措辞更新）
    "a nonlinear probe can still decode structure",
    "high-stakes deployments require re-auditing with a more expressive probe",
    # ---- v28 新增内容
    "Remediation experiments",
    "Table 7",
    "Tables S18 and S19",
    "group-preserving permutation scheme",
    "35 sections over 34 donors",
    "21 pairings",
    "outer-loop refit",
    "nearest-neighbour same-group hit rate",
    "no group-conditional LDI is defined",
]

# v27 重写后被取代、v28 中不再逐字存在的旧锚点：只提示，不计失败
RETIRED = [
    "Control: the channel is opened by coupling",
    "Validation is end-to-end in spatial transcriptomics alone",
    "no accepted repair improved a downstream endpoint, which the framework predicts in advance",
    "structural mappings only, for which we claim no transfer",
    "We therefore make no claim that the adversarial operator used here outperforms",
    "Standing qualifier for this section",
    "audited for theoretical predictions only",
    "Re-audit with a more expressive probe wherever the deployment is high-stakes",
    "Do not trust an accept output obtained while the baseline association is near null",
    "future extension rather than a requirement for the present manuscript",
    "it is not a detector of every form in which group identity can be encoded",
    "we report no optimal",
    "the prostate acceptance is a single operating point",
    "releases/tag/v1.0.0",
    "nonlinear probe can decode",
]

# ---- 多号引用清单（v25 事故的防回归：语义无法自动判定，逐条人工核对）
MULTI = re.compile(r"\[(\d+(?:\s*[,\u2013-]\s*\d+)+)\]")
_first = {}
for _l in full.split("\n"):
    _m = re.match(r"^(\d+)\. ", _l)
    if _m:
        _first[int(_m.group(1))] = _l[:44]
_mseen = {}
for _m in MULTI.finditer(full):
    _tok = _m.group(1).replace(" ", "")
    _mseen.setdefault(_tok, [int(x) for x in re.findall(r"\d+", _tok)])
print("多号引用（重编号事故高发区，逐条人工核对）：")
for _tok, _nums in sorted(_mseen.items()):
    _names = " ; ".join(_first.get(n, "?") for n in _nums)
    print(f"  [{_tok}]  {_names}")
for _tok, _nums in _mseen.items():
    if any(n < 1 or n > len(_first) for n in _nums):
        fails.append("multi-citation out of range: [%s]" % _tok)

print("禁用措辞：")
for bad in ["related submission", "Interim access:", "companion study",
            "companion manuscript", "in preparation", "reference [1]",
            "TO BE INSERTED BEFORE SUBMISSION",
            # 内部核查语不能进提交物
            "returned HTTP 404", "must be verified", "must be updated after",
            "must be confirmed by the corresponding author"]:
    n = full.count(bad)
    print(f"  {'OK ' if n == 0 else 'FAIL'} {n}  absent: {bad[:60]}")
    if n:
        fails.append(f"forbidden phrase present: {bad}")

print("ASCII 统计量漏网（正文必须用 σ̂ / τ_LOO / κ / Δ / λ）：")
for pat in ["sigma_", "tau_", "kappa", "Delta =", "lambda ="]:
    # "Delta =" 与 "lambda =" 只在 Unicode 版不存在时才算漏网
    n = len(re.findall(pat, full))
    print(f"  {'OK ' if n == 0 else 'FAIL'} {n}  {pat}")
    if n:
        fails.append(f"ASCII statistic name present: {pat} ({n})")

print("必需锚点：")
for c in checks:
    n = full.count(c)
    print(f"  {'OK ' if n >= 1 else 'MISS'} {n}  {c[:70]}")
    if n < 1:
        fails.append(f"missing: {c[:60]}")

print("已退役锚点（v27/v28 重写后不再逐字存在，仅提示）：")
for c in RETIRED:
    print(f"  {'present' if full.count(c) else 'retired':8s} {c[:70]}")

# ---- 参考文献与补充材料
print("ref count:", len(_first))
si = Document(D / "Supplemental_Information_Patterns.docx")
print("SI tables:", len(si.tables))
si_txt = "\n".join(p.text for p in si.paragraphs)
for t in ("Table S18", "Table S19"):
    ok = t in si_txt
    print(f"  {'OK ' if ok else 'MISS'}  SI contains {t}")
    if not ok:
        fails.append(f"SI missing {t}")

print()
if fails:
    print(f"RESULT: {len(fails)} FAILURES")
    for f in fails:
        print("  -", f)
else:
    print("RESULT: ALL CHECKS PASSED")
