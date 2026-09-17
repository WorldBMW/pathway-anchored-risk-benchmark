"""
baseline_hpv_auc_eval.py — 算 Ridge / MLP / KNN baseline 的真实 HPV proxy AUC

为什么存在：
  审稿人指出 build_cmpb_paper_final.py L62 的 baseline_hpv_auc=0.0326 是硬编造数字。
  baseline_compare.py 只算了 MSE/Pearson/HPV_overlap，没算 AUC。本脚本用与
  train_st.py 完全一致的 HPV proxy label 定义（KEGG_HPV 基因均值 + median
  threshold → 0/1），对 baseline 的预测结果算真实 AUC。

  Ridge 的 AUC 预期接近 0.5（它完全没学到 HPV 信号，hpv_top50_overlap=0.0）。
  但 0.5 不是 0.03，诚实值和编造值差太远。

Usage:
  python scripts/baseline_hpv_auc_eval.py \
      --data data/st_visium \
      --labels data/st_visium/labels/cervix_histology_labels_extended.csv \
      --fm uni --device cuda \
      --out results/baseline_hpv_auc.json \
      --max_folds 6     # 可选：只跑前 N 张切片快速验证
"""
from __future__ import annotations
import argparse, json, os, sys, time, traceback, gc, warnings
from pathlib import Path
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
from sklearn.linear_model import RidgeCV
from sklearn.neural_network import MLPRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

SEED = 42; os.environ.setdefault("PYTHONHASHSEED", str(SEED)); np.random.seed(SEED)
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src import st_data as S

# === 与 train_st.py L55-73 完全一致的 108-gene KEGG_HPV 集合 ===
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
    br = d / "binned_outputs"
    if br.exists():
        for sub in sorted([p for p in br.iterdir() if p.is_dir()]):
            if (sub / "filtered_feature_bc_matrix.h5").exists(): return True
    return False


# === 宫颈相关切片子目录白名单 ===
# 其他 cross-cohort 基线（breast/ovarian/prostate/colon）和 HD 数据跳过
_CERVIX_TOP_DIRS = {"geo_cesc", "geo_ectocervix", "cervical_cancer_1"}


def _collect_cervix_sample_dirs(root: Path) -> list[Path]:
    """Walk root/geo_cesc + root/geo_ectocervix + root/cervical_cancer_1 to find
    ALL Visium subdirs. Skip breast/ovarian/prostate/visium_hd_* etc."""
    out = []
    for top in _CERVIX_TOP_DIRS:
        top_p = root / top
        if not top_p.is_dir():
            continue
        # If top itself is a Visium dir, add it
        if _is_visium_dir(top_p):
            out.append(top_p)
        # Otherwise scan children (most common case)
        for child in sorted(top_p.iterdir()):
            if _is_visium_dir(child):
                out.append(child)
    return out


def load_all_samples(root: Path, fm: str, device, n_genes: int = 2000, patch_size: int = 224,
                     sample_limit: int = None):
    """Load all Cervix Visium samples (35 slices) → list of dict{name, exp, genes, X}"""
    import torch
    from src.foundation_encoder import FoundationMorphologyEncoder

    sample_dirs = _collect_cervix_sample_dirs(root)
    if sample_limit: sample_dirs = sample_dirs[:sample_limit]
    print(f"[load] {len(sample_dirs)} CERVIX samples only (skipped breast/ovarian/prostate/colon/HD), fm={fm}, n_genes={n_genes}")

    enc = FoundationMorphologyEncoder(name=fm.lower(), out_dim=128, freeze=True).to(device).eval()
    enc_cache = {"encoder": enc}

    all_raw = []
    for i, sd in enumerate(sample_dirs):
        print(f"  [{i+1}/{len(sample_dirs)}] {sd.name}")
        sample = S.load_sample(sd)
        paired = S.build_paired_tensors(sample, n_genes_keep=max(n_genes, 2500), patch_size=patch_size)
        exp = np.asarray(paired["exp"].numpy(), dtype=np.float32)
        genes = paired["genes"]
        # coords is ALREADY numpy (not tensor) in build_paired_tensors return
        coords = paired["coords"] if "coords" in paired else None

        # FM features
        with torch.no_grad():
            img = paired["img"].to(device)
            feats = []
            for j in range(0, img.shape[0], 64):
                feats.append(enc(img[j:j+64]).cpu().numpy())
            X = np.concatenate(feats, axis=0).astype(np.float32)

        all_raw.append({"name": sd.name, "exp": exp, "genes": genes, "X": X, "coords": coords})
        gc.collect()

    return all_raw


def align_union(all_raw, n_genes_final: int = 2000):
    """Union-intersect gene panel across all samples → aligned matrices"""
    all_genes = set()
    for d in all_raw: all_genes.update(d["genes"])
    all_genes = sorted(all_genes | KEGG_HPV_INFECTION_GENES)
    print(f"[align] union genes={len(all_genes)}")

    gene_to_idx = {g: i for i, g in enumerate(all_genes)}
    aligned = []
    for d in all_raw:
        e = np.zeros((d["exp"].shape[0], len(all_genes)), dtype=np.float32)
        d_g2i = {g: i for i, g in enumerate(d["genes"])}
        for g in d["genes"]:
            if g in gene_to_idx:
                e[:, gene_to_idx[g]] = d["exp"][:, d_g2i[g]]
        aligned.append(e)

    # HVG selection
    stacked = np.concatenate(aligned, axis=0)
    var = stacked.var(axis=0)
    hpv_pos = np.array([gene_to_idx[g] for g in KEGG_HPV_INFECTION_GENES if g in gene_to_idx], dtype=np.int64)
    top_hvg = np.argsort(-var)[:n_genes_final]
    keep = np.unique(np.concatenate([top_hvg, hpv_pos]))[:n_genes_final + len(hpv_pos)]

    aligned_final = [e[:, keep] for e in aligned]
    final_genes = [all_genes[i] for i in keep]
    hpv_idx_in_final = [i for i, g in enumerate(final_genes) if g in KEGG_HPV_INFECTION_GENES]
    print(f"[align] final genes={len(final_genes)}, HPV genes in panel={len(hpv_idx_in_final)}")

    return aligned_final, final_genes, hpv_idx_in_final


def run_evaluator(all_raw, aligned_exp, final_genes, hpv_idx_in_final, device, regressor_name: str):
    """35-fold LOSO ridge/MLP → 每折独立算 HPV proxy AUC"""
    from sklearn.linear_model import RidgeCV
    from sklearn.neural_network import MLPRegressor

    # Build per-sample X matrices
    Xs = [d["X"] for d in all_raw]
    names = [d["name"] for d in all_raw]
    n_samples = len(names)

    folds = []
    for held_out in range(n_samples):
        t0 = time.time()
        # Train
        Xtr = np.concatenate([Xs[i] for i in range(n_samples) if i != held_out], axis=0)
        ytr = np.concatenate([aligned_exp[i] for i in range(n_samples) if i != held_out], axis=0)
        Xte = Xs[held_out]
        yte = aligned_exp[held_out]

        scaler_X = StandardScaler()
        Xtr = scaler_X.fit_transform(Xtr)
        Xte = scaler_X.transform(Xte)

        if regressor_name == "ridge":
            model = RidgeCV(alphas=np.logspace(-3, 2, 10))
            model.fit(Xtr, ytr)
            ypred = model.predict(Xte)
        elif regressor_name == "mlp":
            model = MLPRegressor(hidden_layer_sizes=(128, 64), early_stopping=True,
                                 validation_fraction=0.1, max_iter=150, random_state=0,
                                 learning_rate_init=1e-3, batch_size=2048)
            model.fit(Xtr, ytr)
            ypred = model.predict(Xte)
        else:
            raise ValueError(f"unknown {regressor_name}")

        # === HPV proxy label: 和 train_st.py L533-535 完全一致 ===
        true_hpv_mean = yte[:, hpv_idx_in_final].mean(axis=1)
        thr = np.median(true_hpv_mean)
        hpv_y = (true_hpv_mean >= thr).astype(int)

        # === Baseline "risk score": 用预测的 HPV 基因均值 ===
        pred_hpv_mean = ypred[:, hpv_idx_in_final].mean(axis=1)

        # === AUC ===
        if len(np.unique(hpv_y)) == 2 and np.std(pred_hpv_mean) > 1e-8:
            try:
                auc = roc_auc_score(hpv_y, pred_hpv_mean)
            except Exception:
                auc = float("nan")
        else:
            auc = float("nan")

        folds.append({
            "held_out": names[held_out],
            "n_spots": int(len(hpv_y)),
            "auc": float(auc) if not np.isnan(auc) else None,
            "true_hpv_mean": float(np.mean(true_hpv_mean)),
            "pred_hpv_mean": float(np.mean(pred_hpv_mean)),
            "fit_seconds": round(time.time() - t0, 1),
        })
        gc.collect()
        if (held_out + 1) % 5 == 0 or held_out == n_samples - 1:
            done = folds[-5:]
            avg_auc = np.nanmean([f["auc"] for f in folds if f["auc"] is not None]) if any(f["auc"] is not None for f in folds) else float("nan")
            print(f"  [fold {held_out+1}/{n_samples}] avg_AUC_so_far={avg_auc:.4f}  "
                  f"last_fold={folds[-1]['held_out']} AUC={folds[-1]['auc']}", flush=True)

    valid = [f for f in folds if f["auc"] is not None]
    summary = {
        "regressor": regressor_name,
        "n_samples": n_samples,
        "n_valid_folds": len(valid),
        "n_hpv_genes_in_final_panel": len(hpv_idx_in_final),
        "mean_auc": round(float(np.nanmean([f["auc"] for f in valid])), 4) if valid else None,
        "std_auc": round(float(np.nanstd([f["auc"] for f in valid])), 4) if valid else None,
        "median_auc": round(float(np.nanmedian([f["auc"] for f in valid])), 4) if valid else None,
        "per_fold": folds,
    }
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--fm", default="uni")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out", default="results/baseline_hpv_auc.json")
    ap.add_argument("--regressors", default="ridge,mlp",
                    help="comma-separated subset of ridge,mlp OR 'all' (adds knn)")
    ap.add_argument("--n_genes", type=int, default=2000)
    ap.add_argument("--patch_size", type=int, default=224)
    ap.add_argument("--max_folds", type=int, default=None)
    args = ap.parse_args()

    device = args.device
    regs = [r.strip() for r in args.regressors.split(",") if r.strip()]
    if args.regressors == "all": regs = ["ridge", "mlp", "knn"]

    all_raw = load_all_samples(Path(args.data), args.fm, device,
                               n_genes=args.n_genes, patch_size=args.patch_size,
                               sample_limit=args.max_folds)
    aligned, final_genes, hpv_idx = align_union(all_raw, n_genes_final=args.n_genes)

    summaries = []
    for reg in regs:
        print(f"\n===== Evaluating {reg} =====", flush=True)
        try:
            s = run_evaluator(all_raw, aligned, final_genes, hpv_idx, device, reg)
            summaries.append(s)
            print(f"  => mean AUC = {s['mean_auc']:.4f} ± {s['std_auc']:.4f}", flush=True)
        except Exception as e:
            tb = traceback.format_exc()
            print(f"  !! {reg} CRASHED: {type(e).__name__}: {e}\n{tb}", flush=True)
            summaries.append({"regressor": reg, "crash": str(e), "traceback": tb})

    out = {
        "generated": pd.Timestamp.now().isoformat(),
        "labels_used": "mean of KEGG_HPV genes (108) median-thresholded binary — MATCHES train_st.py L533-535",
        "gene_set": "KEGG_HPV_INFECTION (MSigDB v2025.1, 108 genes)",
        "n_hpv_genes_in_final_panel": len(hpv_idx),
        "samples": [d["name"] for d in all_raw],
        "per_regressor": summaries,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, default=str))

    # === FINAL SUMMARY ===
    print("\n===== BASELINE HPV PROXY AUC (TRUTHFUL) =====")
    print(json.dumps({r["regressor"]: {"mean_AUC": r.get("mean_auc"), "std": r.get("std_auc")}
                      for r in summaries if "mean_auc" in r}, indent=2))
    print(f"\nSaved → {out_path}")
    print("NOTE: Ridge AUC should be ~0.5 (random) — that's CORRECT.")
    print("Build_cmpb_paper_final.py hardcoded 0.0326 MUST BE DELETED.")


if __name__ == "__main__":
    main()
