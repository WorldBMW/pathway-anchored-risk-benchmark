#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Aggregate Experiment A (SOTA head-to-head, guide §12.2).

Reads results/expA_<cohort>_<arm>.json produced by repair_e3_methodB_train.py
with --method {mrp,groupdro,irm} on the two scale-matched SIM cohorts:

  cohort A : strong SHARED disease program  (signal_a=2.5)  -> SAFETY arm
             (repair must NOT kill a real, transferable signal)
  cohort C : identity-fingerprint confound   (signal_c=1.2) -> LEAKAGE arm
             (no transferable class signal; in-sample memory only)

and reports, per (arm, dose), the three unified metrics of §12.2 plus the
three-axis acceptance of §9.5:

  LDI  = (tau_lodo - tau_perp) / sigma_null          (calibrated index)
  R    = tau_lodo / tau_in                            (transferable fraction)
  axis1 safety      : cohort-A tau_lodo retention >= 0.70 * baseline
  axis2 leakage-cut : cohort-C in-sample gap (tau_in - tau_lodo) shrinks
  axis3 non-blind   : cohort-A LDI > gate (still SUPPORTED)
                      AND cohort-C LDI < gate (still UNSUPPORTED)

Baseline (dose 0) is method-independent (verified bit-identical across arms);
it is read from expA_<cohort>_baseline.json.

Outputs:
  results/expA_sota_table.csv      long-format per-(cohort, arm, dose)
  results/expA_sota_summary.json   per-(cohort, arm, dose) means + axis verdicts
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

import numpy as np

R_ = Path(__file__).resolve().parents[1] / "results"
GATE = 1.645
FIDELITY_KEEP = 0.70
TAU_PERP = 0.001


def _means(rs):
    ldi = np.array([r["ldi"] for r in rs], float)
    tau_lo = np.array([r["tau_lodo"] for r in rs], float)
    tau_in = np.array([r["tau_insample"] for r in rs], float)
    p = np.array([r["p_refit"] for r in rs], float)
    R = np.divide(tau_lo, tau_in, out=np.full_like(tau_lo, np.nan),
                  where=np.abs(tau_in) > 1e-9)
    return {
        "ldi_mean": float(np.mean(ldi)), "ldi_sd": float(np.std(ldi, ddof=1)),
        "tau_lodo_mean": float(np.mean(tau_lo)),
        "tau_lodo_sd": float(np.std(tau_lo, ddof=1)),
        "tau_in_mean": float(np.mean(tau_in)),
        "R_mean": float(np.nanmean(R)),
        "p_mean": float(np.mean(p)),
        "gap_mean": float(np.mean(tau_in - tau_lo)),
        "n_seeds": len(rs),
    }


def _load(path: Path):
    """-> {dose: [per-seed scan records]} keyed by dose value."""
    d = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for key, r in d["scan"].items():
        dose = float(key.split("lam")[1])
        out.setdefault(dose, []).append(r)
    return out, d["params"]


def collect(models):
    """models: {(cohort, arm): Path} -> nested stats."""
    cache = {}
    for (coh, arm), p in models.items():
        if not p.exists():
            print(f"[warn] missing {p.name}")
            continue
        doses, params = _load(p)
        for dose, rs in doses.items():
            cache[(coh, arm, dose)] = (_means(rs), params)
    return cache


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="expA", help="result filename tag")
    ap.add_argument("--out-csv", default="results/expA_sota_table.csv")
    ap.add_argument("--out-json", default="results/expA_sota_summary.json")
    args = ap.parse_args()

    cohorts = {"A": "safety (shared signal)", "C": "leakage (identity confound)"}
    arms = ["mrp", "groupdro", "irm"]
    models = {}
    for c in cohorts:
        models[(c, "baseline")] = R_ / f"{args.tag}_{c}_baseline.json"
        for a in arms:
            models[(c, a)] = R_ / f"{args.tag}_{c}_{a}.json"
    cache = collect(models)

    table, summary = [], {}
    for c, desc in cohorts.items():
        base = cache.get((c, "baseline", 0.0))
        base_tau = base[0]["tau_lodo_mean"] if base else None
        base_gap = base[0]["gap_mean"] if base else None
        for arm in ["baseline"] + arms:
            doses = sorted(d for (cc, aa, d) in cache if cc == c and aa == arm)
            for dose in doses:
                m, params = cache[(c, arm, dose)]
                row = dict(cohort=c, arm=arm, dose=dose,
                           method=params.get("method"), **m)
                # axis 1: safety (cohort A only)
                row["axis1_safety"] = ("" if base_tau is None else
                                       f"{m['tau_lodo_mean'] / base_tau:.3f}"
                                       if abs(base_tau) > 1e-9 else "n/a")
                # axis 2: leakage-cut (cohort C only) = gap retained
                row["axis2_gap_ratio"] = ("" if base_gap is None else
                                          f"{m['gap_mean'] / base_gap:.3f}"
                                          if abs(base_gap) > 1e-9 else "n/a")
                # axis 3: instrument non-blinding
                row["axis3_supported"] = bool(m["ldi_mean"] > GATE)
                table.append(row)
                summary.setdefault(c, {}).setdefault(arm, {})[f"{dose}"] = {
                    "desc": desc, "metrics": m,
                    "axis1_safety_ratio": row["axis1_safety"],
                    "axis2_gap_ratio": row["axis2_gap_ratio"],
                    "axis3_supported": row["axis3_supported"],
                }

    # --- three-axis verdict per (arm, dose) ---
    verdicts = {}
    for arm in arms:
        passing = []
        for dose in sorted(d for (cc, aa, d) in cache
                           if aa == arm and cc == "A"):
            a = cache.get(("A", arm, dose))
            cc_ = cache.get(("C", arm, dose))
            if a is None or cc_ is None:
                continue
            ab = cache.get(("A", "baseline", 0.0))
            cb = cache.get(("C", "baseline", 0.0))
            if ab is None or cb is None:
                continue
            base_tau = ab[0]["tau_lodo_mean"]
            base_gap = cb[0]["gap_mean"]
            safe = abs(base_tau) > 1e-9 and \
                a[0]["tau_lodo_mean"] / base_tau >= FIDELITY_KEEP
            leak = abs(base_gap) > 1e-9 and abs(cc_[0]["gap_mean"]) < abs(base_gap)
            nonblind = (a[0]["ldi_mean"] > GATE) and (cc_[0]["ldi_mean"] < GATE)
            verdicts.setdefault(arm, {})[f"{dose}"] = {
                "safety": bool(safe), "leakage_cut": bool(leak),
                "non_blind": bool(nonblind),
                "three_axis_pass": bool(safe and leak and nonblind),
                "A_retention": (a[0]["tau_lodo_mean"] / base_tau
                                if abs(base_tau) > 1e-9 else None),
                "C_gap_ratio": (cc_[0]["gap_mean"] / base_gap
                                if abs(base_gap) > 1e-9 else None),
            }
        passing = [d for d, v in verdicts[arm].items() if v["three_axis_pass"]]
        verdicts[arm]["_passing_doses"] = passing

    out = {"gate": GATE, "fidelity_keep": FIDELITY_KEEP,
           "tau_perp": TAU_PERP, "table": summary, "three_axis": verdicts}
    Path(args.out_json).write_text(json.dumps(out, indent=2), encoding="utf-8")

    if table:
        fields = list(table[0].keys())
        with open(args.out_csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(table)

    # ---- console report ----
    for c, desc in cohorts.items():
        print(f"\n===== cohort {c}: {desc} =====")
        print(f"  {'arm':10s} {'dose':>6s}  {'LDI':>8s}  {'tau_lodo':>9s}  "
              f"{'tau_in':>7s}  {'R':>7s}  {'gap':>7s}  axis")
        for arm in ["baseline"] + arms:
            for dose in sorted(d for (cc, aa, d) in cache
                               if cc == c and aa == arm):
                m = cache[(c, arm, dose)][0]
                flag = ("safe=%.2f" % float(summary[c][arm][f"{dose}"]
                                            ["axis1_safety_ratio"])
                        if summary[c][arm][f"{dose}"]["axis1_safety_ratio"] != ""
                        else "")
                gapr = summary[c][arm][f"{dose}"]["axis2_gap_ratio"]
                if gapr not in ("", "n/a"):
                    flag = "gap=%.2f" % float(gapr)
                print(f"  {arm:10s} {dose:6.2f}  {m['ldi_mean']:+8.3f}  "
                      f"{m['tau_lodo_mean']:+9.4f}  {m['tau_in_mean']:+7.4f}  "
                      f"{m['R_mean']:+7.3f}  {m['gap_mean']:+7.3f}  {flag}")
    print("\n===== three-axis pass (both cohorts) =====")
    for arm in arms:
        print(f"  {arm:10s} passing doses = {verdicts[arm]['_passing_doses']}")
    print(f"\n  -> {args.out_json}\n  -> {args.out_csv}")


if __name__ == "__main__":
    main()
