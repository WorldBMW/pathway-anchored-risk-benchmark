# -*- coding: utf-8 -*-
"""
build_external_corrected.py
---------------------------
Single reproducible source for the TWO corrected external-transfer numbers used by the v10 paper:

(1) GeoMx GSE316098 — the ROI *name prefix* (1A / 1b-1) is a TMA core/block id, NOT the
    Silva pattern. The true labels come from the GEO SOFT metadata
    (`silva pattern`, `risk`, `caseid`). We re-attach correct labels to the already-computed
    expression-branch scores (results/external_gse316098_validation.json -> per_roi) and report:
      - benign vs tumor(A+B+C)  [ROI-level, core-level, within-patient paired]
      - Silva A vs B vs C       [non-monotonic, descriptive]
      - pathology risk High vs Low [n.s.]
      - epithelial vs stromal compartment
(2) LODOv2 — 4 leave-one-disease-out folds trained under the FINAL locked protocol
    (46820-spot cohort, lambda_recon=0.2/sup=5/prog=1.5). Percentile of each held-out disease
    slide among the 31 training normals.

Writes results/external_corrected_numbers.json (read by gen_figures_v10.py / gen_word_v10.py).
"""
import gzip, re, json, glob, os
import numpy as np, pandas as pd
from scipy.stats import mannwhitneyu, wilcoxon

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOFT = 'data/st_visium/geo_cervical_geomx_GSE316098/GSE316098_family.soft.gz'
# Override with GEO_MX_SCORE_JSON env var to build stats from a different
# checkpoint's scores (e.g. final-protocol external_gse316098_validation_FINAL.json).
SCORE_JSON = os.environ.get('GEO_MX_SCORE_JSON', 'results/external_gse316098_validation.json')
OUT = os.environ.get('GEO_MX_OUT', 'results/external_corrected_numbers.json')


def mwu(a, b):
    return float(mannwhitneyu(np.asarray(a, float), np.asarray(b, float),
                              alternative='two-sided').pvalue)


# =================================================================== GeoMx
soft = gzip.open(SOFT, 'rt', encoding='utf-8', errors='replace').read()
rows = []
for blk in soft.split('^SAMPLE =')[1:]:
    t = re.search(r'!Sample_title\s*=\s*(\S+)', blk)
    def char(key):
        m = re.search(r'!Sample_characteristics_ch1\s*=\s*%s:\s*(.+)' % key, blk)
        return m.group(1).strip() if m else None
    if t:
        rows.append(dict(roi=t.group(1).strip(), silva=char('silva pattern'),
                         risk=char('risk'), caseid=char('caseid')))
meta = pd.DataFrame(rows)

g = json.load(open(SCORE_JSON, encoding='utf-8'))
sc = pd.DataFrame(g['per_roi'])
sc['roi'] = sc['roi'].str.replace(r'^1b-1\.', '1b.1.', regex=True)  # counts<->SOFT name
m = sc.merge(meta, on='roi', how='left')
assert m['silva'].notna().all(), "unlabeled ROIs after join"
m['core'] = m['roi'].str.rsplit('.', n=1).str[0]
m['is_tumor'] = m['silva'].isin(['A', 'B', 'C'])

# ROI level (186)
def grp_means(df, key):
    return {str(k): float(v.mean()) for k, v in df.groupby(key)['score']}

A = m.loc[m.silva == 'A', 'score']; B = m.loc[m.silva == 'B', 'score']
C = m.loc[m.silva == 'C', 'score']; N = m.loc[m.silva == '~m'] if False else m.loc[~m.is_tumor, 'score']
T = m.loc[m.is_tumor, 'score']
epi = m.loc[m.compartment == 'epi', 'score']; stro = m.loc[m.compartment == 'stroma', 'score']
hi = m.loc[m.risk.str.lower() == 'high', 'score']; lo = m.loc[m.risk.str.lower() == 'low', 'score']

# core level (93 paired epi+stroma tissue regions)
core = m.groupby(['core', 'caseid', 'silva', 'risk'], as_index=False)['score'].mean()
cA = core.loc[core.silva == 'A', 'score']; cB = core.loc[core.silva == 'B', 'score']
cC = core.loc[core.silva == 'C', 'score']; cN = core.loc[~core.silva.isin(['A','B','C']), 'score']
cT = core.loc[core.silva.isin(['A','B','C']), 'score']
cHi = core.loc[core.risk.str.lower() == 'high', 'score']
cLo = core.loc[core.risk.str.lower() == 'low', 'score']

# within-patient paired (caseids carrying both benign and tumor cores)
pm = core.assign(is_tumor=core.silva.isin(['A','B','C'])).groupby(['caseid','is_tumor'])['score'].mean().unstack()
pm.columns = ['normal_mean' if c is False else 'tumor_mean' for c in pm.columns]
both = pm.dropna()
wp = wilcoxon(both['tumor_mean'], both['normal_mean'])

geomx = {
    "n_rois": int(len(m)), "n_cores": int(len(core)), "n_patients": int(m.caseid.nunique()),
    "roi_level": {
        "benign_n": int(len(N)), "tumor_n": int(len(T)),
        "benign_mean": float(N.mean()), "tumor_mean": float(T.mean()),
        "benign_vs_tumor_p": mwu(N, T),
        "silva": {k: {"n": int((m.silva == k).sum()), "mean": float(m.loc[m.silva == k, 'score'].mean())}
                  for k in ['A', 'B', 'C']},
        "silva_A_vs_B_p": mwu(A, B), "silva_A_vs_C_p": mwu(A, C), "silva_B_vs_C_p": mwu(B, C),
        "risk_high_n": int(len(hi)), "risk_low_n": int(len(lo)),
        "risk_high_mean": float(hi.mean()), "risk_low_mean": float(lo.mean()),
        "risk_high_vs_low_p": mwu(hi, lo),
        "epi_mean": float(epi.mean()), "stroma_mean": float(stro.mean()),
        "compartment_p": float(g.get('compartment_p', mwu(epi, stro))),
    },
    "core_level": {
        "benign_n": int(len(cN)), "tumor_n": int(len(cT)),
        "benign_mean": float(cN.mean()), "tumor_mean": float(cT.mean()),
        "benign_vs_tumor_p": mwu(cN, cT),
        "silva": {k: {"n": int((core.silva == k).sum()), "mean": float(core.loc[core.silva == k, 'score'].mean())}
                  for k in ['A', 'B', 'C']},
        "silva_A_vs_B_p": mwu(cA, cB), "silva_B_vs_C_p": mwu(cB, cC),
        "risk_high_mean": float(cHi.mean()), "risk_low_mean": float(cLo.mean()),
        "risk_high_vs_low_p": mwu(cHi, cLo),
    },
    "within_patient": {
        "n_patients_paired": int(len(both)),
        "tumor_mean": float(both['tumor_mean'].mean()),
        "normal_mean": float(both['normal_mean'].mean()),
        "mean_diff": float((both['tumor_mean'] - both['normal_mean']).mean()),
        "all_tumor_gt_normal": bool((both['tumor_mean'] > both['normal_mean']).all()),
        "paired_wilcoxon_p": float(wp.pvalue),
    },
}

# =================================================================== LODO v2
def severity(name):
    n = str(name).lower()
    if 'ca_hpv' in n or 'cancer' in n or 'carcinoma' in n: return 2
    if 'hsil' in n or 'cin' in n: return 1
    return 0

folds = []
for f in sorted(glob.glob('results/results_LODOv2_*.json')):
    d = json.load(open(f, encoding='utf-8'))
    held = d['run_id'].replace('LODOv2_', '')
    pss = {k.split('/')[-1]: v for k, v in d.get('per_sample_score', {}).items()}
    nv = np.array([v for k, v in pss.items() if severity(k) == 0], float)
    ho = d.get('holdout') or {}
    ho_mean = ho_moran = None
    for k, v in ho.items():
        if isinstance(v, dict):
            ho_mean, ho_moran = v.get('mean_risk'), v.get('moran_i')
    pct = float((nv < ho_mean).mean())
    folds.append({"holdout": held, "holdout_mean_risk": float(ho_mean),
                  "holdout_moran_i": ho_moran, "n_normal_train": int(len(nv)),
                  "normal_mean": float(nv.mean()), "percentile_vs_normal": pct,
                  "above_median_normal": bool(ho_mean > np.median(nv)),
                  "above_all_normal": bool(ho_mean > nv.max()),
                  "lambda_recon": d.get('lambda_recon'), "lambda_sup": d.get('lambda_sup'),
                  "lambda_prog": d.get('lambda_prog'), "n_train_samples": d.get('n_samples'),
                  "train_spots": d.get('n_spots')})
pcts = np.array([x['percentile_vs_normal'] for x in folds])
lodo = {
    "protocol": "final locked (full-spot cohort; lambda_recon=0.2, lambda_hpv=1.0, "
                "lambda_neigh=0.3, lambda_sup=5.0, lambda_prog=1.5; other 3 labeled diseases kept)",
    "n_folds": len(folds), "folds": folds,
    "mean_percentile_vs_normal": float(pcts.mean()),
    "min_percentile_vs_normal": float(pcts.min()),
    "n_above_median": int(sum(x['above_median_normal'] for x in folds)),
    "n_above_all": int(sum(x['above_all_normal'] for x in folds)),
    "note": "Semi-supervised LODO. Fully unsupervised LODO (lambda_sup=lambda_prog=0) collapses "
            "(results_UNSUP_LODO_*), consistent with NO-PROG.",
}

# ================================================== UNSUP LODO v2 (final protocol rerun)
def _collect_lodo(pattern, tag):
    out = []
    for f in sorted(glob.glob(pattern)):
        d = json.load(open(f, encoding='utf-8'))
        held = d['run_id'].replace(tag, '')
        pss = {k.split('/')[-1]: v for k, v in d.get('per_sample_score', {}).items()}
        nv = np.array([v for k, v in pss.items() if severity(k) == 0], float)
        ho = d.get('holdout') or {}
        ho_mean = ho_moran = None
        for k, v in ho.items():
            if isinstance(v, dict):
                ho_mean, ho_moran = v.get('mean_risk'), v.get('moran_i')
        if ho_mean is None or len(nv) == 0:
            continue
        if d.get('n_samples') != 34:
            print(f"  [skip] {f}: n_samples={d.get('n_samples')} (locked LODO fold must be 34; likely cohort contamination)")
            continue
        out.append({"holdout": held, "holdout_mean_risk": float(ho_mean),
                    "holdout_moran_i": ho_moran, "n_normal_train": int(len(nv)),
                    "normal_mean": float(nv.mean()),
                    "percentile_vs_normal": float((nv < ho_mean).mean()),
                    "above_median_normal": bool(ho_mean > np.median(nv)),
                    "above_all_normal": bool(ho_mean > nv.max()),
                    "hpv_proxy_auc": d.get('hpv_proxy_auc'),
                    "lambda_recon": d.get('lambda_recon'), "lambda_sup": d.get('lambda_sup'),
                    "lambda_prog": d.get('lambda_prog'), "n_train_samples": d.get('n_samples'),
                    "train_spots": d.get('n_spots')})
    return out

ufolds = _collect_lodo('results/results_UNSUP_LODOv2_*.json', 'UNSUP_LODOv2_')
if ufolds:
    upcts = np.array([x['percentile_vs_normal'] for x in ufolds])
    unsup_lodo = {
        "protocol": "final locked, fully unsupervised (full-spot cohort, no spot cap; "
                    "lambda_sup=0, lambda_prog=0; lambda_recon=0.2, lambda_hpv=1.0, lambda_neigh=0.3)",
        "n_folds": len(ufolds), "folds": ufolds,
        "mean_percentile_vs_normal": float(upcts.mean()),
        "min_percentile_vs_normal": float(upcts.min()),
        "max_percentile_vs_normal": float(upcts.max()),
        "n_above_median": int(sum(x['above_median_normal'] for x in ufolds)),
        "n_above_all": int(sum(x['above_all_normal'] for x in ufolds)),
        "note": "Final-protocol rerun replacing the exploratory 30,000-spot results_UNSUP_LODO_* folds.",
    }
else:
    unsup_lodo = {"n_folds": 0, "folds": [],
                  "note": "Pending: run results_UNSUP_LODOv2_* (full-spot, lambda_sup=lambda_prog=0)."}

json.dump({"geomx_gse316098_corrected": geomx, "lodo_v2": lodo, "unsup_lodo_v2": unsup_lodo},
          open(OUT, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
m.to_csv('results/gse316098_corrected_silva_labels.csv', index=False)
core.to_csv('results/gse316098_core_level.csv', index=False)

print("GeoMx corrected:")
print(f"  benign {N.mean():.3f} (n={len(N)}) vs tumor {T.mean():.3f} (n={len(T)})  ROI p={mwu(N,T):.2e}")
print(f"  core benign {cN.mean():.3f} vs tumor {cT.mean():.3f}  p={mwu(cN,cT):.2e}")
print(f"  within-patient {len(both)} cases Wilcoxon p={wp.pvalue:.4f}  all higher={geomx['within_patient']['all_tumor_gt_normal']}")
print(f"  Silva A {A.mean():.3f} B {B.mean():.3f} C {C.mean():.3f} | A vs B p={mwu(A,B):.4f} | risk H vs L p={mwu(hi,lo):.3f}")
print(f"LODOv2: mean percentile {pcts.mean():.3f}, above median {lodo['n_above_median']}/4, above all {lodo['n_above_all']}/4")
print("wrote", OUT)
