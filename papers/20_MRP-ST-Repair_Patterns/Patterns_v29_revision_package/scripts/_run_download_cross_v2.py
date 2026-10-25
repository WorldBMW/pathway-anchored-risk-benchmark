"""Fixed cross-cancer download — uses GEO series-level RAW.tar."""
import urllib.request, os, tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "data" / "st_visium"
TMP = ROOT / "_dl_tmp"
TMP.mkdir(parents=True, exist_ok=True)

def download(url, dest):
    if dest.exists() and dest.stat().st_size > 1_000_000:
        print(f"  [skip] {dest.name} ({dest.stat().st_size/1e6:.1f} MB exists)")
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  [download] {dest.name} ...", flush=True)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = resp.read()
        dest.write_bytes(data)
        print(f"  [done] {dest.name} ({len(data)/1e6:.1f} MB)")
        return True
    except Exception as e:
        print(f"  [fail] {dest.name}: {e}")
        return False

def extract_tar(archive, dest_dir):
    if not archive.exists(): return
    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"  [extract] {archive.name} -> {dest_dir.name}/", flush=True)
    try:
        with tarfile.open(archive, 'r:gz') as t:
            t.extractall(dest_dir, filter='data')
    except:
        try:
            with tarfile.open(archive, 'r:') as t:
                t.extractall(dest_dir, filter='data')
        except Exception as e:
            print(f"  [extract-fail] {e}")
    h5s = list(dest_dir.rglob("filtered_feature_bc_matrix.h5"))
    print(f"  [done] {dest_dir.name}: {len(h5s)} h5 files found")

# ============ 10x FFPE Breast (already done above — verify) ============
print("\n=== 10x Public Visium (already done or doing now) ===")
d = ROOT / "10x_breast_ffpe"
h5_ffpe = list(d.glob("filtered_feature_bc_matrix.h5"))
if h5_ffpe:
    print(f"  10x_breast_ffpe: OK ({len(h5_ffpe)} h5)")
else:
    # retry
    download("https://cf.10xgenomics.com/samples/spatial-exp/2.0.0/CytAssist_FFPE_Human_Breast_Cancer/CytAssist_FFPE_Human_Breast_Cancer_filtered_feature_bc_matrix.h5",
             d / "filtered_feature_bc_matrix.h5")
    download("https://cf.10xgenomics.com/samples/spatial-exp/2.0.0/CytAssist_FFPE_Human_Breast_Cancer/CytAssist_FFPE_Human_Breast_Cancer_spatial.tar.gz",
             d / "spatial.tar.gz")
    extract_tar(d / "spatial.tar.gz", d / "spatial")

# ============ GEO GSE210616 — TNBC Breast (43 samples!) ============
print("\n=== GEO GSE210616 TNBC Breast (43 samples) ===")
out_dir = ROOT / "geo_breast_tnbc"
tar_path = TMP / "GSE210616_RAW.tar"
download("https://ftp.ncbi.nlm.nih.gov/geo/series/GSE210nnn/GSE210616/suppl/GSE210616_RAW.tar", tar_path)
extract_tar(tar_path, out_dir)

# ============ GEO GSE252176 — TNBC Breast v2 (4 sections) ============
print("\n=== GEO GSE252176 TNBC Breast v2 ===")
out_dir = ROOT / "geo_breast_tnbc_v2"
tar_path = TMP / "GSE252176_RAW.tar"
download("https://ftp.ncbi.nlm.nih.gov/geo/series/GSE252nnn/GSE252176/suppl/GSE252176_RAW.tar", tar_path)
extract_tar(tar_path, out_dir)

# ============ GEO GSE192912 — NSCLC Lung Visium ============
print("\n=== GEO GSE192912 NSCLC Lung ===")
out_dir = ROOT / "geo_lung_nsclc"
tar_path = TMP / "GSE192912_RAW.tar"
download("https://ftp.ncbi.nlm.nih.gov/geo/series/GSE192nnn/GSE192912/suppl/GSE192912_RAW.tar", tar_path)
extract_tar(tar_path, out_dir)

# ============ GEO GSE183568 — Ovarian Cancer ============
print("\n=== GEO GSE183568 Ovarian ===")
out_dir = ROOT / "geo_ovarian_2"
tar_path = TMP / "GSE183568_RAW.tar"
download("https://ftp.ncbi.nlm.nih.gov/geo/series/GSE183nnn/GSE183568/suppl/GSE183568_RAW.tar", tar_path)
extract_tar(tar_path, out_dir)

# ============ Dryad Prostate (correct URL) ============
print("\n=== Dryad Prostate Visium ===")
out_dir = ROOT / "dryad_prostate"
tar_path = TMP / "dryad_prostate.tar.gz"
# Try the doi landing page to find actual download URL
for trial_url in [
    "https://datadryad.org/stash/downloads/file_stream/4891612",
    "https://datadryad.org/api/v2/files/4891612/download",
]:
    ok = download(trial_url, tar_path)
    if ok and tar_path.exists() and tar_path.stat().st_size > 1_000_000:
        extract_tar(tar_path, out_dir)
        break
    else:
        if tar_path.exists(): tar_path.unlink()
else:
    print("  Dryad failed — will need manual download from https://datadryad.org/stash/dataset/doi:10.5061/dryad.0cfxpnwhc")

# ============ 10x Prostate Public ============
print("\n=== 10x Public Prostate ===")
# Try known 10x URLs
prostate_urls = [
    ("https://cf.10xgenomics.com/samples/spatial-exp/1.1.0/Visium_FFPE_Human_Prostate/Visium_FFPE_Human_Prostate_filtered_feature_bc_matrix.h5",
     ROOT / "10x_prostate_ffpe" / "filtered_feature_bc_matrix.h5"),
]
for url, dest in prostate_urls:
    download(url, dest)

# ============ Summary ============
print("\n" + "="*60)
print("FINAL SUMMARY")
print("="*60)
all_h5 = sorted(ROOT.rglob("filtered_feature_bc_matrix.h5"))
cervix = [h for h in all_h5 if any(k in str(h) for k in ["geo_ectocervix", "geo_cesc", "cervical_cancer"])]
colon = [h for h in all_h5 if "visium_hd_colon" in str(h)]
cross = [h for h in all_h5 if h not in cervix and h not in colon and "_dl_tmp" not in str(h)]

print(f"\nTotal Visium h5: {len(all_h5)}")
print(f"  Cervical:       {len(cervix)}")
print(f"  Colon HD:       {len(colon)}")  
print(f"  Cross-cancer:   {len(cross)}")

print("\nCross-cancer breakdown by dir:")
from collections import Counter
cc_counts = Counter()
for h in cross:
    parent = Path(h).parent.parent.name
    cc_counts[parent] += 1
for k, v in sorted(cc_counts.items(), key=lambda x: -x[1]):
    print(f"  {k:25s}: {v} samples")

print("\nCross-cancer h5 paths:")
for h in cross:
    print(f"  {h}")
