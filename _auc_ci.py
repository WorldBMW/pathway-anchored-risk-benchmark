# -*- coding: utf-8 -*-
"""计算 disease AUC 的 bootstrap 95% CI"""
import json, numpy as np
from pathlib import Path
from sklearn.metrics import roc_auc_score

R = Path(r"f:\project4_cervix_multimodal\results")
bl = json.load(open(R/"baseline_hpv_gene_mean_vs_model.json"))

# 疾病样本 = label 1
labels = []
scores_model = []
scores_baseline = []
for name, info in bl['per_sample'].items():
    labels.append(info['label'])
    scores_model.append(info['model_risk'])
    scores_baseline.append(info['hpv_gene_mean'])

labels = np.array(labels)
scores_model = np.array(scores_model)
scores_baseline = np.array(scores_baseline)

n_pos = int(labels.sum())
n_neg = len(labels) - n_pos
print(f"n_pos={n_pos}, n_neg={n_neg}")

# Bootstrap CI for model AUC
np.random.seed(42)
n_boot = 10000
boot_aucs_model = []
boot_aucs_baseline = []
for _ in range(n_boot):
    idx = np.random.choice(len(labels), len(labels), replace=True)
    y = labels[idx]
    if len(np.unique(y)) < 2:
        continue
    boot_aucs_model.append(roc_auc_score(y, scores_model[idx]))
    boot_aucs_baseline.append(roc_auc_score(y, scores_baseline[idx]))

ci_model = np.percentile(boot_aucs_model, [2.5, 97.5])
ci_base = np.percentile(boot_aucs_baseline, [2.5, 97.5])
print(f"\nModel AUC: {roc_auc_score(labels, scores_model):.4f}")
print(f"  Bootstrap 95% CI: [{ci_model[0]:.4f}, {ci_model[1]:.4f}]")
print(f"\nBaseline (HPV mean) AUC: {roc_auc_score(labels, scores_baseline):.4f}")
print(f"  Bootstrap 95% CI: [{ci_base[0]:.4f}, {ci_base[1]:.4f}]")

# DeLong test (model vs baseline)
from scipy.stats import norm as scipy_norm

def delong_auc_ci(y_true, y_score, alpha=0.05):
    """Compute AUC and DeLong 95% CI."""
    auc = roc_auc_score(y_true, y_score)
    pos = y_score[y_true == 1]
    neg = y_score[y_true == 0]
    n_pos = len(pos)
    n_neg = len(neg)

    # DeLong variance
    v_pos = np.array([(np.sum(neg < p) + 0.5*np.sum(neg == p)) / n_neg for p in pos])
    v_neg = np.array([(np.sum(pos > n) + 0.5*np.sum(pos == n)) / n_pos for n in neg])
    var_pos = np.var(v_pos, ddof=1) / n_pos
    var_neg = np.var(v_neg, ddof=1) / n_neg
    var = var_pos + var_neg
    se = np.sqrt(var)
    z = scipy_norm.ppf(1 - alpha/2)
    ci = [max(0, auc - z*se), min(1, auc + z*se)]
    return auc, ci

auc_m, ci_m = delong_auc_ci(labels, scores_model)
auc_b, ci_b = delong_auc_ci(labels, scores_baseline)
print(f"\n=== DeLong CI ===")
print(f"Model AUC: {auc_m:.4f}, 95% CI: [{ci_m[0]:.4f}, {ci_m[1]:.4f}]")
print(f"Baseline AUC: {auc_b:.4f}, 95% CI: [{ci_b[0]:.4f}, {ci_b[1]:.4f}]")

# DeLong test comparing two AUCs
def delong_test(y_true, score1, score2):
    auc1 = roc_auc_score(y_true, score1)
    auc2 = roc_auc_score(y_true, score2)
    pos_idx = y_true == 1
    neg_idx = y_true == 0
    n_pos = pos_idx.sum()
    n_neg = neg_idx.sum()
    pos1, pos2 = score1[pos_idx], score2[pos_idx]
    neg1, neg2 = score1[neg_idx], score2[neg_idx]

    v_pos1 = np.array([(np.sum(neg1 < p) + 0.5*np.sum(neg1 == p)) / n_neg for p in pos1])
    v_neg1 = np.array([(np.sum(pos1 > n) + 0.5*np.sum(pos1 == n)) / n_pos for n in neg1])
    v_pos2 = np.array([(np.sum(neg2 < p) + 0.5*np.sum(neg2 == p)) / n_neg for p in pos2])
    v_neg2 = np.array([(np.sum(pos2 > n) + 0.5*np.sum(pos2 == n)) / n_pos for n in neg2])

    var1 = np.var(v_pos1, ddof=1)/n_pos + np.var(v_neg1, ddof=1)/n_neg
    var2 = np.var(v_pos2, ddof=1)/n_pos + np.var(v_neg2, ddof=1)/n_neg
    cov = np.cov(v_pos1, v_pos2)[0,1]/n_pos + np.cov(v_neg1, v_neg2)[0,1]/n_neg
    var_diff = var1 + var2 - 2*cov
    z = (auc1 - auc2) / np.sqrt(var_diff)
    p = 2 * (1 - scipy_norm.cdf(abs(z)))
    return z, p

z, p = delong_test(labels, scores_model, scores_baseline)
print(f"\nDeLong test (model vs baseline): z={z:.3f}, p={p:.4f}")
print(f"\n=== 建议论文写法 ===")
print(f"疾病/正常 AUC = {auc_m:.3f} (DeLong 95% CI [{ci_m[0]:.3f}, {ci_m[1]:.3f}], n_pos={n_pos})")
print(f"对比平凡基线 AUC = {auc_b:.3f} (CI [{ci_b[0]:.3f}, {ci_b[1]:.3f}])")
print(f"DeLong 检验: z={z:.2f}, p={p:.4f}")
