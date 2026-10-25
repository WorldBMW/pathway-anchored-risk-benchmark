#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""exp_within_group_label_geomx.py — 标签「组内是否变化」的受控对照实验。

动机（v13 评审遗留项）
----------------------
论文 Table 的 18 个 dosed cell 里只有 3 个通过双门。此前的解释是"队列可行性
排序"，但缺少一个**机制性**解释：为什么多数队列修不动？

候选机制：当 label 是**供体派生**、因而在组内恒定时（宫颈 prog_y、HNSCC HPV 状态、
前列腺癌分期），identity 通道与 task 通道携带的是同一份信息 —— 抹掉身份必然同时
抹掉任务信号，因此 LDI 门与保真门不可兼得。反之，当 label 在**组内变化**（同一
患者的不同区域有不同病理读数）时，两个通道可分离，修复才可能通过双门。

本实验在**同一个数据集**上检验这条机制：特征矩阵 X 与分组变量 g 完全不变，
只更换标签 y，而 y 的组内变异程度形成一个梯度。任何读数差异都只能来自标签的
变异结构，不能来自数据、嵌入或分组。

数据集
------
GSE316098（NanoString GeoMx DSP，宫颈组织）：186 个 ROI（region of interest），
来自 7 个病例（caseid WU-01..WU-07，每组 8–44 个 ROI）。每个 ROI 带独立病理标注，
因此标签在**组内真实变化**，而不是供体派生后广播给所有单位。

三个 arm（组内变异度递增）
--------------------------
  A. risk        患者风险分层  Normal(0) < Low(1) < High(2)；多数组内恒定
  B. silva       Silva 浸润模式 normal(0) < A(1) < B(2) < C(3)；ROI 级病理读数，
                 5/7 组内变化
  C. cell_type   上皮 / 基质  epi(0) vs stroma(1)；ROI 级，7/7 组内变化且与组正交

仪器与算子逐字复用 exp_crossdomain_audit.py（与 HAR / gas / 宫颈阶梯同一口径）。

用法
----
    python scripts/exp_within_group_label_geomx.py                 # CPU，约 20-40 分钟
    python scripts/exp_within_group_label_geomx.py --epochs 30 --topg 2000
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(Path(__file__).resolve()).parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

from exp_crossdomain_audit import (  # noqa: E402
    run_domain, norm_mi, LDI_GATE, TAU_PERP, FIDELITY_KEEP, PERM_SEED,
)

DATA = ROOT / "data" / "st_visium" / "geo_cervical_geomx_GSE316098"
RES = ROOT / "results"

RISK_ORD = {"Normal": 0, "Low": 1, "High": 2}
SILVA_ORD = {"normal": 0, "A": 1, "B": 2, "C": 3}
CELL_ORD = {"epi": 0, "stroma": 1}


# --------------------------------------------------------------- 数据
def load_geomx(top_gene: int = 2000, min_det: int = 20):
    """返回 X (n_ROI x top_gene, log-CPM), meta (dict by title), roi titles."""
    import pandas as pd

    meta = json.load(open(DATA / "sample_metadata.json", encoding="utf-8"))
    df = pd.read_csv(DATA / "GSE316098_raw.counts.linear.formatted.csv.gz",
                     index_col=0)
    df.index = df.index.astype(str)
    # 列名与 metadata 的 title 对齐（1A.001.epi 等）。
    # 注意：GEO 提交用连字符（1b-1.001.epi），metadata 用点（1b.1.001.epi）；
    # 逐列回退匹配，保证 186 个 ROI 全部对齐，而不是静默丢掉一半。
    cols = [str(c) for c in df.columns]
    df.columns = cols
    colmap = {}
    for c in cols:
        if c in meta:
            colmap[c] = c
        else:
            alt = c.replace("-", ".")
            if alt in meta:
                colmap[c] = alt
    if len(colmap) != len(cols):
        miss = [c for c in cols if c not in colmap]
        raise RuntimeError(f"{len(miss)} ROI columns not matched to metadata, "
                           f"e.g. {miss[:5]}")
    df = df[cols].rename(columns=colmap)
    print(f"matrix: {df.shape[0]} genes x {df.shape[1]} ROIs (all matched to metadata)")

    # 表达基因过滤：至少在 min_det 个 ROI 中非零
    det = (df.values > 0).sum(axis=1)
    df = df.loc[det >= min_det]
    # CPM -> log1p
    lib = df.values.sum(axis=0)
    lib[lib == 0] = 1.0
    cpm = df.values / lib * 1e4
    L = np.log1p(cpm)
    # top 高变基因（与 ST 队列一致的降维口径）
    if top_gene and L.shape[0] > top_gene:
        v = L.var(axis=1)
        idx = np.argsort(-v)[:top_gene]
        L = L[idx]
    X = L.T.astype(np.float64)          # n_ROI x genes
    titles = list(df.columns)
    return X, meta, titles


def build_arms(meta, titles):
    """按 title 顺序给出 g（病例）与三个 arm 的 y。"""
    gcase, yrisk, ysilva, ycell = [], [], [], []
    for t in titles:
        m = meta[t]
        gcase.append(m["caseid"])
        yrisk.append(RISK_ORD[m["risk"]])
        ysilva.append(SILVA_ORD[m["silva pattern"]])
        ycell.append(CELL_ORD[m["cell type"]])
    _, ginv = np.unique(gcase, return_inverse=True)
    g = ginv.astype(int)
    return g, (np.asarray(yrisk, float), np.asarray(ysilva, float),
               np.asarray(ycell, float)), np.asarray(gcase)


def within_group_variation(y, g):
    """组内标签变异的两个量化指标。

    frac_groups_varying : 组内标签不唯一的组占比（1.0 = 每组内部都有变化）
    ent_ratio           : 组内条件熵 / 总熵（1.0 = 标签完全不被组解释）
    """
    def ent(v):
        _, c = np.unique(v, return_counts=True)
        p = c / c.sum()
        return float(-(p * np.log(p)).sum())

    vary, cond = [], []
    for gg in np.unique(g):
        yy = y[g == gg]
        vary.append(len(np.unique(yy)) > 1)
        cond.append(ent(yy) * len(yy) / len(y))
    H = ent(y)
    return {"frac_groups_varying": float(np.mean(vary)),
            "cond_entropy_ratio": (float(np.sum(cond)) / H) if H > 0 else float("nan")}


# --------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--doses", default="0,0.5,1,2,5")
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--topg", type=int, default=2000)
    ap.add_argument("--arm", default="risk,silva,cell_type")
    args = ap.parse_args()

    doses = [float(x) for x in args.doses.split(",")]
    seeds = [int(x) for x in args.seeds.split(",")]

    X, meta, titles = load_geomx(top_gene=args.topg)
    g, ys, gcase = build_arms(meta, titles)
    G = len(np.unique(g))
    print(f"ROIs={len(titles)}  cases(G)={G}  "
          f"ROIs per case={ {int(k): int(v) for k, v in zip(*np.unique(g, return_counts=True))} }")

    arms = {
        "risk": (ys[0], "patient risk stratum (0=normal,1=low,2=high)"),
        "silva": (ys[1], "Silva invasion pattern per ROI (0=normal,1=A,2=B,3=C)"),
        "cell_type": (ys[2], "ROI cell type (0=epithelium,1=stroma; nominal)"),
    }
    arm_names = [a.strip() for a in args.arm.split(",")]

    all_rows, summary = [], {}
    for name in arm_names:
        y, desc = arms[name]
        wv = within_group_variation(y, g)
        kap = norm_mi(g, y)
        print(f"\n--- arm {name}: within-group varying groups="
              f"{wv['frac_groups_varying']:.2f}  cond-entropy ratio="
              f"{wv['cond_entropy_ratio']:.3f}  kappa={kap:.4f}")
        rows = run_domain(f"GEOMX_{name.upper()}", X, y, g, 64, args.epochs,
                          doses, seeds, desc, f"patient / caseid (G={G})", len(y))
        for r in rows:
            r["arm"] = name
            r["frac_groups_varying"] = wv["frac_groups_varying"]
            r["cond_entropy_ratio"] = wv["cond_entropy_ratio"]
        all_rows += rows

        b = [r for r in rows if r["lam"] == 0.0]
        dosed = [r for r in rows if r["lam"] > 0]
        tau_b = float(np.mean([r["tau_loo"] for r in b]))
        sig = float(np.mean([r["sigma"] for r in b]))
        summary[name] = {
            "label": desc,
            "n_units": int(len(y)), "G": int(G),
            "frac_groups_varying": wv["frac_groups_varying"],
            "cond_entropy_ratio": wv["cond_entropy_ratio"],
            "kappa_group_label": kap,
            "tau_base": tau_b, "sigma_hat": sig,
            "tau_lgo_base": float(np.mean([r["tau_lgo"] for r in b])),
            "ldi_base": float(np.mean([r["ldi"] for r in b])),
            "inflation_base": float(np.mean([r["inflation"] for r in b])),
            "group_id_lift_base": float(np.mean([r["group_id_lift"] for r in b])),
            "c_crit": (LDI_GATE * sig / tau_b) if tau_b > 0 else float("nan"),
            "dosed_cells": len(dosed),
            "ldi_gate_pass_dosed": int(sum(bool(r["ldi_gate_pass"]) for r in dosed)),
            "dual_gate_pass_dosed": int(sum(bool(r["dual_gate_pass"]) for r in dosed)),
            "best_dual": [
                {"lam": r["lam"], "seed": r["seed"], "tau_loo": r["tau_loo"],
                 "ldi": r["ldi"], "keep_ratio": r["safety_tau_loo_kept"],
                 "pass": bool(r["dual_gate_pass"])}
                for r in sorted(dosed, key=lambda z: (-z["dual_gate_pass"],
                                                      -z["tau_loo"]))[:3]],
        }

    RES.mkdir(exist_ok=True)
    payload = {
        "protocol": {
            "question": ("does within-group label variation, not the data or the "
                         "grouping, determine whether the repair can pass the dual gate?"),
            "design": ("one dataset, one feature matrix, one grouping; only the "
                       "label changes, along a gradient of within-group variation"),
            "dataset": ("GSE316098 NanoString GeoMx DSP, cervix; 186 ROIs from 7 "
                        "cases; each ROI carries its own pathology annotation"),
            "preprocessing": "counts -> CPM(1e4) -> log1p -> top variable genes",
            "top_variable_genes": args.topg,
            "instrument": "identical to exp_crossdomain_audit (reused verbatim)",
            "tau_perp": TAU_PERP, "ldi_gate": LDI_GATE,
            "fidelity_keep": FIDELITY_KEEP, "perm_seed": PERM_SEED,
            "perm_B_sigma": 2000, "perm_B_p": 10000,
            "encoder": "MLP autoencoder + GRL group adversary",
            "doses": doses, "seeds": seeds, "epochs": args.epochs,
            "note": ("cell_type is a nominal label; its tau sign depends on the "
                     "arbitrary epi/stroma coding and is reported as-is."),
        },
        "summary": summary, "runs": all_rows,
    }
    (RES / "within_group_label_geomx.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    with open(RES / "within_group_label_geomx.csv", "w", newline="",
              encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(all_rows[0].keys()))
        w.writeheader()
        w.writerows(all_rows)

    print("\n===== SUMMARY (within-group label variation) =====")
    for k, s in summary.items():
        print(f"\n[{k}] units={s['n_units']} G={s['G']} "
              f"varying_groups={s['frac_groups_varying']:.2f} kappa={s['kappa_group_label']:.3f}")
        print(f"  tau_base={s['tau_base']:.4f} sigma={s['sigma_hat']:.4f} "
              f"tau_LGO={s['tau_lgo_base']:.4f} LDI={s['ldi_base']:.3f}")
        print(f"  inflation(base)={s['inflation_base']:+.4f} "
              f"grpID lift={s['group_id_lift_base']:.2f} c_crit={s['c_crit']:.3f}")
        print(f"  dosed cells={s['dosed_cells']} "
              f"LDI-gate pass={s['ldi_gate_pass_dosed']} "
              f"dual-gate pass={s['dual_gate_pass_dosed']}")
    print("\nsaved results/within_group_label_geomx.json / .csv")


if __name__ == "__main__":
    main()
