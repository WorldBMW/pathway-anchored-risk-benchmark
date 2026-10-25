# -*- coding: utf-8 -*-
"""threshold_robustness_scan.py — 定级阈值鲁棒性扫描（回应评审 3.1）

审稿人攻击点：supported/suggestive/unsupported 的界值（τ_up=0.35、τ_low=0.15）
是人为预设，换一组阈值结论是否改变？

本脚本对阳性对照仿真 A/B/C 三臂，用与 scripts/mrpst_lodo.py **完全一致**的预注册
规则在 (τ_up, τ_low) 网格上重新定级：
    supported   : mean τ_LODO ≥ τ_up 且 ≥2/3 种子 p < α
    unsupported : |mean τ_LODO| ≤ τ_low 且 0 种子显著
    suggestive  : 其余
检验目标：A 是否在合理范围内恒为 supported、C 是否恒为 unsupported，
仅刻意设计为边界情形的 B 允许在界值附近移动。

纯后处理：只读 results/sim_lodo_summary.json（服务器已产出的 per-seed τ_LODO
与置换 p），不重训、不重跑探针。

Usage:
  python scripts/threshold_robustness_scan.py \
      [--summary results/sim_lodo_summary.json] \
      [--out results/threshold_robustness.json]
"""
import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ALPHA = 0.05
UP_GRID = [0.20, 0.25, 0.30, 0.35, 0.40, 0.45]
LOW_GRID = [0.10, 0.15, 0.20]
PREREG = (0.35, 0.15)


def grade(taus, ps, up, low):
    """与 mrpst_lodo.grade 完全一致的预注册规则。"""
    n_sig = int((ps < ALPHA).sum())
    m = float(np.mean(taus))
    if m >= up and n_sig / len(ps) >= 2 / 3:
        return "supported"
    if abs(m) <= low and n_sig == 0:
        return "unsupported"
    return "suggestive"


def load_arms(path):
    d = json.load(open(path, encoding="utf-8"))
    arms = {}
    for g, blk in d["arms"].items():
        seeds = [s for s in blk.get("seeds", []) if s.get("transfer")]
        arms[g] = (np.array([s["transfer"]["tau_lodo"] for s in seeds]),
                   np.array([s["transfer"]["p"] for s in seeds]))
    return arms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", default="results/sim_lodo_summary.json")
    ap.add_argument("--out", default="results/threshold_robustness.json")
    args = ap.parse_args()

    arms = load_arms(ROOT / args.summary)

    def pick(letter):
        # 兼容 group_A / group_A_small 两种命名
        for k in arms:
            if k.startswith(f"group_{letter}"):
                return k
        return None

    ga, gb, gc = pick("A"), pick("B"), pick("C")
    groups = [g for g in (ga, gb, gc) if g]

    print("per-arm per-seed tau_LODO / p:")
    for g in groups:
        taus, ps = arms[g]
        sd = float(taus.std(ddof=1)) if len(taus) > 1 else 0.0
        print(f"  {g}: mean={taus.mean():+.3f} sd={sd:.3f} "
              f"seeds={[round(float(t), 3) for t in taus]} "
              f"p={[round(float(p), 4) for p in ps]}")

    table = []
    n_intended = 0
    for up in UP_GRID:
        for low in LOW_GRID:
            row = {"tau_up": up, "tau_low": low}
            for g in groups:
                row[g] = grade(arms[g][0], arms[g][1], up, low)
            row["intended"] = (row.get(ga) == "supported"
                               and row.get(gc) == "unsupported"
                               and row.get(gb) == "suggestive")
            n_intended += int(row["intended"])
            table.append(row)

    print("\n(tau_up, tau_low) grid — A / B / C verdicts (* = pre-registered):")
    for row in table:
        mark = " *" if (row["tau_up"], row["tau_low"]) == PREREG else "  "
        print(f"  up={row['tau_up']:.2f} low={row['tau_low']:.2f}{mark} "
              f"{row[ga]:>11} {row[gb]:>11} {row[gc]:>11}"
              + ("   <- intended" if row["intended"] else ""))

    a_mean = float(arms[ga][0].mean()) if ga else None
    b_mean = float(arms[gb][0].mean()) if gb else None
    c_mean = float(arms[gc][0].mean()) if gc else None
    print("\ninterpretation:")
    if a_mean is not None:
        print(f"  A stays 'supported' for every tau_up <= tau_A={a_mean:.3f}; "
              f"it can only leave 'supported' above that.")
    if b_mean is not None:
        print(f"  B (deliberately borderline, mean tau={b_mean:.3f}) moves between "
              f"'supported' and 'suggestive' as tau_up crosses its mean — the intended "
              f"behavior of a borderline control.")
    if c_mean is not None:
        print(f"  C stays 'unsupported' while tau_low >= |tau_C|={abs(c_mean):.3f}; "
              f"below that it becomes 'suggestive'.")

    out = {
        "pre_registered": {"supported_tau": PREREG[0],
                           "unsupported_abs_tau": PREREG[1], "alpha": ALPHA},
        "arms_per_seed": {g: {"tau_lodo": [float(x) for x in arms[g][0]],
                              "p": [float(x) for x in arms[g][1]]} for g in groups},
        "grid": table,
        "n_intended_combos": n_intended,
        "n_combos": len(table),
    }
    op = ROOT / args.out
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nsaved -> {op}")
    print(f"intended grading (A=supported / B=suggestive / C=unsupported) holds in "
          f"{n_intended}/{len(table)} (tau_up, tau_low) combos.")


if __name__ == "__main__":
    main()