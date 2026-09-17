#!/usr/bin/env python
"""
validate_markers_scrna.py — validate the cell-type marker sets in
src/downstream_genes.py against the cervical scRNA-seq reference
GSE308792 (31,002 cells, integrated gene×cell matrix).

Why: the microenvironment analysis uses curated markers to score Visium spots.
Before trusting those scores we confirm, on real single-cell data, that (a) the
markers of each lineage co-vary (within-set coherence) and (b) distinct lineages
are anti-correlated / separable (specificity) — i.e. the markers are not just
picking up a shared housekeeping / library-size signal.

No clustering or cell-type annotation is required (the reference ships none);
we use rank-based per-cell lineage scores and inspect their correlation
structure and dominant-lineage assignments.

Run (local, no GPU):
  python scripts/validate_markers_scrna.py
Output: results/scrna_marker_validation.json
"""
from __future__ import annotations
import json, sys, gzip
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.downstream_genes import CELL_MARKERS  # noqa: E402

DATA = ROOT / "data/scrna_cervical_GSE308792/GSE308792_Integrated_gene_expression.csv.gz"


def rank_score(X: np.ndarray, idx_per_set: dict):
    """X = (cells, genes) log/normalised expression. Mean-rank enrichment per set."""
    n, g = X.shape
    order = X.argsort(axis=1)
    ranks = np.empty_like(order, dtype=np.float64)
    rr = np.arange(g)
    for i in range(n):
        ranks[i, order[i]] = rr + 1.0
    names = list(idx_per_set.keys())
    S = np.zeros((n, len(names)))
    for k, nm in enumerate(names):
        S[:, k] = ranks[:, idx_per_set[nm]].mean(axis=1) / g - 0.5
    return S, names


def main():
    if not DATA.exists():
        print(f"[FAIL] {DATA} not found"); sys.exit(1)
    print(f"loading {DATA.name} (this is ~1 GB, ~30-60 s) ...")
    df = pd.read_csv(DATA, index_col=0)
    df = df[~df.index.duplicated(keep="first")]
    print(f"  matrix: {df.shape[0]} genes x {df.shape[1]} cells")

    # keep only marker genes present
    sets = {}
    for ct, genes in CELL_MARKERS.items():
        present = [g for g in genes if g in df.index]
        sets[ct] = present
        print(f"  {ct:16s} {len(present)}/{len(genes)} markers present")

    use_genes = sorted({g for v in sets.values() for g in v})
    X = df.loc[use_genes].T.astype(np.float32)          # cells x marker-genes
    # log1p if counts-like
    if X.values.min() >= 0 and X.values.max() > 50:
        X = np.log1p(X)
    X = X.values
    gidx = {g: j for j, g in enumerate(use_genes)}
    idx_per_set = {ct: [gidx[g] for g in genes] for ct, genes in sets.items()
                   if len([g for g in genes]) >= 3}

    S, names = rank_score(X, idx_per_set)              # (cells, lineages)

    # --- 1. within-set gene coherence vs between-set (gene-gene correlations) ---
    Xz = (X - X.mean(0)) / (X.std(0) + 1e-9)
    gene_corr = np.corrcoef(Xz, rowvar=False)
    within, between = [], []
    gene_to_set = {}
    for ct, genes in idx_per_set.items():
        for gi in genes:
            gene_to_set[gi] = ct
    allidx = list(gene_to_set.keys())
    for a_i, a in enumerate(allidx):
        for b in allidx[a_i + 1:]:
            c = gene_corr[a, b]
            (within if gene_to_set[a] == gene_to_set[b] else between).append(c)
    within = np.array(within); between = np.array(between)

    # --- 2. lineage-score correlation matrix (specificity) ---
    Sz = (S - S.mean(0)) / (S.std(0) + 1e-9)
    lin_corr = np.corrcoef(Sz, rowvar=False)

    # --- 3. dominant lineage assignment + per-sample composition ---
    dom = np.argmax(S, axis=1)
    cell_cols = df.columns.astype(str)
    sample = np.array([c.split("-")[-1] for c in cell_cols])
    comp = {}
    for s in np.unique(sample):
        m = sample == s
        comp[f"sample_{s}"] = {names[k]: int((dom[m] == k).sum()) for k in range(len(names))}
        tot = m.sum()
        comp[f"sample_{s}"]["total_cells"] = int(tot)

    out = {
        "reference": "GSE308792 integrated cervical scRNA-seq",
        "n_cells": int(X.shape[0]),
        "n_marker_genes_used": int(X.shape[1]),
        "within_set_gene_corr_mean": float(np.nanmean(within)),
        "between_set_gene_corr_mean": float(np.nanmean(between)),
        "coherence_minus_between": float(np.nanmean(within) - np.nanmean(between)),
        "lineage_score_corr": {names[i]: {names[j]: round(float(lin_corr[i, j]), 3)
                                          for j in range(len(names))}
                               for i in range(len(names))},
        "dominant_lineage_overall_fraction": {
            names[k]: round(float((dom == k).mean()), 3) for k in range(len(names))},
        "per_sample_composition": comp,
        "interpretation": (
            "Marker validation PASSED if within-set gene correlation is clearly "
            "higher than between-set (markers co-vary by lineage) and the "
            "lineage-score correlation matrix shows off-diagonal negatives between "
            "epithelial vs immune lineages (distinct populations)."),
    }
    op = ROOT / "results/scrna_marker_validation.json"
    json.dump(out, open(op, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    print("\n===== marker validation summary =====")
    print(f"within-set gene corr  = {np.nanmean(within):+.3f}")
    print(f"between-set gene corr = {np.nanmean(between):+.3f}")
    print(f"coherence gap         = {np.nanmean(within) - np.nanmean(between):+.3f} "
          f"(want > 0 and sizeable)")
    print("dominant lineage fraction (all cells):")
    for k in range(len(names)):
        print(f"  {names[k]:18s} {(dom == k).mean():.3f}")
    print(f"\nsaved -> {op}")


if __name__ == "__main__":
    main()
