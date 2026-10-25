"""Download cross-cancer Visium ST datasets for FUNI-HPV cross-cohort validation.

Priority order (fastest -> slowest):
  1. Zenodo Spatial Hallmarks (26 sections, 6 cancer types) — ONE archive, huge coverage
     https://zenodo.org/records/14044964
  2. GEO breast cancer Visium datasets
  3. GEO ovarian / prostate / lung / colorectal Visium datasets

AutoDL usage (run on AutoDL GPU machine):
  cd /root/autodl-tmp/project/project4_cervix_multimodal
  pip install requests wget
  python scripts/download_cross_cohort.py --all
"""
import argparse
import os
import subprocess
import tarfile
import zipfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "st_visium"
OUT.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# 1. Zenodo Spatial Hallmarks — 26 Visium sections, 6 cancer types
#    breast, colorectal, glioblastoma, lung, ovarian, prostate
#    Reference: "Spatial Hallmarks" collection @ Zenodo
# ------------------------------------------------------------
ZENODO_URL = "https://zenodo.org/records/14044964/files/spatial_hallmarks_visium.tar.gz"
ZENODO_ARCHIVE = OUT / "_dl_tmp" / "spatial_hallmarks_visium.tar.gz"

# ------------------------------------------------------------
# 2. GEO Visium datasets — supplementary, higher-quality but slower
#    Each entry: (GEO accession, display_name, notes)
# ------------------------------------------------------------
GEO_VISIUM_DATASETS = [
    # Breast cancer
    ("GSE176078", "breast_GSE176078", "8 breast tumor sections"),
    ("GSE225600", "breast_GSE225600", "4 primary tumor + 4 paired LN Visium"),
    ("GSE218951", "breast_GSE218951", "Starfysh breast Visium"),
    # Ovarian cancer
    ("GSE183568", "ovarian_GSE183568", "6 ovarian cancer sections"),
    # Prostate cancer
    ("GSE212760", "prostate_GSE212760", "5 prostate adenocarcinoma"),
    # Colorectal cancer
    ("GSE160269", "colorectal_GSE160269", "4 CRC sections"),
    # Lung cancer
    ("GSE192912", "lung_GSE192912", "4 NSCLC sections"),
]


def _download(url: str, dest: Path) -> None:
    """Streaming download with progress bar."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1_000_000:
        print(f"  [skip] {dest.name} already exists ({dest.stat().st_size/1e6:.1f} MB)")
        return
    print(f"  [download] {url[:80]}... -> {dest.name}")
    try:
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = 100 * downloaded // total
                        print(f"\r    {pct}% ({downloaded/1e6:.1f}/{total/1e6:.1f} MB)", end="", flush=True)
        print()
        if total > 0 and abs(dest.stat().st_size - total) > 1024:
            raise RuntimeError(f"Size mismatch: expected {total}, got {dest.stat().st_size}")
    except Exception as e:
        print(f"  [error] download failed: {e}")
        if dest.exists():
            dest.unlink()


def _extract_tar(archive: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"  [extract] {archive.name} -> {dest_dir.name}/")
    try:
        with tarfile.open(archive) as t:
            t.extractall(dest_dir)
        print(f"  [done] extracted {archive.name}")
    except Exception as e:
        print(f"  [warn] tar extract failed ({e}); trying zip...")
        try:
            with zipfile.ZipFile(archive) as z:
                z.extractall(dest_dir)
        except Exception as e2:
            print(f"  [error] both tar and zip failed: {e2}")


def download_zenodo_spatial_hallmarks() -> None:
    """Download Zenodo Spatial Hallmarks — 26 Visium sections pan-cancer."""
    print("\n" + "=" * 60)
    print("1. Zenodo Spatial Hallmarks (26 sections, 6 cancer types)")
    print("=" * 60)
    _dl_tmp = OUT / "_dl_tmp"
    _dl_tmp.mkdir(parents=True, exist_ok=True)

    # Try to get the Zenodo file URL directly (it's usually served via a redirect)
    # We need the actual file URL. Zenodo record 14044964 has spatial_hallmarks_visium.tar.gz
    zenodo_direct = "https://zenodo.org/records/14044964/files/spatial_hallmarks_visium.tar.gz?download=1"
    print(f"  Source: Zenodo https://zenodo.org/records/14044964")
    print(f"  Note: if this fails, try wget or curl manually:")
    print(f"    wget -O data/st_visium/_dl_tmp/spatial_hallmarks_visium.tar.gz '{zenodo_direct}'")

    _download(zenodo_direct, ZENODO_ARCHIVE)
    if ZENODO_ARCHIVE.exists() and ZENODO_ARCHIVE.stat().st_size > 1_000_000:
        _extract_tar(ZENODO_ARCHIVE, OUT / "zenodo_spatial_hallmarks")


def download_geo(accession: str, dest_name: str, note: str = "") -> None:
    """Download supplementary Visium data from a GEO Series.

    GEO Series usually provides tar.gz archives in the /suppl/ directory.
    We try the common URL patterns and fall back to wget.
    """
    geo_dir = OUT / dest_name
    if geo_dir.exists() and any(geo_dir.iterdir()):
        print(f"  [skip] {dest_name} already has files")
        return
    print(f"\n  GEO {accession}: {dest_name} ({note})")
    geo_dir.mkdir(parents=True, exist_ok=True)

    # GEO FTP pattern: ftp.ncbi.nlm.nih.gov/geo/series/GSEXXnnn/GSEXXX/suppl/
    # Files are usually .tar.gz or .zip
    prefix = accession[:-3] + "nnn"  # e.g. GSE176 -> GSE176nnn
    base = f"https://ftp.ncbi.nlm.nih.gov/geo/series/{prefix}/{accession}/suppl/"

    # Try to find the supplementary tarball — common naming patterns
    for fname in [f"{accession}_RAW.tar", f"{accession}_suppl.tar.gz", f"{accession}.tar.gz",
                  f"{accession}_files.tar.gz"]:
        url = base + fname
        dest = geo_dir / fname
        r = requests.head(url, timeout=10, allow_redirects=True)
        if r.status_code == 200 and int(r.headers.get("content-length", 0)) > 1_000_000:
            print(f"  Found: {fname} ({int(r.headers['content-length'])/1e6:.0f} MB)")
            _download(url, dest)
            _extract_tar(dest, geo_dir)
            return

    # Fallback: use GEOparse or print manual instructions
    print(f"  [warn] No standard tarball found for {accession}")
    print(f"  Manual: visit https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={accession}")
    print(f"    → Supplementary files → download tar.gz → extract to {geo_dir}/")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zenodo", action="store_true", help="Download Zenodo Spatial Hallmarks only")
    ap.add_argument("--geo", action="store_true", help="Download GEO supplementary datasets only")
    ap.add_argument("--all", action="store_true", help="Download everything (Zenodo + GEO)")
    ap.add_argument("--dry_run", action="store_true", help="Print what would be downloaded, don't download")
    args = ap.parse_args()

    if not (args.zenodo or args.geo or args.all):
        args.all = True  # default = all

    print(f"Output directory: {OUT}")
    print(f"Download mode: {'all' if args.all else 'zenodo' if args.zenodo else 'geo'}")

    if args.all or args.zenodo:
        if args.dry_run:
            print(f"\n[DRY-RUN] Would download Zenodo Spatial Hallmarks from {ZENODO_URL[:60]}...")
        else:
            download_zenodo_spatial_hallmarks()

    if args.all or args.geo:
        print("\n" + "=" * 60)
        print("2. GEO Visium supplementary datasets")
        print("=" * 60)
        if args.dry_run:
            for acc, name, note in GEO_VISIUM_DATASETS:
                print(f"  [DRY-RUN] {acc} -> {name}/ ({note})")
        else:
            for acc, name, note in GEO_VISIUM_DATASETS:
                try:
                    download_geo(acc, name, note)
                except Exception as e:
                    print(f"  [error] {acc}: {e}")

    print("\n" + "=" * 60)
    print("Download complete. Summary of cross-cancer data dirs:")
    print("=" * 60)
    for d in sorted(OUT.iterdir()):
        if d.is_dir():
            files = list(d.rglob("*.h5")) + list(d.rglob("filtered_feature_bc_matrix.h5"))
            if files or "cross" in d.name.lower() or "zenodo" in d.name.lower() or any(
                k in d.name.lower() for k in ["breast", "ovarian", "prostate", "lung", "colorectal"]
            ):
                print(f"  {d.name}/  ({len(list(d.rglob('*')))} entries)")

    print("\nNext step (after download + extraction):")
    print("  # Run FUNI-HPV on each cross-cancer sample dir")
    print("  python scripts/train_st.py --data data/st_visium/breast_sample1 ...")
    print("  # The discovery logic auto-finds each Visium sample dir with h5 + spatial/")


if __name__ == "__main__":
    main()
