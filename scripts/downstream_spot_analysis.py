#!/usr/bin/env python
"""
downstream_spot_analysis.py — post-training biology from one (or more)
fused_embs_<run_id>.npz dumps. Zero GPU.

Produces three pieces of evidence for the CSBJ revision (plan item ③a/③b):

  1. RISK DISTRIBUTION (violin/KW): per-spot risk by histology severity
     (normal=0 / HSIL=1 / cancer=2). GUARDRAIL: spots within a slide are NOT
     independent, so the spot-level KW p is reported as DESCRIPTIVE sensitivity
     analysis only; the honest inference is the per-SAMPLE mean comparison
     (n=31 normal vs 4 disease), which is also printed.

  2. PATHWAY / CELL-COMPOSITION x RISK correlation: an skmisc-free rank-based
     ssGSEA score (mean-rank enrichment) is computed per spot for every set in
     src/downstream_genes.py (8 cell types + 7 HPV-related pathways), then
     Spearman-correlated with the risk score. Scores/risk are z-scored WITHIN
     each sample before pooling so cross-slide batch offsets don't inflate r.
     Benjamini-Hochberg FDR across sets.

  3. A 2-panel figure (violin + correlation bar) saved under results/.

Usage:
  python scripts/downstream_spot_analysis.py --run_id FULL_seed0
  python scripts/downstream_spot_analysis.py --glob "results/fused_embs_*.npz"
"""
from __future__ import annotations
import argparse, glob, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.downstream_genes import all_gene_sets  # noqa: E402


def rank_enrichment(X: np.ndarray, gene_sets: dict, gene_names: list[str]):
    """skmisc-free ssGSEA-like score.

    X: (n_spots, n_genes) expression (log). For each spot we rank genes by
    expression and give a set the mean rank of its members, centred at 0.5
    (rank/N). Positive => set members sit in the high-expression tail.
    Returns (n_spots, n_sets) float matrix + ordered set names.
    """
    n, g = X.shape
    # average-rank per row (1..g); argsort twice gives dense ranks; ties -> mean
    order = X.argsort(axis=1)
    ranks = np.empty_like(order, dtype=np.float64)
    rng_ar = np.arange(g)
    for i in range(n):
        ranks[i, order[i]] = rng_ar + 1.0
    # tie-correct (identical expression values get the mean rank)
    # vectorised tie averaging is heavy; Visium log-values rarely tie after
    # normalisation, so dense ranks are an acceptable approximation here.
    names = list(gene_sets.keys())
    gidx = {gn: j for j, gn in enumerate(gene_names)}
    out = np.zeros((n, len(names)), dtype=np.float64)
    keep = []
    for k, sname in enumerate(names):
        idx = [gidx[g_] for g_ in gene_sets[sname] if g_ in gidx]
        if len(idx) < 3:
            continue
        keep.append((k, sname, idx))
    for k, sname, idx in keep:
        mr = ranks[:, idx].mean(axis=1) / g          # mean rank in (0,1]
        out[:, k] = mr - 0.5                          # centre
    final_names = [sname for _, sname, _ in keep]
    out = out[:, [k for k, _, _ in keep]]
    return out, final_names


def zscore_within_sample(vals, sample_ids):
    """z-score per sample to remove slide-level offset; return pooled vector."""
    v = np.asarray(vals, dtype=float).copy()
    for s in np.unique(sample_ids):
        m = sample_ids == s
        sd = v[m].std()
        v[m] = (v[m] - v[m].mean()) / (sd if sd > 1e-9 else 1.0)
    return v


def analyze_npz(path: str):
    z = np.load(path, allow_pickle=True)
    scores = z["scores"].astype(float)
    sev = z["prog_y"].astype(int)
    sids = z["sample_ids"].astype(str)
    n = len(scores)
    has_expr = ("exp_sub" in z.files) and ("exp_genes" in z.files)
    if has_expr:
        exp = z["exp_sub"].astype(float)
        genes = [str(x) for x in z["exp_genes"]]
    else:
        exp, genes = None, []
        print("  [WARN] no exp_sub in this npz (dumped by older train_st.py) — "
              "pathway/cell analysis skipped. Re-run training with the updated "
              "train_st.py --dump_fused to enable it.")
    print(f"\n=== {Path(path).name} ===")
    print(f"spots={n}  exp_sub={exp.shape if has_expr else 'ABSENT'}  "
          f"genes_in_panel={len(genes)}")

    res = {"run_id": Path(path).stem.replace("fused_embs_", ""),
           "n_spots": int(n), "n_samples": int(len(np.unique(sids)))}

    # ---- 1. risk by severity (spot-level, descriptive) ----
    groups = {lab: scores[sev == lab] for lab in (0, 1, 2) if (sev == lab).any()}
    glabel = {0: "normal", 1: "HSIL", 2: "cancer"}
    print("  spot risk by severity (mean +/- SD, n):")
    for lab, v in groups.items():
        print(f"    {glabel.get(lab, lab):8s} {v.mean():.3f} +/- {v.std():.3f}  n={len(v)}")
    try:
        from scipy.stats import kruskal
        kw_H, kw_p = kruskal(*groups.values())
    except Exception:
        kw_H, kw_p = float("nan"), float("nan")
    # honest per-sample means
    df = pd.DataFrame({"sid": sids, "sev": sev, "score": scores})
    per_sample = df.groupby(["sid", "sev"])["score"].mean().reset_index()
    norm_s = per_sample.loc[per_sample.sev == 0, "score"].values
    dis_s = per_sample.loc[per_sample.sev > 0, "score"].values
    try:
        from scipy.stats import mannwhitneyu
        u_p = mannwhitneyu(dis_s, norm_s, alternative="greater").pvalue
    except Exception:
        u_p = float("nan")
    print(f"  [descriptive] spot-level KW H={kw_H:.1f} p={kw_p:.2e} "
          f"(spots NOT independent — sensitivity only)")
    print(f"  [honest] per-sample mean: disease n={len(dis_s)} vs normal n={len(norm_s)} "
          f"MWU one-sided p={u_p:.4f}")
    res["risk_by_severity_spot"] = {
        glabel.get(lab, str(lab)): {"mean": float(v.mean()), "sd": float(v.std()),
                                     "n_spots": int(len(v))}
        for lab, v in groups.items()}
    res["spot_level_KW"] = {"H": float(kw_H), "p": float(kw_p),
                            "note": "spots non-independent; descriptive only"}
    res["per_sample_disease_vs_normal_MWU_p"] = float(u_p)

    # ---- 2. ssGSEA x risk ----
    rows = []
    if has_expr:
        S, set_names = rank_enrichment(exp, all_gene_sets(), genes)
        rz = zscore_within_sample(scores, sids)
        from scipy.stats import spearmanr
        for j, sname in enumerate(set_names):
            sz = zscore_within_sample(S[:, j], sids)
            rho, p = spearmanr(rz, sz)
            rows.append({"set": sname, "spearman_rho": float(rho), "p": float(p)})
        # BH FDR
        try:
            from statsmodels.stats.multitest import multipletests
            pv = [r["p"] for r in rows]
            _, q, _, _ = multipletests(pv, method="fdr_bh")
            for r, qq in zip(rows, q):
                r["BH_q"] = float(qq)
        except Exception:
            for r in rows:
                r["BH_q"] = None
        rows.sort(key=lambda r: -abs(r["spearman_rho"]))
        res["pathway_cell_corr"] = rows
        print("  pathway/cell score ~ risk (within-sample z, Spearman):")
        for r in rows[:12]:
            star = "*" if (r["BH_q"] is not None and r["BH_q"] < 0.05) else " "
            qs = f"q={r['BH_q']:.1e}" if r["BH_q"] is not None else "q=NA"
            print(f"    {star} {r['set']:26s} rho={r['spearman_rho']:+.3f} "
                  f"p={r['p']:.1e} {qs}")
    else:
        res["pathway_cell_corr"] = None
    return res, groups, glabel, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run_id", default=None,
                    help="single run, e.g. FULL_seed0 -> results/fused_embs_FULL_seed0.npz")
    ap.add_argument("--glob", dest="globpat", default=None,
                    help="glob for multiple npz, e.g. 'results/fused_embs_FULL_seed*.npz'")
    ap.add_argument("--out", default=str(ROOT / "results/downstream_spot_analysis.json"))
    ap.add_argument("--fig", default=str(ROOT / "results/downstream_spot_analysis.png"))
    args = ap.parse_args()

    if args.run_id:
        paths = [str(ROOT / "results" / f"fused_embs_{args.run_id}.npz")]
    elif args.globpat:
        paths = sorted(glob.glob(args.globpat))
    else:
        paths = sorted(glob.glob(str(ROOT / "results/fused_embs_FULL_seed0.npz")))
    paths = [p for p in paths if Path(p).exists()]
    if not paths:
        print("[FAIL] no fused_embs npz found. Run train_st.py with --dump_fused first.")
        sys.exit(1)

    all_res = []
    fig_groups = None
    for p in paths:
        r, groups, glabel, rows = analyze_npz(p)
        all_res.append(r)
        fig_groups = (groups, glabel, rows, Path(p).stem.replace("fused_embs_", ""))

    json.dump(all_res if len(all_res) > 1 else all_res[0],
              open(args.out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"\nsaved -> {args.out}")

    # ---- figure (from first/representative run) ----
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        groups, glabel, rows, tag = fig_groups
        fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
        labs = [glabel.get(l, str(l)) for l in sorted(groups)]
        data = [groups[l] for l in sorted(groups)]
        parts = axes[0].violinplot(data, showmeans=True, showextrema=False)
        for pc, c in zip(parts["bodies"], ["#4C72B0", "#DD8452", "#C44E52"][:len(data)]):
            pc.set_facecolor(c); pc.set_alpha(0.7)
        axes[0].set_xticks(range(1, len(labs) + 1)); axes[0].set_xticklabels(labs)
        axes[0].set_ylabel("spot risk score"); axes[0].set_title(f"Risk by severity ({tag})")
        if rows:
            top = rows[:10][::-1]
            cols = ["#55A868" if r["spearman_rho"] > 0 else "#C44E52" for r in top]
            axes[1].barh([r["set"] for r in top], [r["spearman_rho"] for r in top], color=cols)
            axes[1].set_xlabel("Spearman rho (within-sample z)")
            axes[1].set_title("Pathway / cell-type score ~ risk")
            axes[1].axvline(0, color="k", lw=0.6)
        else:
            axes[1].set_title("pathway analysis n/a (re-run with updated train_st.py)")
        plt.tight_layout(); plt.savefig(args.fig, dpi=160)
        print(f"figure -> {args.fig}")
    except Exception as e:
        print(f"[fig skipped] {e}")


if __name__ == "__main__":
    main()
