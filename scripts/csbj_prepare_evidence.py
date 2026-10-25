from pathlib import Path
import json, urllib.request, urllib.parse, concurrent.futures, hashlib, csv, sys
import numpy as np
from scipy.stats import kendalltau, wilcoxon
R=Path('G:/project4_cervix_multimodal'); O=R/'papers/12_CSBJ_audit_20261010'; E=O/'evidence'; E.mkdir(exist_ok=True)
refs={'stahl':'10.1126/science.aaf2403','moses':'10.1038/s41592-022-01409-2','uni':'10.1038/s41591-024-02857-3','stnet':'10.1038/s41551-020-0578-x','whalen':'10.1038/s41576-021-00434-9','kapoor':'10.1016/j.patter.2023.100804','varo':'10.1038/s41746-022-00592-y','bh':'10.1111/j.2517-6161.1995.tb02031.x','moran':'10.2307/2332142','kegg':'10.1093/nar/gkae909','phipson':'10.2202/1544-6115.1585','tripod':'10.1136/bmj-2023-078378','tcga':'10.1038/nature21386','ssgsea':'10.1038/nature08460','silva':'10.1097/PGP.0000000000000735','numpy':'10.1038/s41586-020-2649-2','scipy':'10.1038/s41592-019-0686-2'}
def fetch(kv):
 k,doi=kv
 try:
  u='https://api.crossref.org/works/'+urllib.parse.quote(doi,safe='')
  d=json.load(urllib.request.urlopen(u,timeout=40))['message']
  return k,dict(doi=doi,title=d['title'][0],authors=[(a.get('given','')+' '+a.get('family','')).strip() for a in d.get('author',[])],journal=d.get('container-title',[''])[0],year=d.get('published',{}).get('date-parts',[[None]])[0][0],volume=d.get('volume',''),page=d.get('page',d.get('article-number','')),url='https://doi.org/'+doi)
 except Exception as e:return k,{'doi':doi,'error':str(e)}
rr=json.loads((E/'references_verified.json').read_text(encoding='utf-8'))
for k,v in list(rr.items()):
 if 'error' in v: rr[k]=fetch((k,v['doi']))[1]
rr['ojala']={'title':'Permutation Tests for Studying Classifier Performance','authors':['Markus Ojala','Gemma C. Garriga'],'journal':'Journal of Machine Learning Research','year':2010,'volume':'11','page':'1833–1863','url':'https://www.jmlr.org/papers/v11/ojala10a.html'}
(E/'references_verified.json').write_text(json.dumps(rr,indent=2,ensure_ascii=False),encoding='utf-8')
print('REFERENCES',[(k,v.get('title',v.get('error'))) for k,v in rr.items()])
# Record exact real-data runs; seed sets must not be misrepresented as paired.
variants={'FULL':[0,3,4],'NOIMAGE':[0,1,2],'NOHPV':[0,1,2],'NONEIGH':[0,1,2],'NOPROG':[0,1,2,3],'NOSUP':[0,1,2],'NOALL':[0,1,2]}
runs={}
for v,seeds in variants.items():
 rows=[]
 for s in seeds:
  f=R/'results'/f'results_{v}_seed{s}.json'; d=json.loads(f.read_text(encoding='utf-8'))
  prog=d.get('progression_monotonicity')
  if not prog:
   from scipy.stats import kendalltau
   import sys
   sys.path.insert(0,str(R/'scripts'))
   from probe_lodo import severity_of
   scores=d['per_sample_score']; pairs=[(score,severity_of(name)) for name,score in scores.items() if severity_of(name) is not None]
   d['progression_monotonicity']={'kendall_tau':float(kendalltau(*zip(*pairs)).statistic)}
  rows.append({'seed':s,'file':f.name,'tau':d['progression_monotonicity']['kendall_tau'],'moran':d['moran_i'],'config':{k:d.get(k) for k in ['lambda_recon','lambda_sup','lambda_prog','lambda_hpv','lambda_neigh','fm','n_samples','n_spots','n_prior_genes','hpv_gene_set_size','no_neigh']},'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
 runs[v]=rows
(E/'real_run_registry.json').write_text(json.dumps(runs,indent=2),encoding='utf-8')
print('RUNS',[(v,len(a),float(np.mean([x['tau'] for x in a]))) for v,a in runs.items()])
# GeoMx FINAL scores linked to corrected labels; use patient means, not stale CSV scores.
rows=list(csv.DictReader((R/'results/gse316098_corrected_silva_labels.csv').open()))
patients=[]
for p in sorted(set(r['caseid'] for r in rows)):
 a=[float(r['score']) for r in rows if r['caseid']==p and r['is_tumor']=='True']; b=[float(r['score']) for r in rows if r['caseid']==p and r['is_tumor']=='False']
 if a and b: patients.append({'patient':p,'tumor_mean':float(np.mean(a)),'benign_mean':float(np.mean(b)),'difference':float(np.mean(a)-np.mean(b))})
g={'pairs':patients,'n_pairs':len(patients),'p_two_sided':float(wilcoxon([r['difference'] for r in patients],method='exact').pvalue)}
(E/'geomx_patient_final.json').write_text(json.dumps(g,indent=2),encoding='utf-8'); print('GEOMX',g)
# Reference metadata for datasets and repository, without credentials.
for accession in ['GSE208654','GSE217237','GSE316098','GSE268014','GSE281978','GSE308792']:
 try:
  u='https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc='+accession+'&targ=self&form=text&view=quick'
  s=urllib.request.urlopen(u,timeout=25).read().decode(); (E/(accession+'_metadata.txt')).write_text(s,encoding='utf-8'); print(accession,s[:100])
 except Exception as e:print(accession,type(e).__name__)
