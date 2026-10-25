from pathlib import Path
import json,sys
import fitz
from PIL import Image,ImageDraw
sys.stdout.reconfigure(encoding='utf-8')
Q=Path('.qa/patterns_v29/render');out=[]
for f in Q.glob('*.pdf'):
 d=fitz.open(f);folder=Q/f.stem;folder.mkdir(exist_ok=True);paths=[]
 for i,p in enumerate(d):
  outpng=folder/f'page-{i+1}.png';p.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(outpng);paths.append(outpng)
 for start in range(0,len(paths),6):
  sheet=Image.new('RGB',(1530,2200),'#ddd');draw=ImageDraw.Draw(sheet)
  for k,path in enumerate(paths[start:start+6]):
   im=Image.open(path).convert('RGB');im.thumbnail((750,690));x=(k%2)*765+(765-im.width)//2;y=(k//2)*730+25
   sheet.paste(im,(x,y));draw.text((x,y-18),f'{f.stem} page {start+k+1}',fill='black')
  sheet.save(Q/f'{f.stem}_contact_{start//6+1}.jpg')
 out.append({'file':f.name,'pages':len(d)})
print(json.dumps(out,indent=2));(Q/'render_summary.json').write_text(json.dumps(out,indent=2))
