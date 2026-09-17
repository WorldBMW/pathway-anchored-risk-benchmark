import json, os, numpy as np
from sklearn.metrics import roc_auc_score

BASE = r'f:\project4_cervix_multimodal\results'
main = json.load(open(os.path.join(BASE, 'results_CERVIX35_PROG.json')))
noimg = json.load(open(os.path.join(BASE, 'results_ABL_NOIMAGE_CERVIX35.json')))

disease = {'cervical_cancer_1','CA_HPV_1','CA_HPV_2','HSIL_HPV'}

def compute_auc(d):
    scores = d['per_sample_score']
    order = list(scores.keys())
    y = [1 if any(k in s for k in disease) else 0 for s in order]
    vals = [scores[k] for k in order]
    return roc_auc_score(y, vals) if len(set(y)) > 1 else None

def find_key(d, needle):
    for k in d:
        if needle in k: return k
    return None

print('=' * 60)
print('NO-IMAGE ABLATION vs FULL MODEL')
print('=' * 60)

# --- Moran's I ---
m_m = main.get('moran_i', main.get('spatial', {}).get('moran_i', 'NA'))
m_n = noimg.get('moran_i', noimg.get('spatial', {}).get('moran_i', 'NA'))
print(f"\nMoran's I:   MAIN={m_m}  NO-IMG={m_n}  diff={float(m_m)-float(m_n):+.4f}" if m_m != 'NA' else 'Moran NA')

# --- Kendall tau ---
kt_m = main.get('progression_monotonicity', {}).get('kendall_tau', 'NA')
kt_n = noimg.get('progression_monotonicity', {}).get('kendall_tau', 'NA')
kp_m = main.get('progression_monotonicity', {}).get('permutation_p', 'NA')
kp_n = noimg.get('progression_monotonicity', {}).get('permutation_p', 'NA')
print(f'\nKendall tau: MAIN={kt_m} (p={kp_m})  NO-IMG={kt_n} (p={kp_n})')

# --- AUC ---
auc_m = compute_auc(main)
auc_n = compute_auc(noimg)
print(f'\nDisease-vs-Normal AUC: MAIN={auc_m:.3f}  NO-IMG={auc_n:.3f}')

# --- DEGs ---
deg_m = main.get('n_deg_perm_fdr05_effect', 'NA')
deg_n = noimg.get('n_deg_perm_fdr05_effect', 'NA')
print(f'\nPermutation DEG (FDR05): MAIN={deg_m}  NO-IMG={deg_n}')

# --- Top DEGs ---
print(f'\nTop 6 DEGs MAIN:  {[g[0] for g in main.get("top_degs", [])[:6]]}')
print(f'Top 6 DEGs NOIMG: {[g[0] for g in noimg.get("top_degs", [])[:6]]}')

# --- Sample scores ---
print('\n--- 样本均值风险对比 ---')
print(f'{"样本":22s} {"主实验":>10s} {"NO-IMG":>10s}')
cervix_keys = [k for k in main['per_sample_score'] if 'LI_SING' not in k]
m_cervix = {k: main['per_sample_score'][k] for k in cervix_keys}
n_cervix = {k: noimg['per_sample_score'][find_key(noimg['per_sample_score'], os.path.basename(k))] for k in cervix_keys}

for tag in ['HSIL_HPV','CA_HPV_1','CA_HPV_2','cervical_cancer_1','N_HPV']:
    mk = find_key(m_cervix, tag)
    nk_cand = [k for k in noimg['per_sample_score'].keys() if tag in k]
    if mk and nk_cand:
        print(f'{os.path.basename(mk):22s} {m_cervix[mk]:10.3f} {noimg["per_sample_score"][nk_cand[0]]:10.3f}')

# Normal ranges (cervix only)
m_norm_vals = [v for k, v in m_cervix.items() if not any(d in k for d in disease)]
n_norm_keys = [k for k in noimg['per_sample_score'].keys() if 'LI_SING' not in k and not any(d in k for d in disease)]
n_norm_vals = [noimg['per_sample_score'][k] for k in n_norm_keys]

print(f'\n正常样本（仅宫颈）:')
print(f'  MAIN:  [{min(m_norm_vals):.3f}, {max(m_norm_vals):.3f}]  mean={np.mean(m_norm_vals):.3f}  std={np.std(m_norm_vals):.3f}')
print(f'  NOIMG: [{min(n_norm_vals):.3f}, {max(n_norm_vals):.3f}]  mean={np.mean(n_norm_vals):.3f}  std={np.std(n_norm_vals):.3f}')

# Percentile of each disease in normal range
print('\n--- 疾病样本在正常分布中的百分位 ---')
for tag in ['HSIL_HPV','CA_HPV_1','CA_HPV_2','cervical_cancer_1']:
    mk = find_key(m_cervix, tag)
    nk_cand = [k for k in noimg['per_sample_score'].keys() if tag in k]
    if mk and nk_cand:
        sv_m = m_cervix[mk]
        sv_n = noimg['per_sample_score'][nk_cand[0]]
        pct_m = sum(1 for x in m_norm_vals if x < sv_m) / len(m_norm_vals)
        pct_n = sum(1 for x in n_norm_vals if x < sv_n) / len(n_norm_vals)
        flag = '✓' if pct_n > 0.95 else ('△' if pct_n > 0.7 else '✗')
        print(f'  {tag:22s} MAIN={pct_m:.3f}  NO-IMG={pct_n:.3f} {flag}')
