#!/usr/bin/env python
"""
tcga_deg_cox.py — 11 个空间识别 DEG 在 TCGA-CESC 的逐基因单因素 Cox 生存分析

为什么存在（CSBJ 改造方案 ③d）：
  把"空间识别的基因"和"临床生存"建立最低限度的生物学关联，作为下游可解释性证据。
  严格边界（写进论文措辞，不可越界）：
    - 只陈述"部分空间识别 DEG 与 bulk 生存存在单基因关联"；
    - 严禁表述"模型风险分数可预测 bulk 生存"（模型分数是 spot 级、TCGA 是 bulk 级，
      二者不可直接对齐，强行对齐即数据泄漏/口径错误）。

输入：
  data/cesc/cesc_rnaseq.csv            (gene x sample，log 或 counts，脚本内标准化)
  data/cesc/cesc_clinical_patched.csv  (OS_MONTHS, event)
  11 个 DEG 来自 results/align_hpv_cervix35.json: layer3_cox.signature_genes

输出：
  results/tcga_deg_cox.json   每个基因：HR / 95%CI / Wald p / n / events / BH校正p

用法：
  python scripts/tcga_deg_cox.py
  python scripts/tcga_deg_cox.py --deg_json results/align_hpv_cervix35.json
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

# Fallback DEG list (verified present in cesc_rnaseq.csv, all up-regulated).
DEFAULT_DEGS = ["KRT5", "B2M", "HLA-A", "KRT14", "HLA-C", "KRT19",
                "PSME2", "CCND1", "KRT17", "PTEN", "PSMB8"]


def load_degs(deg_json: Path) -> list[str]:
    """Pull the 11-DEG signature from the alignment JSON if available."""
    try:
        d = json.load(open(deg_json, encoding="utf-8"))
        sig = d["layer3_cox"]["signature_genes"]          # [[gene, dir], ...]
        genes = [g for g, _ in sig]
        print(f"[deg] loaded {len(genes)} DEG from {deg_json.name}: {genes}")
        return genes
    except Exception as e:
        print(f"[deg] could not read {deg_json} ({e}); using built-in list")
        return DEFAULT_DEGS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--expr", default=str(ROOT / "data/cesc/cesc_rnaseq.csv"))
    ap.add_argument("--clin", default=str(ROOT / "data/cesc/cesc_clinical_patched.csv"))
    ap.add_argument("--deg_json", default=str(RESULTS / "align_hpv_cervix35.json"))
    ap.add_argument("--out", default=str(RESULTS / "tcga_deg_cox.json"))
    ap.add_argument("--min_expr_log", type=float, default=1.0,
                    help="drop genes whose mean log-expression is below this (uninformative)")
    args = ap.parse_args()

    try:
        from lifelines import CoxPHFitter
    except ImportError:
        print("[FAIL] lifelines not installed -> pip install lifelines"); sys.exit(1)

    degs = load_degs(Path(args.deg_json))

    # ---- expression: gene x sample -> sample x gene ----
    ex = pd.read_csv(args.expr)
    idcol = ex.columns[0]
    ex = ex.set_index(idcol)
    print(f"[expr] matrix {ex.shape[0]} genes x {ex.shape[1]} samples")
    missing = [g for g in degs if g not in ex.index]
    if missing:
        print(f"[expr] WARNING DEG not in matrix (skipped): {missing}")
    ex = ex.loc[[g for g in degs if g in ex.index]]
    # log2 CPM-style transform if data look like counts; if already log, this is idempotent-ish
    X = ex.astype(float)
    if X.values.min() < 0:
        print("[expr] negative values -> assume already log-transformed")
    else:
        print("[expr] non-negative -> applying log2(1+x)")
        X = np.log2(1.0 + X)
    X = X.T  # samples x genes

    # ---- clinical ----
    cl = pd.read_csv(args.clin)
    cl = cl[["patient_id", "OS_MONTHS", "event"]].dropna()
    cl["patient_id"] = cl["patient_id"].astype(str)
    cl["OS_MONTHS"] = pd.to_numeric(cl["OS_MONTHS"], errors="coerce")
    cl["event"] = pd.to_numeric(cl["event"], errors="coerce")
    cl = cl.dropna()
    # X is samples x genes here (index = full barcode). Keep PRIMARY TUMOR
    # aliquots only (suffix -01) and collapse to one row per patient: the raw
    # matrix has 308 columns but 303 patients, and the 5 duplicated patients
    # carry a second aliquot (-11/-06) that would break the survival join.
    bc = pd.Series(X.index.astype(str), index=X.index)
    prim = bc[bc.str.endswith("-01")].index
    X = X.loc[prim]
    print(f"[expr] primary-tumor (-01) samples kept={len(X)}")
    patient = pd.Series([str(b)[:12] for b in X.index], index=X.index)
    X = X.groupby(patient.values).mean()     # one row per patient
    print(f"[expr] collapsed to unique patients={X.shape[0]}")
    common = X.index.intersection(cl["patient_id"])
    X = X.loc[common]
    cl = cl.set_index("patient_id").loc[common]
    print(f"[align] {len(common)} samples with both expression + survival "
          f"(events={int(cl['event'].sum())})")

    # z-score each gene so HR is per-SD (interpretable, comparable across genes)
    Z = (X - X.mean()) / (X.std(ddof=0).replace(0, np.nan))
    Z = Z.dropna(axis=1)

    rows = []
    for g in Z.columns:
        df = pd.DataFrame({"T": cl["OS_MONTHS"].values,
                           "E": cl["event"].values,
                           "x": Z[g].values})
        df = df.replace([np.inf, -np.inf], np.nan).dropna()
        if df["x"].std() < 1e-8:
            continue
        cph = CoxPHFitter()
        try:
            cph.fit(df, duration_col="T", event_col="E")
            s = cph.summary.loc["x"]
            rows.append({
                "gene": g,
                "HR_per_SD": float(np.exp(s["coef"])),
                "CI_low": float(np.exp(s["coef lower 95%"])),
                "CI_high": float(np.exp(s["coef upper 95%"])),
                "wald_p": float(s["p"]),
                "n": int(len(df)),
                "events": int(df["E"].sum()),
            })
            flag = " *" if s["p"] < 0.05 else ""
            print(f"  {g:8s} HR={np.exp(s['coef']):.3f} "
                  f"[{np.exp(s['coef lower 95%']):.2f},{np.exp(s['coef upper 95%']):.2f}] "
                  f"p={s['p']:.3g}{flag}")
        except Exception as e:
            print(f"  {g:8s} FAILED: {e}")

    # ---- Benjamini-Hochberg FDR across the 11 tests ----
    from statsmodels.stats.multitest import multipletests
    if rows:
        pvals = [r["wald_p"] for r in rows]
        try:
            _, q, _, _ = multipletests(pvals, method="fdr_bh")
            for r, qq in zip(rows, q):
                r["BH_q"] = float(qq)
        except Exception:
            for r in rows:
                r["BH_q"] = None

    n_sig_raw = sum(1 for r in rows if r["wald_p"] < 0.05)
    n_sig_fdr = sum(1 for r in rows if r.get("BH_q") is not None and r["BH_q"] < 0.05)
    out = {
        "generated": pd.Timestamp.now().isoformat(),
        "cohort": "TCGA-CESC",
        "method": "per-gene univariate Cox, expression z-scored (HR = per 1 SD)",
        "n_tests": len(rows),
        "n_significant_raw_p05": n_sig_raw,
        "n_significant_BH_q05": n_sig_fdr,
        "interpretation_guardrail": (
            "Single-gene association only. This does NOT validate the model's "
            "spot-level risk score for bulk survival; do not phrase it that way."),
        "per_gene": sorted(rows, key=lambda r: r["wald_p"]),
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("=" * 60)
    print(f"raw p<0.05: {n_sig_raw}/{len(rows)}    BH q<0.05: {n_sig_fdr}/{len(rows)}")
    print(f"saved -> {args.out}")
    if n_sig_fdr == 0:
        print("[NOTE] no gene survives FDR -> report as descriptive trend only "
              "(consistent with the known 11-DEG bulk Cox being non-significant).")


if __name__ == "__main__":
    main()
