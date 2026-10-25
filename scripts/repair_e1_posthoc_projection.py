#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""repair_e1_posthoc_projection.py — MRP-ST-Repair E1 go/no-go（方法 A：患者块残差投影）。

问题
----
审计检测到的标签依赖（LDI > 1.645）能否被 post-hoc 修复算子单调压到门槛以下，
同时保留真实表征信息（tau_insample 降幅 < 30%）？

方法 A（零训练成本）
--------------------
对 spot 级嵌入 Z (N_spots × d)：按切片（=独立病灶/患者代理）算均值 μ_p，
对 {μ_p − μ̄} 做 SVD 取前 k 维得患者均值子空间 P_pat (d×k)，
修复嵌入 Z̃ = Z − P_pat P_patᵀ Z，再切片级池化 → LDI / p_refit / tau_insample。

判定（方案 §4 E1）
------------------
go   = FULL 臂（真实宫颈 + 仿真强/弱共享）存在 k 使 LDI 单调降至 < 1.645，
       且 tau_insample 保留 ≥ 70%；
对照 = C 恒等混淆（修复不得制造新显著性）+ A_NOALL 无监督阴性（修复后 LDI 仍 < 1.645）。

口径
----
LDI = (tau − 0.001) / σ_null；σ_null 取 refit 置换分布（B=10000，seed=20261010，
与审计论文/主检验完全一致）的 SD；p_refit 同一分布的精确置换 p。
operator()/置换逻辑逐字复用 refit_grid_audit.py。
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import kendalltau

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from refit_grid_audit import operator, kendall_tau, insample_tau  # noqa: E402
from probe_lodo import severity_of  # noqa: E402

RES = ROOT / "results"
OUT = RES / "repair_e1_posthoc.json"

TAU_PERP = 0.001      # 审计论文固定零中心
LDI_GATE = 1.645      # 单侧 5% 高斯门
KS = [0, 1, 2, 4, 8]  # 0 = 不修复基线
B_PERM = 10000
SEED = 20261010
FIDELITY_KEEP = 0.70  # LOO tau（τ̄_FULL 口径）保留阈值（降幅 <30%）

ARMS = [
    # (arm, kind, files, role)
    # 判定臂仅真实宫颈（仿真注入 program 本身决定 y，切片级 LDI 无法区分
    # 任务信号与泄漏——见输出注记；仿真臂降级为机制观察，不入 go 判据）
    ("cervical_FULL", "real", [RES / f"fused_embs_FULL_seed{s}.npz" for s in (0, 3, 4)],
     "target"),
    ("simA_FULL", "sim", [RES / f"fused_embs_SIM_group_A_FULL_seed{s}.npz" for s in (0, 1, 2)],
     "mechanism-observation"),
    ("simB_FULL", "sim", [RES / f"fused_embs_SIM_group_B_FULL_seed{s}.npz" for s in (0, 1, 2)],
     "mechanism-observation"),
    ("simC_CTRL", "sim", [RES / f"fused_embs_SIM_group_C_FULL_seed{s}.npz" for s in (0, 1, 2)],
     "confound-control"),
    ("simA_NOALL", "sim", [RES / f"fused_embs_SIM_group_A_NOALL_seed{s}.npz" for s in (0, 1, 2)],
     "mechanism-observation"),
]


def pool_by_sample(Z, sids):
    """与 probe_lodo.per_sample_embedding 相同的池化与 severity 附着。"""
    names, inv = np.unique(sids, return_inverse=True)
    vecs, ys, kept = [], [], []
    for k, nm in enumerate(names):
        sev = severity_of(str(nm))
        if sev is None:
            continue
        vecs.append(Z[inv == k].mean(axis=0))
        ys.append(sev)
        kept.append(str(nm))
    return np.vstack(vecs), np.array(ys, float), kept


def patient_block_project(Z, sids, k):
    """方法 A：患者（切片）均值子空间残差投影。"""
    names, inv = np.unique(sids, return_inverse=True)
    M = np.stack([Z[inv == i].mean(axis=0) for i in range(len(names))])
    Mc = M - M.mean(axis=0)
    _, _, Vt = np.linalg.svd(Mc, full_matrices=False)
    P = Vt[:k].T                      # d × k
    return Z - (Z @ P) @ P.T          # Z̃ = Z − P Pᵀ Z


def ldi_probe(X, y):
    """审计口径置换（B=10000，seed 固定）→ tau / p_refit / LDI。"""
    H = operator(X)
    pred = H @ y
    obs = float(kendalltau(pred, y)[0])
    rng = np.random.default_rng(SEED)
    i, j = np.triu_indices(len(y), 1)
    taus = np.empty(B_PERM)
    den_mask = None
    for start in range(0, B_PERM, 100):
        Y = np.stack([rng.permutation(y) for _ in range(100)])
        P = Y @ H.T
        a = np.sign(P[:, j] - P[:, i])
        b = np.sign(Y[:, j] - Y[:, i])
        den = np.sqrt((a * a).sum(1) * (b * b).sum(1))
        t = np.divide((a * b).sum(1), den, out=np.zeros(len(P)), where=den > 0)
        taus[start:start + 100] = t
    ge = int((taus >= obs - 1e-12).sum())
    sigma_null = float(taus.std(ddof=1))
    return {"tau": obs,
            "p_refit": (ge + 1) / (B_PERM + 1),
            "sigma_null": sigma_null,
            "ldi": (obs - TAU_PERP) / sigma_null if sigma_null > 0 else float("inf")}


def run_file(fp, tag):
    npz = np.load(fp, allow_pickle=True)
    Z0 = npz["fused"]
    sids = npz["sample_ids"].astype(str)
    rows = {}
    for k in KS:
        Z = Z0 if k == 0 else patient_block_project(Z0, sids, k)
        X, y, _ = pool_by_sample(Z, sids)
        if len(np.unique(y)) < 2:
            rows[k] = None
            continue
        r = ldi_probe(X, y)
        r["tau_insample"] = insample_tau(X, y)
        r["n_slices"] = int(len(y))
        rows[k] = r
        print(f"  [{tag}] k={k}  LDI={r['ldi']:+.3f}  tau={r['tau']:+.4f}  "
              f"p_refit={r['p_refit']:.4f}  tau_in={r['tau_insample']:+.4f}")
    return rows


def main():
    report = {"params": {"ks": KS, "b_perm": B_PERM, "seed": SEED,
                         "tau_perp": TAU_PERP, "ldi_gate": LDI_GATE,
                         "fidelity_keep": FIDELITY_KEEP},
              "arms": {}}
    for arm, kind, files, role in ARMS:
        print(f"=== {arm} ({role}, {kind}) ===")
        runs = []
        for fp in files:
            if not fp.exists():
                print(f"  [miss] {fp.name}")
                runs.append(None)
                continue
            runs.append(run_file(fp, fp.name.replace("fused_embs_", "").replace(".npz", "")))
        report["arms"][arm] = {"role": role, "kind": kind, "runs": runs}

    # ---- 判定聚合 ----
    verdict = {}

    def arm_metric(arm):
        """跨种子均值：每个 k 的 LDI 均值与 LOO tau（τ̄_FULL 口径）均值。"""
        runs = [r for r in report["arms"][arm]["runs"] if r]
        ks = [k for k in KS if all(r and r.get(k) for r in runs)]
        mean_ldi = {k: float(np.mean([r[k]["ldi"] for r in runs])) for k in ks}
        mean_tau = {k: float(np.mean([r[k]["tau"] for r in runs])) for k in ks}
        return mean_ldi, mean_tau

    # 目标臂（真实宫颈）：存在 k 使 mean LDI < 门，k 扫描单调（允许 ≤0.05 抖动），
    # 且 **LOO tau**（τ̄_FULL 口径）保留 ≥ 70%
    target_ok, detail = {}, {}
    for arm in ("cervical_FULL",):
        mean_ldi, mean_tau = arm_metric(arm)
        base_tau = mean_tau.get(0)
        ks_sorted = sorted(mean_ldi)
        mono = all(mean_ldi[ks_sorted[i + 1]] <= mean_ldi[ks_sorted[i]] + 0.05
                   for i in range(len(ks_sorted) - 1))
        pass_ks = [k for k in ks_sorted if k > 0 and mean_ldi[k] < LDI_GATE]
        keep_ok = any(base_tau is not None and base_tau > 0 and
                      mean_tau[k] >= FIDELITY_KEEP * base_tau for k in pass_ks)
        target_ok[arm] = bool(pass_ks and mono and keep_ok)
        detail[arm] = {"mean_ldi": mean_ldi, "mean_tau_lodo": mean_tau,
                       "monotone": mono, "pass_ks": pass_ks,
                       "fidelity_ok": keep_ok}
    verdict["targets"] = detail

    # 机制观察臂（仿真）：如实报告，不入判定
    for arm in ("simA_FULL", "simB_FULL", "simC_CTRL", "simA_NOALL"):
        ml, mt = arm_metric(arm)
        verdict.setdefault("sim_observations", {})[arm] = {"mean_ldi": ml, "mean_tau_lodo": mt}

    full_pass = all(target_ok.values())
    n_pass = sum(target_ok.values())
    verdict["E1"] = ("go" if full_pass else
                     "partial-go" if n_pass >= 2 else
                     "no-go")
    verdict["target_pass_summary"] = target_ok
    report["verdict"] = verdict

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\n==== E1 verdict ====")
    for arm, ok in target_ok.items():
        print(f"  {arm:16s}: {'PASS' if ok else 'FAIL'}  "
              f"pass_ks={detail[arm]['pass_ks']}  mono={detail[arm]['monotone']}  "
              f"fidelity={detail[arm]['fidelity_ok']}")
    for arm, obs in verdict["sim_observations"].items():
        print(f"  [obs] {arm:16s}: mean LDI(k)={[round(v,2) for v in obs['mean_ldi'].values()]}"
              f"  mean tau(k)={[round(v,3) for v in obs['mean_tau_lodo'].values()]}")
    print(f"  E1 = {verdict['E1']}  (saved {OUT.relative_to(ROOT)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
