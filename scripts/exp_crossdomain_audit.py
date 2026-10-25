#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""exp_crossdomain_audit.py — 身份泄漏审计 + 对抗修复在**两个非生物领域**的验证。

目的
----
Patterns 改修后论文的核心论点是"identity leakage 是 group-structured data 的
通用失效模式，空间转录组只是验证域"。本脚本在两个**非生物**公开数据上跑同一套
仪器与同一套修复算子，给出跨领域的实证锚点（而非纯结构性论证）。

仪器（逐字复用 refit_grid_audit，与 ST 队列口径一致）
------------------------------------------------------
  tau_in  : 全样本岭探针 Kendall tau-b（记忆化对照）
  tau_LOO : leave-one-UNIT-out 岭探针 tau + 重拟合置换 p（B=10000）
  tau_LGO : leave-one-GROUP-out 岭探针 tau（同组 sibling unit 整块移出）
  sigma   : tau_LOO 重拟合置换零分布 SD，B=2000，seed 20261010
  LDI     : (tau_LOO - 0.001)/sigma，门限 1.645
  R       : tau_LOO / tau_in（可迁移份额）

修复算子
--------
MLP 自编码器 + 梯度反转（GRL）分组对抗头，剂量扫描 λ ∈ {0, 0.5, 1, 2, 5}，3 seeds。
λ=0 为不施加去偏的基线（同时给出 τ_base/σ̂ 与 Proposition 1 的双门可行性预测）。

领域
----
  HAR      UCI Human Activity Recognition Using Smartphones（可穿戴行为识别）
           group = subject 受试者（G=30）；unit = (subject × activity) cell（180）
           label = 活动类别（序数 0..5）
  GASDRIFT UCI Gas Sensor Array Drift at Different Concentrations（化学传感）
           group = measurement batch 测量批次（G=10）；unit = (batch × gas) cell
           label = 气体种类（序数 0..5）；批次与类别天然不平衡（耦合）

用法
----
    python scripts/exp_crossdomain_audit.py                 # CPU，数分钟
    python scripts/exp_crossdomain_audit.py --epochs 30
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

from refit_grid_audit import audit, insample_tau, operator, kendall_tau  # noqa: E402

import torch  # noqa: E402
import torch.nn as nn  # noqa: E402

TAU_PERP = 0.001
LDI_GATE = 1.645
FIDELITY_KEEP = 0.70
PERM_SEED = 20261010
DATA = ROOT / "data" / "crossdomain"
RES = ROOT / "results"


# --------------------------------------------------------------- 数据
def load_har():
    d = DATA / "har" / "inner" / "UCI HAR Dataset"
    out = []
    for sp in ("train", "test"):
        X = np.loadtxt(d / sp / f"X_{sp}.txt")
        y = np.loadtxt(d / sp / f"y_{sp}.txt")
        s = np.loadtxt(d / sp / f"subject_{sp}.txt")
        out.append((X, y, s))
    X = np.vstack([o[0] for o in out]).astype(np.float64)
    y = np.concatenate([o[1] for o in out]).astype(float)
    s = np.concatenate([o[2] for o in out]).astype(int)
    return X, y - 1.0, s                # 活动类别 -> 0..5


def load_gas():
    d = DATA / "gas" / "Dataset"
    rows, ys, gs = [], [], []
    for b in range(1, 11):
        with open(d / f"batch{b}.dat") as fh:
            for line in fh:
                tok = line.split()
                if not tok:
                    continue
                v = np.zeros(128)
                for t in tok[1:]:
                    i, val = t.split(":")
                    v[int(i) - 1] = float(val)
                rows.append(v)
                ys.append(int(tok[0]))
                gs.append(b)
    X = np.vstack(rows)
    return X, np.asarray(ys, float) - 1.0, np.asarray(gs)


def zscore(X):
    mu, sd = X.mean(0), X.std(0) + 1e-8
    return (X - mu) / sd


def clip_z(X):
    lo, hi = np.percentile(X, [1, 99], axis=0)
    X = np.clip(X, lo, hi)
    return zscore(X)


def subsample_units(y, g, n_units, seed=PERM_SEED):
    """组内比例分层抽样：unit = 单个观测，保留**天然**的 group × label 联合分布
    （即保留真实耦合 κ），同时把 n 压到审计仪器可承受的量级。

    注意：不能用 (group × label) 聚合单元 —— 那样会人为地把标签在组间配平，
    直接抹掉要研究的耦合。"""
    rng = np.random.default_rng(seed)
    g = np.asarray(g, int)
    idx = []
    N = len(y)
    for gg in np.unique(g):
        pool = np.where(g == gg)[0]
        take = int(round(n_units * len(pool) / N))
        take = min(len(pool), max(3, take))
        idx.append(rng.choice(pool, size=take, replace=False))
    idx = np.concatenate(idx)
    return np.sort(idx)


def norm_mi(a, b):
    """归一化互信息（观测层面 group–label 耦合强度 κ），0=独立。"""
    from sklearn.metrics import normalized_mutual_info_score
    return float(normalized_mutual_info_score(a, b))


# --------------------------------------------------------------- 模型
class RevGrad(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, lambd):
        ctx.lambd = lambd
        return x.view_as(x)

    @staticmethod
    def backward(ctx, g):
        return -ctx.lambd * g, None


class AE(nn.Module):
    def __init__(self, d, h, hidden=256):
        super().__init__()
        self.enc = nn.Sequential(nn.Linear(d, hidden), nn.ReLU(),
                                 nn.Linear(hidden, h))
        self.dec = nn.Sequential(nn.Linear(h, hidden), nn.ReLU(),
                                 nn.Linear(hidden, d))

    def forward(self, x):
        z = self.enc(x)
        return z, self.dec(z)


class Adv(nn.Module):
    def __init__(self, h, G, hidden=128):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(h, hidden), nn.ReLU(),
                                 nn.Linear(hidden, G))

    def forward(self, z):
        return self.net(z)


def train_embed(Xw, gw, h, G, lam, seed, epochs, bs=512, lr=1e-3):
    torch.manual_seed(seed)
    np.random.seed(seed)
    d = Xw.shape[1]
    ae, adv = AE(d, h), Adv(h, G)
    opt = torch.optim.Adam(list(ae.parameters()) + list(adv.parameters()), lr=lr)
    ce = nn.CrossEntropyLoss()
    Xt = torch.tensor(Xw, dtype=torch.float32)
    gt = torch.tensor(gw - gw.min(), dtype=torch.long)
    n = len(Xt)
    ae.train()
    adv.train()
    for _ in range(epochs):
        perm = torch.randperm(n)
        for st in range(0, n, bs):
            idx = perm[st:st + bs]
            xb, gb = Xt[idx], gt[idx]
            z, rec = ae(xb)
            loss = ((rec - xb) ** 2).mean()
            if lam > 0:
                loss = loss + ce(adv(RevGrad.apply(z, lam)), gb).mean()
            opt.zero_grad()
            loss.backward()
            opt.step()
    ae.eval()
    with torch.no_grad():
        Z = np.empty((n, h), dtype=np.float64)
        for st in range(0, n, 4096):
            Z[st:st + 4096] = ae.enc(Xt[st:st + 4096]).numpy()
    return Z


def group_id_acc(Zw, gw, seed=0, cap=2500):
    """观测层面：嵌入是否仍能识别分组身份（对抗是否生效的直接证据）。

    多分类 LogisticRegression 在全部观测上很慢，故按组分层抽至 cap 条再拟合。
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    if len(Zw) > cap:
        idx = subsample_units(np.zeros(len(gw)), gw, cap, seed=seed)
        Zw, gw = Zw[idx], gw[idx]
    Zs = (Zw - Zw.mean(0)) / (Zw.std(0) + 1e-8)
    # 每组只有 1 个单位时无法分层（每类仅 1 个成员），退化为不分层切分
    _, cnt = np.unique(gw, return_counts=True)
    strat = gw if cnt.min() >= 2 else None
    Xtr, Xte, ytr, yte = train_test_split(
        Zs, gw, train_size=0.5, random_state=seed, stratify=strat)
    clf = LogisticRegression(max_iter=1000, C=1.0)
    clf.fit(Xtr, ytr)
    acc = float((clf.predict(Xte) == yte).mean())
    chance = 1.0 / len(np.unique(gw))
    return {"acc": acc, "chance": chance, "lift": acc / chance}


# --------------------------------------------------------------- 审计
def sigma_null(X, y):
    H = operator(X)
    rng = np.random.default_rng(PERM_SEED)
    i, j = np.triu_indices(len(y), 1)
    taus = np.empty(2000)
    for st in range(0, 2000, 100):
        Y = np.stack([rng.permutation(y) for _ in range(100)])
        P = Y @ H.T
        aa = np.sign(P[:, j] - P[:, i])
        bb = np.sign(Y[:, j] - Y[:, i])
        den = np.sqrt((aa * aa).sum(1) * (bb * bb).sum(1))
        taus[st:st + 100] = np.divide((aa * bb).sum(1), den,
                                      out=np.zeros(len(P)), where=den > 0)
    return float(taus.std(ddof=1))


def tau_loo_fast(X, y):
    """不带置换的 LOO 岭探针 tau（与 audit() 的观测统计量数学等价，仅省去 p 值）。
    σ̂ 仍走 B=2000 重拟合置换；p_refit 只在 λ=0 基线处计算一次。"""
    H = operator(X)
    return float(kendall_tau(H @ y, y))


def tau_lgo(X, y, groups):
    """leave-one-GROUP-out 岭探针：同组所有 sibling unit 整块移出训练折。"""
    preds = np.zeros(len(y))
    for g in np.unique(groups):
        tr = groups != g
        te = ~tr
        if tr.sum() < 2 or te.sum() == 0:
            continue
        mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-8
        Zt = (X[tr] - mu) / sd
        Ze = (X[te] - mu) / sd
        p = Zt.shape[1]
        w = np.linalg.solve(Zt.T @ Zt + np.eye(p), Zt.T @ y[tr])
        preds[te] = Ze @ w
    return float(kendall_tau(preds, y))


def audit_bundle(X, y, groups, need_p=False):
    tau_loo = tau_loo_fast(X, y)
    a = audit(X, y) if need_p else {"p_refit": float("nan")}
    tau_in = insample_tau(X, y)
    sig = sigma_null(X, y)
    ldi = (tau_loo - TAU_PERP) / sig if sig > 0 else float("inf")
    return {"tau_loo": float(tau_loo), "p_refit": float(a["p_refit"]),
            "tau_in": float(tau_in), "sigma": sig, "ldi": float(ldi),
            "tau_lgo": tau_lgo(X, y, groups),
            "R": float(tau_loo / tau_in) if abs(tau_in) > 1e-9 else float("nan"),
            "gap": float(tau_in - tau_loo)}


# --------------------------------------------------------------- 主流程
def run_domain(name, X, y, g, hid, epochs, doses, seeds, label_name, group_name,
               n_units):
    y = np.asarray(y, float)
    g = np.asarray(g, int)
    kappa = norm_mi(g, y)
    Xw = clip_z(X)
    G = len(np.unique(g))
    ui = subsample_units(y, g, n_units)
    print(f"\n===== {name} =====")
    print(f"  observations={len(y)}  groups(G)={G}  audit units={len(ui)}  "
          f"kappa(group-label NMI)={kappa:.4f}")

    rows = []
    for seed in seeds:
        base = None
        for lam in doses:
            Z = train_embed(Xw, g, hid, G, lam, seed, epochs)
            Xu = Z[ui]
            m = audit_bundle(Xu, y[ui], g[ui], need_p=(lam == 0))
            gid = group_id_acc(Z, g, seed=seed)
            m["inflation"] = float(m["tau_loo"] - m["tau_lgo"])
            if lam == 0:
                base = m
            row = {"domain": name, "seed": seed, "lam": lam,
                   "label": label_name, "group": group_name,
                   "G": G, "m_units": int(len(ui)), "n_obs": int(len(y)),
                   "kappa_obs": kappa,
                   "group_id_acc": gid["acc"], "group_id_chance": gid["chance"],
                   "group_id_lift": gid["lift"],
                   "safety_tau_lgo_kept": (
                       m["tau_lgo"] / base["tau_lgo"]
                       if (base and abs(base["tau_lgo"]) > 1e-9) else float("nan")),
                   "ldi_gate_pass": bool(m["ldi"] < LDI_GATE),
                   "dual_gate_pass": bool(m["ldi"] < LDI_GATE and base is not None
                                          and m["tau_loo"] >= FIDELITY_KEEP * base["tau_loo"]),
                   "safety_tau_loo_kept": (
                       m["tau_loo"] / base["tau_loo"]
                       if (base and abs(base["tau_loo"]) > 1e-9) else float("nan")),
                   }
            row.update(m)
            rows.append(row)
            print(f"  seed{seed} lam={lam:<4} tau_LOO={m['tau_loo']:+.4f} "
                  f"tau_in={m['tau_in']:+.4f} tau_LGO={m['tau_lgo']:+.4f} "
                  f"sig={m['sigma']:.4f} LDI={m['ldi']:+.3f} R={m['R']:.3f} "
                  f"grpID={gid['acc']:.3f}/{gid['chance']:.3f}")
    return rows


def summarise(rows):
    out = {}
    for dom in sorted({r["domain"] for r in rows}):
        rs = [r for r in rows if r["domain"] == dom]
        base = [r for r in rs if r["lam"] == 0]
        tb = float(np.mean([r["tau_loo"] for r in base]))
        sb = float(np.mean([r["sigma"] for r in base]))
        ratio = tb / sb if sb > 0 else float("nan")
        per_dose = []
        for lam in sorted({r["lam"] for r in rs}):
            d = [r for r in rs if r["lam"] == lam]
            per_dose.append({
                "lam": lam,
                "ldi_mean": float(np.mean([r["ldi"] for r in d])),
                "ldi_min": float(np.min([r["ldi"] for r in d])),
                "ldi_max": float(np.max([r["ldi"] for r in d])),
                "tau_loo_mean": float(np.mean([r["tau_loo"] for r in d])),
                "tau_lgo_mean": float(np.mean([r["tau_lgo"] for r in d])),
                "tau_in_mean": float(np.mean([r["tau_in"] for r in d])),
                "tau_loo_sd": float(np.std([r["tau_loo"] for r in d], ddof=1)),
                "tau_lgo_sd": float(np.std([r["tau_lgo"] for r in d], ddof=1)),
                "inflation_mean": float(np.mean([r["inflation"] for r in d])),
                "R_mean": float(np.mean([r["R"] for r in d])),
                "gap_mean": float(np.mean([r["gap"] for r in d])),
                "grp_id_acc_mean": float(np.mean([r["group_id_acc"] for r in d])),
                "grp_id_lift_mean": float(np.mean([r["group_id_lift"] for r in d])),
                "ldi_gate_pass": f"{sum(r['ldi_gate_pass'] for r in d)}/{len(d)}",
                "dual_gate_pass": f"{sum(r['dual_gate_pass'] for r in d)}/{len(d)}",
            })
        out[dom] = {
            "G": int(rs[0]["G"]), "m_units": int(rs[0]["m_units"]),
            "kappa_obs": float(rs[0]["kappa_obs"]),
            "label": rs[0]["label"], "group": rs[0]["group"],
            "group_id_chance": float(rs[0]["group_id_chance"]),
            "tau_base": tb, "sigma_hat": sb, "tau_base_over_sigma": ratio,
            "dual_gate_window_predicted": "non-empty" if ratio < 1.645 / FIDELITY_KEEP
                                          else "empty",
            "prop1_threshold": 1.645 / FIDELITY_KEEP,
            "per_dose": per_dose,
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--doses", default="0,0.5,1,2,5")
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--n-units", type=int, default=300)
    ap.add_argument("--domain", default="all", choices=["all", "HAR", "GASDRIFT"])
    args = ap.parse_args()
    doses = [float(x) for x in args.doses.split(",")]
    seeds = [int(x) for x in args.seeds.split(",")]

    all_rows = []
    if args.domain in ("all", "HAR"):
        X, y, g = load_har()
        all_rows += run_domain("HAR", X, y, g, 64, args.epochs, doses, seeds,
                               "activity (6-class ordinal)", "subject (G=30)",
                               args.n_units)
    if args.domain in ("all", "GASDRIFT"):
        X, y, g = load_gas()
        all_rows += run_domain("GASDRIFT", X, y, g, 32, args.epochs, doses, seeds,
                               "gas species (6-class ordinal)",
                               "measurement batch (G=10)", args.n_units)

    RES.mkdir(exist_ok=True)
    summary = summarise(all_rows)
    tag = args.domain.lower()
    payload = {"protocol": {
        "instrument": "refit_grid_audit (identical to the ST cohorts)",
        "tau_perp": TAU_PERP, "ldi_gate": LDI_GATE,
        "fidelity_keep": FIDELITY_KEEP, "perm_seed": PERM_SEED,
        "perm_B_sigma": 2000, "perm_B_p": 10000,
        "encoder": "MLP autoencoder + GRL group adversary",
        "doses": doses, "seeds": seeds, "epochs": args.epochs},
        "summary": summary, "runs": all_rows}
    (RES / f"crossdomain_{tag}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    with open(RES / f"crossdomain_{tag}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(all_rows[0].keys()))
        w.writeheader()
        w.writerows(all_rows)

    print(f"\n===== SUMMARY ({args.domain}) =====")
    for dom, s in summary.items():
        print(f"\n[{dom}] G={s['G']} units={s['m_units']} kappa={s['kappa_obs']:.4f}")
        print(f"  tau_base={s['tau_base']:.4f} sigma_hat={s['sigma_hat']:.4f} "
              f"ratio={s['tau_base_over_sigma']:.2f} "
              f"(threshold {s['prop1_threshold']:.2f}) -> "
              f"dual-gate window predicted {s['dual_gate_window_predicted']}")
        for d in s["per_dose"]:
            print(f"  lam={d['lam']:<5} LDI={d['ldi_mean']:+.3f} "
                  f"[{d['ldi_min']:+.2f},{d['ldi_max']:+.2f}] "
                  f"tau_LOO={d['tau_loo_mean']:+.4f} tau_LGO={d['tau_lgo_mean']:+.4f} "
                  f"infl={d['inflation_mean']:+.4f} "
                  f"tau_in={d['tau_in_mean']:+.4f} R={d['R_mean']:.3f} "
                  f"grpID_lift={d['grp_id_lift_mean']:.2f} "
                  f"LDIgate={d['ldi_gate_pass']} dualgate={d['dual_gate_pass']}")
    print(f"\nsaved results/crossdomain_{tag}.json / .csv")


if __name__ == "__main__":
    main()
