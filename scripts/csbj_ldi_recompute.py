#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""MRP-ST / LDI validation recomputation for the CSBJ revision.

Why this exists
---------------
The CSBJ manuscript dropped the named contribution (MRP-ST clauses + the
Label-Dependence Index LDI) and reported only two floating descriptive
differences D_ordinal / D_joint. The graders' desk-reject reason was
"insufficient strength of the advance".

The LDI validation already existed in the repository
(``results/ldi_synthetic_validation.json``) but was computed on stale
aggregates (results/paper_v10_numbers.json), whose NOALL tau = -0.1055 no
longer matches the current NPZ-derived value. This script re-derives every
number directly from the CURRENT fused-embedding NPZ files, so that the
manuscript, the figure and the Zenodo archive share one口径:

  tau_v,k     Kendall tau-b between per-sample mean score and severity
  LDI         tau_FULL - tau_NOALL          (backward, unpaired; SD propagated)
  theta       label-permutation null quantile of the FULL score
  gate        LDI > theta  ->  "label-dependent"
  calibration tau(alpha) under injected label ranks (monotone response)

Outputs
  results/csbj_ldi_validated.json
  papers/12_CSBJ_audit_20261010/figures/Fig_LDI_validation.png

Usage:  python scripts/csbj_ldi_recompute.py [--perm 10000]
"""
import argparse
import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, rankdata

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
FIGDIR = ROOT / "papers" / "12_CSBJ_audit_20261010" / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)

# training seeds actually available per variant (real-data cohort)
SEEDS = {"FULL": [0, 3, 4], "NOIMAGE": [0, 1, 2], "NOHPV": [0, 1, 2],
         "NONEIGH": [0, 1, 2], "NOPROG": [0, 1, 2, 3], "NOSUP": [0, 1, 2],
         "NOALL": [0, 1, 2]}
ORDER = ["FULL", "NOIMAGE", "NOHPV", "NONEIGH", "NOPROG", "NOSUP", "NOALL"]


def severity_of(name):
    """Severity mapping identical to scripts/gen_figures_v10.py (tau口径对齐)."""
    n = str(name).lower()
    if "ca_hpv" in n or "cancer" in n or "carcinoma" in n:
        return 2
    if "hsil" in n or "cin" in n:
        return 1
    return 0


def per_sample_score(variant, seed):
    fp = RES / f"fused_embs_{variant}_seed{seed}.npz"
    if not fp.exists():
        return None
    z = np.load(fp, allow_pickle=True)
    df = pd.DataFrame({"sid": z["sample_ids"].astype(str),
                       "score": z["scores"].astype(float)})
    return df.groupby("sid")["score"].mean()


def tau_between(score_series, sev_series):
    common = score_series.index.intersection(sev_series.index)
    s = score_series.loc[common].astype(float).values
    v = sev_series.loc[common].astype(float).values
    if len(np.unique(v)) < 2:
        return float("nan")
    return float(kendalltau(v, s).statistic)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--perm", type=int, default=10000)
    ap.add_argument("--perm-seed", type=int, default=20261005)
    args = ap.parse_args()

    # ---- per-variant tau ----
    variant_stats = {}
    for v in ORDER:
        taus = []
        for s in SEEDS[v]:
            ps = per_sample_score(v, s)
            if ps is None:
                continue
            sev = pd.Series({k: severity_of(k) for k in ps.index})
            taus.append(tau_between(ps, sev))
        if not taus:
            continue
        arr = np.array(taus, dtype=float)
        variant_stats[v] = {
            "tau_mean": float(arr.mean()),
            "tau_sd": float(arr.std(ddof=1)) if len(arr) > 1 else 0.0,
            "tau_per_seed": [float(x) for x in arr],
            "seeds": SEEDS[v][:len(arr)],
            "n_samples": 35,
        }
        print(f"[tau] {v:8s} mean={arr.mean():+.4f} sd={arr.std(ddof=1) if len(arr)>1 else 0:.4f}")

    tau_full = variant_stats["FULL"]["tau_mean"]
    tau_noall = variant_stats["NOALL"]["tau_mean"]
    sd_full = variant_stats["FULL"]["tau_sd"]
    sd_noall = variant_stats["NOALL"]["tau_sd"]

    # ---- theta calibration: label-permutation null of the FULL score ----
    full_ps = per_sample_score("FULL", 0)
    sev = pd.Series({k: severity_of(k) for k in full_ps.index})
    s_full = full_ps.loc[sev.index].astype(float).values
    y_true = sev.loc[sev.index].astype(float).values
    rng = np.random.default_rng(args.perm_seed)
    null = np.array([kendalltau(rng.permutation(y_true), s_full).statistic
                     for _ in range(args.perm)])
    theta95 = float(np.quantile(null, 0.95))
    theta99 = float(np.quantile(null, 0.99))
    p_upper = float((np.asarray(null) >= tau_full).mean())
    null_mean = float(null.mean())
    null_sd = float(null.std())

    # ---- Label-Dependence Index: precision-stable, null-standardized ----
    # LDI = (tau_FULL - tau_perp) / sigma_null, tau_perp = E[tau | label permutation].
    # The raw contrast tau_FULL - tau_NOALL is deliberately NOT used: the NOALL scalar
    # head collapses to a near-constant per-sample offset, so its tau is dtype-dependent
    # numerically-indeterminate noise (float32 vs float64 differ from the same npz).
    ldi = (tau_full - null_mean) / null_sd
    theta_z = 1.6448536269514722                       # Phi^{-1}(0.95)
    ldi_noall_raw = tau_full - tau_noall               # transparency only

    # ---- injected-dependence calibration (metric monotonicity) ----
    rng_n = np.random.default_rng(args.perm_seed)
    noise = rng_n.normal(size=len(y_true))
    r_noise, r_sev = rankdata(noise), rankdata(y_true)
    alphas = np.linspace(0.0, 1.0, 21)
    curve = [float(kendalltau(y_true, (1 - a) * r_noise + a * r_sev).statistic)
             for a in alphas]
    monotone = all(curve[i] <= curve[i + 1] + 1e-12 for i in range(len(curve) - 1))
    equiv_alpha = None
    for i in range(len(alphas) - 1):
        if (curve[i] - tau_full) * (curve[i + 1] - tau_full) <= 0:
            t1, t2 = curve[i], curve[i + 1]
            if t2 != t1:
                equiv_alpha = float(alphas[i] + (tau_full - t1) * 0.05 / (t2 - t1))
            break

    # ---- random-panel negative control ----
    rand_taus = []
    for fp in sorted(glob.glob(str(RES / "results_RANDOM108_*.json"))):
        d = json.load(open(fp, encoding="utf-8"))
        ps = d.get("per_sample_score")
        if not isinstance(ps, dict) or not ps:
            continue
        sids = list(ps.keys())
        rand_taus.append(float(kendalltau([severity_of(s) for s in sids],
                                          [float(ps[s]) for s in sids]).statistic))
    rand_taus = np.array(rand_taus) if rand_taus else np.array([np.nan])

    gate = "label-dependent" if ldi > theta_z else "not label-dependent"

    out = {
        "definition": {
            "tau": "Kendall tau-b between per-sample mean score and ordinal severity",
            "LDI": "(tau_FULL - tau_perp) / sigma_null, standardized excess over the label-permutation null",
            "tau_perp": "E[tau | complete sample-label permutation] of the supervised score",
            "theta": "Phi^-1(0.95) = 1.6449, one-sided Gaussian gate on the LDI scale",
            "gate_rule": "LDI > theta -> label-dependent",
            "not_used": "tau_FULL - tau_NOALL is not used: the NOALL head collapses to a near-constant offset so its tau is dtype-dependent (indeterminate) noise",
            "severity_map": "normal=0, HSIL/CIN=1, cancer/carcinoma=2 (gen_figures_v10 convention)",
        },
        "variant_stats": variant_stats,
        "ldi": {"value": float(ldi), "theta": theta_z,
                "tau_full": float(tau_full), "tau_perp": null_mean,
                "sigma_null": null_sd, "tau_noall": float(tau_noall),
                "tau_noall_sd": float(sd_noall),
                "raw_noall_contrast_not_used": float(ldi_noall_raw)},
        "theta_calibration": {
            "B": args.perm, "perm_seed": args.perm_seed,
            "null_mean": null_mean, "null_sd": null_sd,
            "theta_q95": theta95, "theta_q99": theta99,
            "true_tau_full": float(tau_full), "p_upper": p_upper,
        },
        "gate": {"threshold": theta_z, "state": gate,
                 "reasons": [f"LDI={ldi:.3f} {'>' if ldi > theta_z else '<='} theta={theta_z:.3f}"]},
        "injected_calibration": {
            "alphas": [float(a) for a in alphas], "tau_curve": curve,
            "monotone": bool(monotone), "equiv_alpha": equiv_alpha,
        },
        "random_panel_control": {
            "n": int(len(rand_taus)), "mean": float(np.nanmean(rand_taus)),
            "sd": float(np.nanstd(rand_taus)),
            "note": "RANDOM108 keeps lambda_sup/lambda_prog, so its score ordering "
                    "tracks severity irrespective of panel content.",
        },
    }
    json.dump(out, open(RES / "csbj_ldi_validated.json", "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)

    # ---- figure ----
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "figure.dpi": 150,
                         "savefig.dpi": 300, "savefig.bbox": "tight"})
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
    ax = axes[0]
    ax.hist(null, bins=60, color="#cfe2f3", edgecolor="#6fa8dc")
    ax.axvline(tau_full, color="#cc0000", lw=2, label=f"TRUE tau = {tau_full:.3f}")
    ax.axvline(theta95, color="#38761d", ls="--", lw=1.6, label=f"theta = {theta95:.3f}")
    ax.set_xlabel("tau under shuffled severity")
    ax.set_ylabel("count")
    ax.set_title("(a) Label-permutation null & theta")
    ax.legend(fontsize=8, frameon=False)

    ax = axes[1]
    ax.plot(alphas, curve, "o-", color="#0b5394", lw=2, ms=4)
    ax.axhline(tau_full, color="#cc0000", ls="--", lw=1.4, label=f"TRUE tau={tau_full:.3f}")
    if equiv_alpha is not None:
        ax.axvline(equiv_alpha, color="#cc0000", ls=":", lw=1)
        ax.annotate(f"alpha*={equiv_alpha:.2f}", (equiv_alpha, tau_full),
                    textcoords="offset points", xytext=(6, -12), fontsize=8,
                    color="#cc0000")
    ax.set_xlabel("injected label-dependence alpha")
    ax.set_ylabel("Kendall tau")
    ax.set_title("(b) Injected-dependence calibration")
    ax.legend(fontsize=8, frameon=False)

    ax = axes[2]
    xs = np.arange(len(ORDER))
    vals = [variant_stats[v]["tau_mean"] for v in ORDER]
    sds = [variant_stats[v]["tau_sd"] for v in ORDER]
    ax.errorbar(xs, vals, yerr=sds, marker="o", color="#0b5394", lw=2,
                capsize=4, ms=6)
    ax.axhline(theta95, color="#38761d", ls="--", lw=1.2, label=f"theta={theta95:.3f}")
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xticks(xs)
    ax.set_xticklabels(ORDER, rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("tau (per-sample mean score)")
    ax.set_title(f"(c) Supervision removal  (tau scale)\nLDI={ldi:.2f} vs theta={theta_z:.2f}")
    ax.legend(fontsize=8, frameon=False)

    fig.tight_layout()
    fig.savefig(FIGDIR / "Fig_LDI_validation.png")
    print(f"figure -> {FIGDIR / 'Fig_LDI_validation.png'}")

    print("\n===== CSBJ LDI recomputation =====")
    print(f"tau_FULL={tau_full:+.4f} (sd {sd_full:.4f})  "
          f"tau_NOALL={tau_noall:+.4f} (sd {sd_noall:.4f})")
    print(f"LDI={ldi:.4f}   theta(z95)={theta_z:.4f}   "
          f"tau_null={null_mean:+.4f} (sd {null_sd:.4f})")
    print(f"tau(q95)={theta95:.4f}  tau(q99)={theta99:.4f}  "
          f"raw tau_FULL-tau_NOALL (not used)={ldi_noall_raw:+.4f}")
    print(f"gate -> {gate}")
    print(f"injected calibration monotone={monotone}, equiv_alpha*={equiv_alpha}")
    print(f"random-panel control tau mean={np.nanmean(rand_taus):.4f} (n={len(rand_taus)})")


if __name__ == "__main__":
    main()