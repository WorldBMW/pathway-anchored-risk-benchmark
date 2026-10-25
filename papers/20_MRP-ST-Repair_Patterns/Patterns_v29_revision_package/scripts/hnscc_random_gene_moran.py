"""
===========================================================================
 hnscc_random_gene_moran.py
===========================================================================
Purpose
-------
Plan-A random gene-set control for the cross-organ HNSCC cohorts
(CSBJ v10 review, hard-injury 1b): the manuscript already reports that in the
main cervical cohort, Moran's I of ANY 108-gene set's model score is ~0.92
(random_control_summary.json: 0.9157 across 30 retrained random panels vs
0.9433 for KEGG-HPV). To make the same statement directly on the HNSCC slides
themselves, for every Visium section we compute:

  1. Moran's I of the plain per-spot mean log-normalized expression of the
     KEGG-HPV 108-gene panel;
  2. Moran's I for 30 size-matched (108-gene) random gene sets drawn from four
     universes: (a) UNION of per-slide 2000 HVGs (flavor='seurat' on lognorm;
     primary), (b) genes HVG in >=2 slides, (c) HVG-union panels matched to the
     KEGG panel on pooled mean-expression deciles, (d) all measured genes (weak
     strawman reference; the intersection of per-slide HVGs has <108 genes and
     cannot be used);
  3. a coordinate-fixed permutation null (B=1000 value permutations) for the
     KEGG-panel score — the valid CSR negative control.

Caliber note (reported in the output JSON): this uses plain expression means,
not scores of 30 separately retrained models (the main-cohort caliber). It is
the direct test of "is high Moran's I a generic property of Visium data",
which is exactly the claim relevant to the HNSCC cross-organ paragraph. The
model-score Moran + its permutation null are produced separately by
hnscc_moran_permutation_control.py.

Spatial graph / statistic are identical to src.models.moran_i
(k=6 symmetric k-NN from a 7-neighbour cKDTree query, self excluded).

Usage (AutoDL, from repo root):
  python scripts/hnscc_random_gene_moran.py \
      --cohort-dir data/st_visium/geo_hnscc_hpv_GSE268014 \
      --cohort-dir data/st_visium/geo_hpv_hnscc_GSE281978 \
      --out results/hnscc_random_gene_moran.json \
      --n-sets 30 --n-perm 1000 --seed 20260912
===========================================================================
"""
from __future__ import annotations
import argparse, ast, json, sys
from pathlib import Path

import numpy as np
import pandas as pd
import scanpy as sc
from scipy.spatial import cKDTree
from scipy.sparse import csr_matrix

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from infer_st import load_sample_external  # noqa: E402

# The cohort directories contain many extra GSM sections (later downloads, some
# without spatial/). Only the sections used by the FINAL inference belong to
# this analysis; restrict to them by default. Override with
#   --only geo_hnscc_hpv_GSE268014:GSM1,GSM2 --only geo_hpv_hnscc_GSE281978:LI1,LI2
DEFAULT_ONLY = {
    "geo_hnscc_hpv_GSE268014": [
        "GSM8283897", "GSM8283898", "GSM8283899", "GSM8283900",
        "GSM8283901", "GSM8283902", "GSM8283903", "GSM8283904",
    ],
    "geo_hpv_hnscc_GSE281978": [
        "LI_SING_21_00757", "LI_SING_21_00758",
        "LI_SING_21_01569", "LI_SING_21_01570",
        "LI_SING_21_01586", "LI_SING_21_01587",
    ],
}


def kegg_panel_from_train_script() -> set[str]:
    """Extract KEGG_HPV_INFECTION_GENES literal from scripts/train_st.py
    without importing torch/training side effects."""
    src = (REPO / "scripts" / "train_st.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "KEGG_HPV_INFECTION_GENES":
                    return set(ast.literal_eval(node.value))
    raise RuntimeError("KEGG_HPV_INFECTION_GENES not found in scripts/train_st.py")


def moran_from_neighbors(z: np.ndarray, nbr: np.ndarray, n: int, k: int = 6) -> float:
    num = float((z * z[nbr].sum(axis=1)).sum())
    return float((n / (n * k)) * (num / float((z * z).sum())))


def load_lognorm(sample_dir: Path):
    """Same spot/cohort discovery/coordinates as inference; log1p CPM10k."""
    s = load_sample_external(sample_dir)
    if s is None:
        return None
    Xraw = csr_matrix(s["X"])
    adata = sc.AnnData(X=Xraw.copy())
    adata.var_names = list(s["genes"])
    adata.var_names_make_unique()
    # raw detection fraction (count > 0) before normalization
    det = np.asarray((Xraw > 0).mean(axis=0)).ravel()
    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)
    mean_lognorm = np.asarray(adata.X.mean(axis=0)).ravel()
    sc.pp.highly_variable_genes(adata, n_top_genes=2000, flavor="seurat")
    hvg = set(adata.var_names[adata.var.highly_variable])
    return {"name": s["name"], "X": adata.X, "genes": list(adata.var_names),
            "coords": s["coords"], "hvg": hvg, "n_spots": adata.n_obs,
            "mean_lognorm": mean_lognorm, "detection": det}


def panel_mean(X, genes, panel: list[str]) -> np.ndarray:
    idx = [genes.index(g) for g in panel if g in genes]
    if not idx:
        raise ValueError("no panel genes present")
    v = np.asarray(X[:, idx].mean(axis=1)).ravel()
    return v


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort-dir", action="append", required=True, type=Path)
    ap.add_argument("--only", action="append", default=[],
                    help="Restrict a cohort to named sample dirs, format "
                         "'COHORT_DIR_NAME:name1,name2'; repeatable. "
                         "Defaults to the 8 GSE268014 / 6 GSE281978 FINAL sections.")
    ap.add_argument("--n-sets", type=int, default=30)
    ap.add_argument("--n-perm", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=20260912)
    ap.add_argument("--out", type=Path,
                    default=REPO / "results" / "hnscc_random_gene_moran.json")
    args = ap.parse_args()

    kegg = kegg_panel_from_train_script()
    print(f"[panel] KEGG-HPV genes = {len(kegg)}")
    out = {"config": {"n_random_sets": args.n_sets, "n_perm": args.n_perm,
                      "seed": args.seed, "panel_size": len(kegg),
                      "score": "mean log1p(CPM10k) expression per spot",
                      "random_universes": "panels drawn from (a) union of per-slide "
                                         "2000 HVGs (primary), (b) HVG in >=2 slides, "
                                         "(c) HVG-union expression-decile matched to "
                                         "KEGG panel, (d) all measured genes (weak/"
                                         "strawman reference; the earlier intersection-"
                                         "of-HVGs universe had <108 genes and was unusable)",
                      "moran": "k=6 kNN, identical to src.models.moran_i"},
           "cohorts": {}}

    only_map = {k: list(v) for k, v in DEFAULT_ONLY.items()}
    for spec in args.only:
        cname, _, names = spec.partition(":")
        only_map[cname.strip()] = [x.strip() for x in names.split(",") if x.strip()]

    for cohort_dir in args.cohort_dir:
        sample_dirs = sorted(p for p in Path(cohort_dir).iterdir() if p.is_dir())
        if cohort_dir.name in only_map:
            allow = set(only_map[cohort_dir.name])
            missing = allow - {p.name for p in sample_dirs}
            if missing:
                raise SystemExit(f"[error] --only samples not found under "
                                 f"{cohort_dir}: {sorted(missing)}")
            sample_dirs = [p for p in sample_dirs if p.name in allow]
            print(f"[{cohort_dir.name}] restricted to {len(sample_dirs)} allow-listed sections")
        slides = []
        for sd in sample_dirs:
            print(f"[{cohort_dir.name}] loading {sd.name} ...")
            try:
                s = load_lognorm(sd)
            except Exception as e:  # noqa: BLE001 - skip non-Visium / coord-less dirs
                print(f"  [skip] {sd.name}: {e}")
                continue
            if s is not None:
                slides.append(s)
        if not slides:
            print(f"[warn] no loadable slides under {cohort_dir}")
            continue

        # ---- Gene universes (all restricted to genes measured in EVERY slide) ----
        all_shared = sorted(set.intersection(*[set(s["genes"]) for s in slides]))
        hvg_count = {g: 0 for g in all_shared}
        for s in slides:
            for g in s["hvg"]:
                if g in hvg_count:
                    hvg_count[g] += 1
        hvg_intersection = sorted(g for g, c in hvg_count.items()
                                  if c == len(slides))
        hvg_union = sorted(g for g, c in hvg_count.items() if c >= 1)
        hvg_ge2 = sorted(g for g, c in hvg_count.items() if c >= 2)
        print(f"  slides={len(slides)} | HVG2000 intersection={len(hvg_intersection)} "
              f"(< {len(kegg)} => intersection unusable); union={len(hvg_union)}; "
              f"ge2={len(hvg_ge2)}; all-shared={len(all_shared)}")

        # Pooled per-gene mean lognorm / detection (equal slide weight),
        # used to build expression-matched random panels.
        idx_of = {g: i for i, g in enumerate(all_shared)}
        mean_mat = np.vstack([
            pd.Series(s["mean_lognorm"], index=s["genes"]).reindex(all_shared).to_numpy()
            for s in slides])
        pooled_mean = mean_mat.mean(axis=0)

        def make_random_panels(univ, tag_off):
            # KEGG panel genes are excluded from every random panel.
            pool = [g for g in univ if g not in kegg]
            assert len(pool) >= len(kegg), "random pool smaller than panel"
            ps = []
            for i in range(args.n_sets):
                rng = np.random.default_rng(args.seed + i + tag_off)
                ps.append(list(rng.choice(pool, size=len(kegg), replace=False)))
            return ps

        def make_expr_matched_panels(pool, tag_off):
            """For each KEGG gene draw a replacement from the same pooled-mean
            decile of the HVG-union pool (KEGG genes excluded), no replacement
            within a panel."""
            pool = [g for g in pool if g in idx_of and g not in kegg]
            pm = np.array([pooled_mean[idx_of[g]] for g in pool])
            _, edges = pd.qcut(pm, q=10, retbins=True, duplicates="drop")
            bin_of = dict(zip(pool, np.clip(np.searchsorted(edges[1:-1], pm),
                                            0, len(edges) - 2)))
            cand = {}
            for g, b in bin_of.items():
                cand.setdefault(b, []).append(g)
            kegg_present = [g for g in sorted(kegg) if g in idx_of]
            kb = [int(np.clip(np.searchsorted(edges[1:-1],
                                              pooled_mean[idx_of[g]]),
                              0, len(edges) - 2)) for g in kegg_present]
            ps = []
            for i in range(args.n_sets):
                rng = np.random.default_rng(args.seed + i + tag_off)
                used, panel = set(), []
                for g, b in zip(kegg_present, kb):
                    avail = [x for x in cand[b] if x not in used]
                    pick = avail[rng.integers(len(avail))]
                    used.add(pick); panel.append(pick)
                ps.append(panel)
            return ps

        panels_by_ctrl = {
            "random_HVG_union": make_random_panels(hvg_union, 0),
            "random_HVG_ge2": make_random_panels(hvg_ge2, 10000),
            "random_HVG_union_exprMatched":
                make_expr_matched_panels(hvg_union, 20000),
            "random_allMeasured_strawman":
                make_random_panels(all_shared, 30000),
        }

        rows = []
        for s in slides:
            X, genes, coords = s["X"], s["genes"], s["coords"]
            n = len(coords)
            tree = cKDTree(coords)
            _, kidx = tree.query(coords, k=7)
            nbr = kidx[:, 1:]

            kegg_present = [g for g in kegg if g in genes]
            v_kegg = panel_mean(X, genes, kegg_present)
            i_kegg = moran_from_neighbors(v_kegg - v_kegg.mean(), nbr, n)

            controls = {}
            for cname, panels in panels_by_ctrl.items():
                i_rand = np.asarray([
                    moran_from_neighbors((lambda v: v - v.mean())(
                        panel_mean(X, genes, p)), nbr, n) for p in panels])
                controls[cname] = {
                    "random_moran_mean": float(i_rand.mean()),
                    "random_moran_sd": float(i_rand.std(ddof=0)),
                    "random_moran_min": float(i_rand.min()),
                    "random_moran_max": float(i_rand.max()),
                    "delta_kegg_minus_random": float(i_kegg - i_rand.mean()),
                    "p_kegg_vs_random_sets": float(
                        (1 + int((i_rand >= i_kegg).sum())) / (args.n_sets + 1))}

            # CSR permutation null for the KEGG-panel score
            z = v_kegg - v_kegg.mean()
            rng_p = np.random.default_rng(args.seed)
            nulls = np.empty(args.n_perm)
            for b in range(args.n_perm):
                nulls[b] = moran_from_neighbors(z[rng_p.permutation(n)], nbr, n)
            p_perm = (1 + int((nulls >= i_kegg).sum())) / (args.n_perm + 1)

            row = {"name": s["name"], "n_spots": n,
                   "kegg_genes_present": len(kegg_present),
                   "kegg_moran": float(i_kegg),
                   "controls": controls,
                   "kegg_perm_null_mean": float(nulls.mean()),
                   "kegg_perm_null_q025": float(np.quantile(nulls, 0.025)),
                   "kegg_perm_null_q975": float(np.quantile(nulls, 0.975)),
                   "kegg_perm_p": float(p_perm)}
            rows.append(row)
            u = controls["random_HVG_union"]
            m = controls["random_HVG_union_exprMatched"]
            print(f"  {s['name']:>18s} n={n:5d} KEGG I={i_kegg:.4f} | "
                  f"HVGunion {u['random_moran_mean']:.4f} d={u['delta_kegg_minus_random']:+.3f} "
                  f"p={u['p_kegg_vs_random_sets']:.3f} | exprMatch {m['random_moran_mean']:.4f} "
                  f"d={m['delta_kegg_minus_random']:+.3f} | strawman "
                  f"{controls['random_allMeasured_strawman']['random_moran_mean']:.4f} | "
                  f"perm p={p_perm:.4f}")

        km = np.array([r["kegg_moran"] for r in rows])
        ctrl_means = {}
        from scipy.stats import binomtest
        for cname in panels_by_ctrl:
            rm = np.array([r["controls"][cname]["random_moran_mean"] for r in rows])
            ds = np.array([r["controls"][cname]["delta_kegg_minus_random"]
                           for r in rows])
            n_pos = int((ds > 0).sum())
            # two-sided exact sign test at the SLIDE level (n=8 / n=6)
            sign_p = float(binomtest(n_pos, len(rows), 0.5,
                                     alternative="two-sided").pvalue)
            ctrl_means[cname] = {"random_moran_mean": float(rm.mean()),
                                 "delta": float(km.mean() - rm.mean()),
                                 "delta_mean_of_per_slide": float(ds.mean()),
                                 "n_slides_kegg_gt_random": n_pos,
                                 "n_slides": len(rows),
                                 "slide_level_sign_test_p": sign_p}
        out["cohorts"][cohort_dir.name] = {
            "n_slides": len(rows),
            "sections": [r["name"] for r in rows],
            "universes": {"hvg2000_intersection": len(hvg_intersection),
                          "hvg_union": len(hvg_union),
                          "hvg_in_ge2_slides": len(hvg_ge2),
                          "all_measured": len(all_shared),
                          "kegg_genes_measured": len([g for g in kegg if g in idx_of]),
                          "kegg_genes_in_hvg_union": len(kegg & set(hvg_union)),
                          "kegg_excluded_from_random_panels": True},
            "primary_control": "random_HVG_union_exprMatched",
            "per_slide": rows,
            "cohort_mean": {"kegg_moran": float(km.mean()),
                            "controls": ctrl_means},
        }
        print(f">> {cohort_dir.name}: KEGG {km.mean():.4f} | "
              + " | ".join(f"{c} {v['random_moran_mean']:.4f} (d={v['delta']:+.3f})"
                           for c, v in ctrl_means.items()) + "\n")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
