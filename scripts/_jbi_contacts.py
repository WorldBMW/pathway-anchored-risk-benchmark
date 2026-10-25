from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
p=Path('papers/08_JBI/_qa_20260924/render')
for folder in p.iterdir():
 if not folder.is_dir():continue
 files=sorted(folder.glob('page-*.png'),key=lambda x:int(x.stem.split('-')[-1]))
 for k in range(0,len(files),4):
  canvas=Image.new('RGB',(1240,1660),'#aaaaaa');d=ImageDraw.Draw(canvas)
  for j,f in enumerate(files[k:k+4]):
   im=Image.open(f).convert('RGB');im.thumbnail((610,800));x=(j%2)*620;y=(j//2)*830;canvas.paste(im,(x,y+22));d.text((x+5,y+3),f'{folder.name} / {f.stem}',fill='black')
  canvas.save(p/f'{folder.name}_sheet{k//4+1}.jpg',quality=78)
