"""infer_st.py — Load a trained ST+HE checkpoint and score external cohorts.

Supports:
  - Standard Visium (filtered_feature_bc_matrix.h5 + spatial/)
  - GEO mtx format (barcodes.tsv.gz + features.tsv.gz + matrix.mtx.gz + spatial/)
  - Full multimodal model (expression + UNI image)  OR  expression-only fallback

Usage (cervical-trained checkpoint on HNSCC cross-organ validation):
    python scripts/infer_st.py \
        --checkpoint results/checkpoint_MAIN_KEGG_seed42.pt \
        --data data/st_visium/geo_hnscc_hpv_GSE268014 \
        --run_id XCOHORT_HNSCC \
        --device cuda

Usage (expression-only fallback, no FM needed):
    python scripts/infer_st.py \
        --checkpoint results/checkpoint_MAIN_KEGG_seed42.pt \
        --data data/st_visium/geo_hnscc_hpv_GSE268014 \
        --run_id XCOHORT_HNSCC \
        --expression_only \
        --device cpu
"""
from __future__ import annotations
import argparse
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from src.models import GeneEncoder, STHEFusionModel, moran_i
from src.st_data import _read_tissue_positions, crop_patch


# ---------------------------------------------------------------------------
# Data loading: support both h5 and mtx
# ---------------------------------------------------------------------------

def _read_mtx(sample_dir: Path):
    """Read 10x mtx format -> (X_sparse spots x genes, barcodes, genes)."""
    from scipy.io import mmread
    from scipy.sparse import csr_matrix

    mtx_path = sample_dir / "matrix.mtx.gz"
    feat_path = sample_dir / "features.tsv.gz"
    bc_path = sample_dir / "barcodes.tsv.gz"

    if not (mtx_path.exists() and feat_path.exists() and bc_path.exists()):
        return None, None, None

    mat = mmread(mtx_path).tocsc()  # (genes x spots)
    with gzip.open(feat_path, "rt") as f:
        raw_genes = [line.strip().split("\t")[1] for line in f]  # column 1 = gene name
    # Strip common GEO prefixes (e.g. "GRCh38_IGKC" -> "IGKC", "GRCh38_AL627309.1" -> "AL627309.1")
    genes = [g[len("GRCh38_"):] if g.startswith("GRCh38_") else g
             for g in raw_genes]
    with gzip.open(bc_path, "rt") as f:
        barcodes = [line.strip() for line in f]
    X = mat.T.tocsr()  # (spots x genes)
    return X, barcodes, genes


def _read_h5(sample_dir: Path):
    from src.st_data import _read_10x_h5
    h5 = sample_dir / "filtered_feature_bc_matrix.h5"
    if not h5.exists():
        return None, None, None
    return _read_10x_h5(h5)


def load_sample_external(sample_dir: Path):
    """Load an external sample supporting both h5 and mtx formats.

    Returns dict with: name, X (csr), barcodes, genes, coords, image,
    scalefactors, spot_radius_px. Returns None if neither format found.
    """
    sample_dir = Path(sample_dir)
    name = sample_dir.name

    # Try h5 first, then mtx
    X, barcodes, genes = _read_h5(sample_dir)
    if X is None:
        X, barcodes, genes = _read_mtx(sample_dir)
    if X is None:
        print(f"  [skip] {name}: no h5 or mtx found")
        return None

    # Spatial info
    spatial_dir = sample_dir / "spatial"
    if not spatial_dir.exists():
        # Some GEO datasets put spatial at parent or inside sample
        for cand in [sample_dir / "outs" / "spatial", sample_dir.parent / "spatial"]:
            if cand.exists():
                spatial_dir = cand
                break

    sf_path = spatial_dir / "scalefactors_json.json"
    if not sf_path.exists():
        sf_path = sample_dir / "scalefactors_json.json"
    if sf_path.exists():
        with open(sf_path) as fh:
            sf = json.load(fh)
    else:
        sf = {"tissue_hires_scalef": 1.0, "spot_diameter_fullres": 89.0}
        print(f"  [warn] {name}: no scalefactors_json.json, using defaults")

    # Tissue positions
    coords_map = _read_tissue_positions(spatial_dir, scale=sf.get("tissue_hires_scalef", 1.0))
    # Filter to in-tissue barcodes that have coords
    valid = [(i, coords_map[b]) for i, b in enumerate(barcodes) if b in coords_map]
    if not valid:
        print(f"  [warn] {name}: no in-tissue spots with coordinates")
        return None
    keep_idx = [i for i, _ in valid]
    coords = np.array([c for _, c in valid], dtype=np.float32)
    X = X[keep_idx]
    barcodes = [barcodes[i] for i in keep_idx]

    # Image
    img_path = spatial_dir / "tissue_hires_image.png"
    if not img_path.exists():
        img_path = sample_dir / "tissue_hires_image.png"
    if img_path.exists():
        from PIL import Image
        image = Image.open(img_path).convert("RGB")
    else:
        # blank placeholder
        w = int(coords[:, 0].max()) + 100 if len(coords) else 1000
        h = int(coords[:, 1].max()) + 100 if len(coords) else 1000
        from PIL import Image
        image = Image.new("RGB", (max(w, 224), max(h, 224)), (200, 200, 200))
        print(f"  [warn] {name}: no H&E image, using blank placeholder")

    spot_radius_px = float(sf.get("spot_diameter_fullres", 89.0)) * 0.5 * sf.get("tissue_hires_scalef", 1.0)

    return {
        "name": name,
        "X": X,
        "barcodes": barcodes,
        "genes": genes,
        "coords": coords,
        "image": image,
        "scalefactors": sf,
        "spot_radius_px": spot_radius_px,
    }


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def load_model(checkpoint_path: Path, device: torch.device,
               expression_only: bool = False):
    """Load checkpoint and rebuild model. Returns (model, genes, fm_name, mode)."""
    ckpt = torch.load(checkpoint_path, map_location="cpu")
    genes = list(ckpt["genes"])
    n_genes = int(ckpt.get("n_genes", len(genes)))
    fm_name = ckpt.get("fm", "none")
    sd = ckpt["model_state_dict"]

    # ---- Try full multimodal model ----
    if not expression_only:
        try:
            from src.foundation_encoder import FoundationMorphologyEncoder
            img_enc = FoundationMorphologyEncoder(fm_name, out_dim=128, freeze=True)
            model = STHEFusionModel(n_genes, img_encoder=img_enc).to(device)
            model.load_state_dict(sd, strict=True)
            model.eval()
            print(f"[model] loaded FULL multimodal (fm={fm_name}, genes={n_genes})")
            return model, genes, fm_name, "full"
        except Exception as e:
            print(f"[model] full model load failed ({e}); falling back to expression-only")

    # ---- Expression-only branch (gene_enc + head) ----
    gene_enc = GeneEncoder(n_genes, hidden=256, out=128).to(device)
    head = nn.Sequential(
        nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, 1),
    ).to(device)
    gene_enc_sd = {k[len("gene_enc."):]: v for k, v in sd.items()
                   if k.startswith("gene_enc.")}
    head_sd = {k[len("head."):]: v for k, v in sd.items()
               if k.startswith("head.")}
    gene_enc.load_state_dict(gene_enc_sd)
    head.load_state_dict(head_sd)
    gene_enc.eval()
    head.eval()
    # Wrap into a callable that mimics model(gene, img) -> score
    class ExprOnlyModel(nn.Module):
        def __init__(self, enc, hd):
            super().__init__()
            self.gene_enc = enc
            self.head = hd
        def forward(self, gene, img=None):
            return self.head(self.gene_enc(gene)).squeeze(-1)
    model = ExprOnlyModel(gene_enc, head).to(device)
    print(f"[model] loaded expression-only branch (genes={n_genes})")
    return model, genes, fm_name, "expr_only"


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------

@torch.no_grad()
def score_sample(model, sample, genes, device, mode: str,
                 patch_size: int = 224, max_spots: int = 30000,
                 inner_chunk: int = 32):
    """Run inference on a single sample. Returns per-spot risk scores + Moran's I."""
    X = sample["X"]
    coords = sample["coords"]
    barcodes = sample["barcodes"]
    spot_radius = sample["spot_radius_px"]
    image = sample["image"]

    # Subsample if too many spots
    if max_spots and X.shape[0] > max_spots:
        rng = np.random.default_rng(0)
        keep = np.sort(rng.choice(X.shape[0], max_spots, replace=False))
        X = X[keep]
        coords = coords[keep]
        barcodes = [barcodes[i] for i in keep]

    # Align genes to checkpoint panel
    gene_to_col = {g: i for i, g in enumerate(sample["genes"])}
    # Build expression matrix in checkpoint gene order
    Xd = np.asarray(X.todense(), dtype=np.float32)
    X_aligned = np.zeros((Xd.shape[0], len(genes)), dtype=np.float32)
    for j, g in enumerate(genes):
        if g in gene_to_col:
            X_aligned[:, j] = Xd[:, gene_to_col[g]]
    del Xd

    # log1p normalize (same as training)
    X_aligned = np.log1p(X_aligned)

    n_spots = X_aligned.shape[0]
    scores = np.zeros(n_spots, dtype=np.float32)
    batch_size = 256

    for i in range(0, n_spots, batch_size):
        j = min(i + batch_size, n_spots)
        x_gene = torch.from_numpy(X_aligned[i:j]).to(device)

        if mode == "full":
            # Crop image patches
            patches = []
            for c in coords[i:j]:
                p = crop_patch(image, np.array([c[1], c[0]]), spot_radius, patch_size)
                patches.append(p)
            x_img = torch.from_numpy(
                np.stack(patches, axis=0).transpose(0, 3, 1, 2)
            ).float().to(device)
            scores[i:j] = model(x_gene, x_img).cpu().numpy()
        else:
            scores[i:j] = model(x_gene).cpu().numpy()

    mi = moran_i(scores, coords)
    return {
        "name": sample["name"],
        "n_spots": int(n_spots),
        "mean_score": float(scores.mean()),
        "std_score": float(scores.std()),
        "median_score": float(np.median(scores)),
        "moran_i": float(mi),
        "scores": scores.tolist(),
        "barcodes": barcodes,
        "coords": coords.tolist(),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True, type=Path)
    ap.add_argument("--data", required=True, type=Path,
                    help="Directory containing sample subdirectories")
    ap.add_argument("--run_id", default="INFER", type=str)
    ap.add_argument("--device", default="cuda", type=str)
    ap.add_argument("--expression_only", action="store_true",
                    help="Use expression branch only (no FM image encoder)")
    ap.add_argument("--max_spots", type=int, default=30000)
    ap.add_argument("--only", type=str, default=None,
                    help="Comma-separated allowlist of sample directory names to infer "
                         "(e.g. GSM8283897,GSM8283898); all other subdirectories are skipped.")
    ap.add_argument("--fm", type=str, default=None,
                    help="Override FM name (default: from checkpoint)")
    ap.add_argument("--out_dir", type=Path, default=ROOT / "results")
    args = ap.parse_args()

    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    print(f"[device] {device}")

    # Load model
    model, genes, fm_name, mode = load_model(args.checkpoint, device, args.expression_only)
    if args.fm:
        fm_name = args.fm
    print(f"[mode] {mode}  [fm] {fm_name}  [genes] {len(genes)}")

    # Discover samples
    data_dir = Path(args.data)
    sample_dirs = sorted([p for p in data_dir.iterdir() if p.is_dir()])
    if args.only:
        allow = {s.strip() for s in args.only.split(",") if s.strip()}
        missing = allow - {p.name for p in sample_dirs}
        if missing:
            raise SystemExit(f"[error] --only samples not found under {data_dir}: {sorted(missing)}")
        sample_dirs = [p for p in sample_dirs if p.name in allow]
    # If data_dir itself is a sample, use it
    if not sample_dirs:
        sample_dirs = [data_dir]

    print(f"[discover] {len(sample_dirs)} sample directories")

    all_results = []
    for sd in sample_dirs:
        print(f"\n[sample] {sd.name}")
        sample = load_sample_external(sd)
        if sample is None:
            continue
        print(f"  spots={sample['X'].shape[0]}  genes={len(sample['genes'])}  "
              f"matched={len([g for g in genes if g in sample['genes']])}")
        try:
            res = score_sample(model, sample, genes, device, mode,
                               max_spots=args.max_spots)
            all_results.append(res)
            print(f"  mean_score={res['mean_score']:.4f}  std={res['std_score']:.4f}  "
                  f"Moran_I={res['moran_i']:.4f}")
        except Exception as e:
            print(f"  [error] {e}")
            import traceback
            traceback.print_exc()

    # Summary
    summary = {
        "run_id": args.run_id,
        "checkpoint": str(args.checkpoint),
        "mode": mode,
        "fm": fm_name,
        "n_genes": len(genes),
        "n_samples": len(all_results),
        "per_sample": [
            {
                "name": r["name"],
                "n_spots": r["n_spots"],
                "mean_score": r["mean_score"],
                "std_score": r["std_score"],
                "median_score": r["median_score"],
                "moran_i": r["moran_i"],
            }
            for r in all_results
        ],
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / f"infer_{args.run_id}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"\n[done] saved {summary_path}")

    # Also save full per-spot results
    full_path = out_dir / f"infer_{args.run_id}_full.json"
    full_path.write_text(json.dumps({"samples": all_results}, indent=2))
    print(f"[done] saved {full_path}")


if __name__ == "__main__":
    main()
