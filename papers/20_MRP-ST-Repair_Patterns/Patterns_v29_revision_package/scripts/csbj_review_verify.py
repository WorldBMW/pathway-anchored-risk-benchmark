from pathlib import Path
import json,sys,re,urllib.request,concurrent.futures,hashlib
import numpy as np
from scipy.stats import kendalltau
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'papers/13_CSBJ_v2_20261014';O=SRC/'CSBJ_submission_checked_20261014';Q=SRC/'submission_review'

def operator(X,intercept=False):
    n,p=X.shape;H=np.zeros((n,n))
    for i in range(n):
        tr=np.arange(n)!=i;mu=X[tr].mean(0);sd=X[tr].std(0)+1e-8;Z=(X[tr]-mu)/sd;z=(X[i]-mu)/sd
        h=np.linalg.solve(Z@Z.T+np.eye(n-1),Z@z)
        if intercept:h=h-h.mean()+1/(n-1)
        H[i,tr]=h
    return H

def audit(X,y,intercept=False):
    H=operator(X,intercept);pred=H@y;obs=float(kendalltau(pred,y).statistic)
    rng=np.random.default_rng(20261010);i,j=np.triu_indices(len(y),1);ge=0
    for start in range(0,10000,100):
        Y=np.stack([rng.permutation(y) for _ in range(100)]);P=Y@H.T;a=np.sign(P[:,j]-P[:,i]);b=np.sign(Y[:,j]-Y[:,i]);den=np.sqrt((a*a).sum(1)*(b*b).sum(1));t=np.divide((a*b).sum(1),den,out=np.zeros(len(P)),where=den>0);ge+=int((t>=obs-1e-12).sum())
    return {'tau':obs,'p_refit':(ge+1)/10001}

def probes():
    p=json.loads((SRC/'evidence/corrected_probe.json').read_text(encoding='utf-8'));report=[]
    for cohort,rr in p['groups'].items():
        for r in rr:
            fp=SRC/'evidence'/f"pooled_{cohort}_seed{r['seed']}.npz"
            with np.load(fp) as z:X=z['X'];y=z['y']
            a=audit(X,y);original=r['legacy_no_intercept'];match=abs(a['tau']-original['tau'])<1e-9 and abs(a['p_refit']-original['p_refit'])<1e-9
            report.append({'cohort':cohort,'seed':r['seed'],'recomputed':a,'stored':original,'match':match});print(cohort,r['seed'],a,'match',match,flush=True)
    if (Q/'primary_probe_reproduction.json').exists():
        previous=json.loads((Q/'primary_probe_reproduction.json').read_text(encoding='utf-8'))
        if len(previous)==21 and not all(r['match'] for r in previous):(Q/'primary_probe_float64_sensitivity.json').write_text(json.dumps(previous,indent=2),encoding='utf-8')
    (Q/'primary_probe_reproduction.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    assert all(r['match'] for r in report),'Primary probe mismatch requires investigation'
    print('All 21 primary probes reproduced',flush=True)

def sources():
    accessions=['GSE208654','GSE217237','GSE316098','GSE268014','GSE281978','GSE308792']
    def one(acc):
        url='https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc='+acc+'&targ=self&form=text&view=full'
        try:
            with urllib.request.urlopen(url,timeout=45) as r:t=r.read().decode('utf-8')
            (Q/(acc+'_live.txt')).write_text(t,encoding='utf-8');return {'accession':acc,'url':url,'valid':('^SERIES = '+acc) in t,'title':next((x for x in t.splitlines() if x.startswith('!Series_title')),''),'status':next((x for x in t.splitlines() if x.startswith('!Series_status')),'')}
        except Exception as e:return {'accession':acc,'url':url,'error':str(e)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:r=list(pool.map(one,accessions))
    (Q/'geo_live_checks.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');print(r,flush=True)
    # Inspect the actual tagged tree without changing or publishing anything.
    try:
        req=urllib.request.Request('https://api.github.com/repos/WorldBMW/pathway-anchored-risk-benchmark/git/trees/v1.0?recursive=1',headers={'User-Agent':'CSBJ-manuscript-review'})
        with urllib.request.urlopen(req,timeout=45) as r:t=json.load(r)
        (Q/'github_v1_tree.json').write_text(json.dumps(t,indent=2),encoding='utf-8');paths=[x['path'] for x in t['tree']];print('Tagged tree',len(paths),'files; npz count',sum(p.endswith('.npz') for p in paths),flush=True)
    except Exception as e:print('Tagged tree access',str(e),flush=True)

if __name__=='__main__':
    if '--sources' in sys.argv:sources()
    else:probes()
