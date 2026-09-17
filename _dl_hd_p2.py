import os, sys, tarfile, time
from pathlib import Path
sys.path.insert(0, "scripts")
from download_10x_st import extract_spatial

import requests

BASE_HD = "https://cf.10xgenomics.com/samples/spatial-exp/3.0.0"
DS_ID = "Visium_HD_Human_Colon_Cancer_P2"
NAME = "visium_hd_colon_p2"
OUT = Path("data") / "st_visium" / NAME
OUT.mkdir(parents=True, exist_ok=True)

MAX_RETRIES = 30
CONN_TIMEOUT = 60
CHUNK = 1 << 20


def remote_size(url, timeout=30):
    try:
        with requests.head(url, timeout=timeout, allow_redirects=True) as r:
            r.raise_for_status()
            return int(r.headers.get("Content-Length", 0))
    except Exception as e:
        print(f"  [head warn] {e}", flush=True)
        return 0


def is_complete(dest, rsize):
    if not dest.exists():
        return False
    local = dest.stat().st_size
    if rsize and abs(local - rsize) < 1_000_000:
        return True
    return False


def stream_download(url, dest, rsize):
    """Resume-capable download with auto-retry on network errors."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            existing = dest.stat().st_size if dest.exists() else 0
            headers = {}
            if existing > 0:
                headers["Range"] = f"bytes={existing}-"
            with requests.get(url, headers=headers, stream=True, timeout=CONN_TIMEOUT) as r:
                r.raise_for_status()
                mode = "ab" if r.status_code == 206 else "wb"
                total = int(r.headers.get("Content-Length", 0)) + (existing if mode == "ab" else 0)
                with open(dest, mode) as fh:
                    got = existing if mode == "ab" else 0
                    t0 = time.time()
                    for cb in r.iter_content(CHUNK):
                        if not cb:
                            continue
                        fh.write(cb)
                        got += len(cb)
                        if time.time() - t0 > 20:
                            t0 = time.time()
                            pct = f"{100*got/total:.0f}%" if total else "?"
                            print(f"  {dest.name}: {got/1e6:.0f}/{total/1e6:.0f} MB ({pct})", flush=True)
            if is_complete(dest, rsize):
                return True
            # partial write finished without error but size mismatch -> server closed early; retry resumes
            print(f"  [partial] {dest.name} {dest.stat().st_size/1e6:.0f}MB, retrying ({attempt}/{MAX_RETRIES})", flush=True)
        except Exception as e:
            print(f"  [error] {e} (attempt {attempt}/{MAX_RETRIES})", flush=True)
            time.sleep(10)
    return is_complete(dest, rsize)


prefix = f"{DS_ID}/{DS_ID}"
for f in ("spatial.tar.gz", "binned_outputs.tar.gz"):
    url = f"{BASE_HD}/{prefix}_{f}"
    dest = OUT / f
    rsize = remote_size(url)
    if is_complete(dest, rsize):
        print(f"[skip complete] {f} ({dest.stat().st_size/1e6:.0f}/{rsize/1e6:.0f} MB)", flush=True)
        ok = True
    else:
        if dest.exists():
            print(f"[incomplete {dest.stat().st_size/1e6:.0f}MB vs {rsize/1e6:.0f}MB] will resume/redownload {f}", flush=True)
        t0 = time.time()
        print(f"[start] {f}", flush=True)
        ok = stream_download(url, dest, rsize)
        print(f"[{'ok' if ok else 'FAIL'}] {f}  ({time.time()-t0:.0f}s)", flush=True)
    if ok and f.endswith(".tar.gz"):
        extract_spatial(OUT, f)
print("P2 download finished.", flush=True)
