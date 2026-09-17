"""Aggregate random gene-set controls and compute permutation p-values.

Collects all results_RANDOM108_S*.json plus results_MAIN_KEGG.json (KEGG 108-gene
panel) and tests whether KEGG's Moran's I is significantly higher than the
random-gene null distribution.

Permutation p-value: fraction of random runs whose Moran's I >= KEGG's Moran's I.
  p = (count(random_moran >= kegg_moran) + 1) / (n_random + 1)
(the +1 / +1 is the conservative Phipson-Smyth correction for finite permutations).

Also reports hpv_proxy AUC null distribution (expected: KEGG not significantly
higher than random, confirming the label-controllability finding).

Output: results/random_control_summary.json + markdown table.
"""
from __future__ import annotations
import json
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"


def main():
    kegg_json = RESULTS / "results_MAIN_KEGG.json"
    if not kegg_json.exists():
        raise SystemExit(f"[error] {kegg_json} not found; run MAIN_KEGG first")

    kegg = json.load(open(kegg_json))
    kegg_moran = float(kegg.get("moran_i", float("nan")))
    kegg_auc = float(kegg.get("hpv_proxy_auc", float("nan")))
    pm = kegg.get("progression_monotonicity", {}) or {}
    kegg_tau = pm.get("kendall_tau")

    random_files = sorted(glob.glob(str(RESULTS / "results_RANDOM108_S*.json")))
    if not random_files:
        raise SystemExit("[error] no results_RANDOM108_S*.json found")

    rand_morans, rand_aucs, rand_taus = [], [], []
    for f in random_files:
        d = json.load(open(f))
        rand_morans.append(float(d.get("moran_i", float("nan"))))
        rand_aucs.append(float(d.get("hpv_proxy_auc", float("nan"))))
        rpm = d.get("progression_monotonicity", {}) or {}
        rand_taus.append(rpm.get("kendall_tau"))

    import statistics
    n = len(rand_morans)

    # Permutation p-value (Phipson-Smyth conservative):
    # p = (#random >= observed + 1) / (n + 1)
    moran_ge = sum(1 for m in rand_morans if m >= kegg_moran)
    p_moran = (moran_ge + 1) / (n + 1)
    auc_ge = sum(1 for a in rand_aucs if a >= kegg_auc)
    p_auc = (auc_ge + 1) / (n + 1)

    summary = {
        "kegg": {"moran_i": kegg_moran, "hpv_auc": kegg_auc, "kendall_tau": kegg_tau},
        "random": {
            "n": n,
            "moran_i": {"mean": statistics.mean(rand_morans),
                        "std": statistics.pstdev(rand_morans),
                        "min": min(rand_morans), "max": max(rand_morans)},
            "hpv_auc": {"mean": statistics.mean(rand_aucs),
                        "std": statistics.pstdev(rand_aucs),
                        "min": min(rand_aucs), "max": max(rand_aucs)},
            "kendall_tau_mean": statistics.mean(t for t in rand_taus if t is not None),
        },
        "permutation_test": {
            "moran_i": {
                "n_random_ge_kegg": moran_ge,
                "p_value": p_moran,
                "interpretation": ("KEGG Moran's I significantly higher than random (p<0.05)"
                                   if p_moran < 0.05 else
                                   "KEGG Moran's I NOT significantly higher than random"),
            },
            "hpv_auc": {
                "n_random_ge_kegg": auc_ge,
                "p_value": p_auc,
                "interpretation": ("KEGG AUC significantly higher than random"
                                   if p_auc < 0.05 else
                                   "KEGG AUC NOT significantly higher than random (confirms label-controllability)"),
            },
        },
        "random_runs": [{"file": Path(f).name,
                          "moran_i": rand_morans[i],
                          "hpv_auc": rand_aucs[i]}
                         for i, f in enumerate(random_files)],
    }

    out = RESULTS / "random_control_summary.json"
    json.dump(summary, open(out, "w"), indent=2)
    print(f"Saved -> {out}")

    print(f"\nKEGG    : moran_i={kegg_moran:.4f}  hpv_auc={kegg_auc:.4f}")
    print(f"RANDOM(n={n}): moran_i={statistics.mean(rand_morans):.4f}±{statistics.pstdev(rand_morans):.4f}  "
          f"hpv_auc={statistics.mean(rand_aucs):.4f}±{statistics.pstdev(rand_aucs):.4f}")
    print(f"Permutation p (Moran's I): {p_moran:.4f}  -> {summary['permutation_test']['moran_i']['interpretation']}")
    print(f"Permutation p (hpv_auc) : {p_auc:.4f}  -> {summary['permutation_test']['hpv_auc']['interpretation']}")


if __name__ == "__main__":
    main()
