"""AutoDL cross-cancer Visium download — single command run."""
import subprocess, os, sys, tarfile
from pathlib import Path

ROOT = Path("/root/autodl-tmp/project/project4_cervix_multimodal/data/st_visium")
TMP = ROOT / "_dl_tmp"
TMP.mkdir(parents=True, exist_ok=True)

def wget(url, dest, timeout=600):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1_000_000:
        print(f"  [skip] {dest.name} ({dest.stat().st_size/1e6:.1f} MB exists)")
        return True
    print(f"  [wget] {dest.name} ...", flush=True)
    r = subprocess.run(["wget", "-q", "--show-progress", "-O", str(dest), url],
                       capture_output=True, timeout=timeout)
    if r.returncode == 0 and dest.exists() and dest.stat().st_size > 1_000_000:
        print(f"  [ok] {dest.name} ({dest.stat().st_size/1e6:.1f} MB)")
        return True
    else:
        print(f"  [fail] {dest.name}: rc={r.returncode}")
        if dest.exists(): dest.unlink()
        return False

def extract(tar_path, dest_dir):
    if not tar_path.exists(): return 0
    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"  [extract] {tar_path.name} -> {dest_dir.name}/", flush=True)
    try:
        with tarfile.open(tar_path, 'r:*') as t:
            t.extractall(dest_dir)
    except Exception as e:
        print(f"  [extract-fail] {e}")
    h5s = list(dest_dir.rglob("filtered_feature_bc_matrix.h5"))
    print(f"  [done] {dest_dir.name}: {len(h5s)} h5 files")
    return len(h5s)

total_h5 = 0

# ============================================================
# 1. 10x Public Visium SD Breast FFPE (1 sample) — 最小最快
# ============================================================
print("\n=== [1/5] 10x Breast FFPE (Visium SD, 1 sample) ===")
d = ROOT / "10x_breast_ffpe"
B = "https://cf.10xgenomics.com/samples/spatial-exp/2.0.0/CytAssist_FFPE_Human_Breast_Cancer"
wget(f"{B}/CytAssist_FFPE_Human_Breast_Cancer_filtered_feature_bc_matrix.h5",
     d / "filtered_feature_bc_matrix.h5")
wget(f"{B}/CytAssist_FFPE_Human_Breast_Cancer_spatial.tar.gz",
     d / "spatial.tar.gz")
extract(d / "spatial.tar.gz", d / "spatial")
total_h5 += len(list(d.rglob("filtered_feature_bc_matrix.h5")))

# ============================================================
# 2. 10x Public Visium SD Breast Fresh Frozen (1 sample)
# ============================================================
print("\n=== [2/5] 10x Breast Fresh Frozen (Visium SD, 1 sample) ===")
d = ROOT / "10x_breast_ff"
B = "https://cf.10xgenomics.com/samples/spatial-exp/2.0.0/Visium_FF_Human_Breast_Cancer"
wget(f"{B}/Visium_FF_Human_Breast_Cancer_filtered_feature_bc_matrix.h5",
     d / "filtered_feature_bc_matrix.h5")
wget(f"{B}/Visium_FF_Human_Breast_Cancer_spatial.tar.gz",
     d / "spatial.tar.gz")
extract(d / "spatial.tar.gz", d / "spatial")
total_h5 += len(list(d.rglob("filtered_feature_bc_matrix.h5")))

# ============================================================
# 3. GEO GSE210616 — TNBC Breast (43 samples!) — 最大最值钱
# ============================================================
print("\n=== [3/5] GEO GSE210616 TNBC Breast (43 samples!) ===")
d = ROOT / "geo_breast_tnbc"
tar = TMP / "GSE210616_RAW.tar"
ok = wget("https://ftp.ncbi.nlm.nih.gov/geo/series/GSE210nnn/GSE210616/suppl/GSE210616_RAW.tar",
          tar, timeout=1800)
if ok:
    n = extract(tar, d)
    total_h5 += n

# ============================================================
# 4. GEO GSE183568 — Ovarian Cancer (5-6 samples)
# ============================================================
print("\n=== [4/5] GEO GSE183568 Ovarian Cancer ===")
d = ROOT / "geo_ovarian_2"
tar = TMP / "GSE183568_RAW.tar"
ok = wget("https://ftp.ncbi.nlm.nih.gov/geo/series/GSE183nnn/GSE183568/suppl/GSE183568_RAW.tar",
          tar, timeout=900)
if ok:
    n = extract(tar, d)
    total_h5 += n

# ============================================================
# 5. Dryad Prostate Visium SD (2 samples) — try multiple URLs
# ============================================================
print("\n=== [5/5] Dryad Prostate Visium ===")
d = ROOT / "dryad_prostate"
tar = TMP / "dryad_prostate.tar.gz"
for url in [
    "https://datadryad.org/stash/downloads/file_stream/4891612",
    "https://datadryad.org/api/v2/files/4891612/download",
]:
    ok = wget(url, tar, timeout=600)
    if ok:
        n = extract(tar, d)
        total_h5 += n
        break
else:
    print("  [skip] Dryad failed — manual download needed later")

# ============================================================
# FINAL SUMMARY
# ============================================================
print("\n" + "="*60)
print("DOWNLOAD COMPLETE")
print("="*60)
all_h5 = sorted(ROOT.rglob("filtered_feature_bc_matrix.h5"))
cervix = [h for h in all_h5 if any(k in str(h) for k in ["geo_ectocervix", "geo_cesc", "cervical_cancer"])]
colon = [h for h in all_h5 if "visium_hd_colon" in str(h)]
cross = [h for h in all_h5 if h not in cervix and h not in colon and "_dl_tmp" not in str(h)]

from collections import Counter
cc_counts = Counter()
for h in cross:
    parts = Path(h).parts
    # find the cross-cancer dir name
    for p in parts:
        if any(k in p.lower() for k in ["breast", "prostate", "ovarian", "lung", "colorectal", "10x", "dryad", "geo_"]):
            cc_counts[p] += 1
            break

print(f"\nTotal Visium h5 files: {len(all_h5)}")
print(f"  Cervical:       {len(cervix)}")
print(f"  Colon HD:       {len(colon)}")
print(f"  Cross-cancer:   {len(cross)}")
print("\nCross-cancer breakdown:")
for k, v in sorted(cc_counts.items(), key=lambda x: -x[1]):
    print(f"  {k:25s}: {v}")

print("\nAll cross-cancer h5 paths:")
for h in cross:
    print(f"  {h}")

print("\n" + "="*60)
print("Next: run FUNI-HPV on each new cross-cancer dir")
print("="*60)
print("""
python scripts/train_st.py --data data/st_visium/geo_breast_tnbc \\
    --exclude_substr geo_ectocervix,geo_cesc,cervical_cancer,visium_hd_colon \\
    --fm uni --device cuda --epochs 50 --permutation_n 10000 --run_id BREAST_TNBC

python scripts/train_st.py --data data/st_visium/10x_breast_ff --fm uni --device cuda --epochs 50 --permutation_n 10000 --run_id BREAST_FF
python scripts/train_st.py --data data/st_visium/10x_breast_ffpe --fm uni --device cuda --epochs 50 --permutation_n 10000 --run_id BREAST_FFPE
python scripts/train_st.py --data data/st_visium/geo_ovarian_2 --fm uni --device cuda --epochs 50 --permutation_n 10000 --run_id OVARIAN_GEO
python scripts/train_st.py --data data/st_visium/dryad_prostate --fm uni --device cuda --epochs 50 --permutation_n 10000 --run_id PROSTATE_DRYAD
""")
