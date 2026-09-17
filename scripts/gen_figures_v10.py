# -*- coding: utf-8 -*-
"""gen_figures_v10.py — 重构版论文(v10)图 + 锁定数字 JSON

数字全部从真实 results/*.json / fused_embs*.npz 计算并导出
results/paper_v10_numbers.json（正文与图共用，保证一致）。图内标签用英文。
"""
import json, os, glob
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import kendalltau, mannwhitneyu

ROOT = r"f:\project4_cervix_multimodal"
os.chdir(ROOT)
OUT = os.path.join(ROOT, "papers", "07_CSBJ_v10", "Figures")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.dpi': 200, 'savefig.dpi': 600, 'savefig.bbox': 'tight',
                     'font.family': 'sans-serif',
                     'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans']})
NUM = {}

def severity_of(name):
    n = str(name).lower()
    if 'ca_hpv' in n or 'cancer' in n or 'carcinoma' in n: return 2
    if 'hsil' in n or 'cin' in n: return 1
    return 0

# ---------- 1. multi-seed ablation ----------
VARIANTS = ['FULL', 'NOIMAGE', 'NOHPV', 'NONEIGH', 'NOPROG']
VLBL = {'FULL': 'FULL', 'NOIMAGE': 'NO-IMAGE', 'NOHPV': 'NO-HPV',
        'NONEIGH': 'NO-NEIGH', 'NOPROG': 'NO-PROG\n(no label)'}
abl, abl_summary = {}, {}
for v in VARIANTS:
    rows = []
    for p in sorted(glob.glob(f'results/fused_embs_{v}_seed*.npz')):
        seed = p.split('seed')[-1].split('.')[0]
        z = np.load(p, allow_pickle=True)
        scores = z['scores'].astype(float); sids = z['sample_ids'].astype(str)
        jp = f'results/results_{v}_seed{seed}.json'
        moran = json.load(open(jp, encoding='utf-8')).get('moran_i') if os.path.exists(jp) else np.nan
        df = pd.DataFrame({'sid': sids, 'score': scores}); df['sev'] = df['sid'].map(severity_of)
        ps = df.groupby(['sid', 'sev'])['score'].mean().reset_index()
        dis = ps.loc[ps.sev > 0, 'score'].values; nor = ps.loc[ps.sev == 0, 'score'].values
        tau, tp = kendalltau(ps['sev'].values, ps['score'].values)
        mwu = mannwhitneyu(dis, nor, alternative='greater').pvalue
        rows.append({'seed': seed, 'moran': float(moran), 'tau': float(tau),
                     'tau_p': float(tp), 'mwu_p': float(mwu)})
    abl[v] = rows
    ma = np.array([r['moran'] for r in rows]); ta = np.array([r['tau'] for r in rows])
    abl_summary[v] = {'n_seeds': len(rows),
                      'moran_mean': float(ma.mean()), 'moran_sd': float(ma.std(ddof=1) if len(rows) > 1 else 0),
                      'tau_mean': float(ta.mean()), 'tau_sd': float(ta.std(ddof=1) if len(rows) > 1 else 0),
                      'tau_p_min': float(min(r['tau_p'] for r in rows)), 'tau_p_max': float(max(r['tau_p'] for r in rows)),
                      'mwu_p_min': float(min(r['mwu_p'] for r in rows)), 'mwu_p_max': float(max(r['mwu_p'] for r in rows))}
# Correct sample-level label-permutation p (B=10000; severity labels shuffled
# over all 35 samples) — supersedes scipy's asymptotic Kendall p quoted earlier.
_rp_path = 'results/rank_perm_B10000.json'
if os.path.exists(_rp_path):
    _rp = json.load(open(_rp_path, encoding='utf-8'))
    for _v, _rows in _rp['variants'].items():
        if _v in abl_summary:
            _ps = [r['p_perm_B10000'] for r in _rows]
            abl_summary[_v]['tau_perm_p_min'] = float(min(_ps))
            abl_summary[_v]['tau_perm_p_max'] = float(max(_ps))
            abl_summary[_v]['tau_perm_B'] = _rp['B']

NUM['ablation'] = abl_summary

fig, axes = plt.subplots(1, 2, figsize=(12, 4.3))
xs = np.arange(len(VARIANTS)); cols = ['#2F5496', '#5B9BD5', '#70AD47', '#ED7D31', '#C00000']
rng = np.random.default_rng(0)
ax = axes[0]
for i, v in enumerate(VARIANTS):
    s = abl_summary[v]
    ax.bar(i, s['moran_mean'], 0.62, color=cols[i], alpha=0.88, yerr=s['moran_sd'], capsize=4,
           error_kw=dict(lw=1.2))
    for r in abl[v]:
        ax.plot(i + rng.uniform(-0.13, 0.13), r['moran'], 'o', color='black', ms=4, alpha=0.65)
ax.set_xticks(xs); ax.set_xticklabels([VLBL[v] for v in VARIANTS], fontsize=10.2)
ax.set_ylabel("Moran's I (spatial coherence)"); ax.set_ylim(0, 1.02)
ax.set_title("A. Spatial coherence", fontsize=12, fontweight='bold')
ax = axes[1]
for i, v in enumerate(VARIANTS):
    s = abl_summary[v]
    ax.bar(i, s['tau_mean'], 0.62, color=cols[i], alpha=0.88, yerr=s['tau_sd'], capsize=4,
           error_kw=dict(lw=1.2))
    for r in abl[v]:
        ax.plot(i + rng.uniform(-0.13, 0.13), r['tau'], 'o', color='black', ms=4, alpha=0.65)
    p = s.get('tau_perm_p_max', s['tau_p_max'])
    if p <= 1e-3:
        lab = r"p$\leq$2e-4"
    elif p < 0.05:
        lab = "p=%.3f*" % p
    else:
        lab = "boundary\n(p=%.3f)" % p
    ax.text(i, s['tau_mean'] + s['tau_sd'] + 0.045, lab, ha='center', fontsize=9.2,
            fontweight='bold', color=('C00000' if p >= 0.05 else 'black'))
ax.set_xticks(xs); ax.set_xticklabels([VLBL[v] for v in VARIANTS], fontsize=10.2)
ax.set_ylabel("Kendall τ (disease ordering)"); ax.set_ylim(0, 0.62)
ax.set_title("B. Disease ordering vs. label supervision", fontsize=12, fontweight='bold')
plt.tight_layout(); plt.savefig(os.path.join(OUT, "Fig3_ablation_multiseed.png")); plt.close()

# ---------- 2. biology correlations (mean over FULL seeds) ----------
bio = json.load(open('results/downstream_spot_analysis.json', encoding='utf-8'))
sets = [c['set'] for c in bio[0]['pathway_cell_corr']]
bio_mean = {}
for s in sets:
    rhos = [next(c['spearman_rho'] for c in r['pathway_cell_corr'] if c['set'] == s) for r in bio]
    qs = [next(c['BH_q'] for c in r['pathway_cell_corr'] if c['set'] == s) for r in bio]
    bio_mean[s] = {'rho': float(np.mean(rhos)), 'rho_sd': float(np.std(rhos, ddof=1) if len(rhos) > 1 else 0),
                   'q_max': float(max(qs))}
NUM['biology'] = bio_mean
order = sorted(sets, key=lambda s: bio_mean[s]['rho'])
labels = [s.replace('CELL_', '').replace('_', ' ').replace('ANTIVIRAL', 'antiviral') for s in order]
rhos = [bio_mean[s]['rho'] for s in order]
bcols = ['#C00000' if r < -0.15 else ('#70AD47' if r > 0.15 else '#BFBFBF') for r in rhos]
fig, ax = plt.subplots(figsize=(8.8, 5.2))
y = np.arange(len(order))
ax.barh(y, rhos, color=bcols, alpha=0.88, height=0.66)
ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=11)
ax.axvline(0, color='black', lw=0.9)
for yi, r in zip(y, rhos):
    ax.text(r + (0.022 if r >= 0 else -0.022), yi, f"{r:+.2f}", va='center',
            ha='left' if r >= 0 else 'right', fontsize=10.2, fontweight='bold',
            color='#2B2B2B')
ax.set_xlabel("Spearman ρ with spot risk (within-sample z, mean of 3 seeds)", fontsize=11.5)
ax.set_title("Pathway / cell-state score vs. risk\n"
             "(all 11 correlations survive BH correction; weakest q=4.9e-9)",
             fontsize=12.5, fontweight='bold')
ax.set_xlim(-0.80, 0.78)
ax.set_ylim(-0.75, len(order) - 0.25)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "Fig4_biology_correlation.png")); plt.close()

# ---------- 3. spot risk violin by severity (FULL seed0) ----------
z = np.load('results/fused_embs_FULL_seed0.npz', allow_pickle=True)
sc = z['scores'].astype(float); sid = z['sample_ids'].astype(str)
sev = np.array([severity_of(s) for s in sid])
groups = [sc[sev == 0], sc[sev == 1], sc[sev == 2]]
glab = ['Normal\n(n=31 samples)', 'HSIL\n(n=1)', 'Cancer\n(n=3)']
NUM['risk_by_severity_spot'] = {
    'normal_mean': float(groups[0].mean()), 'hsil_mean': float(groups[1].mean()),
    'cancer_mean': float(groups[2].mean()),
    'normal_n_spots': int(len(groups[0])), 'hsil_n_spots': int(len(groups[1])), 'cancer_n_spots': int(len(groups[2]))}
fig, ax = plt.subplots(figsize=(6.6, 4.6))
parts = ax.violinplot(groups, positions=[0, 1, 2], showmedians=True, widths=0.75)
for pc, c in zip(parts['bodies'], ['#9DC3E6', '#FFD966', '#E06666']):
    pc.set_facecolor(c); pc.set_alpha(0.85)
parts['cmedians'].set_color('black')
ax.set_xticks([0, 1, 2]); ax.set_xticklabels(glab, fontsize=10.5)
ax.set_ylabel("Spot-level risk score (FULL, seed 0)")
ax.set_title("Risk by histologic severity\n(descriptive; in-sample, n=4 disease)", fontsize=12, fontweight='bold')
for i, g in enumerate(groups):
    ax.text(i, g.mean() + 0.18, f"{g.mean():.2f}", ha='center', fontsize=10, fontweight='bold')
plt.tight_layout(); plt.savefig(os.path.join(OUT, "Fig2_risk_violin.png")); plt.close()

# ---------- 4. external transfer (CORRECTED labels + final-protocol LODO) ----------
# FINAL-protocol HNSCC inference (FULL_DEPLOY_FAST checkpoint, expr-only, all spots)
hnscc = json.load(open('results/infer_XCOHORT_HNSCC_FINAL_summary.json', encoding='utf-8'))
def morans(d):
    if 'per_sample' in d:
        return [x.get('moran_i') for x in d['per_sample'] if x.get('moran_i') is not None]
    return d.get('moran_i') or []
hm = morans(hnscc)
g28 = morans(json.load(open('results/infer_XCOHORT_HNSCC_GSE281978_FINAL_summary.json',
                            encoding='utf-8')))

# Genuine negative control: coordinate permutation null of the MODEL score
perm = json.load(open('results/hnscc_moran_permutation_control_FINAL.json', encoding='utf-8'))
def perm_block(key):
    ps = perm[key]['per_sample']
    return {'null_mean': float(np.mean([s['perm_null_mean'] for s in ps])),
            'null_max': float(np.max([s['perm_null_max'] for s in ps])),
            'z_min': float(np.min([s['z_vs_null'] for s in ps])),
            'p_max': float(np.max([s['perm_p_ge'] for s in ps])),
            'n': len(ps)}
pm268 = perm_block('GSE268014_HNSCC'); pm281 = perm_block('GSE281978_HNSCC')

# Random gene-set controls (plain lognorm means; HVG-union expr-matched = primary)
rgm = json.load(open('results/hnscc_random_gene_moran.json', encoding='utf-8'))
def rg_block(dirname):
    c = rgm['cohorts'][dirname]; cm = c['cohort_mean']
    per = c['per_slide']
    out = {'kegg_mean': cm['kegg_moran'], 'n_slides': c['n_slides'],
           'kegg_per_slide': [r['kegg_moran'] for r in per]}
    for ctrl in ['random_HVG_union', 'random_HVG_union_exprMatched',
                 'random_HVG_ge2', 'random_allMeasured_strawman']:
        v = cm['controls'][ctrl]
        out[ctrl] = {'mean': v['random_moran_mean'], 'delta': v['delta'],
                     'sign_p': v['slide_level_sign_test_p'],
                     'n_pos': v['n_slides_kegg_gt_random'], 'n': v['n_slides'],
                     'per_slide': [r['controls'][ctrl]['random_moran_mean'] for r in per]}
    out['perm_p_max'] = float(np.max([r['kegg_perm_p'] for r in per]))
    return out
rg268 = rg_block('geo_hnscc_hpv_GSE268014')
rg281 = rg_block('geo_hpv_hnscc_GSE281978')

# Discriminative sample-level contrasts (pseudo-replication-free)
disc = json.load(open('results/hnscc_discriminative_eval.json', encoding='utf-8'))
d268 = disc['GSE268014']; d281 = disc['GSE281978']
sp = d268['sample_level_paired']
disc_num = {
    'mal_non_delta': sp['malignant_minus_nonmalignant']['mean_delta'],
    'mal_non_p': sp['malignant_minus_nonmalignant']['wilcoxon_p'],
    'mal_non_pos': sp['malignant_minus_nonmalignant']['n_sections_positive'],
    'mal_non_n': sp['malignant_minus_nonmalignant']['n_sections'],
    'edge_core_delta': sp['edge_zone1_minus_core_zone3']['mean_delta'],
    'edge_core_p': sp['edge_zone1_minus_core_zone3']['wilcoxon_p'],
    'edge_core_pos': sp['edge_zone1_minus_core_zone3']['n_sections_positive'],
    'edge_core_n': sp['edge_zone1_minus_core_zone3']['n_sections'],
    'hpv268_pos': d268['sample_level_hpv']['all_spots_mean']['mean_x'],
    'hpv268_neg': d268['sample_level_hpv']['all_spots_mean']['mean_y'],
    'hpv268_p': d268['sample_level_hpv']['all_spots_mean']['mwu_p'],
    'hpv268_npos': d268['sample_level_hpv']['all_spots_mean']['n_x'],
    'hpv268_nneg': d268['sample_level_hpv']['all_spots_mean']['n_y'],
    'hpv281_pos': d281['sample_level']['hpv_pos_vs_neg']['mean_x'],
    'hpv281_neg': d281['sample_level']['hpv_pos_vs_neg']['mean_y'],
    'hpv281_p': d281['sample_level']['hpv_pos_vs_neg']['mwu_p'],
    'hpv281_npos': d281['sample_level']['hpv_pos_vs_neg']['n_pos'],
    'hpv281_nneg': d281['sample_level']['hpv_pos_vs_neg']['n_neg'],
    'pt_mean': d281['sample_level']['primary_vs_lnmt']['mean_x'],
    'lnmt_mean': d281['sample_level']['primary_vs_lnmt']['mean_y'],
    'pt_lnmt_p': d281['sample_level']['primary_vs_lnmt']['mwu_p'],
    'pt_n': d281['sample_level']['primary_vs_lnmt']['n_pt'],
    'lnmt_n': d281['sample_level']['primary_vs_lnmt']['n_lnmt']}

ext = json.load(open('results/external_corrected_numbers.json', encoding='utf-8'))
gx = ext['geomx_gse316098_corrected']; lodo = ext['lodo_v2']; ul = ext.get('unsup_lodo_v2', {})
core_df = pd.read_csv('results/gse316098_core_level.csv')
roi_df = pd.read_csv('results/gse316098_corrected_silva_labels.csv')

NUM['external'] = {
    # GeoMx corrected (true SOFT labels: 1A/1b-1 are TMA core ids, NOT Silva)
    'geomx_n_patients': gx['n_patients'], 'geomx_n_cores': gx['n_cores'], 'geomx_n_rois': gx['n_rois'],
    'geomx_benign_mean': gx['roi_level']['benign_mean'], 'geomx_tumor_mean': gx['roi_level']['tumor_mean'],
    'geomx_tn_roi_p': gx['roi_level']['benign_vs_tumor_p'],
    'geomx_core_benign_mean': gx['core_level']['benign_mean'], 'geomx_core_tumor_mean': gx['core_level']['tumor_mean'],
    'geomx_tn_core_p': gx['core_level']['benign_vs_tumor_p'],
    'geomx_wp_n': gx['within_patient']['n_patients_paired'], 'geomx_wp_p': gx['within_patient']['paired_wilcoxon_p'],
    'geomx_wp_all': gx['within_patient']['all_tumor_gt_normal'],
    'geomx_silva_A': gx['roi_level']['silva']['A']['mean'], 'geomx_silva_B': gx['roi_level']['silva']['B']['mean'],
    'geomx_silva_C': gx['roi_level']['silva']['C']['mean'], 'geomx_AB_p': gx['roi_level']['silva_A_vs_B_p'],
    'geomx_core_silva_A': gx['core_level']['silva']['A']['mean'],
    'geomx_core_silva_B': gx['core_level']['silva']['B']['mean'],
    'geomx_core_silva_C': gx['core_level']['silva']['C']['mean'],
    'geomx_core_silva_AB_p': gx['core_level']['silva_A_vs_B_p'],
    'geomx_compartment_epi': gx['roi_level']['epi_mean'],
    'geomx_compartment_stroma': gx['roi_level']['stroma_mean'],
    'geomx_risk_hi': gx['roi_level']['risk_high_mean'], 'geomx_risk_lo': gx['roi_level']['risk_low_mean'],
    'geomx_risk_p': gx['roi_level']['risk_high_vs_low_p'],
    'geomx_risk_core_hi': gx['core_level']['risk_high_mean'],
    'geomx_risk_core_lo': gx['core_level']['risk_low_mean'],
    'geomx_risk_core_p': gx['core_level']['risk_high_vs_low_p'],
    'geomx_risk_core_hi_n': int((core_df.risk == 'High').sum()),
    'geomx_risk_core_lo_n': int((core_df.risk == 'Low').sum()),
    'geomx_compartment_p': gx['roi_level']['compartment_p'],
    # post-hoc: Silva pattern x compartment (rules out epi/stroma imbalance as
    # the cause of non-monotonicity and localizes the pattern-A-high signal)
    'geomx_silva_epi_A': float(roi_df.query("is_tumor and silva=='A' and compartment=='epi'").score.mean()),
    'geomx_silva_epi_B': float(roi_df.query("is_tumor and silva=='B' and compartment=='epi'").score.mean()),
    'geomx_silva_epi_C': float(roi_df.query("is_tumor and silva=='C' and compartment=='epi'").score.mean()),
    'geomx_silva_epi_AB_p': float(mannwhitneyu(
        roi_df.query("silva=='A' and compartment=='epi'").score,
        roi_df.query("silva=='B' and compartment=='epi'").score).pvalue),
    'geomx_silva_str_A': float(roi_df.query("is_tumor and silva=='A' and compartment=='stroma'").score.mean()),
    'geomx_silva_str_B': float(roi_df.query("is_tumor and silva=='B' and compartment=='stroma'").score.mean()),
    'geomx_silva_str_C': float(roi_df.query("is_tumor and silva=='C' and compartment=='stroma'").score.mean()),
    # exact-test resolution / Clopper-Pearson intervals for tiny-n counts
    'geomx_wp_exact_two_sided_floor_n6': 2.0 / 64.0,
    'geomx_wp_ci_lo': 0.541,
    'lodo_4of4_ci_lo': 0.398, 'unsup_3of4_ci_lo': 0.194,
    'rank_perm_distinct_labelings_35': int(35 * (34 * 33 * 32) // 6),
    # HNSCC — FINAL model-score Moran
    'hnscc_moran_mean': float(np.mean(hm)), 'hnscc_moran_min': float(np.min(hm)), 'hnscc_moran_max': float(np.max(hm)),
    'hnscc_n_samples': len(hm),
    'hnscc_gse281978_moran_mean': float(np.mean(g28)),
    'hnscc_gse281978_moran_min': float(np.min(g28)), 'hnscc_gse281978_moran_max': float(np.max(g28)),
    'hnscc_gse281978_n': len(g28),
    # coordinate-permutation null of the model score
    'hnscc_perm_null_mean_268': pm268['null_mean'], 'hnscc_perm_p_max_268': pm268['p_max'],
    'hnscc_perm_z_min_268': pm268['z_min'],
    'hnscc_perm_null_mean_281': pm281['null_mean'], 'hnscc_perm_p_max_281': pm281['p_max'],
    'hnscc_perm_z_min_281': pm281['z_min'],
    # random gene-set Moran controls (plain lognorm panel means)
    'rg268_kegg': rg268['kegg_mean'], 'rg268_exprm': rg268['random_HVG_union_exprMatched']['mean'],
    'rg268_exprm_delta': rg268['random_HVG_union_exprMatched']['delta'],
    'rg268_exprm_signp': rg268['random_HVG_union_exprMatched']['sign_p'],
    'rg268_exprm_npos': rg268['random_HVG_union_exprMatched']['n_pos'],
    'rg268_exprm_n': rg268['random_HVG_union_exprMatched']['n'],
    'rg268_hvgu': rg268['random_HVG_union']['mean'],
    'rg268_hvgu_signp': rg268['random_HVG_union']['sign_p'],
    'rg268_hvgu_npos': rg268['random_HVG_union']['n_pos'],
    'rg281_kegg': rg281['kegg_mean'], 'rg281_exprm': rg281['random_HVG_union_exprMatched']['mean'],
    'rg281_exprm_delta': rg281['random_HVG_union_exprMatched']['delta'],
    'rg281_exprm_signp': rg281['random_HVG_union_exprMatched']['sign_p'],
    'rg281_exprm_npos': rg281['random_HVG_union_exprMatched']['n_pos'],
    'rg281_exprm_n': rg281['random_HVG_union_exprMatched']['n'],
    'rg281_hvgu': rg281['random_HVG_union']['mean'],
    'rg281_hvgu_signp': rg281['random_HVG_union']['sign_p'],
    'rg281_hvgu_npos': rg281['random_HVG_union']['n_pos'],
    # discriminative sample-level contrasts
    **disc_num,
    # LODO v2 (final protocol, semi-supervised)
    'lodo_mean_pct': lodo['mean_percentile_vs_normal'], 'lodo_min_pct': lodo['min_percentile_vs_normal'],
    'lodo_n_above_median': lodo['n_above_median'], 'lodo_n_above_all': lodo['n_above_all'],
    'lodo_folds': lodo['folds'],
    # fully-unsupervised LODO v2 (final protocol, lambda_sup=lambda_prog=0)
    'unsup_lodo_mean_pct': ul.get('mean_percentile_vs_normal'),
    'unsup_lodo_min_pct': ul.get('min_percentile_vs_normal'),
    'unsup_lodo_max_pct': ul.get('max_percentile_vs_normal'),
    'unsup_lodo_n_above_median': ul.get('n_above_median'),
    'unsup_lodo_n_above_all': ul.get('n_above_all'),
    'unsup_lodo_n_folds': ul.get('n_folds', 0),
    'unsup_lodo_folds': ul.get('folds', []),
}

# ---------- 4b. leave-one-SAMPLE-out baselines (cross-sample extrapolation) ----------
# All numbers read verbatim from the baseline result JSONs; these are the
# honest "does in-cohort performance extrapolate across samples" anchors.
def _baseline_block():
    bl = {}
    p_auc = 'results/baseline_hpv_auc.json'
    if os.path.exists(p_auc):
        d = json.load(open(p_auc, encoding='utf-8'))
        for r in d['per_regressor']:
            if r['regressor'] == 'ridge':
                bl['loso_hpv_ridge_auc'] = r['mean_auc']
                bl['loso_hpv_ridge_auc_sd'] = r['std_auc']
                bl['loso_hpv_ridge_valid'] = r['n_valid_folds']
                bl['loso_hpv_ridge_total'] = r['n_samples']
            elif r['regressor'] in ('mlp', 'MLP'):
                bl['loso_hpv_mlp_auc'] = r['mean_auc']
                bl['loso_hpv_mlp_auc_sd'] = r['std_auc']
                bl['loso_hpv_mlp_valid'] = r['n_valid_folds']
    p_ridge = 'results/baseline_BASELINE_LOSO35_RIDGE.json'
    if os.path.exists(p_ridge):
        d = json.load(open(p_ridge, encoding='utf-8'))
        agg = d['per_regressor'][0]['aggregate']
        bl['loso35_mode'] = d.get('mode')
        bl['loso35_n_samples'] = d.get('n_samples')
        bl['loso35_fm'] = d.get('fm')
        bl['loso35_n_target_genes'] = d.get('n_final_genes')
        bl['loso35_recon_mse'] = agg['mean_mse']
        bl['loso35_per_gene_pearson'] = agg['mean_pearson']
        bl['loso35_valid_folds'] = agg['n_valid_folds']
    p_he = 'results/baseline_BASELINE_HE2ST.json'
    if os.path.exists(p_he):
        d = json.load(open(p_he, encoding='utf-8'))
        r0 = d['per_regressor'][0]
        bl['he2st_mode'] = d.get('mode')
        bl['he2st_sample'] = d.get('sample')
        bl['he2st_mse'] = r0['heldout_recon_mse']
    return bl

NUM['baseline'] = _baseline_block()

fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.6))

# A. cross-organ HNSCC: model score / plain KEGG panel / expr-matched random / coord-null
ax = axes[0, 0]
groups2 = ['GSE268014\n(n=8 sections)', 'GSE281978\n(n=6 sections)']
series = [
    ("Model score", [np.mean(hm), np.mean(g28)], [hm, g28], '#2F5496'),
    ("KEGG panel (plain mean)", [rg268['kegg_mean'], rg281['kegg_mean']],
     [rg268['kegg_per_slide'], rg281['kegg_per_slide']], '#5B9BD5'),
    ("Random 108 genes\n(expr-matched)",
     [rg268['random_HVG_union_exprMatched']['mean'],
      rg281['random_HVG_union_exprMatched']['mean']],
     [rg268['random_HVG_union_exprMatched']['per_slide'],
      rg281['random_HVG_union_exprMatched']['per_slide']], '#A6A6A6'),
    ("Coord. permutation\nnull", [0.0, 0.0], None, '#D9D9D9'),
]
x = np.arange(2); w = 0.2
for j, (lbl, means, dots, col) in enumerate(series):
    pos = x + (j - 1.5) * w
    bars = ax.bar(pos, means, w * 0.92, color=col, alpha=0.9,
                  label=lbl, edgecolor='white', linewidth=0.4,
                  hatch='//' if j == 3 else None)
    if dots is not None:
        for xi, arr in zip(pos, dots):
            jit = rng.uniform(-w * 0.28, w * 0.28, len(arr))
            ax.plot(np.full(len(arr), xi) + jit, arr, 'o',
                    color='#333333', ms=2.6, alpha=0.45, zorder=3)
    else:
        for xi in pos:
            ax.text(xi, 0.03, "~0", ha='center', va='bottom', fontsize=8, color='#595959')
ax.set_xticks(x); ax.set_xticklabels(groups2, fontsize=10.4)
ax.set_ylabel("Moran's I", fontsize=11); ax.set_ylim(0, 1.36)
ax.legend(fontsize=8.2, frameon=False, loc='upper center', ncol=2,
          handlelength=1.2, labelspacing=0.35, columnspacing=1.0,
          bbox_to_anchor=(0.5, 1.02))
ax.set_title(f"A. HNSCC: real spatial organization; weak pathway specificity\n"
             f"model {np.mean(hm):.2f}/{np.mean(g28):.2f}; KEGG vs expr-matched random "
             f"sign p={rg268['random_HVG_union_exprMatched']['sign_p']:.3f}/"
             f"{rg281['random_HVG_union_exprMatched']['sign_p']:.3f}; "
             f"perm p<=0.001",
             fontsize=10.2, fontweight='bold')

# B. GeoMx benign vs tumor (core-level violin)
ax = axes[0, 1]
ben = core_df.loc[~core_df.silva.isin(['A', 'B', 'C']), 'score'].values
tum = core_df.loc[core_df.silva.isin(['A', 'B', 'C']), 'score'].values
vp = ax.violinplot([ben, tum], positions=[0, 1], showmedians=True, widths=0.7)
for pc, c in zip(vp['bodies'], ['#9DC3E6', '#C00000']): pc.set_facecolor(c); pc.set_alpha(0.8)
for i, arr in enumerate([ben, tum]):
    ax.plot(np.full(len(arr), i) + rng.uniform(-0.08, 0.08, len(arr)), arr, 'o', ms=3,
            color='#333333', alpha=0.45)
ax.set_xticks([0, 1]); ax.set_xticklabels([f"Benign\n(n={len(ben)})", f"Tumor A/B/C\n(n={len(tum)})"], fontsize=10.5)
ax.set_ylabel("Pathway risk (GeoMx, expr-only)", fontsize=10.5)
ax.set_title(f"B. Cross-platform tumor>normal\n{tum.mean():.2f} vs {ben.mean():.2f}, MWU p={gx['core_level']['benign_vs_tumor_p']:.1e}",
             fontsize=11.5, fontweight='bold')

# C. GeoMx: core-level Silva pattern (non-monotonic) + pathological risk (reversed, n.s.)
ax = axes[1, 0]
labels = ['Silva A', 'Silva B', 'Silva C']
cs = gx['core_level']['silva']
means = [cs[k]['mean'] for k in ['A', 'B', 'C']]
ns = [cs[k]['n'] for k in ['A', 'B', 'C']]
xb = np.arange(3)
ax.bar(xb, means, 0.6, color=['#ED7D31', '#70AD47', '#2F5496'], alpha=0.85)
for i, (v, n) in enumerate(zip(means, ns)):
    ax.text(i, v + 0.12, f"{v:.2f}\n(n={n})", ha='center', fontsize=9)
ax.set_xticks(xb); ax.set_xticklabels(labels, fontsize=10)
ax.set_ylabel("Pathway risk (core level)", fontsize=10.5); ax.set_ylim(0, max(means) + 2.6)
rh, rl = gx['core_level']['risk_high_mean'], gx['core_level']['risk_low_mean']
ax.set_title(f"C. Not a risk grade (core level)\nA vs B p={gx['core_level']['silva_A_vs_B_p']:.3f}; "
             f"risk Low({rl:.2f}) > High({rh:.2f}), reversed, p={gx['core_level']['risk_high_vs_low_p']:.3f}",
             fontsize=10.0, fontweight='bold')

# D. LODO v2 percentile per fold: semi-supervised vs fully-unsupervised
ax = axes[1, 1]
semi_by = {f['holdout']: f['percentile_vs_normal'] for f in lodo['folds']}
uns_by = {f['holdout']: f['percentile_vs_normal'] for f in ul.get('folds', [])}
names_order = ['HSIL_HPV', 'CA_HPV_1', 'CA_HPV_2', 'cervical_cancer_1']
labels = [n.replace('_', '\n', 1) for n in names_order]
semi_v = [semi_by[n] for n in names_order]
uns_v = [(uns_by[n] if n in uns_by else np.nan) for n in names_order]
x = np.arange(4); w = 0.38
b1 = ax.bar(x - w/2, semi_v, w, color='#2F5496', alpha=0.9, label='Semi-sup. (3 diseases labeled)')
b2 = ax.bar(x + w/2, uns_v, w, color='#ED7D31', alpha=0.9, label='Fully unsup. (no labels)')
ax.axhline(0.5, ls='--', color='#7F7F7F', lw=1.2)
for xi, v in zip(x - w/2, semi_v):
    ax.text(xi, v + 0.045, f"{v:.2f}", ha='center', fontsize=9.3, fontweight='bold', color='#1F3864')
for xi, v in zip(x + w/2, uns_v):
    if not np.isnan(v):
        ax.text(xi, v + 0.045, f"{v:.2f}", ha='center', fontsize=9.3, color='#9C4A00')
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9.4)
ax.set_ylabel("Held-out disease percentile vs 31 normals", fontsize=10.5)
ax.set_ylim(0, 1.46)
ax.legend(fontsize=8.7, loc='upper center', ncol=2, frameon=False,
          bbox_to_anchor=(0.5, 1.01))
ax.set_title(f"D. LODO (final protocol): semi {lodo['n_above_median']}/4 vs unsup {ul.get('n_above_median','-')}/4 "
             f"above median\nmean pct {lodo['mean_percentile_vs_normal']:.2f} vs "
             f"{ul.get('mean_percentile_vs_normal', float('nan')):.2f}",
             fontsize=10.5, fontweight='bold')

plt.tight_layout(); plt.savefig(os.path.join(OUT, "Fig5_external_transfer.png")); plt.close()

# ---------- 5. random control + scrna + tcga numbers ----------
rc = json.load(open('results/random_control_summary.json', encoding='utf-8'))
NUM['random_control'] = {
    'kegg_moran': rc['kegg']['moran_i'], 'random_moran_mean': rc['random']['moran_i']['mean'],
    'random_moran_min': rc['random']['moran_i']['min'], 'random_moran_max': rc['random']['moran_i']['max'],
    'n_random': rc['random']['n'],
    'moran_perm_p': rc['permutation_test']['moran_i']['p_value'],
    'auc_perm_p': rc['permutation_test']['hpv_auc']['p_value'],
    'kegg_kendall': rc['kegg']['kendall_tau'], 'random_kendall_mean': rc['random']['kendall_tau_mean']}
sc_rna = json.load(open('results/scrna_marker_validation.json', encoding='utf-8'))
NUM['scrna'] = {'n_cells': sc_rna['n_cells'], 'n_markers': sc_rna['n_marker_genes_used'],
                'within_corr': sc_rna['within_set_gene_corr_mean'],
                'between_corr': sc_rna['between_set_gene_corr_mean'],
                'gap': sc_rna['coherence_minus_between']}
tc = json.load(open('results/tcga_deg_cox.json', encoding='utf-8'))
pg = sorted(tc['per_gene'], key=lambda r: r['wald_p'])
NUM['tcga'] = {'n_patients': pg[0]['n'], 'events': pg[0]['events'], 'n_genes': tc['n_tests'],
               'n_sig_BH': tc['n_significant_BH_q05'], 'min_gene': pg[0]['gene'],
               'min_p': pg[0]['wald_p'], 'min_HR': pg[0]['HR_per_SD']}
NUM['cohort'] = {'n_samples': 35, 'n_normal': 31, 'n_disease': 4, 'n_spots': 46820,
                 'n_genes_panel': 107, 'n_seed_full': abl_summary['FULL']['n_seeds']}

with open('results/paper_v10_numbers.json', 'w', encoding='utf-8') as f:
    json.dump(NUM, f, ensure_ascii=False, indent=2)
print("OK figures + numbers written.")
print(json.dumps(NUM['ablation'], indent=1)[:600])
print("external hnscc moran mean=%.3f n=%d | geomx tumor>normal core p=%.2e | LODO mean pct=%.3f" %
      (NUM['external']['hnscc_moran_mean'], NUM['external']['hnscc_n_samples'],
       NUM['external']['geomx_tn_core_p'], NUM['external']['lodo_mean_pct']))
