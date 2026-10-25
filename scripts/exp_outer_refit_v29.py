"""Corrected HAR outer audit: preprocessing fitted on outer-training groups only.

Produces new outputs only. Reports pooled and mean-within-group rank statistics
separately; neither fold SD nor one seed is used as an equivalence test.
"""
from pathlib import Path
import sys,json,time
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from exp_crossdomain_audit import load_har,subsample_units
from exp_outer_refit_v28 import train_embed_subset
from exp_regate_v28 import lgo_pred,kendall_tau

def preprocess(train_raw,all_raw):
 lo,hi=np.percentile(train_raw,[1,99],axis=0)
 clipped=np.clip(train_raw,lo,hi)
 mu=clipped.mean(0);sd=clipped.std(0);sd=np.where(sd>1e-8,sd,1.)
 return ((np.clip(all_raw,lo,hi)-mu)/sd).astype(np.float64)

def predict(train_X,train_y,test_X):
 mu=train_X.mean(0);sd=train_X.std(0)+1e-8
 Z=(train_X-mu)/sd;Ze=(test_X-mu)/sd
 w=np.linalg.solve(Z.T@Z+np.eye(Z.shape[1]),Z.T@train_y)
 return Ze@w

def main():
 X,y,g=load_har();y=np.asarray(y,float);_,g=np.unique(g,return_inverse=True)
 ui=subsample_units(y,g,300);yu,gu=y[ui],g[ui];rows=[]
 for lam in [0.,2.]:
  start=time.time();Z=train_embed_subset(preprocess(X,X),g,np.arange(len(y)),64,len(np.unique(g)),lam,0,30)
  frozen=lgo_pred(Z[ui],yu,gu);outer=np.full(len(ui),np.nan);folds=[]
  for k,gg in enumerate(np.unique(gu)):
   tr_obs=np.flatnonzero(g!=gg);tr=gu!=gg;te=~tr
   fold_X=preprocess(X[tr_obs],X)
   Zf=train_embed_subset(fold_X,g,tr_obs,64,len(np.unique(g)),lam,0,30)
   outer[te]=predict(Zf[ui][tr],yu[tr],Zf[ui][te])
   folds.append({'group':int(gg),'n_test':int(te.sum()),'tau_frozen':float(kendall_tau(frozen[te],yu[te])),'tau_outer':float(kendall_tau(outer[te],yu[te]))})
   if (k+1)%10==0:print('dose',lam,'folds',k+1,flush=True)
  row={'domain':'HAR','seed':0,'lam':lam,'n_folds':len(folds),'m_units':len(ui),'pooled_tau_frozen':float(kendall_tau(frozen,yu)),'pooled_tau_outer':float(kendall_tau(outer,yu)),'mean_fold_tau_frozen':float(np.nanmean([f['tau_frozen'] for f in folds])),'mean_fold_tau_outer':float(np.nanmean([f['tau_outer'] for f in folds])),'folds':folds,'seconds':time.time()-start}
  rows.append(row);print('DONE', {k:v for k,v in row.items() if k!='folds'},flush=True)
 payload={'protocol':{'preprocessing':'1/99 percentiles, clipped mean and SD fitted solely on outer-training observations; probe scaling also train-only','epochs':30,'seeds':[0],'doses':[0,2],'metric_scope':'nominal-code-dependent exploratory Kendall tau; pooled out-of-fold and mean-fold tau are distinct','no_equivalence_test':True},'runs':rows}
 Path('results/outer_refit_v29.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
if __name__=='__main__':main()
