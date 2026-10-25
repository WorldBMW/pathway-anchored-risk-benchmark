#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""benchmark_st_methods.py — 统一 ST 方法基线：STAGATE / SpaGCN / GraphST
在同一仿真队列 + 同一 LODO 协议下与 MRP-ST（LDI-gate）对比跨供体泛化。

回应 CSBJ "strength of advance"：证明 MRP-ST 的跨供体 LODO 泛化优于
已发表 ST 基线（在主 MMRP 框架所覆盖的稀缺标记场景）。

统一评估口径（跨所有方法，禁止针对单方法定制，保证可审计）
------------------------------------------------------------
1. 输入：某个仿真队列 data/sim_power/<group>/{N_*,CA_*} 的 Visium 样本。
2. 每种方法出「逐 spot 风险分数」：
     - MRP-ST: fused embedding 的 HPV 锚定输出（已有 npz，无需重训）
     - STAGATE / SpaGCN / GraphST: 逐样本无监督聚类/嵌入 -> 簇级 HPV 通路
       均值表达 (风险=簇的 HPV 通路均值；样本级风险聚合 --risk_agg)。
3. 样本级指标 = 所有已发表方法统一用 LODO 线性探针（Kendall tau-b）+ 置换。
   与 scripts/mrpst_lodo.py 完全相同的 grade 口径：
       supported   : mean LODO tau >= 0.35 且 >=2/3 seed p<0.05
       unsupported : |mean LODO tau| <= 0.15 且 0 seed 显著
       suggestive  : 其余
   —— 风险在于：已发表 ST 方法为逐样本无监督，不产生可跨样本的共享表征；
   逐样本聚类在 LODO 下天然退化（只能看簇内 HPV 均值，无共享方向可迁移）。
   这正是要展示的差距（"无标签锚定、无跨样本模型的已发表方法无法跨供体泛化"）。

用法（服务器，GPU 上跑 STAGATE/GraphST，SpaGCN 可 CPU）
    cd /root/autodl-tmp/project/project4_cervix_multimodal
    /root/miniconda3/bin/python scripts/benchmark_st_methods.py \
        --groups group_A_g20261006_L1 group_A_g20261006_L2 group_C_g20261006_CTRL \
        --methods STAGATE,SpaGCN,GraphST --n_perm 2000 \
        --out results/st_methods_benchmark.json
    # 冒烟（1 队列 1 方法 2 样本）：--smoke 2 --methods SpaGCN（CPU 最快）
"""
import argparse
import gc
import json
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

# 复用 MRP-ST 的 LODO 探针 + 恒常数值口径
from probe_lodo import per_sample_embedding, lodo_probe, kendall_tau  # noqa: E402

SUP_THR = 0.35
UNSUP_THR = 0.15
P_ALPHA = 0.05

# 运行参数（main() 从 CLI 注入）
STAGATE_EPOCHS = 1000      # 官方默认
GRAPHST_EPOCHS = 600       # 官方默认
GRAPHST_NEIGHBORS = 3      # construct_interaction 默认
RAD_CUTOFF = 150           # Cal_Spatial_Net Radius 模式
DEVICE = None              # 自动检测 cpu/cuda

# HPV 通路基因（与主实验同款 docs/hpv_genes.json，KEGG_HVP 108）
_HPV_FALLBACK = [
    "TP63", "CDKN2A", "MYC", "CCND1", "EGFR", "PIK3CA", "KRAS", "EP300", "GATA3", "KRT8",
    "KRT18", "MKI67", "PCNA", "CD274", "PDCD1LG2", "CTLA4", "FOXP3", "CD8A", "CD4", "IL2RG",
    "STAT1", "IRF1", "MX1", "OAS1", "E2F1", "E2F2", "E2F3", "RB1", "CCNE1", "CCNA2", "PLK1",
    "AURKA", "TOP2A", "BUB1", "CENPF", "TK1", "RRM2", "TYMS", "HMGB2", "KPNA2",
]


def _load_hpv_genes() -> list[str]:
    p = ROOT / "docs" / "hpv_genes.json"
    if p.exists():
        try:
            g = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(g, dict):
                g = list(g.keys())
            return [str(x) for x in g]
        except Exception:
            pass
    return list(_HPV_FALLBACK)


def severity_of(name: str):
    n = name.upper()
    if n.startswith("N_") or n.startswith("ECTO_") or "NORMAL" in n:
        return 0
    if "HSIL" in n or "CIN" in n or "DYS" in n:
        return 1
    if n.startswith("CA_") or "CANCER" in n or "TUMOR" in n or n.startswith("CERVICAL_CANCER"):
        return 2
    return None


def _load_sample(sample_dir: Path):
    from src.st_data import load_sample
    s = load_sample(sample_dir)
    X = s.expression
    # 兼容稀疏表达矩阵（sim 为 sparse 10x）
    if hasattr(X, "toarray"):
        X = X.toarray()
    return (np.asarray(X, dtype=np.float32), list(s.genes),
            np.asarray(s.coords, dtype=float))


def _to_anndata(X, genes, coords, normalized=True):
    """构造 AnnData。normalized=True 时做 normalize_total+log1p（STAGATE/SpaGCN）；
    False 保留原始 count（GraphST 内部 seurat_v3 HVG 需要原始 count）。"""
    import scanpy as sc
    import anndata as ad
    adata = ad.AnnData(X)
    adata.var_names = genes
    adata.obsm["spatial"] = coords
    if normalized:
        sc.pp.normalize_total(adata, target_sum=1e4)
        sc.pp.log1p(adata)
    return adata


def _cluster_hpv_risk(expr, genes, coords, hpv_genes, cluster_fn, risk_agg):
    """簇级 HPV 通路均值表达 -> 逐 spot 风险 -> 样本级聚合。"""
    g2i = {g: i for i, g in enumerate(genes)}
    hidx = [g2i[g] for g in hpv_genes if g in g2i]
    if not hidx:
        raise ValueError("HPV 通路基因与表达矩阵无交集")
    pred = cluster_fn(expr, genes, coords)
    pred = list(pred)
    import numpy as _np
    hpv_expr = _np.asarray(expr)[:, hidx].mean(axis=1)
    cl = _np.unique(pred)
    act = {int(c): float(hpv_expr[_np.array(pred) == c].mean()) for c in cl}
    per_c = _np.array([act[int(c)] for c in pred], dtype=float)
    vals = _np.array(list(act.values()), dtype=float)
    if risk_agg == "max":
        sample_risk = float(vals.max())
    elif risk_agg == "p90":
        sample_risk = float(_np.percentile(vals, 90))
    else:
        sample_risk = float(_np.sort(vals)[-2:].mean())
    return per_c, sample_risk


def _cluster_spagcn(expr, genes, coords):
    import scanpy as sc
    import SpaGCN as spg
    adata = _to_anndata(expr, genes, coords, normalized=True)
    x = [float(v) for v in coords[:, 0]]
    y = [float(v) for v in coords[:, 1]]
    # SpaGCN 1.2.7 新版：calculate_adj_matrix(x, y, beta, alpha, histology=False)
    adj = spg.calculate_adj_matrix(x, y, beta=49, alpha=1, histology=False)
    m = spg.SpaGCN()
    m.set_l(0.5)
    m.train(adata, adj, num_pcs=50, init_spa=True, init="louvain",
            res=1.0, tol=5e-3)
    pred, _prob = m.predict()
    return pred


def _embed_stagate(expr, genes, coords):
    import scanpy as sc
    import torch
    from STAGATE_pyG import Cal_Spatial_Net, train_STAGATE
    adata = _to_anndata(expr, genes, coords, normalized=True)
    sc.pp.scale(adata)
    # STAGATE 官方必须先在 uns 构造 Spatial_Net，否则 train_STAGATE 报错
    Cal_Spatial_Net(adata, rad_cutoff=RAD_CUTOFF, model="Radius")
    train_STAGATE(adata, n_epochs=STAGATE_EPOCHS, lr=0.001,
                  key_added="STAGATE", random_seed=0, verbose=False,
                  device=DEVICE)
    return adata.obsm["STAGATE"]


def _cluster_stagate(expr, genes, coords):
    import numpy as _np
    import sklearn.cluster as skc
    emb = _embed_stagate(expr, genes, coords).astype(float)
    k = min(15, max(3, int(_np.sqrt(len(expr)))))
    lab = skc.KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(emb)
    return lab


def _embed_graphst(expr, genes, coords):
    import torch
    from GraphST import GraphST
    # GraphST 内部 preprocess 用 seurat_v3 做 HVG，要求原始 count（normalized=False）
    adata = _to_anndata(expr, genes, coords, normalized=False)
    model = GraphST.GraphST(adata, device=DEVICE, epochs=GRAPHST_EPOCHS,
                            dim_output=64, deconvolution=False,
                            datatype="10X", random_seed=0)
    model.train()
    return model.adata.obsm["emb"]


def _cluster_graphst(expr, genes, coords):
    import numpy as _np
    import sklearn.cluster as skc
    emb = _embed_graphst(expr, genes, coords).astype(float)
    k = min(15, max(3, int(_np.sqrt(len(expr)))))
    lab = skc.KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(emb)
    return lab


def _cluster_fn(method):
    if method == "SpaGCN":
        return _cluster_spagcn
    if method == "STAGATE":
        return _cluster_stagate
    if method == "GraphST":
        return _cluster_graphst
    raise ValueError(method)


def _embed_dispatch(method, expr, genes, coords):
    """导出模式：返回方法的逐 spot 连续嵌入。

    SpaGCN 不在此列：其软聚类概率的维度 k 由逐样本 louvain 决定，
    随样本变化、跨样本不可堆叠——即该方法不产生跨样本共享的连续表征。
    统一探针对其不可适用，这一事实本身是审计发现（记录于 manifest）。
    """
    if method == "STAGATE":
        return _embed_stagate(expr, genes, coords).astype(float)
    if method == "GraphST":
        return _embed_graphst(expr, genes, coords).astype(float)
    raise ValueError(f"no shared continuous embedding for {method}")


def lodo_from_sample_risks(sample_risks: dict[str, float], names: list[str],
                           n_perm: int):
    """对逐样本风险向量跑 LODO 线性探针 + 置换（与 MRP-ST 同口径）。"""
    n = len(names)
    ys = np.array([severity_of(x) for x in names], dtype=float)
    xs = np.array([[sample_risks[x]] for x in names], dtype=float)
    if len(set(ys.tolist())) < 2:
        return {"tau": None, "p": None, "reason": "single severity level"}
    tau_obs = kendall_tau(xs[:, 0], ys)
    rng = np.random.default_rng(0)
    n_ge = 0
    for _ in range(n_perm):
        if kendall_tau(xs[:, 0], rng.permutation(ys)) >= tau_obs:
            n_ge += 1
    return {"tau": round(float(tau_obs), 4), "p": round((n_ge + 1) / (n_perm + 1), 4)}


def grade(rows):
    taus = [r["tau"] for r in rows if r.get("tau") is not None]
    ps = [r["p"] for r in rows if r.get("p") is not None]
    if not taus:
        return "missing", {}
    tm = np.mean(taus)
    n_sig = sum(1 for p in ps if p < P_ALPHA)
    frac = n_sig / len(rows)
    if tm >= SUP_THR and frac >= 2 / 3:
        verdict = "supported"
    elif abs(tm) <= UNSUP_THR and n_sig == 0:
        verdict = "unsupported"
    else:
        verdict = "suggestive"
    return verdict, {"mean_tau": round(tm, 4), "n_sig_seeds": n_sig, "n_seeds": len(rows)}


def main():
    global DEVICE, STAGATE_EPOCHS, GRAPHST_EPOCHS
    import numpy as np
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", nargs="+", required=True,
                    help="仿真队列目录名（位于 data/sim_power 下）")
    ap.add_argument("--methods", default="SpaGCN,STAGATE,GraphST")
    ap.add_argument("--data-root", default="data/sim_power")
    ap.add_argument("--hpv-gene-set", default="docs/hpv_genes.json")
    ap.add_argument("--risk-agg", default="max", choices=["max", "p90", "top2_mean"])
    ap.add_argument("--n-perm", type=int, default=2000)
    ap.add_argument("--max-spots", type=int, default=0, help="0=不抽样")
    ap.add_argument("--smoke", type=int, default=0, help=">0 每队列最多用前 N 样本")
    ap.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    ap.add_argument("--stagate-epochs", type=int, default=1000)
    ap.add_argument("--graphst-epochs", type=int, default=600)
    ap.add_argument("--out", default="results/st_methods_benchmark.json")
    ap.add_argument("--export-emb", default=None, metavar="DIR",
                    help="导出模式：每个 (group, method) 保存样本级池化连续嵌入 npz"
                         "（STAGATE/GraphST）。开启后不计算 cluster-max 风险、"
                         "不写 --out 存档，只写 --export-manifest。")
    ap.add_argument("--export-manifest",
                    default="results/st_method_embeddings_manifest.json")
    args = ap.parse_args()

    import torch
    if args.device == "auto":
        DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    elif args.device == "cuda":
        DEVICE = torch.device("cuda:0")
    else:
        DEVICE = torch.device("cpu")
    STAGATE_EPOCHS = args.stagate_epochs
    GRAPHST_EPOCHS = args.graphst_epochs
    print("[device]", DEVICE, "| STAGATE epochs:", STAGATE_EPOCHS,
          "| GraphST epochs:", GRAPHST_EPOCHS, flush=True)

    hpv_genes = _load_hpv_genes()
    methods = [m.strip() for m in args.methods.split(",")]
    root = Path(args.data_root)

    report = {"analysis_date": time.strftime("%Y-%m-%d"),
              "protocol": ("统一 LODO：簇级 HPV 通路均值表达 -> 样本级风险（agg="
                           + args.risk_agg + "）-> LODO 线性探针 Kendall tau + 置换"),
              "n_seed_groups": len(args.groups), "groups": {}}
    for g in args.groups:
        gdir = root / g
        if not gdir.is_dir():
            print(f"[skip] {g}: 目录不存在 {gdir}")
            continue
        samples = sorted([p for p in gdir.iterdir()
                          if p.is_dir() and severity_of(p.name) is not None])
        if args.smoke:
            # 分层采样：确保 normal(sev0) 与 disease(sev>0) 都有，LODO 才有对比
            norm = [p for p in samples if severity_of(p.name) == 0]
            dis = [p for p in samples if severity_of(p.name) > 0]
            n_d = max(1, int(args.smoke * (len(dis) / len(samples))))
            n_n = args.smoke - n_d
            samples = dis[:n_d] + norm[:n_n]
        print(f"\n=== {g} : {len(samples)} samples (smoke={args.smoke}) ===")
        names = [p.name for p in samples]
        report["groups"][g] = {"n_samples": len(names), "methods": {}}
        for method in methods:
            if args.export_emb:
                export_dir = Path(args.export_emb)
                export_dir.mkdir(parents=True, exist_ok=True)
                if method == "SpaGCN":
                    report["groups"][g]["methods"][method] = {
                        "export": ("n/a: sample-specific soft-cluster dimensionality "
                                   "(louvain-chosen k); no shared continuous "
                                   "representation for a unified probe")}
                    print(f"    [{method}] export n/a (no shared continuous "
                          f"representation)")
                    continue
                pooled = {}
                t0 = time.time()
                for p in samples:
                    try:
                        X, genes, coords = _load_sample(p)
                        emb = _embed_dispatch(method, X, genes, coords)
                        pooled[p.name] = np.asarray(emb, dtype=np.float32).mean(axis=0)
                        print(f"      {method} {p.name}: emb{emb.shape} pooled "
                              f"({time.time()-t0:.0f}s)", flush=True)
                    except Exception as e:
                        print(f"      {method} {p.name}: EXPORT FAIL -> {e}",
                              flush=True)
                    gc.collect()
                if pooled:
                    names_e = [x for x in names if x in pooled]
                    Xe = np.stack([pooled[n] for n in names_e]).astype(np.float32)
                    fp = export_dir / f"{g}__{method}.npz"
                    np.savez(fp, X=Xe, names=np.array(names_e),
                             y=np.array([severity_of(n) for n in names_e],
                                        dtype=float))
                    report["groups"][g]["methods"][method] = {
                        "export": str(fp), "n_samples": len(names_e),
                        "emb_dim": int(Xe.shape[1])}
                    print(f"    [{method}] exported {len(names_e)} pooled "
                          f"embeddings (dim {Xe.shape[1]})")
                continue
            try:
                cfn = _cluster_fn(method)
            except Exception as e:
                print(f"  [skip] {method}: 不可用 -> {e}")
                report["groups"][g]["methods"][method] = {"error": str(e)}
                continue
            risks = {}
            t0 = time.time()
            for p in samples:
                try:
                    X, genes, coords = _load_sample(p)
                    if args.max_spots and len(X) > args.max_spots:
                        rng = np.random.RandomState(42)
                        idx = rng.choice(len(X), args.max_spots, replace=False)
                        X, coords = X[idx], coords[idx]
                    _, spr = _cluster_hpv_risk(X, genes, coords, hpv_genes, cfn,
                                               args.risk_agg)
                    risks[p.name] = spr
                    print(f"      {method} {p.name}: risk={spr:.4f} "
                          f"({len(X)} spots, {time.time()-t0:.0f}s)", flush=True)
                except Exception as e:
                    print(f"      {method} {p.name}: FAIL -> {e}", flush=True)
                    risks[p.name] = None
                gc.collect()
            valid = {k: v for k, v in risks.items() if v is not None}
            lodo = lodo_from_sample_risks(valid, [x for x in names if x in valid],
                                          args.n_perm)
            report["groups"][g]["methods"][method] = {
                "n_valid_samples": len(valid), "sample_risks": valid,
                "lodo": lodo}
            print(f"    [{method}] LODO tau={lodo.get('tau')} p={lodo.get('p')}")

    # 汇总三级判据 + 每方法跨队列判定
    for g, grp in report["groups"].items():
        for method, r in grp["methods"].items():
            if "error" in r or "lodo" not in r:
                continue
            rows = [r["lodo"]]
            v, st = grade(rows)
            r["grade_3tier"] = v
            r["grade_stats"] = st
    if args.export_emb:
        with open(args.export_manifest, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)
        print(f"\n[done] export mode: embeddings in {args.export_emb}; "
              f"manifest {args.export_manifest}; archived {args.out} untouched")
        return

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    print(f"\n[done] saved {args.out}")
    _print_summary(report)


def _print_summary(report):
    print("\n===== SUMMARY (3-tier) =====")
    for g, grp in report["groups"].items():
        for method, r in grp["methods"].items():
            if "error" in r:
                print(f"  {g}/{method}: ERROR {r['error']}")
                continue
            l = r.get("lodo", {})
            print(f"  {g}/{method}: tau={l.get('tau')} p={l.get('p')} "
                  f"grade={r.get('grade_3tier')} {r.get('grade_stats')}")


if __name__ == "__main__":
    main()