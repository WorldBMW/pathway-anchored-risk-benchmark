from docx import Document
from pathlib import Path
from docx.oxml.ns import qn
import sys
sys.stdout.reconfigure(encoding='utf-8')
d=Document('papers/20_MRP-ST-Repair_Patterns/Manuscript_Patterns_v29.docx')
for ti,tab in enumerate(d.tables):
 if len(tab.columns)<9:continue
 print('TABLE',ti,'cols',len(tab.columns))
 e=tab._tbl
 for _ in range(4):
  e=e.getprevious()
  if e is None:break
  print(e.tag.split('}')[-1],''.join(e.itertext())[:250],bool(e.findall('.//'+qn('w:sectPr'))))
