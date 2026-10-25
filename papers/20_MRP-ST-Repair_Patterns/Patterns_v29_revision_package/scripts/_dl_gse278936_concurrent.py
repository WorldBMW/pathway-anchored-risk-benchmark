"""Concurrent downloader for GSE278936 (reuses logic from download_gse278936.py).

Speeds up the slow GEO FTP by fetching multiple files in parallel.
Resumable: existing files are skipped; .part files continue.
"""
from __future__ import annotations
import sys
import time
import gzip
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# reuse the original module's data + helpers
sys.path.insert(0, str(Path(__file__).resolve().parent))
from download_gse278936 import (
    _SAMPLES, WANT, gsm_dir, list_dir, download_file, build_h5,
    OUT_DIR, GSE,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "st_visium" / OUT_DIR
WORKERS = 6


def collect_jobs():
    """Return list of (url, dest_path, gzipped_dest) for missing files.

    URLs are constructed directly (filename = <GSM>_<prefix>_<suffix>)
    to avoid 52 slow directory-list HTTP requests.
    """
    jobs = []
    for gsm, prefix in _SAMPLES.items():
        sdir = BASE / prefix
        sdir.mkdir(parents=True, exist_ok=True)
        suppl = gsm_dir(gsm)
        for suffix, dest_name in WANT.items():
            dest = sdir / dest_name
            if dest.exists() and dest.stat().st_size > 0:
                continue
            fname = f"{gsm}_{prefix}_{suffix}"
            url = f"{suppl}/{fname}"
            gz = (not dest_name.endswith(".gz")) and fname.endswith(".gz")
            jobs.append((url, dest, gz))
    return jobs


def run_job(job):
    url, dest, gz = job
    ok = download_file(url, dest, gz)
    return (dest, ok)


def main():
    BASE.mkdir(parents=True, exist_ok=True)
    print(f"[{time.strftime('%H:%M:%S')}] collecting file list ...", flush=True)
    jobs = collect_jobs()
    print(f"[{time.strftime('%H:%M:%S')}] {len(jobs)} files to download "
          f"({WORKERS} workers)", flush=True)

    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(run_job, j): j for j in jobs}
        for fut in as_completed(futures):
            dest, ok = fut.result()
            done += 1
            tag = "ok" if ok else "FAIL"
            print(f"  [{done}/{len(jobs)}] {tag} {dest.name}", flush=True)

    # build h5 for completed samples
    print(f"[{time.strftime('%H:%M:%S')}] building h5 for completed samples ...",
          flush=True)
    for prefix in _SAMPLES.values():
        sdir = BASE / prefix
        if (sdir / "matrix.mtx.gz").exists() and \
           (sdir / "barcodes.tsv.gz").exists() and \
           (sdir / "features.tsv.gz").exists():
            h5 = sdir / "filtered_feature_bc_matrix.h5"
            if not h5.exists():
                if build_h5(sdir):
                    print(f"  h5 ok: {prefix}", flush=True)
                else:
                    print(f"  h5 FAIL: {prefix}", flush=True)

    print(f"[{time.strftime('%H:%M:%S')}] done.", flush=True)


if __name__ == "__main__":
    main()
