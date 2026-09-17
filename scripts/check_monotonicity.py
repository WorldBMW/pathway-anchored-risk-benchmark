"""check_monotonicity.py — Verify the CORE hypothesis of positioning A:

"Does the learned risk score increase monotonically along the cervical
progression axis (Normal < HSIL < Cancer)?"

This is the headline result for the "spatial risk quantification along
carcinogenesis" framing. If the score does NOT order the samples by disease
severity, positioning A is not viable and we must revisit the method.

Run (CPU smoke is enough to judge direction; final numbers on GPU+UNI):
  python scripts/check_monotonicity.py \
      --data data/st_visium/geo_cesc --fm none --device cpu \
      --epochs 15 --lambda_hpv 1.0
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

import importlib.util
_spec = importlib.util.spec_from_file_location("train_st_lib",
                                              str(Path(__file__).resolve().parent / "train_st.py"))
train_st = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(train_st)

build_neighbor_targets = train_st.build_neighbor_targets
infer_scores = train_st.infer_scores
HPV_SPECIFIC_GENES = train_st.HPV_SPECIFIC_GENES

# disease-progression order (severity ascending)
PROGRESSION = ["N_HPV", "HSIL_HPV", "CA_HPV_1", "CA_HPV_2"]


def load_sample(sd, n_genes, patch_size, device, max_spots=0):
    sample = S.load_sample(sd)
    paired = S.build_paired_tensors(sample, n_genes_keep=n_genes,
                                    patch_size=patch_size, max_spots=max_spots)
    return paired["exp"].to(device), paired["img"].to(device), paired["coords"], paired["genes"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--fm", default="none")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--bs", type=int, default=128)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--n_genes", type=int, default=2000)
    ap.add_argument("--lambda_hpv", type=float, default=1.0)
    ap.add_argument("--lambda_sup", type=float, default=2.0)
    ap.add_argument("--lambda_neigh", type=float, default=0.3)
    ap.add_argument("--lambda_recon", type=float, default=1.0)
    ap.add_argument("--out", default="results/monotonicity.json")
    args = ap.parse_args()

    root = Path(args.data)
    sample_dirs = sorted([d for d in root.iterdir()
                          if d.is_dir() and (d / "filtered_feature_bc_matrix.h5").exists()])
    device = args.device
    patch_size = 224 if (args.fm and args.fm.lower() != "none") else 64

    loaded = {}
    for sd in sample_dirs:
        loaded[sd.name] = load_sample(sd, args.n_genes, patch_size, device)
        print(f"  loaded {sd.name}: {loaded[sd.name][0].shape[0]} spots")

    # common gene order: UNION of all samples' panels (intersection collapses to
    # ~980 genes and drops HPV-specific genes). Align via S.align_genes.
    common = []
    seen = set()
    for sd in sample_dirs:
        for g in loaded[sd.name][3]:
            if g not in seen:
                seen.add(g)
                common.append(g)
    print(f"  unified gene panel: {len(common)} genes (union)")

    def _reindex(name):
        exp, img, coords, genes = loaded[name]
        exp = S.align_genes(exp, genes, common)
        return exp, img, coords.astype(np.float64)

    # build the joint training set with per-sample coordinate offsets
    exp_parts, img_parts, coord_parts, slices = [], [], [], []
    off = 0
    for si, sd in enumerate(sample_dirs):
        e, i, c = _reindex(sd.name)
        c = c + si * 10000.0
        exp_parts.append(e); img_parts.append(i); coord_parts.append(c)
        slices.append((sd.name, off, off + e.shape[0]))
        off += e.shape[0]
    exp = torch.cat(exp_parts, 0)
    img = torch.cat(img_parts, 0)
    coords = np.vstack(coord_parts)

    # model + HPV proxy label
    n_genes = exp.shape[1]
    img_encoder = None
    if args.fm and args.fm.lower() != "none":
        from src.foundation_encoder import FoundationMorphologyEncoder
        img_encoder = FoundationMorphologyEncoder(name=args.fm.lower(), out_dim=128,
                                                  freeze=True).to(device)
    model = M.build_model("st_he_fusion", n_genes, img_encoder=img_encoder).to(device)

    hpv_idx = [i for i, g in enumerate(common) if g in HPV_SPECIFIC_GENES]
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

    # per-sample batch sampler
    class _Sampler(torch.utils.data.Sampler):
        def __init__(self, slices, bs, seed=0):
            self.slices, self.bs, self.rng = slices, bs, np.random.default_rng(seed)
        def __iter__(self):
            batches = []
            for _n, s, e in self.slices:
                idx = list(range(s, e)); self.rng.shuffle(idx)
                batches += [idx[k:k+self.bs] for k in range(0, len(idx), self.bs)]
            self.rng.shuffle(batches)
            return iter(batches)
        def __len__(self):
            return sum((e - s + self.bs - 1)//self.bs for _, s, e in self.slices)

    ds = TensorDataset(exp, img, torch.as_tensor(coords, dtype=torch.float32), hpv_y)
    dl = DataLoader(ds, batch_sampler=_Sampler(slices, args.bs))

    for ep in range(args.epochs):
        model.train()
        for b_exp, b_img, b_coords, b_y in dl:
            b_img = b_img.to(device)
            out = model(b_exp, b_img)
            l_rec = recon_loss(out["recon"], b_exp)
            neigh = build_neighbor_targets(b_coords.numpy(), out["score"].detach().squeeze(-1))
            l_neigh = score_loss(out["score"], neigh.to(device))
            l_sup = torch.zeros((), device=device)
            l_fused = torch.zeros((), device=device)
            if has_probe:
                l_sup = score_sup(out["score"], b_y.to(device))
                l_fused = fused_sup_loss(fused_sup_head(out["fused"]),
                                         b_y.to(device).unsqueeze(-1).float())
            l_var = torch.clamp(0.2 - out["score"].std(), min=0.0)
            loss = (args.lambda_recon * l_rec
                    + args.lambda_neigh * l_neigh
                    + args.lambda_sup * l_sup + args.lambda_sup * l_fused + 0.1 * l_var)
            opt.zero_grad(); loss.backward(); opt.step()
        print(f"  epoch {ep+1}/{args.epochs} recon={float(l_rec):.4f} sup={float(l_sup):.4f}")

    # ---- per-sample risk score + monotonicity ----
    model.eval()
    with torch.no_grad():
        scores, _ = infer_scores(model, exp, img, args.bs, device)
    scores_np = scores.cpu().numpy()

    per_sample = {}
    for name, s, e in slices:
        per_sample[name] = float(np.mean(scores_np[s:e]))

    print("\n=== Per-sample mean risk score (progression order) ===")
    ordered = [per_sample.get(n, float("nan")) for n in PROGRESSION]
    for n, v in zip(PROGRESSION, ordered):
        print(f"  {n:12s} -> {v:+.3f}")

    # monotonicity check: strictly increasing along PROGRESSION?
    diffs = [ordered[i+1] - ordered[i] for i in range(len(ordered)-1)]
    n_up = sum(d > 0 for d in diffs)
    n_total = len(diffs)
    monotonic = n_up == n_total
    print(f"\n  monotonic increases: {n_up}/{n_total} "
          f"({'PASS' if monotonic else 'FAIL'})")

    # Kendall tau trend (rank correlation with severity 0..3)
    from scipy.stats import kendalltau
    tau, p = kendalltau(range(len(ordered)), ordered)
    print(f"  Kendall tau (score vs severity) = {tau:.3f} (p={p:.3f})")

    out = {"per_sample_score": per_sample, "ordered": ordered,
           "n_up": n_up, "n_total": n_total, "monotonic": bool(monotonic),
           "kendall_tau": float(tau), "kendall_p": float(p)}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2, default=str, allow_nan=False))
    print(f"\nSaved -> {args.out}")


if __name__ == "__main__":
    main()
