#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Aggregate positive-control simulation audit results.

Reads results/results_SIM_<group>_<variant>_seed<s>.json produced by
run_sim_audit.sh, computes LDI + marginal decomposition + supported/suggestive/
unsupported grading for each simulated group, and writes
results/sim_audit_summary.json.

Expected verdicts (design ground truth):
  group_A (strong intrinsic signal) -> SUPPORTED
  group_B (weak signal)              -> SUGGESTIVE
  group_C (no signal + batch)        -> UNSUPPORTED
"""
import json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

VARIANTS = ["FULL", "NOIMAGE", "NOHPV", "NONEIGH", "NOPROG", "NOSUP", "NOALL"]
GROUPS = ["group_A", "group_B", "group_C"]


def load_tau_moran(group, variant):
    """Return (tau_values, moran_values, tau_perm_p_values) across seeds."""
    taus, morans, ps = [], [], []
    for seed in range(3):
        fp = RESULTS / f"results_SIM_{group}_{variant}_seed{seed}.json"
        if not fp.exists():
            print(f"  [warn] missing {fp.name}")
            continue
        d = json.load(open(fp, encoding="utf-8"))
        prog = d.get("progression_monotonicity") or {}
        kt = prog.get("kendall_tau")
        if kt is not None:
            taus.append(float(kt))
        else:
            print(f"  [warn] {fp.name}: kendall_tau is None")
        mi = d.get("moran_i")
        if mi is not None:
            morans.append(float(mi))
        pp = prog.get("permutation_p")
        if pp is not None:
            ps.append(float(pp))
    return taus, morans, ps


def mean_sd(vals):
    import statistics
    if not vals:
        return None, None
    m = statistics.mean(vals)
    s = statistics.stdev(vals) if len(vals) > 1 else 0.0
    return m, s


def grade_group(variant_stats):
    """Apply MRP-ST 3-level grading.

    supported:   FULL tau significant (p<0.05) AND NO-ALL tau still significant
                 AND stable across seeds (>=2/3 seeds significant).
    suggestive:  FULL tau significant but NO-PROG/NO-SUP borderline (p 0.03-0.08)
                 and seed-unstable (<=1/3 seeds significant at NO-ALL).
    unsupported: tau collapses after label removal (NO-ALL not significant) OR
                 FULL not significant.
    """
    full = variant_stats["FULL"]
    noprog = variant_stats["NOPROG"]
    nosup = variant_stats["NOSUP"]
    noall = variant_stats["NOALL"]

    full_sig = full["p_mean"] is not None and full["p_mean"] < 0.05
    noall_sig = noall["p_mean"] is not None and noall["p_mean"] < 0.05
    noprog_sig = noprog["p_mean"] is not None and noprog["p_mean"] < 0.05

    # seed stability: count seeds with p < 0.05
    full_n_sig = sum(1 for p in full["ps"] if p < 0.05) if full["ps"] else 0
    noall_n_sig = sum(1 for p in noall["ps"] if p < 0.05) if noall["ps"] else 0

    if full_sig and noall_sig and noall_n_sig >= 2:
        return "supported"
    if full_sig and not noall_sig and noprog_sig:
        return "suggestive"
    return "unsupported"


def main():
    summary = {}
    for group in GROUPS:
        print(f"\n===== {group} =====")
        vstats = {}
        for v in VARIANTS:
            taus, morans, ps = load_tau_moran(group, v)
            tau_m, tau_sd = mean_sd(taus)
            moran_m, moran_sd = mean_sd(morans)
            p_m, _ = mean_sd(ps)
            vstats[v] = {
                "tau_mean": tau_m, "tau_sd": tau_sd,
                "moran_mean": moran_m, "moran_sd": moran_sd,
                "p_mean": p_m, "ps": ps,
                "n_seeds": len(taus),
            }
            # safe format helpers
            def _fm(x):
                if x is None: return "  N/A "
                return f"{x:+.3f}"
            def _fm_sd(x):
                if x is None: return "  N/A "
                return f"{x:.3f}"
            def _fm_p(x):
                if x is None: return "  N/A "
                return f"{x:.0e}"
            print(f"  {v:8s} tau={_fm(tau_m)}±{_fm_sd(tau_sd)}  "
                  f"p={_fm_p(p_m)}  "
                  f"moran={_fm(moran_m)}  (n={len(taus)})")

        # LDI
        tau_full = vstats["FULL"]["tau_mean"] or 0.0
        tau_noall = vstats["NOALL"]["tau_mean"] or 0.0
        ldi = tau_full - tau_noall
        sd_f = vstats["FULL"]["tau_sd"] or 0.0
        sd_a = vstats["NOALL"]["tau_sd"] or 0.0
        ldi_sd = (sd_f**2 + sd_a**2)**0.5
        print(f"  LDI = {ldi:.3f} ± {ldi_sd:.3f}")

        # grade
        grade = grade_group(vstats)
        print(f"  -> GRADE: {grade.upper()}")

        summary[group] = {
            "variants": {k: {kk: vv for kk, vv in v.items() if kk != "ps"}
                         for k, v in vstats.items()},
            "ldi_mean": ldi,
            "ldi_sd": ldi_sd,
            "grade": grade,
        }

    # expected vs actual
    expected = {"group_A": "supported", "group_B": "suggestive", "group_C": "unsupported"}
    print("\n===== VALIDATION SUMMARY =====")
    all_pass = True
    for g in GROUPS:
        actual = summary[g]["grade"]
        exp = expected[g]
        ok = actual == exp
        all_pass = all_pass and ok
        print(f"  {g}: expected={exp:11s} actual={actual:11s}  {'PASS' if ok else 'FAIL'}")
    print(f"\n  OVERALL: {'ALL PASS - audit discriminates correctly' if all_pass else 'SOME FAILED - revisit simulation params or grading'}")

    summary["_expected"] = expected
    summary["_all_pass"] = all_pass
    out = RESULTS / "sim_audit_summary.json"
    json.dump(summary, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n  -> {out}")


if __name__ == "__main__":
    main()
