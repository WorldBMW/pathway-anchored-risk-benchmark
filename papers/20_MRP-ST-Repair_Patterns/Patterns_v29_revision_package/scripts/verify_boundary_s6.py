#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Table S6 boundary verification with 5 seeds (3 grid + s3/s4 reseed).

Cells: (signal, n) x lambda. R = tau_lodo / tau_insample per run.
Verdict criteria (manuscript L80):
  sig 1.0: boundary in (16, 32]  -> n16 damaged (min lambda>0 cell mean < 0.86),
                                n32 intact  (min lambda>0 cell mean >= 0.86)
  sig 0.3: boundary in (32, 64] -> n16 damaged, n32 damaged
"Damaged" tolerates the mid-dose worst cells; the verdict is boundary placement.
Prints per-cell 5-seed means and a final VERDICT line.
"""
import json
from pathlib import Path
import statistics as st

RES = Path(__file__).resolve().parents[1] / "results"
LAMS = ["0.0", "0.5", "1.0", "2.0", "5.0"]

# (signal, n) -> list of result json filenames (5 seeds)
CELLS = {
    ("1.0", 16): ["e2_phase_ax1_n16_s0.json", "e2_phase_ax1_n16_s1.json",
                  "e2_phase_ax1_n16_s2.json", "e2r_n16_s3.json", "e2r_n16_s4.json"],
    ("1.0", 32): ["e2_phase_ax1_n32_s0.json", "e2_phase_ax1_n32_s1.json",
                  "e2_phase_ax1_n32_s2.json", "e2r_n32_s3.json", "e2r_n32_s4.json"],
    ("0.3", 16): ["e2b_ax1_n16_s0.json", "e2b_ax1_n16_s1.json",
                  "e2b_ax1_n16_s2.json", "e2br_n16_s3.json", "e2br_n16_s4.json"],
    ("0.3", 32): ["e2b_ax1_n32_s0.json", "e2b_ax1_n32_s1.json",
                  "e2b_ax1_n32_s2.json", "e2br_n32_s3.json", "e2br_n32_s4.json"],
}


def load_R(fname):
    """Return {lam: R} for one seed-file, or None if missing."""
    p = RES / fname
    if not p.exists():
        return None
    sc = json.loads(p.read_text(encoding="utf-8")).get("scan", {})
    out = {}
    for lam in LAMS:
        # keys are f"s{seed}_lam{lam}" — find the one matching this lam
        cands = [v for k, v in sc.items() if k.endswith(f"lam{lam}")]
        if not cands:
            continue
        v = cands[0]
        tin = v.get("tau_insample")
        tlo = v.get("tau_lodo")
        if tin and abs(tin) > 1e-9:
            out[lam] = tlo / tin
    return out


def main():
    table = {}
    for (sig, n), files in CELLS.items():
        per_lam = {lam: [] for lam in LAMS}
        n_seeds = 0
        for f in files:
            R = load_R(f)
            if R is None:
                print(f"  [missing] {f}")
                continue
            n_seeds += 1
            for lam, r in R.items():
                per_lam[lam].append(r)
        cell = {lam: (st.mean(v) if v else float("nan")) for lam, v in per_lam.items()}
        table[(sig, n)] = {"n_seeds": n_seeds, "cells": cell}

    print(f"{'cell':10s} {'seeds':>5s} " + " ".join(f"λ={lam:<5s}" for lam in LAMS))
    for (sig, n), d in table.items():
        row = " ".join(f"{d['cells'][lam]:+.3f}" for lam in LAMS)
        print(f"sig={sig} n={n:<3d} {d['n_seeds']:>5d} {row}")

    # per-donor-count worst repair cell (lambda > 0)
    def worst_repair(sig, n):
        cells = table[(sig, n)]["cells"]
        return min(v for lam, v in cells.items() if lam != "0.0")

    checks = []
    s16 = worst_repair("1.0", 16)
    s32 = worst_repair("1.0", 32)
    w16 = worst_repair("0.3", 16)
    w32 = worst_repair("0.3", 32)
    checks.append(("sig1.0 n16 damaged (<0.86)", s16 < 0.86, s16))
    checks.append(("sig1.0 n32 intact  (>=0.86)", s32 >= 0.86, s32))
    checks.append(("sig0.3 n16 damaged (<0.86)", w16 < 0.86, w16))
    checks.append(("sig0.3 n32 damaged (<0.86)", w32 < 0.86, w32))
    all5 = all(d["n_seeds"] == 5 for d in table.values())

    for name, ok, val in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}: worst repair cell mean = {val:+.3f}")
    print(f"  {'PASS' if all5 else 'WARN'}  all four cells at 5 seeds")

    if all(ok for _, ok, _ in checks):
        print("VERDICT: BOUNDARY-PLACEMENT-UNCHANGED "
              "(sig1.0 in (16,32]; sig0.3 in (32,64]) — Table S6 holds")
    else:
        print("VERDICT: BOUNDARY-PLACEMENT-MOVED — Table S6 needs revision")


if __name__ == "__main__":
    main()
