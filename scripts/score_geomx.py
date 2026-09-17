"""
===========================================================================
 score_geomx.py — Expression-branch scoring of GeoMx DSP GSE316098 ROIs
===========================================================================
Why this exists
---------------
The GeoMx ROI scores used by build_external_corrected.py were originally
produced by an ad hoc notebook on the remote server (only its JSON output was
synced). This script is the auditable reconstruction of that exact scorer:

  1. load GSE316098 raw linear counts (18,677 genes x 186 ROIs);
  2. align genes to the checkpoint panel, zero-fill missing genes;
  3. np.log1p on raw counts (identical to scripts/infer_st.py Visium path —
     NO library-size / Q3 normalization);
  4. frozen GeneEncoder + risk head (expression-only branch).

Fidelity was proven bit-for-bit: with checkpoint_MAIN_KEGG_seed42.pt this
script reproduces all 186 scores in results/external_gse316098_validation.json
with RMSE=0.0000 (Pearson=1.00000).

Usage:
  python scripts/score_geomx.py \
      --checkpoint results/checkpoint_FULL_DEPLOY_FAST_seed42.pt \
      --out results/external_gse316098_validation_FINAL.json
===========================================================================
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from src.models import GeneEncoder

EXPR = REPO / "data" / "st_visium" / "geo_cervical_geomx_GSE316098" / \
    "GSE316098_raw.counts.linear.formatted.csv.gz"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    ckpt = torch.load(args.checkpoint, map_location="cpu")
    genes = list(ckpt["genes"])
    sd = ckpt["model_state_dict"]

    enc = GeneEncoder(len(genes), hidden=256, out=128)
    enc.load_state_dict({k[len("gene_enc."):]: v for k, v in sd.items()
                         if k.startswith("gene_enc.")})
    head = nn.Sequential(nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, 1))
    head.load_state_dict({k[len("head."):]: v for k, v in sd.items()
                          if k.startswith("head.")})
    enc.eval(); head.eval()

    expr = pd.read_csv(EXPR).rename(columns={"Unnamed: 0": "gene"}).set_index("gene")
    # counts CSV uses "1b-1." while GEO SOFT uses "1b.1." — canonicalize
    expr.columns = [c.replace("1b-1.", "1b.1.") for c in expr.columns]
    rois = list(expr.columns)
    X = expr[rois].T.values.astype(np.float32)
    g2i = {g: i for i, g in enumerate(expr.index)}

    A = np.zeros((X.shape[0], len(genes)), dtype=np.float32)
    matched = 0
    for j, g in enumerate(genes):
        if g in g2i:
            A[:, j] = X[:, g2i[g]]
            matched += 1
    A = np.log1p(A)  # raw counts -> log1p, same as Visium inference path

    with torch.no_grad():
        scores = head(enc(torch.from_numpy(A))).numpy().ravel()

    per_roi = [{"roi": r,
                "score": float(s),
                "pattern": r.split(".")[0],
                "compartment": r.rsplit(".", 1)[-1]}
               for r, s in zip(rois, scores)]

    silva_A = [x["score"] for x in per_roi if x["pattern"] == "1A"]
    out = {
        "dataset": "GSE316098",
        "type": "cervical adenocarcinoma GeoMx",
        "checkpoint": str(args.checkpoint),
        "mode": "expr_only",
        "normalization": "log1p(raw counts aligned to checkpoint panel, zero-fill missing)",
        "n_rois": len(per_roi),
        "panel_n_genes": len(genes),
        "gene_match": matched,
        "silva_A_mean_oldlabel": float(np.mean(silva_A)),
        "per_roi": per_roi,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2))
    print(f"n_rois={len(per_roi)} panel={len(genes)} matched={matched} "
          f"mean_score={scores.mean():.4f} -> {args.out}")


if __name__ == "__main__":
    main()
