"""Scan public repositories for cervical-cancer spatial-transcriptomics datasets.

Goal (project gap): the cervical ST cohort has only ~4 malignant sections, all from
one study (GSE208654), which is not enough for an *independent* external validation.
This script sweeps GEO for cervical / uterine-cervix spatial datasets and reports,
for every candidate, whether it actually ships 10x-style ``*.h5`` matrices
(``filtered_feature_bc_matrix.h5``) plus ``spatial/`` coordinate folders — the two
things `src/st_data.py` needs.

Checks performed per candidate GSE:
  1. GEO DataSets metadata (title / organism / n_samples / platform / date)
  2. ``<GSE>/suppl/`` FTP listing  -> h5 present?
  3. per-sample ``GSM*/suppl/`` listing -> h5 present?

Usage:
    python scripts/scan_cervical_st_datasets.py                 # scan + report
    python scripts/scan_cervical_st_datasets.py --out scan.csv  # also write CSV
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
GEO_FTP = "https://ftp.ncbi.nlm.nih.gov/geo"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) project4-scan"}

# GEO GDS search terms aimed at cervix + spatial. GPL24676 is Illumina NovaSeq
# (the platform 10x Visium libraries are sequenced on), which is why it is used
# as a soft co-filter rather than the sole criterion.
SEARCH_TERMS = [
    "cervical cancer AND spatial transcriptomics",
    "cervical cancer AND Visium",
    "cervical cancer AND spatial",
    "cervix AND spatial transcriptomics",
    "cervix AND Visium",
    "endocervical AND spatial",
    "cervical intraepithelial neoplasia AND spatial",
    "uterine cervix AND spatial transcriptomics",
    "HPV AND cervical AND spatial",
    "cervical squamous cell carcinoma AND spatial",
    "cervical adenocarcinoma AND spatial",
    "HPV-associated AND endocervical AND spatial",
]

# Words that must appear in the title/summary for a series to be worth a FTP probe.
CERVIX_PAT = re.compile(
    r"cervi|cervix|cervical|\bcesc\b|endocervic|ectocervic|\bcin\b|hpv", re.I
)
SPATIAL_PAT = re.compile(
    r"spatial|visium|stereum|stereo-seq|geomics|geomx|xenium|slide-seq|merfish|"
    r"spatial transcriptom|spatially resolved", re.I
)
# Obvious non-spatial / non-cervix noise
NOISE_PAT = re.compile(
    r"geospatial|geographic|spatial analysis of .*services|spatial mapping and grading|"
    r"screening|spatial distribution and characteristics", re.I
)


def _get(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")


def esearch(term: str, retmax: int = 80) -> list[str]:
    url = (f"{EUTILS}esearch.fcgi?db=gds&retmode=json&retmax={retmax}"
           f"&term={urllib.parse.quote(term)}")
    try:
        js = json.loads(_get(url, 30))
        return js.get("esearchresult", {}).get("idlist", []) or []
    except Exception as exc:  # network / rate-limit
        print(f"  ! esearch failed for {term!r}: {exc}", file=sys.stderr)
        return []


def esummary(uids: list[str]) -> dict:
    out: dict[str, dict] = {}
    for i in range(0, len(uids), 60):
        chunk = uids[i:i + 60]
        url = f"{EUTILS}esummary.fcgi?db=gds&retmode=json&id={','.join(chunk)}"
        try:
            js = json.loads(_get(url, 40))
        except Exception as exc:
            print(f"  ! esummary failed: {exc}", file=sys.stderr)
            continue
        for uid in chunk:
            rec = js.get("result", {}).get(uid)
            if rec:
                out[uid] = rec
        time.sleep(0.35)
    return out


def ftp_list(path: str) -> list[str]:
    """Return file names in a GEO FTP directory (empty list on any error)."""
    url = f"{GEO_FTP}/{path.strip('/')}/"
    try:
        html = _get(url, 30)
    except Exception:
        return []
    items = re.findall(r'href="([^"]+)"', html)
    return [i.rstrip("/") for i in items
            if not i.startswith(("/", "http", "?")) and i not in ("", "../")]


def gse_ftp_dir(acc: str) -> str:
    """GSE208654 -> series/GSE208nnn/GSE208654"""
    return f"series/{acc[:-3]}nnn/{acc}"


def probe_files(acc: str) -> tuple[list[str], list[str]]:
    """Return (all files seen, h5 files seen) for a GSE's series + sample dirs."""
    files: list[str] = []
    base = gse_ftp_dir(acc)
    files += [f"suppl/{f}" for f in ftp_list(f"{base}/suppl")]
    files += [f"matrix/{f}" for f in ftp_list(f"{base}/matrix")]
    return files, [f for f in files if f.lower().endswith((".h5", ".h5ad", ".hdf5"))]


def probe_gsm_h5(acc: str, max_gsm: int = 12) -> int:
    """Peek at a few GSM suppl dirs; return count of h5 files found there."""
    # resolve GSMs from the SOFT family file (cheap, one request)
    try:
        soft = _get(f"{GEO_FTP}/{gse_ftp_dir(acc)}/soft/{acc}_family.soft.gz", 40)
    except Exception:
        return -1
    import gzip
    try:
        txt = gzip.decompress(soft).decode("utf-8", "ignore") if isinstance(soft, bytes) else soft
    except Exception:
        return -1
    gsm_ids = sorted(set(re.findall(r"\^Sample = (GSM\d+)", txt)))[:max_gsm]
    if not gsm_ids:
        return 0
    found = 0
    for gsm in gsm_ids:
        d = f"samples/{gsm[:-3]}nnn/{gsm}/suppl"
        for f in ftp_list(d):
            if f.lower().endswith((".h5", ".h5ad", ".hdf5")):
                found += 1
    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="", help="optional CSV output path")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    print("== Step 1: GEO DataSets search ==")
    uids: list[str] = []
    for t in SEARCH_TERMS:
        got = esearch(t)
        print(f"  {t:<52s} -> {len(got)}")
        uids += got
        time.sleep(0.4)
    uids = sorted(set(uids))
    print(f"  union = {len(uids)} UIDs")

    print("== Step 2: metadata ==")
    meta = esummary(uids)
    print(f"  resolved {len(meta)} records")

    # ---- Step 3: keep plausible cervix+spatial human series -------------------
    cand: list[dict] = []
    for uid, r in meta.items():
        acc = r.get("accession", "")
        if not acc.startswith("GSE"):
            continue
        title = str(r.get("title", ""))
        summary = str(r.get("summary", ""))
        blob = title + " " + summary
        if not CERVIX_PAT.search(blob):
            continue
        if not SPATIAL_PAT.search(blob):
            continue
        if NOISE_PAT.search(title):
            continue
        if "Homo sapiens" not in str(r.get("taxon", "")):
            continue
        cand.append({
            "accession": acc,
            "n_samples": r.get("n_samples"),
            "platform": r.get("gpl"),
            "date": str(r.get("pdat", ""))[:10] or str(r.get("pubmedids", ""))[:0],
            "title": title[:180],
        })
    cand.sort(key=lambda d: d["accession"])
    print(f"  candidates after title filter = {len(cand)}")

    print("== Step 3: FTP probe for h5 / h5ad ==")
    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        fut = {ex.submit(probe_files, c["accession"]): c for c in cand}
        for f in as_completed(fut):
            c = fut[f]
            try:
                allf, h5 = f.result()
            except Exception as exc:
                allf, h5 = [], []
                print(f"  ! {c['accession']}: {exc}")
            c["h5_series"] = len(h5)
            c["files_sample"] = "; ".join(allf[:6])
            rows.append(c)
            flag = "H5!" if h5 else "    "
            print(f"  {flag} {c['accession']} n={c['n_samples']} "
                  f"h5={len(h5)}  {c['title'][:70]}")

    # ---- for series without a series-level h5, peek a few GSM dirs ------------
    todo = [r for r in rows if r["h5_series"] == 0]
    if todo:
        print(f"== Step 4: per-sample (GSM) probe for {len(todo)} series ==")
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            fut = {ex.submit(probe_gsm_h5, r["accession"]): r for r in todo}
            for f in as_completed(fut):
                r = fut[f]
                try:
                    n = f.result()
                except Exception:
                    n = -1
                r["h5_gsm"] = n
                if n > 0:
                    print(f"  H5! {r['accession']} -> {n} h5 in GSM dirs  {r['title'][:60]}")

    for r in rows:
        r.setdefault("h5_gsm", 0)
        r["usable_h5"] = "YES" if (r["h5_series"] or r["h5_gsm"] > 0) else "no"

    rows.sort(key=lambda r: (r["usable_h5"] != "YES", r["accession"]))

    print("\n================ RESULT ================")
    for r in rows:
        print(f"{r['usable_h5']:>3} | {r['accession']:<12} | n={str(r['n_samples']):>4} | "
              f"GPL={r['platform']} | series_h5={r['h5_series']} gsm_h5={r['h5_gsm']}")
        print(f"       {r['title'][:110]}")

    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"\nCSV -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
