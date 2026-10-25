"""Download external-validation ST cohorts for the cervix ST-H&E project.

Why this exists
---------------
The cervical ST cohort has only ~4 malignant sections and they all come from a
single study (GSE208654: N / HSIL / SCC / ADC). Using one study as both
development and validation is circular. This script pulls *independent* ST
cohorts that can serve as external validation.

Important (verified 2026-09-07): none of these GEO series ship an h5 in the
series-level `suppl/` dir. Two delivery patterns exist:

  A. per-sample `samples/GSMxxx/suppl/` already contains
     `*_filtered_feature_bc_matrix.h5` + `*_tissue_positions_list.csv.gz` +
     `*_tissue_hires_image.png.gz` + `*_scalefactors_json.json.gz`
     -> GSE281978. Download as-is, zero conversion needed.

  B. per-sample only has `barcodes/features/matrix.mtx` + images
     -> GSE268014 (also ships real tissue_positions_list.csv, better than
        GSE208654 whose coordinates had to be reconstructed).
        Run `scripts/reconstruct_spatial.py` afterwards to build the h5.

Cohorts
-------
  GSE281978 : 6 sections, HPV-associated head & neck squamous cell carcinoma
              (10x Visium, full Space Ranger output incl. h5). ~100 MB total.
  GSE268014 : 39 sections, HPV+ vs HPV- head & neck squamous cell carcinoma
              (10x Visium CytAssist, mtx + real coordinates, no h5).
              NOTE: the RAW.tar is 21 GB because each sample carries a ~700 MB
              20x TIFF. We download per-sample and SKIP the TIFF, which keeps
              each sample to ~35-90 MB.

Usage
-----
  python scripts/download_st_external_validation.py --cohort GSE281978
  python scripts/download_st_external_validation.py --cohort GSE268014 --max-samples 8
  python scripts/download_st_external_validation.py --cohort all --max-samples 6
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import sys
import time
import urllib.request
from pathlib import Path

GEO_SAMPLES = "https://ftp.ncbi.nlm.nih.gov/geo/samples"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) project4-st-dl"}

# ---------------------------------------------------------------- cohorts ----
COHORTS: dict[str, dict] = {
    "GSE281978": {
        "description": "HPV-associated head & neck SCC, 10x Visium, FULL Space Ranger output (h5 included)",
        "out_dir": "geo_hpv_hnscc_GSE281978",
        "has_h5": True,
        # GSM -> short sample label (lesion id from the file names)
        "samples": {
            "GSM8633891": "LI_SING_21_00757",
            "GSM8633892": "LI_SING_21_00758",
            "GSM8633893": "LI_SING_21_01569",
            "GSM8633894": "LI_SING_21_01570",
            "GSM8633895": "LI_SING_21_01586",
            "GSM8633896": "LI_SING_21_01587",
        },
        # file suffix -> destination path inside the sample dir
        "want": {
            "filtered_feature_bc_matrix.h5": "filtered_feature_bc_matrix.h5",
            "tissue_positions_list.csv.gz": "spatial/tissue_positions_list.csv",
            "tissue_hires_image.png.gz": "spatial/tissue_hires_image.png",
            "scalefactors_json.json.gz": "spatial/scalefactors_json.json",
        },
    },
    "GSE268014": {
        "description": "HPV+ vs HPV- head & neck SCC, 10x Visium CytAssist (mtx + real coords, no h5)",
        "out_dir": "geo_hnscc_hpv_GSE268014",
        "has_h5": False,
        # 39 samples; discovered dynamically from the filelist unless limited
        "samples": {},
        "want": {
            "matrix.mtx.gz": "matrix.mtx.gz",
            "barcodes.tsv.gz": "barcodes.tsv.gz",
            "features.tsv.gz": "features.tsv.gz",
            "tissue_positions_list.csv.gz": "spatial/tissue_positions_list.csv",
            "tissue_hires_image.png.gz": "spatial/tissue_hires_image.png",
            "scalefactors_json.json.gz": "spatial/scalefactors_json.json",
            "detected_tissue_image.jpg.gz": "detected_tissue_image.jpg",
        },
        # never download: 20x full-resolution TIFF, ~700 MB each
        "skip_suffix": (".tif.gz", "_20x.tif.gz"),
    },
}


def gsm_dir(gsm: str) -> str:
    return f"{GEO_SAMPLES}/{gsm[:-3]}nnn/{gsm}/suppl"


def http_get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read()


def remote_size(url: str) -> int:
    try:
        req = urllib.request.Request(url, method="HEAD", headers=UA)
        return int(urllib.request.urlopen(req, timeout=30).headers.get("Content-Length", 0))
    except Exception:
        return -1


def list_dir(url: str) -> list[str]:
    import re
    html = http_get(url, 40).decode("utf-8", "ignore")
    items = re.findall(r'href="([^"]+)"', html)
    return [i for i in items
            if not i.startswith(("/", "http", "?")) and i not in ("", "../")]


def discover_gse268014(limit: int) -> dict[str, str]:
    """Read GSE268014 filelist.txt -> {GSM: sample_prefix}."""
    url = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE268nnn/GSE268014/suppl/filelist.txt"
    txt = http_get(url, 90).decode("utf-8", "ignore")
    out: dict[str, str] = {}
    for line in txt.splitlines():
        parts = [p for p in line.split("\t") if p.strip()]
        if len(parts) < 2 or not parts[1].startswith("GSM"):
            continue
        fname = parts[1].strip()
        gsm = fname.split("_")[0]
        if not gsm.startswith("GSM"):
            continue
        if gsm not in out:
            out[gsm] = gsm
        if limit and len(out) >= limit:
            break
    return out


CHUNK = 256 * 1024          # bytes per Range request
MAX_RETRIES = 6


def download_file(url: str, dest: Path, gzipped_dest: bool) -> bool:
    """Range-chunked, resumable downloader.

    NCBI GEO over a direct (non-proxied) link from mainland China runs at
    ~8-9 KB/s and often drops the connection mid-stream on multi-MB files.
    Requesting small ranges and appending to a `.part` file makes the transfer
    survivable across interruptions: re-running the script resumes where it
    stopped instead of starting over.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")

    total = remote_size(url)
    have = part.stat().st_size if part.exists() else 0
    if total > 0 and have >= total:
        part.replace(dest) if False else None  # fall through to finalize

    attempt = 0
    while True:
        if total > 0 and have >= total:
            break
        end = min(have + CHUNK, total) - 1 if total > 0 else have + CHUNK - 1
        if total > 0 and have + CHUNK > total:
            end = total - 1
        try:
            req = urllib.request.Request(
                url, headers={**UA, "Range": f"bytes={have}-{end}"})
            with urllib.request.urlopen(req, timeout=90) as r:
                blob = r.read()
        except Exception as exc:
            attempt += 1
            if attempt > MAX_RETRIES:
                print(f"      ! giving up at {have}/{total}: {exc}")
                return False
            time.sleep(min(2 ** attempt, 20))
            continue
        if not blob:
            # server ignored Range and returned nothing new -> treat as done
            break
        attempt = 0
        with open(part, "ab") as fh:
            fh.write(blob)
        have += len(blob)
        if total > 0:
            pct = 100.0 * have / total
            mb = have / 1e6
            print(f"        {mb:8.2f} / {total/1e6:.2f} MB  ({pct:5.1f}%)", flush=True)

    if not part.exists():
        return False
    data = part.read_bytes()
    if gzipped_dest and url.endswith(".gz"):
        try:
            data = gzip.decompress(data)
        except Exception:
            pass  # not actually gzipped, keep raw
    dest.write_bytes(data)
    part.unlink(missing_ok=True)
    return True


def process_sample(gsm: str, label: str, cfg: dict, out_root: Path,
                   dry: bool) -> tuple[int, int]:
    files = list_dir(gsm_dir(gsm) + "/")
    got, plan = 0, 0
    for suffix, rel in cfg["want"].items():
        matches = [f for f in files if f.endswith(suffix)]
        if not matches:
            continue
        # skip giant TIFFs
        if any(m.endswith(cfg.get("skip_suffix", ())) for m in matches):
            continue
        fname = sorted(matches, key=len)[0]
        plan += 1
        dest = out_root / label / rel
        if dest.exists() and dest.stat().st_size > 0:
            print(f"      = {rel} (exists)")
            got += 1
            continue
        url = f"{gsm_dir(gsm)}/{fname}"
        size = remote_size(url)
        gzipped_dest = not rel.endswith(".gz") and not rel.endswith(".h5")
        print(f"      > {fname}  ({size/1e6:.1f} MB)")
        if dry:
            continue
        if download_file(url, dest, gzipped_dest):
            got += 1
    return got, plan


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", default="GSE281978",
                    choices=list(COHORTS) + ["all"])
    ap.add_argument("--max-samples", type=int, default=0, help="0 = all")
    ap.add_argument("--out", default="data/st_visium")
    ap.add_argument("--dry", action="store_true", help="list what would be downloaded")
    args = ap.parse_args()

    out_root = Path(args.out)
    targets = list(COHORTS) if args.cohort == "all" else [args.cohort]
    total_ok = 0

    for acc in targets:
        cfg = COHORTS[acc]
        samples = dict(cfg["samples"])
        if not samples:  # dynamic discovery (GSE268014)
            samples = discover_gse268014(args.max_samples)
        if args.max_samples:
            samples = dict(list(samples.items())[:args.max_samples])

        print(f"\n=== {acc}: {cfg['description']}")
        print(f"    samples: {len(samples)}  -> {out_root / cfg['out_dir']}")
        root = out_root / cfg["out_dir"]
        root.mkdir(parents=True, exist_ok=True)

        for gsm, label in samples.items():
            print(f"  [{label}] {gsm}")
            try:
                got, plan = process_sample(gsm, label, cfg, root, args.dry)
                print(f"      -> {got}/{plan} files")
                total_ok += got
            except Exception as exc:
                print(f"      ! {exc}")

    print(f"\nDone. files written: {total_ok}")
    if not args.dry:
        print("Next: run scripts/verify_st_download.py to check h5 readability.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
