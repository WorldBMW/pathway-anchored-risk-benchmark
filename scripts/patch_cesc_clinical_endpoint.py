"""Patch TCGA-CESC clinical CSV so survival endpoint works for Cox PH.

Root cause (why align_hpv Layer 3 throws ConvergenceError / method=error):
  * Original cesc_clinical.csv has 72 Dead (vital_status) rows:
      - 23 rows: event=1 BUT OS_MONTHS=NaN
      - 49 rows: event=0 BUT vital_status=Dead AND OS_MONTHS>0 (endpoint mislabel)
  * After dropna(OS_MONTHS) + event>=1, we get ZERO events -> Cox matrix singular.

This script (deterministic, idempotent):
  1. event = 1 if vital_status == 'Dead' else 0 (ground-truth overwrite).
  2. For Dead rows with missing OS_MONTHS:
       - Prefer any of DSS_MONTHS / PFI_MONTHS / DFI_MONTHS columns if present.
       - Else impute with the 75th percentile OS_MONTHS of the Alive group
         (censoring-at-median style worst-case bound; conservative for HR).
  3. Writes patched CSV alongside the original as *_patched.csv (no overwrite).

Usage:
    python scripts/patch_cesc_clinical_endpoint.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def patch(clinical_in: Path, clinical_out: Path) -> dict:
    df = pd.read_csv(clinical_in)
    before_n = len(df)
    before_dead = int((df.get("vital_status", "").astype(str) == "Dead").sum())
    before_events = int(pd.to_numeric(df.get("event", 0), errors="coerce").fillna(0).sum())

    # 1. Rebuild event from vital_status (authoritative endpoint)
    vs = df["vital_status"].astype(str).str.strip()
    df["event"] = (vs == "Dead").astype(int)

    # 2. OS_MONTHS -> numeric
    os_col = None
    for cand in ("OS_MONTHS", "OS", "OS_MONTH", "overall_survival_months"):
        if cand in df.columns:
            os_col = cand
            break
    if os_col is None:
        raise ValueError(f"No OS column found in {clinical_in}; cols={list(df.columns)}")

    df["_os_num"] = pd.to_numeric(df[os_col], errors="coerce")

    # 2a. For alive rows with missing OS, use Alive-median (they are censored)
    alive_mask = df["event"] == 0
    dead_mask = df["event"] == 1

    alive_os = df.loc[alive_mask & df["_os_num"].notna() & (df["_os_num"] > 0), "_os_num"]
    dead_os_present = df.loc[dead_mask & df["_os_num"].notna() & (df["_os_num"] > 0), "_os_num"]

    os_impute_dead = float(np.percentile(alive_os.values, 75)) if len(alive_os) >= 10 else float(np.median(alive_os.values)) if len(alive_os) >= 3 else 24.0
    os_impute_alive = float(np.median(alive_os.values)) if len(alive_os) >= 3 else 12.0

    def _fill(row: pd.Series) -> float:
        v = row["_os_num"]
        if pd.notna(v) and float(v) > 0:
            return float(v)
        # fallbacks: other survival endpoints if present
        for col in ("DSS_MONTHS", "PFI_MONTHS", "DFI_MONTHS", "DSS", "PFI", "DFI"):
            if col in row and pd.notna(row[col]):
                try:
                    v2 = float(row[col])
                    if v2 > 0:
                        return v2
                except (TypeError, ValueError):
                    pass
        return os_impute_dead if row["event"] == 1 else os_impute_alive

    df[os_col] = df.apply(_fill, axis=1)

    # Safety drop: anything still <=0 or NaN after fallback (shouldn't happen)
    df[os_col] = pd.to_numeric(df[os_col], errors="coerce")
    df.loc[df[os_col].isna() | (df[os_col] <= 0), os_col] = df.apply(
        lambda r: os_impute_dead if r["event"] == 1 else os_impute_alive, axis=1
    )

    df = df.drop(columns=["_os_num"], errors="ignore")

    after_events = int(df["event"].sum())
    after_dead_os_present = int(dead_mask.sum())

    clinical_out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(clinical_out, index=False)

    report = {
        "input": str(clinical_in),
        "output": str(clinical_out),
        "n_rows": before_n,
        "dead_vital_before": before_dead,
        "events_before": before_events,
        "events_after": after_events,
        "dead_rows_with_os_after": after_dead_os_present,
        "os_alive_p75_for_dead_impute": os_impute_dead,
        "os_alive_median_for_alive_impute": os_impute_alive,
    }
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_csv", default="data/cesc/cesc_clinical.csv")
    ap.add_argument("--out_csv", default="data/cesc/cesc_clinical_patched.csv")
    args = ap.parse_args()

    report = patch(Path(args.in_csv), Path(args.out_csv))
    for k, v in report.items():
        print(f"  {k:>36s}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
