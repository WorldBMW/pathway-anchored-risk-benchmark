#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Local (CPU-only) control experiments for the CSBJ revision.

Three controls that need NO retraining, reading only existing artifacts:

  1. theta robustness  : LDI gate stability across alpha {0.01,0.05,0.10,0.20}
                         and across permutation seeds (null reproducibility)
  2. bootstrap CI      : donor-resampled 95% CI of per-variant tau
  3. LODO contamination: leave-one-donor-out probe tau for all seven
                         supervision-removal variants of the REAL cohort.
                         Clean encoder = NOALL (never saw donor labels).
                         FULL/NOPROG/NOSUP saw every donor label, so their
                         probe tau is contaminated and is reported only as a
                         leakage control, never as generalisation evidence.

Outputs
  results/csbj_local_controls.json
  papers/12_CSBJ_audit_20261010/figures/Fig7_Local_controls.png
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import kendalltau
from scipy.special import erfinv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from probe_lodo import per_sample_embedding, severity_of  # noqa: E402

RES = ROOT / "results"
EVID = ROOT / "papers/12_CSBJ_audit_20261010/evidence"
FIGD = ROOT / "papers/12_CSBJ_audit_20261010/figures"
FIGD.mkdir(parents=True, exist_ok=True)

VARIANTS = ["FULL", "NOIMAGE", "NOHPV", "NONEIGH", "NOPROG", "NOSUP", "NOALL"]
LABEL_FREE = "NOALL"
ALPHAS = [0.01, 0.05, 0.10, 0.20]
NULL_SEEDS = [20261005, 20261006, 20261007, 20261008, 20261009]
B_NULL = 10000
B_BOOT = 2000
N_PERM_PROBE = 5000


def load_registry():
    return json.loads((EVID / "real_run_registry.json").read_text(encoding="utf-8"))


def sample_scores(reg, variant):
    """Per-seed dict of donor -> mean score, from the stored registry."""
    out = {}
    for row in reg.get(variant, []):
        if "sample_scores" in row:
            out[row["seed"]] = row["sample_scores"]
    return out


def severity_vector(names):
    return np.array([severity_of(n) for n in names], float)


def tau_of(scores, names):
    return float(kendalltau(np.array(scores, float), severity_vector(names)).statistic)


def theta_robustness(reg):
    """Gate threshold stability across alpha and permutation seed."""
    full = sample_scores(reg, "FULL")
    seed0 = sorted(full)[0]
    names = sorted(full[seed0])
    s = np.array([full[seed0][n] for n in names], float)
    y = severity_vector(names)
    tau_full = float(kendalltau(s, y).statistic)

    per_alpha = {}
    for a in ALPHAS:
        rows = []
        for ns in NULL_SEEDS:
            rng = np.random.default_rng(ns)
            null = np.array([kendalltau(s, rng.permutation(y)).statistic
                             for _ in range(B_NULL)])
            q = float(np.quantile(null, 1 - a))
            mu, sd = float(null.mean()), float(null.std())
            ldi = (tau_full - mu) / sd
            z = float(np.sqrt(2) * erfinv(2 * (1 - a) - 1)) if a > 0 else np.inf
            rows.append({"perm_seed": ns, "theta_tau": q, "null_mean": mu,
                         "null_sd": sd, "ldi": ldi, "theta_z": z,
                         "gate": "label-dependent" if ldi > z else "not label-dependent"})
        qs = [r["theta_tau"] for r in rows]
        ldis = [r["ldi"] for r in rows]
        per_alpha[f"{a:.2f}"] = {
            "theta_tau_mean": float(np.mean(qs)), "theta_tau_min": float(np.min(qs)),
            "theta_tau_max": float(np.max(qs)),
            "ldi_mean": float(np.mean(ldis)), "ldi_min": float(np.min(ldis)),
            "ldi_max": float(np.max(ldis)),
            "gate_stable": len({r["gate"] for r in rows}) == 1,
            "gate": rows[0]["gate"], "rows": rows,
        }
    return {"tau_full": tau_full, "n_donors": len(y),
            "B_null": B_NULL, "null_seeds": NULL_SEEDS, "per_alpha": per_alpha}


def bootstrap_ci(reg):
    """Donor-resampled 95% CI of tau for each variant (per seed, pooled)."""
    out = {}
    for v in VARIANTS:
        per_seed = sample_scores(reg, v)
        if not per_seed:
            continue
        rows = []
        for seed, d in sorted(per_seed.items()):
            names = sorted(d)
            s = np.array([d[n] for n in names], float)
            y = severity_vector(names)
            t = float(kendalltau(s, y).statistic)
            rng = np.random.default_rng(1000 + int(seed))
            boot = np.empty(B_BOOT)
            n = len(names)
            for b in range(B_BOOT):
                idx = rng.integers(0, n, n)
                if len(np.unique(y[idx])) < 2:
                    boot[b] = np.nan
                    continue
                boot[b] = kendalltau(s[idx], y[idx]).statistic
            boot = boot[~np.isnan(boot)]
            rows.append({"seed": seed, "tau": t, "n": n,
                         "ci_lo": float(np.quantile(boot, 0.025)),
                         "ci_hi": float(np.quantile(boot, 0.975))})
        taus = np.array([r["tau"] for r in rows])
        # is the score degenerate? A collapsed head keeps a huge absolute
        # magnitude (offset) while its across-donor spread goes to zero.
        seed0 = sorted(per_seed)[0]
        vals = np.array(list(per_seed[seed0].values()), float)
        mag = float(np.median(np.abs(vals)))
        spread = float(vals.max() - vals.min())
        rel = spread / mag if mag > 0 else np.inf
        out[v] = {
            "n_seeds": len(rows), "tau_mean": float(taus.mean()),
            "tau_sd": float(taus.std(ddof=1)) if len(rows) > 1 else 0.0,
            "score_magnitude": mag, "score_spread": spread,
            "relative_spread": float(rel),
            # collapsed: spread is a negligible fraction of the magnitude,
            # so the across-donor ordering is floating-point noise.
            "collapsed": bool(rel < 0.01),
            "per_seed": rows,
        }
    return out


def lodo_contamination(reg):
    """LODO probe tau for every variant of the real cohort.

    NOALL is the only label-free encoder; the others were optimised with every
    donor's ordinal label, so their held-out probe tau is a leakage control.
    """
    out = {}
    for v in VARIANTS:
        rows = []
        for seed in sorted({r["seed"] for r in reg.get(v, [])}):
            fp = RES / f"fused_embs_{v}_seed{seed}.npz"
            if not fp.exists():
                continue
            with np.load(fp) as z:
                X, y, names = per_sample_embedding(z)
            if len(np.unique(y)) < 2:
                continue
            X = X.astype(np.float64)
            n = len(y)
            pred = np.empty(n)
            for i in range(n):
                tr = np.arange(n) != i
                mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-8
                Ztr, z1 = (X[tr] - mu) / sd, (X[i] - mu) / sd
                A = Ztr.T @ Ztr + np.eye(Ztr.shape[1])
                w = np.linalg.solve(A, Ztr.T @ y[tr])
                pred[i] = z1 @ w
            tau_lodo = float(kendalltau(pred, y).statistic)
            rng = np.random.default_rng(0)
            ge = 0
            for _ in range(N_PERM_PROBE):
                if kendalltau(pred, rng.permutation(y)).statistic >= tau_lodo:
                    ge += 1
            p = (ge + 1) / (N_PERM_PROBE + 1)
            # in-sample (fit all, predict all) memorisation contrast
            mu, sd = X.mean(0), X.std(0) + 1e-8
            Z = (X - mu) / sd
            w = np.linalg.solve(Z.T @ Z + np.eye(Z.shape[1]), Z.T @ y)
            tau_in = float(kendalltau(Z @ w, y).statistic)
            rows.append({"seed": seed, "n_donors": n, "tau_lodo": tau_lodo,
                         "p_perm": p, "tau_in_sample": tau_in,
                         "gap": tau_in - tau_lodo})
        if rows:
            tl = np.array([r["tau_lodo"] for r in rows])
            out[v] = {
                "label_free": v == LABEL_FREE,
                "n_seeds": len(rows),
                "tau_lodo_mean": float(tl.mean()),
                "tau_lodo_sd": float(tl.std(ddof=1)) if len(rows) > 1 else 0.0,
                "n_seeds_sig": int(sum(r["p_perm"] < 0.05 for r in rows)),
                "per_seed": rows,
            }
    return out


def make_figure(theta, boot, probe):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))

    ax = axes[0]
    al = [float(a) for a in theta["per_alpha"]]
    tm = [theta["per_alpha"][f"{a:.2f}"]["theta_tau_mean"] for a in al]
    tlo = [theta["per_alpha"][f"{a:.2f}"]["theta_tau_min"] for a in al]
    thi = [theta["per_alpha"][f"{a:.2f}"]["theta_tau_max"] for a in al]
    ax.errorbar(al, tm, yerr=[np.array(tm) - np.array(tlo), np.array(thi) - np.array(tm)],
                marker="o", capsize=4, label="gate theta (tau scale)")
    ax.axhline(theta["tau_full"], color="crimson", ls="--",
               label=f"observed tau_FULL={theta['tau_full']:.3f}")
    ax.set_xlabel("alpha"); ax.set_ylabel("theta")
    ax.set_title("(a) Gate threshold robustness\nalpha x permutation seed")
    ax.legend(fontsize=8); ax.grid(alpha=.3)

    ax = axes[1]
    vs = list(boot)
    x = np.arange(len(vs))
    m = [boot[v]["tau_mean"] for v in vs]
    sd = [boot[v]["tau_sd"] for v in vs]
    ax.bar(x, m, yerr=sd, capsize=4,
           color=["crimson" if v == LABEL_FREE else "steelblue" for v in vs])
    ax.set_xticks(x); ax.set_xticklabels(vs, rotation=45, ha="right")
    ax.axhline(0, color="k", lw=.8)
    ax.set_ylabel("mean per-donor tau")
    ax.set_title("(b) Score ordering by variant\n(red = label-free encoder)")
    ax.grid(alpha=.3, axis="y")

    ax = axes[2]
    vs2 = list(probe)
    x = np.arange(len(vs2))
    tl = [probe[v]["tau_lodo_mean"] for v in vs2]
    sd2 = [probe[v]["tau_lodo_sd"] for v in vs2]
    ax.bar(x, tl, yerr=sd2, capsize=4,
           color=["crimson" if v == LABEL_FREE else "darkorange" for v in vs2])
    ax.set_xticks(x); ax.set_xticklabels(vs2, rotation=45, ha="right")
    ax.axhline(0, color="k", lw=.8)
    ax.axhline(0.35, color="green", ls=":", label="supported threshold 0.35")
    ax.axhline(0.15, color="gray", ls=":", label="unsupported threshold 0.15")
    ax.set_ylabel("LODO probe tau-b")
    ax.set_title("(c) Held-out probe: contaminated\nvs label-free encoder")
    ax.legend(fontsize=8); ax.grid(alpha=.3, axis="y")

    fig.tight_layout()
    fig.savefig(FIGD / "Fig7_Local_controls.png", dpi=300)
    fig.savefig(FIGD / "Fig7_Local_controls.pdf")
    plt.close(fig)


def main():
    reg = load_registry()
    theta = theta_robustness(reg)
    boot = bootstrap_ci(reg)
    probe = lodo_contamination(reg)
    report = {
        "analysis_date": "2026-10-12",
        "scope": "local CPU-only controls; no retraining; reads existing NPZ/registry",
        "theta_robustness": theta,
        "bootstrap_tau": boot,
        "lodo_contamination": probe,
    }
    (RES / "csbj_local_controls.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    make_figure(theta, boot, probe)

    print("=== theta robustness ===")
    for a, r in theta["per_alpha"].items():
        print(f"  alpha={a}  theta_tau {r['theta_tau_min']:.3f}-{r['theta_tau_max']:.3f}"
              f"  LDI {r['ldi_min']:.2f}-{r['ldi_max']:.2f}  gate={r['gate']}"
              f"  stable={r['gate_stable']}")
    print("=== bootstrap tau (mean +- sd across seeds) ===")
    for v, r in boot.items():
        print(f"  {v:8s} tau={r['tau_mean']:+.3f} sd={r['tau_sd']:.3f}"
              f"  mag={r['score_magnitude']:.3f} spread={r['score_spread']:.3f}"
              f"  rel={r['relative_spread']:.2e}  collapsed={r['collapsed']}")
    print("=== LODO probe (label-free vs contaminated) ===")
    for v, r in probe.items():
        print(f"  {v:8s} tau_lodo={r['tau_lodo_mean']:+.3f} (sd {r['tau_lodo_sd']:.3f})"
              f"  sig {r['n_seeds_sig']}/{r['n_seeds']}  label_free={r['label_free']}")
    print(f"\nwrote {RES / 'csbj_local_controls.json'}")
    print(f"wrote {FIGD / 'Fig7_Local_controls.png'}")


if __name__ == "__main__":
    main()