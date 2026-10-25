from pathlib import Path
p=Path('scripts/jbi_submission_build.py');s=p.read_text(encoding='utf-8')
s=s.replace("from docx.shared import Pt,Inches","from docx.shared import Pt,Inches,RGBColor")
s=s.replace("ps=['September 24, 2026'","ps=['September 25, 2026'")
s=s.replace(" doc.save(P/name)",""" for p in doc.paragraphs:
  if p.style.name=='Caption':
   for r in p.runs:r.font.color.rgb=RGBColor(0,0,0);r.font.size=Pt(10);r.italic=False;r.bold=False
  elif p.style.name=='Normal' and len(p.text)>180 and len(p.runs)==1:
   p.runs[0].bold=False
 if name=='Manuscript_JBI_中文.docx':
  rep(doc,'谱系内评分相关','标记集内基因相关');rep(doc,'谱系间','标记集间');rep(doc,'标记有效性','标记集一致性')
 doc.save(P/name)""")
s=s.replace(" supplementary(g)"," supplementary(g)")
p.write_text(s,encoding='utf-8')
