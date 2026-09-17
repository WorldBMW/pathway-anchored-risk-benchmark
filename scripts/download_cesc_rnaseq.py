"""
download_cesc_rnaseq.py — Download TCGA-CESC gene expression matrix for the
cross-cohort HPV alignment (scripts/align_hpv.py Layer 2).

Source: UCSC Xena (public, no auth required).
  https://tcga.xenahubs.net/download/TCGA.CESC.sampleMap/HiSeqV2.gz
  -> RSEM normalized expression, rows = gene symbol, cols = TCGA-CESC samples.

Output: data/cesc/cesc_rnaseq.csv  (rows = genes, cols = TCGA-CESC sample_ids)

Note: GDC API returns STAR-Counts as controlled-access (403 without dbGaP
token), so we use Xena's open-access mirror instead.

Run:
  python scripts/download_cesc_rnaseq.py
"""
import requests
import pandas as pd
import numpy as np
from pathlib import Path
import gzip, shutil, sys

XENA_URL = "https://tcga.xenahubs.net/download/TCGA.CESC.sampleMap/HiSeqV2.gz"
OUT = Path("data/cesc")
OUT.mkdir(parents=True, exist_ok=True)
GZ = OUT / "_HiSeqV2.gz"
CSV = OUT / "cesc_rnaseq.csv"


def main():
    print(f"Downloading TCGA-CESC expression from Xena ({XENA_URL}) ...")
    with requests.get(XENA_URL, stream=True, timeout=600) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0))
        done = 0
        with open(GZ, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                if not chunk:
                    continue
                f.write(chunk)
                done += len(chunk)
                if total:
                    sys.stdout.write(f"\r  {done/1e6:.1f}/{total/1e6:.1f} MB")
                    sys.stdout.flush()
    print("\n  download complete, parsing ...")

    # Xena format: header row = sample ids, col0 = gene symbol, tab-separated
    df = pd.read_csv(GZ, sep="\t", index_col=0, compression="gzip")
    df.index.name = "gene"
    df.to_csv(CSV)
    print(f"Saved -> {CSV}  shape={df.shape}  (genes x samples)")
    # cleanup the large gz to save space
    GZ.unlink(missing_ok=True)
    print("Done. Layer 2 of align_hpv.py is now enabled.")


if __name__ == "__main__":
    main()
