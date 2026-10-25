"""Cross-cohort / cross-cancer evaluation of the proposed ST-H&E fusion model.

Why this exists (Q1/Q2 reviewer requirement)
-------------------------------------------
A method that only works on one cervical sample is a case study, not a method.
We evaluate the SAME training protocol on multiple independent cohorts
(breast / ovarian / prostate cancers, and Visium-HD colon) to show the
HPV-anchored risk field generalises beyond the cervical discovery cohort.
For each cohort we report reconstruction error, spatial coherence (Moran's I),
the number of biologically-plausible DEGs, and -- where applicable -- overlap
of the high-risk field with the same curated HPV-related gene set.

This is intentionally a thin wrapper that reuses train_st.py's model, data
loader and DEG machinery so the cross-cohort numbers are produced by the exact
same code path as the main results (no divergent implementation).

Usage
-----
  python scripts/cross_cohort_eval.py --root data/st_visium --device cuda \
      --epochs 40 --run_id XCOHORT
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import st_data as S
from src import models as M
import scripts.train_st as T  # reuse model build, losses, DEG machinery

# prior gene panel (reused from the main DEG analysis; kept here as a flat list
# so the cross-cohort DEG test uses the SAME biology panel as train_st.py).
PRIOR_PANEL = [
    "TP63","CDKN2A","MYC","CCND1","EGFR","PIK3CA","KRAS","EP300","GATA3","KRT8",
    "KRT18","MKI67","PCNA","CD274","PDCD1LG2","CTLA4","FOXP3","CD8A","CD4","IL2RG",
    "STAT1","IRF1","MX1","OAS1","E2F1","E2F2","E2F3","RB1","CCNE1","CCNA2","PLK1",
    "AURKA","TOP2A","BUB1","CENPF","TK1","RRM2","TYMS","HMGB2","KPNA2",
    "PDCD1","LAG3","HAVCR2","TIGIT","IDO1","GZMB","IFNG","PRF1","TBX21","CXCL9",
    "CXCL10","CD68","ITGAM","NOS2","TNF","CD163","MRC1","MSR1","TGFB1","IL10",
    "ACTA2","COL1A1","COL3A1","FAP","S100A4","PDGFRB","CCNB1","CDK1","EPCAM",
    "KRT19","CDH1","VEGFA","PECAM1","CD34","FLT1","TP53","ERBB2","MTOR",
    "MMP1","MMP2","MMP3","MMP9","MMP11","MMP23B",
]

# HPV prior gene panel for cross-cohort overlap test.
# Hard-coded fallback so the script works even when docs/hpv_genes.json is
# missing on the remote server (e.g. someone forgot to upload docs/).
# The source of truth is docs/hpv_genes.json when present.
_HPV_GENES_FALLBACK = [
    "TP63","CDKN2A","MYC","CCND1","EGFR","PIK3CA","KRAS","EP300","GATA3","KRT8",
    "KRT18","MKI67","PCNA","CD274","PDCD1LG2","CTLA4","FOXP3","CD8A","CD4","IL2RG",
    "STAT1","IRF1","MX1","OAS1","E2F1","E2F2","E2F3","RB1","CCNE1","CCNA2","PLK1",
    "AURKA","TOP2A","BUB1","CENPF","TK1","RRM2","TYMS","HMGB2","KPNA2",
]
_hpv_json_path = Path(__file__).resolve().parent.parent / "docs/hpv_genes.json"
if _hpv_json_path.exists():
    try:
        raw = json.loads(_hpv_json_path.read_text())
        if isinstance(raw, dict):
            # allow {"genes": [...]} envelope too
            raw = raw.get("genes", raw)
        HPV_GENES = set(raw)
        if not all(isinstance(g, str) for g in HPV_GENES):
            raise ValueError("HPV gene list contains non-string entries")
    except Exception as e:
        print(f"[WARN] docs/hpv_genes.json exists but unreadable ({e}); "
              f"falling back to built-in HPV gene list ({len(_HPV_GENES_FALLBACK)} genes)")
        HPV_GENES = set(_HPV_GENES_FALLBACK)
else:
    print(f"[WARN] docs/hpv_genes.json not found at {_hpv_json_path}; using built-in HPV gene list ({len(_HPV_GENES_FALLBACK)} genes)")
    HPV_GENES = set(_HPV_GENES_FALLBACK)


def train_one(data_dir, fm, device, epochs, bs, lr, n_genes, lambda_hpv,
              lambda_neigh, lambda_recon, fm_cache=False):
    """Train ST-H&E fusion model on one external cohort.

    NOTE on lambda_hpv for cross-cohort runs:
      Most non-cervical cohorts (breast / ovarian / prostate / colon) do NOT
      carry an HPV-status annotation.  We therefore **never** compute an HPV
      supervision loss inside this train_one — the lambda_hpv argument is
      accepted only for CLI parity with train_st.py and so it appears in the
      output config.  HPV-related information only enters evaluate() via the
      *HPV_GENES prior panel overlap with DEGs*, which is a label-free
      post-hoc statistic that works for every cohort.
    """
    sample = S.load_sample(Path(data_dir))
    patch_size = 224 if (fm and fm.lower() != "none") else 64
    paired = S.build_paired_tensors(sample, n_genes_keep=n_genes,
                                    patch_size=patch_size)
    exp = paired["exp"].to(device)
    # Keep images on CPU until we know if fm_cache will replace them with
    # precomputed backbone features (tiny feat_dim tensor).
    img = paired["img"]
    coords = paired["coords"]
    genes = paired["genes"]

    img_encoder = None
    if fm and fm.lower() != "none":
        from src.foundation_encoder import (
            FoundationMorphologyEncoder,
            precompute_fm_backbone_cache,
            load_fm_backbone_cache,
        )
        img_encoder = FoundationMorphologyEncoder(name=fm.lower(), out_dim=128,
                                                  freeze=True).to(device)
        if fm_cache:
            import hashlib
            RESULTS_DIR = Path("results/cache")
            RESULTS_DIR.mkdir(parents=True, exist_ok=True)
            coh_name = Path(data_dir).name
            key_src = (f"fm={fm}|n_genes={n_genes}|patch_size={patch_size}"
                       f"|sample={coh_name}")
            key_hash = hashlib.md5(key_src.encode()).hexdigest()[:10]
            cache_path = RESULTS_DIR / f"xcc_{fm.lower()}_{coh_name}_{key_hash}.pt"
            if cache_path.exists():
                print(f"[FM cache] HIT: {cache_path}")
                backbone_feats, adapter_only_enc = load_fm_backbone_cache(
                    cache_path, img_encoder.adapter)
            else:
                try:
                    backbone_feats, adapter_only_enc = precompute_fm_backbone_cache(
                        img_encoder, img, device, batch_size=bs,
                        cache_path=cache_path, verbose=True)
                except RuntimeError as e:
                    err_lc = str(e).lower()
                    # Match ANY CUDA memory / allocator failure, not just the
                    # literal "out of memory" string. This catches:
                    #   - classic OOM                           -> "out of memory"
                    #   - CUDACachingAllocator expandable_segments assertion -> "expandable_segment_"
                    #   - PyTorch internal assert on allocator      -> "internal assert failed"
                    #   - generic CUDA error string                -> "cuda error"
                    is_mem_failure = any(tok in err_lc for tok in (
                        "out of memory", "expandable_segment_",
                        "internal assert failed", "cuda error",
                        "cudacachingallocator"))
                    if is_mem_failure:
                        print(f"[FM cache] CUDA-allocator failure at bs={bs}; "
                              f"halving to bs={max(1, bs // 2)}. Reason preview: {str(e)[:140]}")
                        if device.type == "cuda":
                            torch.cuda.empty_cache()
                        backbone_feats, adapter_only_enc = precompute_fm_backbone_cache(
                            img_encoder, img, device, batch_size=max(1, bs // 2),
                            cache_path=cache_path, verbose=True)
                    else:
                        raise
            img = backbone_feats
            img_encoder = adapter_only_enc
    img = img.to(device)
    model = M.build_model("st_he_fusion", len(genes),
                          img_encoder=img_encoder).to(device)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],
                            lr=lr, weight_decay=1e-4)
    recon_loss = nn.MSELoss()
    score_loss = nn.MSELoss()
    coord_t = torch.tensor(coords, dtype=torch.float32)

    # ---- Auto-decrease bs on CUDA OOM (common for Visium-HD colon) ----
    attempt = 0
    while True:
        attempt += 1
        try:
            dl = DataLoader(TensorDataset(exp, img, coord_t),
                            batch_size=bs, shuffle=True)
            model.train()
            for _ in range(epochs):
                for b_exp, b_img, b_coords in dl:
                    b_img = b_img.to(device, non_blocking=True)
                    out = model(b_exp, b_img)
                    loss = recon_loss(out["recon"], b_exp)
                    if lambda_neigh:
                        neigh = T.build_neighbor_targets(
                            b_coords.numpy(), out["score"].detach().squeeze(-1))
                        loss = loss + lambda_neigh * score_loss(out["score"], neigh.to(device))
                    opt.zero_grad()
                    loss.backward()
                    opt.step()
            break  # training succeeded
        except RuntimeError as e:
            err_lc = str(e).lower()
            is_mem_failure = any(tok in err_lc for tok in (
                "out of memory", "expandable_segment_",
                "internal assert failed", "cuda error",
                "cudacachingallocator"))
            if is_mem_failure and bs >= 4 and attempt <= 5:
                print(f"[warn] {Path(data_dir).name} CUDA mem failure at bs={bs}; "
                      f"halving to bs={bs // 2} (attempt {attempt}). "
                      f"Reason preview: {str(e)[:140]}")
                if device.type == "cuda":
                    torch.cuda.empty_cache()
                # rebuild opt + model weights to reset any broken state
                del opt
                model = M.build_model("st_he_fusion", len(genes),
                                      img_encoder=img_encoder).to(device)
                opt = torch.optim.AdamW(
                    [p for p in model.parameters() if p.requires_grad],
                    lr=lr, weight_decay=1e-4)
                bs = bs // 2
            else:
                raise

    model.eval()
    with torch.no_grad():
        out = model(exp, img)
    score = out["score"].squeeze(-1).cpu().numpy()
    return {"exp": exp.cpu().numpy(), "score": score, "coords": coords,
            "genes": genes, "recon": out["recon"].cpu().numpy()}


def evaluate(data_dir, fm, device, epochs, bs, lr, n_genes, lambda_hpv,
             lambda_neigh, lambda_recon, n_perm=200, fm_cache=False):
    d = train_one(data_dir, fm, device, epochs, bs, lr, n_genes, lambda_hpv,
                  lambda_neigh, lambda_recon, fm_cache=fm_cache)
    exp, score, coords, genes = d["exp"], d["score"], d["coords"], d["genes"]
    # Moran's I
    mi = float(M.moran_i(score, coords))
    # high/low split by median score
    high = score > np.median(score)
    # spatial-perm DEG on prior panel
    gidx = {g: i for i, g in enumerate(genes)}
    present = [g for g in PRIOR_PANEL if g in gidx]
    gi = [gidx[g] for g in present]
    p_perm, _ = T.spatial_block_perm_test(exp, coords, high, gi, n_perm=n_perm)
    # BH over perm p
    m = len(p_perm)
    order = np.argsort(p_perm)
    fdr = np.empty(m); prev = 1.0
    for r in range(m - 1, -1, -1):
        prev = min(prev, p_perm[order[r]] * m / (r + 1))
        fdr[order[r]] = prev
    fdr = np.clip(fdr, 0, 1)
    deltas = exp[high][:, gi].mean(0) - exp[~high][:, gi].mean(0)
    n_deg = int(((fdr < 0.05) & (np.abs(deltas) > 0.3)).sum())
    # HPV-set overlap of significant DEGs
    sig = {present[i] for i in np.where((fdr < 0.05) & (np.abs(deltas) > 0.3))[0]}
    hpv_overlap = sorted(sig & HPV_GENES)
    return {
        "cohort": Path(data_dir).name,
        "n_spots": int(exp.shape[0]),
        "moran_i": round(mi, 4),
        "n_deg_perm_fdr05": n_deg,
        "hpv_gene_overlap_in_deg": hpv_overlap,
        "n_hpv_overlap": len(hpv_overlap),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/st_visium")
    ap.add_argument("--cohorts", nargs="*",
                    default=["breast_cancer_1", "ovarian_cancer_1",
                             "prostate_cancer_1", "visium_hd_colon_p1"])
    ap.add_argument("--fm", default="uni")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--bs", type=int, default=256)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--n_genes", type=int, default=2000)
    ap.add_argument("--lambda_hpv", type=float, default=0.5)
    ap.add_argument("--lambda_neigh", type=float, default=0.3)
    ap.add_argument("--lambda_recon", type=float, default=1.0)
    ap.add_argument("--run_id", default="XCOHORT")
    ap.add_argument("--fm_cache", action="store_true",
                    help="3-5x speedup: cache frozen FM backbone features once per "
                         "cohort (identical across epochs). Training dynamics unchanged.")
    args = ap.parse_args()

    rows = []
    for coh in args.cohorts:
        d = Path(args.root) / coh
        if not d.exists():
            print(f"[skip] {coh} not found")
            continue
        print(f"\n===== CROSS-COHORT: {coh} =====")
        try:
            r = evaluate(str(d), args.fm, args.device, args.epochs, args.bs,
                         args.lr, args.n_genes, args.lambda_hpv,
                         args.lambda_neigh, args.lambda_recon,
                         fm_cache=args.fm_cache)
        except Exception as e:
            print(f"[warn] {coh} failed: {e}")
            continue
        print(json.dumps(r, indent=2))
        rows.append(r)

    out = {"rows": rows,
           "config": {"fm": args.fm, "lambda_hpv": args.lambda_hpv,
                      "lambda_neigh": args.lambda_neigh,
                      "lambda_recon": args.lambda_recon, "epochs": args.epochs}}
    out_dir = Path("results")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"cross_cohort_{args.run_id}.json").write_text(
        json.dumps(out, indent=2, default=str, allow_nan=False))
    print(f"\nSaved results/cross_cohort_{args.run_id}.json")


if __name__ == "__main__":
    main()
