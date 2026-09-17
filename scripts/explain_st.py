"""Interpretability: occlusion-sensitivity saliency map on H&E patches.

Goal (paper-facing): *which regions of the H&E patch drive the fused
microenvironment risk score?* We use a perturbation-based attribution
(occlusion / sliding-window masking) which is backbone-agnostic and works
even with a **frozen** pathology foundation model (no gradient through the
FM needed). This is a standard, defensible interpretability method
(cf. Zeiler & Fergus, 2014; relevance for pathology in多篇 Nature 子刊).

For each spot we mask a grid of square tiles (replacing pixels with the
dataset mean), forward through the *already-trained* fusion model, and
record the absolute drop in the spot's risk score. Aggregating across spots
in a region yields a per-patch saliency heatmap, saved as PNG.

Usage
-----
    # first train and dump fused embeddings (keeps the model checkpoint-free;
    # we simply reload train_st logic). Simpler: call with --train to run a
    # short training pass then explain.
    python scripts/explain_st.py --data data/st_visium/cervical_cancer_1 \
        --fm uni --device cuda --out_dir results/explain
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import st_data as S
from src import models as M
# Reuse helpers from train_st.py (importing them here does NOT run main()
# because train_st guards CLI parsing under `if __name__ == "__main__":`).
from scripts.train_st import (
    hpv_pathway_consistency,
    build_neighbor_targets,
    HPV_RELATED_GENES,
)

MEAN_RGB = (0.81, 0.71, 0.66)  # approximate H&E mean; used as occlusion fill


def load_model_and_data(data_dir, fm, n_genes, device, epochs, bs, lr,
                        lambda_hpv=1.0, lambda_sup=3.0, lambda_recon=1.0,
                        lambda_neigh=0.3, fm_cache=False):
    root = Path(data_dir)
    sample = S.load_sample(root)
    patch_size = 224 if (fm and fm.lower() != "none") else 64
    paired = S.build_paired_tensors(sample, n_genes_keep=n_genes, patch_size=patch_size)
    exp = paired["exp"].to(device)
    genes = paired["genes"]
    # Keep raw images on CPU for now. For saliency/occlusion downstream we
    # ALWAYS need the raw (N, 3, H, W) pixel tensor — the FM cache optimisation
    # only replaces the image tensor *inside the training DataLoader*.
    raw_img = paired["img"]
    train_img = raw_img  # may be swapped for cached backbone feats below
    coords = paired["coords"]

    # HPV proxy supervised loss (same scheme as train_st.py / cross_validation.py)
    hpv_idx = [i for i, g in enumerate(genes) if g in HPV_RELATED_GENES]
    has_probe = len(hpv_idx) >= 2
    if has_probe:
        hpv_proxy = exp[:, hpv_idx].mean(dim=1)
        hpv_thr = float(hpv_proxy.median().item())
        hpv_y = (hpv_proxy >= hpv_thr).float()  # (N,)
        fused_sup_head = nn.Linear(128, 1).to(device)
        fused_sup_loss_fn = nn.BCEWithLogitsLoss()
    else:
        hpv_y = torch.zeros(exp.shape[0])
        fused_sup_head = None
        fused_sup_loss_fn = None
    hpv_y_np = hpv_y.cpu()

    img_encoder = None
    if fm and fm.lower() != "none":
        from src.foundation_encoder import (
            FoundationMorphologyEncoder,
            precompute_fm_backbone_cache,
            DualModeEncoder,
        )
        full_encoder = FoundationMorphologyEncoder(name=fm.lower(), out_dim=128,
                                                   freeze=True).to(device)
        if fm_cache:
            # Training-side cache only: replace the training tensor with
            # precomputed backbone feats (epochs × batches skip ViT).
            # Saliency code still receives the RAW `raw_img` and feeds 4D
            # patches into the model; DualModeEncoder auto-dispatch takes care
            # of routing those through the full encoder.
            print(f"[FM cache] Precomputing backbone for explanation training "
                  f"set ({raw_img.shape[0]} spots)...")
            backbone_feats, adapter_only_enc = precompute_fm_backbone_cache(
                full_encoder, raw_img, device, batch_size=bs,
                cache_path=None, verbose=True)
            train_img = backbone_feats
            img_encoder = DualModeEncoder(full_encoder, adapter_only_enc)
        else:
            img_encoder = full_encoder
    train_img = train_img.to(device)
    coord_t = torch.tensor(coords, dtype=torch.float32)
    model = M.build_model("st_he_fusion", n_genes, img_encoder=img_encoder).to(device)
    opt = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad]
        + (list(fused_sup_head.parameters()) if fused_sup_head is not None else []),
        lr=lr, weight_decay=1e-4)
    recon_loss_fn = nn.MSELoss()
    score_loss_fn = nn.MSELoss()
    # Build dataset with exp, train_img, coords, hpv_y — matches train_st.py's
    # structure so we can reuse exactly the same losses.
    ds = TensorDataset(exp, train_img, coord_t, hpv_y)
    dl = DataLoader(ds, batch_size=bs, shuffle=True)
    model.train()
    if fused_sup_head is not None:
        fused_sup_head.train()
    for ep in range(epochs):
        tot_loss = 0.0
        n_b = 0
        for b_exp, b_img, b_coords, b_hpv in dl:
            b_img = b_img.to(device)
            out = model(b_exp, b_img)
            l_rec = recon_loss_fn(out["recon"], b_exp)
            l_hpv = hpv_pathway_consistency(out["recon"], b_exp, out["score"],
                                            genes, device, lam=lambda_hpv)
            l_neigh = torch.zeros((), device=device)
            if lambda_neigh > 0 and b_coords.shape[0] >= 4:
                neigh = build_neighbor_targets(b_coords.numpy(),
                                               out["score"].detach().squeeze(-1))
                l_neigh = score_loss_fn(out["score"], neigh.to(device))
            l_sup = torch.zeros((), device=device)
            if fused_sup_head is not None and fused_sup_loss_fn is not None:
                fused = fused_sup_head(out["fused"].detach())
                l_sup = fused_sup_loss_fn(fused.squeeze(-1), b_hpv.to(device))
            loss = (lambda_recon * l_rec
                    + l_hpv
                    + lambda_neigh * l_neigh
                    + lambda_sup * l_sup)
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot_loss += float(loss.item())
            n_b += 1
        if (ep + 1) % max(1, epochs // 5) == 0:
            print(f"  [explain train] epoch {ep+1}/{epochs}  avg_loss={tot_loss/max(n_b,1):.4f}")
    model.eval()
    # Return raw_img (NOT training feats) so saliency/visualisation code can
    # do pixel-level occlusion. `raw_img` is on CPU; callers move it per-patch.
    return model, exp, raw_img, coords


@torch.no_grad()
def saliency_map(model, img_patch, exp_vec, grid=7, tile=None, device="cpu"):
    """Occlusion saliency for a single (3,H,W) patch + its expression vector."""
    _, H, W = img_patch.shape
    if tile is None:
        tile = H // grid
    base = model(exp_vec.unsqueeze(0).to(device),
                 img_patch.unsqueeze(0).to(device))["score"].item()
    sal = np.zeros((grid, grid))
    for i in range(grid):
        for j in range(grid):
            masked = img_patch.clone()
            y0, x0 = i * tile, j * tile
            masked[:, y0:y0 + tile, x0:x0 + tile] = torch.tensor(MEAN_RGB).view(3, 1, 1)
            sc = model(exp_vec.unsqueeze(0).to(device),
                       masked.unsqueeze(0).to(device))["score"].item()
            sal[i, j] = abs(base - sc)
    return sal


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/st_visium/cervical_cancer_1")
    ap.add_argument("--fm", default="uni")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--bs", type=int, default=64)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--n_genes", type=int, default=2000)
    ap.add_argument("--grid", type=int, default=7, help="saliency grid resolution")
    ap.add_argument("--n_spots", type=int, default=50,
                    help="number of spots to attribute (for speed)")
    ap.add_argument("--out_dir", default="results/explain")
    ap.add_argument("--fm_cache", action="store_true",
                    help="3-5x speedup: cache frozen FM backbone once for training "
                         "(epochs skip ViT). Saliency/occlusion still run on RAW pixels.")
    # Loss weights — kept identical to train_st.py / cross_validation.py so the
    # explanation model is trained with the SAME objective as the main paper
    # model. Previously explain_st.py accepted none of these, causing argparse
    # crashes when users copied Step 7 commands from the runbook.
    ap.add_argument("--lambda_hpv",   type=float, default=1.0)
    ap.add_argument("--lambda_sup",   type=float, default=3.0)
    ap.add_argument("--lambda_recon", type=float, default=1.0,
                    help="reconstruction loss weight")
    ap.add_argument("--lambda_neigh", type=float, default=0.3,
                    help="spatial-coherence neighbor loss weight; 0 disables")
    ap.add_argument("--hpv_gene_set", default="default",
                    help="(P1-3) HPV-anchored gene panel used for overlay selection; "
                         "same semantics as train_st.py: default | kegg_hpv | dropout_20pct | custom:<path>")
    ap.add_argument("--histology_label_csv", default="",
                    help="(P0-2) Path to cervix_histology_labels.csv (sample_id,cin_grade,"
                         "histology_subtype,progression_ordinal). If provided, outputs "
                         "histology vs risk-score boxplot CSVs + per-sample risk CSV.")
    args = ap.parse_args()

    device = torch.device(args.device)
    Path(args.out_dir).mkdir(parents=True, exist_ok=True)

    model, exp, img, coords = load_model_and_data(
        args.data, args.fm, args.n_genes, device, args.epochs, args.bs, args.lr,
        lambda_hpv=args.lambda_hpv, lambda_sup=args.lambda_sup,
        lambda_recon=args.lambda_recon, lambda_neigh=args.lambda_neigh,
        fm_cache=args.fm_cache)

    # ---- compute risk-score distribution stats (for paper reporting) ----
    # Reported alongside saliency so readers know what score range the heatmap
    # perturbations are acting on (a 0.1 drop means something different if the
    # total range is 0.2 vs 5.0).
    model.eval()
    with torch.no_grad():
        score_np = np.concatenate([
            model(exp[i:i + args.bs].to(device),
                  img[i:i + args.bs].to(device))["score"].cpu().numpy().reshape(-1)
            for i in range(0, exp.shape[0], args.bs)
        ], axis=0)
    score_min = float(score_np.min())
    score_max = float(score_np.max())
    score_range = float(score_max - score_min)
    print(f"Risk-score distribution: min={score_min:.3f}  max={score_max:.3f}  "
          f"range={score_range:.3f}  (n_scores={len(score_np)})")

    n = min(args.n_spots, exp.shape[0])
    H = img.shape[-1]
    tile = H // args.grid
    agg = np.zeros((args.grid, args.grid))
    kept = 0
    for s in range(n):
        try:
            sm = saliency_map(model, img[s].cpu(), exp[s].cpu(),
                              grid=args.grid, tile=tile, device=device)
        except Exception as e:
            print(f"  [skip spot {s}] {e}")
            continue
        agg += sm
        kept += 1
    agg /= max(kept, 1)

    # save heatmap PNG
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.figure(figsize=(4, 4))
        plt.imshow(agg, cmap="jet", interpolation="nearest")
        plt.colorbar(label="|risk score drop|")
        plt.title(f"Occlusion saliency ({args.fm}, {kept} spots)")
        plt.axis("off")
        out_png = Path(args.out_dir) / "saliency_heatmap.png"
        plt.savefig(out_png, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"Saved {out_png}")
    except ImportError:
        print("[warn] matplotlib not installed; saved raw saliency .npy only")

    np.save(Path(args.out_dir) / "saliency_agg.npy", agg)
    json.dump({"fm": args.fm, "n_spots": kept, "grid": args.grid,
               "score_min": score_min, "score_max": score_max,
               "score_range": score_range, "n_scores_total": int(len(score_np))},
              open(Path(args.out_dir) / "saliency_meta.json", "w"), indent=2, default=str, allow_nan=False)
    print(f"Occlusion saliency done for {kept} spots (grid={args.grid}).")

    # ---- P1-3: top-HPV gene spatial overlay + risk-score scatter -----------
    # Outputs:
    #   hpv_top_overlay.csv: (x,y,risk_score,gene1_expr,gene2_expr,gene3_expr,...)
    #       — one row per spot, top-5 HPV-anchored genes with largest |mean-high - mean-low|
    #   hpv_risk_scatter.csv: (spot_idx, risk_score, mean_hpv_gene_expr)
    #       — for plotting scatter (HPV expression vs risk) in the paper
    #   (if matplotlib available) hpv_gene_spatial_overlay.png, hpv_risk_scatter.png
    try:
        from scripts.train_st import _resolve_hpv_gene_set, _ACTIVE_HPV_SET
        active = _resolve_hpv_gene_set(args.hpv_gene_set)
    except Exception:
        active = HPV_RELATED_GENES
    genes = []  # filled by scanning data_loader side-channel below via paired
    try:
        # Reload paired data once to grab the gene list (the public loader
        # returns it via `paired["genes"]`). This is cheap (<0.5 s on CPU).
        root2 = Path(args.data)
        p_size = 224 if (args.fm and args.fm.lower() != "none") else 64
        _tmp = S.load_sample(root2 if root2.is_dir() else root2.parent)
        # if data was a parent dir (multi sample) use first child
        _child = root2 if (root2 / "filtered_feature_bc_matrix.h5").exists() else \
            [c for c in sorted(root2.iterdir()) if (c / "filtered_feature_bc_matrix.h5").exists()][0]
        _p = S.build_paired_tensors(S.load_sample(_child), n_genes_keep=args.n_genes,
                                    patch_size=p_size)
        genes = _p["genes"]
        _coords_full = _p["coords"]
        _exp_full_np = _p["exp"].cpu().numpy() if hasattr(_p["exp"], "cpu") else np.asarray(_p["exp"])
    except Exception as e:
        print(f"[warn] HPV spatial overlay: cannot reload paired data ({e}); skipping")
        _coords_full = None
        _exp_full_np = None

    if _coords_full is not None and _exp_full_np is not None and len(genes) >= 5 and len(score_np) == len(_coords_full):
        gi_map = {g: i for i, g in enumerate(genes)}
        active_idx = [(g, gi_map[g]) for g in active if g in gi_map]
        # choose top-5 HPV genes with largest absolute high-vs-low expression gap
        thr = float(np.median(score_np))
        high = score_np >= thr
        gaps = []
        for g, gi in active_idx:
            a = float(_exp_full_np[high, gi].mean()) if high.any() else 0.0
            b = float(_exp_full_np[~high, gi].mean()) if (~high).any() else 0.0
            gaps.append((abs(a - b), g, gi, a - b))
        gaps.sort(reverse=True)
        top_gaps = gaps[:5]
        print(f"[HPV overlay] top-5 HPV-panel genes by high/low expression gap:")
        for mg, g, _gi, _d in top_gaps:
            print(f"  {g}: |gap|={mg:.3f}  delta={_d:+.3f}")
        rows = []
        hpv_expr = np.zeros(len(score_np))
        for i in range(len(score_np)):
            row = {"pxl_col": float(_coords_full[i, 0]),
                   "pxl_row": float(_coords_full[i, 1]),
                   "risk_score": float(score_np[i])}
            for _, g, gi, _d in top_gaps:
                row[g] = float(_exp_full_np[i, gi])
            rows.append(row)
            # HPV mean expression: mean of all active-panel genes (not just top 5)
            if active_idx:
                hpv_expr[i] = float(np.mean([_exp_full_np[i, gi] for _, gi in active_idx]))
        import csv as _csv
        overlay_csv = Path(args.out_dir) / "hpv_gene_spatial_overlay.csv"
        with open(overlay_csv, "w", newline="") as f:
            w = _csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"Saved {overlay_csv}  (top HPV genes: {[g for _,g,_,_ in top_gaps]})")
        # scatter CSV
        scatter_csv = Path(args.out_dir) / "hpv_risk_scatter.csv"
        with open(scatter_csv, "w", newline="") as f:
            w = _csv.writer(f)
            w.writerow(["spot_idx", "risk_score", "mean_hpv_gene_expr", "high_risk"])
            for i in range(len(score_np)):
                w.writerow([i, float(score_np[i]), float(hpv_expr[i]), int(bool(high[i]))])
        print(f"Saved {scatter_csv}")
        # figures
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            fig, axes = plt.subplots(1, 2, figsize=(10, 4))
            # (A) HPV mean vs risk score scatter
            axes[0].scatter(hpv_expr, score_np, s=4, alpha=0.5, c=score_np, cmap="coolwarm")
            axes[0].set_xlabel("Mean HPV-panel gene expr (z)")
            axes[0].set_ylabel("Per-spot risk score")
            axes[0].set_title("HPV-anchored expression vs Risk score")
            # Spearman correlation for caption
            from scipy.stats import spearmanr
            rho, _pv = spearmanr(hpv_expr, score_np)
            axes[0].text(0.02, 0.98, f"Spearman rho={rho:.3f}",
                         transform=axes[0].transAxes, va="top", fontsize=9)
            # (B) spatial risk overlay colored by score
            sc = axes[1].scatter(_coords_full[:, 0], -_coords_full[:, 1],
                                 c=score_np, s=6, cmap="coolwarm", alpha=0.7)
            axes[1].set_aspect("equal", adjustable="datalim")
            axes[1].set_xlabel("pxl_col")
            axes[1].set_ylabel("-pxl_row (flip Y for image coords)")
            axes[1].set_title("Per-spot risk score (spatial)")
            plt.colorbar(sc, ax=axes[1], label="risk score")
            fig.tight_layout()
            fig_png = Path(args.out_dir) / "hpv_gene_spatial_overlay.png"
            fig.savefig(fig_png, dpi=150, bbox_inches="tight")
            plt.close(fig)
            print(f"Saved {fig_png}")
        except Exception as e:
            print(f"[warn] HPV overlay figure failed: {e}")

    # ---- P0-2: histology-vs-risk boxplot CSV (if label CSV given) ---------
    if args.histology_label_csv and Path(args.histology_label_csv).exists() and _coords_full is not None:
        try:
            import pandas as pd
            hdf = pd.read_csv(args.histology_label_csv)
            # try to find sample_id matching: the input `args.data` basename
            data_name = Path(args.data).name
            match_row = hdf[hdf["sample_id"].astype(str).str.strip() == data_name]
            if len(match_row) == 0:
                # try parent directory name (if user pointed to a single-sample dir)
                parent_name = Path(args.data).parent.name
                match_row = hdf[hdf["sample_id"].astype(str).str.strip() == parent_name]
            if len(match_row) > 0:
                row = match_row.iloc[0]
                label_row = {"sample_id": data_name,
                             "cin_grade": row.get("cin_grade"),
                             "histology_subtype": row.get("histology_subtype"),
                             "progression_ordinal": row.get("progression_ordinal"),
                             "risk_median": float(np.median(score_np)),
                             "risk_mean": float(np.mean(score_np)),
                             "risk_std": float(np.std(score_np)),
                             "n_spots": int(len(score_np))}
                out_csv = Path(args.out_dir) / "histology_risk_row.csv"
                pd.DataFrame([label_row]).to_csv(out_csv, index=False)
                print(f"Saved {out_csv} -> {label_row}")
                # also write a "spot-level" CSV for the paper's boxplot:
                # cin_grade / histology_subtype / risk_score — every spot 1 row
                spots_csv = Path(args.out_dir) / "histology_risk_spot_boxplot.csv"
                _df = pd.DataFrame({
                    "cin_grade": [row.get("cin_grade")] * len(score_np),
                    "histology_subtype": [row.get("histology_subtype")] * len(score_np),
                    "sample_id": [data_name] * len(score_np),
                    "risk_score": score_np.astype(float),
                })
                _df.to_csv(spots_csv, index=False)
                print(f"Saved {spots_csv} (spot-level, for boxplot)")
            else:
                print(f"[warn] histology_label_csv has no row matching sample_id "
                      f"`{data_name}` or parent `{parent_name if 'parent_name' in locals() else None}`")
        except Exception as e:
            print(f"[warn] histology label output failed: {e}")


if __name__ == "__main__":
    main()
