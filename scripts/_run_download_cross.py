"""Actual download script — run this on Windows or AutoDL."""
import urllib.request, os, sys, gzip, tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "data" / "st_visium"
TMP = ROOT / "_dl_tmp"
TMP.mkdir(parents=True, exist_ok=True)

def download(url, dest, skip_if_exists=True):
    if skip_if_exists and dest.exists() and dest.stat().st_size > 1_000_000:
        print(f"  [skip] {dest.name} ({dest.stat().st_size/1e6:.1f} MB exists)")
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  [download] {url.split('/')[-1]} ...", flush=True)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=120) as resp:
            total = int(resp.headers.get('content-length', 0))
            data = resp.read()
        dest.write_bytes(data)
        size_mb = len(data)/1e6
        print(f"  [done] {dest.name} ({size_mb:.1f} MB)")
        return True
    except Exception as e:
        print(f"  [fail] {dest.name}: {e}")
        return False

def extract_targz(archive, dest_dir):
    if not archive.exists(): return False
    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"  [extract] {archive.name} -> {dest_dir.name}/", flush=True)
    try:
        with tarfile.open(archive, 'r:gz') as t:
            t.extractall(dest_dir)
        print(f"  [done] extracted")
        return True
    except Exception as e:
        try:
            with tarfile.open(archive, 'r:') as t:
                t.extractall(dest_dir)
            return True
        except Exception as e2:
            print(f"  [fail] extract: {e2}")
            return False

def gunzip_file(gz_path):
    try:
        with gzip.open(gz_path, 'rb') as gz:
            data = gz.read()
        out = gz_path.with_suffix('')
        out.write_bytes(data)
        gz_path.unlink()
        return True
    except: return False

# ============ PHASE 1: 10x Genomics Public Visium ============
print("\n=== Phase 1: 10x Public Visium Breast ===")

# 1A. CytAssist FFPE Breast Cancer (Visium SD)
d = ROOT / "10x_breast_ffpe"
files_1a = {
    "CytAssist_FFPE_Human_Breast_Cancer_filtered_feature_bc_matrix.h5":
        "https://cf.10xgenomics.com/samples/spatial-exp/2.0.0/CytAssist_FFPE_Human_Breast_Cancer/CytAssist_FFPE_Human_Breast_Cancer_filtered_feature_bc_matrix.h5",
    "CytAssist_FFPE_Human_Breast_Cancer_raw_feature_bc_matrix.h5":
        "https://cf.10xgenomics.com/samples/spatial-exp/2.0.0/CytAssist_FFPE_Human_Breast_Cancer/CytAssist_FFPE_Human_Breast_Cancer_raw_feature_bc_matrix.h5",
    "CytAssist_FFPE_Human_Breast_Cancer_spatial.tar.gz":
        "https://cf.10xgenomics.com/samples/spatial-exp/2.0.0/CytAssist_FFPE_Human_Breast_Cancer/CytAssist_FFPE_Human_Breast_Cancer_spatial.tar.gz",
}
for fname, url in files_1a.items():
    download(url, d / fname)
s = d / "CytAssist_FFPE_Human_Breast_Cancer_spatial.tar.gz"
if s.exists(): extract_targz(s, d)

# 1B. Visium FF Breast Cancer
d = ROOT / "10x_breast_ff"
BASE = "https://cf.10xgenomics.com/samples/spatial-exp/2.0.0/Visium_FF_Human_Breast_Cancer"
for fname in ["Visium_FF_Human_Breast_Cancer_filtered_feature_bc_matrix.h5",
              "Visium_FF_Human_Breast_Cancer_spatial.tar.gz",
              "Visium_FF_Human_Breast_Cancer_tissue_image.tif"]:
    download(f"{BASE}/{fname}", d / fname)
s = d / "Visium_FF_Human_Breast_Cancer_spatial.tar.gz"
if s.exists(): extract_targz(s, d)

# ============ PHASE 2: GEO GSE210616 — TNBC Breast (5 samples) ============
print("\n=== Phase 2: GEO GSE210616 TNBC Breast ===")
geo_samples = [
    ("GSM6433585", "P9_sec1"),
    ("GSM6433589", "P12_sec1"),  
    ("GSM6433593", "P14_sec1"),
    ("GSM6433597", "P1_sec1"),
    ("GSM6433601", "P3_sec1"),
]
for gsm, label in geo_samples:
    gsm_num = gsm[3:]
    prefix = gsm_num[:5] + "nnn"
    base = f"https://ftp.ncbi.nlm.nih.gov/geo/samples/{prefix}/{gsm}/suppl"
    dest = ROOT / "geo_breast_tnbc" / label
    print(f"\n  [{gsm}] {label}")
    for f in [f"{gsm}_filtered_feature_bc_matrix.h5",
              f"{gsm}_scalefactors_json.json.gz",
              f"{gsm}_tissue_hires_image.png.gz",
              f"{gsm}_tissue_positions_list.csv.gz"]:
        ok = download(f"{base}/{f}", dest / f, skip_if_exists=True)
        if ok and f.endswith('.gz'):
            gunzip_file(dest / f)

# ============ PHASE 3: GEO GSE252176 — TNBC Breast v2 (4 sections) ============
print("\n=== Phase 3: GEO GSE252176 TNBC Breast v2 ===")
geo_v2 = ["GSM7996201", "GSM7996202", "GSM7996203", "GSM7996204"]
for gsm in geo_v2:
    gsm_num = gsm[3:]
    prefix = gsm_num[:5] + "nnn"
    base = f"https://ftp.ncbi.nlm.nih.gov/geo/samples/{prefix}/{gsm}/suppl"
    dest = ROOT / "geo_breast_tnbc_v2" / gsm
    print(f"\n  [{gsm}]")
    for f in [f"{gsm}_filtered_feature_bc_matrix.h5",
              f"{gsm}_scalefactors_json.json.gz",
              f"{gsm}_tissue_hires_image.png.gz",
              f"{gsm}_tissue_positions_list.csv.gz"]:
        ok = download(f"{base}/{f}", dest / f, skip_if_exists=True)
        if ok and f.endswith('.gz'):
            gunzip_file(dest / f)

# ============ PHASE 4: Dryad Prostate Visium (2 samples) ============
print("\n=== Phase 4: Dryad Prostate ===")
d = ROOT / "dryad_prostate"
download("https://datadryad.org/downloads/file_stream/4891612",
         TMP / "dryad_prostate.tar.gz")
s = TMP / "dryad_prostate.tar.gz"
if s.exists() and s.stat().st_size > 1_000_000:
    extract_targz(s, d)
    found = list(d.rglob("filtered_feature_bc_matrix.h5"))
    print(f"  Prostate h5 files found: {len(found)}")
    for f in found: print(f"    {f}")

# ============ Summary ============
print("\n" + "="*60)
print("DOWNLOAD COMPLETE — Summary")
print("="*60)

all_h5 = list(ROOT.rglob("filtered_feature_bc_matrix.h5"))
cross = [h for h in all_h5 if not any(k in str(h) for k in ["geo_ectocervix", "geo_cesc", "cervical_cancer", "visium_hd_colon", "_dl_tmp"])]
cervix = [h for h in all_h5 if any(k in str(h) for k in ["geo_ectocervix", "geo_cesc", "cervical_cancer"])]
colon = [h for h in all_h5 if "visium_hd_colon" in str(h)]

print(f"\nTotal Visium h5 files: {len(all_h5)}")
print(f"  Cervical:     {len(cervix)}")
print(f"  Cross-cancer: {len(cross)}")
print(f"  Colon HD:     {len(colon)}")

print("\nCross-cancer files:")
for h in sorted(cross):
    p = Path(h)
    print(f"  {h}")

print("\nNext step (on AutoDL or Windows):")
print("  # Run FUNI-HPV on each new cross-cancer dir")
print("  python scripts/train_st.py --data data/st_visium/geo_breast_tnbc ... --run_id BREAST_TNBC")
print("  python scripts/train_st.py --data data/st_visium/dryad_prostate ... --run_id PROSTATE_DRYAD")
print("  # ... etc")
