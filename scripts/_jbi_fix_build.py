from pathlib import Path
p=Path('scripts/jbi_submission_build.py')
s=p.read_text(encoding='utf-8-sig')
s=s.replace("g.save=save_final","g._set_cell_margins=fixed_margins\n g.save=save_final")
s=s.replace("def main():","def fixed_margins(cell,top=80,start=100,bottom=80,end=100):\n pr=cell._tc.get_or_add_tcPr();mar=pr.find(qn('w:tcMar'))\n if mar is None:mar=OxmlElement('w:tcMar');pr.append(mar)\n for side,val in [('top',top),('start',start),('bottom',bottom),('end',end)]:\n  x=OxmlElement('w:'+side);x.set(qn('w:w'),str(val));x.set(qn('w:type'),'dxa');mar.append(x)\ndef main():")
p.write_text(s,encoding='utf-8')
