from pathlib import Path
import json,numpy as np,sys
from scipy.stats import kendalltau
R=Path('G:/project4_cervix_multimodal');sys.path.insert(0,str(R/'scripts')); from probe_lodo import severity_of
for k in range(3):
 d=json.loads((R/f'results/results_NOALL_seed{k}.json').read_text()); z=np.load(R/f'results/fused_embs_NOALL_seed{k}.npz');print(k,'keys',z.files,'raw_tau',d.get('progression_monotonicity'))
 print('scorekeys',[x for x in z.files if 'score' in x or 'risk' in x]); print('registry tau',json.loads((R/'papers/12_CSBJ_audit_20261010/evidence/real_run_registry.json').read_text())['NOALL'][k]['tau']);print('sample counts',len(d['per_sample_score']),len(set(z['sample_ids'])))
 print('unknown',[(n,s) for n,s in d['per_sample_score'].items() if severity_of(n) is None])
N=json.loads((R/'results/paper_v10_numbers.json').read_text());print('agg',N['ablation']['NOALL']); print('all schema',[(v,[r['config'] for r in rr][:1]) for v,rr in json.loads((R/'papers/12_CSBJ_audit_20261010/evidence/real_run_registry.json').read_text()).items()])
