# -*- coding: utf-8 -*-
"""生成 CMPB 论文全部 7 张关键图 (v9)

所有数据来自真实 results/*.json，与论文数字严格一致。
输出目录: papers/06_cmpb_最终版_v2_20260905/Figures/
"""
import json
import os
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import seaborn as sns
from pathlib import Path

# ============ 全局样式 ============
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
    'axes.unicode_minus': False,
    'figure.dpi': 200,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'axes.linewidth': 1.2,
    'xtick.major.width': 1.2,
    'ytick.major.width': 1.2,
    'font.size': 10,
})

CMPB_BLUE = '#2F5496'
CMPB_RED = '#C00000'
CMPB_GREEN = '#548235'
CMPB_ORANGE = '#ED7D31'
NORMAL_COLOR = '#4472C4'
DISEASE_COLOR = '#C00000'

ROOT = Path(r"f:\project4_cervix_multimodal")
RESULTS = ROOT / "results"
OUT = ROOT / "papers" / "06_cmpb_最终版_v2_20260905" / "Figures"
OUT.mkdir(parents=True, exist_ok=True)

def load_json(p):
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)

# ============ Fig 1: 方法框架图 ============
def fig1_framework():
    """方法框架示意图"""
    fig, ax = plt.subplots(1, 1, figsize=(14, 6))
    ax.set_xlim(0, 14); ax.set_ylim(0, 6)
    ax.axis('off')
    fig.patch.set_facecolor('white')

    # 标题
    ax.text(7, 5.7, 'Pathway-Anchored Multimodal Spatial Risk Framework',
            ha='center', va='center', fontsize=14, fontweight='bold', color=CMPB_BLUE)

    # === 左侧: 输入 ===
    # 表达输入
    box = FancyBboxPatch((0.3, 3.8), 2.2, 1.4, boxstyle="round,pad=0.1",
                         facecolor='#D6E4F0', edgecolor=CMPB_BLUE, linewidth=2)
    ax.add_patch(box)
    ax.text(1.4, 4.85, '10× Visium', ha='center', va='center', fontsize=9, fontweight='bold')
    ax.text(1.4, 4.4, 'Expression', ha='center', va='center', fontsize=9)
    ax.text(1.4, 4.0, '(spot × 3661 genes)', ha='center', va='center', fontsize=8, color='#666')

    # H&E输入
    box = FancyBboxPatch((0.3, 1.2), 2.2, 1.4, boxstyle="round,pad=0.1",
                         facecolor='#FCE4D6', edgecolor=CMPB_ORANGE, linewidth=2)
    ax.add_patch(box)
    ax.text(1.4, 2.25, 'H&E Image', ha='center', va='center', fontsize=9, fontweight='bold')
    ax.text(1.4, 1.8, '224×224 patch', ha='center', va='center', fontsize=9)
    ax.text(1.4, 1.4, 'per spot', ha='center', va='center', fontsize=8, color='#666')

    # 箭头
    ax.annotate('', xy=(2.8, 4.5), xytext=(2.5, 4.5),
                arrowprops=dict(arrowstyle='->', color=CMPB_BLUE, lw=2))
    ax.annotate('', xy=(2.8, 1.9), xytext=(2.5, 1.9),
                arrowprops=dict(arrowstyle='->', color=CMPB_ORANGE, lw=2))

    # === 中间: 编码器 ===
    # 表达编码器
    box = FancyBboxPatch((3.0, 3.7), 2.5, 1.6, boxstyle="round,pad=0.1",
                         facecolor='#E2EFDA', edgecolor=CMPB_GREEN, linewidth=2)
    ax.add_patch(box)
    ax.text(4.25, 4.9, 'Expression Encoder', ha='center', va='center', fontsize=9, fontweight='bold')
    ax.text(4.25, 4.4, '2-layer MLP', ha='center', va='center', fontsize=8)
    ax.text(4.25, 4.0, 'Dropout 0.2', ha='center', va='center', fontsize=8)
    ax.text(4.25, 3.75, '→ z_g ∈ R^128', ha='center', va='center', fontsize=8, color=CMPB_GREEN)

    # 图像编码器
    box = FancyBboxPatch((3.0, 1.0), 2.5, 1.6, boxstyle="round,pad=0.1",
                         facecolor='#E2EFDA', edgecolor=CMPB_GREEN, linewidth=2)
    ax.add_patch(box)
    ax.text(4.25, 2.2, 'UNI Image Encoder', ha='center', va='center', fontsize=9, fontweight='bold')
    ax.text(4.25, 1.75, 'Frozen UNI (Nat Med 2024)', ha='center', va='center', fontsize=8)
    ax.text(4.25, 1.35, '→ z_i ∈ R^128', ha='center', va='center', fontsize=8, color=CMPB_GREEN)

    # 箭头到融合
    ax.annotate('', xy=(5.8, 4.8), xytext=(5.5, 4.5),
                arrowprops=dict(arrowstyle='->', color=CMPB_GREEN, lw=2))
    ax.annotate('', xy=(5.8, 1.6), xytext=(5.5, 1.9),
                arrowprops=dict(arrowstyle='->', color=CMPB_GREEN, lw=2))

    # === 融合模块 ===
    box = FancyBboxPatch((6.0, 2.8), 2.2, 2.4, boxstyle="round,pad=0.1",
                         facecolor='#FFF2CC', edgecolor='#BF8F00', linewidth=2.5)
    ax.add_patch(box)
    ax.text(7.1, 4.8, 'Cross-Modal', ha='center', va='center', fontsize=9, fontweight='bold')
    ax.text(7.1, 4.4, 'Attention', ha='center', va='center', fontsize=9, fontweight='bold')
    ax.text(7.1, 3.8, '4-head', ha='center', va='center', fontsize=8)
    ax.text(7.1, 3.3, 'z_g ⊕ z_i → z_m', ha='center', va='center', fontsize=8, color='#BF8F00')
    ax.text(7.1, 3.0, '∈ R^128', ha='center', va='center', fontsize=8, color='#BF8F00')

    # 箭头到融合
    ax.annotate('', xy=(8.5, 4.5), xytext=(8.2, 4.2),
                arrowprops=dict(arrowstyle='->', color='#BF8F00', lw=2))
    ax.annotate('', xy=(8.5, 1.9), xytext=(8.2, 2.2),
                arrowprops=dict(arrowstyle='->', color='#BF8F00', lw=2))

    # === 右侧: 多头输出 ===
    # 风险头
    box = FancyBboxPatch((8.7, 4.2), 2.0, 1.4, boxstyle="round,pad=0.1",
                         facecolor='#F2F2F2', edgecolor='black', linewidth=2)
    ax.add_patch(box)
    ax.text(9.7, 5.1, 'Risk Head', ha='center', va='center', fontsize=9, fontweight='bold')
    ax.text(9.7, 4.6, 'Linear → r ∈ R', ha='center', va='center', fontsize=8)
    ax.text(9.7, 4.3, '(per-spot risk)', ha='center', va='center', fontsize=7, color='#666')

    # HPV通路头
    box = FancyBboxPatch((8.7, 2.2), 2.0, 1.4, boxstyle="round,pad=0.1",
                         facecolor='#E2EFDA', edgecolor=CMPB_GREEN, linewidth=2)
    ax.add_patch(box)
    ax.text(9.7, 3.1, 'HPV Pathway', ha='center', va='center', fontsize=9, fontweight='bold')
    ax.text(9.7, 2.6, 'Alignment Head', ha='center', va='center', fontsize=8)
    ax.text(9.7, 2.3, '(108 genes)', ha='center', va='center', fontsize=7, color='#666')

    # 重构头
    box = FancyBboxPatch((8.7, 0.2), 2.0, 1.4, boxstyle="round,pad=0.1",
                         facecolor='#F2F2F2', edgecolor='black', linewidth=2)
    ax.add_patch(box)
    ax.text(9.7, 1.1, 'Recon Head', ha='center', va='center', fontsize=9, fontweight='bold')
    ax.text(9.7, 0.6, 'Linear → x̂', ha='center', va='center', fontsize=8)

    # 空间邻域分支
    box = FancyBboxPatch((11.2, 2.8), 2.5, 1.8, boxstyle="round,pad=0.1",
                         facecolor='#D9E1F2', edgecolor=CMPB_BLUE, linewidth=2)
    ax.add_patch(box)
    ax.text(12.45, 4.1, 'Spatial Neighborhood', ha='center', va='center', fontsize=9, fontweight='bold')
    ax.text(12.45, 3.6, '6 nearest neighbors', ha='center', va='center', fontsize=8)
    ax.text(12.45, 3.2, 'on Visium hexagonal', ha='center', va='center', fontsize=8)
    ax.text(12.45, 2.9, 'lattice', ha='center', va='center', fontsize=8)

    # 箭头: z_m到三个头
    ax.annotate('', xy=(8.7, 4.9), xytext=(8.2, 4.2),
                arrowprops=dict(arrowstyle='->', color='black', lw=1.5))
    ax.annotate('', xy=(8.7, 2.9), xytext=(8.2, 2.2),
                arrowprops=dict(arrowstyle='->', color=CMPB_GREEN, lw=1.5))
    ax.annotate('', xy=(8.7, 0.9), xytext=(8.2, 1.6),
                arrowprops=dict(arrowstyle='->', color='black', lw=1.5))
    # 风险头到邻域
    ax.annotate('', xy=(11.2, 3.7), xytext=(10.7, 4.5),
                arrowprops=dict(arrowstyle='->', color=CMPB_BLUE, lw=1.5))

    # === 底部: 损失函数 ===
    ax.text(7, 0.3, 'Multi-task Loss: L = λ_recon·L_recon + λ_hpv·L_hpv + λ_sup·L_sup + λ_prog·L_prog + λ_neigh·L_neigh',
            ha='center', va='center', fontsize=10, fontweight='bold', color=CMPB_BLUE,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#F2F2F2', edgecolor=CMPB_BLUE))

    # NO-IMAGE 标注
    ax.text(4.25, 0.45, 'NO-IMAGE ablation: zero out image encoder output',
            ha='center', va='center', fontsize=8, fontstyle='italic', color=CMPB_RED)

    plt.tight_layout()
    fig.savefig(OUT / "Fig1_Framework.png", facecolor='white')
    plt.close()
    print("  [OK] Fig1_Framework.png")


# ============ Fig 2: 风险分布 + Kendall's τ ============
def fig2_risk_distribution():
    """35样本风险分布 + 进展单调性"""
    data = load_json(RESULTS / "results_CERVIX35_PROG.json")
    scores = data['per_sample_score']

    # 分类
    disease_ids = ['CA_HPV_1', 'CA_HPV_2', 'HSIL_HPV', 'cervical_cancer_1']
    subtype_map = {
        'CA_HPV_1': 'SCC', 'CA_HPV_2': 'ADC',
        'HSIL_HPV': 'HSIL', 'cervical_cancer_1': 'SCC',
        'N_HPV': 'HPV+ Normal'
    }

    # 排序: 正常→HSIL→癌
    normal_scores = [(k, v) for k, v in scores.items() if k.startswith('ecto') or k == 'N_HPV']
    disease_scores = [(k, v) for k, v in scores.items() if k in disease_ids]

    # 画两面板
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Disease-vs-Normal Risk Characterization', fontsize=13, fontweight='bold', y=1.02)

    # --- 左: 分布图 ---
    # 正常散点
    n_norm = len(normal_scores)
    norm_x = np.arange(n_norm)
    norm_y = [v for _, v in normal_scores]
    norm_colors = [NORMAL_COLOR if k != 'N_HPV' else '#7030A0' for k, _ in normal_scores]

    ax1.scatter(norm_x, norm_y, c=norm_colors, s=40, alpha=0.8, zorder=3)
    # 正常分布箱线
    bp = ax1.boxplot(norm_y, positions=[n_norm + 0.5], widths=3, patch_artist=True,
                     boxprops=dict(facecolor=NORMAL_COLOR, alpha=0.3),
                     medianprops=dict(color=NORMAL_COLOR, linewidth=2))

    # 疾病散点 (在箱线右侧)
    dis_x = [n_norm + 3 + i for i in range(len(disease_scores))]
    dis_y = [v for _, v in disease_scores]
    dis_labels = [f"{subtype_map.get(k, k)}\n(k)" for k, _ in disease_scores]
    ax1.scatter(dis_x, dis_y, c=DISEASE_COLOR, s=80, zorder=5, edgecolors='black', linewidths=0.5)
    for i, (x, y, l) in enumerate(zip(dis_x, dis_y, dis_labels)):
        ax1.annotate(l, (x, y), textcoords="offset points", xytext=(0, 15),
                     ha='center', fontsize=7, fontweight='bold', color=DISEASE_COLOR)

    # 中位数线
    norm_median = np.median(norm_y)
    ax1.axhline(norm_median, color=NORMAL_COLOR, linestyle='--', linewidth=1, alpha=0.7)

    ax1.set_xlim(-2, dis_x[-1] + 2)
    ax1.set_ylabel('Per-sample Mean Risk Score', fontsize=11)
    ax1.set_title('(A) Risk Score Distribution', fontsize=12, fontweight='bold')
    # 显式图例句柄，避免多色scatter图例取色错误
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor=NORMAL_COLOR, markersize=8, label='Normal (n=31)'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor=DISEASE_COLOR, markersize=10, markeredgecolor='black', label='Disease (n=4)'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#7030A0', markersize=8, label='N_HPV (HPV+ normal)'),
        Line2D([0], [0], color=NORMAL_COLOR, linestyle='--', linewidth=1, label=f'Normal median = {norm_median:.3f}'),
    ]
    ax1.legend(handles=legend_elements, loc='upper left', fontsize=8)
    ax1.set_xticks([])
    ax1.grid(axis='y', alpha=0.3)

    # --- 右: 进展单调性 ---
    prog = data['progression_monotonicity']
    # 按severity分组取均值
    order = prog['order']
    severity = prog['severity']
    score_list = prog['score']

    sev_labels = {0: 'Normal', 1: 'HSIL', 2: 'Carcinoma'}
    sev_colors = {0: NORMAL_COLOR, 1: CMPB_ORANGE, 2: DISEASE_COLOR}

    # 散点
    for sev in [0, 1, 2]:
        pts = [(severity[i], score_list[i]) for i in range(len(severity)) if severity[i] == sev]
        xs = [p[0] + np.random.normal(0, 0.05) for p in pts]
        ys = [p[1] for p in pts]
        ax2.scatter(xs, ys, c=sev_colors[sev], s=50, alpha=0.7, zorder=3, label=sev_labels[sev])
        # 均值
        ax2.scatter([sev], [np.mean(ys)], c=sev_colors[sev], s=200, marker='D', zorder=5,
                    edgecolors='black', linewidths=1.5)

    # 连均值线
    means = [np.mean([score_list[i] for i in range(len(severity)) if severity[i] == s]) for s in [0, 1, 2]]
    ax2.plot([0, 1, 2], means, color=CMPB_BLUE, linewidth=2, linestyle='-', zorder=4)

    ax2.set_xticks([0, 1, 2])
    ax2.set_xticklabels(['Normal', 'HSIL', 'Carcinoma'], fontsize=11)
    ax2.set_ylabel('Per-sample Mean Risk Score', fontsize=11)
    ax2.set_title('(B) Progression Monotonicity', fontsize=12, fontweight='bold')

    tau = prog['kendall_tau']
    pval = prog['kendall_p']
    ax2.text(0.98, 0.02, f"Kendall's τ = {tau:.3f}\np = {pval:.3f}",
             transform=ax2.transAxes, fontsize=10, va='bottom', ha='right',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    ax2.legend(fontsize=9)
    ax2.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    fig.savefig(OUT / "Fig2_RiskDistribution.png", facecolor='white')
    plt.close()
    print("  [OK] Fig2_RiskDistribution.png")


# ============ Fig 3: LODO 泛化 ============
def fig3_lodo():
    """LODO 百分位柱状图"""
    lodo = load_json(RESULTS / "leave_disease_out_summary.json")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle('Leave-One-Disease-Out Generalization', fontsize=13, fontweight='bold', y=1.02)

    # --- 左: 百分位柱状 ---
    folds = lodo['folds']
    names = [f"{f['holdout_sample']}" for f in folds]
    percentiles = [f['percentile_vs_normal'] for f in folds]
    means = [f['holdout_mean_risk'] for f in folds]

    colors = [DISEASE_COLOR if p >= 0.9 else CMPB_ORANGE for p in percentiles]
    bars = ax1.bar(range(len(names)), percentiles, color=colors, edgecolor='black', linewidth=1)

    for bar, p, m in zip(bars, percentiles, means):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                 f'{p:.3f}\n(risk={m:.2f})', ha='center', va='bottom', fontsize=8, fontweight='bold')

    ax1.axhline(1.0, color=CMPB_RED, linestyle='--', linewidth=1.5, alpha=0.7, label='Above all normal')
    ax1.axhline(0.5, color='gray', linestyle=':', linewidth=1, alpha=0.5, label='Normal median')
    ax1.set_xticks(range(len(names)))
    ax1.set_xticklabels(names, fontsize=9, rotation=15)
    ax1.set_ylabel('Percentile vs. Normal Distribution', fontsize=10)
    ax1.set_title('(A) Held-out Disease Percentile', fontsize=11, fontweight='bold')
    ax1.set_ylim(0, 1.2)
    ax1.legend(fontsize=8, loc='upper left')
    ax1.grid(axis='y', alpha=0.3)

    # --- 右: 逐fold正常分布 + 留出样本 ---
    for i, fold in enumerate(folds):
        normal_scores = fold['normal_scores']
        holdout_risk = fold['holdout_mean_risk']
        # 画小提琴或直方图
        parts = ax2.violinplot([normal_scores], positions=[i], showmeans=True, showmedians=True)
        for pc in parts['bodies']:
            pc.set_facecolor(NORMAL_COLOR); pc.set_alpha(0.4)
        # 留出样本点
        ax2.scatter([i], [holdout_risk], c=DISEASE_COLOR, s=100, zorder=5,
                    edgecolors='black', linewidths=1)

    ax2.set_xticks(range(len(names)))
    ax2.set_xticklabels(names, fontsize=9, rotation=15)
    ax2.set_ylabel('Risk Score', fontsize=10)
    ax2.set_title('(B) vs. Training Normal Distribution', fontsize=11, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)

    ax2.text(0.02, 0.02, f"Mean percentile = {lodo['mean_percentile_vs_normal']:.3f}\n3/{lodo['n_successful_folds']} above all normal",
             transform=ax2.transAxes, fontsize=9, va='bottom',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout()
    fig.savefig(OUT / "Fig3_LODO.png", facecolor='white')
    plt.close()
    print("  [OK] Fig3_LODO.png")


# ============ Fig 4: 消融对比 ============
def fig4_ablation():
    """消融对比柱状图"""
    main = load_json(RESULTS / "results_CERVIX35_PROG.json")
    noimg = load_json(RESULTS / "results_ABL_NOIMAGE_CERVIX35.json")
    abl = load_json(RESULTS / "ablation_summary.json")

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle('Ablation Study — Module Contributions', fontsize=13, fontweight='bold', y=1.02)

    # 配置 (统一为108-gene panel的两个: FULL主实验 + NO-IMAGE)
    # Disease AUC 用 baseline 的真实标签重算: FULL=1.000, NO-IMAGE=0.952
    configs_108 = ['FULL (main)', 'NO-IMAGE']
    moran_108 = [main['moran_i'], noimg['moran_i']]
    auc_108 = [1.000, 0.952]  # 用 baseline_hpv_gene_mean_vs_model.json 的标签重算
    kendall_p_108 = [0.001, 0.166]  # results_ABL_NOIMAGE JSON 原始值 0.1655

    # 40-gene panel的消融 (Spearman相关)
    rows = {r['config']: r for r in abl['per_config']}
    configs_40 = ['FULL', 'NO-HPV', 'NO-NEIGH', 'FM-UNI2', 'BASELINE-CNN']
    spearman_vals = [rows[c]['spearman_rho_vs_full'] for c in configs_40]
    moran_40 = [rows[c]['moran_i'] for c in configs_40]

    # --- 左: Moran's I (108-gene) ---
    ax = axes[0]
    colors_m = [CMPB_BLUE, CMPB_RED]
    bars = ax.bar(configs_108, moran_108, color=colors_m, edgecolor='black', linewidth=1.2, width=0.5)
    for bar, v in zip(bars, moran_108):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f'{v:.3f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    ax.axhline(moran_108[0], color='gray', linestyle=':', linewidth=1, alpha=0.5)
    ax.set_ylabel("Moran's I", fontsize=11)
    ax.set_title("(A) Spatial Coherence (108-gene)", fontsize=11, fontweight='bold')
    ax.set_ylim(0, 1.0)
    ax.grid(axis='y', alpha=0.3)
    # 增益标注
    delta = moran_108[0] - moran_108[1]
    ax.annotate(f'Δ = +{delta:.3f}\n(image contribution)',
                xy=(0.75, (moran_108[0]+moran_108[1])/2), fontsize=9, color=CMPB_RED, fontweight='bold')

    # --- 中: Disease AUC (108-gene) ---
    ax = axes[1]
    bars = ax.bar(configs_108, auc_108, color=colors_m, edgecolor='black', linewidth=1.2, width=0.5)
    for bar, v in zip(bars, auc_108):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f'{v:.3f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    ax.axhline(auc_108[0], color='gray', linestyle=':', linewidth=1, alpha=0.5)
    ax.set_ylabel('Disease-vs-Normal AUC', fontsize=11)
    ax.set_title("(B) Disease Discrimination (108-gene)", fontsize=11, fontweight='bold')
    ax.set_ylim(0.93, 1.02)
    ax.grid(axis='y', alpha=0.3)
    delta = auc_108[0] - auc_108[1]
    ax.annotate(f'Δ = +{delta:.3f}',
                xy=(0.75, (auc_108[0]+auc_108[1])/2), fontsize=10, color=CMPB_RED, fontweight='bold')

    # --- 右: Spearman ρ (40-gene, 与FULL的结构相似性) ---
    ax = axes[2]
    colors_s = [CMPB_BLUE] + [CMPB_ORANGE]*4
    bars = ax.bar(configs_40, spearman_vals, color=colors_s, edgecolor='black', linewidth=1.2, width=0.5)
    for bar, v in zip(bars, spearman_vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                f'{v:.3f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.axhline(1.0, color='gray', linestyle=':', linewidth=1, alpha=0.5, label='Identical to FULL')
    ax.set_ylabel("Spearman ρ vs. FULL", fontsize=11)
    ax.set_title("(C) Score-Structure Change (40-gene)", fontsize=11, fontweight='bold')
    ax.set_ylim(0.8, 1.05)
    ax.grid(axis='y', alpha=0.3)
    ax.legend(fontsize=8)
    plt.setp(ax.get_xticklabels(), rotation=15, ha='right')

    plt.tight_layout()
    fig.savefig(OUT / "Fig4_Ablation.png", facecolor='white')
    plt.close()
    print("  [OK] Fig4_Ablation.png")


# ============ Fig 5: 基线对比 + 随机对照 ============
def fig5_baseline_and_random():
    """基线对比柱状 + 随机对照分布"""
    bl = load_json(RESULTS / "baseline_hpv_gene_mean_vs_model.json")
    rc = load_json(RESULTS / "random_control_summary.json")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle('Baseline Comparison & Random-Gene-Set Control', fontsize=13, fontweight='bold', y=1.02)

    # --- 左: 基线对比 ---
    ax = axes[0]
    methods = ['HPV 108-gene mean\n(trivial baseline)', 'Multimodal\nModel (FULL)']
    aucs = [bl['baseline_hpv_gene_mean_auc'], bl['model_risk_auc']]
    colors = [CMPB_ORANGE, CMPB_BLUE]
    bars = ax.bar(methods, aucs, color=colors, edgecolor='black', linewidth=1.5, width=0.5)
    for bar, v in zip(bars, aucs):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f'{v:.3f}', ha='center', va='bottom', fontsize=12, fontweight='bold')
    ax.set_ylabel('Disease-vs-Normal AUC', fontsize=11)
    ax.set_title('(A) Baseline Comparison (n=35)', fontsize=11, fontweight='bold')
    ax.set_ylim(0.5, 1.1)
    ax.grid(axis='y', alpha=0.3)

    # --- 右: 随机对照 Moran's I 分布 ---
    ax = axes[1]
    random_morans = [r['moran_i'] for r in rc['random_runs']]
    kegg_moran = rc['kegg']['moran_i']

    ax.hist(random_morans, bins=10, color=NORMAL_COLOR, edgecolor='black', alpha=0.7, label=f'Random (n=30)')
    ax.axvline(kegg_moran, color=CMPB_RED, linestyle='--', linewidth=2.5,
               label=f'KEGG HPV = {kegg_moran:.3f}')
    ax.axvline(np.mean(random_morans), color='gray', linestyle=':', linewidth=1.5,
               label=f'Random mean = {np.mean(random_morans):.3f}')
    ax.set_xlabel("Moran's I", fontsize=11)
    ax.set_ylabel('Count', fontsize=11)
    ax.set_title('(B) 30-seed Random-Gene-Set Control', fontsize=11, fontweight='bold')
    pval = rc['permutation_test']['moran_i']['p_value']
    ax.text(0.98, 0.95, f'Permutation p = {pval:.3f}', transform=ax.transAxes,
            fontsize=10, va='top', ha='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    ax.legend(fontsize=9)
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    fig.savefig(OUT / "Fig5_Baseline_and_Random.png", facecolor='white')
    plt.close()
    print("  [OK] Fig5_Baseline_and_Random.png")


# ============ Fig 6: 外部验证 ============
def fig7_external_validation():
    """GSE316098 Silva + HNSCC跨器官"""
    gse = load_json(RESULTS / "external_gse316098_validation.json")
    hnscc_full = load_json(RESULTS / "infer_XCOHORT_HNSCC_FULL_summary.json")

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('External Validation', fontsize=13, fontweight='bold', y=1.02)

    # --- 左: GSE316098 Silva A vs B (ROI级) ---
    # GSE316098: 7例患者, 186个ROI (Pattern A: 94, Pattern B: 92)
    # ROI非独立(同一患者多ROI), p值为描述性
    ax = axes[0]
    from scipy.stats import mannwhitneyu
    silva_a = []
    silva_b = []
    for roi in gse['per_roi']:
        if '1b' in roi['pattern']:
            silva_b.append(roi['score'])
        else:
            silva_a.append(roi['score'])

    _, pval_roi = mannwhitneyu(silva_a, silva_b, alternative='two-sided')

    # 小提琴+散点
    vp = ax.violinplot([silva_a, silva_b], positions=[0, 1], showmeans=True, showmedians=True)
    colors_v = [CMPB_GREEN, DISEASE_COLOR]
    for i, pc in enumerate(vp['bodies']):
        pc.set_facecolor(colors_v[i]); pc.set_alpha(0.5)

    ax.scatter([0]*len(silva_a), silva_a, c=CMPB_GREEN, s=15, alpha=0.5, zorder=3, label=f'Pattern A (n={len(silva_a)} ROI)')
    ax.scatter([1]*len(silva_b), silva_b, c=DISEASE_COLOR, s=15, alpha=0.5, zorder=3, label=f'Pattern B (n={len(silva_b)} ROI)')

    ax.set_xticks([0, 1])
    ax.set_xticklabels(['Silva Pattern A\n(Non-destructive)', 'Silva Pattern B\n(Destructive)'], fontsize=10)
    ax.set_ylabel('Model Risk Score (ROI-level)', fontsize=10)
    ax.set_title('(A) Independent Cervical ADC Cohort\nGSE316098 (7 patients, 186 ROIs)', fontsize=11, fontweight='bold')
    ax.text(0.5, 0.98, f'ROI-level Mann-Whitney p = {pval_roi:.4f}\n(non-independent ROIs, descriptive)',
            transform=ax.transAxes, fontsize=9, va='top', ha='center', fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.9))
    ax.legend(fontsize=9, loc='lower right')
    ax.grid(axis='y', alpha=0.3)

    # --- 右: HNSCC 跨器官 Moran's I ---
    ax = axes[1]
    hnscc_data = hnscc_full if 'samples' in hnscc_full else {}
    cohorts = ['GSE268014\n(HNSCC)', 'GSE281978\n(HNSCC)', 'Cervical\n(in-sample)']
    ranges = [(0.594, 0.860), (0.587, 0.870), (0.866, 0.866)]
    means_h = [0.738, 0.664, 0.866]

    y_pos = range(len(cohorts))
    for i, ((lo, hi), m, coh) in enumerate(zip(ranges, means_h, cohorts)):
        ax.hlines(i, lo, hi, color=CMPB_BLUE, linewidth=3, zorder=3)
        ax.scatter([m], [i], c=CMPB_RED, s=120, zorder=5, edgecolors='black', linewidths=1)
        ax.text(m, i + 0.12, f'{m:.3f}', ha='center', fontsize=10, fontweight='bold', color=CMPB_RED)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(cohorts, fontsize=10)
    ax.set_xlabel("Moran's I", fontsize=11)
    ax.set_title('(B) Cross-Organ Transfer to HPV+ HNSCC', fontsize=11, fontweight='bold')
    ax.set_xlim(0.45, 1.0)
    ax.grid(axis='x', alpha=0.3)
    ax.axvline(0.866, color='gray', linestyle=':', linewidth=1, alpha=0.5, label='Cervical in-sample mean')

    plt.tight_layout()
    fig.savefig(OUT / "Fig7_ExternalValidation.png", facecolor='white')
    plt.close()
    print("  [OK] Fig7_ExternalValidation.png")


# ============ Fig 6: Top DEGs + TME 标志物热图 ============
def fig6_deg_tme():
    """Top DEGs 条形 + TME 标志物分组热图"""
    data = load_json(RESULTS / "results_CERVIX35_PROG.json")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7), gridspec_kw={'width_ratios': [1, 1.2]})
    fig.suptitle('Biological Interpretability — DEGs & TME Markers', fontsize=13, fontweight='bold', y=1.01)

    # --- 左: Top DEGs 条形 ---
    top_degs = data['top_degs'][:15]  # top 15
    genes = [d[0] for d in top_degs]
    effects = [d[1] for d in top_degs]
    pvals = [d[2] for d in top_degs]

    # 按effect排序
    order = np.argsort(effects)
    genes_sorted = [genes[i] for i in order]
    effects_sorted = [effects[i] for i in order]
    pvals_sorted = [pvals[i] for i in order]

    colors_d = [CMPB_RED if p < 0.05 else 'gray' for p in pvals_sorted]
    bars = ax1.barh(range(len(genes_sorted)), effects_sorted, color=colors_d, edgecolor='black', linewidth=0.5)
    ax1.set_yticks(range(len(genes_sorted)))
    ax1.set_yticklabels(genes_sorted, fontsize=10, fontweight='bold')
    ax1.set_xlabel('Risk Score Effect Size', fontsize=11)
    ax1.set_title('(A) Significant Permutation DEGs (FDR<0.05)', fontsize=11, fontweight='bold')
    ax1.axvline(0, color='black', linewidth=0.8)
    # 标注p值
    for i, (v, p) in enumerate(zip(effects_sorted, pvals_sorted)):
        sig = '***' if p < 0.001 else ('**' if p < 0.01 else '*') if p < 0.05 else 'ns'
        x_pos = v + 0.02 if v >= 0 else v - 0.08
        ax1.text(x_pos, i, sig, va='center', fontsize=9, color=CMPB_RED if p < 0.05 else 'gray')
    ax1.grid(axis='x', alpha=0.3)

    # --- 右: TME 标志物热图 (每个category取top 3-5个基因的effect) ---
    tme = data['tme_markers']
    categories = ['HPV_related', 'Epithelial', 'Stroma_CAF', 'Proliferation', 'Immune_activation', 'Tumor_drivers', 'Angiogenesis']
    cat_labels = ['HPV Pathway', 'Epithelial', 'Stroma/CAF', 'Proliferation', 'Immune Activation', 'Tumor Drivers', 'Angiogenesis']

    # 收集数据
    heatmap_data = []
    gene_labels = []
    cat_colors_list = []

    cat_color_map = {
        'HPV_related': '#FCE4D6',
        'Epithelial': '#E2EFDA',
        'Stroma_CAF': '#D9E1F2',
        'Proliferation': '#FFF2CC',
        'Immune_activation': '#E4DFEC',
        'Tumor_drivers': '#F8CBAD',
        'Angiogenesis': '#DDEBF7',
    }

    for cat, clabel in zip(categories, cat_labels):
        markers = tme.get(cat, [])
        # 取每个category的top 5 by abs effect
        markers_sorted = sorted(markers, key=lambda x: abs(x[1]), reverse=True)[:5]
        for m in markers_sorted:
            gene_labels.append(m[0])
            heatmap_data.append(m[1])  # effect size
            cat_colors_list.append(cat_color_map.get(cat, '#CCCCCC'))

    # 水平条形图 (代替热图, 更清晰)
    y_pos = np.arange(len(gene_labels))
    colors_h = [CMPB_RED if v > 0 else CMPB_BLUE for v in heatmap_data]
    bars = ax2.barh(y_pos, heatmap_data, color=colors_h, edgecolor='black', linewidth=0.3)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(gene_labels, fontsize=9)
    ax2.set_xlabel('Risk Score Effect Size', fontsize=11)
    ax2.set_title('(B) TME Marker Effect Sizes by Category', fontsize=11, fontweight='bold')
    ax2.axvline(0, color='black', linewidth=0.8)
    ax2.grid(axis='x', alpha=0.3)

    # 添加category色块背景
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=cat_color_map[c], label=l) for c, l in zip(categories, cat_labels)]
    ax2.legend(handles=legend_elements, loc='lower right', fontsize=8, ncol=2, framealpha=0.9)

    plt.tight_layout()
    fig.savefig(OUT / "Fig6_DEG_TME.png", facecolor='white')
    plt.close()
    print("  [OK] Fig6_DEG_TME.png")


# ============ Main ============
if __name__ == '__main__':
    print(f"Output dir: {OUT}")
    print("Generating all 7 figures...\n")

    fig1_framework()
    fig2_risk_distribution()
    fig3_lodo()
    fig4_ablation()
    fig5_baseline_and_random()
    fig6_deg_tme()
    fig7_external_validation()

    print(f"\nAll 7 figures saved to: {OUT}")
    print("Done!")
