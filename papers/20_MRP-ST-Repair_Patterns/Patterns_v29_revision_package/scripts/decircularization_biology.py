#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""De-circularization interpretability control (#5 in D checklist).

Re-runs the 11-pathway/cell-type ssGSEA-vs-risk correlation under FULL,
NO-PROG, NO-SUP, and NO-ALL to determine which biology correlations are
CONSTRUCTED (by the HPV-proxy training target) vs. REAL (intrinsic, surviving
label removal).

Logic:
  - FULL uses HPV-proxy supervision (lambda_sup>0) + ordinal labels (lambda_prog>0)
    + HPV pathway prior (lambda_hpv>0).  High-risk spots are trained to correlate
    with HPV panel expression -> HPV-program enrichment is partly circular.
  - NO-PROG removes ordinal labels but keeps the expression-derived HPV proxy.
  - NO-SUP removes both labels AND the HPV proxy (lambda_sup=lambda_prog=0),
    keeping only reconstruction + neighborhood + morphology + pathway prior.
  - NO-ALL removes labels, proxy, AND pathway prior.

Correlations that survive into NO-SUP / NO-ALL are REAL (intrinsic data
biology).  Correlations present in FULL but absent in NO-SUP are CONSTRUCTED
by the supervised training target.

Output: results/decircularization_biology.json (per-variant, per-set rho/q,
with constructed-vs-real classification).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from downstream_spot_analysis import analyze_npz

RESULTS = ROOT / "results"

# key pathways/cell types to report (the ones used in Fig 4 of the paper)
KEY_SETS = [
    "CELL_tumor_epithelial",
    "HPV_INTEGRATION_CANDIDATE",
    "ANTIGEN_PRESENTATION",
    "INTERFERON_ANTIVIRAL",
    "PROLIFERATION",
    "CELL_stromal",
    "CELL_immune",
]

VARIANTS = {
    "FULL": ["FULL_seed0", "FULL_seed3", "FULL_seed4"],
    "NOPROG": ["NOPROG_seed0", "NOPROG_seed1", "NOPROG_seed2", "NOPROG_seed3"],
    "NOSUP": ["NOSUP_seed0", "NOSUP_seed1", "NOSUP_seed2"],
    "NOALL": ["NOALL_seed0", "NOALL_seed1", "NOALL_seed2"],
}


def get_corr(rows, set_name):
    for r in rows:
        if r["set"] == set_name:
            return r["spearman_rho"], r["BH_q"]
    return None, None


def main():
    summary = {"variants": {}, "classification": {}}

    for variant, run_ids in VARIANTS.items():
        print(f"\n{'='*60}")
        print(f"  {variant}")
        print(f"{'='*60}")
        set_rhos = {s: [] for s in KEY_SETS}
        for rid in run_ids:
            fp = RESULTS / f"fused_embs_{rid}.npz"
            if not fp.exists():
                print(f"  [skip] {fp.name} not found")
                continue
            res, _groups, _gl, rows = analyze_npz(str(fp))
            for s in KEY_SETS:
                rho, q = get_corr(rows, s)
                if rho is not None:
                    set_rhos[s].append(rho)

        vstats = {}
        for s in KEY_SETS:
            rhos = set_rhos[s]
            if rhos:
                vstats[s] = {
                    "rho_mean": float(np.mean(rhos)),
                    "rho_sd": float(np.std(rhos, ddof=1)) if len(rhos) > 1 else 0.0,
                    "n_seeds": len(rhos),
                    "rhos": [float(x) for x in rhos],
                }
            else:
                vstats[s] = {"rho_mean": None, "rho_sd": None, "n_seeds": 0, "rhos": []}
        summary["variants"][variant] = vstats

        # print table
        print(f"\n  {'Set':30s} {'rho(FULL)':>10s} {'rho(NO-PROG)':>12s} "
              f"{'rho(NO-SUP)':>11s} {'rho(NO-ALL)':>11s}")
        for s in KEY_SETS:
            vals = []
            for v in ["FULL", "NOPROG", "NOSUP", "NOALL"]:
                rm = summary["variants"].get(v, {}).get(s, {}).get("rho_mean")
                vals.append(f"{rm:+.3f}" if rm is not None else "  N/A  ")
            print(f"  {s:30s} {vals[0]:>10s} {vals[1]:>12s} {vals[2]:>11s} {vals[3]:>11s}")

    # ---- classification: constructed vs real ----
    print(f"\n{'='*60}")
    print("  CONSTRUCTED vs REAL classification")
    print(f"{'='*60}")
    for s in KEY_SETS:
        full_rho = summary["variants"]["FULL"].get(s, {}).get("rho_mean")
        nosup_rho = summary["variants"]["NOSUP"].get(s, {}).get("rho_mean")
        noall_rho = summary["variants"]["NOALL"].get(s, {}).get("rho_mean")

        if full_rho is None:
            cls = "no_data"
        elif nosup_rho is not None and abs(nosup_rho) > 0.05:
            # survives label+proxy removal -> real
            cls = "REAL (survives NO-SUP)"
        elif noall_rho is not None and abs(noall_rho) > 0.05:
            cls = "PARTIAL (survives NO-ALL only via pathway prior)"
        else:
            cls = "CONSTRUCTED (lost after label/proxy removal)"

        summary["classification"][s] = cls
        fr = f"{full_rho:+.3f}" if full_rho is not None else "  N/A"
        nr = f"{nosup_rho:+.3f}" if nosup_rho is not None else "  N/A"
        al = f"{noall_rho:+.3f}" if noall_rho is not None else "  N/A"
        print(f"  {s:30s}  FULL={fr}  NO-SUP={nr}  NO-ALL={al}  -> {cls}")

    out = RESULTS / "decircularization_biology.json"
    json.dump(summary, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n  -> {out}")


if __name__ == "__main__":
    main()
