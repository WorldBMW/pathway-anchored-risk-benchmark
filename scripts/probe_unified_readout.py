#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""probe_unified_readout.py — 统一读出：同一岭 LODO 探针 + 重拟合置换，
应用于已发表方法导出的样本级池化嵌入（benchmark_st_methods.py --export-emb 产物）。

目的（P0-2）：消灭「读出差异 vs 模型差异」质疑——SpaGCN/STAGATE/GraphST 的
cluster-max 读出与参考协议的 ridge 探针是两条不同管道，不能据此比较模型。
本脚本把 STAGATE/GraphST 的导出嵌入放进与参考协议完全相同的探针：
    LOO 岭回归（训练折标准化、alpha=1、无截距）+ 重拟合置换（B=10000, seed=20261010）
    —— 与 refit_grid_audit.audit() / 21 项主要检验完全同口径。

SpaGCN 不适用（无跨样本共享连续表征，见 benchmark_st_methods._embed_dispatch 文档），
manifest 中已记录。

单 run 三级判据（与 benchmark_st_methods.grade 的单行口径一致）：
    supported   : tau >= 0.35 且 p < 0.05
    unsupported : |tau| <= 0.15 且 p >= 0.05
    suggestive  : 其余

用法（本地，CPU，秒级）：
    python scripts/probe_unified_readout.py \
        --emb-dir results/st_method_embeddings \
        --ref results/v2_ours_subset_probe_refit.json \
        --out results/unified_readout_probe.json
"""
import argparse
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(HERE))
from refit_grid_audit import audit  # noqa: E402  # 同口径探针

SUP_THR = 0.35
UNSUP_THR = 0.15
ALPHA = 0.05


def grade_single(tau, p):
    if tau >= SUP_THR and p < ALPHA:
        return "supported"
    if abs(tau) <= UNSUP_THR and p >= ALPHA:
        return "unsupported"
    return "suggestive"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emb-dir", default="results/st_method_embeddings")
    ap.add_argument("--ref", default="results/v2_ours_subset_probe_refit.json",
                    help="参考协议子集探针（refit part D 产物），仅并排打印")
    ap.add_argument("--out", default="results/unified_readout_probe.json")
    args = ap.parse_args()
    edir = Path(args.emb_dir)
    ref = json.loads(Path(args.ref).read_text(encoding="utf-8")) if Path(args.ref).exists() else {}

    out = {"protocol": "LOO ridge probe (train-fold scaling, alpha=1, no intercept) "
                      "+ refit permutation B=10000 seed=20261010; identical to "
                      "reference protocol and the 21 primary tests",
           "single_run_criteria": {"supported": "tau>=0.35 & p<0.05",
                                   "unsupported": "|tau|<=0.15 & p>=0.05",
                                   "suggestive": "otherwise"},
           "probes": {}}
    for fp in sorted(edir.glob("*__*.npz")):
        group, method = fp.stem.split("__", 1)
        d = np.load(fp, allow_pickle=True)
        X, y = d["X"], d["y"]
        if len(np.unique(y)) < 2:
            out["probes"][fp.stem] = {"error": "single severity level"}
            continue
        a = audit(X, y)
        v = grade_single(a["tau"], a["p_refit"])
        out["probes"][fp.stem] = {
            "group": group, "method": method, "n": int(len(y)),
            "tau": round(a["tau"], 4), "p_refit": round(a["p_refit"], 4),
            "grade": v}
        print(f"{group:32s} {method:8s} n={len(y):2d}  "
              f"tau={a['tau']:+.3f}  p_refit={a['p_refit']:.4f}  {v}")

    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False),
                              encoding="utf-8")
    print(f"\nsaved {args.out}")

    # 并排参考协议（3 种子）便于撰写对比表
    if ref:
        print("\n=== 参考协议（同子集，3 训练种子，refit part D） ===")
        for g, r in ref.items():
            print(f"{g:32s} ref     tau={r['mean_tau']:+.3f}  "
                  f"p_refit={[round(x['p_refit'], 4) for x in r['runs']]}")


if __name__ == "__main__":
    main()
