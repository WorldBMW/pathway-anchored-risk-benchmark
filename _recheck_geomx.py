# -*- coding: utf-8 -*-
"""用 GSE316098 真实样本元数据（silva pattern / risk / caseid）重算通路风险分组比较"""
import json, re
from collections import defaultdict
from scipy.stats import mannwhitneyu, kruskal
import numpy as np

d = json.load(open('results/external_gse316098_validation.json'))
meta = json.load(open('data/st_visium/geo_cervical_geomx_GSE316098/sample_metadata.json'))

# 键名规范化：去掉所有非字母数字字符后匹配（"1b-1.001.epi" vs "1b.1.001.epi"）
canon = lambda k: re.sub(r'[^A-Za-z0-9]', '', k)
norm = {canon(k): v for k, v in meta.items()}
import re as _re

bysilva = defaultdict(list); byrisk = defaultdict(list); bycase = defaultdict(list)
for r in d['per_roi']:
    m = norm.get(canon(r['roi']), {})
    bysilva[m.get('silva pattern', '?')].append(r['score'])
    byrisk[m.get('risk', '?')].append(r['score'])
    bycase[m.get('caseid', '?')].append(r['score'])

print("== pathway risk by TRUE Silva pattern ==")
for k in ['normal', 'A', 'B', 'C']:
    v = bysilva[k]
    print("  %-7s n=%3d mean=%.2f median=%.2f" % (k, len(v), np.mean(v), np.median(v)))
groups = [bysilva[k] for k in ['normal', 'A', 'B', 'C']]
print("  Kruskal H p=%.4g" % kruskal(*groups).pvalue)
for a, b in [('A', 'B'), ('A', 'C'), ('B', 'C'), ('normal', 'A'), ('normal', 'C')]:
    u = mannwhitneyu(bysilva[a], bysilva[b], alternative='two-sided')
    print("  MWU %s vs %s: p=%.4g" % (a, b, u.pvalue))

print("== pathway risk by risk label ==")
for k in ['Normal', 'Low', 'High']:
    v = byrisk[k]
    print("  %-7s n=%3d mean=%.2f median=%.2f" % (k, len(v), np.mean(v), np.median(v)))
for a, b in [('High', 'Low'), ('Low', 'Normal'), ('High', 'Normal')]:
    u = mannwhitneyu(byrisk[a], byrisk[b], alternative='two-sided')
    print("  MWU %s vs %s: p=%.4g" % (a, b, u.pvalue))
print("  Kruskal: %.4g" % kruskal(byrisk['Normal'], byrisk['Low'], byrisk['High']).pvalue)

print("== per case (7 cases) ==")
for k in sorted(bycase):
    v = bycase[k]
    print("  %s n=%3d mean=%.2f" % (k, len(v), np.mean(v)))

print("== compartment within pattern ==")
byc = defaultdict(lambda: defaultdict(list))
for r in d['per_roi']:
    m = norm.get(canon(r['roi']), {})
    byc[m.get('silva pattern', '?')][r['compartment']].append(r['score'])
for k in ['normal', 'A', 'B', 'C']:
    e = byc[k]['epi']; s = byc[k]['stroma']
    print("  %-7s epi=%.2f stroma=%.2f MWU p=%.3g" % (k, np.mean(e), np.mean(s), mannwhitneyu(e, s).pvalue))

oldA = [r['score'] for r in d['per_roi'] if r['pattern'] == '1A']
oldB = [r['score'] for r in d['per_roi'] if r['pattern'] != '1A']
print("old block grouping: 1A=%.2f 1b-1=%.2f p=%.4g" % (np.mean(oldA), np.mean(oldB), mannwhitneyu(oldA, oldB).pvalue))

# 方向性检验：tumor ROI(epi) 中 pattern C vs A
tum = defaultdict(list)
for r in d['per_roi']:
    if r['compartment'] != 'epi':
        continue
    m = norm.get(canon(r['roi']), {})
    tum[m.get('silva pattern', '?')].append(r['score'])
print("== tumor-epithelium ROIs only ==")
for k in ['normal', 'A', 'B', 'C']:
    v = tum[k]
    print("  %-7s n=%3d mean=%.2f" % (k, len(v), np.mean(v)))
for a, b in [('C', 'A'), ('C', 'B'), ('B', 'A')]:
    u = mannwhitneyu(tum[a], tum[b], alternative='two-sided')
    print("  MWU %s vs %s: p=%.4g" % (a, b, u.pvalue))
