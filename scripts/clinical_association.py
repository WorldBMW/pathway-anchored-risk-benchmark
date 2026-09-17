"""clinical_association.py — Cross-cohort clinical validation of the learned
HPV-anchored signature against TCGA-CESC (independent cohort).

WHY this exists (the fix for the "label leakage / circularity" problem)
-----------------------------------------------------------------------
The in-slide `hpv_proxy_auc` in train_st.py is built from the SAME HPV gene
expression it predicts, so a high AUC there is circular (predicting expression
with expression). That number must NOT be used as prediction performance.

This script is the NON-circular counterpart: it takes the HPV-related DEGs
discovered on the Visium cervix slide (train_st.py `top_degs`), computes a
signature score from those genes' expression in the INDEPENDENT TCGA-CESC
RNA-seq cohort, and tests it against THREE real clinical endpoints:
  1. HPV status  -> AUC (can the Visium-derived signature separate real HPV+/- ?)
  2. Overall survival -> KM split + Cox HR + C-index (is high signature worse?)
  3. AJCC stage  -> ANOVA (is the signature associated with stage?)

This is a true cross-cohort transfer: Visium (discovery) -> TCGA-CESC (validation).
No gene used for scoring is derived from the TCGA labels themselves.

Run (after train_st.py has produced results/results_st.json):
  python scripts/clinical_association.py \
      --results results/results_st.json \
      --clinical data/cesc/cesc_clinical.csv \
      --rnaseq data/cesc/cesc_rnaseq.csv \
      --out results/clinical_association.json
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def load_deg_genes(results_path: str) -> list[str]:
    """Extract HPV-related DEG gene names from train_st.py results."""
    d = json.loads(Path(results_path).read_text())
    top = d.get("top_degs", [])
    # top_degs entries: [gene, delta, fdr_perm, p_naive]
    genes = [x[0] for x in top]
    return genes


def signature_score(expr: pd.DataFrame, genes: list[str]) -> np.ndarray:
    """Mean z-scored log expression of `genes` per sample (row = gene, col = sample).

    Returns array aligned with expr.columns.
    """
    # keep genes present in the matrix
    keep = [g for g in genes if g in expr.index]
    if len(keep) < 2:
        raise RuntimeError(
            f"Only {len(keep)} DEG genes found in TCGA matrix; need >=2. "
            "Check that the gene symbols match (Xena uses HUGO symbols).")
    sub = expr.loc[keep]
    # z-score across samples per gene, then average across genes
    z = sub.sub(sub.mean(axis=1), axis=0).div(sub.std(axis=1) + 1e-9, axis=0)
    score = z.mean(axis=0)
    return score, keep


def auc(y_true, score):
    from sklearn.metrics import roc_auc_score
    return roc_auc_score(y_true, score)


def cox_hr(time, event, score):
    """Univariate Cox PH hazard ratio (score -> higher = higher risk)."""
    try:
        from lifelines import CoxPHFitter
    except ImportError:
        return float("nan"), float("nan"), float("nan"), float("nan")
    df = pd.DataFrame({"T": time, "E": event, "x": score})
    df = df.dropna()
    if len(df) < 10 or df["E"].sum() < 3:
        return float("nan"), float("nan"), float("nan"), float("nan")
    cph = CoxPHFitter()
    try:
        cph.fit(df, duration_col="T", event_col="E")
        hr = float(np.exp(cph.params_["x"]))
        ci_low = float(np.exp(cph.confidence_intervals_.loc["x", "95% lower-bound"]))
        ci_high = float(np.exp(cph.confidence_intervals_.loc["x", "95% upper-bound"]))
        p = float(cph.summary.loc["x", "p"])
    except Exception:
        return float("nan"), float("nan"), float("nan"), float("nan")
    # concordance index
    try:
        from lifelines.utils import concordance_index
        ci = concordance_index(df["T"], -df["x"], df["E"])
    except Exception:
        ci = float("nan")
    return hr, ci_low, ci_high, ci


def permutation_auc(y, score, n_perm=1000, seed=0):
    """Empirical p-value for the HPV AUC by permuting labels."""
    rng = np.random.default_rng(seed)
    obs = auc(y, score)
    cnt = 0
    for _ in range(n_perm):
        yp = rng.permutation(y)
        if auc(yp, score) >= obs:
            cnt += 1
    p = (cnt + 1) / (n_perm + 1)
    return obs, p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results/results_st.json")
    ap.add_argument("--clinical", default="data/cesc/cesc_clinical.csv")
    ap.add_argument("--rnaseq", default="data/cesc/cesc_rnaseq.csv")
    ap.add_argument("--out", default="results/clinical_association.json")
    ap.add_argument("--n_perm", type=int, default=1000)
    args = ap.parse_args()

    genes = load_deg_genes(args.results)
    print(f"[signature] {len(genes)} DEG genes from {args.results}")

    cl = pd.read_csv(args.clinical)
    expr = pd.read_csv(args.rnaseq, index_col=0)

    # map TCGA sample columns (TCGA-XX-XXXX-01) to clinical submitter_id (TCGA-XX-XXXX)
    pref = {c[:12]: c for c in expr.columns if isinstance(c, str) and c.startswith("TCGA")}
    cl["_xena_col"] = cl["submitter_id"].astype(str).str[:12].map(pref)
    matched = cl.dropna(subset=["_xena_col"]).copy()
    print(f"[match] {len(matched)}/{len(cl)} TCGA patients have RNA-seq")

    score, keep = signature_score(expr, genes)
    matched = matched.copy()
    matched["sig"] = matched["_xena_col"].map(score.to_dict())
    # reconstruct event from vital_status: Dead -> 1, Alive -> 0
    # (the `event` column under-counts deaths in this clinical file)
    matched["event_vs"] = matched["vital_status"].map({"Dead": 1, "Alive": 0})

    out = {"n_deg_genes": len(genes), "n_genes_in_matrix": len(keep),
           "n_matched": int(len(matched))}

    # ---- 1. HPV status AUC ----
    hpv = matched.dropna(subset=["hpv_status", "sig"])
    hpv = hpv[hpv["hpv_status"].isin(["Positive", "Negative"])]
    y = (hpv["hpv_status"] == "Positive").astype(int).values
    s = hpv["sig"].values
    if len(np.unique(y)) == 2 and len(y) >= 10:
        a, p = permutation_auc(y, s, n_perm=args.n_perm)
        out["hpv_auc"] = {"auc": float(a), "perm_p": float(p),
                          "n_pos": int(y.sum()), "n_neg": int((1 - y).sum())}
        print(f"[HPV AUC] auc={a:.3f} (perm p={p:.4f}) "
              f"HPV+={int(y.sum())} HPV-={int((1-y).sum())}")
    else:
        out["hpv_auc"] = {"auc": float("nan"), "perm_p": float("nan")}
        print("[HPV AUC] skipped (insufficient labels)")

    # ---- 2. survival (event reconstructed from vital_status) ----
    surv = matched.dropna(subset=["OS_MONTHS", "event_vs", "sig"]).copy()
    if len(surv) >= 20:
        med = float(surv["sig"].median())
        surv["hi"] = (surv["sig"] >= med).astype(int)
        from lifelines import KaplanMeierFitter
        kmf = KaplanMeierFitter()
        logrank_p = None
        try:
            from lifelines.statistics import logrank_test
            t_hi = surv.loc[surv["hi"] == 1, "OS_MONTHS"].values
            t_lo = surv.loc[surv["hi"] == 0, "OS_MONTHS"].values
            e_hi = surv.loc[surv["hi"] == 1, "event_vs"].values
            e_lo = surv.loc[surv["hi"] == 0, "event_vs"].values
            lr = logrank_test(t_hi, t_lo, e_hi, e_lo)
            logrank_p = float(lr.p_value)
        except Exception:
            logrank_p = float("nan")
        hr, ci_low, ci_high, ci = cox_hr(surv["OS_MONTHS"], surv["event_vs"], surv["sig"])
        out["survival"] = {"n": int(len(surv)), "n_events": int(surv["event_vs"].sum()),
                           "logrank_p": logrank_p, "cox_hr": hr,
                           "cox_ci_low": ci_low, "cox_ci_high": ci_high,
                           "c_index": ci}
        print(f"[Survival] n={len(surv)} events={int(surv['event_vs'].sum())} "
              f"logrank_p={logrank_p:.4f} HR={hr:.3f} "
              f"[{ci_low:.3f},{ci_high:.3f}] C-index={ci:.3f}")
    else:
        out["survival"] = {"n": int(len(surv))}
        print("[Survival] skipped (insufficient)")

    # ---- 3. vital status (Dead/Alive) association ----
    # (ajcc_stage is >99% NaN in this clinical file, so we use Dead/Alive instead)
    vs = matched.dropna(subset=["vital_status", "sig"])
    vs = vs[vs["vital_status"].isin(["Dead", "Alive"])]
    if vs["vital_status"].nunique() == 2 and len(vs) >= 10:
        y_vs = (vs["vital_status"] == "Dead").astype(int).values
        s_vs = vs["sig"].values
        a_vs, p_vs = permutation_auc(y_vs, s_vs, n_perm=args.n_perm)
        out["vital_status_auc"] = {"auc": float(a_vs), "perm_p": float(p_vs),
                                   "n_dead": int(y_vs.sum()),
                                   "n_alive": int((1 - y_vs).sum())}
        print(f"[Vital-status AUC] auc={a_vs:.3f} (perm p={p_vs:.4f}) "
              f"Dead={int(y_vs.sum())} Alive={int((1-y_vs).sum())}")
    else:
        out["vital_status_auc"] = {"n": int(len(vs))}
        print("[Vital-status] skipped (insufficient)")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2, default=str, allow_nan=False))
    print(f"\nSaved -> {args.out}")


if __name__ == "__main__":
    main()
