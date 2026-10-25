#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""C3-lite multi-seed: strict pairs of (run embeddings, same-run decoder).

Four strict pairs (decoder W belongs to the same training run as Xs):
  s0/lam2.0  from repair_e4_hnscc_stable.json + e4_decoder_w.npz
  s1/lam2.0  from e4_dump_s1_lam2.json        + e4_decoder_w_s1_lam2.npz
  s2/lam2.0  from e4_dump_s2_lam2.json        + e4_decoder_w_s2_lam2.npz
  s1/lam5.0  from e4_dump_s1_lam5.json        + e4_decoder_w_s1_lam5.npz

Per pair: ridge HPV direction on slice-mean embeddings -> gene loadings
through W -> top-100 |loading| enrichment vs HPV+ keratinization markers
(hypergeometric + permutation null). Output: results/c3lite_multiseed.json
"""
from __future__ import annotations
import json
from math import comb
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1] / "results"

HPV_POS_MARKERS = [
    "CDKN2A", "CDKN2B", "CCNA1", "ID1", "KRT5", "KRT14", "KRT6A",
    "KRT16", "KRT17", "TP63", "DLL1", "CYLD", "SFN", "S100A7", "CDC6",
]

PAIRS = [
    ("s0_lam2.0", "repair_e4_hnscc_stable.json", "e4_decoder_w.npz", "lam2.0"),
    ("s1_lam2.0", "e4_dump_s1_lam2.json", "e4_decoder_w_s1_lam2.npz", "lam2.0"),
    ("s2_lam2.0", "e4_dump_s2_lam2.json", "e4_decoder_w_s2_lam2.npz", "lam2.0"),
    ("s1_lam5.0", "e4_dump_s1_lam5.json", "e4_decoder_w_s1_lam5.npz", "lam5.0"),
]


def norm(g):
    return g[7:] if g.startswith("GRCh38_") else g


def ridge_dir(Xs, y, alpha=1.0):
    mu, sd = Xs.mean(0), Xs.std(0) + 1e-8
    Z = (Xs - mu) / sd
    w = np.linalg.solve(Z.T @ Z + alpha * np.eye(Z.shape[1]), Z.T @ y)
    return w / (np.linalg.norm(w) + 1e-12)


def hypergeom_p(hit, k_draw, m_mark, n_total):
    return min(1.0, sum(comb(m_mark, h) * comb(n_total - m_mark, k_draw - h)
                        for h in range(hit, min(k_draw, m_mark) + 1))
               / comb(n_total, k_draw))


def main():
    # shared panel from the s0 decoder; work in UNIQUE-gene-name space
    # (the union panel can contain duplicated symbols; a marker hit on any
    # duplicate index must count once). Each unique gene takes its max
    # |loading| across duplicate indices.
    w0 = np.load(R / "e4_decoder_w.npz", allow_pickle=True)
    raw_panel = [norm(str(g)) for g in w0["panel"]]
    print(f"[panel] {len(raw_panel)} entries")
    m_pos = len([g for g in set(raw_panel) if g in HPV_POS_MARKERS])
    n_uniq = len(set(raw_panel))
    print(f"[panel] {n_uniq} unique genes; {m_pos}/"
          f"{len(HPV_POS_MARKERS)} HPV+ markers present")

    # shared permutation null: draw 100 UNIQUE genes uniformly
    uniq = sorted(set(raw_panel))
    rng = np.random.default_rng(20261018)
    null_hits = np.array([
        sum(g in HPV_POS_MARKERS
            for g in rng.choice(uniq, 100, replace=False))
        for _ in range(2000)])
    print(f"[null] mean hits per 100 unique genes = {null_hits.mean():.3f}")

    out = {"panel_entries": len(raw_panel), "panel_unique": n_uniq,
           "markers_in_panel": m_pos, "null_mean": float(null_hits.mean()),
           "pairs": {}}
    for tag, json_f, npz_f, _ in PAIRS:
        jf, nf = R / json_f, R / npz_f
        if not jf.exists() or not nf.exists():
            print(f"[skip] {tag}: missing {json_f} / {npz_f}")
            continue
        d = json.loads(jf.read_text())
        dx = d.get("dump_xs", {})
        if tag not in dx:
            print(f"[skip] {tag}: no dump_xs[{tag}] "
                  f"(keys={list(dx)[:2]}...)")
            continue
        Xs = np.array(dx[tag]["Xs"], dtype=float)
        y = np.array(dx[tag]["y"], dtype=float)
        W = np.asarray(
            np.load(nf, allow_pickle=True)["W"], dtype=float)
        d_emb = ridge_dir(Xs, y)
        L = np.abs(W @ d_emb)
        # unique-name max-|loading| ranking
        best = {}
        for i, g in enumerate(raw_panel):
            if g not in best or L[i] > best[g]:
                best[g] = L[i]
        ranked = sorted(best.items(), key=lambda kv: -kv[1])[:100]
        top = [g for g, _ in ranked]
        hits = [g for g in top if g in HPV_POS_MARKERS]
        krt = [g for g in top if g.startswith("KRT") or g.startswith("SPRR")
               or g == "IVL"]
        p_hg = hypergeom_p(len(hits), 100, m_pos, n_uniq)
        p_emp = float((null_hits >= len(hits)).mean())
        print(f"[{tag}] hits={len(hits)} {hits} p_hg={p_hg:.4f} "
              f"p_emp={p_emp:.4f} krt={krt}")
        print("        top10: " + ", ".join(
            f"{g}({v:+.2f})" for g, v in ranked[:10]))
        out["pairs"][tag] = {"hits": hits, "n_hits": len(hits),
                             "p_hypergeom": p_hg, "p_empirical": p_emp,
                             "keratinization": krt, "top25": top[:25]}
    (R / "c3lite_multiseed.json").write_text(json.dumps(out, indent=2))
    print("[saved] results/c3lite_multiseed.json")


if __name__ == "__main__":
    main()
