from pathlib import Path
import json,sys,numpy as np,urllib.request
from scipy.stats import kendalltau
R=Path('G:/project4_cervix_multimodal');sys.path.insert(0,str(R/'scripts'))
from probe_lodo import severity_of
p=R/'scripts/csbj_prepare_evidence.py';s=p.read_text(encoding='utf-8-sig')
s=s.replace("with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex: rr=dict(ex.map(fetch,refs.items()))", "rr=json.loads((E/'references_verified.json').read_text(encoding='utf-8'))\nfor k,v in list(rr.items()):\n if 'error' in v: rr[k]=fetch((k,v['doi']))[1]")
s=s.replace("f=R/'results'/f'results_{v}_seed{s}.json'; d=json.loads(f.read_text(encoding='utf-8'))", "f=R/'results'/f'results_{v}_seed{s}.json'; d=json.loads(f.read_text(encoding='utf-8'))\n  prog=d.get('progression_monotonicity')\n  if not prog:\n   from scipy.stats import kendalltau\n   import sys\n   sys.path.insert(0,str(R/'scripts'))\n   from probe_lodo import severity_of\n   scores=d['per_sample_score']; pairs=[(score,severity_of(name)) for name,score in scores.items() if severity_of(name) is not None]\n   d['progression_monotonicity']={'kendall_tau':float(kendalltau(*zip(*pairs)).statistic)}")
p.write_text(s,encoding='utf-8')
