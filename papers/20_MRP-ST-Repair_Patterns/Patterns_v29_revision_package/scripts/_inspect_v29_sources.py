from pathlib import Path
import json,sys,urllib.request,zipfile,hashlib
sys.stdout.reconfigure(encoding='utf-8')
Q=Path('.qa/patterns_v29');P=Path('papers/20_MRP-ST-Repair_Patterns')
a=json.loads((Q/'zenodo.json').read_text(encoding='utf-8'))
for f in a['files']:
 out=Q/Path(f['key']).name
 if not out.exists():
  req=urllib.request.Request(f['links']['self'],headers={'User-Agent':'ManuscriptArchiveAudit/1.0'})
  with urllib.request.urlopen(req,timeout=90) as r:out.write_bytes(r.read())
 print('DOWNLOADED',out.name,'md5',hashlib.md5(out.read_bytes()).hexdigest(),'expected',f['checksum'])
 if out.suffix=='.zip':
  z=zipfile.ZipFile(out);paths=z.namelist();(Q/'zenodo_zip_paths.txt').write_text('\n'.join(paths),encoding='utf-8');print('ZIP members',len(paths))
  for n in ['exp_regate_v28.py','exp_crossdomain_audit.py','make_figures_patterns.py','refit_grid_audit.py']:print(n,[p for p in paths if p.endswith(n)])
import fitz
d=fitz.open(Q/'Manuscript_Patterns.pdf');text='\n'.join(p.get_text() for p in d);(Q/'archived_manuscript_text.txt').write_text(text,encoding='utf-8')
print('ARCHIVED PDF',len(d),'pages','Remediation experiments' in text,'Table S18' in text)
t=(P/'MRP-ST-Repair_manuscript_Patterns_v28.md').read_text(encoding='utf-8')
s=t.index('### Remediation experiments');e=t.index('### Practical reporting',s)
print(t[s:e])
print('\nMETHODS NEW:')
for b in t.split('\n\n'):
 if b.startswith('**Group-preserving null') or b.startswith('**Symbols and interpretation') or 'outer-loop' in b or 'Code.**' in b:print(b+'\n')
