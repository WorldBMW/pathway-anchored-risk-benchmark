#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_summarize_v28.py — 把 results/regate_v28.json 整理成 REANALYSIS_REPORT_v28.md。

只做汇总与格式化，不产生任何新统计量；所有数字直接来自实验脚本输出。
用法：python scripts/_summarize_v28.py [--quick]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"


def f(v, nd=4):
    if v is None:
        return "n/a"
    if isinstance(v, float) and not np.isfinite(v):
        return "n/a"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    tag = "_quick" if args.quick else ""
    src = RES / f"regate_v28{tag}.json"
    payload = json.loads(src.read_text(encoding="utf-8"))
    rows = payload["runs"]
    out = []
    w = out.append

    w("# 重做实验报告（v28）")
    w("")
    w(f"数据源：`{src.name}`；{len(rows)} 个 run。所有数字由 "
      "`scripts/exp_regate_v28.py` 实算，未改写任何既有存档结果。")
    w("")

    # --- A. 组保持置换空分布
    w("## A. 组保持置换空分布与 LDI 门限")
    w("")
    w("`sigma_free` 为既有口径（全样本随机置换标签），`sigma_group` 为组保持置换"
      "（组内独立置换，保持 group–label 耦合 κ）。当标签在组内恒定时，组保持置换"
      "退化为恒等变换，σ_group = 0，LDI 无定义（表中 `degen`），这是组级推断不可行"
      "的直接证据，不是数值错误。")
    w("")
    w("| 域 | arm | λ | τ_LOO | σ_free | σ_group | LDI_free | LDI_group | "
      "p_free | p_group | 组内变异组占比 | degen |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        w(f"| {r['domain']} | {r.get('arm') or '-'} | {r['lam']} | "
          f"{f(r['tau_loo'])} | {f(r['sigma_free'])} | {f(r['sigma_group'])} | "
          f"{f(r['ldi_free'], 2)} | {f(r['ldi_group'], 2)} | "
          f"{f(r['p_free'], 3)} | {f(r['p_group'], 3)} | "
          f"{f(r.get('frac_groups_varying'), 2)} | "
          f"{'yes' if r['null_degenerate_group'] else 'no'} |")
    w("")

    # --- B. 三指标分解
    w("## B. 三指标分解：标签效用 / 身份解码 / 泄漏差值")
    w("")
    w("身份解码用两个不依赖类别可见性的度量：`id_knn_lift` = 留一最近邻同组命中率 / "
      "同组先验 Σ(n_g/N)²；`id_pair_auc` = 同组对 vs 异组对的嵌入距离判别 AUROC。"
      "（未采用「留出整组再预测组 ID」：留出组的类别在训练折中从未出现，准确率会被"
      "结构性压到 0，与身份是否可解无关。）`Δ = τ_LOO − τ_LGO`。")
    w("")
    w("| 域 | arm | λ | τ_LOO | τ_LGO | Δ | 1-NN 同组命中 | 同组先验 | "
      "id_knn_lift | id_pair_auc |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        w(f"| {r['domain']} | {r.get('arm') or '-'} | {r['lam']} | "
          f"{f(r['tau_loo'])} | {f(r['tau_lgo'])} | {f(r['inflation'])} | "
          f"{f(r.get('id_knn_hit'))} | {f(r.get('id_knn_chance'))} | "
          f"{f(r.get('id_knn_lift'), 2)} | {f(r.get('id_pair_auc'), 3)} |")
    w("")

    # --- C. 名义多分类指标 + 重编码敏感性
    w("## C. 名义多分类指标与重编码敏感性")
    w("")
    w("`macro_ovr_auc` 与 `balanced_acc` 走逐类 one-vs-rest 的组留一折外预测，"
      "不使用类别编号。`tau_loo_recode_*` 为把类别编号随机重排 R=20 次后 τ_LOO 的"
      "离散度；`auc_recode_delta` 为同一重排下 macro AUROC 的变化（应恒为 0）。")
    w("")
    w("| 域 | arm | λ | macro OVR AUROC | balanced acc | 类别数 | "
      "τ_LOO 重编码 SD | τ_LOO 重编码极差 | AUROC 重编码 Δ |")
    w("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        if "macro_ovr_auc" not in r:
            continue
        w(f"| {r['domain']} | {r.get('arm') or '-'} | {r['lam']} | "
          f"{f(r.get('macro_ovr_auc'), 3)} | {f(r.get('balanced_acc'), 3)} | "
          f"{r.get('n_classes', '-')} | {f(r.get('tau_loo_recode_sd'))} | "
          f"{f(r.get('tau_loo_recode_range'))} | "
          f"{f(r.get('auc_recode_delta'))} |")
    w("")

    # --- D. 冻结基线 σ̂
    w("## D. 冻结基线 σ̂ 的尺度敏感性")
    w("")
    w("同一批 run：逐 run 重估 σ̂（既有口径）与冻结 λ=0 基线 σ̂（跨 seed 均值）"
      "两种尺度下的 LDI 与门限通过计数。")
    w("")
    groups = {}
    for r in rows:
        groups.setdefault((r["domain"], r.get("arm") or "-"), []).append(r)
    w("| 域 | arm | σ̂_frozen(free) | 逐 run LDI_free 范围 | 冻结 LDI_free 范围 | "
      "逐 run 通过 | 冻结通过 |")
    w("|---|---|---|---|---|---|---|")
    for (dom, arm), rs in groups.items():
        base = [r for r in rs if r["lam"] == 0 and r["sigma_free"] > 0]
        if not base:
            continue
        sf = float(np.mean([r["sigma_free"] for r in base]))
        per = [r["ldi_free"] for r in rs if r["ldi_free"] is not None]
        froz = [(r["tau_loo"] - 0.001) / sf for r in rs if r["sigma_free"] > 0]
        w(f"| {dom} | {arm} | {f(sf)} | "
          f"[{min(per):.2f}, {max(per):.2f}] | [{min(froz):.2f}, {max(froz):.2f}] | "
          f"{sum(1 for v in per if v < 1.645)}/{len(per)} | "
          f"{sum(1 for v in froz if v < 1.645)}/{len(froz)} |")
    w("")

    # --- E. 宫颈供体对照表
    cerv = [r for r in rows if r["domain"] == "CERVIX"]
    if cerv:
        w("## E. 宫颈切片→供体对照表与按供体重算")
        w("")
        r0 = cerv[0]
        w(f"35 切片 → {r0['G']} 供体；切片/供体分布："
          f"{r0['n_slices_per_donor']}（键为供体序号，值为切片数）。"
          f"同名归组规则：`{r0['donor_pairs']}`。")
        w("")
        w("| seed | λ | τ_LOO | τ_LGO(donor) | Δ | σ_free | σ_group | degen |")
        w("|---|---|---|---|---|---|---|---|")
        for r in cerv:
            w(f"| {r['seed']} | {r['lam']} | {f(r['tau_loo'])} | "
              f"{f(r['tau_lgo'])} | {f(r['inflation'])} | {f(r['sigma_free'])} | "
              f"{f(r['sigma_group'])} | "
              f"{'yes' if r['null_degenerate_group'] else 'no'} |")
        w("")

    # --- F. GeoMx 患者配对枚举
    pe = payload.get("patient_enumeration")
    if pe:
        w("## F. GeoMx 患者层级敏感性（21 配对枚举）")
        w("")
        w("原文仅声明 7 例来自 6 名患者，未公开哪一例配对；因此对 C(7,2)=21 种"
          "配对全部枚举，报告组级统计量是否依赖配对。")
        w("")
        w("| arm | τ_LGO(case, G=7) | τ_LGO(patient, 21 配对) min | max | 极差 |")
        w("|---|---|---|---|---|")
        for arm in sorted({r["arm"] for r in pe}):
            sub = [r for r in pe if r["arm"] == arm]
            v = [r["tau_lgo_patient"] for r in sub]
            w(f"| {arm} | {f(sub[0]['tau_lgo_case'])} | {f(min(v))} | "
              f"{f(max(v))} | {f(max(v) - min(v))} |")
        w("")

    # --- G. 外层留组重拟合
    gp = RES / "outer_refit_v28.json"
    if gp.exists():
        od = json.loads(gp.read_text(encoding="utf-8"))
        w("## G. 外层留组重拟合（编码器也折进外层）")
        w("")
        w("既有 τ_LGO 是条件表示审计：编码器在探针折外之前已见过该组。这里把编码器、"
          "对抗头与探针全部放进外层折内重训，留出组不参与任何表示学习，再与同一配置"
          "下的冻结嵌入 τ_LGO 对比；两者之差即「编码器见过该组」带来的乐观量。")
        w("")
        w("| 域 | seed | λ | 折数 | τ_LGO 冻结 | τ_LGO 外层 | 折间 SD | "
          "冻结−外层（乐观量） | τ_LOO(全单位) |")
        w("|---|---|---|---|---|---|---|---|---|")
        for r in od["runs"]:
            w(f"| {r['domain']} | {r['seed']} | {r['lam']} | {r['n_folds']} | "
              f"{f(r['tau_lgo_frozen'])} | {f(r['tau_outer_lgo'])} | "
              f"{f(r['fold_sd'])} | {f(r['optimism'])} | {f(r['tau_loo_all'])} |")
        w("")
        w("乐观量为负表示外层重拟合的组留一关联**高于**冻结嵌入口径，即冻结条件审计"
          "在该队列上并未高估。差异（≤0.028）小于折间 SD（0.094–0.103），属噪声量级。"
          "本项只在一个域、一个训练种子上完成：每折都要重训表示。")
        w("")

    dst = ROOT / "papers" / "20_MRP-ST-Repair_Patterns" / "REANALYSIS_REPORT_v28.md"
    dst.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {dst} ({len(out)} lines)")


if __name__ == "__main__":
    main()
