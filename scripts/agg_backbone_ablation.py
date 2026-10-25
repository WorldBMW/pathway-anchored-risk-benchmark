"""骨干对照汇总：GAT（图注意力） vs MLP（无消息传递，与跨域审计同族）。

输出 results/backbone_ablation.json / .csv，用于手稿 Table S12 与
"Backbone generality" 一节。口径与正文一致：
  LDI      = (tau_LOO - tau_perp) / sigma_null
  tau_base/sigma_hat  = tau_LDO(lambda=0) / sigma_null   （Proposition 1 的可预测量）
  retention = tau_LDO(lambda) / tau_LDO(lambda=0)
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

RES = Path(__file__).resolve().parents[1] / "results"
TAU_PERP = 0.0          # 与 refit_grid_audit 一致
PROP1_THRESHOLD = 2.35  # c = 0.7
LDI_GATE = 1.645
FIDELITY_KEEP = 0.70


def load_scan(path):
    """返回 {lam: {seed: row}}。"""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    out = {}
    for k, v in d["scan"].items():
        # key 形如 s0_lam0.0
        seed = int(k.split("_")[0][1:])
        lam = float(k.split("lam")[1])
        out.setdefault(lam, {})[seed] = v
    return out, d.get("params", {})


def collect(dataset, backbone, paths):
    """paths: list of result json（会被合并到同一 (dataset, backbone) 下）"""
    scans = {}
    for p in paths:
        fp = RES / p
        if not fp.exists():
            print(f"  [miss] {p}")
            continue
        s, _ = load_scan(fp)
        for lam, per_seed in s.items():
            scans.setdefault(lam, {}).update(per_seed)
    return {"dataset": dataset, "backbone": backbone, "scans": scans}


def summarise(cfg):
    scans = cfg["scans"]
    rows = []
    base_tau, base_sig = None, None
    if 0.0 in scans:
        t = [r["tau_lodo"] for r in scans[0.0].values()]
        s = [r["sigma_null"] for r in scans[0.0].values()]
        base_tau, base_sig = float(np.mean(t)), float(np.mean(s))
    for lam in sorted(scans):
        per = scans[lam]
        ldi = [r["ldi"] for r in per.values()]
        tau = [r["tau_lodo"] for r in per.values()]
        sig = [r["sigma_null"] for r in per.values()]
        tin = [r["tau_insample"] for r in per.values()]
        ratio = (np.mean(tau) / np.mean(sig)) if np.mean(sig) > 0 else float("nan")
        rows.append({
            "dataset": cfg["dataset"], "backbone": cfg["backbone"],
            "lam": lam, "n_seeds": len(per),
            "ldi_mean": float(np.mean(ldi)),
            "ldi_sd": float(np.std(ldi, ddof=1)) if len(ldi) > 1 else 0.0,
            "ldi_min": float(np.min(ldi)), "ldi_max": float(np.max(ldi)),
            "tau_lodo_mean": float(np.mean(tau)),
            "sigma_hat_mean": float(np.mean(sig)),
            "tau_in_mean": float(np.mean(tin)),
            "gap_mean": float(np.mean(tin) - np.mean(tau)),
            "tau_base_over_sigma": float(base_tau / base_sig) if (base_tau is not None and base_sig) else float("nan"),
            "ratio_at_lam": float(ratio),
            "retention": (float(np.mean(tau) / base_tau)
                          if base_tau not in (None, 0) else float("nan")),
            "predicted_dual_gate_empty": bool(
                (base_tau / base_sig) > PROP1_THRESHOLD) if base_tau is not None else None,
            "n_pass_ldi_gate": int(sum(1 for x in ldi if x < LDI_GATE)),
            # 双门（泄漏 + 保真），只统计 lambda > 0 的修复点：
            # lambda = 0 是未修复基线，不构成"被接受的修复"。
            "n_pass_dual": int(sum(
                1 for r in per.values()
                if r["ldi"] < LDI_GATE
                and base_tau is not None
                and r["tau_lodo"] >= FIDELITY_KEEP * base_tau
            )) if lam > 0 else 0,
            "is_dosed": bool(lam > 0),
        })
    return rows


def main():
    configs = [
        # ---- group A: signal 2.5 / batch 0.3 / shared ----
        collect("A", "GAT (graph attention)", [
            "expA_A_baseline.json", "expA_A_mrp.json",
            "_time_gat.json", "bb_A_gat_base.json", "bb_A_gat_dose.json"]),
        collect("A", "MLP (no message passing)", ["bb_A_mlp.json"]),
        # ---- group C: signal 1.2 / batch 0.5 / spurious ----
        collect("C", "GAT (graph attention)", [
            "expA_C_baseline.json", "expA_C_mrp.json"]),
        collect("C", "MLP (no message passing)", ["bb_C_mlp.json"]),
    ]

    rows = []
    for cfg in configs:
        rows += summarise(cfg)

    payload = {
        "protocol": {
            "question": "does the verdict depend on the encoder backbone?",
            "backbones": {
                "GAT": "two-layer graph attention over the unit-level kNN graph (k=6)",
                "MLP": "two-layer perceptron, no message passing; identical decoder, "
                       "adversary, GRL schedule, dose grid and audit instrument",
            },
            "data": {
                "A": "sim_st/group_A_expA: 32 donors, 800 spots each, 3000 genes, "
                     "signal 2.5, batch 0.3, shared mode",
                "C": "sim_st/group_C_expA: 32 donors, 800 spots each, 3000 genes, "
                     "signal 1.2, batch 0.5, spurious mode",
            },
            "prop1_threshold": PROP1_THRESHOLD,
            "ldi_gate": 1.645, "epochs": 150, "hid": 256, "warmup": 50,
            "clip": 1.0, "adv_sn": True,
        },
        "rows": rows,
    }
    (RES / "backbone_ablation.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    with open(RES / "backbone_ablation.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"{'data':5} {'backbone':26} {'lam':>5} {'n':>2} "
          f"{'LDI':>7} {'sd':>5} {'tau_LDO':>8} {'sigma':>6} "
          f"{'tau/sig':>8} {'ret':>6} {'pred_empty':>10} {'pass':>5}")
    for r in rows:
        print(f"{r['dataset']:5} {r['backbone']:26} {r['lam']:>5} {r['n_seeds']:>2} "
              f"{r['ldi_mean']:>7.2f} {r['ldi_sd']:>5.2f} {r['tau_lodo_mean']:>8.4f} "
              f"{r['sigma_hat_mean']:>6.3f} {r['ratio_at_lam']:>8.2f} "
              f"{r['retention']:>6.3f} "
              f"{str(r['predicted_dual_gate_empty']):>10} {r['n_pass_ldi_gate']:>5}")

    print("\n=== backbone contrast (group A, lambda=0 baseline) ===")
    for r in rows:
        if r["dataset"] == "A" and r["lam"] == 0.0:
            print(f"  {r['backbone']:26} tau_base/sigma_hat={r['ratio_at_lam']:.2f} "
                  f"LDI={r['ldi_mean']:.2f}  (threshold {PROP1_THRESHOLD})")


if __name__ == "__main__":
    main()
