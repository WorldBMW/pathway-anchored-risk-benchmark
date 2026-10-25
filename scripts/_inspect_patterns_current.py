from pathlib import Path
import json
from docx import Document
P=Path('papers/20_MRP-ST-Repair_Patterns')
t=(P/'MRP-ST-Repair_manuscript_Patterns_v26.md').read_text(encoding='utf-8')
print(t[t.index('## DISCUSSION'):t.index('## EXPERIMENTAL PROCEDURES')])
print('\nDOCX TABLES')
d=Document(P/'Supplemental_Information_Patterns.docx')
for i,tab in enumerate(d.tables):
 print(i+1, len(tab.rows), [[c.text for c in r.cells] for r in tab.rows[:2]])
print('\nDATA SUMMARY')
for f in ['repair_e4_hnscc_stable.json','repair_prostate_gse278936_stable.json','unit_ladder_cervical.json']:
 a=json.loads((Path('results')/f).read_text(encoding='utf-8'))
 print(f,list(a), str(a.get('summary',{}))[:2400])
