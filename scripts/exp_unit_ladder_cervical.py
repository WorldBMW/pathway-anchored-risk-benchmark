#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""exp_unit_ladder_cervical.py — 单位分辨率阶梯：sibling-unit 通道是否由「单位定义」产生。

设计
----
同一队列、同一供体级标签、同一 spot 嵌入，**只改动 unit 的定义**：

    K = 每个供体（切片）贡献多少个 unit
      K = 1 : unit = 整张切片的 mean-pooled 嵌入（论文现有宫颈臂；每供体 1 unit）
      K = 3 : 切片内 spot 随机分成 3 块，每块 mean-pool 成一个 unit
      K = 8 : 同上，8 块

因为 label 是供体级的（severity 0/1/2），同一供体的所有 unit 共享标签，
所以 K 每增大一档，就凭空多出 K-1 个 sibling unit —— 除了单位定义之外，
数据、嵌入、标签、分组变量全部不变。

这直接检验论文的核心断言：sibling-unit trap 是**所选单位的性质**，不是数据的性质。
K=1 时 leave-one-unit-out ≡ leave-one-group-out，Δ ≡ 0 由构造保证（对照臂）；
K>1 时若 Δ > 0 且随 K 上升，且 LDI 读数按 Proposition 1 预期的方向移动，
则框架预测被真实人体组织数据确认。

单位定义在实践中的对应：K>1 正是空间转录组里「spot 级随机切分训练/测试折」的
标准做法 —— 同一张切片的相邻 spot 被分到折的两侧。

仪器与算子与 exp_crossdomain_audit.py 完全一致（逐字复用），口径与 ST 队列一致。

用法
----
    python scripts/exp_unit_ladder_cervical.py                # CPU，约 10-20 分钟
    python scripts/exp_unit_ladder_cervical.py --epochs 30 --k 1,3,8
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

from exp_crossdomain_audit import (  # noqa: E402
    run_domain, clip_z, norm_mi, LDI_GATE, TAU_PERP, FIDELITY_KEEP, PERM_SEED,
)

RES = ROOT / "results"
BLOCK_SEED = 20261010


def severity_of(name: str) -> int | None:
    """与 scripts/benchmark_st_methods.py::severity_of 逐字一致（供体级序数标签）。"""
    n = str(name).upper()
    if n.startswith("N_") or n.startswith("ECTO_") or "NORMAL" in n:
        return 0
    if "HSIL" in n or "CIN" in n or "DYS" in n:
        return 1
    if n.startswith("CA_") or "CANCER" in n or "TUMOR" in n or n.startswith("CERVICAL_CANCER"):
        return 2
    return None


def build_arm(fused, sids, K, seed=BLOCK_SEED):
    """把 spot 级嵌入按「每供体 K 块」聚合成 unit 级矩阵。

    返回 X (n_units × d), y (供体严重度，共享), g (供体索引)。
    K=1 时退化为 per-sample mean-pool，与论文现有宫颈臂数学等价。
    """
    names, inv = np.unique(sids, return_inverse=True)
    rng = np.random.default_rng(seed)
    Xs, ys, gs = [], [], []
    d = fused.shape[1]
    for k, nm in enumerate(names):
        sev = severity_of(nm)
        if sev is None:
            continue
        rows = np.where(inv == k)[0]
        if len(rows) < K:
            continue
        # 供体内 spot 随机分块；块内 mean-pool 成 unit
        perm = rng.permutation(rows)
        blocks = np.array_split(perm, K)
        for b in blocks:
            Xs.append(fused[b].mean(axis=0))
            ys.append(float(sev))
            gs.append(k)
    return (np.vstack(Xs).astype(np.float64),
            np.asarray(ys, float), np.asarray(gs, int), len(Xs))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--doses", default="0,0.5,1,2,5")
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--k", default="1,3,8")
    ap.add_argument("--npz", default="fused_embs_FULL_seed0.npz")
    args = ap.parse_args()

    doses = [float(x) for x in args.doses.split(",")]
    seeds = [int(x) for x in args.seeds.split(",")]
    Ks = [int(x) for x in args.k.split(",")]

    fp = RES / args.npz
    d = np.load(fp, allow_pickle=True)
    fused, sids = d["fused"], d["sample_ids"].astype(str)
    print(f"loaded {fp.name}: {fused.shape[0]} spots x {fused.shape[1]}d, "
          f"{len(np.unique(sids))} sections")

    all_rows = []
    for K in Ks:
        X, y, g, n = build_arm(fused, sids, K)
        G = len(np.unique(g))
        print(f"\n--- arm K={K}: units={n} groups={G} "
              f"label counts={ {int(v): int((y == v).sum()) for v in np.unique(y)} }")
        rows = run_domain(f"CERVICAL_K{K}", X, y, g, 64, args.epochs, doses, seeds,
                          "donor severity (0/1/2, shared by all units of a donor)",
                          f"donor / section (G={G})", n)
        for r in rows:
            r["units_per_group"] = K
        all_rows += rows

    # 汇总：每个 K 的 baseline（λ=0）读数与双门计数
    summary = {}
    for K in Ks:
        rs = [r for r in all_rows if r["units_per_group"] == K]
        b = [r for r in rs if r["lam"] == 0.0]
        tau_b = float(np.mean([r["tau_loo"] for r in b]))
        sig = float(np.mean([r["sigma"] for r in b]))
        tgo = float(np.mean([r["tau_lgo"] for r in b]))
        infl = [r["inflation"] for r in rs]
        dosed = [r for r in rs if r["lam"] > 0]
        summary[f"K{K}"] = {
            "units": int(rs[0]["m_units"]), "G": int(rs[0]["G"]),
            "tau_base": tau_b, "sigma_hat": sig, "tau_lgo_base": tgo,
            "inflation_base_mean": float(np.mean([r["inflation"] for r in b])),
            "inflation_all_mean": float(np.mean(infl)),
            "inflation_range": [float(min(infl)), float(max(infl))],
            "ldi_base": float(np.mean([r["ldi"] for r in b])),
            "ratio_tau_base_over_sigma": tau_b / sig if sig > 0 else float("inf"),
            "c_crit": (LDI_GATE * sig / tau_b) if tau_b > 0 else float("nan"),
            "dosed_cells": len(dosed),
            "ldi_gate_pass_dosed": int(sum(bool(r["ldi_gate_pass"]) for r in dosed)),
            "dual_gate_pass_dosed": int(sum(bool(r["dual_gate_pass"]) for r in dosed)),
        }

    RES.mkdir(exist_ok=True)
    payload = {"protocol": {
        "instrument": "identical to exp_crossdomain_audit (reused verbatim)",
        "design": "unit-resolution ladder: only the definition of the unit changes",
        "tau_perp": TAU_PERP, "ldi_gate": LDI_GATE, "fidelity_keep": FIDELITY_KEEP,
        "perm_seed": PERM_SEED, "block_seed": BLOCK_SEED,
        "perm_B_sigma": 2000, "perm_B_p": 10000,
        "encoder": "MLP autoencoder + GRL group adversary",
        "doses": doses, "seeds": seeds, "epochs": args.epochs,
        "embedding_npz": args.npz,
        "note": ("K=1 gives one unit per donor, so leave-one-unit-out is "
                 "identical to leave-one-group-out and Delta is zero by "
                 "construction; this is the control arm.")},
        "summary": summary, "runs": all_rows}
    (RES / "unit_ladder_cervical.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    with open(RES / "unit_ladder_cervical.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(all_rows[0].keys()))
        w.writeheader()
        w.writerows(all_rows)

    print("\n===== SUMMARY (unit ladder) =====")
    for k, s in summary.items():
        print(f"\n[{k}] units={s['units']} G={s['G']}")
        print(f"  tau_base={s['tau_base']:.4f} sigma={s['sigma_hat']:.4f} "
              f"tau_LGO={s['tau_lgo_base']:.4f}")
        print(f"  inflation(base)={s['inflation_base_mean']:+.4f}  "
              f"all-dose range=[{s['inflation_range'][0]:+.4f}, "
              f"{s['inflation_range'][1]:+.4f}]")
        print(f"  LDI_base={s['ldi_base']:.3f}  ratio={s['ratio_tau_base_over_sigma']:.2f} "
              f" c_crit={s['c_crit']:.3f}")
        print(f"  dosed cells={s['dosed_cells']}  LDI-gate pass={s['ldi_gate_pass_dosed']} "
              f" dual-gate pass={s['dual_gate_pass_dosed']}")
    print("\nsaved results/unit_ladder_cervical.json / .csv")


if __name__ == "__main__":
    main()
