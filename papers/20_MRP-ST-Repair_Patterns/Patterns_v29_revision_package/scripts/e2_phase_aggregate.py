#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""E2 phase-diagram aggregation (guide §10.1).

Reads the 24 per-cohort JSONs produced by repair_e3_methodB_train.py on the
E2 grid (axis 1: n_patients x {4,8,16,32,64}, k=1; axis 2: k x {2,4,8},
n=16; 3 sim seeds each), computes the order parameter

    R(n, k, lambda) = tau_lodo / tau_in        (LOO retention of true signal)

and estimates the leakage-dominated phase boundary phi*(lambda):
the smallest patient count (axis 1) / the largest slices-per-donor (axis 2)
at which mean R >= 0.90, with linear interpolation between grid points.

Outputs:
  results/e2_phase_table.csv      long-format per-(cohort, lam) table
  results/e2_phase_summary.json   per-(n,k,lam) means, phi* per lam, delta phi*
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np

R_ = Path(__file__).resolve().parents[1] / "results"
AXIS1 = [4, 8, 16, 32, 64]
AXIS2_K = [2, 4, 8]
SEEDS = [0, 1, 2]
LAMS = [0.0, 0.5, 1.0, 2.0, 5.0]
R_GATE = 0.90


def load(path: Path):
    d = json.loads(path.read_text())
    seed = d["params"].get("seed", 0)
    rows = []
    for key, r in d["scan"].items():
        lam = float(key.split("lam")[1])
        tau_in = r["tau_insample"]
        tau_lo = r["tau_lodo"]
        rows.append(dict(lam=lam, tau_in=tau_in, tau_lodo=tau_lo,
                         R=(tau_lo / tau_in if abs(tau_in) > 1e-9 else np.nan),
                         ldi=r["ldi"], p=r["p_refit"]))
    return seed, rows


def interp_gate(xs, ys, gate=R_GATE):
    """smallest x (linear interp) at which y >= gate, None if never."""
    for i, y in enumerate(ys):
        if y >= gate:
            if i == 0:
                return float(xs[0])
            y0, y1 = ys[i - 1], y
            if y1 == y0:
                return float(xs[i])
            return float(xs[i - 1] + (gate - y0) / (y1 - y0)
                         * (xs[i] - xs[i - 1]))
    return None


def main():
    table = []
    # axis 1: (n, k=1); axis 2: (n=16, k) with k=1 from axis-1 n16 cell
    cells = {}  # (n, k) -> {lam -> [R per seed]}
    for n in AXIS1:
        for s in SEEDS:
            p = R_ / f"e2_phase_ax1_n{n}_s{s}.json"
            if not p.exists():
                print(f"[warn] missing {p.name}")
                continue
            seed, rows = load(p)
            for r in rows:
                table.append(dict(axis=1, n=n, k=1, seed=s, **r))
                cells.setdefault((n, 1), {}).setdefault(r["lam"], []).append(r["R"])
    for k in AXIS2_K:
        for s in SEEDS:
            p = R_ / f"e2_phase_ax2_k{k}_s{s}.json"
            if not p.exists():
                print(f"[warn] missing {p.name}")
                continue
            seed, rows = load(p)
            for r in rows:
                table.append(dict(axis=2, n=16, k=k, seed=s, **r))
                cells.setdefault((16, k), {}).setdefault(r["lam"], []).append(r["R"])

    # per-cell per-lam means
    summary = {}
    for (n, k), lams in cells.items():
        for lam, rs in lams.items():
            summary.setdefault(f"n{n}_k{k}", {})[f"lam{lam}"] = {
                "R_mean": float(np.nanmean(rs)),
                "R_sd": float(np.nanstd(rs)),
                "n_seeds": len(rs),
            }

    # phi* along axis 1 per lambda (k=1), interpolation on log2(n)
    phis = {}
    for lam in LAMS:
        xs, ys = [], []
        for n in AXIS1:
            key = f"n{n}_k1"
            if key in summary and f"lam{lam}" in summary[key]:
                xs.append(np.log2(n))
                ys.append(summary[key][f"lam{lam}"]["R_mean"])
        if xs:
            g = interp_gate(xs, ys)
            phis[f"lam{lam}"] = (None if g is None else float(2 ** g))
    # axis 2: leakage RE-ENTERS as k grows -> phi2* = largest k with R >= gate
    phis2 = {}
    for lam in LAMS:
        ks = [1] + AXIS2_K
        ys = []
        for k in ks:
            key = f"n16_k{k}"
            if key in summary and f"lam{lam}" in summary[key]:
                ys.append(summary[key][f"lam{lam}"]["R_mean"])
        good = [ks[i] for i, y in enumerate(ys) if y >= R_GATE]
        phis2[f"lam{lam}"] = (max(good) if good else 0)

    out = {"R_gate": R_GATE, "cells": summary,
           "phi_star_axis1_per_lam": phis,
           "phi2_star_axis2_per_lam": phis2,
           "delta_phi_star": (phis.get("lam0.0") is not None
                              and any(v is not None for k2, v in phis.items()
                                      if k2 != "lam0.0"))}
    (R_ / "e2_phase_summary.json").write_text(json.dumps(out, indent=2))

    import csv
    with open(R_ / "e2_phase_table.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0].keys()))
        w.writeheader()
        w.writerows(table)

    print("== axis 1 (patients n, k=1): mean R per lam ==")
    print("  n   " + "".join(f"lam{lam:<7}" for lam in LAMS))
    for n in AXIS1:
        key = f"n{n}_k1"
        row = [summary[key].get(f"lam{lam}", {}).get("R_mean", float("nan"))
               for lam in LAMS]
        print(f"  {n:<3} " + "".join(f"{v:+.3f}   " for v in row))
    print("== axis 2 (slices/donor k, n=16): mean R per lam ==")
    print("  k   " + "".join(f"lam{lam:<7}" for lam in LAMS))
    for k in [1] + AXIS2_K:
        key = f"n16_k{k}"
        row = [summary[key].get(f"lam{lam}", {}).get("R_mean", float("nan"))
               for lam in LAMS]
        print(f"  {k:<3} " + "".join(f"{v:+.3f}   " for v in row))
    print("phi* (axis1, patients):", phis)
    print("phi2* (axis2, max k with R>=gate):", phis2)


if __name__ == "__main__":
    main()
