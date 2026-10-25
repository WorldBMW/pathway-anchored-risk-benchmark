from pathlib import Path
import fitz,json
P=Path('papers/08_JBI/_qa_20260924/render')
out={}
for f in P.glob('*.pdf'):
 d=fitz.open(f);out[f.name]={'pages':len(d),'text_chars':[]};p=P/f.stem;p.mkdir(exist_ok=True)
 for i,page in enumerate(d):
  page.get_pixmap(matrix=fitz.Matrix(1.25,1.25)).save(p/f'page-{i+1}.png')
  out[f.name]['text_chars'].append(len(page.get_text()))
  (p/f'page-{i+1}.txt').write_text(page.get_text(),encoding='utf-8')
 print(f.name,len(d),out[f.name]['text_chars'])
(P/'page_inventory.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
