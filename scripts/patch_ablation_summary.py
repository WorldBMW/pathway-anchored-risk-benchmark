"""Backfill missing 二区-critical columns into ablation_summary.json/.csv without
re-running the 7 ablation trainings. Uses the already-generated results_*.json
files, consistent with ablation_study.py v2 row format.

Also:
  - ensures FULL has spearman_rho_vs_full=1.0
  - recomputes HPV-ROBUST-A/B Spearman rho vs FULL using per-sample scores
  - rewrites CSV header/rows to match new 22-column schema

Safe: only modifies results/ablation_summary.json and ablation_summary.csv
(idempotent; re-running yields identical output).
"""

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
AB_JSON = RESULTS / "ablation_summary.json"
AB_CSV = RESULTS / "ablation_summary.csv"

NEW_KEYS = [
    "config", "run_id", "fm", "hpv_gene_set_mode", "hpv_gene_set_size",
    "lambda_hpv", "lambda_sup", "lambda_prog", "lambda_neigh", "lambda_recon",
    "recon_mse_proxy", "hpv_auc", "hpv_high_low_gap",
    "moran_i", "n_deg_perm", "n_deg_naive",
    "high_risk_ratio", "n_prior_genes",
    "prog_kendall_tau", "prog_perm_p", "subtype_kruskal_p",
    "spearman_rho_vs_full",
]


def _json_safe(v):
    """NaN / Inf -> None; numpy scalars -> native Python.

    Prevents the exact Aug-2026 crash that motivated ablation_recover_summary:
    allow_nan=False will otherwise raise ValueError on any NaN float.
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

# --- (1) load existing rows, keep original order of configs ---
rows = json.loads(AB_JSON.read_text())["rows"]
# If rows is a dict in older version normalise to list
if isinstance(rows, dict):
    rows = list(rows.values())

# --- (2) for each row, backfill fields from its results_<run_id>.json ---
def backfill(r):
    cfg = r.get("config")
    rid = r.get("run_id")
    jpath = RESULTS / f"results_{rid}.json"
    if not jpath.exists():
        # fallback: results_<config>.json (sometimes run_id == config)
        jpath = RESULTS / f"results_{cfg}.json"
    if jpath.exists():
        d = json.loads(jpath.read_text())
        ha = d.get("histology_association") or {}
        prog = d.get("progression_monotonicity") or {}
        # Round scalars consistent with ablation_study.py precision
        getf = lambda k, p=4: (lambda v: round(float(v), p) if v is not None else None)(d.get(k))
        new = {
            "config": cfg,
            "run_id": rid,
            "fm": d.get("fm"),
            "hpv_gene_set_mode": d.get("hpv_gene_set_mode"),
            "hpv_gene_set_size": d.get("hpv_gene_set_size"),
            "lambda_hpv": d.get("lambda_hpv"),
            "lambda_neigh": d.get("lambda_neigh"),
            "lambda_recon": d.get("lambda_recon"),
            "lambda_sup": d.get("lambda_sup"),
            "lambda_prog": d.get("lambda_prog"),
            "recon_mse_proxy": getf("recon_mse_proxy"),
            "hpv_auc": getf("hpv_proxy_auc"),
            "hpv_high_low_gap": getf("hpv_gene_high_low_gap"),
            "moran_i": getf("moran_i"),
            "n_deg_perm": d.get("n_deg_perm_fdr05_effect"),
            "n_deg_naive": d.get("n_deg_naive_fdr05_effect"),
            "high_risk_ratio": getf("high_risk_ratio"),
            "n_prior_genes": d.get("n_prior_genes"),
            "prog_kendall_tau": (lambda v: round(float(v), 4) if v is not None else None)(prog.get("kendall_tau")),
            "prog_perm_p": prog.get("permutation_p"),
            "subtype_kruskal_p": ha.get("subtype_kruskal_p"),
        }
        # preserve any explicit human-entered fields we didn't override
        merged = dict(r)
        merged.update({k: v for k, v in new.items() if v is not None or k not in merged})
        return merged
    return dict(r)

rows = [backfill(r) for r in rows]

# --- (3) recompute Spearman rho vs FULL per-sample scores ---
full_scores = None
for r in rows:
    if r.get("config") == "FULL":
        p = RESULTS / f"results_{r.get('run_id')}.json"
        if not p.exists():
            p = RESULTS / "results_FULL.json"
        if p.exists():
            full_scores = json.loads(p.read_text()).get("per_sample_score", {})
        break

if full_scores:
    from scipy.stats import spearmanr
    for r in rows:
        if r.get("config") == "FULL":
            r["spearman_rho_vs_full"] = 1.0
            r["spearman_vs_FULL"] = 1.0
            continue
        p = RESULTS / f"results_{r.get('run_id')}.json"
        if not p.exists():
            p = RESULTS / f"results_{r.get('config')}.json"
        if not p.exists():
            r["spearman_rho_vs_full"] = None
            continue
        cur = json.loads(p.read_text()).get("per_sample_score", {})
        common = sorted(set(full_scores.keys()) & set(cur.keys()))
        if len(common) >= 3:
            x = [full_scores[k] for k in common]
            y = [cur[k] for k in common]
            rho, _ = spearmanr(x, y)
            r["spearman_rho_vs_full"] = round(float(rho), 4)
        else:
            r["spearman_rho_vs_full"] = None
else:
    for r in rows:
        r["spearman_rho_vs_full"] = None

# --- (4) clean: keep exactly NEW_KEYS per row for CSV; keep extras in JSON ---
summary = {"per_config": rows, "rows": rows, "keys": NEW_KEYS}
summary_safe = _json_safe(summary)
AB_JSON.write_text(json.dumps(summary_safe, indent=2, default=str, allow_nan=False))
print(f"Wrote {AB_JSON} (rows={len(rows)})")

with open(AB_CSV, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=NEW_KEYS)
    w.writeheader()
    for r in summary_safe["rows"]:
        w.writerow({k: r.get(k, "") for k in NEW_KEYS})
print(f"Wrote {AB_CSV}")

# --- (5) print 二区 ablation snapshot ---
print("\n=== 二区 ablation summary snapshot ===")
for r in rows:
    c = r.get("config")
    auc = r.get("hpv_auc")
    rho = r.get("spearman_rho_vs_full")
    kw = r.get("subtype_kruskal_p")
    moran = r.get("moran_i")
    ndeg = r.get("n_deg_perm")
    print(f"{c:18s} hpv_auc={auc}  moran={moran}  n_deg_perm={ndeg}  subtype_kw_p={kw}  spearman_vs_FULL={rho}")
