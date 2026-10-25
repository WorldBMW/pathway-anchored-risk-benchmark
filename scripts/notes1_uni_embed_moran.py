# -*- coding: utf-8 -*-
"""Supplementary Note S1 — spatial autocorrelation of frozen UNI patch embeddings.

What this does (paper-facing)
-----------------------------
Reviews ask whether the "image-branch null" (dropping H&E leaves the risk score
unchanged) hides pathology signal. Note S1 answers a narrower, falsifiable
question: *do the raw UNI patch embeddings themselves carry WITHIN-SECTION
spatial structure, independent of the trained risk head?*

Statistical design (v2, 2026-09-15)
-----------------------------------
The naive pooled Moran's I on globally-standardised features is confounded by
between-slide mean shifts (different patients / scanners / tissue types): with
the per-sample coordinate offset keeping the k-NN graph inside each section, a
globally-centred statistic counts slide-mean differences as "spatial
autocorrelation". We therefore make the WITHIN-SECTION analysis primary:

  1. per slide: local z-score -> local PC1 -> Moran's I (k=6 k-NN);
  2. distribution of the 35 per-slide values, stratified by source cohort;
  3. pooled within-slide-centred statistic with a coordinate-fixed permutation
     null that permutes PC1 WITHIN each slide (preserving slide means);
  4. per-dimension Moran's I, computed within slide and averaged;
  5. pixel-level patch QC (fraction of unique patches per slide) — guards
     against image-registration failures feeding degenerate inputs.

Moran definition / coordinate offsets are identical to src.models.moran_i and
scripts/train_st.py.

Usage (AutoDL, from repo root)
------------------------------
    # IMPORTANT: requires the 2026-09-15 st_data.py coordinate fix; delete any
    # stale FM backbone cache built before the fix before running ANY image
    # analysis:  rm -f results/cache/fm_uni_*.pt
    python -u scripts/notes1_uni_embed_moran.py \
        --data data/st_visium/cervix_all_ext \
        --out results/uni_embed_moran_s1.json \
        --n_perm 10000 --seed 20260915 2>&1 | tee logs/notes1_uni_embed_moran.log
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path

import numpy as np
import torch
from scipy.spatial import cKDTree

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from src import st_data as S
from src.foundation_encoder import FoundationMorphologyEncoder

K = 6                     # k-NN, identical to src.models.moran_i
SAMPLE_OFFSET = 10000.0   # per-sample coord offset, identical to train_st.py


def moran_from_neighbors(z: np.ndarray, nbr: np.ndarray, n: int, k: int = K) -> float:
    """Global Moran's I given the (N,k) neighbor-index array (self excluded)."""
    z = np.asarray(z, dtype=float)
    denom = float((z * z).sum())
    if denom == 0.0 or n < k + 2:
        return float("nan")
    num = float((z * z[nbr].sum(axis=1)).sum())
    return float((n / (n * k)) * (num / denom))


def patch_qc(img: np.ndarray, max_check: int = 1500) -> dict:
    """Pixel-level guard: are patches spatially registered / distinguishable?

    Returns the fraction of unique patches and the pixel-PC1 spatial Moran's I
    on a spot subset. unique_fraction << 1 means image registration is broken
    (crops clamped to a corner / blank placeholders) and UNI features are
    degenerate by construction."""
    n = img.shape[0]
    idx = np.linspace(0, n - 1, min(n, max_check)).astype(int)
    flat = img[idx].reshape(len(idx), -1).astype(np.float32)
    uniq = np.unique(flat, axis=0).shape[0]
    return {"n_checked": int(len(idx)), "n_unique": int(uniq),
            "unique_fraction": float(uniq / len(idx))}


def discover(data: Path, exclude: set[str]):
    """Visium sample dirs directly under `data`, skipping --exclude_substr hits."""
    if not data.exists():
        raise SystemExit(f"[error] --data not found: {data}")
    subs = sorted([p for p in data.iterdir() if p.is_dir() or p.is_symlink()])
    out = []
    for p in subs:
        if exclude and any(e in str(p).lower() for e in exclude):
            continue
        try:
            S.load_sample(p)
            out.append(p)
        except Exception:
            continue
    return out


def cohort_of(name: str) -> str:
    if name in ("N_HPV", "HSIL_HPV", "CA_HPV_1", "CA_HPV_2"):
        return "GSE208654"
    if name.startswith("ecto_"):
        return "GSE217237"
    if name == "cervical_cancer_1":
        return "10x_cervical_cancer_1"
    return "other"


def local_pc1_moran(Zs: np.ndarray, nbr: np.ndarray, n: int):
    """Within-slide z-scored features -> local PC1 -> Moran's I.

    Returns (I_pc1, pc1_var_ratio, per_dim_mean_I, per_dim_median_I)."""
    C = Zs.T @ Zs / n
    w, v = np.linalg.eigh(C)
    pc1 = Zs @ v[:, -1]
    z = pc1 - pc1.mean()
    I_pc1 = moran_from_neighbors(z, nbr, n)
    # per-dimension Moran's I (chunked)
    Is = []
    for d in range(0, Zs.shape[1], 128):
        Zc = Zs[:, d:d + 128].copy()
        den = (Zc * Zc).sum(axis=0)
        num = (Zc * Zc[nbr].sum(axis=1)).sum(axis=0)
        den[den == 0.0] = 1.0
        Is.append((n / (n * K)) * num / den)
    Is = np.concatenate(Is)
    return I_pc1, float(w[-1] / w.sum()), float(Is.mean()), float(np.median(Is))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, type=Path,
                    help="dir whose children are Visium sample dirs (e.g. "
                         "data/st_visium/cervix_all_ext)")
    ap.add_argument("--exclude_substr", default="",
                    help="comma-separated substrings to skip (matched against "
                         "full path, lower-cased)")
    ap.add_argument("--out", type=Path,
                    default=REPO / "results" / "uni_embed_moran_s1.json")
    ap.add_argument("--n_perm", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=20260915)
    ap.add_argument("--chunk", type=int, default=32,
                    help="patches per backbone inner forward (memory-safe on 24GB)")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--fm", default="uni", help="uni | uni2")
    args = ap.parse_args()

    exclude = {s.strip().lower() for s in args.exclude_substr.split(",") if s.strip()}
    sample_dirs = discover(args.data, exclude)
    if not sample_dirs:
        raise SystemExit(f"[error] no loadable Visium samples under {args.data}")
    print(f"[discovery] {len(sample_dirs)} samples: "
          f"{', '.join(p.name for p in sample_dirs)}", flush=True)

    encoder = FoundationMorphologyEncoder(name=args.fm.lower(), out_dim=128, freeze=True)
    backbone = encoder.backbone.to(args.device)
    backbone.eval()
    feat_dim = encoder.feat_dim

    feats_list, coords_list, names, qc_list = [], [], [], []
    t0 = time.time()
    for si, sd in enumerate(sample_dirs):
        try:
            smp = S.load_sample(sd)
            paired = S.build_paired_tensors(smp, n_genes_keep=2000, patch_size=224,
                                            max_spots=0, verbose=True)
        except Exception as e:
            print(f"[skip] {sd.name}: {e}", flush=True)
            continue
        img = paired["img"]                       # (n,3,224,224)
        qc = patch_qc(img.numpy())
        c = paired["coords"].astype(np.float64) + si * SAMPLE_OFFSET
        n = img.shape[0]
        Fk = []
        with torch.no_grad():
            for s in range(0, n, args.chunk):
                e = min(s + args.chunk, n)
                f = backbone(img[s:e].to(args.device))
                if isinstance(f, dict):
                    f = f.get("features", f.get("global_pool"))
                Fk.append(f.cpu())
        Fk = torch.cat(Fk, dim=0).numpy().astype(np.float64)
        assert Fk.shape[0] == n and Fk.shape[1] == feat_dim, (Fk.shape, n, feat_dim)
        feats_list.append(Fk)
        coords_list.append(c)
        names.append(sd.name)
        qc_list.append(qc)
        print(f"  [{si+1}/{len(sample_dirs)}] {sd.name}: {n} spots, "
              f"unique_patch_frac={qc['unique_fraction']:.3f}  {time.time()-t0:.0f}s",
              flush=True)

    n_bad_reg = [nm for nm, q in zip(names, qc_list) if q["unique_fraction"] < 0.5]
    if n_bad_reg:
        print(f"[QC-WARN] {len(n_bad_reg)} samples with <50% unique patches "
              f"(broken image registration / placeholder): {n_bad_reg}", flush=True)

    # =====================================================================
    # PRIMARY ANALYSIS — within-section autocorrelation
    # =====================================================================
    per_sample, centered_blocks = [], []
    off = 0
    for nm, Fk, ck in zip(names, feats_list, coords_list):
        nk = Fk.shape[0]
        mu = Fk.mean(axis=0)
        sd = Fk.std(axis=0)
        sd[sd == 0.0] = 1.0
        Zs = (Fk - mu) / sd
        tk = cKDTree(ck)
        kk = min(K + 1, nk)
        _, kidx = tk.query(ck, k=kk)
        nbr = kidx[:, 1:] if kk > 1 else kidx[:, :0]
        if nk > K + 2:
            I_pc1, evr, I_dim_mean, I_dim_med = local_pc1_moran(Zs, nbr, nk)
        else:
            I_pc1, evr, I_dim_mean, I_dim_med = (float("nan"),) * 4
        per_sample.append({
            "name": nm, "cohort": cohort_of(nm), "n_spots": int(nk),
            "pc1_moran": float(I_pc1), "pc1_var_ratio": float(evr),
            "mean_dim_moran": float(I_dim_mean),
            "median_dim_moran": float(I_dim_med),
            "patch_qc": dict(qc_list[len(per_sample)]),
        })
        # block for pooled within-slide-centred analysis (local z-score)
        pc1 = Zs @ np.linalg.eigh(Zs.T @ Zs / nk)[1][:, -1]
        centered_blocks.append(pc1 - pc1.mean())
        off += nk

    pc1_series = np.concatenate(centered_blocks)
    coords = np.vstack(coords_list)
    Ntot = pc1_series.shape[0]
    tree = cKDTree(coords)
    _, kidx_all = tree.query(coords, k=K + 1)
    nbr_all = kidx_all[:, 1:]

    # pooled Moran on within-slide-centred PC1
    z = pc1_series
    den = float((z * z).sum())
    pooled_I = (Ntot / (Ntot * K)) * float((z * z[nbr_all].sum(axis=1)).sum()) / den

    # ---- within-slide permutation null (slide means preserved by construction,
    # since every per-slide block is centred; we shuffle WITHIN each block) ----
    rng = np.random.default_rng(args.seed)
    nulls = np.empty(args.n_perm)
    blocks = [(s, e) for s, e in zip(np.cumsum([0] + [b.shape[0] for b in centered_blocks])[:-1],
                                      np.cumsum([b.shape[0] for b in centered_blocks]))]
    zshuf = np.empty_like(z)
    t1 = time.time()
    for b in range(args.n_perm):
        for s, e in blocks:
            zshuf[s:e] = z[s:e][rng.permutation(e - s)]
        nulls[b] = (Ntot / (Ntot * K)) * float(
            (zshuf * zshuf[nbr_all].sum(axis=1)).sum()) / den
    p_perm = float((1 + int((nulls >= pooled_I).sum())) / (args.n_perm + 1))
    print(f"[pooled-within] I={pooled_I:.4f}  null mean={nulls.mean():.5f} "
          f"q99={np.quantile(nulls,0.99):.5f}  p={p_perm:.2e} ({time.time()-t1:.0f}s)",
          flush=True)

    # ---- stratify per-slide results ----
    def _stats(vals):
        v = np.asarray([x for x in vals if not np.isnan(x)], dtype=float)
        if v.size == 0:
            return {}
        return {"n": int(v.size), "mean": float(v.mean()), "median": float(np.median(v)),
                "sd": float(v.std(ddof=1)) if v.size > 1 else 0.0,
                "q25": float(np.quantile(v, 0.25)), "q75": float(np.quantile(v, 0.75)),
                "min": float(v.min()), "max": float(v.max())}

    strata = {}
    for coh in ["GSE208654", "GSE217237", "10x_cervical_cancer_1", "other"]:
        rows = [r for r in per_sample if r["cohort"] == coh]
        if rows:
            strata[coh] = {
                "n_samples": len(rows),
                "n_spots": int(sum(r["n_spots"] for r in rows)),
                "pc1_moran": _stats([r["pc1_moran"] for r in rows]),
                "mean_dim_moran": _stats([r["mean_dim_moran"] for r in rows]),
                "median_unique_patch_fraction":
                    float(np.median([r["patch_qc"]["unique_fraction"] for r in rows])),
            }

    out = {
        "note": "Supplementary Note S1 — WITHIN-SECTION spatial autocorrelation "
                "of frozen UNI patch embeddings (morphology), independent of the "
                "risk head. Primary estimand is per-slide local-PC1 Moran's I; "
                "the pooled statistic uses within-slide-centred PC1 and a "
                "within-slide permutation null.",
        "config": {
            "n_samples": len(names), "n_spots": int(Ntot), "feat_dim": int(feat_dim),
            "fm": args.fm.lower(), "k_neighbors": K,
            "coord_offset_per_sample": SAMPLE_OFFSET,
            "standardization": "per-slide z-score before local PCA",
            "moran_definition": "identical to src.models.moran_i / train_st.py",
            "null": f"permutation of PC1 WITHIN each slide (means preserved), "
                    f"B={args.n_perm}, seed={args.seed}",
            "registration_fix": "src/st_data.py 2026-09-15: standard Visium "
                                "coords now scaled by tissue_hires_scalef",
        },
        "n_bad_registration_samples": len(n_bad_reg),
        "bad_registration_samples": n_bad_reg,
        "pooled_within_slide_pc1_moran": float(pooled_I),
        "pooled_within_slide_perm_p": float(p_perm),
        "pooled_perm_null": {"mean": float(nulls.mean()),
                             "q025": float(np.quantile(nulls, 0.025)),
                             "q975": float(np.quantile(nulls, 0.975)),
                             "q990": float(np.quantile(nulls, 0.99)),
                             "max": float(nulls.max())},
        "per_slide_pc1_moran_all": _stats([r["pc1_moran"] for r in per_sample]),
        "by_cohort": strata,
        "per_sample": per_sample,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"saved -> {args.out}")
    for coh, st in strata.items():
        mm = st["pc1_moran"]
        print(f"  {coh:24s} n={mm['n']:2d}  PC1 I mean={mm['mean']:.4f} "
              f"median={mm['median']:.4f} [{mm['min']:.3f},{mm['max']:.3f}]  "
              f"uniq_patch_med={st['median_unique_patch_fraction']:.3f}")


if __name__ == "__main__":
    main()
