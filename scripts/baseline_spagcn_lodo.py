# -*- coding: utf-8 -*-
"""baseline_spagcn_lodo.py — SpaGCN 已发表方法基线：同一 LODO 协议定量对比

回应审稿意见 C1（"未在统一 LODO 协议下运行 GraphST、SpaGCN 等已发表 ST 方法"）。

设计（方法学口径，投稿时照此描述）
------------------------------------
- 方法：SpaGCN（Hu et al. 2021, Nature Genetics）标准流程——表达 + 空间坐标构造图，
  louvain 初始化 + 图卷积聚类（固定 l=0.5、res=1.0，跳过官方 l 网格搜索，属"简化适配"）。
- 风险分数：SpaGCN 为逐样本无监督聚类（不接触疾病标签、无跨样本模型），因此
  35 个样本各独立运行一次即可；风险分数 = 每个 spot 所属空间簇的 HPV 通路均值
  表达（与主模型"HPV 通路锚定"风险定义对齐；无图像分支、无显式邻域一致性损失、
  无通路结构约束）。样本级风险 = 该样本各簇 HPV 活性的最大值（--risk_agg）。
- LODO 评估（与 results/leave_disease_out_summary.json 同口径）：对每个留出疾病样本，
  计算其样本级风险在 31 个正常样本中的百分位（严格低于其值的正常样本占比）、
  是否高于全部正常；同时报告留出样本逐 spot 风险分数的 Moran's I（k=6 最近邻，
  与主模型一致）。主模型 LODO 参考：mean_percentile=0.911、min=0.645、3/4 高于全部正常。
- 结论判读：若 SpaGCN 基线 mean_percentile 明显低于 0.911（如 <0.6），证明
  "无疾病锚定、无图像、仅空间图聚类"的已发表方法在数据稀缺 LODO 下无法达到
  本文泛化水平 → 直接回应 C1。

用法（Linux 服务器）
--------------------
    # 依赖（requirements.txt 已含 spaGCN>=1.2.0；如未装）：
    #   pip install "spaGCN>=1.2.0"
    python scripts/baseline_spagcn_lodo.py \
        --data data/st_visium \
        --histology_label_csv data/st_visium/labels/cervix_histology_labels_extended.csv \
        --exclude_substr breast,ovarian,prostate,visium_hd \
        --max_spots 2000 --n_jobs 4 \
        --out results/baseline_spagcn_lodo.json
    # 冒烟：--smoke 2 只跑前 2 个样本（验证 SpaGCN 环境可用）
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

warnings.filterwarnings("ignore")

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _import_spagcn():
    """Import SpaGCN with actionable guidance on failure."""
    try:
        import SpaGCN as spg  # noqa: F401
        return spg
    except ImportError:
        raise SystemExit(
            "SpaGCN 未安装。请在服务器执行：\n"
            "    pip install \"spaGCN>=1.2.0\"\n"
            "（项目 requirements.txt 已包含 spaGCN>=1.2.0；确认激活的是项目环境）"
        )


spg = _import_spagcn()

# ---------------------------------------------------------------------------
# HPV 通路基因面板（与主实验同款：docs/hpv_genes.json，KEGG_HPV_INFECTION 108 基因）
# ---------------------------------------------------------------------------
_HPV_GENES_FALLBACK = [
    "TP63", "CDKN2A", "MYC", "CCND1", "EGFR", "PIK3CA", "KRAS", "EP300", "GATA3", "KRT8",
    "KRT18", "MKI67", "PCNA", "CD274", "PDCD1LG2", "CTLA4", "FOXP3", "CD8A", "CD4", "IL2RG",
    "STAT1", "IRF1", "MX1", "OAS1", "E2F1", "E2F2", "E2F3", "RB1", "CCNE1", "CCNA2", "PLK1",
    "AURKA", "TOP2A", "BUB1", "CENPF", "TK1", "RRM2", "TYMS", "HMGB2", "KPNA2",
]


def _load_hpv_genes() -> list[str]:
    p = ROOT / "docs" / "hpv_genes.json"
    if p.exists():
        try:
            genes = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(genes, dict):  # 兼容 {gene: ...} 结构
                genes = list(genes.keys())
            return [str(g) for g in genes]
        except Exception as e:
            print(f"[warn] 解析 {p} 失败（{e}），回退内置 HPV 基因表")
    return list(_HPV_GENES_FALLBACK)


# ---------------------------------------------------------------------------
# 样本发现 / 标签读取（与 scripts/leave_disease_out.py 同逻辑）
# ---------------------------------------------------------------------------
def _is_visium_dir(d: Path) -> bool:
    if not d.is_dir():
        return False
    if (d / "filtered_feature_bc_matrix.h5").exists():
        return True
    br = d / "binned_outputs"
    if br.exists():
        for sub in sorted([p for p in br.iterdir() if p.is_dir()]):
            if (sub / "filtered_feature_bc_matrix.h5").exists():
                return True
    return False


def _leaf(sid: str) -> str:
    sid = sid.strip()
    return sid[len("ecto_"):] if sid.startswith("ecto_") else sid


def _read_labels(csv_path: Path, exclude_substr: str) -> tuple[list[str], set[str]]:
    """返回 (disease_leaf_names, normal_leaf_names)。progression_ordinal>=1 为疾病。"""
    import csv
    required = {"sample_id", "progression_ordinal"}
    rows = []
    with open(csv_path, encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise SystemExit(f"histology CSV 为空或表头缺失: {csv_path}")
        missing = required - set(reader.fieldnames)
        if missing:
            raise SystemExit(f"histology CSV 缺少列: {missing}")
        for row in reader:
            rows.append(row)
    disease, normals = [], set()
    for row in rows:
        try:
            ordinal = int(row["progression_ordinal"])
        except (TypeError, ValueError):
            continue
        leaf = _leaf(str(row["sample_id"]))
        if exclude_substr and any(x in leaf for x in exclude_substr.split(",")):
            continue
        if ordinal >= 1:
            disease.append(leaf)
        else:
            normals.add(leaf)
    seen, out = set(), []
    for d in disease:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out, normals


def discover_samples(data_root: Path, keep_names: set[str]) -> list[Path]:
    """扫描 data 根目录下所有 Visium 子目录，保留 CSV 名单内的样本。"""
    out = []
    for sub in sorted(data_root.iterdir()):
        if not sub.is_dir():
            continue
        if _is_visium_dir(sub):
            if sub.name in keep_names:
                out.append(sub)
            continue
        # 嵌套一层（geo_cesc/CA_HPV_1 等）
        for sub2 in sorted(sub.iterdir()):
            if sub2.is_dir() and _is_visium_dir(sub2) and sub2.name in keep_names:
                out.append(sub2)
    missing = keep_names - {d.name for d in out}
    if missing:
        print(f"[warn] 名单中未找到目录的样本: {sorted(missing)}")
    return out


# ---------------------------------------------------------------------------
# 单样本 SpaGCN → 簇级 HPV 活性 → 逐 spot 风险分数
# ---------------------------------------------------------------------------
def run_spagcn_sample(sample_dir: Path, hpv_genes: list[str], args) -> dict:
    t0 = time.time()
    from src.st_data import load_sample
    from src.models import moran_i

    sample = load_sample(sample_dir)
    X = np.asarray(sample.expression, dtype=np.float32)  # (spots, genes)
    genes = list(sample.genes)
    coords = np.asarray(sample.coords, dtype=float)      # (spots, 2) hires px

    n0 = X.shape[0]
    if args.max_spots and n0 > args.max_spots:
        rng = np.random.RandomState(42)
        idx = rng.choice(n0, args.max_spots, replace=False)
        X, coords = X[idx], coords[idx]

    g2i = {g: i for i, g in enumerate(genes)}
    hpv_idx = [g2i[g] for g in hpv_genes if g in g2i]
    n_hpv = len(hpv_idx)
    if n_hpv == 0:
        raise ValueError(
            f"{sample_dir.name}: HPV 通路基因与表达矩阵无交集，风险定义不可用。"
            f"请检查 docs/hpv_genes.json 与表达矩阵基因名（如均大写/均小写）")
    if n_hpv < 30:
        print(f"  [warn] {sample_dir.name}: HPV 通路基因交集仅 {n_hpv} 个，"
              f"风险定义不稳定，请检查 docs/hpv_genes.json 与表达矩阵基因名")

    # ---- 构造 anndata：SpaGCN 需要 log1p 归一化表达 + obsm['spatial'] ----
    import scanpy as sc
    import anndata as ad
    adata = ad.AnnData(X)
    adata.var_names = genes
    adata.obsm["spatial"] = coords
    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)

    # ---- SpaGCN 邻接矩阵（兼容不同版本签名） ----
    try:
        adj = spg.calculate_adj_matrix(adata, histology=False,
                                       beta=args.adj_beta, alpha=1)
    except TypeError:
        adj = spg.calculate_adj_matrix(adata, beta=args.adj_beta, alpha=1)

    spgcn = spg.SpaGCN()
    spgcn.set_l(args.l)
    spgcn.train(adj, num_pcs=args.num_pcs, init_spa=True, init="louvain",
                res=args.res, tol=5e-3)
    pred, _prob = spgcn.predict()
    pred = np.asarray(pred)

    # ---- 簇级 HPV 活性 → 逐 spot 风险分数 ----
    hpv_expr = np.asarray(adata.X.todense() if hasattr(adata.X, "todense")
                          else adata.X)[:, hpv_idx].mean(axis=1)
    clusters = np.unique(pred)
    cluster_activity: dict[int, float] = {}
    for c in clusters:
        cluster_activity[int(c)] = float(hpv_expr[pred == c].mean())
    spot_risk = np.array([cluster_activity[int(c)] for c in pred], dtype=float)
    act_vals = np.array(list(cluster_activity.values()), dtype=float)

    moran = float(moran_i(spot_risk, coords, k=6))

    result = {
        "sample": sample_dir.name,
        "n_spots": int(n0),
        "n_spots_used": int(X.shape[0]),
        "n_clusters": int(len(clusters)),
        "n_hpv_genes_intersect": int(n_hpv),
        "cluster_activity": {str(k): round(float(v), 6)
                             for k, v in sorted(cluster_activity.items())},
        "risk_max": float(act_vals.max()),
        "risk_p90": float(np.percentile(act_vals, 90)),
        "risk_top2_mean": float(np.sort(act_vals)[-2:].mean()),
        "moran_i_spot_risk": moran,
        "elapsed_sec": round(time.time() - t0, 1),
    }
    print(f"  [done] {sample_dir.name}: spots={result['n_spots_used']} "
          f"clusters={result['n_clusters']} risk_max={result['risk_max']:.4f} "
          f"moran={moran:.4f} ({result['elapsed_sec']}s)", flush=True)
    return result


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="SpaGCN 基线：同一 LODO 协议对比（回应 C1）")
    ap.add_argument("--data", default="data/st_visium")
    ap.add_argument("--histology_label_csv",
                    default="data/st_visium/labels/cervix_histology_labels_extended.csv")
    ap.add_argument("--exclude_substr", default="breast,ovarian,prostate,visium_hd")
    ap.add_argument("--hpv_gene_set", default="docs/hpv_genes.json")
    ap.add_argument("--out", default="results/baseline_spagcn_lodo.json")
    ap.add_argument("--max_spots", type=int, default=2000,
                    help="每样本最大 spot 数（随机抽样，控制邻接矩阵与训练成本）")
    ap.add_argument("--n_jobs", type=int, default=1, help="并行样本数（Linux 建议 4）")
    ap.add_argument("--smoke", type=int, default=0,
                    help=">0 时只跑前 N 个样本（环境验证）")
    # SpaGCN 超参（简化适配，固定值）
    ap.add_argument("--l", type=float, default=0.5)
    ap.add_argument("--res", type=float, default=1.0)
    ap.add_argument("--num_pcs", type=int, default=50)
    ap.add_argument("--adj_beta", type=int, default=49)
    ap.add_argument("--risk_agg", default="max",
                    choices=["max", "p90", "top2_mean"],
                    help="样本级风险聚合（默认 max；其余口径同时输出，仅用于敏感性参考）")
    ap.add_argument("--device", default="cpu", help="cpu 或 cuda（SpaGCN 小图 CPU 通常更快）")
    args = ap.parse_args()

    if args.device.startswith("cuda"):
        try:
            import torch
            if not torch.cuda.is_available():
                print("[warn] --device cuda 但无可用 GPU，回退 cpu")
                args.device = "cpu"
        except Exception:
            print("[warn] torch 不可用，回退 cpu")
            args.device = "cpu"

    data_root = Path(args.data)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    samples_cache = out_path.with_name(out_path.stem + ".samples.json")

    hpv_genes = _load_hpv_genes()
    print(f"[SpaGCN baseline] hpv_gene_panel={len(hpv_genes)} 来自 {args.hpv_gene_set}")

    disease, normals = _read_labels(Path(args.histology_label_csv), args.exclude_substr)
    keep = set(disease) | set(normals)
    print(f"[labels] disease({len(disease)}): {disease}")
    print(f"[labels] normal({len(normals)}): {len(normals)} 个")

    sample_dirs = discover_samples(data_root, keep)
    print(f"[data] 命中样本目录 {len(sample_dirs)} 个: {[d.name for d in sample_dirs]}")
    if args.smoke:
        sample_dirs = sample_dirs[:args.smoke]
        print(f"[smoke] 仅跑前 {len(sample_dirs)} 个样本")

    # ---- 续跑：已有结果缓存则跳过 ----
    done = {}
    if samples_cache.exists():
        try:
            done = {r["sample"]: r for r in json.loads(samples_cache.read_text())}
            print(f"[cache] 已有 {len(done)} 个样本结果，跳过已完成的")
        except Exception:
            done = {}
    todo = [d for d in sample_dirs if d.name not in done]

    if todo:
        if args.n_jobs > 1 and len(todo) > 1:
            print(f"[run] 并行 n_jobs={args.n_jobs} 处理 {len(todo)} 个样本 ...", flush=True)
            with ProcessPoolExecutor(max_workers=args.n_jobs) as ex:
                futures = {ex.submit(run_spagcn_sample, d, hpv_genes, args): d
                           for d in todo}
                for fut in futures:
                    d = futures[fut]
                    try:
                        done[d.name] = fut.result()
                    except Exception as e:
                        import traceback
                        print(f"  [FAIL] {d.name}: {e}\n{traceback.format_exc()}", flush=True)
                        done[d.name] = {"sample": d.name, "error": str(e)}
        else:
            for i, d in enumerate(todo, 1):
                print(f"\n[run {i}/{len(todo)}] {d.name} ...", flush=True)
                try:
                    done[d.name] = run_spagcn_sample(d, hpv_genes, args)
                except Exception as e:
                    import traceback
                    print(f"  [FAIL] {d.name}: {e}\n{traceback.format_exc()}", flush=True)
                    done[d.name] = {"sample": d.name, "error": str(e)}
                gc.collect()
        # 保存缓存
        samples_cache.write_text(
            json.dumps(list(done.values()), indent=2, default=str, ensure_ascii=False))
        print(f"[cache] 已保存样本级结果: {samples_cache}")

    # ---- LODO 汇总（同 leave_disease_out.py 口径） ----
    agg_key = f"risk_{args.risk_agg}"
    folds = []
    valid_disease = [d for d in disease if d in done and "error" not in done[d]]
    for dname in valid_disease:
        ho = done[dname]
        normal_risks = [done[n][agg_key] for n in sorted(normals)
                        if n in done and "error" not in done[n]]
        if not normal_risks:
            continue
        ho_risk = ho[agg_key]
        norm_arr = sorted(normal_risks)
        below = sum(1 for x in norm_arr if x < ho_risk)
        folds.append({
            "holdout_sample": dname,
            "holdout_risk": round(ho_risk, 6),
            "n_normal": len(norm_arr),
            "percentile_vs_normal": below / len(norm_arr),
            "above_median_normal": bool(ho_risk > norm_arr[len(norm_arr) // 2]),
            "above_all_normal": bool(ho_risk > max(norm_arr)),
            "moran_i_spot_risk": ho.get("moran_i_spot_risk"),
            "n_clusters": ho.get("n_clusters"),
        })
        print(f"  holdout {dname}: risk={ho_risk:.4f} "
              f"percentile={below/len(norm_arr):.3f} "
              f"above_all={ho_risk > max(norm_arr)} "
              f"moran={ho.get('moran_i_spot_risk')}")

    percentiles = [f["percentile_vs_normal"] for f in folds]
    summary = {
        "description": ("SpaGCN 已发表方法基线：同一 LODO 协议下疾病-正常风险排序泛化 "
                        "(风险=空间簇的 HPV 通路均值表达，风险聚合=" + args.risk_agg + ")"),
        "method": "SpaGCN",
        "hpv_gene_panel_n": len(hpv_genes),
        "risk_agg": args.risk_agg,
        "spagcn_hyperparams": {"l": args.l, "res": args.res, "num_pcs": args.num_pcs,
                               "adj_beta": args.adj_beta},
        "main_model_reference": {"mean_percentile": 0.9113, "min_percentile": 0.6452,
                                 "n_above_all_normal": "3/4", "moran_i": 0.8665,
                                 "source": "results/leave_disease_out_summary.json + "
                                           "results_CERVIX35_PROG.json"},
        "n_disease_folds": len(folds),
        "n_successful_folds": len(valid_disease),
        "mean_percentile_vs_normal": round(float(np.mean(percentiles)), 4) if percentiles else None,
        "min_percentile_vs_normal": round(float(np.min(percentiles)), 4) if percentiles else None,
        "n_above_all_normal": sum(1 for f in folds if f["above_all_normal"]),
        "n_above_median_normal": sum(1 for f in folds if f["above_median_normal"]),
        "mean_moran_i_spot_risk": round(float(np.nanmean(
            [f["moran_i_spot_risk"] for f in folds if f.get("moran_i_spot_risk") is not None])), 4),
        "folds": folds,
    }
    out_path.write_text(json.dumps(summary, indent=2, default=str, ensure_ascii=False))
    print("\n===== SPA GCN LODO SUMMARY =====")
    print(f"method=spaGCN  risk_agg={args.risk_agg}")
    print(f"mean percentile-vs-normal: {summary['mean_percentile_vs_normal']} "
          f"(主模型参考 0.911)")
    print(f"min percentile:            {summary['min_percentile_vs_normal']} "
          f"(主模型参考 0.645)")
    print(f"above ALL normals:         {summary['n_above_all_normal']}/{len(folds)} "
          f"(主模型参考 3/4)")
    print(f"mean Moran's I (留出):      {summary['mean_moran_i_spot_risk']} "
          f"(主模型 0.866 为全样本口径，仅参考)")
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
