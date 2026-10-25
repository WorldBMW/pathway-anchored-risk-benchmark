from pathlib import Path
import urllib.request,json,concurrent.futures,sys,zipfile,io,hashlib
sys.stdout.reconfigure(encoding='utf-8')
Q=Path('.qa/patterns_v29');Q.mkdir(parents=True,exist_ok=True)
def fetch(url):
 req=urllib.request.Request(url,headers={'User-Agent':'ManuscriptArchiveAudit/1.0','Accept':'application/json'})
 with urllib.request.urlopen(req,timeout=40) as r:return r.read()
urls={'zenodo':'https://zenodo.org/api/records/23640979','repo':'https://api.github.com/repos/WorldBMW/pathway-anchored-risk-benchmark','release':'https://api.github.com/repos/WorldBMW/pathway-anchored-risk-benchmark/releases/tags/v1.0.0','tree':'https://api.github.com/repos/WorldBMW/pathway-anchored-risk-benchmark/git/trees/v1.0.0?recursive=1'}
out={}
def one(k,u):
 try:
  raw=fetch(u);(Q/f'{k}.json').write_bytes(raw);return k,json.loads(raw)
 except Exception as e:return k,{'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
 for k,a in ex.map(lambda kv:one(*kv),urls.items()):out[k]=a
for k,a in out.items():
 if k=='zenodo':print(k,{x:a.get(x) for x in ['id','doi','metadata','files']})
 elif k=='tree':
  paths=[x['path'] for x in a.get('tree',[])];(Q/'tree_paths.txt').write_text('\n'.join(paths),encoding='utf-8')
  needed=['exp_crossdomain_audit.py','refit_grid_audit.py','exp_regate_v28.py','make_figures_patterns.py','outer_refit_v28.json','regate_v28.json']
  print(k,'sha',a.get('sha'),'paths',len(paths),'error',a.get('error'))
  for n in needed:print('REQUIRED',n,[p for p in paths if p.endswith(n)])
  print('paper files',[p for p in paths if 'Patterns' in p or 'CMPB' in p][:25])
 else:print(k,{x:a.get(x) for x in ['html_url','default_branch','tag_name','target_commitish','body','error']})
(Q/'archive_summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
