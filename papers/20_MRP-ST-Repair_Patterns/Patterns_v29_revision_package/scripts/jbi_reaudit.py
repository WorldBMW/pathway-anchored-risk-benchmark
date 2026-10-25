"""Recompute JBI submission statistics without changing primary result files."""
from pathlib import Path
import json, hashlib, itertools
import numpy as np
import pandas as pd
from scipy.stats import kendalltau, rankdata, mannwhitneyu
from scipy.spatial import cKDTree

ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'results'; OUT=R/'jbi_submission_audit'; OUT.mkdir(exist_ok=True)
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sev(s):
    s=str(s).lower()
    return 2 if any(k in s for k in ['ca_hpv','cancer','carcinoma']) else 1 if any(k in s for k in ['hsil','cin']) else 0
def moran(s,xy):
    z=s-s.mean(); idx=cKDTree(xy).query(xy,k=7)[1][:,1:]
    return float((z[:,None]*z[idx]).sum()/6/(z*z).sum())

# With no score ties, all 209,440 assignments have the same tau denominator.
# Enumerate 3 cancer ranks and 1 distinct HSIL rank; 31 remaining ranks are normal.
null_s=[]
for cancer in itertools.combinations(range(1,36),3):
    for hsil in range(1,36):
        if hsil not in cancer:
            null_s.append(2*(sum(cancer)+hsil)-144+sum(1 if c>hsil else -1 for c in cancer))
null_s=np.asarray(null_s)
assert len(null_s)==209440
rng=np.random.default_rng(20260924)
mc_s=rng.choice(null_s,10000,replace=True)
N=read(R/'paper_v10_numbers.json'); audit={'null_assignments':len(null_s),'monte_carlo_seed':20260924,'variants':{},'discrepancies':[]}
old=read(R/'rank_perm_B10000.json')['variants']
for v in N['ablation']:
    rows=[]
    for fp in sorted(R.glob(f'fused_embs_{v}_seed*.npz')):
        seed=fp.stem.split('seed')[-1]
        z=np.load(fp,allow_pickle=True); scores=z['scores'].astype(float); ids=z['sample_ids'].astype(str)
        ps=pd.DataFrame({'sample':ids,'score':scores}).groupby('sample').score.mean()
        y=np.asarray([sev(s) for s in ps.index]); sc=ps.to_numpy()
        assert len(sc)==35 and len(np.unique(sc))==35
        tau,pas=kendalltau(y,sc); ranks=rankdata(sc)
        c=ranks[y==2]; h=ranks[y==1][0]
        observed=int(2*(sum(c)+h)-144+sum(np.sign(c-h)))
        assert np.isclose(tau,observed/np.sqrt(595*127))
        nge=int((mc_s>=observed).sum()); p=(nge+1)/10001
        exact=float((null_s>=observed).mean())
        d=read(R/f'results_{v}_seed{seed}.json')
        within=[]; numerator=denominator=0.
        for sid in ps.index:
            mask=ids==sid; s=scores[mask]; xy=z['coords'][mask]
            mi=moran(s,xy); within.append(mi); weight=float(((s-s.mean())**2).sum())
            numerator+=mi*weight; denominator+=weight
        row={'seed':seed,'tau':float(tau),'p_asymptotic':float(pas),'p_perm_B10000':p,'n_ge':nge,
             'p_exact':exact,'mwu_p':float(mannwhitneyu(sc[y>0],sc[y==0],alternative='greater').pvalue),
             'moran_global':d['moran_i'],'moran_within_mean':float(np.mean(within)),
             'moran_within_sd':float(np.std(within,ddof=1)), 'moran_within_pooled':numerator/denominator,
             'per_sample_moran':dict(zip(ps.index,within)),
             'score_sha256':hashlib.sha256(scores.tobytes()).hexdigest(),
             'source':str(fp.relative_to(ROOT))}
        rows.append(row)
        prev=next((t for t in old.get(v,[]) if t['seed']==seed),None)
        if prev and not np.isclose(prev['tau'],tau): audit['discrepancies'].append({'variant':v,'seed':seed,'old_tau':prev['tau'],'current_tau':float(tau)})
    audit['variants'][v]=rows
    a=N['ablation'][v]
    for key,field in [('tau','tau'),('moran','moran_global')]:
        vals=[r[field] for r in rows]; a[key+'_mean']=float(np.mean(vals)); a[key+'_sd']=float(np.std(vals,ddof=1))
    a.update(n_seeds=len(rows), seeds=[r['seed'] for r in rows],taus=[r['tau'] for r in rows],
             tau_perm_ps=[r['p_perm_B10000'] for r in rows],tau_perm_p_min=min(r['p_perm_B10000'] for r in rows),
             tau_perm_p_max=max(r['p_perm_B10000'] for r in rows),tau_perm_nsig=sum(r['p_perm_B10000']<.05 for r in rows),
             within_moran_mean=float(np.mean([r['moran_within_mean'] for r in rows])),
             within_moran_sd=float(np.std([r['moran_within_mean'] for r in rows],ddof=1)))
    print(v, 'tau',round(a['tau_mean'],4),'MC p',a['tau_perm_ps'],'within I',round(a['within_moran_mean'],4),flush=True)

# Preserve raw outputs; this is a derived submission-specific manifest.
for name,obj in [('rank_perm_recomputed.json',dict(B=10000,seed=20260924,note='One-sided positive ordering; scores fixed; current NPZ; plus exhaustive sensitivity analysis.',**audit)),('numbers.json',N)]:
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
print('Stale tau entries:',audit['discrepancies'])

def diff(a,b,path=''):
    if isinstance(a,dict) and isinstance(b,dict):
        for k in a.keys()|b.keys(): diff(a.get(k),b.get(k),path+'/'+k)
    elif a!=b and not isinstance(a,list): print('EXTERNAL VERSION',path,str(a)[:150],'=>',str(b)[:150])
diff(read(R/'external_corrected_numbers.json'),read(R/'external_corrected_numbers_FINAL.json'))
