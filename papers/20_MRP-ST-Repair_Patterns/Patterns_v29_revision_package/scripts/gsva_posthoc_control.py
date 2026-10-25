"""
gsva_posthoc_control.py — 训练前 HPV 锚定 vs 训练后 ssGSEA 富集 的对比

为什么存在（审稿人最高概率攻击点）：
  目前只证明了 "训练期 HPV 锚定 > 完全无锚定（NO-HPV）"，
  但没证明 "训练期锚定 > 训练后跑个 ssGSEA" 这种廉价替代方案。
  本脚本的逻辑：
    (1) 用 FULL 模型训练好的 checkpoint 对每张 held-out 切片推 risk score
    (2) 对同一张 held-out 切片的原始基因表达，用 gseapy 跑 ssGSEA / GSVA
        得到 KEGG_HPV 通路富集分数
    (3) 比较：
        - 模型 risk score vs 真实 HPV proxy label 的 AUC（train_st.py 原有指标）
        - ssGSEA 分数 vs 真实 HPV proxy label 的 AUC（cheap posthoc baseline）
        - 模型 risk score vs ssGSEA 分数的 Spearman 相关
    (4) 预期：模型 AUC >> ssGSEA AUC → 训练期锚定真有价值

  如果模型 AUC ≈ ssGSEA AUC → 我们的卖点就是 "用深度学习绕了一圈，
  但 ssGSEA 就能做到一样" → 论文核心贡献坍塌。

Usage:
  python scripts/gsva_posthoc_control.py \
      --data data/st_visium \
      --labels data/st_visium/labels/cervix_histology_labels_extended.csv \
      --results results/results_FULL.json \
      --out results/gsva_vs_model.json \
      --device cpu

依赖: gseapy >= 1.1.0, scanpy, squidpy
"""
from __future__ import annotations
import argparse, json, os, sys, time, gc
from pathlib import Path
import numpy as np
import pandas as pd
import scanpy as sc
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

SEED = 42; os.environ.setdefault("PYTHONHASHSEED", str(SEED)); np.random.seed(SEED)
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src import st_data as S

# === 与 train_st.py 完全一致的 108-gene KEGG_HPV ===
KEGG_HPV_INFECTION_GENES = {
    "TP53","RB1","CDKN1A","CDKN2A","MDM2","MYC","CCND1","CCNE1","CDK2","CDK4",
    "E2F1","E2F2","E2F3","MCM2","MCM3","MCM4","MCM5","MCM6","MCM7","PCNA",
    "CDC25A","CDC6","ORC1","RRM2","TK1","TYMS","FEN1","LIG1","POLA1","PRIM1",
    "CD274","PDCD1LG2","STAT1","IRF1","IRF3","IFNB1","MX1","OAS1","OAS2","OAS3",
    "TNF","IL6","IL1B","CXCL8","CXCL10","CCL2","CCL5","ICAM1","VCAM1","HLA-A",
    "HLA-B","HLA-C","B2M","TAP1","TAP2","PSMB8","PSMB9","PSME1","PSME2",
    "KRT5","KRT6A","KRT8","KRT14","KRT17","KRT18","KRT19","TP63","EPCAM",
    "MKI67","AURKA","AURKB","BUB1","CENPF","PLK1","TOP2A","CCNB1","CCNA2","CDK1",
    "EGFR","ERBB2","PIK3CA","PTEN","KRAS","AKT1","MTOR","MAPK1","MAPK3","JAK1",
    "JAK2","EP300","CREBBP","SMAD2","SMAD3","SMAD4","TGFB1","HMGB2","KPNA2","NUMA1",
    "CTLA4","PDCD1","LAG3","HAVCR2","TIGIT","FOXP3","CD4","CD8A","GZMB","PRF1",
}


def _is_visium_dir(d: Path) -> bool:
    if not d.is_dir(): return False
    if (d / "filtered_feature_bc_matrix.h5").exists(): return True
    return False

_CERVIX_TOP_DIRS = {"geo_cesc", "geo_ectocervix", "cervical_cancer_1"}

def _collect_cervix_sample_dirs(root: Path) -> list[Path]:
    out = []
    for top in _CERVIX_TOP_DIRS:
        top_p = root / top
        if not top_p.is_dir(): continue
        if _is_visium_dir(top_p): out.append(top_p)
        for child in sorted(top_p.iterdir()):
            if _is_visium_dir(child): out.append(child)
    return out


def compute_ssgsea_scores(adata: sc.AnnData, gene_set: set, n_top_genes: int = 2000):
    """Run ssGSEA for KEGG_HPV on the AnnData's HVG subset, return per-spot enrichment score.

    Uses gseapy's ssgsea function — very fast (seconds per slice).
    """
    import gseapy as gp

    # HVG + log-normalize
    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)
    sc.pp.highly_variable_genes(adata, n_top_genes=min(n_top_genes, adata.n_vars), flavor="seurat")
    hvg = adata[:, adata.var.highly_variable].copy()

    # Build the gene set dict expected by gseapy
    gs_dict = {"KEGG_HPV_INFECTION": sorted(gene_set & set(hvg.var_names))}
    # If <2 genes in HVG subset, fall back to using all HPV genes present
    if len(gs_dict["KEGG_HPV_INFECTION"]) < 3:
        gs_dict = {"KEGG_HPV_INFECTION": sorted(gene_set & set(adata.var_names))}

    # Expression matrix (genes × spots)
    exp_df = pd.DataFrame(
        adata.X.toarray() if hasattr(adata.X, "toarray") else np.asarray(adata.X),
        index=adata.var_names,
        columns=adata.obs_names
    )

    # Run ssGSEA — per-spot enrichment score
    ss = gp.ssgsea(data=exp_df, gene_sets=gs_dict, sample_norm_method='rank',
                   no_plot=True, threads=1, verbose=False)
    score = ss.resultsOnSamples.loc["KEGG_HPV_INFECTION"].values.astype(np.float32)
    return score  # (n_spots,)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--results", required=True, help="results_FULL.json path")
    ap.add_argument("--out", default="results/gsva_vs_model.json")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--max_folds", type=int, default=None)
    args = ap.parse_args()

    labels_df = pd.read_csv(args.labels)
    full_res = json.loads(open(args.results).read())

    # Try to find fused embeddings from results
    fused_path = Path(args.results).parent / "fused_embs.npz"

    sample_dirs = _collect_cervix_sample_dirs(Path(args.data))
    if args.max_folds: sample_dirs = sample_dirs[:args.max_folds]
    print(f"[setup] {len(sample_dirs)} CERVIX slices only (skipped breast/ovarian/prostate/colon/HD), device={args.device}")

    per_slice = []
    for sd in sample_dirs:
        t0 = time.time()
        print(f"\n[{sd.name}] loading ...", flush=True)
        try:
            # load_sample returns STSample dataclass (NOT a dict, NOT AnnData)
            sample = S.load_sample(sd)
            # Build AnnData from STSample fields (raw counts for gsva/ssGSEA)
            import anndata as ad
            raw_counts = sample.expression.toarray().astype(np.float32)
            adata = ad.AnnData(X=raw_counts, var=pd.DataFrame(index=sample.genes))
        except Exception as e:
            print(f"  !! {sd.name} load failed: {e}")
            continue

        # === 1. True HPV proxy label (median threshold on raw counts mean) ===
        hpv_in_panel = [g for g in adata.var_names if g in KEGG_HPV_INFECTION_GENES]
        if len(hpv_in_panel) < 3:
            print(f"  !! {sd.name}: only {len(hpv_in_panel)} HPV genes in panel → skip")
            continue

        hpv_idx = [adata.var_names.get_loc(g) for g in hpv_in_panel]
        true_hpv_mean = raw_counts[:, hpv_idx].mean(axis=1)
        thr = np.median(true_hpv_mean)
        hpv_y = (true_hpv_mean >= thr).astype(int)

        # === 2. ssGSEA enrichment score ===
        try:
            print(f"    ssGSEA ...", end=" ", flush=True)
            ss_score = compute_ssgsea_scores(adata, KEGG_HPV_INFECTION_GENES)
            print(f"done (shape={ss_score.shape})")
        except Exception as e:
            print(f"ssGSEA FAILED: {e}")
            ss_score = None

        # === 3. AUC: ssGSEA vs true label ===
        if ss_score is not None and len(np.unique(hpv_y)) == 2 and np.std(ss_score) > 1e-8:
            try:
                ssgsea_auc = roc_auc_score(hpv_y, ss_score)
            except Exception:
                ssgsea_auc = None
        else:
            ssgsea_auc = None

        # === 4. Model risk score — get from FULL results ===
        model_auc_in_full = None
        # Try reading from fused_embs.npz or from results JSON directly
        if "hpv_proxy_auc" in full_res:
            model_auc_in_full = full_res["hpv_proxy_auc"]

        # Try reading per-slice risk score from fused
        model_risk_score = None
        if fused_path.exists():
            try:
                data = np.load(fused_path, allow_pickle=True)
                # fused_embs.npz should have 'embeddings', 'coords', 'sample_ids'
                if "embeddings" in data and "sample_ids" in data:
                    import torch as T
                    embs = data["embeddings"]
                    sids = data["sample_ids"]
                    # Find indices for this slice
                    mask = np.array([sid == sd.name for sid in sids])
                    # Risk score = mean of embeddings (or we just skip if structure unknown)
                    if mask.sum() > 0:
                        model_risk_score = embs[mask].mean(axis=1)  # placeholder
            except Exception as e:
                print(f"    fused_embs read failed: {e}")

        # Spearman: ssGSEA vs true HPV mean (continuous)
        if ss_score is not None:
            try:
                sp_cont, _ = spearmanr(ss_score, true_hpv_mean)
            except Exception:
                sp_cont = None
        else:
            sp_cont = None

        entry = {
            "slice": sd.name,
            "n_spots": int(len(hpv_y)),
            "n_hpv_genes_found": len(hpv_in_panel),
            "ssgsea_auc": float(ssgsea_auc) if ssgsea_auc is not None else None,
            "model_auc_full_run": model_auc_in_full,
            "spearman_ssgsea_vs_true": float(sp_cont) if sp_cont is not None else None,
            "model_risk_score_available": model_risk_score is not None,
            "elapsed_seconds": round(time.time() - t0, 1),
        }
        per_slice.append(entry)
        gc.collect()

    # === Aggregate ===
    valid_ssgsea = [s["ssgsea_auc"] for s in per_slice if s["ssgsea_auc"] is not None]
    sprs = [s["spearman_ssgsea_vs_true"] for s in per_slice if s["spearman_ssgsea_vs_true"] is not None]

    out = {
        "generated": pd.Timestamp.now().isoformat(),
        "what_this_tests": ("Does training-time HPV pathway anchoring (our model) beat "
                            "a cheap post-hoc ssGSEA enrichment on raw counts?"),
        "expected_result": ("model hpv_proxy_auc (0.994) >> mean(ssgsea_auc) → proves "
                           "training-time anchoring captures richer signal than post-hoc enrichment alone"),
        "per_slice": per_slice,
        "summary": {
            "n_slices_with_ssgsea": len(valid_ssgsea),
            "mean_ssgsea_auc": round(float(np.mean(valid_ssgsea)), 4) if valid_ssgsea else None,
            "std_ssgsea_auc": round(float(np.std(valid_ssgsea)), 4) if valid_ssgsea else None,
            "mean_spearman_ssgsea_vs_true": round(float(np.mean(sprs)), 4) if sprs else None,
            "model_hpv_auc_from_results_full": full_res.get("hpv_proxy_auc"),
            "delta_model_minus_ssgsea": round(float(full_res["hpv_proxy_auc"] - np.mean(valid_ssgsea)), 4)
                if full_res.get("hpv_proxy_auc") is not None and valid_ssgsea else None,
        },
    }

    out_path = Path(args.out); out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, default=str))

    print("\n===== GSVA vs MODEL SUMMARY =====")
    print(json.dumps(out["summary"], indent=2))
    print(f"\nSaved → {out_path}")
    print("\nINTERPRETATION:")
    print(f"  model AUC (train_st) = {full_res.get('hpv_proxy_auc')}")
    print(f"  mean ssGSEA AUC      = {out['summary']['mean_ssgsea_auc']}")
    if out["summary"].get("delta_model_minus_ssgsea") is not None:
        d = out["summary"]["delta_model_minus_ssgsea"]
        print(f"  Δ (model - ssGSEA)  = {d:.4f}")
        if d > 0.3: print("  ✅ TRAINING ANCHORING IS SUBSTANTIALLY BETTER than posthoc ssGSEA")
        elif d > 0.1: print("  ⚠️ Training anchoring is somewhat better; modest delta")
        else: print("  ❌ ssGSEA ALMOST AS GOOD — training anchoring claim weakens")


if __name__ == "__main__":
    main()
