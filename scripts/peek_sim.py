#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Quick-look diagnostic for the simulation audit — reads whatever SIM result
JSONs currently exist and prints the τ / p / Moran table immediately.
Run it after ANY subset of runs (no need to wait for all 63).

Usage:
    python scripts/peek_sim.py
"""
import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parent.parent / "results"
GROUPS = ["group_A", "group_B", "group_C"]
VARIANTS = ["FULL", "NOIMAGE", "NOHPV", "NONEIGH", "NOPROG", "NOSUP", "NOALL"]


def main():
    for g in GROUPS:
        print(f"\n===== {g} =====")
        print(f"  {'variant':8s} {'seed':>4s}  {'tau':>8s}  {'perm_p':>9s}  {'moran':>7s}")
        for v in VARIANTS:
            for s in range(3):
                fp = RESULTS / f"results_SIM_{g}_{v}_seed{s}.json"
                if not fp.exists():
                    continue
                d = json.load(open(fp, encoding="utf-8"))
                pm = d.get("progression_monotonicity") or {}
                tau = pm.get("kendall_tau")
                p = pm.get("permutation_p")
                mi = d.get("moran_i")
                ts = f"{tau:+.3f}" if tau is not None else "  null "
                ps = f"{p:.4f}" if p is not None else "  null "
                ms = f"{mi:.3f}" if mi is not None else "  null "
                print(f"  {v:8s} {s:4d}  {ts:>8s}  {ps:>9s}  {ms:>7s}")


if __name__ == "__main__":
    main()
