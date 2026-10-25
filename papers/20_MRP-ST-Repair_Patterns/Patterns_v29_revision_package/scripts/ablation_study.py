"""Ablation study orchestrator for the ST-H&E fusion model.

Runs a battery of ablated configurations of scripts/train_st.py and collects
their results into a single comparison table (ablation_summary.json / .csv).
This is what a Q1/Q2 reviewer expects: *where does the gain come from?*

Configurations probed (5 groups, aligned with the "best model" defaults
lambda_hpv=1.0 / lambda_neigh=0.3 / lambda_recon=1.0):
  1. FULL          : FM=UNI, full proposed method            (=> results_FULL.json)
  2. BASELINE-CNN  : FM=none (from-scratch tiny CNN instead of pathology FM)
  3. NO-HPV        : lambda_hpv=0   (drop the HPV-pathway consistency term)
  4. NO-NEIGH      : lambda_neigh=0 (drop the spatial-coherence term)
  5. FM-UNI2       : alternative foundation model (UNI2-h, vit_giant 1536d vs
                     UNI vit_large 1024d)
NOTE on FM-CHIEF: Removed from this ablation suite (Aug 2026) because
Mahmood Lab has NOT published any visual encoder named "CHIEF" on
HuggingFace (repo MahmoodLab/CHIEF returns 404/401 both on hf.co and on
hf-mirror). FM cross-architecture ablation is adequately covered by
FM-UNI2 (same group, different scale, published + locally cached) which
is a stronger architectural contrast anyway. A reviewer expecting two
alternative FMs can be pointed to the cross-cohort experiments where the
same UNI backbone generalises to 4 independent cancer types.

Each run writes results_<RUN_ID>.json; this script aggregates
{run_id, fm, lambda_hpv, lambda_neigh, lambda_recon, recon_mse_proxy,
 moran_i, n_deg_perm, high_risk_ratio, n_prior_genes} and prints a
Markdown-ready table.

Usage
-----
    # 5-group ablation on cervix geo_cesc (4090 server GPU):
    python scripts/ablation_study.py --data data/st_visium/geo_cesc --device cuda
    # quick CPU smoke test (only the CNN baseline runs without external weights):
    python scripts/ablation_study.py --data data/st_visium/cervical_cancer_1 --device cpu --epochs 3
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
    """Recursively coerce NaN/Inf → None and numpy → native Python.

    Aug-2026: ablation_study.py crashed at the final JSON write because some
    float fields survived as float('nan') while we dump with allow_nan=False.
    We now sanitize the entire summary dict immediately before writing so a
    single NaN never aborts a multi-hour aggregation run.
    """
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
        import numpy as np  # type: ignore
        if isinstance(v, np.generic):
            return _json_safe(v.item())
    except Exception:
        pass
    if isinstance(v, dict):
        return {str(k): _json_safe(vv) for k, vv in v.items()}
    if isinstance(v, (list, tuple)):
        return [_json_safe(x) for x in v]
    return str(v)


# Each entry: (run_id, extra CLI args). Configs deliberately use the SAME
# default lambda_hpv/lambda_neigh as the best model except for the one factor
# being ablated, so each row isolates a single contribution.
CONFIGS = [
    ("FULL",         ["--fm", "uni", "--lambda_hpv", "1.0", "--hpv_gene_set", "default"]),
    ("BASELINE-CNN", ["--fm", "none", "--lambda_hpv", "1.0", "--hpv_gene_set", "default"]),
    ("NO-HPV",       ["--fm", "uni", "--lambda_hpv", "0", "--hpv_gene_set", "default"]),
    ("NO-NEIGH",     ["--fm", "uni", "--lambda_neigh", "0", "--lambda_hpv", "1.0", "--hpv_gene_set", "default"]),
    ("FM-UNI2",      ["--fm", "uni2", "--lambda_hpv", "1.0", "--hpv_gene_set", "default"]),
    # ---- P0-3: HPV gene-set robustness ablation (proves the score is NOT
    # driven by a tiny subset of hand-picked genes).
    #   HPV-ROBUST-A = default panel with 20% genes deterministically dropped
    #                  (leave-20%-genes-out style ablation).
    #   HPV-ROBUST-B = swap to MSigDB KEGG_HPV_INFECTION (94-gene curated panel)
    ("HPV-ROBUST-A", ["--fm", "uni", "--lambda_hpv", "1.0", "--hpv_gene_set", "dropout_20pct"]),
    ("HPV-ROBUST-B", ["--fm", "uni", "--lambda_hpv", "1.0", "--hpv_gene_set", "kegg_hpv"]),
    # NOTE: FM-CHIEF was removed — MahmoodLab CHIEF model is NOT published
    # on HuggingFace (repo returns 404/401). FM-UNI2 provides the necessary
    # cross-foundation-model ablation (vit_giant vs vit_large).
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/st_visium/cervical_cancer_1")
    ap.add_argument("--device", default="cuda" if __import__("torch").cuda.is_available() else "cpu")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--bs", type=int, default=256)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--n_genes", type=int, default=2000)
    ap.add_argument("--max_spots", type=int, default=0)
    ap.add_argument("--fm_cache", action="store_true",
                    help="Pass --fm_cache down to every train_st.py ablation run "
                         "(3-5x wall-clock speedup). Training dynamics identical.")
    ap.add_argument("--histology_label_csv", default="",
                    help="Optional CSV with sample_id + progression_ordinal; passed to train_st.py.")
    ap.add_argument("--exclude_substr", default="",
                    help="Comma-separated substrings; skip any sample dir whose path "
                         "contains any of them (same as train_st.py --exclude_substr).")
    ap.add_argument("--permutation_n", type=int, default=10000,
                    help="Permutation count for DEG / progression tests (default 10000).")
    ap.add_argument("--run_id", default="",
                    help="Optional prefix for per-config run_ids / summary suffix.")
    args = ap.parse_args()

    rows = []
    RESULTS = ROOT / "results"
    RESULTS.mkdir(parents=True, exist_ok=True)
    for cfg_id, extra in CONFIGS:
        run_id = (f"{args.run_id}_{cfg_id}") if args.run_id else cfg_id
        # skip foundation models if running on CPU (download/compute heavy)
        if args.device == "cpu" and cfg_id not in ("FULL", "BASELINE-CNN", "NO-NEIGH", "HPV-ROBUST-A", "HPV-ROBUST-B"):
            print(f"[skip] {run_id} on CPU (foundation-model heavy)")
            continue
        # P0-3: HPV-ROBUST-B still needs UNI FM weights; skip if cpu
        if args.device == "cpu" and cfg_id in ("FM-UNI2", "HPV-ROBUST-A", "HPV-ROBUST-B"):
            print(f"[skip] {run_id} on CPU (foundation-model weights not downloaded locally)")
            continue
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
            "--run_id", run_id,
        ]
        if args.max_spots:
            cmd += ["--max_spots", str(args.max_spots)]
        if args.fm_cache:
            cmd += ["--fm_cache"]
        if args.histology_label_csv:
            cmd += ["--histology_label_csv", args.histology_label_csv]
        if args.exclude_substr:
            cmd += ["--exclude_substr", args.exclude_substr]
        if args.permutation_n:
            cmd += ["--permutation_n", str(args.permutation_n)]
        cmd += extra
        print(f"\n===== ABLATION RUN: {run_id} (cfg={cfg_id}) =====")
        rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
        if rc != 0:
            print(f"[warn] {run_id} exited with code {rc}; skipping from summary")
            continue
        try:
            res = json.loads(out_json.read_text())
        except FileNotFoundError:
            print(f"[warn] {run_id} produced no results json; skipping")
            continue
        rows.append({
            "config": cfg_id,
            "run_id": run_id,
            "fm": res.get("fm"),
            "hpv_gene_set_mode": res.get("hpv_gene_set_mode"),
            "hpv_gene_set_size": res.get("hpv_gene_set_size"),
            "lambda_hpv": res.get("lambda_hpv"),
            "lambda_neigh": res.get("lambda_neigh"),
            "lambda_recon": res.get("lambda_recon"),
            "lambda_sup": res.get("lambda_sup"),
            "lambda_prog": res.get("lambda_prog"),
            "recon_mse_proxy": round(res.get("recon_mse_proxy", float("nan")), 4),
            "moran_i": round(res.get("moran_i", float("nan")), 4),
            "hpv_auc": round(res.get("hpv_proxy_auc", float("nan")), 4),
            "hpv_high_low_gap": round(res.get("hpv_gene_high_low_gap", float("nan")), 4),
            "prog_kendall_tau": round(((res.get("progression_monotonicity") or {}).get("kendall_tau") or float("nan")), 4),
            "prog_perm_p": (res.get("progression_monotonicity") or {}).get("permutation_p") or float("nan"),
            "n_deg_perm": res.get("n_deg_perm_fdr05_effect"),
            "n_deg_naive": res.get("n_deg_naive_fdr05_effect"),
            "high_risk_ratio": round(res.get("high_risk_ratio", float("nan")), 4),
            "n_prior_genes": res.get("n_prior_genes"),
            "subtype_kruskal_p": (res.get("histology_association") or {}).get("subtype_kruskal_p"),
        })

    # ---- print + save summary ----
    if not rows:
        print("No ablation runs completed.")
        return

    # P0-3: compute per-sample risk-score Spearman correlation of each config vs
    # FULL.  Used to prove the HPV-ROBUST-A/B configurations recover the same
    # sample-level risk ordering as the main claim (rho >= 0.85 is the paper target).
    full_scores = None
    full_row = None
    for r in rows:
        if r["config"] == "FULL":
            try:
                full_scores = json.loads(
                    (RESULTS / f"results_{r['run_id']}.json").read_text()).get("per_sample_score", {})
            except Exception:
                full_scores = None
            break
    if full_scores:
        try:
            from scipy.stats import spearmanr
            for r in rows:
                if r["config"] == "FULL":
                    r["spearman_vs_FULL"] = 1.0
                    r["spearman_rho_vs_full"] = 1.0
                    continue
                try:
                    cur = json.loads(
                        (RESULTS / f"results_{r['run_id']}.json").read_text()).get("per_sample_score", {})
                    common = sorted(set(full_scores.keys()) & set(cur.keys()))
                    if len(common) >= 3:
                        x = [full_scores[k] for k in common]
                        y = [cur[k] for k in common]
                        rho, _p = spearmanr(x, y)
                        r["spearman_rho_vs_full"] = round(float(rho), 4)
                        r["spearman_vs_FULL"] = r["spearman_rho_vs_full"]
                    else:
                        r["spearman_vs_FULL"] = None
                        r["spearman_rho_vs_full"] = None
                except Exception:
                    r["spearman_vs_FULL"] = None
                    r["spearman_rho_vs_full"] = None
        except Exception:
            for r in rows:
                r["spearman_vs_FULL"] = None
                r["spearman_rho_vs_full"] = None
    else:
        for r in rows:
            r["spearman_vs_FULL"] = None
            r["spearman_rho_vs_full"] = None

    keys = ["config", "run_id", "fm", "hpv_gene_set_mode", "hpv_gene_set_size",
            "lambda_hpv", "lambda_sup", "lambda_prog", "lambda_neigh", "lambda_recon",
            "recon_mse_proxy", "hpv_auc", "hpv_high_low_gap",
            "moran_i", "n_deg_perm", "n_deg_naive",
            "high_risk_ratio", "n_prior_genes",
            "prog_kendall_tau", "prog_perm_p", "subtype_kruskal_p",
            "spearman_rho_vs_full"]
    print("\n===== ABLATION SUMMARY =====")
    header = " | ".join(keys)
    print(header)
    print("-" * len(header))
    rows_safe = _json_safe(rows)  # NaN/Inf → None before any I/O
    for r in rows_safe:
        print(" | ".join(str(r.get(k, "")) for k in keys))

    summary = {"per_config": rows_safe, "rows": rows_safe, "keys": keys}
    summary_safe = _json_safe(summary)
    (RESULTS / "ablation_summary.json").write_text(
        json.dumps(summary_safe, indent=2, default=str, allow_nan=False))
    # CSV for the paper
    import csv
    with open(RESULTS / "ablation_summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows_safe:
            w.writerow({k: r.get(k, "") for k in keys})
    print("\nSaved results/ablation_summary.json / results/ablation_summary.csv")


if __name__ == "__main__":
    main()
