from pathlib import Path
import fitz
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'papers/13_CSBJ_v2_20261014/submission_review'
for pdf in (QA/'word_render').glob('*.pdf'):
    dest=QA/'pages'/pdf.stem;dest.mkdir(parents=True,exist_ok=True)
    doc=fitz.open(pdf);pngs=[]
    for i,p in enumerate(doc):
        f=dest/f'page-{i+1}.png';p.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(f);pngs.append(f)
    for offset in range(0,len(pngs),4):
        sheet=Image.new('RGB',(1224,1644),'#dddddd');draw=ImageDraw.Draw(sheet)
        for j,f in enumerate(pngs[offset:offset+4]):
            im=Image.open(f);im.thumbnail((600,785));x=(j%2)*612;y=(j//2)*822;sheet.paste(im,(x,y+25));draw.text((x+10,y+5),str(offset+j+1),fill='black')
        sheet.save(dest/f'contact-{offset//4+1}.png')
    print(pdf.stem,len(doc),'pages',flush=True)
