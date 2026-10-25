"""Download 10x Visium spatial-transcriptomics datasets (ST + matched H&E).

Each 10x Visium sample is a SINGLE tissue section: the spatial gene-expression
matrix (spots) and the H&E whole-slide image come from the SAME slide of the
SAME patient -> perfectly paired, no cross-cohort stitching. This is the
rigorous foundation for the multimodal (ST + pathology) fusion study.

We download the files needed for fusion per sample:
  Standard Visium (55um):
    - filtered_feature_bc_matrix.h5  (spot x gene expression)
    - spatial.tar.gz                 (tissue_hires_image.png + scalefactors + spot coords)
  Visium HD (subcellular, 2/8um bins) -- the 2025 high-resolution platform:
    - spatial.tar.gz                 (tissue_hires_image.png + aligned images)
    - binned_outputs.tar.gz          (square_008um/: h5 + tissue_positions.parquet + scalefactors)
  NOTE: HD data lives under spatial-exp/3.0.0 and uses binned_outputs.tar.gz
  (not a standalone filtered_feature_bc_matrix.h5). st_data.py auto-detects both.
"""
import os
import tarfile
import zipfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "st_visium"
OUT.mkdir(parents=True, exist_ok=True)

# Standard Visium (55um) -- path 1.3.0
BASE_STD = "https://cf.10xgenomics.com/samples/spatial-exp/1.3.0"
# Visium HD (subcellular) -- path 3.0.0
BASE_HD = "https://cf.10xgenomics.com/samples/spatial-exp/3.0.0"

# (dataset_id, display_name) -- standard Visium, downloadable on 1.3.0.
DATASETS_STD = [
    ("Visium_FFPE_Human_Cervical_Cancer", "cervical_cancer_1"),
    ("Visium_FFPE_Human_Breast_Cancer", "breast_cancer_1"),
    ("Visium_FFPE_Human_Ovarian_Cancer", "ovarian_cancer_1"),
    ("Visium_FFPE_Human_Prostate_Cancer", "prostate_cancer_1"),
]

# Visium HD samples (subcellular resolution) -- verified downloadable on 3.0.0.
# Colon HD P1/P2 are confirmed public; add more as needed.
DATASETS_HD = [
    ("Visium_HD_Human_Colon_Cancer_P1", "visium_hd_colon_p1"),
    ("Visium_HD_Human_Colon_Cancer_P2", "visium_hd_colon_p2"),
]

NEED_STD = [
    "filtered_feature_bc_matrix.h5",
    "spatial.tar.gz",
    "image.jpg",
]

NEED_HD = [
    "spatial.tar.gz",
    "binned_outputs.tar.gz",
]


def download(url, dest):
    # Download straight into dest (no .part temp) to avoid the Windows
    # "file in use" (WinError 32) rename clash caused by AV real-time scan
    # locking the .part file. If a partial dest exists we resume by restart.
    if dest.exists() and dest.stat().st_size > 0:
        return True
    # remove any stale .part left from a previous interrupted run
    part = dest.with_suffix(dest.suffix + ".part")
    if part.exists():
        try:
            part.unlink()
        except OSError:
            pass
    r = requests.get(url, stream=True, timeout=600)
    if r.status_code != 200:
        print(f"  [FAIL {r.status_code}] {url}")
        return False
    with open(dest, "wb") as f:
        for chunk in r.iter_content(1 << 20):
            f.write(chunk)
    return dest.exists() and dest.stat().st_size > 0


def extract_spatial(sample_dir, tar_name):
    tar = sample_dir / tar_name
    if tar.exists():
        with tarfile.open(tar) as t:
            t.extractall(sample_dir)
        print(f"  extracted {tar_name}")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["std", "hd", "both"], default="std",
                    help="std=55um Visium, hd=Visium HD, both=all")
    args = ap.parse_args()

    if args.mode in ("std", "both"):
        for ds_id, name in DATASETS_STD:
            sdir = OUT / name
            sdir.mkdir(parents=True, exist_ok=True)
            prefix = f"{ds_id}/{ds_id}"
            print(f"== {name} ({ds_id}) ==")
            for f in NEED_STD:
                url = f"{BASE_STD}/{prefix}_{f}"
                dest = sdir / f
                ok = download(url, dest)
                print(f"  {'[ok]' if ok else '[FAIL]'} {f}")
            extract_spatial(sdir, "spatial.tar.gz")

    if args.mode in ("hd", "both"):
        for ds_id, name in DATASETS_HD:
            sdir = OUT / name
            sdir.mkdir(parents=True, exist_ok=True)
            prefix = f"{ds_id}/{ds_id}"
            print(f"== {name} (HD, {ds_id}) ==")
            for f in NEED_HD:
                url = f"{BASE_HD}/{prefix}_{f}"
                dest = sdir / f
                ok = download(url, dest)
                print(f"  {'[ok]' if ok else '[FAIL]'} {f}")
            extract_spatial(sdir, "spatial.tar.gz")
            extract_spatial(sdir, "binned_outputs.tar.gz")
    print("DONE ->", OUT.resolve())


if __name__ == "__main__":
    main()
