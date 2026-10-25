"""CPU reproduction of pooled representation probes supplied with the manuscript.

Dependencies: numpy and scipy. Run from the extracted evidence archive root.
The feature arithmetic preserves the stored array dtype; the solve is float64.
"""
from pathlib import Path
import argparse,json
import numpy as np
from scipy.stats import kendalltau

def calculate(X,y,B,seed=20261010):
    n=len(y);H=np.zeros((n,n))
    for i in range(n):
        tr=np.arange(n)!=i;mu=X[tr].mean(0);sd=X[tr].std(0)+1e-8
        Z=(X[tr]-mu)/sd;z=(X[i]-mu)/sd
        H[i,tr]=np.linalg.solve(Z@Z.T+np.eye(n-1),Z@z)
    pred=H@y;tau=float(kendalltau(pred,y).statistic)
    rng=np.random.default_rng(seed);ii,jj=np.triu_indices(n,1);ge=0
    for start in range(0,B,100):
        Y=np.stack([rng.permutation(y) for _ in range(min(100,B-start))]);P=Y@H.T
        a=np.sign(P[:,jj]-P[:,ii]);b=np.sign(Y[:,jj]-Y[:,ii]);den=np.sqrt((a*a).sum(1)*(b*b).sum(1))
        t=np.divide((a*b).sum(1),den,out=np.zeros(len(P)),where=den>0)
        ge+=int((t>=tau-1e-12).sum())
    return {'tau':tau,'p_refit':(ge+1)/(B+1),'n':n,'n_permutations':B,'dtype':str(X.dtype)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--evidence',default='evidence');ap.add_argument('--section',choices=['primary','published','grid','all'],default='primary');ap.add_argument('--permutations',type=int,default=10000);ap.add_argument('--out',default='audit_reproduction.json');args=ap.parse_args()
    if args.permutations<1:ap.error('--permutations must be positive')
    ev=Path(args.evidence);files=[]
    if args.section in ['primary','all']:files+=sorted(ev.glob('pooled_*_seed*.npz'))
    if args.section in ['published','all']:files+=sorted((ev/'st_method_embeddings').glob('*.npz'))
    if args.section in ['grid','all']:files+=sorted((ev/'pooled_grid').glob('*.npz'))
    if not files:raise SystemExit('No pooled arrays found; run from the extracted archive root or pass --evidence.')
    output={}
    for p in files:
        with np.load(p,allow_pickle=True) as z:r=calculate(z['X'],z['y'],args.permutations)
        output[str(p.relative_to(ev))]=r;print(p.name,r,flush=True)
    Path(args.out).write_text(json.dumps(output,indent=2),encoding='utf-8')
if __name__=='__main__':main()
