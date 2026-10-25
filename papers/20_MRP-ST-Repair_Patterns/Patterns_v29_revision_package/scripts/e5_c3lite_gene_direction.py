#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""C3-lite: post-repair program survival — gene-direction analysis.

Materials (already on disk):
  results/e4_decoder_w.npz            W (n_union_genes, emb=128) decoder
                                      weights of the ACCEPTED run
                                      (seed 0, lambda 2.0, E4 HNSCC stable)
  results/repair_e4_hnscc_stable.json dump_xs per (seed, lam): slice-mean
                                      embeddings Xs (16,128), y (HPV 1/0)

Logic:
 1. Fit the HPV+/HPV- discriminant direction d in EMBEDDING space (ridge on
    the repaired run's slice-mean embeddings — the signal that SURVIVED
    repair).
 2. Map d back to GENE space through the decoder: L = W @ d  (per-gene
    loading on the surviving discriminant axis).
 3. Test whether top-loaded genes enrich known HPV+ HNSCC biology
    (CDKN2A/p16 axis, keratinizing-basal program; Puram 2017 / NG 2026).
 4. Robustness: repeat across the other (seed, lam) embeddings and against
    a permutation null for the enrichment p-value.

Outputs: results/c3lite_gene_direction.json (+ console report).
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1] / "results"

# Known HPV+ HNSCC biology (literature markers: CDKN2A/p16 retinoblastoma-
# axis, cell-cycle entry, keratinizing/basal differentiation; Puram et al.
# 2017; Simkin/Barrett/Tirosh/Puram NG 2026 dataset paper)
HPV_POS_MARKERS = [
    "CDKN2A", "CDKN2B", "CCNA1", "ID1", "KRT5", "KRT14", "KRT6A",
    "KRT16", "KRT17", "TP63", "DLL1", "CYLD", "SFN", "S100A7", "CDC6",
]
HPV_NEG_MARKERS = [
    "EGFR", "FGFR3", "Cav1", "CAV1", "SQSTM1", "ITGA6", "ITGB4",
    "LAMC2", "COL17A1", "DSG3", "PDCD1", "TIGIT",
]


def ridge_dir(Xs, y, alpha=1.0):
    mu, sd = Xs.mean(0), Xs.std(0) + 1e-8
    Z = (Xs - mu) / sd
    w = np.linalg.solve(Z.T @ Z + alpha * np.eye(Z.shape[1]), Z.T @ y)
    return w / (np.linalg.norm(w) + 1e-12)


def hypergeom_p(hit, k_draw, m_mark, n_total):
    """P(X >= hit) for drawing k from N with m successes."""
    from math import comb
    N = n_total
    return min(1.0, sum(comb(m_mark, h) * comb(N - m_mark, k_draw - h)
                        for h in range(hit, min(k_draw, m_mark) + 1))
               / comb(N, k_draw))


def main():
    wnp = np.load(R / "e4_decoder_w.npz", allow_pickle=True)
    W = np.asarray(wnp["W"], dtype=float)          # (n_genes, 128)
    panel = [str(g) for g in wnp["panel"]]
    # GSE268014 features use "GRCh38_<SYMBOL>" gene names -> strip prefix so
    # literature markers match (e.g. GRCh38_KRT14 -> KRT14).
    def norm(g):
        return g[7:] if g.startswith("GRCh38_") else g
    panel_n = [norm(g) for g in panel]
    gene_ix = {g: i for i, g in enumerate(panel_n)}
    n_genes = len(panel)

    d = json.loads((R / "repair_e4_hnscc_stable.json").read_text())
    dx = d["dump_xs"]
    keys = sorted(dx.keys())
    print(f"[load] W{W.shape}  panel={n_genes}  dump_xs runs={len(keys)}")

    report = {"panel_size": n_genes, "note": "gene names normalized "
              "(GRCh38_ prefix stripped); STRICT pairing only: decoder W is "
              "the s0/lam2.0 run, so only s0_lam2.0 is a valid pairing. "
              "Cross-run rows are reported as coordinate-system-mismatched "
              "and are NOT evidence.", "runs": {}}

    # main: the accepted run (s0, lam2.0) — matches decoder dump
    key0 = "s0_lam2.0"
    Xs = np.array(dx[key0]["Xs"], dtype=float)
    y = np.array(dx[key0]["y"], dtype=float)
    d_emb = ridge_dir(Xs, y)
    Lg = W @ d_emb
    order = np.argsort(-np.abs(Lg))
    top100 = [panel_n[i] for i in order[:100]]
    hits_pos = [g for g in top100 if g in HPV_POS_MARKERS]
    hits_neg = [g for g in top100 if g in HPV_NEG_MARKERS]
    m_pos = sum(g in gene_ix for g in HPV_POS_MARKERS)
    m_neg = sum(g in gene_ix for g in HPV_NEG_MARKERS)
    p_pos = hypergeom_p(len(hits_pos), 100, m_pos, n_genes)
    p_neg = hypergeom_p(len(hits_neg), 100, m_neg, n_genes)
    print(f"\n[{key0}] STRICT pairing (decoder == this run)")
    print(f"  top-100: HPV+ markers hit {len(hits_pos)}/{m_pos}-in-panel "
          f"{'/'.join(hits_pos) if hits_pos else '—'}  p={p_pos:.4f}")
    print(f"           HPV- markers hit {len(hits_neg)}/{m_neg}-in-panel "
          f"{'/'.join(hits_neg) if hits_neg else '—'}  p={p_neg:.4f}")
    print("  top-25 |loading| genes:",
          ", ".join(f"{panel_n[i]}({Lg[i]:+.2f})" for i in order[:25]))

    # orientation: positive loading = HPV+ side (ridge target y=1)
    pos_side = [panel_n[i] for i in order if Lg[i] > 0][:100]
    neg_side = [panel_n[i] for i in order if Lg[i] < 0][:100]
    pos_hits = [g for g in pos_side if g in HPV_POS_MARKERS]
    neg_hits = [g for g in neg_side if g in HPV_NEG_MARKERS]
    krt_in_top = [g for g in top100 if g.startswith("KRT")
                  or g in ("SPRR1A", "SPRR1B", "SPRR2A", "SPRR3", "IVL")]
    print(f"  orientation: HPV+ markers on HPV+ side={len(pos_hits)} {pos_hits}")
    print(f"               HPV- markers on HPV- side={len(neg_hits)} {neg_hits}")
    print(f"  keratinization genes in top-100: {krt_in_top}")

    report["runs"][key0] = {
        "top100": top100, "top25_abs": [panel_n[i] for i in order[:25]],
        "hpvpos_hits": hits_pos, "hpvpos_p": p_pos,
        "hpvneg_hits": hits_neg, "hpvneg_p": p_neg,
        "pos_side_hpvhits": pos_hits, "neg_side_hpvneg_hits": neg_hits,
        "keratinization_top100": krt_in_top,
    }

    # permutation null for enrichment: random 100-gene draws
    rng = np.random.default_rng(20261018)
    null_hits = np.array([
        sum(panel_n[i] in HPV_POS_MARKERS
            for i in rng.choice(n_genes, 100, replace=False))
        for _ in range(2000)])
    p_emp = float((null_hits >= len(hits_pos)).mean())
    print(f"  permutation-null P(X>={len(hits_pos)} hits) = {p_emp:.4f} "
          f"(null mean {null_hits.mean():.2f})")
    report["runs"][key0]["p_empirical"] = p_emp
    report["null_mean_hits"] = float(null_hits.mean())

    # Cross-run rows (coordinate-system MISMATCHED: decoder belongs to
    # s0/lam2.0 only) — reported for transparency, not evidence.
    print("\n[cross-run, decoder mismatched — NOT evidence] hits(top100):")
    for key in keys:
        if key == key0:
            continue  # strict pair already recorded; do not overwrite it
        lam = float(key.split("lam")[1])
        Xs_k = np.array(dx[key]["Xs"], dtype=float)
        y_k = np.array(dx[key]["y"], dtype=float)
        d_k = ridge_dir(Xs_k, y_k)
        L_k = W @ d_k
        o_k = np.argsort(-np.abs(L_k))[:100]
        h_pos = sum(panel_n[i] in HPV_POS_MARKERS for i in o_k)
        h_neg = sum(panel_n[i] in HPV_NEG_MARKERS for i in o_k)
        krt = sum(panel_n[i].startswith("KRT")
                  or panel_n[i] in ("SPRR1B", "SPRR1A") for i in o_k)
        print(f"  {key:>11}: hpvpos={h_pos} hpvneg={h_neg} krt={krt}")
        report["runs"][key] = {"hpvpos_hits_n": h_pos, "hpvneg_hits_n": h_neg,
                               "keratinization_n": krt, "mismatched": True}

    (R / "c3lite_gene_direction.json").write_text(json.dumps(report, indent=2))
    print(f"\n[saved] results/c3lite_gene_direction.json")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
