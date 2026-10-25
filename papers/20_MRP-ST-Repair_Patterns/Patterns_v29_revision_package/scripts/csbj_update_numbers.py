from pathlib import Path
import json,numpy as np
R=Path('G:/project4_cervix_multimodal'); O=R/'papers/12_CSBJ_audit_20261010';r=json.loads((O/'evidence/real_run_registry.json').read_text());a=[x['tau'] for x in r['NOALL']];mu=np.mean(a);sd=np.std(a,ddof=1);full=np.mean([x['tau'] for x in r['FULL']]);print(mu,sd,full-mu)
p=O/'Manuscript_CSBJ.md';s=p.read_text();s=s.replace('−0.105','−0.092').replace('D_joint 0.565','D_joint 0.551').replace('−0.092 (SD 0.084)','−0.092 (SD 0.095)');p.write_text(s,encoding='utf-8')
print('REF YEARS'); refs=json.loads((O/'evidence/references_verified.json').read_text());print([(k,d.get('year'),len(d.get('authors',[])),d.get('page')) for k,d in refs.items()]);print('GEO titles');print('\n'.join([l for p in (O/'evidence').glob('GSE*txt') for l in p.read_text().splitlines() if l.startswith('!Series_title') or l.startswith('!Series_pubmed_id')]))
