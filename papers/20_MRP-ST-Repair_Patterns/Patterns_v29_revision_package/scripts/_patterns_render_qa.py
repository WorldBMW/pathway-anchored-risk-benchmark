from pathlib import Path
import sys,json
sys.stdout.reconfigure(encoding='utf-8')
import fitz
from PIL import Image,ImageOps,ImageDraw
Q=Path('.qa/patterns_v27_render');info=[]
for f in Q.glob('*.pdf'):
 d=fitz.open(f);folder=Q/f.stem;folder.mkdir(exist_ok=True)
 pages=[]
 for i,p in enumerate(d):
  pix=p.get_pixmap(matrix=fitz.Matrix(1.5,1.5));out=folder/f'page-{i+1}.png';pix.save(out)
  pages.append(out)
 for start in range(0,len(pages),6):
  sheet=Image.new('RGB',(1530,2200),'#dddddd');draw=ImageDraw.Draw(sheet)
  for k,impath in enumerate(pages[start:start+6]):
   im=Image.open(impath).convert('RGB');im.thumbnail((750,690));x=(k%2)*765+(765-im.width)//2;y=(k//2)*730+25
   sheet.paste(im,(x,y));draw.text((x,y-18),f'{f.stem} page {start+k+1}',fill='black')
  sheet.save(Q/f'{f.stem}_contact_{start//6+1}.jpg')
 info.append({'file':f.name,'pages':len(d),'text_characters':sum(len(p.get_text()) for p in d)})
print(json.dumps(info,indent=2));(Q/'render_summary.json').write_text(json.dumps(info,indent=2))
