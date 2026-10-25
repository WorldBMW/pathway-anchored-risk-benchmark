"""Quick usability check for GSE316098 (186-ROI cervical adenocarcinoma GeoMx).

Confirms the matrix parses, decodes the column naming scheme
(`<SilvaPattern>.<patient>.<epi|stroma>`), and reports expression of a few
marker panels so we know the data is real and analysable before wiring it into
the validation pipeline.

Usage:
    python scripts/verify_gse316098.py
"""
from __future__ import annotations

import gzip
import re
from pathlib import Path

F = (Path(__file__).resolve().parents[1] / "data" / "st_visium"
     / "geo_cervical_geomx_GSE316098"
     / "GSE316098_raw.counts.linear.formatted.csv.gz")

# marker panels we care about in this project
PANELS = {
    " epithelial/tumour": ["KRT5", "KRT16", "CDH1", "MUC1", "EPCAM", "TP63"],
    " stromal": ["COL1A1", "DCN", "COMP", "ACTA2", "FN1"],
    " immune": ["CD3G", "CD8A", "CD68", "FCGR1A", "PTPRC", "IL34", "CSF1R"],
    " proliferation": ["MKI67", "TOP2A", "CCNB1"],
    " HPV/high-risk": ["CDKN2A", "SERPINB3", "MCM2"],
}


def main() -> int:
    if not F.exists():
        print(f"missing {F}")
        return 1
    txt = gzip.decompress(F.read_bytes()).decode("utf-8", "ignore")
    lines = [ln for ln in txt.splitlines() if ln.strip()]
    header = [c.strip().lstrip("\ufeff") for c in lines[0].split(",")]
    genes: list[str] = []
    rows: list[list[float]] = []
    for ln in lines[1:]:
        parts = ln.split(",")
        genes.append(parts[0].strip().strip('"'))
        rows.append([float(x) if x not in ("", "NA", "NaN") else 0.0
                     for x in parts[1:]])
    rois = header[1:]
    print(f"genes : {len(genes)}")
    print(f"ROIs  : {len(rois)}")

    # ---- decode column names ------------------------------------------------
    meta = []
    for r in rois:
        m = re.match(r"^([^\.]+)\.(\d+[A-Za-z\-]*)\.(epi|stroma)$", r)
        if m:
            meta.append((r, m.group(1), m.group(2), m.group(3)))
    print(f"parsed: {len(meta)}/{len(rois)} columns match "
          f"<Silva>.<patient>.<epi|stroma>")

    from collections import Counter
    print("  Silva patterns :", dict(Counter(x[1] for x in meta)))
    print("  compartments   :", dict(Counter(x[3] for x in meta)))
    pats = sorted({x[2] for x in meta})
    print(f"  patients       : {len(pats)} -> {pats[:12]}")

    # ---- marker expression --------------------------------------------------
    idx = {g: i for i, g in enumerate(genes)}
    print("\nmarker detectability (fraction of ROIs with count > 0):")
    for panel, gl in PANELS.items():
        out = []
        for g in gl:
            if g not in idx:
                out.append(f"{g}:NA")
                continue
            col = rows[idx[g]]  # one row per gene, one value per ROI
            det = sum(1 for v in col if v > 0) / len(col)
            out.append(f"{g}:{det*100:4.1f}%")
        print(f" {panel:16s} " + "  ".join(out))

    # ---- epi vs stroma contrast (sanity: stroma markers should be higher) ----
    print("\nepi vs stroma mean (sanity check):")
    epi_i = [i for i, r in enumerate(rois) if r.endswith(".epi")]
    st_i = [i for i, r in enumerate(rois) if r.endswith(".stroma")]
    for g in ["COL1A1", "DCN", "EPCAM", "KRT5", "CD3G"]:
        if g not in idx:
            continue
        row = rows[idx[g]]
        e = sum(row[i] for i in epi_i) / max(len(epi_i), 1)
        s = sum(row[i] for i in st_i) / max(len(st_i), 1)
        print(f"  {g:8s} epi={e:9.1f}   stroma={s:9.1f}   "
              f"{'stroma>' if s > e else 'epi>'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
