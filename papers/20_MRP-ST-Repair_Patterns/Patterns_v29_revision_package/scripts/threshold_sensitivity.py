"""
threshold_sensitivity.py — QC 阈值敏感性分析（解决 "为什么是 0.80 不是 0.75" 质疑）

审稿人攻击点：
  "AUC≥0.80、Moran I≥0.70、Kendall τ≥0.20 是你自己定的，换一组阈值结论变不变？"

本脚本：
  从 results_FULL.json + 消融 JSON 里读 hpv_proxy_auc / moran_i /
  kendall_tau 等实际数值，在合理范围内扫阈值：
    AUC       : 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95
    Moran I   : 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80
    Kendall τ : 0.10, 0.15, 0.20, 0.25, 0.30, 0.35
  对每个阈值组合，统计 FULL vs 各消融 的 PASS/FAIL 状态。

  预期：在 AUC 0.75-0.90 / Moran 0.65-0.75 / Kendall 0.15-0.25 的
  合理区间内，结论稳定（只有 FULL 通过全部，消融各有 FAIL）。

Usage:
  python scripts/threshold_sensitivity.py \
      --full results/results_FULL.json \
      --ablations results/results_NO-NEIGH.json results/results_NO-HPV.json results/results_FM-UNI2.json \
      --out results/threshold_sensitivity.json
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def extract_metrics(res_json: dict) -> dict:
    """Extract the 5 key QC metrics from a results JSON (defensive)."""
    def _g(d, keys, default=None):
        for k in keys:
            if isinstance(d, dict) and k in d:
                return d[k]
        return default

    return {
        "hpv_proxy_auc": _g(res_json, ["hpv_proxy_auc", "auc", "roc_auc"]),
        "moran_i":       _g(res_json, ["moran_i", "morans_i", "spatial_autocorrelation"]),
        "kendall_tau":   _g(res_json, ["kendall_tau", "kendall", "progression_tau"]),
        "n_samples":     _g(res_json, ["n_samples", "n_slides", "samples_n"], default=35),
        "run_id":        _g(res_json, ["run_id", "model_name"], default="?"),
    }


def evaluate_pass(metrics: dict, thr_auc: float, thr_moran: float, thr_kendall: float) -> dict:
    """Return per-metric pass/fail + overall pass count."""
    checks = []
    if metrics["hpv_proxy_auc"] is not None:
        checks.append(("AUC", metrics["hpv_proxy_auc"] >= thr_auc, metrics["hpv_proxy_auc"], thr_auc))
    if metrics["moran_i"] is not None:
        checks.append(("Moran_I", metrics["moran_i"] >= thr_moran, metrics["moran_i"], thr_moran))
    if metrics["kendall_tau"] is not None:
        checks.append(("Kendall_tau", metrics["kendall_tau"] >= thr_kendall, metrics["kendall_tau"], thr_kendall))

    passed = sum(1 for c in checks if c[1])
    total = len(checks)
    return {
        "checks": [{"metric": c[0], "pass": c[1], "value": c[2], "threshold": c[3]} for c in checks],
        "passed": passed,
        "total": total,
        "all_pass": passed == total and total > 0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", required=True, help="results_FULL.json")
    ap.add_argument("--ablations", nargs="*", default=[], help="ablation JSONs")
    ap.add_argument("--out", default="results/threshold_sensitivity.json")
    args = ap.parse_args()

    # Load FULL
    full_data = json.loads(open(args.full).read())
    full_metrics = extract_metrics(full_data)
    print(f"[FULL] run_id={full_metrics['run_id']} AUC={full_metrics['hpv_proxy_auc']} "
          f"Moran={full_metrics['moran_i']} Kendall={full_metrics['kendall_tau']}")

    # Load ablations
    ablation_data = {}
    for ab_path in args.ablations:
        ab = json.loads(open(ab_path).read())
        m = extract_metrics(ab)
        ablation_data[ab_path] = {"metrics": m, "json": ab}
        print(f"  [{m['run_id']}] AUC={m['hpv_proxy_auc']} Moran={m['moran_i']} Kendall={m['kendall_tau']}")

    # Threshold grids
    auc_thrs = [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
    moran_thrs = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]
    kendall_thrs = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35]

    # 1) Single-threshold sweep: vary one at a time, fix others at recommended
    recommended = {"auc": 0.80, "moran": 0.70, "kendall": 0.20}

    sweep_results = {}

    for metric_name, thr_grid, fixed_key in [
        ("AUC", auc_thrs, ("moran", "kendall")),
        ("Moran_I", moran_thrs, ("auc", "kendall")),
        ("Kendall_tau", kendall_thrs, ("auc", "moran")),
    ]:
        sweep = []
        for thr in thr_grid:
            f_m = recommended["moran" if "moran" in fixed_key else "auc" if "auc" in fixed_key else "kendall"]
            f_k = recommended["kendall" if "kendall" in fixed_key else "auc" if "auc" in fixed_key else "moran"]
            if metric_name == "AUC":
                res = evaluate_pass(full_metrics, thr, recommended["moran"], recommended["kendall"])
            elif metric_name == "Moran_I":
                res = evaluate_pass(full_metrics, recommended["auc"], thr, recommended["kendall"])
            else:
                res = evaluate_pass(full_metrics, recommended["auc"], recommended["moran"], thr)

            # Also check ablations
            ab_status = {}
            for ab_path, ab in ablation_data.items():
                if metric_name == "AUC":
                    ab_res = evaluate_pass(ab["metrics"], thr, recommended["moran"], recommended["kendall"])
                elif metric_name == "Moran_I":
                    ab_res = evaluate_pass(ab["metrics"], recommended["auc"], thr, recommended["kendall"])
                else:
                    ab_res = evaluate_pass(ab["metrics"], recommended["auc"], recommended["moran"], thr)
                ab_status[ab["metrics"]["run_id"]] = {"all_pass": ab_res["all_pass"], "passed": ab_res["passed"], "total": ab_res["total"]}

            sweep.append({"threshold": thr, "FULL_all_pass": res["all_pass"],
                          "FULL_passed": res["passed"], "FULL_total": res["total"],
                          "ablations": ab_status})
        sweep_results[metric_name] = sweep

        # Print
        print(f"\n--- Varying {metric_name} threshold (fix others at recommended) ---")
        for s in sweep:
            ab_str = "  ".join(f"{n}={'PASS' if v['all_pass'] else 'FAIL'}" for n,v in s["ablations"].items())
            print(f"  thr={s['threshold']:.2f}: FULL={'PASS' if s['FULL_all_pass'] else 'FAIL'}  {ab_str}")

    # 2) "Whole range PASS/FAIL matrix" — does the recommended combination uniquely pass FULL only?
    recom_check = evaluate_pass(full_metrics, recommended["auc"], recommended["moran"], recommended["kendall"])
    print(f"\n=== RECOMMENDED THRESHOLDS (AUC≥{recommended['auc']}, Moran≥{recommended['moran']}, Kendall≥{recommended['kendall']}) ===")
    print(f"  FULL: {recom_check['passed']}/{recom_check['total']} checks passed {'✅ ALL PASS' if recom_check['all_pass'] else '❌'}")
    for ab_path, ab in ablation_data.items():
        r = evaluate_pass(ab["metrics"], recommended["auc"], recommended["moran"], recommended["kendall"])
        print(f"  {ab['metrics']['run_id']}: {r['passed']}/{r['total']} {'✅ ALL PASS' if r['all_pass'] else '❌ FAIL'}")

    out = {
        "generated": pd.Timestamp.now().isoformat(),
        "recommended_thresholds": recommended,
        "full_metrics": full_metrics,
        "ablation_metrics": {p: a["metrics"] for p, a in ablation_data.items()},
        "single_metric_sweeps": sweep_results,
        "recommended_threshold_eval": {
            "FULL": {"checks": recom_check["checks"], "all_pass": recom_check["all_pass"]},
            "ablations": {a["metrics"]["run_id"]: {"checks": evaluate_pass(a["metrics"], recommended["auc"], recommended["moran"], recommended["kendall"])["checks"],
                                                   "all_pass": evaluate_pass(a["metrics"], recommended["auc"], recommended["moran"], recommended["kendall"])["all_pass"]}
                          for a in ablation_data.values()},
        },
        "interpretation": ("Stability criterion: FULL should PASS all checks at recommended thresholds, "
                          "and at least one ablation should FAIL at the same thresholds. "
                          "If this holds across a reasonable range, the threshold choice is not cherry-picked."),
    }

    out_path = Path(args.out); out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()
