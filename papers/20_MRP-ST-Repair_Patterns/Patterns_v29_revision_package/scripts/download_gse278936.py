"""Download the GSE278936 prostate Visium cohort (2nd independent external ST cohort).

Why this cohort
---------------
The MRP-ST-Repair paper currently has a single independent external spatial
cohort (GSE268014, HPV+/- HNSCC). GSE278936 is an independent 10x Visium cohort
with a clean per-sample binary disease label:

    benign  (BPH  : Benign prostatic hyperplasia)          x4
    tumour  (TRNA : treatment-naive PCa,
             NEADT: neoadjuvant-treated PCa,
             CRPC : castration-resistant PCa,
             MET  : metastatic PCa)                        x48
    -> 52 Visium sections, all from separate patient samples.

Verified 2026-10-19 from the GEO series page + FTP filelist
(https://ftp.ncbi.nlm.nih.gov/geo/series/GSE278nnn/GSE278936/suppl/filelist.txt):
every sample ships standard Space Ranger output *without* the h5:

    <GSM>_<prefix>_barcodes.tsv.gz
    <GSM>_<prefix>_features.tsv.gz
    <GSM>_<prefix>_matrix.mtx.gz
    <GSM>_<prefix>_scalefactors_json.json.gz
    <GSM>_<prefix>_tissue_hires_image.png.gz
    <GSM>_<prefix>_tissue_lowres_image.png.gz
    <GSM>_<prefix>_tissue_positions_list.csv.gz

i.e. delivery pattern B of scripts/download_st_external_validation.py: the images
ship as ``.png.gz`` (not ``.jpg.gz``), so the generic
``scripts/reconstruct_spatial.py`` (which globs ``*.jpg.gz``) cannot be reused
here without editing it.  Instead this script *itself* synthesises
``filtered_feature_bc_matrix.h5`` in each sample dir after the matrix files land,
so repair_e3_methodB_train.py::discover() finds the samples directly.  The real
``spatial/tissue_positions_list.csv`` / ``scalefactors_json.json`` / images also
come straight from GEO (better than reconstructed ones).

No 20x TIFFs exist for this series, so nothing giant needs skipping.

Usage
-----
  python scripts/download_gse278936.py --dry            # list only
  python scripts/download_gse278936.py                  # full cohort (52)
  python scripts/download_gse278936.py --max-samples 8
"""
from __future__ import annotations

import argparse
import gzip
import sys
import time
import urllib.request
from pathlib import Path

GEO_SAMPLES = "https://ftp.ncbi.nlm.nih.gov/geo/samples"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) project4-st-dl"}

GSE = "GSE278936"
OUT_DIR = "geo_prostate_GSE278936"

# --- sample map: GSM -> short prefix (prefix also encodes the label class) ----
# benign (BPH) = benign, everything else = tumour.
_SAMPLES: dict[str, str] = {}
for i in range(1, 5):                                   # BPH 1-4
    _SAMPLES[f"GSM{8557975 + i}"] = f"BPH_{i}"
for i in range(1, 18):                                  # TRNA 1-17 (treatment-naive)
    _SAMPLES[f"GSM{8557979 + i}"] = f"TRNA_{i}"
for i in range(1, 23):                                  # NEADT 1-22 (neoadjuvant)
    _SAMPLES[f"GSM{8557996 + i}"] = f"NEADT_{i}"
for i in range(1, 6):                                   # CRPC 1-5
    _SAMPLES[f"GSM{8558018 + i}"] = f"CRPC_{i}"
for letter in ("A", "B", "C", "D"):                     # MET A-D
    _SAMPLES[f"GSM{8558024 + ord(letter) - 65}"] = f"MET_{letter}"

# suffix in the GEO suppl dir -> destination path inside the sample dir
WANT = {
    "matrix.mtx.gz": "matrix.mtx.gz",
    "barcodes.tsv.gz": "barcodes.tsv.gz",
    "features.tsv.gz": "features.tsv.gz",
    "tissue_positions_list.csv.gz": "spatial/tissue_positions_list.csv",
    "tissue_hires_image.png.gz": "spatial/tissue_hires_image.png",
    "tissue_lowres_image.png.gz": "spatial/tissue_lowres_image.png",
    "scalefactors_json.json.gz": "spatial/scalefactors_json.json",
}
SKIP_SUFFIX = (".tif.gz", "_20x.tif.gz")


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


CHUNK = 256 * 1024          # bytes per Range request
MAX_RETRIES = 6


def download_file(url: str, dest: Path, gzipped_dest: bool) -> bool:
    """Range-chunked, resumable downloader (NCBI GEO is very slow from CN)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")

    total = remote_size(url)
    have = part.stat().st_size if part.exists() else 0

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
                print(f"      ! giving up at {have}/{total}: {exc}", flush=True)
                return False
            time.sleep(min(2 ** attempt, 20))
            continue
        if not blob:
            break
        attempt = 0
        with open(part, "ab") as fh:
            fh.write(blob)
        have += len(blob)
        if total > 0:
            pct = 100.0 * have / total
            print(f"        {have/1e6:8.2f} / {total/1e6:.2f} MB  ({pct:5.1f}%)",
                  flush=True)

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


def build_h5(sample_dir: Path) -> bool:
    """Synthesise canonical 10x ``filtered_feature_bc_matrix.h5`` from the
    downloaded mtx/barcodes/features (GEO ships no h5 for this series).

    Layout expected by st_data.py's ``_read_10x_h5``:
        matrix/{data, indices, indptr, shape, barcodes,
                features/{name, id, feature_type, genome}}
    with ``shape`` = (n_genes, n_spots) and a CSC indptr over the spot axis.
    """
    import numpy as np
    import h5py
    from scipy.sparse import csc_matrix

    matrix_gz = sample_dir / "matrix.mtx.gz"
    barcodes_gz = sample_dir / "barcodes.tsv.gz"
    features_gz = sample_dir / "features.tsv.gz"
    out_h5 = sample_dir / "filtered_feature_bc_matrix.h5"
    if out_h5.exists() and out_h5.stat().st_size > 0:
        return True
    if not (matrix_gz.exists() and barcodes_gz.exists() and features_gz.exists()):
        return False

    rows, cols, data = [], [], []
    n_genes = n_spots = 0
    with gzip.open(matrix_gz, "rt") as g:
        for line in g:
            line = line.strip()
            if not line or line.startswith("%"):
                continue
            parts = line.split()
            if n_genes == 0 and len(parts) == 3:
                n_genes, n_spots, _ = int(parts[0]), int(parts[1]), int(parts[2])
                continue
            rows.append(int(parts[0]) - 1)
            cols.append(int(parts[1]) - 1)
            data.append(float(parts[2]))
    gxc = csc_matrix((data, (rows, cols)), shape=(n_genes, n_spots))

    with gzip.open(barcodes_gz, "rt") as f:
        barcodes = np.array([l.strip().encode() for l in f.readlines()])
    with gzip.open(features_gz, "rt") as f:
        feats = [l.strip().split("\t") for l in f.readlines()]
    gene_ids = np.array([x[0].encode() for x in feats])
    gene_names = np.array([x[1].encode() for x in feats])
    feature_types = np.array([x[2].encode() if len(x) > 2 else b"Gene Expression"
                              for x in feats])

    with h5py.File(out_h5, "w") as h:
        m = h.create_group("matrix")
        m.create_dataset("data", data=np.array(gxc.data, dtype=np.float32))
        m.create_dataset("indices", data=np.array(gxc.indices, dtype=np.int64))
        m.create_dataset("indptr", data=np.array(gxc.indptr, dtype=np.int64))
        m.create_dataset("shape", data=np.array([n_genes, n_spots], dtype=np.int64))
        m.create_dataset("barcodes", data=barcodes)
        ft = m.create_group("features")
        ft.create_dataset("name", data=gene_names)
        ft.create_dataset("id", data=gene_ids)
        ft.create_dataset("feature_type", data=feature_types)
        ft.create_dataset("genome", data=np.array([b"GRCh38" for _ in feats]))
    return True


def process_sample(gsm: str, label: str, out_root: Path, dry: bool) -> tuple[int, int]:
    files = list_dir(gsm_dir(gsm) + "/")
    got, plan = 0, 0
    for suffix, rel in WANT.items():
        matches = [f for f in files if f.endswith(suffix)]
        if not matches:
            continue
        if any(m.endswith(SKIP_SUFFIX) for m in matches):
            continue
        fname = sorted(matches, key=len)[0]
        plan += 1
        dest = out_root / label / rel
        if dest.exists() and dest.stat().st_size > 0:
            print(f"      = {rel} (exists)", flush=True)
            got += 1
            continue
        url = f"{gsm_dir(gsm)}/{fname}"
        size = remote_size(url)
        decompress = not rel.endswith(".gz")
        print(f"      > {fname}  ({size/1e6:.1f} MB)", flush=True)
        if dry:
            continue
        if download_file(url, dest, decompress):
            got += 1
    if not dry:
        try:
            if build_h5(out_root / label):
                print(f"      [h5] filtered_feature_bc_matrix.h5 ready", flush=True)
            else:
                print(f"      [h5] skipped (matrix files incomplete)", flush=True)
        except Exception as exc:
            print(f"      [h5 FAIL] {exc}", flush=True)
    return got, plan


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-samples", type=int, default=0, help="0 = all")
    ap.add_argument("--out", default="data/st_visium")
    ap.add_argument("--dry", action="store_true", help="list what would be downloaded")
    args = ap.parse_args()

    samples = dict(_SAMPLES)
    if args.max_samples:
        samples = dict(list(samples.items())[:args.max_samples])

    out_root = Path(args.out) / OUT_DIR
    print(f"\n=== {GSE}: prostate Visium, benign(BPH) vs tumour(TRNA/NEADT/CRPC/MET)")
    print(f"    samples: {len(samples)}  -> {out_root}")

    total_ok = 0
    for gsm, label in samples.items():
        print(f"  [{label}] {gsm}", flush=True)
        try:
            got, plan = process_sample(gsm, label, out_root, args.dry)
            print(f"      -> {got}/{plan} files", flush=True)
            total_ok += got
        except Exception as exc:
            print(f"      ! {exc}", flush=True)

    print(f"\nDone. files written: {total_ok}")
    if not args.dry:
        print("Each sample dir now holds filtered_feature_bc_matrix.h5 + spatial/, "
              "i.e. repair_e3_methodB_train.py::discover() ready.")
        print(f"Run: python scripts/repair_e3_methodB_train.py --data "
              f"{out_root.as_posix()} --device cuda:0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
