"""leave_disease_out.py — Leave-One-Disease-Out (LODO) generalization check.

Why this exists
---------------
The main-model core metrics (HPV-proxy AUC, Moran's I, Kendall tau) are all
computed on the *in-sample* 35-case cohort. A Q2 reviewer will ask whether the
learned "disease > normal" risk ordering actually generalises to an UNSEEN
disease slide. Because the disease cohort is tiny (HSIL/CIN3 n=1, SCC n=2,
ADC n=1 => 4 disease samples), we use leave-one-disease-out cross-validation:

  for each disease sample D:
      train the FULL model on the other 34 samples (31 normal + 3 disease)
      score D with the fitted model  (genuine out-of-sample)
      report where D's case-level risk score ranks among the 30 normal samples

The aggregate metric is the out-of-sample percentile/rank of each held-out
disease slide among normal slides: a model that learned a real biological axis
should score every unseen disease slide ABOVE the normal slides.

This is executed as a thin orchestrator over scripts/train_st.py using its new
--leave_out_substr flag (train_st.py trains on everything except the matched
sample, then infers + reports out['holdout']).

Usage
-----
    python scripts/leave_disease_out.py \
        --data data/st_visium \
        --histology_label_csv data/st_visium/labels/cervix_histology_labels_extended.csv \
        --exclude_substr breast,ovarian,prostate,visium_hd \
        --device cuda --epochs 40 --permutation_n 1000 --fm_cache \
        --fm uni --hpv_gene_set default
"""
from __future__ import annotations
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))


def _json_safe(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, str)):
        return v
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    try:
        import numpy as np
        if isinstance(v, np.generic):
            return _json_safe(v.item())
    except Exception:
        pass
    if isinstance(v, dict):
        return {str(k): _json_safe(vv) for k, vv in v.items()}
    if isinstance(v, (list, tuple)):
        return [_json_safe(x) for x in v]
    return str(v)


def _read_disease_samples(histology_csv: Path) -> list[str]:
    """Return disease-sample *leaf dir names* (progression_ordinal >= 1).

    The extended CSV labels ectocervix samples as "ecto_P###", but train_st.py's
    discovery returns the bare leaf name "P###". Handle both forms so the
    disease list matches what --leave_out_substr will see.
    """
    import pandas as pd
    df = pd.read_csv(histology_csv)
    required = {"sample_id", "progression_ordinal"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"histology CSV missing columns: {missing}")
    disease = []
    for _, row in df.iterrows():
        try:
            ordinal = int(row["progression_ordinal"])
        except (TypeError, ValueError):
            continue
        if ordinal < 1:
            continue
        sid = str(row["sample_id"]).strip()
        # bare leaf name (strip any "ecto_" prefix; disease samples carry none)
        leaf = sid[len("ecto_"):] if sid.startswith("ecto_") else sid
        disease.append(leaf)
    # preserve CSV order, dedup
    seen, out = set(), []
    for d in disease:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


def _normal_leaf_names(histology_csv: Path) -> set[str]:
    import pandas as pd
    df = pd.read_csv(histology_csv)
    normals = set()
    for _, row in df.iterrows():
        try:
            ordinal = int(row["progression_ordinal"])
        except (TypeError, ValueError):
            continue
        if ordinal != 0:
            continue
        sid = str(row["sample_id"]).strip()
        leaf = sid[len("ecto_"):] if sid.startswith("ecto_") else sid
        normals.add(leaf)
    return normals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/st_visium")
    ap.add_argument("--histology_label_csv",
                    default="data/st_visium/labels/cervix_histology_labels_extended.csv")
    ap.add_argument("--exclude_substr", default="breast,ovarian,prostate,visium_hd")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--bs", type=int, default=256)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--n_genes", type=int, default=2000)
    ap.add_argument("--max_spots", type=int, default=0)
    ap.add_argument("--fm", default="uni")
    ap.add_argument("--hpv_gene_set", default="default")
    # Loss weights — DEFAULTS match the locked main configuration
    # (lambda_hpv=1.0 / lambda_neigh=0.3 / lambda_recon=1.0) so LODO folds are
    # directly comparable to results_FULL.json. Do NOT change without also
    # re-running the main claim.
    ap.add_argument("--lambda_hpv", type=float, default=1.0)
    ap.add_argument("--lambda_neigh", type=float, default=0.3)
    ap.add_argument("--lambda_recon", type=float, default=1.0)
    ap.add_argument("--fm_cache", action="store_true")
    ap.add_argument("--permutation_n", type=int, default=1000)
    ap.add_argument("--save_checkpoint", action="store_true",
                    help="Also save a deployable checkpoint per fold.")
    args = ap.parse_args()

    RESULTS = ROOT / "results"
    RESULTS.mkdir(parents=True, exist_ok=True)

    disease = _read_disease_samples(Path(args.histology_label_csv))
    normals = _normal_leaf_names(Path(args.histology_label_csv))
    print(f"[LODO] disease samples ({len(disease)}): {disease}")
    print(f"[LODO] normal samples ({len(normals)}): {sorted(normals)}")

    folds = []
    for dname in disease:
        run_id = f"LODO_{dname}"
        out_json = RESULTS / f"results_{run_id}.json"
        if out_json.exists():
            out_json.unlink()
        cmd = [
            sys.executable, str(HERE / "train_st.py"),
            "--data", args.data,
            "--device", args.device,
            "--epochs", str(args.epochs),
            "--bs", str(args.bs),
            "--lr", str(args.lr),
            "--n_genes", str(args.n_genes),
            "--fm", args.fm,
            "--hpv_gene_set", args.hpv_gene_set,
            "--lambda_hpv", str(args.lambda_hpv),
            "--lambda_neigh", str(args.lambda_neigh),
            "--lambda_recon", str(args.lambda_recon),
            "--histology_label_csv", args.histology_label_csv,
            "--exclude_substr", args.exclude_substr,
            "--permutation_n", str(args.permutation_n),
            "--leave_out_substr", dname,
            "--run_id", run_id,
        ]
        if args.max_spots:
            cmd += ["--max_spots", str(args.max_spots)]
        if args.fm_cache:
            cmd += ["--fm_cache"]
        if args.save_checkpoint:
            cmd += ["--save_checkpoint"]
        print(f"\n===== LODO FOLD: hold out {dname} (run_id={run_id}) =====")
        rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
        if rc != 0:
            print(f"[warn] {run_id} exited with code {rc}; skipping fold")
            folds.append({"holdout_sample": dname, "error": f"exit code {rc}"})
            continue
        try:
            res = json.loads(out_json.read_text())
        except FileNotFoundError:
            print(f"[warn] {run_id} produced no results json; skipping fold")
            folds.append({"holdout_sample": dname, "error": "no results json"})
            continue

        holdout = res.get("holdout") or {}
        ho = holdout.get(dname) or (next(iter(holdout.values())) if holdout else None)
        ho_mean = None
        if isinstance(ho, dict) and "mean_risk" in ho:
            ho_mean = float(ho["mean_risk"])

        train_scores = res.get("per_sample_score") or {}
        normal_scores = [float(train_scores[n]) for n in sorted(normals)
                         if n in train_scores and train_scores[n] is not None]

        fold = {
            "holdout_sample": dname,
            "holdout_mean_risk": ho_mean,
            "n_train_samples": int(res.get("n_samples", 0)),
            "n_normal_train": len(normal_scores),
            "normal_scores": normal_scores,
        }
        if ho_mean is not None and normal_scores:
            norm_arr = sorted(normal_scores)
            # percentile: fraction of normal slides scored STRICTLY below the
            # held-out disease slide (0..1); 1.0 = disease > all normals.
            below = sum(1 for x in norm_arr if x < ho_mean)
            fold["percentile_vs_normal"] = below / len(norm_arr)
            fold["above_median_normal"] = bool(ho_mean > float(
                norm_arr[len(norm_arr) // 2]))
            fold["above_all_normal"] = bool(ho_mean > max(norm_arr))
        print(f"  holdout {dname}: mean_risk={ho_mean} | "
              f"percentile_vs_normal={fold.get('percentile_vs_normal')} | "
              f"above_all_normal={fold.get('above_all_normal')}")
        folds.append(fold)

    # ---- aggregate ----
    n_ok = sum(1 for f in folds if "percentile_vs_normal" in f)
    percentiles = [f["percentile_vs_normal"] for f in folds
                   if "percentile_vs_normal" in f]
    above_all = sum(1 for f in folds if f.get("above_all_normal"))
    above_med = sum(1 for f in folds if f.get("above_median_normal"))

    summary = {
        "description": "Leave-one-disease-out generalization of disease-vs-normal risk ordering",
        "n_disease_folds": len(folds),
        "n_successful_folds": n_ok,
        "mean_percentile_vs_normal": (
            float(sum(percentiles) / len(percentiles)) if percentiles else None),
        "min_percentile_vs_normal": (min(percentiles) if percentiles else None),
        "n_above_all_normal": above_all,
        "n_above_median_normal": above_med,
        "folds": _json_safe(folds),
    }
    (RESULTS / "leave_disease_out_summary.json").write_text(
        json.dumps(_json_safe(summary), indent=2, default=str, allow_nan=False))

    print("\n===== LODO SUMMARY =====")
    print(f"folds: {n_ok}/{len(folds)} successful")
    print(f"mean percentile-vs-normal: {summary['mean_percentile_vs_normal']}")
    print(f"min percentile: {summary['min_percentile_vs_normal']}")
    print(f"held-out disease ranked above ALL normals: {above_all}/{len(folds)}")
    print(f"held-out disease ranked above MEDIAN normal: {above_med}/{len(folds)}")
    print(f"Saved results/leave_disease_out_summary.json")


if __name__ == "__main__":
    main()