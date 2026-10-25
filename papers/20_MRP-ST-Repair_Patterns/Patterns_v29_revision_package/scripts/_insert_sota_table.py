"""Insert SOTA head-to-head comparison (Table 3) into the three MRP-ST-Repair
manuscripts (Patterns / JBI / CBM), right after the "downstream clinical
endpoint" Results subsection and before DISCUSSION.

Reads results/expA_sota_summary.json for the numbers.  Idempotent: if the
"Head-to-head" heading already exists, the section is replaced.
"""
from __future__ import annotations
import json
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt

ROOT = Path(r"g:\project4_cervix_multimodal")
DOCS = [
    ROOT / "papers" / "20_MRP-ST-Repair_Patterns" / "Manuscript_Patterns.docx",
    ROOT / "papers" / "21_MRP-ST-Repair_JBI" / "Manuscript_JBI.docx",
    ROOT / "papers" / "22_MRP-ST-Repair_CBM" / "Manuscript_CBM.docx",
]
SUMMARY = ROOT / "results" / "expA_sota_summary.json"

ANCHOR = "Repair preserves signal share but does not improve a downstream clinical endpoint"
NEW_HEADING = "Head-to-head comparison with existing deconfounding methods"

INTRO = (
    "To establish that the repair operator is not a repackaging of an existing "
    "deconfounding technique, we compared MRP-ST-Repair against three widely used "
    "methods on two scale-matched simulation cohorts that differ only in the "
    "nature of the between-slide signal. Cohort A carries a strong shared "
    "disease program (the safety arm: repair must not kill a real, transferable "
    "signal); cohort C carries only an identity-fingerprint confound with no "
    "transferable class signal (the leakage arm). All methods were run on the "
    "same n\u00d7\u03bb\u00d7k grid with three seeds; the LDI gate is 1.645. "
    "MRP-ST-Repair is the only method that simultaneously keeps \u03c4_lodo at "
    "the ceiling in cohort A (R = 1.00, signal fully preserved) and drives LDI "
    "below zero in cohort C (leakage eliminated). Group-DRO leaves the leakage "
    "signal positive (LDI > 0); IRM preserves the identity fingerprint as if it "
    "were an invariant feature (LDI rises to +3.2)."
)

CAPTION = (
    "Table 3. Head-to-head comparison of deconfounding methods on matched "
    "simulation cohorts (three seeds). Cohort A (safety): strong shared disease "
    "program; cohort C (leakage): identity-fingerprint confound only. LDI is "
    "the leakage-detection index; values below the gate 1.645 indicate no "
    "detectable cross-donor leakage. R = \u03c4_lodo / \u03c4_insample is the "
    "transferable fraction. MRP-ST-Repair is the only method with R_A = 1.00 "
    "(full signal retention) and LDI_C < 0 (leakage reversed)."
)


def load_table_rows():
    s = json.loads(SUMMARY.read_text(encoding="utf-8"))
    rows = []
    order = ["baseline", "mrp", "groupdro", "irm"]
    for arm in order:
        if arm not in s["table"]["A"]:
            continue
        for dose in sorted(float(k) for k in s["table"]["A"][arm]):
            a = s["table"]["A"][arm][str(dose)]["metrics"]
            c = s["table"]["C"][arm][str(dose)]["metrics"]
            rows.append({
                "method": "Baseline" if arm == "baseline"
                else ("MRP" if arm == "mrp"
                      else ("Group-DRO" if arm == "groupdro" else "IRM")),
                "dose": dose,
                "ldi_a": a["ldi_mean"],
                "tau_a": a["tau_lodo_mean"],
                "r_a": a["R_mean"],
                "ldi_c": c["ldi_mean"],
                "tau_c": c["tau_lodo_mean"],
                "r_c": c["R_mean"],
            })
    return rows


def fmt(v, nd=3):
    if v is None or v != v:
        return "n/a"
    return f"{v:+.{nd}f}" if abs(v) < 10 else f"{v:.{nd}f}"


def make_paragraph(doc, text, style=None, bold=False):
    p = OxmlElement("w:p")
    if style:
        pPr = OxmlElement("w:pPr")
        pStyle = OxmlElement("w:pStyle")
        pStyle.set(qn("w:val"), style)
        pPr.append(pStyle)
        p.append(pPr)
    r = OxmlElement("w:r")
    if bold:
        rPr = OxmlElement("w:rPr")
        b = OxmlElement("w:b")
        rPr.append(b)
        r.append(rPr)
    t = OxmlElement("w:t")
    t.text = text
    t.set(qn("xml:space"), "preserve")
    r.append(t)
    p.append(r)
    return p


def make_table(doc, rows):
    tbl = doc.add_table(rows=1 + len(rows), cols=8)
    tbl.style = "Table Grid"
    hdr = tbl.rows[0].cells
    headers = ["Method", "\u03bb", "LDI$_A$", "\u03c4_lodo,A", "R$_A$",
               "LDI$_C$", "\u03c4_lodo,C", "R$_C$"]
    for i, h in enumerate(headers):
        hdr[i].text = h
        for p in hdr[i].paragraphs:
            for r in p.runs:
                r.bold = True
    for ri, row in enumerate(rows, start=1):
        c = tbl.rows[ri].cells
        c[0].text = row["method"]
        c[1].text = f"{row['dose']:g}"
        c[2].text = fmt(row["ldi_a"])
        c[3].text = fmt(row["tau_a"], 4)
        c[4].text = fmt(row["r_a"])
        c[5].text = fmt(row["ldi_c"])
        c[6].text = fmt(row["tau_c"], 4)
        c[7].text = fmt(row["r_c"])
    return tbl


def insert_after(ref_element, new_element):
    ref_element.addnext(new_element)
    return new_element


def process(doc_path: Path):
    doc = Document(str(doc_path))

    # Locate anchor heading and its content paragraph
    anchor_p = None
    for p in doc.paragraphs:
        if ANCHOR.lower() in p.text.lower() and "Heading 2" in (p.style.name or ""):
            anchor_p = p
            break
    if anchor_p is None:
        raise RuntimeError(f"anchor heading not found in {doc_path.name}")

    content_p = None
    seen = False
    for p in doc.paragraphs:
        if p._element is anchor_p._element:
            seen = True
            continue
        if seen and p.text.strip() and "Heading" not in (p.style.name or ""):
            content_p = p
            break
    if content_p is None:
        raise RuntimeError(f"content paragraph after anchor not found in {doc_path.name}")

    # Remove a previously inserted SOTA section if present (idempotent)
    body = doc.element.body
    children = list(body)
    start_idx = None
    for i, el in enumerate(children):
        if el.tag.endswith("}p"):
            txt = "".join(t.text or "" for t in el.iter(qn("w:t")))
            if NEW_HEADING.lower() in txt.lower():
                start_idx = i
                break
    if start_idx is not None:
        # Remove from start_idx until the next Heading 1 (DISCUSSION)
        for el in children[start_idx:]:
            if el.tag.endswith("}p"):
                txt = "".join(t.text or "" for t in el.iter(qn("w:t")))
                if txt.strip().upper() == "DISCUSSION":
                    break
            body.remove(el)

    # Build new elements
    rows = load_table_rows()
    heading_el = make_paragraph(doc, NEW_HEADING, style="Heading2")
    intro_el = make_paragraph(doc, INTRO)
    caption_el = make_paragraph(doc, CAPTION)

    # Insert heading + intro after content_p
    insert_after(content_p._element, heading_el)
    insert_after(heading_el, intro_el)
    # Create table at end of doc, then move it
    tbl = make_table(doc, rows)
    tbl_el = tbl._element
    insert_after(intro_el, tbl_el)
    insert_after(tbl_el, caption_el)

    doc.save(str(doc_path))
    print(f"[ok] {doc_path.name}")


if __name__ == "__main__":
    for d in DOCS:
        process(d)
