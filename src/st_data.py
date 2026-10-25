"""Load 10x Visium spatial-transcriptomics samples and align them with the
matched H&E whole-slide image (SAME slide, SAME patient -> rigorously paired).

A Visium sample directory contains:
  - filtered_feature_bc_matrix.h5   (spots x genes, sparse)
  - spatial/tissue_hires_image.png  (H&E image of the same section)
  - spatial/scalefactors_json.json  (pixel<->micron mapping)
  - spatial/tissue_positions_list.csv (per-spot tissue coordinates)

We produce, for each spot, a (gene_expression_vector, image_patch_tensor) pair
that comes from the SAME physical location on the SAME slide.
"""
from __future__ import annotations
import itertools
import json
from pathlib import Path
from dataclasses import dataclass

import numpy as np
import torch
from PIL import Image
from scipy.sparse import csr_matrix

# GEO Visium H&E images can be 100M+ pixels (>PIL default 89M limit). Lift the
# limit globally so st_data.load_sample never issues DecompressionBombWarning
# on real-world hires tissue images.
Image.MAX_IMAGE_PIXELS = None


@dataclass
class STSample:
    name: str
    coords: np.ndarray          # (n_spots, 2) tissue coords (micron or hires px)
    barcodes: list[str]
    expression: csr_matrix      # (n_spots, n_genes) sparse
    genes: list[str]
    image: Image.Image          # H&E of the same section
    scalefactors: dict
    spot_radius_px: float


def _read_10x_h5(path: Path):
    """Read filtered_feature_bc_matrix.h5 -> (X sparse (spots x genes), barcodes, genes)."""
    import h5py
    from scipy.sparse import csc_matrix
    with h5py.File(path, "r") as f:
        grp = f["matrix"]
        # 10x stores the matrix as CSC with shape = (n_genes, n_spots);
        # indptr indexes the spot (barcode) dimension.
        X = csc_matrix((grp["data"][()], grp["indices"][()], grp["indptr"][()]),
                       shape=(grp["shape"][0], grp["shape"][1])).T.tocsr()
        barcodes = [b.decode() for b in grp["barcodes"][()]]
        genes = [g.decode() for g in grp["features"]["name"][()]]
    return X, barcodes, genes


def _read_tissue_positions(spatial_dir: Path, scale: float = 1.0):
    """Return dict: barcode -> (pxl_row, pxl_col) for in-tissue spots.

    Supports both standard Visium (tissue_positions_list.csv, header
    barcode,in_tissue,array_row,array_col,pxl_row,pxl_col) and Visium HD
    (tissue_positions.parquet with columns barcode, pxl_row_in_fullres,
    pxl_col_in_fullres). HD parquet coordinates are in FULLRES pixels and are
    multiplied by `scale` (= tissue_hires_scalef) to map into the hires image
    coordinate system used by crop_patch.
    """
    csv = spatial_dir / "tissue_positions_list.csv"
    if not csv.exists():
        csv = spatial_dir / "tissue_positions.csv"
    # Visium HD places the parquet under spatial/ (same dir as the hires png)
    parquet = spatial_dir / "tissue_positions.parquet"
    if not parquet.exists():
        parquet = spatial_dir.parent / "tissue_positions.parquet"
    if parquet.exists():
        try:
            import pandas as pd
            df = pd.read_parquet(parquet)
            coord_map = {}
            row_c = "pxl_row_in_fullres" if "pxl_row_in_fullres" in df else "pxl_row"
            col_c = "pxl_col_in_fullres" if "pxl_col_in_fullres" in df else "pxl_col"
            for _, r in df.iterrows():
                coord_map[str(r["barcode"])] = (
                    float(r[row_c]) * scale, float(r[col_c]) * scale)
            return coord_map
        except Exception as e:
            print(f"  [warn] parquet positions failed: {e}")
    import csv as _csv
    coord_map = {}
    with open(csv) as fh:
        rd = _csv.reader(fh)
        header = next(rd, None)
        started = False
        if header and header[0].strip().lower() == "barcode":
            started = True  # skip header row
        else:
            rd = itertools.chain([header], rd)  # no header: rewind
        for r in rd:
            if len(r) < 6:
                continue
            barcode = r[0]
            in_tissue = r[1]
            if in_tissue not in ("1", "True", "true"):
                continue
            pxl_row, pxl_col = float(r[-2]), float(r[-1])
            # v2026-09-15 FIX: standard Visium tissue_positions CSV stores
            # FULLRES pixel coordinates. They MUST be scaled into hires-image
            # coordinates (x = fullres * tissue_hires_scalef), exactly like the
            # Visium HD parquet branch above. Previously this scale argument was
            # silently ignored, so any dataset whose hires image is a true
            # ~2000px thumbnail (hires_scalef < 1; e.g. GSE217237 ectocervix
            # 0.041, the 10x cervical_cancer_1 0.145) produced out-of-image crop
            # centres -> PIL clamped every crop to the same corner -> every
            # spot got an IDENTICAL patch. Datasets with hires_scalef=1.0
            # (GSE208654, fullres-size hires) were numerically unaffected.
            coord_map[barcode] = (pxl_row * scale, pxl_col * scale)
    return coord_map


def _find_hd_paths(sample_dir: Path):
    """Detect Visium HD layout. Returns (h5_path, spatial_dir, is_hd).

    Compatible with both standard Visium and Visium HD at any binning
    resolution (auto-discovers square_002um / square_008um / square_016um / …)
    so colon-HD datasets with an uncommon binning still load without code
    changes.
    """
    # standard Visium
    std_h5 = sample_dir / "filtered_feature_bc_matrix.h5"
    std_spatial = sample_dir / "spatial"
    if std_h5.exists() and (std_spatial / "tissue_hires_image.png").exists() \
            and (std_spatial / "scalefactors_json.json").exists():
        return std_h5, std_spatial, False
    # Visium HD: binned_outputs/<any square>/filtered_feature_bc_matrix.h5
    # auto-scan subdirectories instead of hard-coding only 2um/8um.
    binned_root = sample_dir / "binned_outputs"
    if binned_root.exists():
        # Sorting strategy: prefer 008um (8 um) → 016um → others → avoid
        # 002um by default since 2um bins typically produce 5~8M spots which
        # cause 500+ GiB dense arrays on 4090-class GPUs.
        def _bin_priority(hd_path: Path):
            if "008um" in hd_path.name:
                return 0
            if "016um" in hd_path.name:
                return 1
            if "002um" in hd_path.name:
                return 99  # only use if nothing else available
            return 2
        candidates = sorted(
            [p for p in binned_root.iterdir() if p.is_dir()],
            key=_bin_priority,
        )
        for hd in candidates:
            h5 = hd / "filtered_feature_bc_matrix.h5"
            if not h5.exists():
                continue
            # Prefer the bin-specific spatial/ dir (has scalefactors_json.json
            # AND tissue_positions.parquet). Only fall back to the top-level
            # sample_dir/spatial/ if it ALSO has scalefactors_json.json
            # (otherwise we end up with hires image but no way to scale spots).
            bin_sp = hd / "spatial"
            top_sp = sample_dir / "spatial"
            sp = None
            if (bin_sp / "scalefactors_json.json").exists() \
                    and (bin_sp / "tissue_hires_image.png").exists():
                sp = bin_sp
            elif (top_sp / "scalefactors_json.json").exists() \
                    and (top_sp / "tissue_hires_image.png").exists():
                sp = top_sp
            elif (bin_sp / "scalefactors_json.json").exists():
                # scalefactors is mandatory; hires at top_sp still OK because
                # later _read_tissue_positions scales into hires coordinates
                sp = bin_sp
                # but if hires also lives at bin_sp use that, else leave sp as
                # bin_sp (and we'll check img_path fallback in load_sample)
            else:
                continue
            return h5, sp, True
    return None, None, False


def load_sample(sample_dir: Path) -> STSample:
    sample_dir = Path(sample_dir)
    name = sample_dir.name
    h5_path, spatial_dir, is_hd = _find_hd_paths(sample_dir)
    if h5_path is None:
        raise FileNotFoundError(f"No Visium (standard or HD) data found in {sample_dir}")

    sf_path = spatial_dir / "scalefactors_json.json"
    if not sf_path.exists():
        sf_path = h5_path.parent / "scalefactors_json.json"
    with open(sf_path) as fh:
        sf = json.load(fh)

    X, barcodes, genes = _read_10x_h5(h5_path)

    # For Visium HD, the top-level sample_dir/spatial/ often has the
    # true hires image while the bin-specific spatial/ has a smaller
    # copy. Prefer whichever exists; bin-specific is the default.
    img_path = spatial_dir / "tissue_hires_image.png"
    if (not img_path.exists() or img_path.stat().st_size == 0) and is_hd:
        alt = sample_dir / "spatial" / "tissue_hires_image.png"
        if alt.exists() and alt.stat().st_size > 0:
            img_path = alt

    # v2026-09-03: GEO datasets often omit H&E images (only h5 + scalefactors
    # + tissue_positions). Fallback chain: hires → lowres → placeholder.
    # The placeholder is a blank RGB image sized so that spot coords map
    # correctly; FM backbone will extract flat features but the expression
    # reconstruction + spatial-coherence + HPV-pathway losses still work.
    if not img_path.exists() or img_path.stat().st_size == 0:
        alt_lo = spatial_dir / "tissue_lowres_image.png"
        if alt_lo.exists() and alt_lo.stat().st_size > 0:
            img_path = alt_lo
        else:
            alt_lo2 = h5_path.parent / "tissue_lowres_image.png"
            if alt_lo2.exists() and alt_lo2.stat().st_size > 0:
                img_path = alt_lo2

    if not img_path.exists() or img_path.stat().st_size == 0:
        # placeholder: estimate size from coords + spot_diameter
        # try to read tissue_positions to get coord bounds
        try:
            coord_map = _read_tissue_positions(spatial_dir, scale=1.0)
            if not coord_map:
                coord_map = _read_tissue_positions(h5_path.parent, scale=1.0)
            all_xy = np.array(list(coord_map.values()), dtype=float)
            w = int(all_xy[:, 0].max() * 1.2) + 200
            h = int(all_xy[:, 1].max() * 1.2) + 200
        except Exception:
            w, h = 4000, 4000
        w, h = max(w, 2000), max(h, 2000)
        print(f"  [no-image fallback] {name}: generating {w}x{h} blank placeholder")
        image = Image.new("RGB", (w, h), color=(230, 230, 230))
    else:
        image = Image.open(img_path).convert("RGB")

    if is_hd:
        # HD scalefactors use `spot_diameter_fullres` (bin diameter in fullres px)
        # and `tissue_hires_scalef` (fullres->hires px ratio). The bin diameter in
        # hires px is simply the product; do NOT divide (the /6.0 heuristic was
        # wrong for 8um bins).
        spot_diam_px = float(sf.get("spot_diameter_fullres", 0)) * float(
            sf.get("tissue_hires_scalef", 1.0))
        coord_scale = float(sf.get("tissue_hires_scalef", 1.0))
    else:
        if "spot_diameter_pixels" in sf:
            # Legacy/custom layout: diameter already given in hires-image pixels
            # and positions assumed to be in the same frame (no Space Ranger
            # fullres->hires conversion).
            spot_diam_px = float(sf["spot_diameter_pixels"])
            coord_scale = 1.0
        else:
            # Standard Space Ranger: both coordinates and spot diameter live in
            # FULLRES pixels; map both into the hires-image frame with
            # tissue_hires_scalef (v2026-09-15 FIX; coord_scale was wrongly 1.0,
            # which broke every dataset with a scaled hires thumbnail).
            hires_f = float(sf.get("tissue_hires_scalef", 1.0))
            spot_diam_px = float(sf.get("spot_diameter_fullres", 0)) * hires_f
            coord_scale = hires_f

    coord_map = _read_tissue_positions(spatial_dir, scale=coord_scale)
    coords = np.array([coord_map[b] for b in barcodes], dtype=float)

    return STSample(
        name=name,
        coords=coords,
        barcodes=barcodes,
        expression=X,
        genes=genes,
        image=image,
        scalefactors=sf,
        spot_radius_px=max(spot_diam_px, 1.0) / 2.0,
    )


def crop_patch(image: Image.Image, center_xy: np.ndarray, radius_px: float,
               size: int = 64) -> np.ndarray:
    """Crop a square patch (size x size) around a spot center (hires px)."""
    cx, cy = center_xy
    left = int(round(cx - radius_px))
    top = int(round(cy - radius_px))
    right = int(round(cx + radius_px))
    bottom = int(round(cy + radius_px))
    patch = image.crop((left, top, right, bottom)).resize((size, size))
    arr = np.asarray(patch, dtype=np.float32) / 255.0
    return arr  # (size, size, 3)


def build_paired_tensors(sample: STSample, n_genes_keep: int = 2000,
                         patch_size: int = 224, max_spots: int = 0,
                         verbose: bool = True) -> dict:
    """Build paired (expression, image_patch) tensors for a single section.

    Args:
      n_genes_keep: top-variable genes to retain.
      patch_size:   H&E patch edge (224 for UNI/UNI2 foundation models).
      max_spots:    if >0 and n_spots>max_spots, subsample uniformly by spatial
                    grid so HD (hundreds of thousands of bins) fits in memory.
      verbose:      when True, print per-sample progress lines (spot count,
                    HVG pick, patch-crop %, FM ETA). This is the #1 signal the
                    user looks for to confirm "process is not stuck".

    Returns a dict with:
      exp  : (n_spots, n_genes_keep) top-variable-gene log1p expression
      img  : (n_spots, 3, patch_size, patch_size) H&E patches (NCHW)
      coords, barcodes
    """
    import time as _t
    t0 = _t.time()
    X = sample.expression
    n_spots_in = X.shape[0]
    keep_idx = None
    if max_spots and X.shape[0] > max_spots:
        # uniform spatial-grid subsample (preserves tissue coverage)
        rng = np.random.default_rng(0)
        keep_idx = np.sort(rng.choice(X.shape[0], max_spots, replace=False))
        X = X[keep_idx]
        coords = sample.coords[keep_idx]
        barcodes = [sample.barcodes[i] for i in keep_idx]
    else:
        coords = sample.coords
        barcodes = sample.barcodes
    if verbose:
        print(f"    [spots] input={n_spots_in}  retained={X.shape[0]}  "
              f"genes_raw={len(sample.genes)}  "
              f"radius_px={sample.spot_radius_px:.1f}  image_WxH={sample.image.size}",
              flush=True)

    # keep top-variable genes
    kept_gene_names = list(sample.genes)
    if n_genes_keep and n_genes_keep < X.shape[1]:
        Xd = np.asarray(X.todense(), dtype=np.float32)
        var = Xd.var(axis=0)
        keep_genes = np.argsort(var)[::-1][:n_genes_keep]
        X = X[:, keep_genes]
        kept_gene_names = [sample.genes[i] for i in keep_genes]
        if verbose:
            print(f"    [HVG] kept top {len(keep_genes)}/{Xd.shape[1]} genes by variance "
                  f"({_t.time()-t0:.1f}s)", flush=True)
    dense = np.asarray(X.todense(), dtype=np.float32)
    dense = np.log1p(dense)

    patches = []
    n_tot = len(coords)
    _last_print = 0
    t_p0 = _t.time()
    REPORT_EVERY = 500
    for ci, c in enumerate(coords):
        # tissue_positions pxl_row is y, pxl_col is x in hires image
        patch = crop_patch(sample.image, np.array([c[1], c[0]]),
                           sample.spot_radius_px, patch_size)
        patches.append(patch)
        if verbose and ((ci + 1 == n_tot) or ((ci + 1) % REPORT_EVERY == 0)):
            pct = (ci + 1) / n_tot * 100.0
            elapsed = _t.time() - t_p0
            eta_s = (elapsed / (ci + 1)) * (n_tot - ci - 1) if ci + 1 else 0.0
            # throttle print to ~once per REPORT_EVERY patches (cheap I/O)
            if (ci + 1 - _last_print) >= REPORT_EVERY or (ci + 1 == n_tot):
                print(f"    [patch crop] {ci+1:6d}/{n_tot} ({pct:5.1f}%)  "
                      f"elapsed={elapsed:5.1f}s  ETA_remain={eta_s/60:5.1f}min",
                      flush=True)
                _last_print = ci + 1
    img = np.stack(patches, axis=0).transpose(0, 3, 1, 2)  # NCHW
    if verbose:
        print(f"    [patch done] shape={img.shape}  total={_t.time()-t0:.1f}s",
              flush=True)

    return {
        "exp": torch.tensor(dense),
        "img": torch.tensor(img),
        "coords": coords,
        "barcodes": barcodes,
        "genes": kept_gene_names,
    }


def align_genes(exp, genes, common_genes):
    """Reindex a sample's expression matrix to a common gene order.

    Multi-sample training REQUIRES every sample's expression columns to encode
    the SAME gene in the SAME column. `build_paired_tensors` picks each sample's
    OWN top-variable genes (different set + different order), so naive `torch.cat`
    silently misaligns columns (sample 2's col i is NOT sample 1's gene i).

    This reorders `exp` (n_spots, n_genes) to the order of `common_genes` and
    zero-fills any gene absent from this sample (a gene not in the sample's
    panel gets 0 expression everywhere, which is the correct semantics for
    "not measured" in a shared-panel regression).

    Returns:
      exp_aligned: (n_spots, len(common_genes)) tensor (same dtype/device as exp)
    """
    import torch
    gidx = {g: i for i, g in enumerate(genes)}
    cols = [gidx[g] for g in common_genes if g in gidx]
    aligned = torch.zeros((exp.shape[0], len(common_genes)),
                          dtype=exp.dtype, device=exp.device)
    for new_j, old_i in zip([j for j, g in enumerate(common_genes) if g in gidx], cols):
        aligned[:, new_j] = exp[:, old_i]
    return aligned


if __name__ == "__main__":
    import sys
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else \
        Path(__file__).resolve().parent.parent / "data" / "st_visium" / "cervical_cancer_1"
    s = load_sample(d)
    print(f"sample={s.name} spots={s.expression.shape[0]} genes={len(s.genes)} "
          f"image={s.image.size} radius_px={s.spot_radius_px:.1f}")
    t = build_paired_tensors(s)
    print("paired exp", tuple(t["exp"].shape), "img", tuple(t["img"].shape))
