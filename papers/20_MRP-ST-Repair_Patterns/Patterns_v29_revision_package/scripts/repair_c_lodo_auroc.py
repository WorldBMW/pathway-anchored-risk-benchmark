#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""repair_c_lodo_auroc.py — 实验 C：从已保存的修复 dump 计算 LODO 临床终点 AUROC。

背景（方案 §12.4）
-----------------
主稿的全部终点均为表示层指标（tau_lodo / LDI / R），缺少"修复后模型在临床任务上
是否真的更好"的证据。本脚本在不重训的前提下，用已落盘的切片均值嵌入 Xs（+ y/names）
计算：

  - E4（HNSCC，GSE268014）：HPV 二分类 LODO AUROC（λ=0 vs λ>0）
  - 宫颈（序数型严重度 0/1/2）：LODO 序数 AUROC —— 定位为"修复消除样本内假信心"

口径
----
- 探针：与 repair_e3_methodB_train.evaluate() 中 tau_ldo 同款的标准化 + Ridge
  （alpha=1，闭式解），leave-one-DONOR-out（供者整块移出训练折）。
- AUROC：秩和法手算（不依赖 sklearn）。
- 同时报 in-sample AUROC（全量拟合+全量预测），用于"假信心 vs 诚实泛化"对照。

两种模式
--------
  --inspect   仅打印 results/ 下候选 dump 的结构（键、run 列表、Xs 维度），不计算
  （默认）     计算并写 results/repair_c_lodo_auroc.json

用法
----
  python scripts/repair_c_lodo_auroc.py --inspect
  python scripts/repair_c_lodo_auroc.py
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
RESULTS = ROOT / "results"

from probe_lodo import severity_of, kendall_tau  # noqa: E402

DONOR_RE = re.compile(r"((?:HPV[pn]|N|HSIL|CA)_[A-Za-z0-9]+)", re.IGNORECASE)
KEY_RE = re.compile(r"^s(\d+)_lam([0-9.]+)$")


def donor_of(name: str) -> str:
    m = DONOR_RE.match(str(name))
    return (m.group(1).upper() if m else str(name).upper())


def ridge_predict(Xtr, ytr, Xte, alpha=1.0):
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-8
    Ztr, Zte = (Xtr - mu) / sd, (Xte - mu) / sd
    p = Ztr.shape[1]
    A = Ztr.T @ Ztr + alpha * np.eye(p)
    w = np.linalg.solve(A, Ztr.T @ ytr)
    return Zte @ w


def auroc_binary(score, ybin):
    """秩和法 AUROC（ybin 为 0/1）。返回 None 若单类。"""
    ybin = np.asarray(ybin)
    if len(np.unique(ybin)) < 2:
        return None
    order = np.argsort(score, kind="mergesort")
    ranks = np.empty(len(score), float)
    ranks[order] = np.arange(1, len(score) + 1)
    # 处理并列：取平均秩
    s_sorted = score[order]
    i = 0
    while i < len(s_sorted):
        j = i
        while j + 1 < len(s_sorted) and s_sorted[j + 1] == s_sorted[i]:
            j += 1
        if j > i:
            ranks[order[i:j + 1]] = (i + 1 + j + 1) / 2.0
        i = j + 1
    npos = int(ybin.sum())
    nneg = len(ybin) - npos
    if npos == 0 or nneg == 0:
        return None
    auc = (ranks[ybin == 1].sum() - npos * (npos + 1) / 2.0) / (npos * nneg)
    return float(auc)


def macro_auroc(score, y):
    """多类 one-vs-rest 宏平均 AUROC。"""
    aucs = [auroc_binary(score, (np.asarray(y) == c).astype(int))
            for c in np.unique(y)]
    aucs = [a for a in aucs if a is not None]
    return float(np.mean(aucs)) if aucs else None


def lodo_predict(X, y, donors):
    """leave-one-donor-out 闭式 Ridge 预测。"""
    pred = np.full(len(y), np.nan)
    for d in np.unique(donors):
        tr = donors != d
        te = ~tr
        if tr.sum() < 2 or te.sum() == 0:
            continue
        p = ridge_predict(X[tr], y[tr], X[te])
        pred[te] = p
    return pred


def load_runs(path: Path):
    """从 JSON 提取 {key: (Xs, y, names)}；兼容两种布局。"""
    d = json.loads(path.read_text(encoding="utf-8-sig"))
    out = {}
    if isinstance(d, dict) and "dump_xs" in d and isinstance(d["dump_xs"], dict):
        for k, v in d["dump_xs"].items():
            if isinstance(v, dict) and "Xs" in v:
                out[k] = (np.asarray(v["Xs"], float),
                          np.asarray(v["y"], float), list(v["names"]))
    elif isinstance(d, dict) and "Xs" in d and "y" in d:
        out[path.stem] = (np.asarray(d["Xs"], float),
                          np.asarray(d["y"], float), list(d.get("names", [])))
    return out


def summarize(series, label):
    vals = [v for v in series if v is not None]
    if not vals:
        return {"label": label, "n": 0}
    return {"label": label, "n": len(vals), "mean": float(np.mean(vals)),
            "sd": float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0,
            "values": vals}


def analyse(cohort_runs, cohort_tag, binary):
    """cohort_runs: {key: (Xs,y,names)}；返回逐 (lambda,seed) 指标。"""
    res = {}
    for key, (Xs, y, names) in cohort_runs.items():
        m = KEY_RE.match(key)
        if m is None:
            continue
        seed, lam = int(m.group(1)), float(m.group(2))
        donors = np.array([donor_of(n) for n in names]) if names else \
            np.arange(len(y))
        if len(np.unique(y)) < 2:
            continue
        pred_lo = lodo_predict(Xs, y, donors)
        ok = ~np.isnan(pred_lo)
        pred_in = np.array([ridge_predict(Xs, y, Xs[i:i + 1])[0]
                            for i in range(len(y))])
        row = {"seed": seed, "lam": lam, "n_samples": int(len(y)),
               "n_donors": int(len(np.unique(donors))),
               "tau_lodo_mine": float(kendall_tau(pred_lo[ok], y[ok]))}
        if binary:
            row["lodo_auroc"] = auroc_binary(pred_lo[ok], y[ok])
            row["in_auroc"] = auroc_binary(pred_in, y)
        else:
            row["lodo_auroc_macro"] = macro_auroc(pred_lo[ok], y[ok])
            row["in_auroc_macro"] = macro_auroc(pred_in, y)
            neopl = (np.asarray(y) >= 1).astype(float)
            row["lodo_auroc_neopl_vs_normal"] = auroc_binary(pred_lo[ok],
                                                             neopl[ok])
            row["in_auroc_neopl_vs_normal"] = auroc_binary(pred_in, neopl)
        res.setdefault(str(lam), []).append(row)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inspect", action="store_true")
    ap.add_argument("--verify", action="store_true",
                    help="对照 repair_e4_hnscc_stable.json 中已存的 tau_ldo/ldi")
    ap.add_argument("--out", default=str(RESULTS / "repair_c_lodo_auroc.json"))
    args = ap.parse_args()

    candidates = sorted(RESULTS.glob("repair_*.json")) + \
        sorted(RESULTS.glob("e4_dump_*.json")) + \
        sorted(RESULTS.glob("dump_*.json"))
    found = {}
    for p in candidates:
        try:
            runs = load_runs(p)
        except Exception as e:
            print(f"[skip] {p.name}: {e}")
            continue
        if runs:
            found[p.name] = runs

    if args.inspect:
        print("=== dump inventory (files with recoverable Xs) ===")
        for nm, runs in found.items():
            k0 = sorted(runs)[0]
            Xs, y, names = runs[k0]
            print(f"{nm}: {len(runs)} runs | Xs={Xs.shape} | "
                  f"y levels={sorted(set(y))} | names[0]={names[0] if names else '-'}")
            print(f"    keys={sorted(runs)[:12]}")
        if not found:
            print("(none) -> 需要带 --dump-xs 的短 GPU 复跑")
        return

    if args.verify:
        src = RESULTS / "repair_e4_hnscc_stable.json"
        d = json.loads(src.read_text(encoding="utf-8"))
        runs = load_runs(src)
        scan = d.get("scan", {})
        print(f"{'key':10s} {'mine_tau':>9s} {'tau_ldo':>9s} "
              f"{'tau_lodo':>9s} {'ldi':>8s}  {'lodo_auc':>8s}")
        for k in sorted(runs):
            Xs, y, names = runs[k]
            donors = np.array([donor_of(n) for n in names])
            pl = lodo_predict(Xs, y, donors)
            ok = ~np.isnan(pl)
            tmine = kendall_tau(pl[ok], y[ok])
            s = scan.get(k, {})
            tldo = s.get("tau_ldo", float("nan"))
            tld = s.get("tau_lodo", float("nan"))
            ldi = s.get("ldi", float("nan"))
            auc = auroc_binary(pl[ok], y[ok])
            print(f"{k:10s} {tmine:+9.4f} {float(tldo):+9.4f} "
                  f"{float(tld):+9.4f} {float(ldi):+8.3f}  {float(auc):8.4f}")
        return

    report = {"note": "实验 C：LODO 临床终点 AUROC（供者级留出，闭式 Ridge 探针）",
              "E4_HNSCC": {}, "prostate_GSE278936": {}, "cervix": {}}
    # E4 = 名字以 HPVp_/HPVn_ 开头；前列腺 = BPH_/TRNA_/NEADT_/CRPC_/MET_；
    # 其余归入宫颈队列
    e4_runs, pr_runs, cx_runs = {}, {}, {}
    for nm, runs in found.items():
        for k, v in runs.items():
            names = v[2]
            head = donor_of(names[0]) if names else ""
            if head.startswith(("HPVP_", "HPVN_")):
                e4_runs[k] = v
            elif head.startswith(("BPH_", "TRNA_", "NEADT_", "CRPC_", "MET_")):
                pr_runs[k] = v
            else:
                cx_runs[k] = v
    report["E4_HNSCC"] = analyse(e4_runs, "E4", binary=True)
    report["prostate_GSE278936"] = analyse(pr_runs, "prostate", binary=True)
    report["cervix"] = analyse(cx_runs, "cervix", binary=False)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"saved {args.out}")
    for tag in ("E4_HNSCC", "prostate_GSE278936", "cervix"):
        print(f"\n== {tag} ==")
        for lam, rows in sorted(report[tag].items(), key=lambda kv: float(kv[0])):
            is_bin = tag in ("E4_HNSCC", "prostate_GSE278936")
            k = "lodo_auroc" if is_bin else "lodo_auroc_macro"
            ki = "in_auroc" if is_bin else "in_auroc_macro"
            s = summarize([r[k] for r in rows], f"lam={lam}")
            si = summarize([r[ki] for r in rows], f"lam={lam}")
            print(f"  lam={lam:>4}  LODO AUC={s.get('mean'):} ± {s.get('sd'):}"
                  f" (n={s.get('n')})   in-sample AUC={si.get('mean'):}"
                  f" ± {si.get('sd'):}" if s.get("n") else
                  f"  lam={lam:>4}  (无可用 run)")


if __name__ == "__main__":
    main()
