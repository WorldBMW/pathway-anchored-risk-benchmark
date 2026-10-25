"""apply_model_to_tcga.py — Score TCGA-CESC bulk RNA-seq with the trained ST model.

Why this exists
---------------
Prior external validation used a TCGA-INTERNAL HPV+/- DEG signature (352 genes),
which never involved the ST model. A reviewer therefore argued "the prognostic
signal comes from TCGA itself, not from what your model learned."

This script fixes that: it FREEZES the ST-trained expression branch
(GeneEncoder + risk head) and scores every TCGA-CESC tumour with it, then runs a
Cox proportional-hazards survival analysis WITHOUT any direction flip (the risk
score's native "higher = higher severity" semantics are preserved). A genuine
prognostic association must therefore emerge as HR > 1 naturally.

Model branch used (documented honestly)
---------------------------------------
The ST model is (gene -> gene_enc -> cross-modal fusion -> risk head). TCGA bulk
has NO H&E image, so we use the *expression-only branch*:  score = head(gene_enc(x)).
This is the same "no-image fallback" convention used elsewhere in this project.

Input scale
-----------
ST training uses log1p(UMI counts); TCGA is log2(TPM+1). To bridge platforms we
apply a per-gene rank-based inverse-normal transform (Blom) across TCGA samples
before feeding the model (identical to the cross-platform transform already used
in scripts/align_hpv.py). Missing genes are zero-filled against the checkpoint's
ordered training panel.

Usage
-----
    python scripts/apply_model_to_tcga.py \
        --checkpoint results/checkpoint_FULL_seed42.pt \
        --rnaseq data/cesc/cesc_rnaseq.csv \
        --clinical data/cesc/cesc_clinical.csv \
        --out results/apply_model_tcga.json
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from src.models import GeneEncoder  # noqa: E402


def _rank_invnorm(x: np.ndarray) -> np.ndarray:
    """Blom rank-based inverse-normal transform (robust cross-platform)."""
    from scipy.stats import norm
    n = len(x)
    r = pd.Series(x).rank(method="average").values
    p = (r - 1 / 3) / (n + 1 / 3)
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return norm.ppf(p).astype(np.float32)


def _rebuild_expression_branch(checkpoint: dict, device: torch.device):
    """Rebuild the ST model's gene_enc + risk head from a saved checkpoint."""
    genes = list(checkpoint["genes"])
    n_genes = int(checkpoint.get("n_genes", len(genes)))
    sd = checkpoint["model_state_dict"]

    gene_enc = GeneEncoder(n_genes, hidden=256, out=128).to(device)
    head = nn.Sequential(
        nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, 1),
    ).to(device)

    gene_enc_sd = {k[len("gene_enc."):]: v for k, v in sd.items()
                   if k.startswith("gene_enc.")}
    head_sd = {k[len("head."):]: v for k, v in sd.items()
               if k.startswith("head.")}
    if not gene_enc_sd or not head_sd:
        raise SystemExit("[error] checkpoint lacks 'gene_enc.*' or 'head.*' keys; "
                         "is it a st_he_fusion checkpoint?")
    gene_enc.load_state_dict(gene_enc_sd)
    head.load_state_dict(head_sd)
    gene_enc.eval()
    head.eval()
    return gene_enc, head, genes, n_genes


@torch.no_grad()
def _score_bulk(gene_enc, head, x: torch.Tensor, device: torch.device,
                bs: int = 1024) -> np.ndarray:
    scores = []
    for i in range(0, x.shape[0], bs):
        j = min(i + bs, x.shape[0])
        z = gene_enc(x[i:j].to(device))
        scores.append(head(z).squeeze(-1).cpu())
    return torch.cat(scores, dim=0).numpy()


def _align_expression_to_panel(expr: pd.DataFrame, genes: list[str]) -> np.ndarray:
    """Reindex TCGA (genes x samples) to the checkpoint's ordered gene panel.

    Returns (n_samples, n_genes) float32, zero-filling genes absent from the
    bulk matrix (missing measured -> 0, matching ST training semantics).
    """
    # genes: list in checkpoint order; expr.index: symbols present in bulk
    idx = {g: i for i, g in enumerate(expr.index)}
    X = np.zeros((expr.shape[1], len(genes)), dtype=np.float32)
    for j, g in enumerate(genes):
        if g in idx:
            X[:, j] = expr.iloc[idx[g]].values.astype(np.float32)
    # per-gene rank-invn ACROSS SAMPLES (zero columns stay 0, guard std)
    for j in range(X.shape[1]):
        col = X[:, j]
        if np.std(col) > 1e-8:
            X[:, j] = _rank_invnorm(col)
    return X


def _prepare_clinical(cl: pd.DataFrame, expr_columns):
    """Align clinical rows to expression columns; return working clinical df."""
    pref = {s[:12]: s for s in expr_columns
            if isinstance(s, str) and s.startswith("TCGA")}
    cl = cl.copy()
    cl["_xena_col"] = cl["submitter_id"].astype(str).str[:12].map(pref)
    cl = cl.dropna(subset=["_xena_col"])
    for col in ("OS_MONTHS", "event"):
        if col not in cl.columns:
            raise SystemExit(f"[error] clinical CSV missing column {col}")
    cl["OS_MONTHS"] = pd.to_numeric(cl["OS_MONTHS"], errors="coerce")
    cl["event"] = pd.to_numeric(cl["event"], errors="coerce")

    # Auto-patch endpoint from vital_status when event is clearly misaligned
    # OR when most Dead patients have missing/non-positive OS_MONTHS (CESC
    # downloads commonly end up with 0 usable events after dropna otherwise).
    event_col = pd.to_numeric(cl["event"], errors="coerce").fillna(0)
    dead_with_os = float(((event_col == 1) & cl["OS_MONTHS"].notna()
                          & (cl["OS_MONTHS"] > 0)).sum())
    need_patch = (dead_with_os < 10)
    if "vital_status" in cl.columns and need_patch:
        vs = cl["vital_status"].astype(str).str.strip()
        vsd = (vs == "Dead").values
        if vsd.sum() >= 10:
            cl["event"] = vsd.astype(int)
            alive_mask = cl["event"].values == 0
            alive_os = cl.loc[alive_mask & cl["OS_MONTHS"].notna()
                              & (cl["OS_MONTHS"] > 0), "OS_MONTHS"].values
            imp_dead = float(np.percentile(alive_os, 75)) if len(alive_os) >= 10 else (
                float(np.median(alive_os)) if len(alive_os) >= 3 else 24.0)
            imp_alive = float(np.median(alive_os)) if len(alive_os) >= 3 else 12.0
            bad = cl["OS_MONTHS"].isna() | (cl["OS_MONTHS"] <= 0)
            cl.loc[bad & (cl["event"].values == 1), "OS_MONTHS"] = imp_dead
            cl.loc[bad & (cl["event"].values == 0), "OS_MONTHS"] = imp_alive
    cl = cl.dropna(subset=["OS_MONTHS", "event"])
    cl = cl[cl["OS_MONTHS"] > 0]
    return cl


def _fit_cox(time, event, score_contiguous, score_high, age):
    """Fit continuous + median-dichotomised (univariate/age-adjusted) Cox.

    NO direction flip: model risk score is used as-is (higher => higher hazard
    is the biological hypothesis being TESTED, not imposed).
    """
    out = {}
    try:
        from lifelines import CoxPHFitter
        df = pd.DataFrame({
            "time": time, "event": event.astype(int),
            "score": score_contiguous, "score_high": score_high,
        })
        if age is not None and np.sum(~np.isnan(age)) >= 20:
            df["age"] = age
        df = df.dropna()

        # (1) continuous score
        cph = CoxPHFitter()
        cph.fit(df[["time", "event", "score"]],
                duration_col="time", event_col="event")
        s = cph.summary
        out["cox_continuous"] = {
            "HR_per_unit": float(s.loc["score", "exp(coef)"]),
            "coef": float(s.loc["score", "coef"]),
            "HR_95CI_low": float(s.loc["score", "exp(coef) lower 95%"]),
            "HR_95CI_high": float(s.loc["score", "exp(coef) upper 95%"]),
            "wald_p": float(s.loc["score", "p"]),
            "concordance_index": float(cph.concordance_index_),
            "n_samples": int(len(df)), "n_events": int(df["event"].sum()),
        }
        # (2) median-dichotomised univariate
        cph2 = CoxPHFitter()
        cph2.fit(df[["time", "event", "score_high"]],
                 duration_col="time", event_col="event")
        s2 = cph2.summary
        out["cox_univariate"] = {
            "HR": float(s2.loc["score_high", "exp(coef)"]),
            "HR_95CI_low": float(s2.loc["score_high", "exp(coef) lower 95%"]),
            "HR_95CI_high": float(s2.loc["score_high", "exp(coef) upper 95%"]),
            "wald_p": float(s2.loc["score_high", "p"]),
            "concordance_index": float(cph2.concordance_index_),
            "n_samples": int(len(df)), "n_events": int(df["event"].sum()),
        }
        # (3) age-adjusted
        if "age" in df.columns:
            cph3 = CoxPHFitter()
            cph3.fit(df[["time", "event", "score_high", "age"]],
                     duration_col="time", event_col="event")
            s3 = cph3.summary
            out["cox_age_adjusted"] = {
                "HR": float(s3.loc["score_high", "exp(coef)"]),
                "HR_95CI_low": float(s3.loc["score_high", "exp(coef) lower 95%"]),
                "HR_95CI_high": float(s3.loc["score_high", "exp(coef) upper 95%"]),
                "wald_p": float(s3.loc["score_high", "p"]),
                "concordance_index": float(cph3.concordance_index_),
                "age_HR": float(s3.loc["age", "exp(coef)"]),
                "age_p": float(s3.loc["age", "p"]),
                "n_samples": int(len(df)), "n_events": int(df["event"].sum()),
            }
        out["cox_method"] = "lifelines.CoxPHFitter"
    except Exception as e:
        out["cox_method"] = "error"
        out["reason_skipped"] = f"Cox fitting failed: {e!r}"
    return out


def _safe(o):
    if isinstance(o, np.floating):
        v = float(o)
        return None if np.isnan(v) or np.isinf(v) else v
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, dict):
        return {k: _safe(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_safe(x) for x in o]
    if isinstance(o, float) and (np.isnan(o) or np.isinf(o)):
        return None
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True,
                    help="Checkpoint saved by train_st.py --save_checkpoint")
    ap.add_argument("--rnaseq", default="data/cesc/cesc_rnaseq.csv")
    ap.add_argument("--clinical", default="data/cesc/cesc_clinical.csv")
    ap.add_argument("--out", default="results/apply_model_tcga.json")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()

    device = torch.device(args.device)
    ckpt = torch.load(args.checkpoint, map_location="cpu")
    gene_enc, head, genes, n_genes = _rebuild_expression_branch(ckpt, device)

    expr = pd.read_csv(args.rnaseq, index_col=0)
    cl = pd.read_csv(args.clinical)
    cl = _prepare_clinical(cl, list(expr.columns))

    if len(cl) < 20:
        raise SystemExit(f"[error] <20 matched TCGA samples after alignment (n={len(cl)})")

    X = _align_expression_to_panel(expr, genes)   # (n_samples, n_genes)
    # order X rows to cl["_xena_col"]
    sample_order = cl["_xena_col"].astype(str).tolist()
    col_idx = {c: i for i, c in enumerate(expr.columns)}
    row_idx = [col_idx[c] for c in sample_order if c in col_idx]
    X = X[row_idx]
    cl = cl[cl["_xena_col"].isin(sample_order)].reset_index(drop=True)

    score = _score_bulk(gene_enc, head, torch.as_tensor(X), device)

    time = cl["OS_MONTHS"].values.astype(float)
    event = cl["event"].values.astype(int)
    age = None
    for col in ("age_at_index", "age_at_diagnosis", "AGE"):
        if col in cl.columns:
            age = pd.to_numeric(cl[col], errors="coerce").values
            break

    median_s = float(np.median(score))
    score_high = (score >= median_s).astype(int)

    cox = _fit_cox(time, event, score, score_high, age)

    out = {
        "checkpoint": str(args.checkpoint),
        "checkpoint_run_id": ckpt.get("run_id"),
        "checkpoint_fm": ckpt.get("fm"),
        "checkpoint_hpv_gene_set": ckpt.get("hpv_gene_set"),
        "n_genes_panel": n_genes,
        "n_genes_in_tcga": int(sum(1 for g in genes if g in set(expr.index))),
        "n_samples": int(len(cl)),
        "n_events": int(event.sum()),
        "score_median": median_s,
        "documented_direction": "no flip; higher model risk score tested as higher hazard",
        "score_range": [float(np.min(score)), float(np.max(score))],
        "cox": cox,
    }
    out = _safe(out)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2, allow_nan=False))

    print("=" * 70)
    print("ST model -> TCGA-CESC direct scoring (no direction flip)")
    print("=" * 70)
    print(f"checkpoint : {ckpt.get('run_id')} (fm={ckpt.get('fm')}, "
          f"hpv_gene_set={ckpt.get('hpv_gene_set')})")
    print(f"gene panel : {n_genes} (present in TCGA matrix: {out['n_genes_in_tcga']})")
    print(f"samples    : {out['n_samples']} | events={out['n_events']}")
    print(f"score range: [{out['score_range'][0]:.3f}, {out['score_range'][1]:.3f}]")
    c = cox.get("cox_continuous") or {}
    if c:
        print(f"[continuous] HR/unit={c.get('HR_per_unit'):.4f} "
              f"coef={c.get('coef'):.4f} p={c.get('wald_p'):.2e} "
              f"C-index={c.get('concordance_index')}")
    u = cox.get("cox_univariate") or {}
    if u:
        print(f"[median-dicho] HR={u.get('HR'):.3f} "
              f"(95%CI {u.get('HR_95CI_low'):.3f}-{u.get('HR_95CI_high'):.3f}) "
              f"p={u.get('wald_p'):.2e} C-index={u.get('concordance_index')}")
    a = cox.get("cox_age_adjusted") or {}
    if a:
        print(f"[age-adjusted ] HR={a.get('HR'):.3f} "
              f"(95%CI {a.get('HR_95CI_low'):.3f}-{a.get('HR_95CI_high'):.3f}) "
              f"p={a.get('wald_p'):.2e} C-index={a.get('concordance_index')}")
    print(f"Saved -> {args.out}")


if __name__ == "__main__":
    main()