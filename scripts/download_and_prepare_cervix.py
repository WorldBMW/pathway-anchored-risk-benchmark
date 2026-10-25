"""Download GSE208654 RAW tar (if missing) + optionally GSE217237 ectocervix
Visium sections (11 normal-control slices), and consolidate cervical Visium
samples into one directory for co-training.

What it does (deterministic, never falls back to synthetic data)
----------------------------------------------------------------
1. Validate the 4 samples already under data/st_visium/geo_cesc/ are intact,
   otherwise download GSE208654_RAW.tar, extract, and repopulate.
2. Optionally download GSE217237_RAW.tar and assemble 11 ectocervix Visium
   sections (Karolinska cohort, HIV+/DMPA users' normal ectocervical mucosa)
   into data/st_visium/geo_ectocervix/ with 10x-compliant folders.
3. Create data/st_visium/cervix_all/ with 5 subdirs (4 geo_cesc +
   cervical_cancer_1) via Windows junction / copy so the user can run
   `--data data/st_visium/cervix_all`.
4. If --with-ectocervix is passed, additionally create
   data/st_visium/cervix_all_ext/ that contains the 5 core samples + all 11
   ectocervix normal samples (total n=16).
5. Print a manual-download checklist if NCBI HTTP cannot be reached.

Usage
-----
  python scripts/download_and_prepare_cervix.py                     # 5 samples
  python scripts/download_and_prepare_cervix.py --with-ectocervix   # 5 + 11 = 16
"""
from __future__ import annotations
import argparse
import csv
import gzip
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "st_visium"
LABELS_DIR = DATA / "labels"
GEO_DIR = DATA / "geo_cesc"
ECTO_DIR = DATA / "geo_ectocervix"
ALL_DIR = DATA / "cervix_all"
EXT_DIR = DATA / "cervix_all_ext"
CERV1 = DATA / "cervical_cancer_1"

GSE_NAME = "GSE208654"
RAW_URL = "https://www.ncbi.nlm.nih.gov/geo/download/?acc=GSE208654&format=file"
EXPECTED_RAW_SIZE_MB = 222

# GSE217237: SuperSeries that contains GSE290350 (ectocervix Visium).
# The RAW.tar contains per-sample gzipped inner tars named like
#   GSM8811056_P004.tar.gz
#   GSM9044528_P031.tar.gz
#   GSM9053839_P020.tar.gz
# for a total of 30 HIV+/DMPA ectocervical mucosa Visium samples.
# Each inner tar.gz holds the 10x Space Ranger outputs (matrix + spatial).
ECTO_GSE = "GSE217237"
ECTO_RAW_URL = f"https://www.ncbi.nlm.nih.gov/geo/download/?acc={ECTO_GSE}&format=file"
ECTO_EXPECTED_MB = 722
# 30 ectocervix samples actually present in GSE217237_RAW.tar (verified 2026-08).
# Format: "GSM<PREFIX>" prefix used to match outer-tar member
#         `GSM<PREFIX>.tar.gz`; the inner sample is stored as `{PREFIX}`.
ECTO_ST_SAMPLES = [
    # Series 1: GSM8811056–GSM8811065 (Karolinska P004…P047, 10 samples)
    "GSM8811056_P004", "GSM8811057_P008", "GSM8811058_P026",
    "GSM8811059_P044", "GSM8811060_P067", "GSM8811061_P007",
    "GSM8811062_P016", "GSM8811063_P023", "GSM8811064_P028",
    "GSM8811065_P047",
    # Series 2: GSM9044528–GSM9044535 (P031…P118, 8 samples)
    "GSM9044528_P031", "GSM9044529_P080", "GSM9044530_P097",
    "GSM9044531_P105", "GSM9044532_P107", "GSM9044533_P108",
    "GSM9044534_P114", "GSM9044535_P118",
    # Series 3: GSM9053839–GSM9053850 (P020…P117, 12 samples)
    "GSM9053839_P020", "GSM9053840_P045", "GSM9053841_P050",
    "GSM9053842_P057", "GSM9053843_P001", "GSM9053844_P014",
    "GSM9053845_P018", "GSM9053846_P087", "GSM9053847_P021",
    "GSM9053848_P024", "GSM9053849_P081", "GSM9053850_P117",
]
_ECTO_PREFIX_TO_LOCAL = {p: p.split("_", 1)[1] for p in ECTO_ST_SAMPLES}
# Expect total 30 ecto samples; N of them may be Visium ST / others Xenium,
# but the script assembles only Visium-compliant folders.

GSM_TO_LOCAL = {
    "GSM6360689": ("N_HPV",    "N"),
    "GSM6360690": ("HSIL_HPV", "HSIL"),
    "GSM6360691": ("CA_HPV_1", "SCC"),
    "GSM6360692": ("CA_HPV_2", "ADC"),
}

REQUIRED_FILES = [
    Path("filtered_feature_bc_matrix.h5"),
    Path("spatial") / "scalefactors_json.json",
    Path("spatial") / "tissue_hires_image.png",
    Path("spatial") / "tissue_positions_list.csv",
]
ECTO_REQUIRED_MIN = [
    # GSE290350 Visium samples often come with tissue_positions.csv (newer
    # 10x naming) in addition to tissue_positions_list.csv. Accept either.
    Path("filtered_feature_bc_matrix.h5"),
    Path("spatial") / "scalefactors_json.json",
    Path("spatial") / "tissue_hires_image.png",
]


def sample_intact(sample_dir: Path, require_positions: bool = True) -> bool:
    base_ok = all((sample_dir / f).exists() and (sample_dir / f).stat().st_size > 0
                  for f in REQUIRED_FILES if f.name != "tissue_positions_list.csv" or require_positions)
    if not require_positions:
        for req in ECTO_REQUIRED_MIN:
            if not (sample_dir / req).exists() or (sample_dir / req).stat().st_size == 0:
                return False
        # accept either tissue_positions_list.csv OR tissue_positions.csv
        positions_ok = (
            (sample_dir / "spatial" / "tissue_positions_list.csv").exists() or
            (sample_dir / "spatial" / "tissue_positions.csv").exists()
        )
        return positions_ok
    return base_ok


def download_http(url: str, dst: Path, label: str) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".part")
    try:
        print(f"  [DL] {label}: {url}")
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (cervix-multimodal downloader)"
        })
        with urllib.request.urlopen(req, timeout=60) as resp, open(tmp, "wb") as fo:
            total = resp.headers.get("Content-Length")
            total_i = int(total) if total else None
            done = 0
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                fo.write(chunk)
                done += len(chunk)
                if total_i:
                    pct = 100.0 * done / total_i
                    print(f"    {done/1024/1024:6.1f}/{total_i/1024/1024:.1f} MB "
                          f"({pct:5.1f}%)\r", end="", flush=True)
                else:
                    print(f"    {done/1024/1024:6.1f} MB\r", end="", flush=True)
        print()
        tmp.replace(dst)
        return True
    except Exception as e:
        print(f"  [DL FAIL] {label}: {type(e).__name__}: {e}")
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        return False


def _ungz(src: Path, dst: Path):
    with gzip.open(src, "rb") as fi, open(dst, "wb") as fo:
        shutil.copyfileobj(fi, fo)


def _extract_nested_tar(member_tar_bytes: bytes, dst: Path):
    """Extract a Visium-output tar stored as bytes into dst."""
    try:
        with tarfile.open(fileobj=io.BytesIO(member_tar_bytes), mode="r:*") as tar:
            dst.mkdir(parents=True, exist_ok=True)
            # Safe extraction — strip up to one level of common leading dir
            members = list(tar.getmembers())
            common_prefix = None
            if members:
                names = [m.name for m in members if m.isfile()]
                if names:
                    parts = names[0].split("/")
                    if len(parts) > 1 and all(n.startswith(parts[0] + "/") for n in names[1:]):
                        common_prefix = parts[0] + "/"
            for m in members:
                if not m.isfile():
                    continue
                out_name = m.name
                if common_prefix and out_name.startswith(common_prefix):
                    out_name = out_name[len(common_prefix):]
                if not out_name or out_name.startswith("..") or out_name.startswith("/"):
                    continue
                out_path = dst / out_name
                out_path.parent.mkdir(parents=True, exist_ok=True)
                f = tar.extractfile(m)
                if f is None:
                    continue
                with open(out_path, "wb") as fo:
                    shutil.copyfileobj(f, fo)
    except Exception as e:
        print(f"      [WARN] nested tar extract failed: {e}")


def extract_raw_tar(raw_tar: Path):
    tmp_root = DATA / "_dl_tmp" / GSE_NAME
    tmp_root.mkdir(parents=True, exist_ok=True)
    print(f"  [EXTRACT] {raw_tar} -> {tmp_root}")
    try:
        with tarfile.open(raw_tar, "r") as tar:
            tar.extractall(path=tmp_root)
    except Exception as e:
        print(f"  [EXTRACT FAIL] tar extraction failed: {e}")
        return False

    for gsm, (local_name, suffix) in GSM_TO_LOCAL.items():
        sd = GEO_DIR / local_name
        if sample_intact(sd):
            print(f"  [OK] {local_name}: already intact, skip")
            continue
        sd.mkdir(parents=True, exist_ok=True)
        (sd / "spatial").mkdir(parents=True, exist_ok=True)
        for ext, out_name in [
            (f"barcodes.tsv.gz", "barcodes.tsv.gz"),
            (f"features.tsv.gz", "features.tsv.gz"),
            (f"matrix.mtx.gz",   "matrix.mtx.gz"),
        ]:
            member = tmp_root / f"{gsm}_{suffix}.{ext}"
            if not member.exists():
                alt = tmp_root / f"{suffix}.{ext}"
                if alt.exists():
                    member = alt
            if member.exists():
                shutil.copy2(member, sd / out_name)
            else:
                print(f"  [WARN] {local_name}: missing {ext} in extracted tar")
        jpg_gz = tmp_root / f"{gsm}_{suffix}.jpg.gz"
        if jpg_gz.exists():
            try:
                _ungz(jpg_gz, sd / "image.jpg")
            except Exception as e:
                print(f"  [WARN] {local_name}: failed to gunzip image: {e}")
    return True


def extract_ecto_tar(raw_tar: Path) -> int:
    """Extract GSE217237_RAW.tar into ECTO_DIR/<sample>/ for each ST sample.
    Returns number of Visium-compliant samples successfully assembled.

    Outer-tar member format: `{GSMnnnnnnn}_{Pid}.tar.gz` (gzipped inner tar).
    Each inner tar holds one Visium sample's Space Ranger output, typically
    with a single top-level directory that itself contains
    `filtered_feature_bc_matrix.h5` and `spatial/`.
    """
    ECTO_DIR.mkdir(parents=True, exist_ok=True)
    tmp_root = DATA / "_dl_tmp" / ECTO_GSE
    tmp_root.mkdir(parents=True, exist_ok=True)
    print(f"  [EXTRACT ECTO] {raw_tar}")

    n_ok = 0
    try:
        with tarfile.open(raw_tar, "r") as outer:
            for member in outer.getmembers():
                if not member.isfile():
                    continue
                name = member.name  # e.g. "GSM8811056_P004.tar.gz"
                base = Path(name).name
                # Remove .tar.gz / .tar suffix to get the prefix we can match
                stem = base
                for suffix in (".tar.gz", ".tgz", ".tar", ".gz"):
                    if stem.lower().endswith(suffix):
                        stem = stem[: -len(suffix)]
                        break
                # Match against ECTO_ST_SAMPLES: "GSM8811056_P004"
                matched_prefix = None
                if stem in _ECTO_PREFIX_TO_LOCAL:
                    matched_prefix = stem
                else:
                    for prefix in ECTO_ST_SAMPLES:
                        if base.startswith(prefix + ".tar") or base == prefix + ".tar.gz":
                            matched_prefix = prefix
                            break
                if matched_prefix is None:
                    # skip non-sample files (metadata etc.)
                    continue
                local_name = _ECTO_PREFIX_TO_LOCAL[matched_prefix]  # e.g. "P004"
                out_dir = ECTO_DIR / local_name
                if sample_intact(out_dir, require_positions=False):
                    print(f"  [OK] ecto {local_name}: already intact")
                    n_ok += 1
                    continue
                f = outer.extractfile(member)
                if f is None:
                    continue
                inner_bytes = f.read()
                # Inner payload is a gzipped tar or plain tar. `r:*` auto-detects
                # but some GEO files double-compress; we already have bytes so
                # try to strip one extra gzip wrap (magic 1f 8b) if `r:*` fails.
                ok = _extract_nested_tar_smart(inner_bytes, out_dir, local_name)
                if ok and sample_intact(out_dir, require_positions=False):
                    n_ok += 1
                    print(f"  [BUILD] ecto {local_name}: OK")
                else:
                    print(f"  [WARN] ecto {local_name}: still not intact after extract")
    except Exception as e:
        print(f"  [EXTRACT FAIL] ecto tar extraction failed: {e}")
    return n_ok


def _extract_nested_tar_smart(member_tar_bytes: bytes, dst: Path, tag: str = "") -> bool:
    """Extract an inner Visium payload (tar or gzip+tar or even plain spatial
    tar) into dst, returning True iff dst was written successfully.
    """
    # Try one level of gzip decompression first if magic present
    payload = member_tar_bytes
    if len(payload) >= 2 and payload[0] == 0x1F and payload[1] == 0x8B:
        try:
            payload = gzip.decompress(payload)
        except Exception:
            payload = member_tar_bytes
    try:
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:*") as tar:
            dst.mkdir(parents=True, exist_ok=True)
            members = list(tar.getmembers())
            # Strip a single common leading directory (Space Ranger output
            # wraps every sample in one dir).
            common_prefix = None
            if members:
                names = [m.name for m in members if m.isfile()]
                if names:
                    parts = names[0].split("/")
                    if len(parts) > 1 and all(
                        n.startswith(parts[0] + "/") for n in names[1:]
                    ):
                        common_prefix = parts[0] + "/"
            any_written = False
            for m in members:
                if not m.isfile():
                    continue
                out_name = m.name
                if common_prefix and out_name.startswith(common_prefix):
                    out_name = out_name[len(common_prefix):]
                if not out_name or out_name.startswith("..") or out_name.startswith("/"):
                    continue
                # Skip hidden / macOS housekeeping
                if any(p.startswith(".") for p in Path(out_name).parts):
                    continue
                out_path = dst / out_name
                out_path.parent.mkdir(parents=True, exist_ok=True)
                f = tar.extractfile(m)
                if f is None:
                    continue
                with open(out_path, "wb") as fo:
                    shutil.copyfileobj(f, fo)
                any_written = True
            return any_written
    except Exception as e:
        print(f"      [WARN] ({tag}) nested tar extract failed: {type(e).__name__}: {e}")
        return False


def _junction_or_copy(src: Path, dst: Path) -> bool:
    """Create a Windows junction (or symlink/copy) of src at dst. True if
    created fresh, False if already existed or failed."""
    if dst.exists():
        if (dst / "filtered_feature_bc_matrix.h5").exists() or any(
            (dst / r).exists() for r in [ECTO_REQUIRED_MIN[0], ECTO_REQUIRED_MIN[0].name]
        ):
            return False
        shutil.rmtree(dst)
    if not src.exists():
        return False
    try:
        if os.name == "nt":
            subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(dst), str(src)],
                check=True, capture_output=True,
            )
        else:
            dst.symlink_to(src, target_is_directory=True)
    except Exception:
        shutil.copytree(src, dst, symlinks=True)
    return True


def consolidate():
    ALL_DIR.mkdir(parents=True, exist_ok=True)
    sources = []
    for local_name in ["N_HPV", "HSIL_HPV", "CA_HPV_1", "CA_HPV_2"]:
        sources.append((GEO_DIR / local_name, local_name))
    sources.append((CERV1, "cervical_cancer_1"))

    made = 0
    for src, name in sources:
        dst = ALL_DIR / name
        created = _junction_or_copy(src, dst)
        if created:
            made += 1
            print(f"  [cervix_all] {name}: created from {src}")
        elif dst.exists():
            print(f"  [cervix_all] {name}: already present")
    print(f"  [cervix_all] ready: {len([d for d in ALL_DIR.iterdir() if d.is_dir()])} "
          f"sample dirs (new {made})")
    return True


def consolidate_ext():
    """Create cervix_all_ext/: 5 core samples + all ecto samples."""
    EXT_DIR.mkdir(parents=True, exist_ok=True)
    # Step 1: 5 core samples (same as cervix_all)
    sources = []
    for local_name in ["N_HPV", "HSIL_HPV", "CA_HPV_1", "CA_HPV_2"]:
        sources.append((GEO_DIR / local_name, local_name))
    sources.append((CERV1, "cervical_cancer_1"))
    # Step 2: ectocervix samples
    if ECTO_DIR.exists():
        for sd in sorted(ECTO_DIR.iterdir()):
            if sd.is_dir():
                sources.append((sd, f"ecto_{sd.name}"))

    made = 0
    for src, name in sources:
        dst = EXT_DIR / name
        created = _junction_or_copy(src, dst)
        if created:
            made += 1
            print(f"  [cervix_all_ext] {name}: created")
        elif dst.exists():
            print(f"  [cervix_all_ext] {name}: already present")
    total = len([d for d in EXT_DIR.iterdir() if d.is_dir()])
    print(f"  [cervix_all_ext] ready: {total} sample dirs (new {made})")
    return True


def write_ecto_labels():
    """Append 11 ectocervix rows to the histology labels CSV so
    train_st.py --histology_label_csv can read them directly.

    Ectocervix samples are all 'Normal' (ectocervical mucosa from Kenyan
    cohort; not HSIL or invasive cancer); we mark cin_grade=0,
    histology_subtype='Normal_Ecto', progression_ordinal=0 (lowest risk).
    """
    LABELS_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = LABELS_DIR / "cervix_histology_labels_extended.csv"
    # Always rewrite from scratch
    rows = [
        ["sample_id", "cin_grade", "histology_subtype", "progression_ordinal", "notes"],
        ["N_HPV", "0", "Normal", "0", "Normal cervix HPV+; Guo 2023 GSM6360689"],
        ["HSIL_HPV", "3", "HSIL", "1", "HSIL/CIN3 HPV+; Guo 2023 GSM6360690"],
        ["CA_HPV_1", "4", "SCC", "2", "Cervical squamous cell carcinoma; GSM6360691"],
        ["CA_HPV_2", "4", "ADC", "2", "Cervical adenocarcinoma; GSM6360692"],
        ["cervical_cancer_1", "4", "SCC", "2", "10x Visium FFPE Human Cervical Cancer block"],
    ]
    for prefix in ECTO_ST_SAMPLES:
        sample_name = prefix.split("_", 1)[1]  # P004_ST etc.
        pid = sample_name.replace("_ST", "")
        rows.append([
            f"ecto_{sample_name}", "0", "Normal_Ecto", "0",
            f"Ectocervical mucosa Visium ({ECTO_GSE} GSE290350 sample {pid}); "
            "HIV/DMPA cohort normal low-risk control",
        ])
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerows(rows)
    # Also update the original short CSV (keep original 5 rows intact first;
    # append 11 new rows). We don't overwrite the original CSV directly,
    # we write a second copy and a symlink-like copy.
    orig = LABELS_DIR / "cervix_histology_labels.csv"
    if not orig.exists():
        shutil.copy2(csv_path, orig)
    # The user-facing primary label file that includes ecto samples:
    print(f"  [LABELS] wrote {csv_path} ({len(rows)-1} samples)")
    return csv_path


def print_manual_download_checklist():
    print()
    print("=" * 72)
    print("MANUAL DOWNLOAD CHECKLIST (use if HTTP download fails on this machine)")
    print("=" * 72)
    print(f"1. GSE208654_RAW.tar (4 geo_cesc samples):")
    print(f"   {RAW_URL}   (~222 MB)")
    print(f"   drop at: {DATA / '_dl_tmp' / GSE_NAME / GSE_NAME}_RAW.tar")
    print()
    print(f"2. GSE217237_RAW.tar (30 ectocervix Visium sections; extended normal controls)")
    print(f"   {ECTO_RAW_URL}   (~{ECTO_EXPECTED_MB} MB)")
    print(f"   drop at: {DATA / '_dl_tmp' / ECTO_GSE / ECTO_GSE}_RAW.tar")
    print()
    print("3. (Optional) 10x Visium FFPE demo block 'cervical_cancer_1':")
    print("   10x Genomics website -> Resources -> Datasets -> Visium FFPE Human Cervical Cancer")
    print()
    print("Other candidates (email authors for processed ST matrices):")
    print("  - Pavilion et al. 2026 J Pathol (UQ QIMRB): 7x HPV+ CIN3/HSIL Visium")
    print("    email: quan.nguyen@qimrberghofer.edu.au; i.frazer@uq.edu.au")
    print("  - Zhou et al. 2024 J Transl Med 22:1163 (Wuhan University/Hubei MCH):")
    print("    cervical SCC multi-slice Visium; email: shenchao@whu.edu.cn / dongxin@hbfy.com")
    print("  - Wu et al. 2025 Commun Biol: 22 FFPE Xenium (subcellular, NOT Visium)")
    print("=" * 72)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tar", help="Path to pre-downloaded GSE208654_RAW.tar")
    ap.add_argument("--ecto-tar", help=f"Path to pre-downloaded {ECTO_GSE}_RAW.tar")
    ap.add_argument("--with-ectocervix", action="store_true",
                    help="Also download/extract/assemble the 30 ectocervix Visium "
                         "sections from GSE217237 and build cervix_all_ext/ (n<=35).")
    ap.add_argument("--skip-download", action="store_true",
                    help="Do not try HTTP download; just validate + consolidate")
    ap.add_argument("--skip-extract", action="store_true",
                    help="Do not extract tar; just consolidate existing samples")
    ap.add_argument("--print-checklist", action="store_true",
                    help="Only print the manual download checklist and exit")
    args = ap.parse_args()

    if args.print_checklist:
        print_manual_download_checklist()
        return

    # ===== GSE208654 4 core samples =====
    print(f"[1/6] Validate existing geo_cesc samples")
    missing = []
    for gsm, (local_name, _suf) in GSM_TO_LOCAL.items():
        sd = GEO_DIR / local_name
        ok = sample_intact(sd)
        print(f"  {local_name}: {'OK' if ok else 'MISSING/BROKEN'}")
        if not ok:
            missing.append(local_name)

    raw_tar = Path(args.tar) if args.tar else (
        DATA / "_dl_tmp" / GSE_NAME / f"{GSE_NAME}_RAW.tar")
    if missing and not args.skip_extract and not raw_tar.exists() and not args.skip_download:
        print(f"[2/6] Download {GSE_NAME}_RAW.tar ({EXPECTED_RAW_SIZE_MB} MB)")
        ok = download_http(RAW_URL, raw_tar, f"{GSE_NAME}_RAW.tar")
        if not ok:
            print("  HTTP download failed on this machine.")
    elif raw_tar.exists() and missing and not args.skip_extract:
        print(f"[2/6] Using pre-existing tar at {raw_tar}")
    else:
        print("[2/6] All 4 core samples intact; no GSE208654 download required")

    if missing and not args.skip_extract and raw_tar.exists():
        print("[3/6] Extract GSE208654 tar and rebuild core sample dirs")
        extract_raw_tar(raw_tar)
        still = [n for (_, (n, _)) in GSM_TO_LOCAL.items() if not sample_intact(GEO_DIR / n)]
        if still:
            print(f"  [WARN] Still not intact after tar extract: {still} "
                  "(RAW tar doesn't ship spatial/ files; must reuse existing geo_cesc/spatial/)")
    else:
        print("[3/6] GSE208654 extract skipped")

    # ===== GSE217237 ectocervix (optional) =====
    ecto_n_ready = 0
    if args.with_ectocervix:
        print("[4/6] Validate / download / extract GSE217237 ectocervix Visium")
        missing_ecto = []
        for prefix in ECTO_ST_SAMPLES:
            sample_name = prefix.split("_", 1)[1]
            sd = ECTO_DIR / sample_name
            if not sample_intact(sd, require_positions=False):
                missing_ecto.append(sample_name)
        print(f"  ectocervix intact: {len(ECTO_ST_SAMPLES) - len(missing_ecto)}/{len(ECTO_ST_SAMPLES)}")

        ecto_tar = Path(args.ecto_tar) if args.ecto_tar else (
            DATA / "_dl_tmp" / ECTO_GSE / f"{ECTO_GSE}_RAW.tar")
        if missing_ecto and not args.skip_extract and not ecto_tar.exists() and not args.skip_download:
            print(f"  -> Downloading {ECTO_GSE}_RAW.tar (~{ECTO_EXPECTED_MB} MB)")
            download_http(ECTO_RAW_URL, ecto_tar, f"{ECTO_GSE}_RAW.tar")
        if missing_ecto and not args.skip_extract and ecto_tar.exists():
            ecto_n_ready = extract_ecto_tar(ecto_tar)
            # After extract, recount
            ecto_n_ready = sum(1 for prefix in ECTO_ST_SAMPLES
                               if sample_intact(ECTO_DIR / prefix.split("_", 1)[1],
                                                require_positions=False))
        elif not missing_ecto:
            ecto_n_ready = len(ECTO_ST_SAMPLES)
        print(f"  Ectocervix Visium ready: {ecto_n_ready}/{len(ECTO_ST_SAMPLES)}")
        write_ecto_labels()
    else:
        print("[4/6] Ectocervix skipped (pass --with-ectocervix to enable)")

    # ===== Consolidate =====
    print("[5/6] Consolidate 5 core cervical Visium -> cervix_all/")
    consolidate()

    if args.with_ectocervix:
        print("[6/6] Consolidate 5 core + ectocervix -> cervix_all_ext/")
        consolidate_ext()
    else:
        print("[6/6] Extended consolidate (cervix_all_ext) skipped")

    # ===== Final summary =====
    print()
    n_core = sum(1 for d in ALL_DIR.iterdir()
                 if d.is_dir() and sample_intact(d, require_positions=True))
    total_core = len([d for d in ALL_DIR.iterdir() if d.is_dir()])
    print(f"SUMMARY CORE: {n_core}/{total_core} samples under {ALL_DIR}")
    if args.with_ectocervix and EXT_DIR.exists():
        # ecto may use tissue_positions.csv instead of tissue_positions_list.csv
        def _ready(d):
            return sample_intact(d, require_positions=False)
        n_ext = sum(1 for d in EXT_DIR.iterdir() if d.is_dir() and _ready(d))
        total_ext = len([d for d in EXT_DIR.iterdir() if d.is_dir()])
        print(f"SUMMARY EXT : {n_ext}/{total_ext} samples under {EXT_DIR}")
        if n_ext >= 12:
            print(f"  -> Use --data {EXT_DIR.relative_to(ROOT)} "
                  "--histology_label_csv "
                  f"{(LABELS_DIR / 'cervix_histology_labels_extended.csv').relative_to(ROOT)} "
                  "--hpv_gene_set kegg_hpv for 16-sample training")
    if n_core >= 4:
        print(f"  -> Proceed to Step 10 with --data {ALL_DIR.relative_to(ROOT)}")
    else:
        print("  -> Not enough core samples; re-run with --tar <path> or use --print-checklist")
        print_manual_download_checklist()


if __name__ == "__main__":
    main()
