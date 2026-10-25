# -*- coding: utf-8 -*-
"""Correct label-permutation p for sample-level Kendall tau (B=10000).

The 35-sample severity vector (31 zeros, one HSIL=1, three cancers=2) is
permuted against held per-sample mean scores. This is the calibration the
paper cites; scipy's asymptotic Kendall p is reported alongside for
comparison. Writes results/rank_perm_B10000.json.
"""
import json, glob
import numpy as np, pandas as pd
from scipy.stats import kendalltau

B = 10000
VARIANTS = ['FULL', 'NOIMAGE', 'NOHPV', 'NONEIGH', 'NOPROG', 'NOSUP', 'NOALL']

def severity_of(n):
    n = str(n).lower()
    if 'ca_hpv' in n or 'cancer' in n or 'carcinoma' in n: return 2
    if 'hsil' in n or 'cin' in n: return 1
    return 0

out = {'B': B, 'note': 'severity labels (31 normal/1 HSIL/3 cancer) permuted over 35 samples',
       'variants': {}}
rng_master = np.random.default_rng(20260915)

for v in VARIANTS:
    rows = []
    for p in sorted(glob.glob(f'results/fused_embs_{v}_seed*.npz')):
        seed = p.split('seed')[-1].split('.')[0]
        z = np.load(p, allow_pickle=True)
        scores = z['scores'].astype(float); sids = z['sample_ids'].astype(str)
        df = pd.DataFrame({'sid': sids, 'score': scores})
        ps = df.groupby('sid')['score'].mean().reset_index()
        ps['sev'] = ps['sid'].map(severity_of)
        sev = ps['sev'].to_numpy(); sc = ps['score'].to_numpy()
        tau, p_asym = kendalltau(sev, sc)
        rng = np.random.default_rng(20260915 + int(seed))
        ge = 0
        for _ in range(B):
            t, _ = kendalltau(rng.permutation(sev), sc)
            if t >= tau: ge += 1
        p_perm = (ge + 1) / (B + 1)
        rows.append({'seed': seed, 'tau': float(tau), 'p_asymptotic': float(p_asym),
                     'p_perm_B10000': float(p_perm), 'n_ge': ge})
        print(f"{v:8s} seed{seed} tau={tau:+.4f} asymp_p={p_asym:.5f} perm_p={p_perm:.5f} (ge={ge})")
    out['variants'][v] = rows

json.dump(out, open('results/rank_perm_B10000.json', 'w', encoding='utf-8'), indent=1)
print('wrote results/rank_perm_B10000.json')
