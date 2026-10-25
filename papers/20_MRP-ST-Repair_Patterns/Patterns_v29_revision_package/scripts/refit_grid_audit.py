#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""refit_grid_audit.py — 用「重拟合置换」重算所有存档 p 值无效的岭 LODO 探针。

背景
----
probe_lodo.lodo_probe() 的置换是 fixed-prediction（预测固定、只换标签），
对"拟合过标签的探针"不构成有效推断。受影响的存档结果：

  B. 剂量–反应网格（sim_power_summary.json 的显著 run / 判级 / CTRL 假阳性）
  C. CTRL FULL 解离（v2_ctrl_full_probe.json 的 "全部 p ≤ 1e-4"）
  D. 基准子集参考探针（v2_ours_subset_probe.json 的显著种子数）
  A. 真实宫颈诊断变体（probe_lodo.py 直接输出的 Fig 9C 一类 p 值）

不受影响（无需重算）：21 项主要检验（corrected_probe，本脚本口径的来源）、
三方法 cluster-max 读出（标签无关，固定分数置换有效）。

口径
----
operator()/audit() 逐字复制自 csbj_review_verify.py：LOO 岭回归帽矩阵 H
（训练折标准化、alpha=1、无截距），置换时对每个重排标签重拟合（P = Y@H.T），
B=10000、seed=20261010 —— 与 21 项主要检验完全一致。观测 tau 与 lodo_probe
的 LOO 预测数学等价（已在 primary_probe_reproduction.json 验证到 1e-9）。

用法
----
本地（真实宫颈诊断变体，Fig 9C）：
    python scripts/refit_grid_audit.py --mode local
服务器（仿真网格 + 解离 + 子集，CPU 数分钟）：
    python scripts/refit_grid_audit.py --mode server
两者都跑：
    python scripts/refit_grid_audit.py --mode all

输出（均带 _refit 后缀，不覆盖存档文件）
    results/refit_diagnostic_probes.json      A：真实宫颈七变体
    results/sim_power_raw_refit.json           B：逐 run tau / p_refit
    results/sim_power_summary_refit.json      B：与 sim_power_summary.json 同 schema
    results/v2_ctrl_full_probe_refit.json     C：解离（FULL 嵌入探针）
    results/v2_ours_subset_probe_refit.json   D：基准子集参考探针
    results/pooled_grid/*.npz                 B/C 的样本级池化导出（X/y/names，
                                               供 v1.1 证据包与本地复核）
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
from scipy.stats import kendalltau

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from probe_lodo import per_sample_embedding  # noqa: E402

RES = ROOT / "results"
SUP_THR = 0.35
UNSUP_THR = 0.15
ALPHA = 0.05
NAME_RE = re.compile(r"^group_([AC])_(g\d+?)_(L\d+|CTRL)(_small)?$")

# 真实宫颈诊断变体与种子（与 probe_lodo.py / 冻结口径一致）
CERVICAL_VARIANTS = {
    "FULL": [0, 3, 4],
    "NOIMAGE": [0, 1, 2],
    "NOHPV": [0, 1, 2],
    "NONEIGH": [0, 1, 2],
    "NOPROG": [0, 1, 2, 3],
    "NOSUP": [0, 1, 2],
    "NOALL": [0, 1, 2],
}


def operator(X, intercept=False):
    """LOO 岭回归帽矩阵（训练折标准化，alpha=1，无截距）。"""
    n, p = X.shape
    H = np.zeros((n, n))
    for i in range(n):
        tr = np.arange(n) != i
        mu = X[tr].mean(0)
        sd = X[tr].std(0) + 1e-8
        Z = (X[tr] - mu) / sd
        z = (X[i] - mu) / sd
        h = np.linalg.solve(Z @ Z.T + np.eye(n - 1), Z @ z)
        if intercept:
            h = h - h.mean() + 1 / (n - 1)
        H[i, tr] = h
    return H


def audit(X, y):
    """重拟合置换检验：每个重排标签都重新过一遍同一 LOO 岭探针。"""
    H = operator(X)
    pred = H @ y
    obs = float(kendalltau(pred, y)[0])  # 元组索引：老/新 scipy 均兼容
    rng = np.random.default_rng(20261010)
    i, j = np.triu_indices(len(y), 1)
    ge = 0
    for start in range(0, 10000, 100):
        Y = np.stack([rng.permutation(y) for _ in range(100)])
        P = Y @ H.T
        a = np.sign(P[:, j] - P[:, i])
        b = np.sign(Y[:, j] - Y[:, i])
        den = np.sqrt((a * a).sum(1) * (b * b).sum(1))
        t = np.divide((a * b).sum(1), den, out=np.zeros(len(P)), where=den > 0)
        ge += int((t >= obs - 1e-12).sum())
    return {"tau": obs, "p_refit": (ge + 1) / 10001}


def insample_tau(X, y):
    """in-sample 岭探针（全样本拟合预测，记忆化差距对照）。"""
    mu, sd = X.mean(0), X.std(0) + 1e-8
    Z = (X - mu) / sd
    p = Z.shape[1]
    w = np.linalg.solve(Z.T @ Z + np.eye(p), Z.T @ y)
    return float(kendall_tau(Z @ w, y))


def kendall_tau(a, b):
    """与 probe_lodo.kendall_tau 相同的 tau-b（自包含实现）。"""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    n = len(a)
    conc = disc = tx = ty = 0
    for i in range(n - 1):
        di = a[i + 1:] - a[i]
        db = b[i + 1:] - b[i]
        both = (di == 0) & (db == 0)
        tx += int(((di == 0) & ~both).sum())
        ty += int(((db == 0) & ~both).sum())
        conc += int((di * db > 0).sum())
        disc += int((di * db < 0).sum())
    denom = np.sqrt((conc + disc + tx) * (conc + disc + ty))
    return 0.0 if denom == 0 else (conc - disc) / denom


# ---------------------------------------------------------------- A：真实宫颈
def run_cervical(export_dir=None):
    out = {}
    print("=== A. 真实宫颈诊断变体 · 重拟合置换探针（n=35，序数 0/1/2） ===")
    for variant, seeds in CERVICAL_VARIANTS.items():
        rows = []
        for s in seeds:
            fp = RES / f"fused_embs_{variant}_seed{s}.npz"
            if not fp.exists():
                print(f"  [miss] {variant} seed{s}: {fp.name} 不存在，跳过")
                continue
            X, y, names = per_sample_embedding(np.load(fp))
            if len(np.unique(y)) < 2:
                print(f"  [skip] {variant} seed{s}: 单一严重度")
                continue
            a = audit(X, y)
            tau_in = insample_tau(X, y)
            row = {"seed": s, "tau_lodo": a["tau"], "p_refit": a["p_refit"],
                   "tau_insample": tau_in, "n": int(len(y))}
            rows.append(row)
            print(f"  {variant:8s} seed{s}  tau={a['tau']:+.4f}  "
                  f"p_refit={a['p_refit']:.4f}  tau_in={tau_in:+.4f}")
        if rows:
            taus = [r["tau_lodo"] for r in rows]
            out[variant] = {"runs": rows, "mean_tau": float(np.mean(taus)),
                            "n_sig": sum(r["p_refit"] < ALPHA for r in rows)}
    (RES / "refit_diagnostic_probes.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    print("saved results/refit_diagnostic_probes.json")
    return out


# ------------------------------------------------------- B：剂量–反应网格
def discover_grid():
    """扫描 results/ 下属于网格的 NOALL / CTRL FULL 嵌入。"""
    cells = {}
    for fp in sorted(RES.glob("fused_embs_*group_*_seed*.npz")):
        base = fp.name[len("fused_embs_"):-len(".npz")]
        seed = int(base.rsplit("_seed", 1)[1])
        group = base.rsplit("_seed", 1)[0]
        if group.startswith("SIM_"):
            group = group[len("SIM_"):]
        variant = "FULL" if group.endswith("_FULL") else None
        if group.endswith("_NOALL"):
            group, variant = group[:-len("_NOALL")], "NOALL"
        elif group.endswith("_FULL"):
            group, variant = group[:-len("_FULL")], "FULL"
        meta = parse_group(group)
        if meta is None:
            continue
        cells.setdefault(group, {"meta": meta})[f"{variant}_seed{seed}"] = fp
    return cells


def parse_group(name):
    m = NAME_RE.match(name)
    if not m:
        return None
    kind, gen, level, small = m.group(1), m.group(2), m.group(3), bool(m.group(4))
    return {"kind": kind, "gen": gen, "level": level,
            "size": "small" if small else "main"}


def grade_runs(runs):
    """三级判据（与 sim_power_grid.grade_runs 一致，p 换成 p_refit）。"""
    taus = np.array([r["tau_lodo"] for r in runs])
    ps = np.array([r["p_refit"] for r in runs])
    n_sig = int((ps < ALPHA).sum())
    mean_tau = float(taus.mean())
    if mean_tau >= SUP_THR and n_sig / len(runs) >= 2 / 3:
        verdict = "supported"
    elif abs(mean_tau) <= UNSUP_THR and n_sig == 0:
        verdict = "unsupported"
    else:
        verdict = "suggestive"
    return {"mean_tau": mean_tau,
            "sd_tau": float(taus.std(ddof=1)) if len(taus) > 1 else 0.0,
            "n_significant": n_sig, "n_runs": len(runs),
            "frac_significant": n_sig / len(runs), "verdict": verdict}


def run_grid(export_dir, benchmark_fp=None):
    cells = discover_grid()
    if not cells:
        print("[B] 未发现网格嵌入（本地无服务器数据属正常；请在服务器运行 --mode server）")
        return None
    pooled = export_dir / "pooled_grid"
    pooled.mkdir(parents=True, exist_ok=True)
    raw = {}
    print(f"=== B. 剂量–反应网格 · 重拟合置换（发现 {len(cells)} 个队列） ===")
    for group, payload in sorted(cells.items()):
        m = payload["meta"]
        runs = []
        for key, fp in sorted(payload.items()):
            if "_seed" not in key:
                continue  # 跳过 "meta" 元数据键
            variant, seed = key.rsplit("_seed", 1)[0], int(key.rsplit("_seed", 1)[1])
            if variant != "NOALL":
                continue  # FULL 属于解离目标 C，此处只算定级规则
            X, y, names = per_sample_embedding(np.load(fp))
            if len(np.unique(y)) < 2:
                continue
            a = audit(X, y)
            runs.append({"seed": seed, "tau_lodo": a["tau"],
                         "p_refit": a["p_refit"],
                         "tau_insample_probe": insample_tau(X, y),
                         "n_donors": int(len(y))})
            np.savez(pooled / f"{group}_NOALL_seed{seed}.npz",
                     X=np.asarray(X, dtype=np.float64),
                     y=np.asarray(y, dtype=np.float64),
                     names=np.asarray(names))
            print(f"  {group:34s} seed{seed}  tau={a['tau']:+.4f}  "
                  f"p_refit={a['p_refit']:.4f}")
        if runs:
            raw[group] = {"meta": m, "runs": runs}

    # 聚合：与 sim_power_grid.aggregate 同 schema
    by_level_size, ctrl = {}, {}
    for group, payload in raw.items():
        m = payload["meta"]
        key = (m["level"], m["size"])
        tgt = ctrl if m["kind"] == "C" else by_level_size
        tgt.setdefault(key, []).extend(payload["runs"])
    detection, error = {}, {}
    for (level, size), runs in by_level_size.items():
        detection.setdefault(size, {})[level] = grade_runs(runs)
    for (level, size), runs in ctrl.items():
        g = grade_runs(runs)
        g["frac_false_positive"] = g["frac_significant"]
        error.setdefault(size, {})[level] = g
    roc = {}
    levels = ["L1", "L2", "L3", "L4"]
    for size in sorted(detection):
        taus_sig = np.concatenate([[r["tau_lodo"] for r in runs]
                                   for (lv, sz), runs in by_level_size.items()
                                   if sz == size and lv == levels[0]])
        taus_ctrl = np.concatenate([[r["tau_lodo"] for r in runs]
                                    for (lv, sz), runs in ctrl.items() if sz == size])
        grid = np.round(np.arange(0.05, 0.86, 0.025), 3)
        roc[size] = {"threshold": grid.tolist(),
                     "sensitivity": [float((taus_sig >= t).mean()) for t in grid],
                     "one_minus_specificity": [float((taus_ctrl >= t).mean()) for t in grid]}
    summary = {
        "design": {"permutation": "refit (hat-matrix, seed 20261010, B=10000)",
                   "generator_seeds": sorted({p["meta"]["gen"] for p in raw.values()}),
                   "signal_levels": levels,
                   "sizes": sorted({p["meta"]["size"] for p in raw.values()}),
                   "thresholds": {"supported_tau": SUP_THR,
                                  "unsupported_abs_tau": UNSUP_THR, "alpha": ALPHA}},
        "detection_rate": detection,
        "type_i_error_control": error,
        "threshold_roc": roc,
        "per_cohort": raw,
    }
    (RES / "sim_power_raw_refit.json").write_text(json.dumps(raw, indent=2), encoding="utf-8")
    (RES / "sim_power_summary_refit.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("saved results/sim_power_raw_refit.json / sim_power_summary_refit.json")

    # ------------------------------------------------------------- C：解离
    dissoc = {}
    print("=== C. CTRL FULL 嵌入解离 · 重拟合置换 ===")
    for group, payload in sorted(cells.items()):
        if payload["meta"]["kind"] != "C":
            continue
        rows = []
        for key, fp in sorted(payload.items()):
            if "_seed" not in key:
                continue  # 跳过 "meta" 元数据键
            variant, seed = key.rsplit("_seed", 1)[0], int(key.rsplit("_seed", 1)[1])
            if variant != "FULL":
                continue
            X, y, names = per_sample_embedding(np.load(fp))
            a = audit(X, y)
            rows.append({"seed": seed, "tau_lodo": a["tau"], "p_refit": a["p_refit"],
                         "tau_insample": insample_tau(X, y)})
            np.savez(pooled / f"{group}_FULL_seed{seed}.npz",
                     X=np.asarray(X, dtype=np.float64),
                     y=np.asarray(y, dtype=np.float64),
                     names=np.asarray(names))
            print(f"  {group:34s} FULL seed{seed}  tau={a['tau']:+.4f}  "
                  f"p_refit={a['p_refit']:.4f}")
        if rows:
            dissoc[group] = {"taus": [r["tau_lodo"] for r in rows],
                             "p_refits": [r["p_refit"] for r in rows], "runs": rows}
    (RES / "v2_ctrl_full_probe_refit.json").write_text(
        json.dumps(dissoc, indent=2), encoding="utf-8")
    print("saved results/v2_ctrl_full_probe_refit.json")

    # ------------------------------------------------------------- D：子集
    if benchmark_fp and benchmark_fp.exists():
        bm = json.loads(benchmark_fp.read_text(encoding="utf-8"))
        subset_out = {}
        print("=== D. 基准子集参考探针（同 21 样本子集，重拟合置换） ===")
        for g, gd in bm["groups"].items():
            if "methods" not in gd or "SpaGCN" not in gd["methods"]:
                continue
            nset = set(gd["methods"]["SpaGCN"]["sample_risks"].keys())
            rows = []
            for ts in [0, 1, 2]:
                fp = RES / f"fused_embs_SIM_{g}_NOALL_seed{ts}.npz"
                if not fp.exists():
                    continue
                X, y, names = per_sample_embedding(np.load(fp))
                keep = [i for i, s in enumerate(names) if s in nset]
                Xs, ys = X[keep], np.asarray(y)[keep]
                a = audit(Xs, ys)
                rows.append({"seed": ts, "tau": a["tau"], "p_refit": a["p_refit"]})
            if rows:
                taus = [r["tau"] for r in rows]
                subset_out[g] = {"mean_tau": float(np.mean(taus)), "runs": rows,
                                 "n_samples": len(nset)}
                print(f"  {g:34s} taū={np.mean(taus):+.3f}  "
                      f"p_refit={[round(r['p_refit'], 4) for r in rows]}")
        (RES / "v2_ours_subset_probe_refit.json").write_text(
            json.dumps(subset_out, indent=2), encoding="utf-8")
        print("saved results/v2_ours_subset_probe_refit.json")

    # 决策门速览
    print("\n===== 决策门速览（重拟合后） =====")
    for size in sorted(detection):
        for lv in levels:
            g = detection.get(size, {}).get(lv)
            if g:
                print(f"[{size:5s}] {lv}: tau={g['mean_tau']:+.3f} "
                      f"sig={g['n_significant']}/{g['n_runs']} {g['verdict']}")
    for size in sorted(error):
        for lv, g in error[size].items():
            print(f"[{size:5s}] CTRL {lv}: FPR(α)={g['frac_false_positive']:.3f}")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="local", choices=["local", "server", "all"],
                    help="local=真实宫颈诊断变体；server=仿真网格+解离+子集")
    args = ap.parse_args()
    export_dir = RES / "pooled_exports"
    if args.mode in ("local", "all"):
        run_cervical()
    if args.mode in ("server", "all"):
        run_grid(export_dir, RES / "st_methods_benchmark_v2.json")


if __name__ == "__main__":
    main()
