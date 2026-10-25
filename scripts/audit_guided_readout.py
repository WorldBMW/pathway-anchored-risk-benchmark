#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Audit-guided decircularized readout vs the supervised score, on the
independent GeoMx cohort (GSE316098).

Motivation (the "advance" the editors asked for)
------------------------------------------------
The MRP-ST audit certifies WHICH pathway programs survive supervision removal
("REAL (survives NO-SUP)"). If the audit is useful, then a LABEL-FREE readout
built from exactly those certified programs should transfer to an independent
platform at least as well as the supervised risk head -- i.e. the audit does not
merely say "do not trust this score", it tells you what to build the score from.

Design (all CPU, no training, no supervision):
  S_FULL : the frozen supervised risk head scored on GeoMx ROIs
           (results/external_gse316098_validation.json)          [baseline]
  S_dec  : rank-enrichment of the audit-certified REAL programs on GeoMx
           expression only, signed by the NO-SUP rho direction, z-combined
           [audit-guided correction]
Evaluate both on the same labels (GEO SOFT 'silva pattern'): benign vs tumour,
ROI-level AUC + Mann-Whitney, and within-patient paired Wilcoxon.

Writes results/audit_guided_readout_geomx.json
"""
from __future__ import annotations
import gzip, json, re, sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, rankdata, wilcoxon

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from src.downstream_genes import all_gene_sets          # noqa: E402
from downstream_spot_analysis import rank_enrichment     # noqa: E402

GEO = ROOT / "data" / "st_visium" / "geo_cervical_geomx_GSE316098"
COUNTS = GEO / "GSE316098_raw.counts.linear.formatted.csv.gz"
SOFT = GEO / "GSE316098_family.soft.gz"
FULL_JSON = ROOT / "results" / "external_gse316098_validation.json"
DEC_JSON = ROOT / "results" / "decircularization_biology.json"
OUT = ROOT / "results" / "audit_guided_readout_geomx.json"


def auc(a, b):
    """AUC of a (> b) via the Mann-Whitney rank statistic; ties -> average ranks."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    r = rankdata(np.concatenate([a, b]))
    r1 = r[:len(a)].sum()
    u1 = r1 - len(a) * (len(a) + 1) / 2.0
    return float(u1 / (len(a) * len(b)))


def main():
    # ---- audit certificate: which programs survive supervision removal, and with what sign
    dec = json.load(open(DEC_JSON, encoding="utf-8"))
    nosup = dec["variants"]["NOSUP"]
    cert = {s: v["rho_mean"] for s, v in nosup.items() if v.get("rho_mean") is not None}
    real_sets = [s for s, r in cert.items() if abs(r) > 0.05]
    print("Audit-certified REAL programs (|rho_NO-SUP| > 0.05):")
    for s in real_sets:
        print(f"  {s:34s} rho_NO-SUP={cert[s]:+.3f}  -> {dec['classification'].get(s)}")
    if not real_sets:
        raise SystemExit("[abort] no certified REAL programs in decircularization_biology.json")

    # ---- labels from GEO SOFT (the ROI name prefix is a TMA core id, NOT the pattern)
    soft = gzip.open(SOFT, "rt", encoding="utf-8", errors="replace").read()
    rows = []
    for blk in soft.split("^SAMPLE =")[1:]:
        t = re.search(r"!Sample_title\s*=\s*(\S+)", blk)

        def char(key):
            m = re.search(r"!Sample_characteristics_ch1\s*=\s*%s:\s*(.+)" % key, blk)
            return m.group(1).strip() if m else None
        if t:
            rows.append(dict(roi=t.group(1).strip(), silva=char("silva pattern"),
                             risk=char("risk"), caseid=char("caseid")))
    meta = pd.DataFrame(rows)

    # ---- expression -> label-free readout
    expr = pd.read_csv(COUNTS).rename(columns={"Unnamed: 0": "gene"}).set_index("gene")
    expr.columns = [c.replace("1b-1.", "1b.1.") for c in expr.columns]
    rois = list(expr.columns)
    gene_names = list(expr.index)
    X = np.log1p(expr[rois].T.values.astype(np.float32))     # (n_roi, n_gene)

    gs = all_gene_sets()
    subset = {s: gs[s] for s in real_sets if s in gs}
    enr, names = rank_enrichment(X, subset, gene_names)
    Z = (enr - enr.mean(0)) / (enr.std(0) + 1e-9)
    signs = np.array([np.sign(cert[s]) or 1.0 for s in names])
    s_dec = Z @ signs
    print(f"\nreadout: {len(names)} certified sets, signs={dict(zip(names, signs))}")

    # ---- sensitivity: alternative constructions of the same label-free readout
    absr = np.array([abs(cert[s]) for s in names])
    cand = {
        "dec_signsum": s_dec,
        "dec_rho_weighted": Z @ (signs * absr),
        "dec_top2": Z[:, np.argsort(-absr)[:2]] @ signs[np.argsort(-absr)[:2]],
        "dec_epithelial_only": Z[:, names.index("CELL_tumor_epithelial")],
    }

    # ---- supervised baseline
    g = json.load(open(FULL_JSON, encoding="utf-8"))
    sc = pd.DataFrame(g["per_roi"])
    sc["roi"] = sc["roi"].str.replace(r"^1b-1\.", "1b.1.", regex=True)

    df = pd.DataFrame({"roi": rois, **cand}).merge(sc[["roi", "score"]], on="roi", how="left")
    df = df.rename(columns={"score": "s_full"}).merge(meta, on="roi", how="left")
    assert df["silva"].notna().all(), "unlabeled ROIs after join"
    assert df["s_full"].notna().all(), "missing supervised scores after join"
    df["is_tumor"] = df["silva"].isin(["A", "B", "C"])
    df["core"] = df["roi"].str.rsplit(".", n=1).str[0]

    T, N = df.loc[df.is_tumor], df.loc[~df.is_tumor]

    # ---- within-patient paired (core level, patients carrying both)
    cols = ["s_full"] + list(cand)
    core = df.groupby(["core", "caseid", "is_tumor"], as_index=False)[cols].mean()
    pm = core.pivot_table(index="caseid", columns="is_tumor", values=cols)
    res = {}
    for name, col in [("S_full", "s_full")] + [(k, k) for k in cand]:
        a, b = T[col].values, N[col].values
        a_auc = auc(a, b)
        p_roi = float(mannwhitneyu(a, b, alternative="two-sided").pvalue)
        try:
            tv, nv = pm[(col, True)].dropna(), pm[(col, False)].dropna()
            idx = tv.index.intersection(nv.index)
            wp = float(wilcoxon(tv[idx], nv[idx]).pvalue)
            frac = float((tv[idx] > nv[idx]).mean())
        except Exception:
            wp, frac = None, None
        res[name] = {"auc_tumor_vs_benign": a_auc, "mwu_p_roi": p_roi,
                     "within_patient_wilcoxon_p": wp, "within_patient_frac_tumor_higher": frac}
        sup = "supervised" if name == "S_full" else "label-free"
        print(f"{name:22s} [{sup:11s}] AUC={a_auc:.3f}  ROI p={p_roi:.2e}  "
              f"paired p={wp if wp is None else round(wp,4)}  frac={frac}")

    base = res["S_full"]["auc_tumor_vs_benign"]
    best_dec = max((v["auc_tumor_vs_benign"], k) for k, v in res.items() if k != "S_full")

    out = {
        "dataset": "GSE316098 (GeoMx, independent platform)",
        "certified_programs": {s: {"rho_NO_SUP": cert[s], "sign_used": float(np.sign(cert[s]) or 1.0),
                                   "classification": dec["classification"].get(s)} for s in names},
        "n_rois": int(len(df)), "n_benign": int(len(N)), "n_tumor": int(len(T)),
        "n_patients_paired": int(len(pm.index)),
        "scores": res,
        "baseline_auc_supervised": base,
        "best_label_free_readout": {"name": best_dec[1], "auc": best_dec[0]},
        "delta_auc_best_dec_minus_full": best_dec[0] - base,
        "interpretation": ("Label-free readouts built ONLY from audit-certified programs are "
                           "evaluated against the supervised head on an independent platform. "
                           "A non-negative delta_AUC would support an audit-guided performance gain; "
                           "a negative delta means the audit does not yield a better predictor here."),
    }
    json.dump(out, open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"\nbest label-free readout: {best_dec[1]}  AUC={best_dec[0]:.3f}  "
          f"vs supervised {base:.3f}  -> delta_AUC={best_dec[0] - base:+.3f}")
    print("wrote", OUT)


if __name__ == "__main__":
    main()