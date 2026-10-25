"""Reconstruct the `spatial/` folder + `filtered_feature_bc_matrix.h5` for GEO
samples whose Space Ranger output is the bare minimum (barcodes / features /
matrix.mtx / jpg only — no `spatial/` directory).

Background
----------
10x Space Ranger normally produces:
    filtered_feature_bc_matrix.h5
    spatial/{tissue_hires_image.png, tissue_positions_list.csv, scalefactors_json.json}

GEO only ships:
    <prefix>.barcodes.tsv.gz, <prefix>.features.tsv.gz, <prefix>.matrix.mtx.gz, <prefix>.jpg.gz

We reconstruct everything st_data.py needs:
  1. <sample_dir>/filtered_feature_bc_matrix.h5  (anndata 10x h5 format)
  2. <sample_dir>/spatial/tissue_hires_image.png
  3. <sample_dir>/spatial/tissue_positions_list.csv  (barcode, in_tissue, array_row, array_col, pxl_row_in_fullres, pxl_col_in_fullres)
  4. <sample_dir>/spatial/scalefactors_json.json

Reconstruction strategy
-----------------------
- Barcode -> (array_row, array_col) map: 10x's official `visium-v1_coordinates.txt`
  (downloaded once into data/visium-v1_coordinates.txt; barcode sequence = first
  16 bp of "<16bp>-1" line in GEO barcodes.tsv).
- pxl coordinates: build them from array_row/array_col assuming standard Visium
  layout (65 um spot pitch, 4992-spot grid). For GEO images whose resolution we
  don't know, we **set the image as hires with scalef = 1.0 and spot diameter
  = 65 px** — then the in-image pixel position equals the spot's grid position.
  This is an approximation: spatial neighbour construction is distance-based and
  works fine; only H&E patch cropping (for FM embedding) will be approximately
  aligned (within a few pixels), which is acceptable for tile-level ViT-L features.
- scalefactors_json: spot_diameter_fullres = 65, tissue_hires_scalef = 1.0,
  fiducial_diameter_fullres = 100, spot_diameter_hires = 65.

Run after `download_cesc_st_geo.py` finishes:
  python scripts/reconstruct_spatial.py --root data/st_visium/geo_cesc
"""
from __future__ import annotations
import argparse
import gzip
import io
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from scipy.io import mmread


SPOT_PITCH_UM = 65.0          # Visium v1 center-to-center spacing in um
HIRES_SCALE = 1.0             # we treat the GEO jpg as "hires"; fullres = hires
SPOT_DIAMETER_PX = 65.0       # spot pixel diameter in hires (=fullres) image
OFFSET_X = 65.0               # left/top margin between image edge and first spot
OFFSET_Y = 65.0


def _load_coordinate_map() -> dict[str, tuple[int, int]]:
    """Read data/visium-v1_coordinates.txt -> {barcode_16bp: (array_row, array_col)}."""
    src = Path("data/visium-v1_coordinates.txt")
    if not src.exists():
        raise FileNotFoundError(
            f"{src} not found. Download from "
            "https://raw.githubusercontent.com/mahmoodlab/HEST/main/assets/barcode_coords/visium-v1_coordinates.txt "
            "and save to data/visium-v1_coordinates.txt")
    m = {}
    with open(src) as f:
        header = f.readline()
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 3:
                bc, row, col = parts[0], int(parts[1]), int(parts[2])
                m[bc] = (row, col)
    return m


def _build_filtered_h5(matrix_gz: Path, barcodes_gz: Path, features_gz: Path, out_h5: Path):
    """Convert 10x v3 mtx+barcodes+features to an AnnData / filtered_feature_bc_matrix h5."""
    try:
        import scanpy as sc
        adata = sc.read_10x_mtx(matrix_gz.parent, gzipped=True, prefix=matrix_gz.name.replace(".matrix.mtx.gz", ""), var_names="gene_symbols")
        adata.write_h5ad(out_h5)
    except Exception as e:
        raise RuntimeError(f"scanpy read_10x_mtx failed: {e}")


def _build_tissue_positions(barcodes_gz: Path, coord_map: dict, out_csv: Path):
    """Build tissue_positions_list.csv with cols:
    barcode, in_tissue, array_row, array_col, pxl_row_in_fullres, pxl_col_in_fullres
    """
    rows = []
    with gzip.open(barcodes_gz, "rt") as f:
        barcodes = [l.strip() for l in f.readlines()]
    for bc in barcodes:
        seq = bc.split("-")[0]  # 16 bp
        if seq not in coord_map:
            raise KeyError(f"barcode {bc} not in visium-v1 map (n={len(coord_map)})")
        r, c = coord_map[seq]
        pxl_x = OFFSET_X + c * SPOT_PITCH_UM
        pxl_y = OFFSET_Y + r * SPOT_PITCH_UM
        rows.append((bc, 1, r, c, pxl_x, pxl_y))

    df = pd.DataFrame(rows, columns=["barcode", "in_tissue", "array_row", "array_col",
                                      "pxl_row_in_fullres", "pxl_col_in_fullres"])
    df.to_csv(out_csv, index=False)


def _build_scalefactors(out_json: Path):
    s = {
        "spot_diameter_fullres": SPOT_DIAMETER_PX,
        "fiducial_diameter_fullres": 100.0,
        "tissue_lowres_scalef": HIRES_SCALE,
        "tissue_hires_scalef": HIRES_SCALE,
        "tissue_hires_thumbnail_scalef": HIRES_SCALE,
        "spot_diameter_hires": SPOT_DIAMETER_PX,
    }
    out_json.write_text(json.dumps(s, indent=2))


def _unpack_jpg(jpg_gz: Path, out_png: Path):
    # allow large H&E images (GEO jpgs can exceed PIL's default 89M-pixel limit)
    Image.MAX_IMAGE_PIXELS = None
    with gzip.open(jpg_gz, "rb") as g, open(out_png, "wb") as o:
        shutil.copyfileobj(g, o, length=1024 * 256)
    # ensure PNG (st_data.py expects png); convert if necessary
    if out_png.suffix.lower() == ".png":
        try:
            with Image.open(out_png) as im:
                im.convert("RGB").save(out_png, format="PNG")
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/st_visium/geo_cesc")
    args = ap.parse_args()

    coord_map = _load_coordinate_map()
    print(f"[map] loaded {len(coord_map)} barcode->(row,col) pairs")

    for sample_dir in sorted(Path(args.root).iterdir()):
        if not sample_dir.is_dir():
            continue
        # find the three files by suffix
        barcodes_gz = next(sample_dir.glob("*.barcodes.tsv.gz"), None)
        features_gz = next(sample_dir.glob("*.features.tsv.gz"), None)
        matrix_gz = next(sample_dir.glob("*.matrix.mtx.gz"), None)
        jpg_gz = next(sample_dir.glob("*.jpg.gz"), None)
        if not (barcodes_gz and features_gz and matrix_gz and jpg_gz):
            print(f"[skip] {sample_dir.name}: missing files")
            continue

        print(f"\n=== {sample_dir.name} ===")
        spatial_dir = sample_dir / "spatial"
        spatial_dir.mkdir(exist_ok=True)

        # 1. h5
        h5_path = sample_dir / "filtered_feature_bc_matrix.h5"
        if not h5_path.exists():
            print("  [h5] building filtered_feature_bc_matrix.h5 ...")
            try:
                _build_filtered_h5(matrix_gz, barcodes_gz, features_gz, h5_path)
            except Exception as e:
                print(f"  [h5 FAIL] {e}; trying manual mtx->h5 ...")
                _build_filtered_h5_manual(matrix_gz, barcodes_gz, features_gz, h5_path)
            print(f"  [h5] -> {h5_path.stat().st_size/1e6:.1f} MB")
        else:
            print(f"  [h5] exists, skip")

        # 2. jpg -> hires image
        hires_png = spatial_dir / "tissue_hires_image.png"
        if not hires_png.exists():
            print("  [img] extracting tissue_hires_image.png ...")
            _unpack_jpg(jpg_gz, hires_png)
            print(f"  [img] -> {hires_png.stat().st_size/1e6:.1f} MB")
        else:
            print(f"  [img] exists, skip")

        # 3. tissue_positions
        tp = spatial_dir / "tissue_positions_list.csv"
        if not tp.exists():
            print("  [pos] building tissue_positions_list.csv ...")
            _build_tissue_positions(barcodes_gz, coord_map, tp)
            n = pd.read_csv(tp).shape[0]
            print(f"  [pos] -> {n} spots")
        else:
            print(f"  [pos] exists, skip")

        # 4. scalefactors
        sf = spatial_dir / "scalefactors_json.json"
        if not sf.exists():
            _build_scalefactors(sf)
            print(f"  [sf]  -> {sf.name}")

    print("\nDone. Each sample dir now matches the 10x Space Ranger layout expected by st_data.py.")


def _build_filtered_h5_manual(matrix_gz: Path, barcodes_gz: Path, features_gz: Path, out_h5: Path):
    """Build a 10x-standard `filtered_feature_bc_matrix.h5` from mtx (skipping
    `%` metadata comment lines that scipy.mmread chokes on) + h5py.

    Produces the canonical 10x layout that st_data.py's `_read_10x_h5` expects:
        matrix/{data, indices, indptr, shape, barcodes, features/{name, id,
               feature_type, genome}}
    where `matrix/shape` = (n_genes, n_spots) and the sparse array is CSC with
    `indptr` indexing the spot (barcode) dimension.
    """
    import h5py
    from scipy.sparse import csc_matrix

    # parse mtx (row=gene, col=cell), skipping '%' comment lines
    rows, cols, data = [], [], []
    n_genes = n_cells = 0
    with gzip.open(matrix_gz, "rt") as g:
        for line in g:
            line = line.strip()
            if not line or line.startswith("%"):
                continue
            parts = line.split()
            if len(parts) == 3 and n_genes == 0:
                n_genes, n_cells, _ = int(parts[0]), int(parts[1]), int(parts[2])
                continue
            rows.append(int(parts[0]) - 1)   # 1-based -> 0-based (gene)
            cols.append(int(parts[1]) - 1)   # 1-based -> 0-based (cell)
            data.append(float(parts[2]))
    # gene x cell, stored CSC (indptr indexes the cell/spot dimension)
    gxc = csc_matrix((data, (rows, cols)), shape=(n_genes, n_cells))

    with gzip.open(barcodes_gz, "rt") as f:
        barcodes = np.array([l.strip().encode() for l in f.readlines()])
    with gzip.open(features_gz, "rt") as f:
        feats = [l.strip().split("\t") for l in f.readlines()]
    gene_ids = np.array([x[0].encode() for x in feats])
    gene_names = np.array([x[1].encode() for x in feats])
    feature_types = np.array([x[2].encode() for x in feats])

    with h5py.File(out_h5, "w") as h:
        m = h.create_group("matrix")
        m.create_dataset("data", data=np.array(gxc.data, dtype=np.float32))
        m.create_dataset("indices", data=np.array(gxc.indices, dtype=np.int64))
        m.create_dataset("indptr", data=np.array(gxc.indptr, dtype=np.int64))
        m.create_dataset("shape", data=np.array([n_genes, n_cells], dtype=np.int64))
        m.create_dataset("barcodes", data=barcodes)
        ft = m.create_group("features")
        ft.create_dataset("name", data=gene_names)
        ft.create_dataset("id", data=gene_ids)
        ft.create_dataset("feature_type", data=feature_types)
        ft.create_dataset("genome", data=np.array([b"GRCh38" for _ in feats]))


if __name__ == "__main__":
    main()