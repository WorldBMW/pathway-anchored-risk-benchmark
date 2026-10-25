"""Recompute donor-level ridge audit with refitting under label permutation.
Original outputs are never overwritten. Fixed, label-free X allows exact
linear-operator refitting for every permuted y. Includes intercept sensitivity.
"""
from pathlib import Path
import sys, json, hashlib
import numpy as np
from scipy.stats import kendalltau
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from probe_lodo import per_sample_embedding, ridge_predict
OUT=ROOT/'papers/12_CSBJ_audit_20261010'
OUT.mkdir(exist_ok=True)
(OUT/'evidence').mkdir(exist_ok=True)

def operator(X, intercept=False):
    n,p=X.shape; H=np.zeros((n,n))
    for i in range(n):
        tr=np.arange(n)!=i
        mu=X[tr].mean(0); sd=X[tr].std(0)+1e-8
        Z=(X[tr]-mu)/sd; z=(X[i]-mu)/sd
        # dual form equals ridge normal equations, alpha=1
        h=np.linalg.solve(Z@Z.T+np.eye(n-1),Z@z)
        if intercept: h=h-h.mean()+1/(n-1)
        H[i,tr]=h
    return H

def taus(P,Y):
    i,j=np.triu_indices(P.shape[1],1)
    a=np.sign(P[:,j]-P[:,i]); b=np.sign(Y[:,j]-Y[:,i])
    den=np.sqrt((a*a).sum(1)*(b*b).sum(1))
    return np.divide((a*b).sum(1),den,out=np.zeros(len(P)),where=den>0)

def audit(X,y,intercept,B=10000):
    H=operator(X,intercept)
    pred=H@y; obs=float(kendalltau(pred,y).statistic)
    rng=np.random.default_rng(20261010); ge=0; null=[]
    for start in range(0,B,200):
        Y=np.stack([rng.permutation(y) for _ in range(min(200,B-start))])
        ts=taus(Y@H.T,Y); ge+=int((ts>=obs-1e-12).sum()); null.extend(ts.tolist())
    return dict(tau=obs,p_refit=(ge+1)/(B+1),n_perm=B,
                null_mean=float(np.mean(null)),null_q95=float(np.quantile(null,.95)),
                predictions=pred.tolist())

def main():
    groups=['group_A','group_B','group_C','group_A_small','group_B_small','group_C_small','cervical']
    report={'analysis_date':'2026-10-10','permutation':'refit ridge for each donor-label permutation; fixed label-free encoder; one-sided positive association','groups':{}}
    checkpoint=OUT/'evidence/corrected_probe.json'
    if checkpoint.exists(): report=json.loads(checkpoint.read_text())
    for g in groups:
        if len(report['groups'].get(g,[]))==3: continue
        rows=[]
        for seed in range(3):
            name=f'fused_embs_NOALL_seed{seed}.npz' if g=='cervical' else f'fused_embs_SIM_{g}_NOALL_seed{seed}.npz'
            f=ROOT/'results'/name
            if not f.exists(): continue
            with np.load(f) as d: X,y,names=per_sample_embedding(d)
            # self-check legacy predictions against direct normal equations
            if g=='cervical' and seed==0:
                tr=np.arange(len(y))!=0
                assert np.allclose((operator(X.astype(float))@y)[0],ridge_predict(X[tr].astype(float),y[tr],X[:1].astype(float))[0],atol=1e-7)
            np.savez_compressed(OUT/'evidence'/f'pooled_{g}_seed{seed}.npz',X=X,y=y,names=np.array(names))
            row={'seed':seed,'n_samples':len(y),'label_counts':{str(v):int((y==v).sum()) for v in np.unique(y)},'source':name,'source_sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
            for label,intercept in [('legacy_no_intercept',False),('intercept_sensitivity',True)]: row[label]=audit(X,y,intercept)
            rows.append(row)
            print(g,seed,[(k,round(row[k]['tau'],4),row[k]['p_refit']) for k in ['legacy_no_intercept','intercept_sensitivity']],flush=True)
        report['groups'][g]=rows
        (OUT/'evidence/corrected_probe.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    # family-wise multiplicity: BH across 21 primary (no-intercept) seed tests
    rows=[r for rr in report['groups'].values() for r in rr]
    ps=np.array([r['legacy_no_intercept']['p_refit'] for r in rows]); ix=np.argsort(ps)
    q=np.minimum.accumulate((ps[ix]*len(ps)/np.arange(1,len(ps)+1))[::-1])[::-1].clip(0,1)
    for i,v in zip(ix,q): rows[i]['legacy_no_intercept']['q_BH_21']=float(v)
    (OUT/'evidence/corrected_probe.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

if __name__=='__main__': main()
