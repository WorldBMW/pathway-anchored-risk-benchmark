"""Resumable, Range-chunked downloader for GEO / any HTTP file.

Direct (non-proxied) connections to ftp.ncbi.nlm.nih.gov from mainland China
throttle to roughly 8-9 KB/s and frequently reset on multi-megabyte transfers,
so a single `urlopen().read()` almost never completes. This helper pulls the
file in 256 KB ranges and appends to a `.part` file, so an interrupted run can
simply be restarted and will resume from where it stopped.

Usage:
    python scripts/geo_chunked_download.py <url> <output_path>
    python scripts/geo_chunked_download.py <url> <output_path> --chunk 131072
    python scripts/geo_chunked_download.py <url> <output_path> --gunzip

Exit code 0 = file complete and verified against Content-Length.
"""
from __future__ import annotations

import argparse
import gzip
import os
import sys
import time
import urllib.request
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) project4-st-dl"}


def head_size(url: str) -> int:
    try:
        req = urllib.request.Request(url, method="HEAD", headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            return int(r.headers.get("Content-Length", 0) or 0)
    except Exception:
        return 0


def fetch(url: str, out: Path, chunk: int, gunzip: bool, retries: int = 8) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    part = out.with_name(out.name + ".part")
    total = head_size(url)
    have = part.stat().st_size if part.exists() else 0
    print(f"  url   : {url}")
    print(f"  dest  : {out}")
    print(f"  size  : {total/1e6:.2f} MB (resuming from {have/1e6:.2f} MB)")

    fails = 0
    while total == 0 or have < total:
        end = have + chunk - 1
        if total > 0:
            end = min(end, total - 1)
        try:
            req = urllib.request.Request(
                url, headers={**UA, "Range": f"bytes={have}-{end}"})
            with urllib.request.urlopen(req, timeout=120) as r:
                blob = r.read()
        except Exception as exc:
            fails += 1
            if fails > retries:
                print(f"  ! abort after {fails} consecutive failures: {exc}")
                return 1
            time.sleep(min(2 ** fails, 30))
            continue
        if not blob:
            print("  ! empty chunk; assuming complete")
            break
        fails = 0
        with open(part, "ab") as fh:
            fh.write(blob)
        have += len(blob)
        if total:
            print(f"    {have/1e6:8.2f} / {total/1e6:7.2f} MB "
                  f"({100.0*have/total:5.1f}%)", flush=True)
        else:
            print(f"    {have/1e6:8.2f} MB", flush=True)

    data = part.read_bytes()
    if gunzip:
        try:
            data = gzip.decompress(data)
        except Exception as exc:
            print(f"  ! gunzip failed ({exc}); keeping raw bytes")
    out.write_bytes(data)
    part.unlink(missing_ok=True)
    print(f"  OK -> {out} ({out.stat().st_size/1e6:.2f} MB)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("out")
    ap.add_argument("--chunk", type=int, default=256 * 1024)
    ap.add_argument("--gunzip", action="store_true",
                    help="decompress after download (only if remote is .gz)")
    args = ap.parse_args()
    return fetch(args.url, Path(args.out), args.chunk, args.gunzip)


if __name__ == "__main__":
    sys.exit(main())
