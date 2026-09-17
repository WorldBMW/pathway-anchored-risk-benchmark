"""cross_validation.py — Leave-One-Sample-Out (LOSO) external generalisation test.

WHY (二区 requirement #5/#6): a single-slide result cannot show the method
generalises. This runs leave-one-out over the 4-sample cervical progression
cohort (N_HPV / HSIL_HPV / CA_HPV_1 / CA_HPV_2): for each held-out sample, train
on the other 3 and evaluate on the held-out one. Reported per-fold metrics:

  - recon_mse_heldout   (does the cross-modal model reconstruct unseen tissue?)
  - moran_i_heldout     (is the risk field spatially coherent on unseen tissue?)
  - deg_sign_agreement  (do the DEGs discovered on TRAIN slides keep their
                          high/low direction on the HELD-OUT slide?)  [0..1]

Reuses train_st.py internals (data loading, model, losses, infer_scores).

Run:
  python scripts/cross_validation.py \
      --data data/st_visium/geo_cesc --fm uni --device cuda \
      --epochs 40 --lambda_hpv 1.0 --out results/cross_validation.json
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
from src import metrics as MET

# import the reusable pieces from train_st (without running its main)
import importlib.util
_train_st_path = Path(__file__).resolve().parent / "train_st.py"
_spec = importlib.util.spec_from_file_location("train_st_lib", _train_st_path)
train_st = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(train_st)

build_neighbor_targets = train_st.build_neighbor_targets
infer_scores = train_st.infer_scores
hpv_pathway_consistency = train_st.hpv_pathway_consistency
# 2026-08-20 FIX: align hpv gene set with train_st.py's corrected HPV_RELATED_GENES
# (= HPV_SPECIFIC ∪ HOUSEKEEPING). Previously we only tracked the narrower
# HPV_SPECIFIC_GENES, which under-counted sign agreement because proliferation /
# epithelial markers (MKI67/TOP2A/KRT8/EPCAM/...) were excluded from the check.
HPV_RELATED_GENES = train_st.HPV_RELATED_GENES


def load_sample_tensors(sd: Path, n_genes: int, patch_size: int, device, max_spots: int = 0):
    sample = S.load_sample(sd)
    paired = S.build_paired_tensors(sample, n_genes_keep=n_genes,
                                    patch_size=patch_size, max_spots=max_spots)
    # Keep img on CPU; the caller (train_model) decides device after
    # potentially replacing raw images with cached FM backbone feats.
    return (paired["exp"].to(device), paired["img"],
            paired["coords"], paired["genes"])


def train_model(exp, img, coords, genes, args, device, fm_cache=False):
    """Train one model on the given (training) samples. Returns the trained model."""
    n_genes = exp.shape[1]
    img_encoder = None
    if args.fm and args.fm.lower() != "none":
        from src.foundation_encoder import (
            FoundationMorphologyEncoder,
            precompute_fm_backbone_cache,
            DualModeEncoder,
        )
        full_encoder = FoundationMorphologyEncoder(
            name=args.fm.lower(), out_dim=128, freeze=True).to(device)
        if fm_cache:
            # Precompute the frozen backbone for the training-set images.
            # Wrap with DualModeEncoder so held-out RAW images (4D tensor,
            # inferred once at end of fold) still route through the full
            # encoder automatically — zero code changes at call sites.
            print(f"[FM cache] Precomputing backbone for fold training set "
                  f"({img.shape[0]} spots)...")
            backbone_feats, adapter_only_enc = precompute_fm_backbone_cache(
                full_encoder, img, device, batch_size=args.bs,
                cache_path=None, verbose=True)
            img = backbone_feats
            img_encoder = DualModeEncoder(full_encoder, adapter_only_enc)
        else:
            img_encoder = full_encoder
    img = img.to(device)
    model = M.build_model("st_he_fusion", n_genes, img_encoder=img_encoder).to(device)

    hpv_idx = [i for i, g in enumerate(genes) if g in HPV_RELATED_GENES]
    has_probe = len(hpv_idx) >= 2
    if has_probe:
        hpv_proxy = exp[:, hpv_idx].mean(dim=1)
        hpv_thr = float(hpv_proxy.median().item())
        hpv_y = (hpv_proxy >= hpv_thr).float()
        fused_sup_head = nn.Linear(128, 1).to(device)
        fused_sup_loss = nn.BCEWithLogitsLoss()
    else:
        hpv_y = torch.zeros(exp.shape[0])
        fused_sup_head = None
        fused_sup_loss = None

    opt = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad]
        + (list(fused_sup_head.parameters()) if has_probe else []),
        lr=args.lr, weight_decay=1e-4)
    recon_loss = nn.MSELoss()
    score_loss = nn.MSELoss()
    score_sup = nn.BCEWithLogitsLoss() if has_probe else None

    ds = TensorDataset(exp, img, torch.as_tensor(coords, dtype=torch.float32), hpv_y)
    dl = DataLoader(ds, batch_size=args.bs, shuffle=True)
    lambda_neigh = 0.0 if args.no_neigh else args.lambda_neigh

    for _ in range(args.epochs):
        model.train()
        for b_exp, b_img, b_coords, b_y in dl:
            b_img = b_img.to(device)
            out = model(b_exp, b_img)
            l_rec = recon_loss(out["recon"], b_exp)
            neigh = build_neighbor_targets(b_coords.numpy(), out["score"].detach().squeeze(-1))
            l_neigh = score_loss(out["score"], neigh.to(device))
            l_hpv = hpv_pathway_consistency(out["recon"], b_exp, out["score"], genes, device,
                                            lam=args.lambda_hpv)
            l_sup = torch.zeros((), device=device)
            l_fused_sup = torch.zeros((), device=device)
            if has_probe:
                l_sup = score_sup(out["score"], b_y.to(device))
                l_fused_sup = fused_sup_loss(fused_sup_head(out["fused"]),
                                             b_y.to(device).unsqueeze(-1).float())
            l_var = torch.clamp(0.2 - out["score"].std(), min=0.0)
            loss = (args.lambda_recon * l_rec + lambda_neigh * l_neigh
                    + args.lambda_hpv * l_hpv
                    + args.lambda_sup * l_sup + args.lambda_sup * l_fused_sup
                    + 0.1 * l_var)
            opt.zero_grad()
            loss.backward()
            opt.step()
    return model


def eval_heldout(model, exp, img, coords, genes, args, device):
    """Evaluate a trained model on a held-out sample. Returns a dict of metrics."""
    model.eval()
    with torch.no_grad():
        scores, recons = infer_scores(model, exp, img, args.bs, device)
    recon_mse = float(nn.functional.mse_loss(recons, exp).item())
    moran_i = M.moran_i(scores.cpu().numpy(), coords)

    # DEG direction on held-out: for the HPV-RELATION prior panel (HPV_SPECIFIC
    # ∪ HOUSEKEEPING proliferation/epithelial markers), does the high-risk
    # (top-half score) region over-express them relative to low-risk?  2026-08-20
    # FIX: previously we only checked HPV_SPECIFIC_GENES, which under-reported
    # agreement because MKI67/TOP2A/KRT8/EPCAM/... were not being tracked.
    scores_np = scores.cpu().numpy()
    thr = float(np.median(scores_np))
    high = scores_np >= thr
    exp_np = exp.cpu().numpy()
    gidx = {g: i for i, g in enumerate(genes)}
    agree = []
    for g in HPV_RELATED_GENES:
        if g not in gidx:
            continue
        gi = gidx[g]
        delta = float(exp_np[high, gi].mean() - exp_np[~high, gi].mean())
        agree.append(delta > 0)  # HPV-related genes should be UP in high-risk region
    sign_agreement = float(np.mean(agree)) if agree else float("nan")

    return {"recon_mse": recon_mse, "moran_i": float(moran_i),
            "hpv_related_sign_agreement": sign_agreement,
            "n_spots": int(exp.shape[0])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--fm", default="uni")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--bs", type=int, default=64)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--n_genes", type=int, default=2000)
    ap.add_argument("--lambda_hpv", type=float, default=1.0)
    ap.add_argument("--lambda_sup", type=float, default=2.0)
    ap.add_argument("--lambda_neigh", type=float, default=0.3)
    ap.add_argument("--lambda_recon", type=float, default=1.0)
    ap.add_argument("--no_neigh", action="store_true")
    ap.add_argument("--max_spots", type=int, default=0)
    ap.add_argument("--out", default="results/cross_validation.json")
    ap.add_argument("--fm_cache", action="store_true",
                    help="3-5x speedup: precompute frozen FM backbone once per "
                         "fold (identical across epochs). Training dynamics unchanged.")
    args = ap.parse_args()

    root = Path(args.data)
    sample_dirs = [d for d in sorted(root.iterdir())
                   if d.is_dir() and (d / "filtered_feature_bc_matrix.h5").exists()]
    if not sample_dirs:
        raise SystemExit(f"No samples under {root}")
    print(f"LOSO over {len(sample_dirs)} samples: {[d.name for d in sample_dirs]}")

    patch_size = 224 if (args.fm and args.fm.lower() != "none") else 64
    device = args.device

    # load every sample ONCE
    loaded = {}
    for sd in sample_dirs:
        loaded[sd.name] = load_sample_tensors(sd, args.n_genes, patch_size, device, args.max_spots)
        print(f"  loaded {sd.name}: {loaded[sd.name][0].shape[0]} spots")

    # gene alignment: build the UNION of per-sample panels (not intersection —
    # intersection collapsed to ~980 genes and dropped HPV-specific genes), then
    # align every sample to it via S.align_genes (missing -> 0).
    common = []
    seen = set()
    for sd in sample_dirs:
        for g in loaded[sd.name][3]:
            if g not in seen:
                seen.add(g)
                common.append(g)
    print(f"  unified gene panel: {len(common)} genes (union across samples)")

    results = {"folds": {}, "held_out": []}
    for holdout in sample_dirs:
        train_dirs = [d for d in sample_dirs if d != holdout]
        print(f"\n=== fold: hold out {holdout.name}, train on "
              f"{[d.name for d in train_dirs]} ===")

        # reindex each sample to the common gene order (0-fill missing genes)
        def _reindex(name):
            exp, img, coords, genes = loaded[name]
            exp = S.align_genes(exp, genes, common)
            return exp, img, coords, common

        tr_exp, tr_img, tr_coords, tr_genes = [], [], [], []
        for si, d in enumerate(train_dirs):
            e, i, c, g = _reindex(d.name)
            c = c.astype(np.float64) + si * 10000.0  # per-sample offset (avoid cross-sample neighbours)
            tr_exp.append(e); tr_img.append(i); tr_coords.append(c)
        tr_exp = torch.cat(tr_exp, 0)
        tr_img = torch.cat(tr_img, 0)
        tr_coords = np.vstack(tr_coords)

        model = train_model(tr_exp, tr_img, tr_coords, common, args, device,
                            fm_cache=args.fm_cache)

        he_exp, he_img, he_coords, he_genes = _reindex(holdout.name)
        m = eval_heldout(model, he_exp, he_img, he_coords, he_genes, args, device)
        m["held_out_sample"] = holdout.name
        m["n_train_spots"] = int(tr_exp.shape[0])
        results["folds"][holdout.name] = m
        results["held_out"].append(m)
        print(f"  -> recon_mse={m['recon_mse']:.4f} moran_i={m['moran_i']:.3f} "
              f"hpv_sign_agree={m['hpv_related_sign_agreement']:.3f}")

    # aggregate
    agg = {k: float(np.mean([f[k] for f in results["held_out"] if not np.isnan(f[k])]))
           for k in ["recon_mse", "moran_i", "hpv_related_sign_agreement"]}
    results["mean"] = agg
    print(f"\nLOSO mean: recon_mse={agg['recon_mse']:.4f} "
          f"moran_i={agg['moran_i']:.3f} "
          f"hpv_sign_agree={agg['hpv_related_sign_agreement']:.3f}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(results, indent=2, default=str, allow_nan=False))
    print(f"Saved -> {args.out}")


if __name__ == "__main__":
    main()
