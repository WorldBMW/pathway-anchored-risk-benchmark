#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""exp_outer_refit_v28.py — 第 7 项缺口：外层留组后重新拟合完整流程。

v27 报告指出：编码器在探针折外之前就已经拟合完毕，因此既有 τ_LGO 是**条件表示
审计**，不是「完整学习流程对未知组」的泛化估计。本脚本把外层也折进来：每个组
整块移出后，编码器 + 对抗头 + 解码器全部只在剩余组上训练，再在留出组上拟合
探针并读取 τ，得到 τ_outer_LGO。与同一配置下「冻结嵌入 + 探针留组」的
τ_LGO_frozen 并列报告，两者之差就是「编码器见过该组」带来的乐观量。

口径与 exp_crossdomain_audit / exp_regate_v28 一致：同一 clip_z、同一 AE/GRL
结构、同一 LOO/GOD 岭探针（alpha=1、训练折标准化、无截距）。

用法
----
    python scripts/exp_outer_refit_v28.py --domain HAR --doses 0,2 --seeds 0
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

from exp_crossdomain_audit import (  # noqa: E402
    load_har, load_gas, clip_z, subsample_units, AE, Adv, RevGrad, PERM_SEED,
)
from exp_regate_v28 import tau_loo_fast, operator_primal  # noqa: E402

RES = ROOT / "results"


def train_embed_subset(Xw, g_all, idx, h, G, lam, seed, epochs, bs=512, lr=1e-3):
    """只在 idx（训练组）上拟合编码器；返回留出组的嵌入。"""
    torch.manual_seed(seed)
    np.random.seed(seed)
    d = Xw.shape[1]
    ae, adv = AE(d, h), Adv(h, G)
    opt = torch.optim.Adam(list(ae.parameters()) + list(adv.parameters()), lr=lr)
    ce = nn.CrossEntropyLoss()
    Xt = torch.tensor(Xw[idx], dtype=torch.float32)
    gt = torch.tensor(g_all[idx], dtype=torch.long)
    n = len(Xt)
    # 批次内若只剩一个样本，BatchNorm 类层不适用；本 AE 无 BN，故安全
    for _ in range(epochs):
        perm = torch.randperm(n)
        for st in range(0, n, bs):
            b = perm[st:st + bs]
            xb, gb = Xt[b], gt[b]
            z, rec = ae(xb)
            loss = ((rec - xb) ** 2).mean()
            if lam > 0:
                loss = loss + ce(adv(RevGrad.apply(z, lam)), gb).mean()
            opt.zero_grad()
            loss.backward()
            opt.step()
    ae.eval()
    with torch.no_grad():
        Z = ae.enc(torch.tensor(Xw, dtype=torch.float32)).numpy()
    return Z


def tau_holdout_probe(X, y, tr_mask, te_mask, alpha=1.0):
    """在 tr_mask 上拟合岭探针（训练折标准化），在 te_mask 上读 Kendall τ。"""
    from exp_regate_v28 import kendall_tau
    mu, sd = X[tr_mask].mean(0), X[tr_mask].std(0) + 1e-8
    Zt = (X[tr_mask] - mu) / sd
    Ze = (X[te_mask] - mu) / sd
    p = Zt.shape[1]
    w = np.linalg.solve(Zt.T @ Zt + alpha * np.eye(p), Zt.T @ y[tr_mask])
    return float(kendall_tau(Ze @ w, y[te_mask]))


def run_outer(name, X, y, g, hid, epochs, doses, seeds, n_units):
    y = np.asarray(y, float)
    g = np.asarray(g, int)
    Xw = clip_z(X)
    uniq, g0 = np.unique(g, return_inverse=True)
    g0 = g0.astype(int)
    G = len(uniq)
    ui = subsample_units(y, g0, n_units) if n_units < len(y) else np.arange(len(y))
    out = []
    for seed in seeds:
        for lam in doses:
            t0 = time.time()
            # (a) 冻结嵌入：编码器在全部组上训练一次（既有口径）
            Zfull = train_embed_subset(Xw, g0, np.arange(len(y)), hid, G, lam,
                                       seed, epochs)
            Zu = Zfull[ui]
            yu, gu = y[ui], g0[ui]
            # 冻结条件下的组留一探针（对照）
            tau_lgo_frozen = []
            for gg in np.unique(gu):
                tr, te = gu != gg, gu == gg
                if tr.sum() < 2 or te.sum() == 0:
                    continue
                tau_lgo_frozen.append(tau_holdout_probe(Zu, yu, tr, te))
            # (b) 外层留组：编码器也只在剩余组上训练
            tau_outer = []
            for gg in np.unique(gu):
                tr_g, te_g = gu != gg, gu == gg            # 单位级索引（审计单位）
                if tr_g.sum() < 2 or te_g.sum() == 0:
                    continue
                # 外层训练用**全部观测**中属于训练组的那些行
                obs_tr = np.where(g0 != gg)[0]
                obs_te = ui[te_g]
                Z = train_embed_subset(Xw, g0, obs_tr, hid, G, lam, seed, epochs)
                # 探针在训练组的审计单位上拟合，在留出组单位上读取
                tau_outer.append(tau_holdout_probe(Z[ui], yu, tr_g, te_g))
            row = {"domain": name, "seed": seed, "lam": lam, "G": G,
                   "m_units": int(len(ui)),
                   "tau_lgo_frozen": float(np.mean(tau_lgo_frozen)),
                   "tau_outer_lgo": float(np.mean(tau_outer)),
                   "tau_loo_all": float(tau_loo_fast(Zu, yu)),
                   "n_folds": int(len(tau_outer)),
                   "fold_sd": float(np.std(tau_outer, ddof=1)),
                   "optimism": float(np.mean(tau_lgo_frozen) - np.mean(tau_outer)),
                   "sec": round(time.time() - t0, 1)}
            out.append(row)
            print(f"  [{name}] s{seed} lam={lam} 冻结 τ_LGO={row['tau_lgo_frozen']:+.4f} "
                  f"外层 τ_LGO={row['tau_outer_lgo']:+.4f} (fold SD {row['fold_sd']:.3f}) "
                  f"乐观量={row['optimism']:+.4f}  ({row['sec']}s)", flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="HAR", choices=["HAR", "GASDRIFT", "all"])
    ap.add_argument("--doses", default="0,2")
    ap.add_argument("--seeds", default="0")
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--n-units", type=int, default=300)
    args = ap.parse_args()
    doses = [float(x) for x in args.doses.split(",")]
    seeds = [int(x) for x in args.seeds.split(",")]
    rows = []
    if args.domain in ("HAR", "all"):
        X, y, g = load_har()
        rows += run_outer("HAR", X, y, g, 64, args.epochs, doses, seeds,
                          args.n_units)
    if args.domain in ("GASDRIFT", "all"):
        X, y, g = load_gas()
        rows += run_outer("GASDRIFT", X, y, g, 32, args.epochs, doses, seeds,
                          args.n_units)
    payload = {"protocol": {
        "purpose": "outer-loop group-disjoint refit (encoder + adversary + probe)",
        "contrast": "tau_lgo_frozen (encoder saw the group) vs tau_outer_lgo "
                    "(encoder trained only on the remaining groups)",
        "epochs": args.epochs, "doses": doses, "seeds": seeds,
        "n_units": args.n_units, "perm_seed": PERM_SEED}, "runs": rows}
    (RES / "outer_refit_v28.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nsaved results/outer_refit_v28.json ({len(rows)} rows)")


if __name__ == "__main__":
    main()
