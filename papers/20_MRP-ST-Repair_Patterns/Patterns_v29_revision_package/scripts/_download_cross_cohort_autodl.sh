#!/bin/bash
# ============================================================
# Cross-Cancer Visium ST Dataset Download Script
# Run on AutoDL GPU machine
# ============================================================

cd /root/autodl-tmp/project/project4_cervix_multimodal
OUT="data/st_visium"
mkdir -p "$OUT/_dl_tmp"

echo "=============================================="
echo " Phase 1: 10x Genomics Public Visium Datasets"
echo "=============================================="

# --- 1A: CytAssist FFPE Breast Cancer (Visium SD, FFPE, 1 sample, ~1.3GB) ---
echo ""
echo "[1A] Downloading CytAssist_FFPE_Human_Breast_Cancer ..."
mkdir -p "$OUT/10x_breast_ffpe"
BASE="https://cf.10xgenomics.com/samples/spatial-exp/2.0.0/CytAssist_FFPE_Human_Breast_Cancer"
for f in \
    CytAssist_FFPE_Human_Breast_Cancer_tissue_image.tif \
    CytAssist_FFPE_Human_Breast_Cancer_filtered_feature_bc_matrix.h5 \
    CytAssist_FFPE_Human_Breast_Cancer_raw_feature_bc_matrix.h5 \
    CytAssist_FFPE_Human_Breast_Cancer_spatial.tar.gz \
    CytAssist_FFPE_Human_Breast_Cancer_cloupe.cloupe.gz
do
    if [ ! -f "$OUT/10x_breast_ffpe/$f" ]; then
        echo "  wget $f"
        wget -q --show-progress -O "$OUT/10x_breast_ffpe/$f" "$BASE/$f" || echo "  [warn] $f failed"
    else
        echo "  [skip] $f exists"
    fi
done
if [ -f "$OUT/10x_breast_ffpe/CytAssist_FFPE_Human_Breast_Cancer_spatial.tar.gz" ]; then
    tar -xzf "$OUT/10x_breast_ffpe/CytAssist_FFPE_Human_Breast_Cancer_spatial.tar.gz" \
        -C "$OUT/10x_breast_ffpe/"
    echo "  [done] extracted spatial/"
fi

# --- 1B: Human Breast Cancer Fresh Frozen (Visium SD, 1 sample) ---
echo ""
echo "[1B] Downloading Visium_FF_Human_Breast_Cancer ..."
mkdir -p "$OUT/10x_breast_ff"
BASE="https://cf.10xgenomics.com/samples/spatial-exp/2.0.0/Visium_FF_Human_Breast_Cancer"
for f in \
    Visium_FF_Human_Breast_Cancer_tissue_image.tif \
    Visium_FF_Human_Breast_Cancer_filtered_feature_bc_matrix.h5 \
    Visium_FF_Human_Breast_Cancer_spatial.tar.gz
do
    if [ ! -f "$OUT/10x_breast_ff/$f" ]; then
        wget -q --show-progress -O "$OUT/10x_breast_ff/$f" "$BASE/$f" || echo "  [warn] $f failed"
    fi
done
if [ -f "$OUT/10x_breast_ff/Visium_FF_Human_Breast_Cancer_spatial.tar.gz" ]; then
    tar -xzf "$OUT/10x_breast_ff/Visium_FF_Human_Breast_Cancer_spatial.tar.gz" \
        -C "$OUT/10x_breast_ff/"
fi

echo ""
echo "=============================================="
echo " Phase 2: GEO GSE210616 — TNBC Breast Cancer Visium (14 patients, 28+ samples)"
echo " Download first 5 GSMs (each has h5 + spatial)"
echo "=============================================="

GEO_SERIES="GSE210616"
GEO_PREFIX="GSE210nnn"  # GSE210nnn format for FTP
# GSM6433585 - GSM6433627 (43 total), we pick first 5 from different patients
for GSM in GSM6433585 GSM6433589 GSM6433593 GSM6433597 GSM6433601; do
    echo ""
    echo "[GEO] $GSM ..."
    GSM_NUM="${GSM:3}"  # extract number part, e.g. 6433585
    NUM_PREFIX="${GSM_NUM:0:5}nnn"  # e.g. 64335nnn
    DEST="$OUT/geo_breast_tnbc/$GSM"
    mkdir -p "$DEST"
    FTP_BASE="https://ftp.ncbi.nlm.nih.gov/geo/samples/${NUM_PREFIX}/${GSM}/suppl"
    
    for f in \
        "${GSM}_filtered_feature_bc_matrix.h5" \
        "${GSM}_scalefactors_json.json.gz" \
        "${GSM}_tissue_hires_image.png.gz" \
        "${GSM}_tissue_lowres_image.png.gz" \
        "${GSM}_tissue_positions_list.csv.gz"
    do
        URL="$FTP_BASE/$f"
        if [ ! -f "$DEST/$f" ]; then
            wget -q --show-progress -O "$DEST/$f" "$URL" 2>/dev/null || echo "  [skip] $f"
        fi
    done
    
    # decompress gz files
    for gz in "$DEST"/*.gz; do
        [ -f "$gz" ] && gunzip -kf "$gz" && rm "$gz" 2>/dev/null
    done
    
    echo "  [done] $(ls "$DEST" | wc -l) files"
done

echo ""
echo "=============================================="
echo " Phase 3: GSE252176 — TNBC Visium (4 sections, 2024)"
echo "=============================================="
# GSM7996201-7996204 (4 sections)
for GSM in GSM7996201 GSM7996202 GSM7996203 GSM7996204; do
    echo ""
    echo "[GEO] $GSM (GSE252176) ..."
    GSM_NUM="${GSM:3}"
    NUM_PREFIX="${GSM_NUM:0:5}nnn"
    DEST="$OUT/geo_breast_tnbc_v2/$GSM"
    mkdir -p "$DEST"
    FTP_BASE="https://ftp.ncbi.nlm.nih.gov/geo/samples/${NUM_PREFIX}/${GSM}/suppl"
    
    for f in \
        "${GSM}_filtered_feature_bc_matrix.h5" \
        "${GSM}_scalefactors_json.json.gz" \
        "${GSM}_tissue_hires_image.png.gz" \
        "${GSM}_tissue_positions_list.csv.gz"
    do
        URL="$FTP_BASE/$f"
        wget -q --show-progress -O "$DEST/$f" "$URL" 2>/dev/null || echo "  [skip] $f"
    done
    for gz in "$DEST"/*.gz; do
        [ -f "$gz" ] && gunzip -kf "$gz" && rm "$gz" 2>/dev/null
    done
    echo "  [done] $(ls "$DEST" | wc -l) files"
done

echo ""
echo "=============================================="
echo " Phase 4: Dryad Prostate Visium SD FFPE (2 samples)"
echo " PISTACHIO paper, Nature 2026"
echo "=============================================="
# https://datadryad.org/stash/dataset/doi:10.5061/dryad.0cfxpnwhc
# File: dryad_upload.tar.gz (805MB, contains RBJA_ST01 & RBJA_ST02 with full SR output)
echo "[Dryad] Prostate ..."
mkdir -p "$OUT/dryad_prostate"
DRYAD_FILE="$OUT/_dl_tmp/dryad_prostate.tar.gz"
if [ ! -f "$DRYAD_FILE" ]; then
    wget -q --show-progress -O "$DRYAD_FILE" \
        "https://datadryad.org/downloads/file_stream/4891612" 2>/dev/null || \
    wget -q --show-progress -O "$DRYAD_FILE" \
        "https://datadryad.org/stash/downloads/file_stream/4891612" || \
    echo "  [warn] Dryad prostate download failed — try manually: https://datadryad.org/dataset/doi:10.5061/dryad.0cfxpnwhc"
fi
if [ -f "$DRYAD_FILE" ] && [ "$(stat -c%s "$DRYAD_FILE" 2>/dev/null || echo 0)" -gt 1000000 ]; then
    tar -xf "$DRYAD_FILE" -C "$OUT/dryad_prostate/" 2>/dev/null
    echo "  [done] extracted Dryad prostate"
    # Show structure
    find "$OUT/dryad_prostate" -name "filtered_feature_bc_matrix.h5" 2>/dev/null | head -5
fi

echo ""
echo "=============================================="
echo " Phase 5: 10x Visium HD CRC (GSE280318)"
echo " Nature Genetics 2025 — 10x official CRC Visium HD"
echo "=============================================="
echo "  Downloading Visium HD CRC from GEO GSE280318 ..."
mkdir -p "$OUT/geo_colorectal_hd"
# GSE280318 supplementary files (direct GEO FTP)
wget -q --show-progress -O "$OUT/_dl_tmp/GSE280318_RAW.tar" \
    "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE280nnn/GSE280318/suppl/GSE280318_RAW.tar" 2>/dev/null || \
    echo "  [warn] GSE280318 RAW tar download failed (may need manual download)"
if [ -f "$OUT/_dl_tmp/GSE280318_RAW.tar" ]; then
    tar -xf "$OUT/_dl_tmp/GSE280318_RAW.tar" -C "$OUT/geo_colorectal_hd/" 2>/dev/null
    echo "  [done] extracted GSE280318"
fi

echo ""
echo "=============================================="
echo " DOWNLOAD COMPLETE — Summary"
echo "=============================================="
echo ""
echo "Directory structure:"
ls -d "$OUT"/*/ 2>/dev/null | sed "s|$OUT||"
echo ""
echo "Total h5 files (Visium ST):"
find "$OUT" -name "filtered_feature_bc_matrix.h5" | wc -l
echo ""
echo "Cross-cancer Visium samples ready:"
find "$OUT" -maxdepth 3 -name "filtered_feature_bc_matrix.h5" | while read f; do
    echo "  $f"
done
echo ""
echo "=============================================="
echo " Next: run FUNI-HPV on each cross-cancer dataset"
echo "=============================================="
echo ""
echo "# Example — run on all cross-cancer dirs together:"
echo "python scripts/train_st.py \\"
echo "    --data data/st_visium \\"
echo "    --exclude_substr geo_cesc,geo_ectocervix,cervical_cancer,visium_hd \\"
echo "    --fm uni --device cuda --epochs 50 --permutation_n 10000 \\"
echo "    --run_id CROSS_CANCER"
echo ""
echo "# Or run each dataset separately:"
echo "python scripts/train_st.py --data data/st_visium/geo_breast_tnbc --fm uni --device cuda --epochs 50 --run_id BREAST_TNBC"
echo "python scripts/train_st.py --data data/st_visium/geo_breast_tnbc_v2 --fm uni --device cuda --epochs 50 --run_id BREAST_TNBC_V2"
echo "python scripts/train_st.py --data data/st_visium/10x_breast_ff --fm uni --device cuda --epochs 50 --run_id BREAST_FF"
echo "python scripts/train_st.py --data data/st_visium/10x_breast_ffpe --fm uni --device cuda --epochs 50 --run_id BREAST_FFPE"
