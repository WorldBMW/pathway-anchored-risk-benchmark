"""
===========================================================================
 hnscc_moran_permutation_control.py
===========================================================================
Purpose
-------
Replace the invalid "label-shuffled" HNSCC control (run XCOHORT_HNSCC_SMOKE,
which was a smoke test producing a constant score field, std ~ 1e-9) with a
VALID spatial negative control:

  For every cross-organ HNSCC sample, per-spot risk scores and Visium
  coordinates are already stored in infer_*_full.json. We fix the k=6 k-NN
  graph (identical implementation to src.models.moran_i) and permute the
  scores across spots B=1000 times (equivalent to permuting coordinates).
  Expected Moran's I under complete spatial randomness ~ 0.

This control validates that the observed score field is genuinely spatially
autocorrelated, but it does NOT establish pathway specificity (that requires
discriminative evidence, e.g. HPV+ vs HPV- / malignant vs stromal contrast).

Inputs (must contain per-sample scores + coords):
  results/infer_XCOHORT_HNSCC_FULL_full.json         (GSE268014, n=8)
  results/infer_XCOHORT_HNSCC_GSE281978_full.json    (GSE281978, n=6)

Output:
  results/hnscc_moran_permutation_control.json

Usage:
  python scripts/hnscc_moran_permutation_control.py [--n_perm 1000] [--seed 20260912]
===========================================================================
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

INPUTS = {
    "GSE268014_HNSCC": REPO / "results" / "infer_XCOHORT_HNSCC_FULL_full.json",
    "GSE281978_HNSCC": REPO / "results" / "infer_XCOHORT_HNSCC_GSE281978_full.json",
}
OUT = REPO / "results" / "hnscc_moran_permutation_control.json"


def moran_from_neighbors(z: np.ndarray, nbr: np.ndarray, n: int, k: int = 6) -> float:
    """Same statistic as src.models.moran_i, with precomputed k-NN index."""
    num = float((z * z[nbr].sum(axis=1)).sum())
    return float((n / (n * k)) * (num / float((z * z).sum())))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n_perm", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=20260912)
    ap.add_argument("--g268014_full", type=Path,
                    default=INPUTS["GSE268014_HNSCC"],
                    help="inference full.json for GSE268014 (e.g. FINAL rerun)")
    ap.add_argument("--g281978_full", type=Path,
                    default=INPUTS["GSE281978_HNSCC"],
                    help="inference full.json for GSE281978 (e.g. FINAL rerun)")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    inputs = {"GSE268014_HNSCC": args.g268014_full,
              "GSE281978_HNSCC": args.g281978_full}

    rng = np.random.default_rng(args.seed)
    out: dict = {}

    for tag, fn in inputs.items():
        d = json.load(open(fn, encoding="utf-8"))
        rows = []
        for s in d["samples"]:
            y = np.asarray(s["scores"], dtype=float)
            coords = np.asarray(s["coords"], dtype=float)
            n = len(y)
            tree = cKDTree(coords)
            _, idx = tree.query(coords, k=7)  # row[0]=self, identical to moran_i
            nbr = idx[:, 1:]
            z = y - y.mean()
            obs = moran_from_neighbors(z, nbr, n)

            nulls = np.empty(args.n_perm)
            for b in range(args.n_perm):
                nulls[b] = moran_from_neighbors(z[rng.permutation(n)], nbr, n)

            p_ge = (1 + int((nulls >= obs).sum())) / (args.n_perm + 1)
            rows.append({
                "name": s["name"],
                "n_spots": n,
                "moran_obs_json": s["moran_i"],
                "moran_obs_recomputed": obs,
                "perm_null_mean": float(nulls.mean()),
                "perm_null_sd": float(nulls.std()),
                "perm_null_q025": float(np.quantile(nulls, 0.025)),
                "perm_null_q975": float(np.quantile(nulls, 0.975)),
                "perm_null_min": float(nulls.min()),
                "perm_null_max": float(nulls.max()),
                "z_vs_null": float((obs - nulls.mean()) / nulls.std()),
                "perm_p_ge": float(p_ge),
            })
            print(f"{tag} {s['name']:>20s} n={n:5d} obs_json={s['moran_i']:.4f} "
                  f"obs_calc={obs:.4f} null={nulls.mean():.4f}+/-{nulls.std():.4f} "
                  f"range=[{nulls.min():.4f},{nulls.max():.4f}] "
                  f"z={(obs - nulls.mean()) / nulls.std():6.1f} p={p_ge:.4f}")

        obs_mean = float(np.mean([r["moran_obs_recomputed"] for r in rows]))
        null_mean = float(np.mean([r["perm_null_mean"] for r in rows]))
        out[tag] = {
            "n_samples": len(rows),
            "per_sample": rows,
            "pooled_observed_mean": obs_mean,
            "pooled_perm_null_mean": null_mean,
            "delta": obs_mean - null_mean,
            "n_perm": args.n_perm,
            "seed": args.seed,
            "permutation": ("scores permuted across spots with fixed k=6 kNN graph; "
                            "equivalent to coordinate permutation (CSR null)"),
        }
        print(f">> {tag}: observed mean I={obs_mean:.4f} | perm-null mean I={null_mean:.4f} "
              f"| delta={obs_mean - null_mean:.4f}\n")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
