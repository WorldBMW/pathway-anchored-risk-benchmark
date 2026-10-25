"""Independent checks of manuscript structure and archived cross-domain numbers."""
from pathlib import Path
import json,re,hashlib,sys
from docx import Document
sys.stdout.reconfigure(encoding='utf-8')
P=Path('papers/20_MRP-ST-Repair_Patterns');R=Path('results')
t=(P/'MRP-ST-Repair_manuscript_Patterns_v27.md').read_text(encoding='utf-8')
issues=[];checks=[]
def check(label,ok):
 checks.append({'check':label,'pass':bool(ok)})
 if not ok:issues.append(label)
refs=t.split('## REFERENCES')[1]
nums=[int(n) for n in re.findall(r'^(\d+)\. ',refs,re.M)]
check('43 consecutively numbered references',nums==list(range(1,44)))
cit=set()
for m in re.finditer(r'\[(\d+(?:[\s,–-]+\d+)*)\]',t.split('## REFERENCES')[0]):
 for token in m[1].split(','):
  a=re.split('[–-]',token.strip());cit.update(range(int(a[0]),int(a[-1])+1))
check('all numbered citations within bibliography',all(1<=n<=43 for n in cit))
sm=t.split('## SUMMARY')[1].split('**Keywords:')[0];ib=t.split('## IN BRIEF')[1].split('## SUMMARY')[0]
hl=re.findall(r'^\d+\. (.+)$',t.split('## HIGHLIGHTS')[1].split('## IN BRIEF')[0],re.M)
check('Summary at most 150 words',len(sm.split())<=150)
check('In brief at most 50 words',len(ib.split())<=50)
check('four highlights at most 85 characters',len(hl)==4 and max(map(len,hl))<=85)
d=Document(P/'Manuscript_Patterns.docx');check('five embedded main figures',len(d.inline_shapes)==5)
check('six main table objects',len(d.tables)==6)
raw=json.loads((R/'crossdomain_audit.json').read_text(encoding='utf-8-sig'))
for domain in ['HAR','GASDRIFT']:
 rows=[r for r in raw['runs'] if r['domain']==domain]
 check(domain+' has 15 recorded seed-dose cells',len(rows)==15)
 check(domain+' LDI matches implemented unit-level formula',all(abs(r['ldi']-(r['tau_loo']-.001)/r['sigma'])<1e-9 for r in rows))
 check(domain+' inflation matches paired holdout difference',all(abs(r['inflation']-(r['tau_loo']-r['tau_lgo']))<1e-9 for r in rows))
 check(domain+' dual gate matches recorded unit-level convention',all(r['dual_gate_pass']==bool(r['ldi']<1.645 and r['safety_tau_loo_kept']>=.7) for r in rows))
 check(domain+' zero of 12 dosed cells pass',sum(r['dual_gate_pass'] for r in rows if r['lam']>0)==0)
geo=json.loads((R/'within_group_label_geomx.json').read_text(encoding='utf-8'))
check('GeoMx risk inflation correctly assigned',abs(geo['summary']['risk']['inflation_base']-.3736447)<1e-6)
check('GeoMx cell-type inflation correctly assigned',abs(geo['summary']['cell_type']['inflation_base']-.0074872)<1e-6)
manifest=[]
for f in sorted((P/'figures').glob('*')):
 if f.is_file():manifest.append({'file':f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size})
out={'checks':checks,'failures':issues,'word_counts':{'summary':len(sm.split()),'in_brief':len(ib.split()),'main_Introduction_to_Discussion_including_tables':len(t.split('## INTRODUCTION')[1].split('## EXPERIMENTAL PROCEDURES')[0].split())},'highlight_characters':list(map(len,hl)),'uncited_reference_numbers':sorted(set(nums)-cit),'figures':manifest,'limitations':'Structure and specified archive arithmetic only. Not a full experiment rerun, group-null validation, complete source verification or journal acceptance certification.'}
(P/'AUDIT_v27_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
for c in checks:print('PASS' if c['pass'] else 'FAIL',c['check'])
print('Word counts',out['word_counts']);print('Uncited references',out['uncited_reference_numbers'])
if issues:raise SystemExit(1)
