# -*- coding: utf-8 -*-
"""核查 GSE316098 方向和所有相关数字"""
import json
from pathlib import Path
from collections import defaultdict
import numpy as np
from scipy.stats import mannwhitneyu

g = json.load(open(r"f:\project4_cervix_multimodal\results\external_gse316098_validation.json"))

# 正确解析: <SilvaPattern>.<patient>.<epi|stroma>
patient_scores = defaultdict(lambda: defaultdict(list))
for roi in g['per_roi']:
    parts = roi['roi'].split('.')
    pattern = parts[0]
    patient = parts[1]
    compartment = parts[2]
    patient_scores[pattern][patient].append(roi['score'])

pattern_a_means = [np.mean(patient_scores['1A'][p]) for p in patient_scores['1A']]
pattern_b_means = [np.mean(patient_scores['1b-1'][p]) for p in patient_scores['1b-1']]

print("=== GSE316098 Silva Pattern 患者级均值 ===")
print(f"Pattern 1A (n={len(pattern_a_means)}): mean={np.mean(pattern_a_means):.4f}")
print(f"Pattern 1b-1 (n={len(pattern_b_means)}): mean={np.mean(pattern_b_means):.4f}")
print(f"差值 (A - B): {np.mean(pattern_a_means) - np.mean(pattern_b_means):.4f}")
print()
print("⚠️  关键问题：")
print("  Silva 分级：1A = Pattern A（非破坏性，预后好）")
print("              1b-1 = Pattern B（破坏性，预后差）")
print(f"  模型打分：A={np.mean(pattern_a_means):.2f} > B={np.mean(pattern_b_means):.2f}")
print("  → 预后好的A反而风险分更高，方向与临床风险相反！")
print()

# 计算患者级和ROI级p值
u_p, p_p = mannwhitneyu(pattern_a_means, pattern_b_means, alternative='two-sided')
print(f"患者级 Mann-Whitney: U={u_p:.1f}, p={p_p:.4f}")

a_roi = [s for p in patient_scores['1A'] for s in patient_scores['1A'][p]]
b_roi = [s for p in patient_scores['1b-1'] for s in patient_scores['1b-1'][p]]
_, p_roi = mannwhitneyu(a_roi, b_roi, alternative='two-sided')
print(f"ROI级 Mann-Whitney: p={p_roi:.6f}")
print(f"JSON silva_p = {g['silva_p']:.6f}")
print()
print("=== 上皮 vs 间质（患者级聚合后）===")
# 每患者有1个epi和1个stroma ROI
epi_scores = []
stroma_scores = []
for pattern in patient_scores:
    for patient in patient_scores[pattern]:
        for roi in g['per_roi']:
            if roi['roi'].split('.')[1] == patient and roi['roi'].split('.')[0] == pattern:
                if roi['compartment'] == 'epi':
                    epi_scores.append(roi['score'])
                else:
                    stroma_scores.append(roi['score'])

print(f"上皮 ROI 数: {len(epi_scores)}, 均值: {np.mean(epi_scores):.4f}")
print(f"间质 ROI 数: {len(stroma_scores)}, 均值: {np.mean(stroma_scores):.4f}")
_, p_es = mannwhitneyu(epi_scores, stroma_scores, alternative='two-sided')
print(f"上皮 vs 间质 Mann-Whitney p: {p_es:.4f}")
