from pathlib import Path
import json,numpy as np,sys
from scipy.stats import kendalltau
R=Path('G:/project4_cervix_multimodal'); E=R/'papers/12_CSBJ_audit_20261010/evidence';sys.path.insert(0,str(R/'scripts'));from probe_lodo import severity_of
reg=json.loads((E/'real_run_registry.json').read_text())
for v,rr in reg.items():
 for r in rr:
  f=R/f'results/fused_embs_{v}_seed{r["seed"]}.npz'
  if not f.exists():continue
  with np.load(f) as z:
   sid=z['sample_ids'].astype(str);s=z['scores'].astype(np.float64); names=np.unique(sid);vals=[float(s[sid==n].mean()) for n in names];ys=[severity_of(n) for n in names]
  r['tau_json']=r['tau'];r['tau']=float(kendalltau(vals,ys).statistic);r['score_source']=f.name;r['sample_scores']=dict(zip(names,vals))
 print(v,[r['tau'] for r in rr])
(E/'real_run_registry.json').write_text(json.dumps(reg,indent=2),encoding='utf-8')
p=R/'papers/12_CSBJ_audit_20261010/Manuscript_CSBJ.md';s=p.read_text(encoding='utf-8');s=s.replace('The current loader can mix samples within a batch, so this term is not treated as a verified within-section biological interaction graph. This implementation is the object being audited, not a validated spatial mechanism.','The current sampler keeps each batch within a section. Its six-neighbor target is batch-local rather than a fixed whole-section graph; the implementation is an object of the audit, not a validated biological interaction mechanism.');s=s.replace('and neighborhood targets that do not guarantee within-section membership','and batch-local rather than whole-section neighborhood targets');p.write_text(s,encoding='utf-8')
