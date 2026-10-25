from pathlib import Path
p=Path('scripts/jbi_submission_build.py');s=p.read_text(encoding='utf-8').replace("elif p.style.name=='Normal' and len(p.text)>180 and len(p.runs)==1:","elif p.style.name=='Normal' and len(p.text)>45 and len(p.runs)==1 and (p.runs[0].font.size is None or p.runs[0].font.size.pt<=11):")
s=s.replace(" doc.save(P/name)",""" for t in doc.tables:
  if len(t.rows)<=9:
   for i,row in enumerate(t.rows):
    for c in row.cells:
     for p in c.paragraphs:p.paragraph_format.keep_with_next=i<len(t.rows)-1
 doc.save(P/name)""")
p.write_text(s,encoding='utf-8')
