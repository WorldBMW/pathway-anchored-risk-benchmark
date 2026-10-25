#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PERM sensitivity recheck: B=10000 sigma_null vs stored B=2000.

For every (seed, lam) run in the E4 stable dump, recompute the null SD of
the LOO tau with B=10000 permutations (same blocking RNG semantics as
refit_grid_audit.audit) and recompute LDI_10k = (tau_lodo - TAU_PERP) /
sigma_10k. Compare with the stored B=2000 values -> sensitivity of the
acceptance gate to permutation count.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from refit_grid_audit import operator, kendall_tau  # noqa: E402

R = HERE.parent / "results"
TAU_PERP = 0.001
B = 10000
SEED = 20261010


def sigma_null(Xs, y, b=B):
    H = operator(Xs)
    rng = np.random.default_rng(SEED)
    i, j = np.triu_indices(len(y), 2)[:0] or np.triu_indices(len(y), 2)
    taus = np.empty(b)
    for st in range(0, b, 100):
        Y = np.stack([rng.permutation(y) for _ in range(100)])
        P = Y @ H.T
        a = np.sign(P[:, j] - P[:, i])
        bb = np.sign(Y[:, j] - Y[:, i])
        den = np.sqrt((a * a).sum(1) * (bb * bb).sum(1))
        taus[st:st + 100] = np.divide((a * bb).sum(1), den,
                                      out=np.zeros(len(P)), where=den > 0)
    return float(taus.std(ddof=1)), float(kendall_tau(H @ y, y))


def main():
    d = json.loads((R / "repair_e4_hnscc_stable.json").read_text())
    dx = d["dump_xs"]
    out = {}
    print(f"{'run':>11} {'ldi_2k':>8} {'ldi_10k':>8} {'sig_2k':>7} "
          f"{'sig_10k':>8} {'gate@10k':>8}")
    for key in sorted(dx.keys()):
        Xs = np.array(dx[key]["Xs"], dtype=float)
        y = np.array(dx[key]["y"], dtype=float)
        # stored run metrics (find matching scan entry)
        seed = int(key[1:].split("_")[0])
        lam = key.split("lam")[1]
        r = d["scan"].get(f"s{seed}_lam{lam}", {})
        sig10, tau_obs = sigma_null(Xs, y)
        # sanity: recomputed LOO tau should match stored tau_lodo
        ldi10 = (tau_obs - TAU_PERP) / sig10 if sig10 > 0 else float("inf")
        ldi2k = r.get("ldi", float("nan"))
        gate = "PASS" if ldi10 < 1.645 else "fail"
        flag = "" if abs(tau_obs - r.get("tau_lodo", 9)) < 1e-4 else " !tau"
        print(f"{key:>11} {ldi2k:>+8.3f} {ldi10:>+8.3f} "
              f"{r.get('sigma_null', float('nan')):7.4f} {sig10:8.4f} "
              f"{gate:>8}{flag}")
        out[key] = {"ldi_2k": ldi2k, "ldi_10k": ldi10,
                    "sigma_2k": r.get("sigma_null"), "sigma_10k": sig10,
                    "tau_lodo_recheck": tau_obs,
                    "tau_lodo_stored": r.get("tau_lodo")}
    (R / "perm10k_recheck.json").write_text(json.dumps(out, indent=2))
    changed = sum(1 for v in out.values()
                  if (v["ldi_2k"] < 1.645) != (v["ldi_10k"] < 1.645))
    print(f"\n[verdict] gate flips 2k->10k: {changed}/{len(out)} runs")
    print("[saved] results/perm10k_recheck.json")


if __name__ == "__main__":
    main()
