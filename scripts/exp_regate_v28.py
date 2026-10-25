#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""exp_regate_v28.py — 重做 v27 报告列出的六项方法缺口（A–F），不覆盖任何存档结果。

背景
----
REVIEW_REPORT_v27_20261025.md 的「投稿前必须解决的方法问题」列了 7 项。其中
6 项可以在本机用现有公开数据与已冻结嵌入真跑；第 7 项（外层留患者后重新拟合
完整学习流程）需要重训编码器，另由 --outer 开关单独评估其代价。本脚本不改写
results 中任何既有文件，全部输出带 _v28 后缀。

口径（逐字复用既有仪器，不另造统计量）
--------------------------------------
  operator / kendall_tau / insample_tau : refit_grid_audit（LOO 岭帽矩阵，alpha=1）
  tau_LOO / tau_LGO                     : exp_crossdomain_audit.audit_bundle
  load_har / load_gas / clip_z / subsample_units / train_embed : exp_crossdomain_audit
  load_geomx / build_arms               : exp_within_group_label_geomx

新增（本脚本的六项）
--------------------
A. 组保持置换空分布 sigma_group：组内独立置换标签（保持 group×label 联合分布，
   即保持耦合 κ）；与既有 free 置换（全样本随机置换）并列报告，并给出两种置换
   零分布下的**置换 p 值**（同一批 B 次置换同时产出 SD 与 p，无额外成本）。
   若标签在组内恒定，则组保持置换退化为恒等变换 → sigma_group = 0，此时
   LDI 无定义，标记 degenerate：这是「组级推断不可行」的直接证据，不是错误。
B. 三指标分解：标签效用（tau_LOO 与名义多分类指标）、身份解码（leave-one-GROUP-out
   身份分类 lift，避免同组观测跨折）、泄漏差值 Δ = tau_LOO − tau_LGO。
C. 名义多分类指标 + 重编码敏感性：macro one-vs-rest AUROC 与 balanced accuracy
   走 LGO 折外预测、逐类二分类，完全不依赖类别编号；同时对类别编号做 R 次随机
   置换重算 tau_LOO，量化编码依赖。
D. 冻结基线 sigma 的尺度敏感性：同一批 run 上对比逐 run 重估 sigma 与冻结 λ=0
   基线 sigma（逐 seed / 队列均值）两种口径下的 LDI 与双门计数。
E. 宫颈 donor 对照表：35 切片 → 34 供体（CA_HPV_1 / CA_HPV_2 同一供体），按真实
   供体重算 tau_LDO / tau_LGO，取代「LOO = LGO」的表述。
F. GeoMx 患者层级敏感性：7 case / 6 patient 但配对未公开 → 枚举 C(7,2)=21 种配对，
   逐配对重算组级统计量与双门，报告结论是否依赖配对。

用法
----
    python scripts/exp_regate_v28.py --quick            # 单域单 seed 冒烟 + 计时
    python scripts/exp_regate_v28.py                    # 全量（A–E）
    python scripts/exp_regate_v28.py --patient-enum     # 追加 F（21 配对枚举）
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

from refit_grid_audit import operator, insample_tau, kendall_tau  # noqa: E402
from exp_crossdomain_audit import (  # noqa: E402
    load_har, load_gas, clip_z, subsample_units, train_embed, norm_mi,
    TAU_PERP, LDI_GATE, FIDELITY_KEEP, PERM_SEED,
)

RES = ROOT / "results"
B_SIGMA = 2000          # 与既有 σ̂ 口径一致
N_RECODE = 20           # 重编码敏感性重复次数
ID_CAP = 1500           # 身份解码子抽样上限（观测数）
RECODE_SEED = 20261011

# 宫颈切片名 → 供体键（与 repair_e3_methodB_train.py 的 _donor_key 逐字一致）
_DONOR_RE = re.compile(r'((?:HPV[pn]|N|HSIL|CA)_[A-Za-z0-9]+)', re.IGNORECASE)


def donor_key(nm: str) -> str:
    m = _DONOR_RE.match(nm)
    return m.group(1).upper() if m else str(nm)


def operator_primal(X, alpha=1.0):
    """与 refit_grid_audit.operator 数学等价的 primal 实现（训练折标准化、
    alpha=1、无截距）。kernel 版每次留一都解 (n-1)×(n-1) 系统，p << n 时
    primal 版（解 p×p）快一个数量级以上；两版差异在脚本入口做数值自检。"""
    n, p = X.shape
    if p >= n - 1:                      # primal 无优势时回退到既有实现
        return operator(X)
    H = np.zeros((n, n))
    eye = alpha * np.eye(p)
    for i in range(n):
        tr = np.arange(n) != i
        mu = X[tr].mean(0)
        sd = X[tr].std(0) + 1e-8
        Z = (X[tr] - mu) / sd
        z = (X[i] - mu) / sd
        H[i, tr] = Z @ np.linalg.solve(Z.T @ Z + eye, z)
    return H


def selfcheck_operator(seed=0, n=60, p=16):
    """primal 与 kernel 两版帽矩阵的数值等价性自检（写入 protocol）。"""
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, p))
    return float(np.abs(operator_primal(X) - operator(X)).max())


# ----------------------------------------------------------- A. 置换空分布
def _perm_taus(H, Y, i, j):
    """一批重排标签的 LOO 岭探针 tau（重拟合置换，与 refit_grid_audit 同式）。"""
    P = Y @ H.T
    a = np.sign(P[:, j] - P[:, i])
    b = np.sign(Y[:, j] - Y[:, i])
    den = np.sqrt((a * a).sum(1) * (b * b).sum(1))
    return np.divide((a * b).sum(1), den,
                     out=np.zeros(len(P)), where=den > 0)


def _draw_perm(y, groups, rng, mode):
    if mode == "free":
        return rng.permutation(y)
    out = y.copy()
    for g in np.unique(groups):
        idx = np.where(groups == g)[0]
        out[idx] = rng.permutation(y[idx])
    return out


def null_bundle(X, y, groups, obs_tau, B=B_SIGMA, seed=PERM_SEED):
    """两种零分布：free（全样本随机置换，既有口径）与 group（组内置换，保持 κ）。

    同一批 B 次置换同时给出 SD（σ̂）与置换 p 值，不额外增加计算。
    """
    H = operator_primal(X)
    i, j = np.triu_indices(len(y), 1)
    rng = np.random.default_rng(seed)
    out = {}
    for mode in ("free", "group"):
        taus = np.empty(B)
        for st in range(0, B, 100):
            Y = np.stack([_draw_perm(y, groups, rng, mode) for _ in range(100)])
            taus[st:st + 100] = _perm_taus(H, Y, i, j)
        sd = float(taus.std(ddof=1))
        p = float((int((taus >= obs_tau - 1e-12).sum()) + 1) / (B + 1))
        out[f"sigma_{mode}"] = sd
        out[f"p_{mode}"] = p
        out[f"null_degenerate_{mode}"] = bool(sd < 1e-12)
    return out


# ----------------------------------------------------------- B/C. 指标
def tau_loo_fast(X, y):
    H = operator_primal(X)
    return float(kendall_tau(H @ y, y))


def lgo_pred(X, y, groups, alpha=1.0):
    """leave-one-GROUP-out 岭探针折外预测（与 exp_crossdomain_audit.tau_lgo 同式）。"""
    preds = np.full(len(y), np.nan)
    for g in np.unique(groups):
        tr = groups != g
        te = ~tr
        if tr.sum() < 2 or te.sum() == 0:
            continue
        mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-8
        Zt = (X[tr] - mu) / sd
        Ze = (X[te] - mu) / sd
        p = Zt.shape[1]
        w = np.linalg.solve(Zt.T @ Zt + alpha * np.eye(p), Zt.T @ y[tr])
        preds[te] = Ze @ w
    return preds


def tau_lgo(X, y, groups):
    pr = lgo_pred(X, y, groups)
    m = ~np.isnan(pr)
    return float(kendall_tau(pr[m], y[m])) if m.sum() > 2 else float("nan")


def nominal_metrics(X, y, groups):
    """名义多分类指标：逐类 one-vs-rest 的 LGO 折外 AUROC + pooled balanced accuracy。

    不依赖类别编号：每个类单独做二分类岭探针，预测类别取各类分数最大者。
    """
    from sklearn.metrics import roc_auc_score, balanced_accuracy_score
    classes = np.unique(y)
    if len(classes) < 2:
        return {"macro_ovr_auc": float("nan"), "balanced_acc": float("nan"),
                "n_classes": int(len(classes))}
    scores, aucs = [], []
    for c in classes:
        s = lgo_pred(X, (y == c).astype(float), groups)
        m = ~np.isnan(s)
        scores.append(np.where(m, s, -np.inf))
        yy = (y == c).astype(int)
        if len(np.unique(yy[m])) == 2:
            aucs.append(float(roc_auc_score(yy[m], s[m])))
        else:
            aucs.append(float("nan"))
    S = np.vstack(scores).T
    ok = np.isfinite(S).all(1)
    pred = np.argmax(np.where(ok[:, None], S, -np.inf), axis=1)
    bal = float(balanced_accuracy_score(y[ok], classes[pred[ok]])) if ok.sum() > 0 \
        else float("nan")
    return {"macro_ovr_auc": float(np.nanmean(aucs)),
            "balanced_acc": bal,
            "n_classes": int(len(classes)),
            "per_class_auc": [None if np.isnan(a) else round(a, 6) for a in aucs]}


def recoding_sensitivity(X, y, groups, R=N_RECODE, seed=RECODE_SEED):
    """随机重排类别编号后重算 tau_LOO：量化「把名义编号当数值」的编码依赖。

    macro OVR AUROC 走逐类二分类，理论上与编号无关，作为对照一并给出。
    """
    classes = np.unique(y)
    if len(classes) < 2 or len(np.unique(y)) < 3:
        return {"tau_loo_recode_sd": float("nan"),
                "tau_loo_recode_range": float("nan"),
                "tau_loo_identity": float("nan"),
                "auc_recode_sd": float("nan")}
    rng = np.random.default_rng(seed)
    taus = []
    for _ in range(R):
        perm = rng.permutation(classes)
        mapping = {c: v for c, v in zip(classes, perm)}
        yr = np.array([mapping[v] for v in y], dtype=float)
        taus.append(tau_loo_fast(X, yr))
    taus = np.asarray(taus)
    # 对照：一次重编码下的 macro OVR AUROC（应与原编码下相同）
    perm = np.random.default_rng(seed).permutation(classes)
    mapping = {c: v for c, v in zip(classes, perm)}
    yr = np.array([mapping[v] for v in y], dtype=float)
    auc_r = nominal_metrics(X, yr, groups)["macro_ovr_auc"]
    auc_0 = nominal_metrics(X, y, groups)["macro_ovr_auc"]
    return {"tau_loo_recode_sd": float(taus.std(ddof=1)),
            "tau_loo_recode_range": float(taus.max() - taus.min()),
            "tau_loo_identity": float(tau_loo_fast(X, y)),
            "auc_recode_sd": float(abs(auc_r - auc_0)) if np.isfinite(auc_r) else float("nan"),
            "auc_recode_delta": float(auc_r - auc_0) if np.isfinite(auc_r) else float("nan")}


def identity_metrics(Z, groups, cap=ID_CAP, seed=0):
    """身份解码（B 项）：两个**不依赖类别可见性**的组身份可解码性度量。

    为什么不用「留出整组 + 多分类预测组 ID」：当每个组是一个类别时，留出组的
    类别在训练折中从未出现，分类器在结构上不可能预测它，准确率会被压到 0，
    与「嵌入是否携带身份」无关。既有 group_id_acc 走另一个极端：按观测随机
    切分，同组观测同时落在训练与测试折，从而高估可解码性。

    这里改用两个在任何分组方案下都有定义的度量：
      id_knn_lift  留一最近邻是否同组（1-NN 同组命中率 / 同组先验 Σ(n_g/N)²）。
                   不要求测试组的类别在训练集中出现过。
      id_pair_auc  同组对 vs 异组对的嵌入距离判别 AUROC（同组更近 → > 0.5）。
                   成对判别同样不需要类别可见性。
    """
    g = np.asarray(groups)
    n = min(len(Z), len(g))              # 嵌入与分组向量长度必须对齐
    Z, g = Z[:n], g[:n]
    if len(Z) > cap:
        idx = subsample_units(np.zeros(len(g)), g, cap, seed=seed)
        Z, g = Z[idx], g[idx]
    uniq, g = np.unique(g, return_inverse=True)
    g = g.astype(int)
    G = len(uniq)
    if G < 2 or len(g) < 3:
        return {"id_knn_lift": float("nan"), "id_pair_auc": float("nan"),
                "id_note": "G<2"}
    if np.bincount(g, minlength=G).min() < 2:
        # 单样本组：1-NN 同组命中在结构上不可达，仅成对判别仍有定义
        pass
    Zs = (Z - Z.mean(0)) / (Z.std(0) + 1e-8)
    from scipy.spatial.distance import pdist, squareform
    D = squareform(pdist(Zs))
    n_ = len(g)
    # 1-NN 同组命中
    np.fill_diagonal(D, np.inf)
    nn = np.argmin(D, axis=1)
    hit = float((g[nn] == g).mean())
    _, cnt = np.unique(g, return_counts=True)
    chance = float(((cnt / n_) ** 2).sum())
    # 成对距离判别
    from sklearn.metrics import roc_auc_score
    i, j = np.triu_indices(n_, 1)
    same = (g[i] == g[j]).astype(int)
    auc = float(roc_auc_score(same, -D[i, j])) if len(np.unique(same)) == 2 \
        else float("nan")
    return {"id_knn_hit": hit, "id_knn_chance": chance,
            "id_knn_lift": float(hit / chance) if chance > 0 else float("nan"),
            "id_pair_auc": auc, "id_note": "1-NN + pairwise"}


# ----------------------------------------------------------- 单次审计
def audit_full(Xu, yu, gu, Zfull=None, gfull=None, nominal=False, recode=False,
               identity=True):
    """一个 run 的全套读数。Xu/yu/gu 为审计单位；Zfull/gfull 用于身份解码。"""
    tau_loo = tau_loo_fast(Xu, yu)
    tau_in = insample_tau(Xu, yu)
    nb = null_bundle(Xu, yu, gu, tau_loo)
    tau_lgo_v = tau_lgo(Xu, yu, gu)
    out = {"tau_loo": float(tau_loo), "tau_in": float(tau_in),
           "tau_lgo": float(tau_lgo_v),
           "gap": float(tau_in - tau_loo),
           "R": float(tau_loo / tau_in) if abs(tau_in) > 1e-9 else float("nan"),
           "inflation": float(tau_loo - tau_lgo_v)}
    out.update(nb)
    for mode in ("free", "group"):
        sd = out[f"sigma_{mode}"]
        out[f"ldi_{mode}"] = (float((tau_loo - TAU_PERP) / sd)
                              if sd > 1e-12 else None)
        out[f"ldi_{mode}_gate_pass"] = (bool(out[f"ldi_{mode}"] < LDI_GATE)
                                        if out[f"ldi_{mode}"] is not None else None)
    # 组内标签变异（决定组保持置换是否退化）
    vary = []
    for g in np.unique(gu):
        vary.append(len(np.unique(yu[gu == g])) > 1)
    out["frac_groups_varying"] = float(np.mean(vary)) if vary else float("nan")
    out["kappa_units"] = float(norm_mi(gu, yu))
    if nominal or recode:
        nm = nominal_metrics(Xu, yu, gu)
        out["macro_ovr_auc"] = nm["macro_ovr_auc"]
        out["balanced_acc"] = nm["balanced_acc"]
        out["n_classes"] = nm["n_classes"]
    if recode:
        out.update(recoding_sensitivity(Xu, yu, gu))
    if identity and Zfull is not None and gfull is not None:
        out.update(identity_metrics(Zfull, gfull))
    return out


# ----------------------------------------------------------- 域 runner
def run_domain(name, X, y, g, hid, epochs, doses, seeds, n_units, label_desc,
               group_desc, nominal=False, recode=False, identity=True,
               arm=None):
    y = np.asarray(y, float)
    g = np.asarray(g, int)
    Xw = clip_z(X)
    G = len(np.unique(g))
    ui = subsample_units(y, g, n_units) if n_units < len(y) else np.arange(len(y))
    print(f"\n===== {name} =====")
    print(f"  obs={len(y)}  groups(G)={G}  audit units={len(ui)}  "
          f"kappa(obs)={norm_mi(g, y):.4f}", flush=True)
    rows = []
    for seed in seeds:
        for lam in doses:
            t0 = time.time()
            Z = train_embed(Xw, g, hid, G, lam, seed, epochs)
            Xu, yu, gu = Z[ui], y[ui], g[ui]
            m = audit_full(Xu, yu, gu, Z, g, nominal=nominal, recode=recode,
                           identity=identity)
            row = {"domain": name, "arm": arm or "", "seed": seed, "lam": lam,
                   "label": label_desc, "group": group_desc,
                   "G": G, "m_units": int(len(ui)), "n_obs": int(len(y)),
                   "train_sec": round(time.time() - t0, 1)}
            row.update(m)
            rows.append(row)
            print(f"  s{seed} lam={lam:<4} tau_LOO={m['tau_loo']:+.4f} "
                  f"tau_LGO={m['tau_lgo']:+.4f} "
                  f"sd_free={m['sigma_free']:.4f} sd_grp={m['sigma_group']:.4f} "
                  f"p_free={m['p_free']:.4f} p_grp={m['p_group']:.4f} "
                  f"LDI_free={m['ldi_free']} LDI_grp={m['ldi_group']} "
                  f"id_knn_lift={m.get('id_knn_lift')} "
                  f"id_pair_auc={m.get('id_pair_auc')} "
                  f"({row['train_sec']}s)", flush=True)
    return rows


def run_cervix():
    """E 项：宫颈冻结切片级嵌入 + 35 切片 → 34 供体对照表。"""
    p = RES / "dump_cervix.json"
    if not p.exists():
        print("  [skip] dump_cervix.json missing")
        return []
    d = json.loads(p.read_text(encoding="utf-8"))
    rows = []
    for key, v in d["dump_xs"].items():
        Xs = np.asarray(v["Xs"], float)
        y = np.asarray(v["y"], float)
        names = list(v["names"])
        seed = int(re.match(r"s(\d+)_lam", key).group(1))
        lam = float(re.match(r"s\d+_lam([\d.]+)", key).group(1))
        gname = [donor_key(n) for n in names]
        _, g = np.unique(gname, return_inverse=True)
        g = g.astype(int)
        pair = {n: donor_key(n) for n in names if donor_key(n) != n}
        # 核对该供体是否真的对应多个切片
        m = audit_full(Xs, y, g, Zfull=None, gfull=None, nominal=True,
                       recode=False, identity=False)
        row = {"domain": "CERVIX", "arm": "", "seed": seed, "lam": lam,
               "label": "slice-level severity (0=normal,1=HSIL,2=cancer)",
               "group": "donor key (34 donors / 35 slices)",
               "G": int(len(np.unique(g))), "m_units": int(len(y)),
               "n_obs": int(len(y)), "train_sec": 0.0,
               "donor_pairs": pair,
               "n_slices_per_donor": {int(k): int(vv) for k, vv in
                                      zip(*np.unique(g, return_counts=True))}}
        row.update(m)
        rows.append(row)
        print(f"  [CERVIX] {key} donors={row['G']} tau_LOO={m['tau_loo']:+.4f} "
              f"tau_LGO={m['tau_lgo']:+.4f} sd_free={m['sigma_free']:.4f} "
              f"sd_grp={m['sigma_group']:.4f} "
              f"degen_free={m['null_degenerate_free']} "
              f"degen_grp={m['null_degenerate_group']}", flush=True)
    return rows


def patient_enumeration(X, arms, gcase_epochs=30, doses=(0.0, 2.0), seeds=(0,)):
    """F 项：7 case / 6 patient 的配对未公开 → 枚举 21 种配对。"""
    from exp_within_group_label_geomx import load_geomx, build_arms
    Xm, meta, titles = load_geomx(top_gene=2000)
    g, ys, gcase = build_arms(meta, titles)
    arm_map = {"risk": ys[0], "silva": ys[1], "cell_type": ys[2]}
    cases = sorted(set(gcase))
    out = []
    print(f"\n===== F. GeoMx patient-pair enumeration ({len(cases)} cases) =====",
          flush=True)
    for name, y in arm_map.items():
        if arms and name not in arms:
            continue
        # 基线：case 作为组（7 组）
        for a, b in itertools.combinations(range(len(cases)), 2):
            gp = g.copy()
            gp[gp == b] = a                  # 合并两 case 为同一患者
            _, gpr = np.unique(gp, return_inverse=True)
            gpr = gpr.astype(int)
            row = {"arm": name, "pair": f"{cases[a]}+{cases[b]}",
                   "G_patient": int(len(np.unique(gpr))),
                   "tau_lgo_case": float(tau_lgo(Xm, y, g)),
                   "tau_lgo_patient": float(tau_lgo(Xm, y, gpr))}
            out.append(row)
        print(f"  arm={name}: tau_LGO(case)={tau_lgo(Xm, y, g):+.4f}  "
              f"patient-merge range "
              f"[{min(r['tau_lgo_patient'] for r in out if r['arm'] == name):+.4f},"
              f" {max(r['tau_lgo_patient'] for r in out if r['arm'] == name):+.4f}]",
              flush=True)
    return out


# ----------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--doses", default="0,2")
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--n-units", type=int, default=300)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only", default="all",
                    choices=["all", "har", "gas", "geomx", "cervix"])
    ap.add_argument("--patient-enum", action="store_true")
    args = ap.parse_args()
    doses = [float(x) for x in args.doses.split(",")]
    seeds = [int(x) for x in args.seeds.split(",")]
    if args.quick:
        doses, seeds = doses[:1], seeds[:1]

    t_all = time.time()
    rows = []
    if args.only in ("all", "har"):
        X, y, g = load_har()
        rows += run_domain("HAR", X, y, g, 64, args.epochs, doses, seeds,
                           args.n_units, "activity (6-class nominal)",
                           "subject (G=30)", nominal=True, recode=True)
        if args.quick:
            args.only = "har"
    if args.only in ("all", "gas"):
        X, y, g = load_gas()
        rows += run_domain("GASDRIFT", X, y, g, 32, args.epochs, doses, seeds,
                           args.n_units, "gas species (6-class nominal)",
                           "measurement batch (G=10)", nominal=True, recode=True)
    if args.only in ("all", "geomx"):
        from exp_within_group_label_geomx import load_geomx, build_arms
        Xm, meta, titles = load_geomx(top_gene=2000)
        g, ys, _ = build_arms(meta, titles)
        G = len(np.unique(g))
        for nm, yy, desc in (("risk", ys[0], "patient risk stratum (ordinal)"),
                             ("silva", ys[1], "Silva pattern per ROI (ordinal)"),
                             ("cell_type", ys[2], "ROI cell type (nominal)")):
            rows += run_domain(f"GEOMX_{nm.upper()}", Xm, yy, g, 64,
                               args.epochs, doses, seeds, len(yy), desc,
                               f"caseid (G={G})", nominal=True, recode=True,
                               arm=nm)
    if args.only in ("all", "cervix"):
        print("\n===== CERVIX (frozen slice embeddings) =====", flush=True)
        rows += run_cervix()

    payload = {"protocol": {
        "purpose": "re-run of the six remediable method gaps in "
                   "REVIEW_REPORT_v27_20261025.md",
        "instrument": "refit_grid_audit operator (LOO ridge hat matrix, alpha=1)",
        "tau_perp": TAU_PERP, "ldi_gate": LDI_GATE,
        "fidelity_keep": FIDELITY_KEEP,
        "perm_seed": PERM_SEED, "B_sigma_and_p": B_SIGMA,
        "null_modes": ["free (whole-sample label permutation, legacy)",
                       "group (within-group label permutation, preserves kappa)"],
        "recoding_R": N_RECODE, "recode_seed": RECODE_SEED,
        "operator_primal_vs_kernel_max_abs_diff": selfcheck_operator(),
        "identity": "leave-one-GROUP-out multinomial logistic; chance=1/G",
        "doses": doses, "seeds": seeds, "epochs": args.epochs,
        "elapsed_sec": round(time.time() - t_all, 1)},
        "runs": rows}
    if args.patient_enum:
        payload["patient_enumeration"] = patient_enumeration(None, None)

    RES.mkdir(exist_ok=True)
    tag = "_quick" if args.quick else ""
    (RES / f"regate_v28{tag}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    keys = sorted({k for r in rows for k in r})
    with open(RES / f"regate_v28{tag}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"\nsaved results/regate_v28{tag}.json / .csv  "
          f"({len(rows)} runs, {round(time.time() - t_all, 1)}s)")


if __name__ == "__main__":
    main()
