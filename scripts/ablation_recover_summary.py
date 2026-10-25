"""Recover ablation_summary.json / .csv DIRECTLY from per-run results_*.json
files, without re-running the multi-hour ablation training subprocesses.

Why this exists (Aug-2026 crash):
    ablation_study.py sometimes writes rows with `float('nan')` in fields like
    hpv_auc / moran_i / prog_kendall_tau, then at the very end calls
    json.dumps(..., allow_nan=False)  →  ValueError: nan not JSON compliant.
    Each individual ablation *subprocess* (train_st.py) has ALREADY saved its
    full results as results_<run_id>.json BEFORE the aggregator tries to
    summarize.  So we can always rebuild a clean summary by re-reading those
    per-run JSONs.

This script:
  1. Discovers 7 standard ablation configs (FULL, NO-HPV, NO-NEIGH,
     HPV-ROBUST-A/B, FM-UNI2, BASELINE-CNN).  If any config is missing, still
     writes a partial summary (missing rows show SKIP + exact train_st.py
     one-liner the user should run next so they don't re-run FULL etc.).
  2. Rebuilds the full 22-column row schema matching ablation_study.py v2.
  3. Runs a global _json_safe pass: NaN / -inf / inf → None, numpy scalars →
     native Python, so json.dumps(..., allow_nan=False) is guaranteed.
  4. Recomputes Spearman rho vs FULL using per_sample_score dicts.
  5. Writes results/ablation_summary.json and ablation_summary.csv
     (overwrites, idempotent).
  6. Prints NEED_RUNS at the end: exact run_ids that are MISSING + the
     corresponding train_st.py command, so the user only re-runs those.

Usage (4090 bash):
    python scripts/ablation_recover_summary.py
    # → prints which rows were recovered / skipped / NEED_RUNS list with
    #    per-rid single-run train_st.py commands.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
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

# Standard ablation configs used for ABL_CERVIX35 (Step 12b).
# Order: primary paper Figure 4 runs first, then supplementary runs.
STANDARD_CONFIGS: list[dict] = [
    dict(config="FULL",         run_id="FULL",         extra_cli=[]),
    dict(config="NO-HPV",       run_id="NO-HPV",       extra_cli=["--lambda_hpv",      "0.0"]),
    dict(config="NO-NEIGH",     run_id="NO-NEIGH",     extra_cli=["--lambda_neigh",    "0.0"]),
    dict(config="HPV-ROBUST-A", run_id="HPV-ROBUST-A", extra_cli=["--hpv_gene_set_mode","dropout_20pct"]),
    dict(config="HPV-ROBUST-B", run_id="HPV-ROBUST-B", extra_cli=["--hpv_gene_set_mode","kegg_hpv"]),
    dict(config="FM-UNI2",      run_id="FM-UNI2",      extra_cli=["--fm",              "uni2"]),
    dict(config="BASELINE-CNN", run_id="BASELINE-CNN", extra_cli=["--model_type",      "cnn"]),
]


# ---------- JSON sanitization (NaN -> None + numpy -> native) ----------------
def _json_safe(v):
    """Recursively coerce any value into a JSON-safe, NaN-free Python value."""
    if v is None:
        return None
    # bool is a subclass of int; check first
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, str)):
        return v
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    # numpy scalars (int32/float32/bool_)
    try:
        import numpy as np  # type: ignore
        if isinstance(v, np.generic):
            vv = v.item()
            return _json_safe(vv)
    except Exception:
        pass
    if isinstance(v, dict):
        return {str(k): _json_safe(vv) for k, vv in v.items()}
    if isinstance(v, (list, tuple)):
        return [_json_safe(x) for x in v]
    # last fallback: str (matches original default=str behaviour)
    return str(v)


def _rndf(x, p=4):
    """Round a float-like to p decimals; NaN/Inf -> None."""
    if x is None:
        return None
    try:
        f = float(x)
    except Exception:
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, p)


# ---------- Main recovery ----------------------------------------------------
def main() -> int:
    rows: list[dict] = []
    missing: list[dict] = []

    for cfg in STANDARD_CONFIGS:
        cfg_id = cfg["config"]
        run_id = cfg["run_id"]
        # Prefer results_<run_id>.json; fall back to results_<config>.json for
        # old runs where run_id == config.
        jpath = RESULTS / f"results_{run_id}.json"
        if not jpath.exists():
            jpath = RESULTS / f"results_{cfg_id}.json"
        if not jpath.exists():
            print(f"[SKIP   ] {cfg_id:14s} (run_id={run_id}) -> no results json")
            missing.append(cfg)
            continue
        try:
            d = json.loads(jpath.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[SKIP   ] {cfg_id:14s} -> bad json {jpath.name}: {type(e).__name__}: {e}")
            missing.append(cfg)
            continue
        # -- diagnose per-run basic integrity ----------------------------------
        n_samples = d.get("n_samples")
        subtypes = d.get("subtypes") or []
        ha = d.get("histology_association") or {}
        prog = d.get("progression_monotonicity") or {}
        row = {
            "config": cfg_id,
            "run_id": run_id,
            "fm": d.get("fm"),
            "hpv_gene_set_mode": d.get("hpv_gene_set_mode"),
            "hpv_gene_set_size": d.get("hpv_gene_set_size"),
            "lambda_hpv": d.get("lambda_hpv"),
            "lambda_neigh": d.get("lambda_neigh"),
            "lambda_recon": d.get("lambda_recon"),
            "lambda_sup": d.get("lambda_sup"),
            "lambda_prog": d.get("lambda_prog"),
            "recon_mse_proxy": _rndf(d.get("recon_mse_proxy")),
            "hpv_auc": _rndf(d.get("hpv_proxy_auc")),
            "hpv_high_low_gap": _rndf(d.get("hpv_gene_high_low_gap")),
            "moran_i": _rndf(d.get("moran_i")),
            "n_deg_perm": d.get("n_deg_perm_fdr05_effect"),
            "n_deg_naive": d.get("n_deg_naive_fdr05_effect"),
            "high_risk_ratio": _rndf(d.get("high_risk_ratio")),
            "n_prior_genes": d.get("n_prior_genes"),
            "prog_kendall_tau": _rndf(prog.get("kendall_tau")),
            "prog_perm_p": prog.get("permutation_p"),
            "subtype_kruskal_p": ha.get("subtype_kruskal_p"),
        }
        # Sanity-diagnostic tag line printed per row (user needs to know n_samples)
        diag = f"n_samples={n_samples} subtypes={len(subtypes)}"
        if row["hpv_auc"] is not None:
            diag += f" hpv_auc={row['hpv_auc']}"
        if row["n_deg_perm"] is not None:
            diag += f" n_deg_perm={row['n_deg_perm']}"
        print(f"[RECOVER] {cfg_id:14s} rid={run_id:14s} {diag}")
        rows.append(row)

    # --- Recompute Spearman rho vs FULL per-sample scores -------------------
    full_scores = None
    for r in rows:
        if r.get("config") == "FULL":
            p = RESULTS / f"results_{r.get('run_id')}.json"
            if not p.exists():
                p = RESULTS / "results_FULL.json"
            if p.exists():
                try:
                    full_scores = json.loads(p.read_text()).get("per_sample_score", {}) or {}
                except Exception:
                    full_scores = {}
            break
    if full_scores:
        try:
            from scipy.stats import spearmanr  # type: ignore
        except Exception:
            spearmanr = None  # type: ignore
        for r in rows:
            if r.get("config") == "FULL":
                r["spearman_rho_vs_full"] = 1.0
                continue
            p = RESULTS / f"results_{r.get('run_id')}.json"
            if not p.exists():
                p = RESULTS / f"results_{r.get('config')}.json"
            if not p.exists():
                r["spearman_rho_vs_full"] = None
                continue
            try:
                cur = json.loads(p.read_text()).get("per_sample_score", {}) or {}
            except Exception:
                r["spearman_rho_vs_full"] = None
                continue
            common = sorted(set(full_scores.keys()) & set(cur.keys()))
            if spearmanr is not None and len(common) >= 3:
                x = [full_scores[k] for k in common]
                y = [cur[k] for k in common]
                rho, _ = spearmanr(x, y)
                r["spearman_rho_vs_full"] = _rndf(rho)
            else:
                r["spearman_rho_vs_full"] = None
    else:
        for r in rows:
            r["spearman_rho_vs_full"] = None if r.get("config") != "FULL" else 1.0

    # --- Global sanitize + write --------------------------------------------
    rows_safe = _json_safe(rows)
    summary = {"per_config": rows_safe, "rows": rows_safe, "keys": NEW_KEYS}
    summary = _json_safe(summary)

    AB_JSON.write_text(
        json.dumps(summary, indent=2, default=str, allow_nan=False),
        encoding="utf-8",
    )
    with open(AB_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=NEW_KEYS)
        w.writeheader()
        for r in rows_safe:
            w.writerow({k: r.get(k, "") for k in NEW_KEYS})
    print(f"\n[WROTE] {AB_JSON} (rows={len(rows_safe)})")
    print(f"[WROTE] {AB_CSV}")

    # --- NEED_RUNS: exact commands (don't re-run FULL/NO-HPV if done) ------
    if missing:
        print("\n==== NEED_RUNS (MISSING ablation rows; run these individually) ====")
        for m in missing:
            rid = m["run_id"]
            base_cmd = (
                f"python scripts/train_st.py "
                f"--data data/st_visium/cervix_all_ext --device cuda "
                f"--epochs 30 --bs 256 --lr 1e-3 --n_genes 2000 "
                f"--histology_label_csv data/st_visium/labels/cervix_histology_labels_extended.csv "
                f"--run_id {rid}"
            )
            extra = " ".join(m.get("extra_cli", []))
            if extra:
                base_cmd += f" {extra}"
            logn = f"logs/step12b_{rid.lower().replace('-','_')}.log"
            base_cmd += f" 2>&1 | tee {logn}"
            print(base_cmd)
        print(f"\n# Missing {len(missing)} / {len(STANDARD_CONFIGS)} ablation runs. "
              f"Run above one-liners, then re-run: python scripts/ablation_recover_summary.py")
    else:
        print("\n==== ALL 7 standard ablation runs recovered; no NEED_RUNS ====")

    # --- snapshot -----------------------------------------------------------
    print("\n=== 二区 ablation summary snapshot ===")
    for r in rows_safe:
        c = r.get("config")
        auc = r.get("hpv_auc")
        rho = r.get("spearman_rho_vs_full")
        kw = r.get("subtype_kruskal_p")
        moran = r.get("moran_i")
        ndeg = r.get("n_deg_perm")
        print(f"{c:18s} hpv_auc={auc}  moran={moran}  n_deg_perm={ndeg}  subtype_kw_p={kw}  spearman_vs_FULL={rho}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
