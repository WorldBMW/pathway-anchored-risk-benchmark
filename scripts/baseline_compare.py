"""Baseline comparison: HE2ST/Hist2ST-style image->expression imputation.

Why this exists (Q1/Q2 reviewer requirement)
-------------------------------------------
Generic "ST + pathology FM" works (HE2ST, Hist2ST) learn a *direct* image->gene
expression mapping and report reconstruction error. To claim our HPV-anchored,
spatially-regularised fusion is better, we must compare against that family on
the SAME held-out spots. This script reproduces a fair representative of that
family: a frozen pathology foundation-model feature extractor + a lightweight
regressor (KNN / Ridge / SVR / RF / MLP) that predicts log1p expression from
H&E features, with NO HPV pathway term and NO spatial coherence term.

Extended (v2) for Q2 cross-sample generalisation requirement:
  --mode loso  -> Leave-One-Sample-Out across all samples under --data
                  (--data should be a parent dir with multiple sample subdirs).
                  Measures image->expression baseline's ability to GENERALISE
                  to an unseen slide (the proposed method must beat this).

Reported metrics
----------------
  - held-out spot reconstruction MSE (lower = better image->expression fit)
  - mean per-gene Pearson correlation (aggregate across variable genes)
  - HPV-overlap ratio: how many of the top predicted-high genes lie in the
    HPV-related set (proxy for whether baseline learns disease biology)
  - In LOSO mode: per-fold (per-held-out-sample) metrics + aggregate.

Usage
-----
  # Single-sample mode (original HE2ST-style 80/20 spot split)
  python scripts/baseline_compare.py --data data/st_visium/cervical_cancer_1 \
      --fm uni --device cuda --regressor ridge --run_id BASELINE_RIDGE

  # LOSO cross-sample mode (train on 4 samples, test on 1 held-out)
  python scripts/baseline_compare.py --data data/st_visium/cervix_all \
      --fm uni --device cuda --mode loso --regressor ridge \
      --run_id BASELINE_LOSO_RIDGE

  # Run ALL 5 baseline regressors in LOSO mode and aggregate
  python scripts/baseline_compare.py --data data/st_visium/cervix_all \
      --fm uni --device cuda --mode loso --regressor all \
      --run_id BASELINE_LOSO_ALL
"""
from __future__ import annotations
import argparse
import inspect
import json
import sys
import time
import warnings
import gc
import traceback
from pathlib import Path

# ---- Silence noisy sklearn convergence / multi-output wrapping warnings.
#      (LinearSVR / MLP on 1000+ genes x 100k+ spots can fail to converge in
#       default 5000 iters; those are tracked via tol/max_iter tuning below.
#       Suppressing globally keeps stdout focused on per-fold progress.)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
try:
    from sklearn.exceptions import ConvergenceWarning
    warnings.filterwarnings("ignore", category=ConvergenceWarning)
except Exception:
    pass

import numpy as np
import torch
from sklearn.neighbors import KNeighborsRegressor
from sklearn.linear_model import RidgeCV
from sklearn.svm import SVR
from sklearn.ensemble import RandomForestRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputRegressor
from scipy.stats import pearsonr

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import st_data as S

# HPV prior gene panel for overlap test with baseline risk split.
# Hard-coded fallback so the script works even when docs/hpv_genes.json is
# missing on the remote server (e.g. someone forgot to upload docs/).
_HPV_GENES_FALLBACK = [
    "TP63","CDKN2A","MYC","CCND1","EGFR","PIK3CA","KRAS","EP300","GATA3","KRT8",
    "KRT18","MKI67","PCNA","CD274","PDCD1LG2","CTLA4","FOXP3","CD8A","CD4","IL2RG",
    "STAT1","IRF1","MX1","OAS1","E2F1","E2F2","E2F3","RB1","CCNE1","CCNA2","PLK1",
    "AURKA","TOP2A","BUB1","CENPF","TK1","RRM2","TYMS","HMGB2","KPNA2",
]
_hpv_json_path = Path(__file__).resolve().parent.parent / "docs/hpv_genes.json"
if _hpv_json_path.exists():
    HPV_GENES = set(json.loads(_hpv_json_path.read_text()))
else:
    print(f"[WARN] docs/hpv_genes.json not found at {_hpv_json_path}; using built-in HPV gene list ({len(_HPV_GENES_FALLBACK)} genes)")
    HPV_GENES = set(_HPV_GENES_FALLBACK)


REGRESSOR_NAMES = ["knn", "ridge", "svr", "rf", "mlp"]


def make_regressor(name: str):
    """Build a single-output regressor; caller wraps MultiOutputRegressor."""
    if name == "knn":
        return KNeighborsRegressor(n_neighbors=5, weights="distance")
    if name == "ridge":
        return RidgeCV(alphas=np.logspace(-3, 2, 10))
    if name == "svr":
        # On LOSO 35-sample: train set = ~34 slides x (2k-8k spots) with ~2200 genes
        # wrapped in MultiOutputRegressor → ~2200 separate LinearSVR fits.
        # Default max_iter=5000 will trigger ConvergenceWarning on the harder
        # genes; we bump it and relax tol, then fall back to SGDRegressor if
        # installed sklearn disables LinearSVR(loss=). For most 2024+ sklearn
        # (>=1.5), LinearSVR default loss=squared_epsilon_insensitive + larger
        # max_iter converges cleanly.
        from sklearn.svm import LinearSVR
        from sklearn.linear_model import SGDRegressor
        try:
            return LinearSVR(
                C=0.5, epsilon=0.1, loss="squared_epsilon_insensitive",
                tol=1e-3, max_iter=50000, random_state=0, dual="auto",
            )
        except TypeError:
            # Older sklearn (loss kwarg not supported) → SGD with equivalent
            # squared-epsilon-insensitive (Huber-ish) objective; scales better
            # on wide matrices and does not warn on non-converge.
            return SGDRegressor(
                loss="epsilon_insensitive", epsilon=0.1, alpha=1e-4,
                tol=1e-3, max_iter=50000, random_state=0, learning_rate="optimal",
            )
    if name == "rf":
        # Downscale for LOSO 35-sample (300k+ spots × 1-2k genes):
        #  - fewer trees / shallower depth / column subsample / more leaf samples
        #    → cuts peak memory 2-4x vs previous n_estimators=200/max_depth=12/n_jobs=-1.
        #  - n_jobs=4 (not -1) avoids spawning 32 workers each copying Xtr/ytr.
        return RandomForestRegressor(n_estimators=100, max_depth=8,
                                     n_jobs=4, random_state=0,
                                     min_samples_leaf=10, max_features=0.33)
    if name == "mlp":
        # Slim MLP + larger batch → faster + lower memory on wide train mats.
        # early_stopping still active; max_iter trimmed from 200 → 150.
        return MLPRegressor(hidden_layer_sizes=(128, 64), activation="relu",
                            early_stopping=True, validation_fraction=0.1,
                            max_iter=150, random_state=0,
                            learning_rate_init=1e-3, batch_size=2048)
    raise ValueError(f"Unknown regressor: {name}")


def extract_fm_features(img_tensor, fm, device, batch=64, _encoder_cache: dict | None = None,
                        _fm_name: str | None = None, verbose: bool = True):
    """Run frozen foundation model on (N,3,224,224) patches -> (N, D) features.

    New (Aug-2026) observability + speed vs old version:
      * Caller may pass an ``_encoder_cache`` dict with key ``encoder`` already
        initialized; this avoids reloading UNI weights (several hundred MB) for
        every sample (35 samples = 35 redundant weight loads → 35x slowdown).
      * Batch inference now prints a progress line every 20 batches with
        images/sec throughput + ETA_remain.
    """
    from src.foundation_encoder import FoundationMorphologyEncoder
    if _encoder_cache is not None and "encoder" in _encoder_cache:
        enc = _encoder_cache["encoder"]
    else:
        if verbose:
            print(f"    [FM init] name={_fm_name or fm} out_dim=128 freeze=True "
                  f"device={device} ...", flush=True)
        enc = FoundationMorphologyEncoder(name=(_fm_name or fm).lower(), out_dim=128,
                                          freeze=True).to(device).eval()
        if _encoder_cache is not None:
            _encoder_cache["encoder"] = enc
    n = img_tensor.shape[0]
    feats = []
    t_start = time.time()
    _last_report = 0
    with torch.no_grad():
        for i in range(0, n, batch):
            x = img_tensor[i:i + batch].to(device)
            y = enc(x).cpu().numpy()
            feats.append(y)
            n_done = min(i + batch, n)
            now = time.time()
            if (verbose
                and (n_done == n or (i // batch) - _last_report >= 20)):
                ips = n_done / max(now - t_start, 1e-6)
                remain_s = (n - n_done) / ips if ips > 0 else 0.0
                pct = n_done / n * 100.0
                print(f"    [FM forward] {n_done:6d}/{n} ({pct:5.1f}%)  "
                      f"speed={ips:7.1f} im/s  ETA_remain={remain_s/60:5.1f}min",
                      flush=True)
                _last_report = i // batch
    out = np.concatenate(feats, axis=0)
    if verbose:
        print(f"    [FM done] shape={out.shape}  total={time.time()-t_start:.1f}s",
              flush=True)
    return out


def _is_visium_dir(d: Path) -> bool:
    if not d.is_dir():
        return False
    if (d / "filtered_feature_bc_matrix.h5").exists():
        return True
    br = d / "binned_outputs"
    if br.exists():
        for sub in sorted([p for p in br.iterdir() if p.is_dir()]):
            if (sub / "filtered_feature_bc_matrix.h5").exists():
                return True
    return False


def _hpv_overlap_topk(ytrue: np.ndarray, ypred: np.ndarray, genes, topk=50):
    """Given (test_spots, genes) true/pred expression, compute the fraction of
    the top-K highest-predicted (mean across test spots) genes that belong to
    the HPV-related gene panel. Higher = baseline learned more HPV biology."""
    mean_pred = ypred.mean(axis=0)  # (genes,)
    top_idx = np.argsort(-mean_pred)[:topk]
    top_genes = [genes[i] for i in top_idx]
    n_hpv = sum(1 for g in top_genes if g in HPV_GENES)
    return float(n_hpv) / float(topk), top_genes


def evaluate_split(reg_name: str, Xtr, ytr, Xte, yte, genes,
                   label: str = "", gene_progress_every: int = 100) -> dict:
    """Fit regressor on (Xtr, ytr) → predict (Xte, yte) → compute metrics.

    Two code paths:
      * ridge / knn  → sklearn native multi-output fit (fast, black-box).
      * svr / rf / mlp → per-gene serial fit.  This adds ~5-10% overhead vs
        MultiOutputRegressor but gives us:
        1) per-gene progress prints (no "stuck for 30 min with no output")
        2) per-gene try/except — a single impossible gene will not kill an
           entire LOSO fold that already took 20 minutes to reach.
    """
    import gc as _gc
    t0 = time.time()
    n_genes = ytr.shape[1]
    ypred = np.zeros_like(yte, dtype=np.float32)
    gene_failures = []

    if reg_name in ("ridge", "knn"):
        # Native multi-output: no per-gene progress (finishes in seconds anyway).
        # Print explicit start/stop + elapsed so user sees ridge isn't "stuck".
        t_fit = time.time()
        n_s, n_g = Xtr.shape
        print(f"    [fit {reg_name} start] train_mat=({n_s},{n_g}) RidgeCV/native ...",
              flush=True)
        base = make_regressor(reg_name)
        base.fit(Xtr, ytr)
        ypred[:, :] = base.predict(Xte).astype(np.float32, copy=False)
        print(f"    [fit {reg_name} done] elapsed={time.time()-t_fit:.1f}s",
              flush=True)
    else:
        # --- per-gene path with visible progress ----------------------------
        t_fit_start = time.time()
        for g in range(n_genes):
            yg_tr = np.ascontiguousarray(ytr[:, g])
            if yg_tr.std() < 1e-8:
                # Constant gene: predict mean directly, skip fit entirely
                ypred[:, g] = yg_tr.mean()
            else:
                try:
                    model = make_regressor(reg_name)
                    model.fit(Xtr, yg_tr)
                    ypred[:, g] = model.predict(Xte).astype(np.float32, copy=False)
                except Exception as e:
                    gene_failures.append(
                        f"gene_idx={g} name={genes[g] if g < len(genes) else '?'} "
                        f"{type(e).__name__}: {str(e)[:200]}"
                    )
                    # Fallback → predict training-set mean.  The fold will
                    # still produce metrics but MSE/Pearson for this gene is
                    # conservative, never a showstopper.
                    ypred[:, g] = yg_tr.mean()
            if ((g + 1) % gene_progress_every == 0) or ((g + 1) == n_genes):
                elapsed = time.time() - t_fit_start
                n_done = g + 1
                ms_per_gene = elapsed * 1000.0 / max(n_done, 1)
                remaining_genes = n_genes - n_done
                eta_remain_s = remaining_genes * (elapsed / max(n_done, 1))
                print(
                    f"    [gene {n_done:4d}/{n_genes}] "
                    f"elapsed={elapsed:6.1f}s  "
                    f"avg={ms_per_gene:5.1f}ms/gene  "
                    f"ETA_remain={eta_remain_s/60:5.1f}min  "
                    f"fails={len(gene_failures)}",
                    flush=True,
                )
                # Release per-gene model / temp arrays as soon as possible.
                _gc.collect()

    fit_s = time.time() - t0
    mse = float(np.mean((ypred - yte) ** 2))
    # per-gene Pearson
    cors = []
    for g in range(yte.shape[1]):
        if yte[:, g].std() > 1e-6 and ypred[:, g].std() > 1e-6:
            try:
                cors.append(float(pearsonr(ypred[:, g], yte[:, g])[0]))
            except Exception:
                pass
    mean_corr = float(np.nanmean(cors)) if cors else float("nan")
    hpv_ov, _ = _hpv_overlap_topk(yte, ypred, genes, topk=50)
    result = {
        "label": label,
        "regressor": reg_name,
        "n_train": int(Xtr.shape[0]),
        "n_test": int(Xte.shape[0]),
        "fit_seconds": round(fit_s, 1),
        "heldout_recon_mse": round(mse, 5),
        "mean_per_gene_pearson": round(mean_corr, 4),
        "hpv_top50_overlap": round(hpv_ov, 4),
    }
    if gene_failures:
        result["gene_failures_head"] = gene_failures[:10]
        result["gene_failures_n"] = len(gene_failures)
    return result


def _load_one_paired(sd: Path, fm: str, device, n_genes, patch_size,
                     fm_out_dir: Path | None = None, _encoder_cache: dict | None = None,
                     verbose: bool = True):
    """Load one Visium sample → (exp, FM features X, genes).

    New observability + caching vs previous version:
      * Writes / reads ``<fm_out_dir>/FM_<sample>_<fm>_<patch_size>_<n_genes>.npz``
        with keys (X, exp, genes).  On 35-sample runs where UNI patch features
        are the #1 bottleneck, this hits ~100% after first run and turns a
        20-40 min / sample job into 2-5 seconds.
      * ``_encoder_cache`` holds the shared FM encoder across 35 samples so we
        don't reload UNI weights 35 times.
    """
    import hashlib, pickle
    # Stable cache key tied to sample dir + fm + patch_size + n_genes so
    # changing any knob automatically invalidates.
    tag_src = f"{sd.resolve()}|{fm}|{patch_size}|{n_genes}"
    tag = hashlib.sha1(tag_src.encode("utf-8")).hexdigest()[:12]
    cache_path = None
    if fm_out_dir is not None:
        fm_out_dir.mkdir(parents=True, exist_ok=True)
        cache_path = fm_out_dir / f"FM_{sd.name}_{fm}_p{patch_size}_g{n_genes}_{tag}.npz"
    if cache_path is not None and cache_path.exists():
        try:
            t0 = time.time()
            data = np.load(cache_path, allow_pickle=False)
            X = data["X"]
            exp = data["exp"]
            genes = data["genes"].tolist() if "genes" in data.files else None
            if verbose:
                print(f"    [FM cache HIT] {cache_path.name}  load={time.time()-t0:.2f}s  "
                      f"spots={X.shape[0]} genes={exp.shape[1]} fm_dim={X.shape[1]}",
                      flush=True)
            return {"name": sd.name, "exp": exp, "X": X, "genes": genes}
        except Exception as e:
            if verbose:
                print(f"    [FM cache BAD] {cache_path.name} {type(e).__name__}: {e}; "
                      f"recomputing ...", flush=True)
    t0 = time.time()
    if verbose:
        print(f"    [build_paired] crop patches + HVG select {sd.name} ...", flush=True)
    sample = S.load_sample(sd)
    # ---- Signature probe for backward compatibility ------------------------
    # Aug-2026 we added `verbose` kwarg to src.st_data.build_paired_tensors.
    # If the user hasn't yet refreshed src/st_data.py on the server, passing
    # verbose would raise TypeError.  We inspect and only pass verbose when
    # the installed signature accepts it; missing progress prints are a mild
    # cosmetic loss, but a hard crash blocks the whole LOSO run.
    try:
        _sig = inspect.signature(S.build_paired_tensors)
        _has_verbose = "verbose" in _sig.parameters
    except (TypeError, ValueError):
        _has_verbose = False
    bpt_kwargs = dict(n_genes_keep=n_genes, patch_size=patch_size)
    if _has_verbose:
        bpt_kwargs["verbose"] = bool(verbose)
    else:
        if verbose:
            print("    [build_paired] note: st_data.py on host lacks verbose "
                  "patch-progress; patch/FM steps will still run but no per-500 "
                  "progress prints.  Re-upload src/st_data.py to enable them.",
                  flush=True)
    paired = S.build_paired_tensors(sample, **bpt_kwargs)
    exp = np.asarray(paired["exp"].numpy(), dtype=np.float32)
    genes = paired["genes"]
    X = extract_fm_features(paired["img"], fm, device,
                            _encoder_cache=_encoder_cache, _fm_name=fm,
                            verbose=verbose)
    if verbose:
        print(f"    [load_sample done] {sd.name}: spots={exp.shape[0]} genes={exp.shape[1]} "
              f"FM_feat_dim={X.shape[1]}  total={time.time()-t0:.1f}s", flush=True)
    # Write cache atomically (tmp → rename) so an aborted run never leaves a
    # half-written .npz that looks valid to the next run.
    if cache_path is not None:
        try:
            tmp = cache_path.with_suffix(".npz.tmp")
            np.savez_compressed(tmp, X=X, exp=exp,
                                genes=np.asarray(genes, dtype=object))
            tmp.replace(cache_path)
            if verbose:
                sz = cache_path.stat().st_size / (1024 * 1024)
                print(f"    [FM cache WRITTEN] {cache_path.name}  size={sz:.1f}MB",
                      flush=True)
        except Exception as e:
            if verbose:
                print(f"    [FM cache write SKIP] {type(e).__name__}: {e}", flush=True)
    return {"name": sd.name, "exp": exp, "X": X, "genes": genes}


def run_single_sample(args):
    device = torch.device(args.device)
    p = Path(args.data)
    print(f"[mode=single] sample={p}", flush=True)
    fm_dir = None
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    if getattr(args, "fm_cache_dir", None):
        fm_dir = Path(args.fm_cache_dir)
    elif not getattr(args, "no_fm_cache", False):
        # Default baseline FM cache lives next to train_st results cache so the
        # two scripts can share: results/cache/baseline_fm
        fm_dir = out_dir / "cache" / "baseline_fm"
    enc_cache: dict = {}
    d = _load_one_paired(p, args.fm, device, args.n_genes, args.patch_size,
                         fm_out_dir=fm_dir, _encoder_cache=enc_cache)
    exp, X, genes = d["exp"], d["X"], d["genes"]
    print(f"[data] {d['name']}: spots={exp.shape[0]} genes={exp.shape[1]} "
          f"FM_feat_dim={X.shape[1]}")

    Xtr, Xte, ytr, yte = train_test_split(X, exp, test_size=args.test_size,
                                           random_state=0)
    regressors = list(args.regressors_used)
    per_reg = []
    gene_every = int(getattr(args, "gene_progress_every", 100))
    for r in regressors:
        print(f"  [train] {r} ...", flush=True)
        per_reg.append(evaluate_split(r, Xtr, ytr, Xte, yte, genes,
                                      label=f"single@{d['name']}",
                                      gene_progress_every=gene_every))
    _dump_and_print(args, {
        "mode": "single_sample_80_20",
        "fm": args.fm,
        "sample": d["name"],
        "n_hpv_genes_panel": len(HPV_GENES),
        "per_regressor": per_reg,
    })


def run_loso(args):
    device = torch.device(args.device)
    root = Path(args.data)
    if _is_visium_dir(root):
        sample_dirs = [root]
    else:
        sample_dirs = [sd for sd in sorted(root.iterdir()) if _is_visium_dir(sd)]
    # DEBUG cut-in: allow --sample_limit 8 to quickly smoke-test LOSO loop on
    # the first 8 slides before committing to a 3-hour 35-slide run.
    if getattr(args, "sample_limit", None) is not None and args.sample_limit > 0:
        sample_dirs = sample_dirs[:args.sample_limit]
        print(f"[mode=loso] --sample_limit set → truncated to first "
              f"{len(sample_dirs)} samples")
    print(f"[mode=loso] found {len(sample_dirs)} samples under {root}")
    if len(sample_dirs) < 2:
        raise SystemExit("LOSO mode requires >=2 samples in --data")

    # ---- 0) Resolve FM cache dir; load shared FM encoder once (NOT 35x) ----
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    fm_dir = None
    if getattr(args, "fm_cache_dir", None):
        fm_dir = Path(args.fm_cache_dir)
    elif not getattr(args, "no_fm_cache", False):
        fm_dir = out_dir / "cache" / "baseline_fm"
    enc_cache: dict = {}

    # ---- 1) load all samples with UNION gene panel ----
    raw = []
    t_load0 = time.time()
    for si, sd in enumerate(sample_dirs, 1):
        print(f"\n  [load sample {si}/{len(sample_dirs)}] {sd.name}", flush=True)
        # Memory-safer n_genes: load generous HVG per sample, but cap the
        # per-sample union-intersect step later to the user --n_genes ceiling.
        t_s = time.time()
        raw.append(_load_one_paired(sd, args.fm, device,
                                    max(args.n_genes, 2500), args.patch_size,
                                    fm_out_dir=fm_dir,
                                    _encoder_cache=enc_cache,
                                    verbose=not getattr(args, "quiet", False)))
        gc.collect()  # drop temporary tensors after every sample
        if si == 1 or si % 5 == 0 or si == len(sample_dirs):
            elapsed = time.time() - t_load0
            avg_s = elapsed / si
            remain_s = (len(sample_dirs) - si) * avg_s
            print(f"  [load progress] {si}/{len(sample_dirs)} samples  "
                  f"elapsed={elapsed/60:5.1f}min  "
                  f"avg_per_sample={avg_s:5.1f}s  "
                  f"ETA_load_remain={remain_s/60:5.1f}min",
                  flush=True)

    all_genes = set()
    for d in raw:
        all_genes.update(d["genes"])
    all_genes = sorted(all_genes | HPV_GENES)

    print(f"  [align] union gene panel = {len(all_genes)} -> keeping top {args.n_genes} HVGs",
          flush=True)
    aligned_exp = []
    gene_to_idx = {g: i for i, g in enumerate(all_genes)}
    t_a0 = time.time()
    N_RAW = len(raw)
    for di, d in enumerate(raw, 1):
        e = np.zeros((d["exp"].shape[0], len(all_genes)), dtype=np.float32)
        d_g2i = {g: i for i, g in enumerate(d["genes"])}
        for g in d["genes"]:
            if g in gene_to_idx:
                e[:, gene_to_idx[g]] = d["exp"][:, d_g2i[g]]
        aligned_exp.append(e)
        if di == 1 or di % 5 == 0 or di == N_RAW:
            el = time.time() - t_a0
            per_s = el / di
            rem = (N_RAW - di) * per_s
            print(f"  [align sample {di}/{N_RAW}] elapsed={el:5.1f}s  "
                  f"avg={per_s:5.1f}s/sample  ETA_remain={rem/60:4.1f}min",
                  flush=True)
    # Drop the original per-sample raw.exp early; we only keep aligned copy + Xs.
    for d in raw:
        d.pop("exp", None)
    gc.collect()
    print("  [align] computing union variance across all spots for final HVG ...",
          flush=True)
    t_a1 = time.time()
    stacked = np.concatenate(aligned_exp, axis=0)
    var = stacked.var(axis=0)
    hpv_positions = np.array([gene_to_idx[g] for g in HPV_GENES if g in gene_to_idx],
                             dtype=np.int64)
    top_hvg = np.argsort(-var)[:args.n_genes]
    keep = np.unique(np.concatenate([top_hvg, hpv_positions]))
    keep = keep[:args.n_genes + len(hpv_positions)]
    print(f"  [align variance] spots={stacked.shape[0]} union_genes={len(var)} "
          f"took {time.time()-t_a1:.1f}s → top {args.n_genes} HVG + HPV={len(hpv_positions)}",
          flush=True)
    t_a2 = time.time()
    for i in range(len(aligned_exp)):
        aligned_exp[i] = aligned_exp[i][:, keep]
    final_genes = [all_genes[i] for i in keep]
    del stacked, var, top_hvg, keep
    gc.collect()
    print(f"  [align] final gene panel = {len(final_genes)} "
          f"(includes {sum(1 for g in final_genes if g in HPV_GENES)} HPV genes) "
          f"total_align={time.time()-t_a0:.1f}s",
          flush=True)

    Xs = [d["X"] for d in raw]
    names = [d["name"] for d in raw]
    raw.clear()  # last reference drop
    gc.collect()

    regressors = list(args.regressors_used)
    gene_every = int(getattr(args, "gene_progress_every", 100))
    per_reg_summary = []
    failed_folds = []
    total_folds_planned = len(regressors) * len(names)
    folds_completed = 0
    t_wall_start = time.time()

    for reg_idx, reg_name in enumerate(regressors):
        folds = []
        print(f"\n==== LOSO regressor={reg_name} ({reg_idx+1}/{len(regressors)}) ====",
              flush=True)
        for held_out in range(len(names)):
            folds_completed += 1
            # Global ETA across ALL folds (regressors × samples), visible top-of-fold.
            if folds_completed >= 2:
                elapsed_wall = time.time() - t_wall_start
                per_fold_avg = elapsed_wall / max(folds_completed - 1, 1)
                remaining_folds = total_folds_planned - folds_completed + 1
                eta_min = (remaining_folds * per_fold_avg) / 60.0
                print(
                    f"  [progress {folds_completed}/{total_folds_planned}] "
                    f"avg_fold={per_fold_avg/60:5.2f}min  ETA_TOTAL_remain={eta_min:6.1f}min",
                    flush=True,
                )

            Xtr_list, ytr_list = [], []
            for i in range(len(names)):
                if i == held_out:
                    continue
                Xtr_list.append(Xs[i])
                ytr_list.append(aligned_exp[i])
            Xtr = np.concatenate(Xtr_list, axis=0)
            ytr = np.concatenate(ytr_list, axis=0)
            Xte = Xs[held_out]
            yte = aligned_exp[held_out]
            print(f"  [fold held={names[held_out]}] "
                  f"train={Xtr.shape[0]} test={Xte.shape[0]} ...",
                  flush=True)
            try:
                r = evaluate_split(reg_name, Xtr, ytr, Xte, yte, final_genes,
                                   label=f"loso_held={names[held_out]}",
                                   gene_progress_every=gene_every)
                folds.append(r)
                print(f"         MSE={r['heldout_recon_mse']}  "
                      f"Pearson={r['mean_per_gene_pearson']}  "
                      f"HPV_overlap={r['hpv_top50_overlap']}",
                      flush=True)
            except Exception as e:
                # Fold-level failure: log a full traceback to stdout, keep the
                # run moving, and store the failure in JSON for later audit.
                tb = traceback.format_exc()
                err_str = f"{type(e).__name__}: {e}"
                print(f"  !! [FAIL fold held={names[held_out]} reg={reg_name}] "
                      f"{err_str}\n{tb}", flush=True)
                failed_folds.append({
                    "regressor": reg_name,
                    "held_out_sample": names[held_out],
                    "fold_index": held_out,
                    "error": err_str,
                    "traceback": tb,
                })
                folds.append({
                    "label": f"loso_held={names[held_out]}",
                    "regressor": reg_name,
                    "n_train": int(Xtr.shape[0]),
                    "n_test": int(Xte.shape[0]),
                    "fit_seconds": 0.0,
                    "heldout_recon_mse": float("nan"),
                    "mean_per_gene_pearson": float("nan"),
                    "hpv_top50_overlap": float("nan"),
                    "fold_failed": True,
                })
            finally:
                # Drop the big train/test matrices EVERY fold; this is what
                # prevents the 10→20→40GB creep that triggers OOM -Killed.
                del Xtr, ytr, Xte, yte, Xtr_list, ytr_list
                gc.collect()

        valid = [f for f in folds if not f.get("fold_failed", False)]
        agg = {
            "regressor": reg_name,
            "n_valid_folds": len(valid),
            "n_failed_folds": len(folds) - len(valid),
            "mean_mse":        round(float(np.nanmean([f['heldout_recon_mse'] for f in valid])), 5) if valid else float("nan"),
            "mean_pearson":    round(float(np.nanmean([f['mean_per_gene_pearson'] for f in valid])), 4) if valid else float("nan"),
            "mean_hpv_overlap":round(float(np.nanmean([f['hpv_top50_overlap'] for f in valid])), 4) if valid else float("nan"),
            "fit_seconds_sum": round(float(sum(f['fit_seconds'] for f in folds)), 1),
        }
        per_reg_summary.append({"aggregate": agg, "per_fold": folds})
        print(f"  -> AGGREGATE {reg_name}: n_valid={agg['n_valid_folds']}/"
              f"{len(folds)}  MSE={agg['mean_mse']}  "
              f"Pearson={agg['mean_pearson']}  HPV_top50={agg['mean_hpv_overlap']}",
              flush=True)
        gc.collect()

    payload = {
        "mode": "loso_cross_sample",
        "fm": args.fm,
        "samples": names,
        "n_samples": len(names),
        "n_hpv_genes_panel": len(HPV_GENES),
        "n_final_genes": len(final_genes),
        "per_regressor": per_reg_summary,
        "wall_seconds_total": round(time.time() - t_wall_start, 1),
    }
    if failed_folds:
        payload["failed_folds"] = failed_folds
        payload["n_failed_folds"] = len(failed_folds)
    _dump_and_print(args, payload)


def _dump_and_print(args, payload: dict):
    print("\n===== BASELINE COMPARISON SUMMARY =====")
    print(json.dumps(payload, indent=2, default=str))
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"baseline_{args.run_id}.json"
    out_path.write_text(json.dumps(payload, indent=2, default=str))
    print(f"\nSaved: {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/st_visium/cervical_cancer_1")
    ap.add_argument("--fm", default="uni")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--n_genes", type=int, default=2000,
                    help="# HVGs kept after union (memory / speed knob). 1000-1500 "
                         "is plenty for baseline comparison on cervix Visium.")
    ap.add_argument("--patch_size", type=int, default=224)
    ap.add_argument("--test_size", type=float, default=0.2)
    ap.add_argument("--regressor", default="ridge",
                    help="Comma-separated subset of baselines to run, "
                         "OR the single keyword 'all' for all 5 baselines. "
                         "Valid names: knn,ridge,svr,rf,mlp. "
                         "Examples: --regressor ridge  OR  --regressor ridge,svr,rf  OR  --regressor all",
                    metavar="R")
    ap.add_argument("--mode", default="single", choices=["single", "loso"])
    ap.add_argument("--run_id", default="BASELINE_HE2ST")
    ap.add_argument("--out", default="results")
    # ----- Progress / observability knobs ---------------------------------
    ap.add_argument("--gene_progress_every", type=int, default=100,
                    help="Print per-gene progress every N genes for svr/rf/mlp. "
                         "50 = more output; 200 = quieter. Only used in per-gene path.")
    ap.add_argument("--sample_limit", type=int, default=None,
                    help="DEBUG/LOSO smoke-test: keep only first N samples from "
                         "--data parent dir. Use 6 to validate full pipeline in "
                         "~20 minutes before a 3-hour 35-sample run.")
    # ----- Speed / observability knobs ------------------------------------
    fm_cache_default = "results/cache/baseline_fm"
    ap.add_argument("--fm_cache_dir", default=None,
                    help=f"Directory to cache per-sample FM (patch) feature "
                         f"matrices. Default = {fm_cache_default}. First run "
                         f"writes .npz here; every next run reads → turns the "
                         f"slow FM patch-forward step (minutes/slide) into 2-5s/slide.")
    ap.add_argument("--no_fm_cache", action="store_true",
                    help="Disable FM cache recompute from scratch every run.")
    ap.add_argument("--quiet", action="store_true",
                    help="Disable per-sample verbose patch/HVG progress; only "
                         "load/align/fold level progress and summary are printed.")
    args = ap.parse_args()

    # ----- Parse --regressor ----------------------------------------------
    # Accept (case-insensitive, whitespace-tolerant):
    #   'all'                          -> REGRESSOR_NAMES
    #   'ridge'                        -> ['ridge']
    #   'ridge, svr, rf' / 'ridge,svr,rf' -> ['ridge','svr','rf']
    raw_reg = str(args.regressor).strip().lower()
    if raw_reg == "all":
        regressors_used = list(REGRESSOR_NAMES)
    else:
        pieces = [p.strip() for p in raw_reg.split(",") if p.strip()]
        bad = [p for p in pieces if p not in REGRESSOR_NAMES]
        if bad:
            raise SystemExit(
                f"--regressor: invalid name(s): {bad}. "
                f"Valid names: {REGRESSOR_NAMES} (combine with comma, or use 'all')."
            )
        if not pieces:
            raise SystemExit("--regressor is empty. Use a name list or 'all'.")
        # Preserve user-given order but dedupe (first occurrence wins)
        seen, regressors_used = set(), []
        for p in pieces:
            if p not in seen:
                seen.add(p)
                regressors_used.append(p)
    # Stash back onto args for run_single_sample / run_loso which currently
    # read args.regressor as a name / 'all'; but we've already resolved into
    # args.regressors_used so downstream code paths are migrated to use that.
    args.regressors_used = regressors_used

    # Echo a compact banner so the top of the log immediately tells you what
    # combination was launched (helps when comparing multiple log files).
    print(
        f"[baseline_compare] mode={args.mode} fm={args.fm} "
        f"n_genes={args.n_genes} regressors={args.regressors_used} "
        f"sample_limit={args.sample_limit} gene_every={args.gene_progress_every}",
        flush=True,
    )

    if args.mode == "single":
        run_single_sample(args)
    else:
        run_loso(args)


if __name__ == "__main__":
    main()
