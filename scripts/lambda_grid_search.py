"""Loss-weight grid search for the ST-H&E fusion model.

Responds to reviewer concern: the 5 loss weights (lambda_hpv/sup/prog/recon/neigh)
were manually fixed without grid search or uncertainty-based weighting.

We do a SMALL, defensible grid over the two most biologically meaningful weights
(lambda_hpv and lambda_neigh), holding the other three at the default values.
Full 5-D grid is computationally prohibitive (5^5 = 3125 runs); a 2-D grid with
3 levels each = 9 runs is feasible on a single GPU and directly addresses
"did you tune the two weights that the ablation claims are core contributors?".

Grid (lambda_hpv x lambda_neigh):
  (0.5, 0.1), (0.5, 0.3), (0.5, 1.0),
  (1.0, 0.1), (1.0, 0.3), (1.0, 1.0),  # <-- includes default (1.0, 0.3)
  (2.0, 0.1), (2.0, 0.3), (2.0, 1.0)

Output: results/lambda_grid_summary.json with {config, lambda_hpv, lambda_neigh,
moran_i, hpv_auc, kendall_tau, n_deg_perm} per run + a markdown table.
"""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = ROOT / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

# 2-D grid over the two core-contributor weights (ablation-validated).
GRID = [
    (0.5, 0.1), (0.5, 0.3), (0.5, 1.0),
    (1.0, 0.1), (1.0, 0.3), (1.0, 1.0),
    (2.0, 0.1), (2.0, 0.3), (2.0, 1.0),
]

# Fixed defaults for the other three weights.
LAMBDA_SUP = 2.0
LAMBDA_PROG = 1.0
LAMBDA_RECON = 1.0


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/st_visium")
    ap.add_argument("--histology_label_csv",
                    default="data/st_visium/labels/cervix_histology_labels_extended.csv")
    ap.add_argument("--exclude_substr", default="breast,ovarian,prostate,visium_hd,zenodo,cervix_all")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--fm", default="uni")
    ap.add_argument("--hpv_gene_set", default="kegg_hpv")
    ap.add_argument("--fm_cache", action="store_true")
    ap.add_argument("--permutation_n", type=int, default=1000)
    args = ap.parse_args()

    rows = []
    for lhpv, lneigh in GRID:
        run_id = f"LAMBDA_hpv{lhpv}_neigh{lneigh}"
        out_json = RESULTS / f"results_{run_id}.json"
        if out_json.exists():
            out_json.unlink()
        cmd = [
            sys.executable, str(HERE / "train_st.py"),
            "--data", args.data,
            "--device", args.device,
            "--epochs", str(args.epochs),
            "--fm", args.fm,
            "--hpv_gene_set", args.hpv_gene_set,
            "--histology_label_csv", args.histology_label_csv,
            "--exclude_substr", args.exclude_substr,
            "--permutation_n", str(args.permutation_n),
            "--lambda_hpv", str(lhpv),
            "--lambda_neigh", str(lneigh),
            "--lambda_sup", str(LAMBDA_SUP),
            "--lambda_prog", str(LAMBDA_PROG),
            "--lambda_recon", str(LAMBDA_RECON),
            "--run_id", run_id,
        ]
        if args.fm_cache:
            cmd.append("--fm_cache")
        print(f"===== LAMBDA GRID: lambda_hpv={lhpv}, lambda_neigh={lneigh} =====")
        rc = subprocess.call(cmd)
        if rc != 0:
            print(f"[warn] run {run_id} exited with code {rc}; skipping")
            rows.append({
                "run_id": run_id, "lambda_hpv": lhpv, "lambda_neigh": lneigh,
                "error": f"exit_code_{rc}",
            })
            continue
        try:
            d = json.load(open(out_json))
            pm = d.get("progression_monotonicity", {}) or {}
            rows.append({
                "run_id": run_id,
                "lambda_hpv": lhpv,
                "lambda_neigh": lneigh,
                "hpv_auc": d.get("hpv_proxy_auc"),
                "moran_i": d.get("moran_i"),
                "kendall_tau": pm.get("kendall_tau"),
                "n_deg_perm": d.get("n_deg_perm_fdr05_effect"),
            })
        except Exception as e:
            print(f"[warn] failed to parse {out_json}: {e}")
            rows.append({"run_id": run_id, "lambda_hpv": lhpv,
                         "lambda_neigh": lneigh, "error": str(e)})

    # Save summary.
    summary = {"grid": [list(g) for g in GRID], "fixed": {
        "lambda_sup": LAMBDA_SUP, "lambda_prog": LAMBDA_PROG,
        "lambda_recon": LAMBDA_RECON, "hpv_gene_set": args.hpv_gene_set,
    }, "runs": rows}
    out = RESULTS / "lambda_grid_summary.json"
    json.dump(summary, open(out, "w"), indent=2)
    print(f"\nSaved -> {out}")

    # Markdown table.
    print("\n| lambda_hpv | lambda_neigh | hpv_auc | moran_i | kendall_tau | n_deg |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        if "error" in r:
            print(f"| {r['lambda_hpv']} | {r['lambda_neigh']} | ERROR | ERROR | ERROR | ERROR |")
        else:
            print(f"| {r['lambda_hpv']} | {r['lambda_neigh']} | "
                  f"{r['hpv_auc']:.4f} | {r['moran_i']:.4f} | "
                  f"{r['kendall_tau']} | {r['n_deg_perm']} |")


if __name__ == "__main__":
    main()
