from pathlib import Path
import sys,re,json
from docx import Document
from docx.shared import RGBColor
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph
sys.stdout.reconfigure(encoding='utf-8')
P=Path('papers/20_MRP-ST-Repair_Patterns');Q=Path('.qa/patterns_v29')
data=json.loads(Path('results/outer_refit_v29.json').read_text(encoding='utf-8'))
a,b=data['runs'];assert a['lam']==0 and b['lam']==2
new='**Corrected train-only preprocessing check.** We repeated the HAR encoder-refit exercise at seed 0 with all clipping percentiles, centering and scaling fitted solely on outer-training observations (30 epochs, 30 held-out subjects; 299 audit units). Pooled out-of-fold Kendall τ was '+f"{a['pooled_tau_frozen']:.4f} frozen versus {a['pooled_tau_outer']:.4f} outer-refitted at λ = 0, and {b['pooled_tau_frozen']:.4f} versus {b['pooled_tau_outer']:.4f} at λ = 2. Frozen-minus-outer differences were {a['pooled_tau_frozen']-a['pooled_tau_outer']:+.4f} and {b['pooled_tau_frozen']-b['pooled_tau_outer']:+.4f}."+' The corresponding mean-within-fold τ values are reported separately in the result record. This fixes the preprocessing leakage and estimand mismatch for this one-seed HAR check; it is not an equivalence test, remains dependent on nominal class coding, and does not validate the transcriptomic pipelines. Full fold records are provided in outer_refit_v29.json.'
src=P/'MRP-ST-Repair_manuscript_Patterns_v29.md';t=src.read_text(encoding='utf-8')
st=t.index('**Outer-loop encoder refitting.**');en=t.index('\n\n',st)
assert '**Corrected train-only preprocessing check.**' not in t
t=t[:en]+'\n\n'+new+t[en:]
ai='During manuscript preparation, AI-assisted tools were used for language editing and code review. OpenAI Codex also assisted in drafting and checking analysis scripts. Numerical results were obtained by executing the documented scripts rather than generated as narrative values. Script versions, inputs and outputs are supplied for independent verification. The authors remain responsible for the code, scientific claims and submitted content.'
st=t.index('## DECLARATION OF GENERATIVE AI USE');en=t.index('## SUPPLEMENTAL INFORMATION',st)
t=t[:st]+'## DECLARATION OF GENERATIVE AI USE\n\n'+ai+'\n\n'+t[en:]
t=t.replace('| Cervical (donor) |','| Cervical (assumed name-based groups) |')
src.write_text(t,encoding='utf-8')
d=Document(P/'Manuscript_Patterns_v29.docx')
hits=[p for p in d.paragraphs if p.text.startswith('Outer-loop encoder refitting.')];assert len(hits)==1
np=OxmlElement('w:p');hits[0]._p.addnext(np);p=Paragraph(np,hits[0]._parent)
p.add_run('Corrected train-only preprocessing check.').bold=True;p.add_run(' '+new.split('**',2)[-1].strip())
ps=d.paragraphs;idx=[i for i,p in enumerate(ps) if p.text=='DECLARATION OF GENERATIVE AI USE'][0]
for p in ps[idx+1:]:
 if p.text.strip():
  assert 'SUPPLEMENTAL' not in p.text;p.text=ai;break
for tab in d.tables:
 for row in tab.rows:
  for c in row.cells:
   if c.text=='Cervical (donor)':c.text='Cervical (assumed name-based groups)'
for p in d.paragraphs:
 if p.style.name=='Title' or 'Heading' in p.style.name:
  for r in p.runs:r.font.color.rgb=RGBColor(0,0,0)
d.save(P/'Manuscript_Patterns_v29.docx')
s=Document(P/'Supplemental_Information_Patterns_v29.docx');s.add_heading('Corrected HAR outer-refit check',1)
s.add_paragraph(new.replace('**',''))
tab=s.add_table(rows=1,cols=5);tab.style='Table Grid'
for c,v in zip(tab.rows[0].cells,['Dose','Pooled τ frozen','Pooled τ outer','Mean-fold τ frozen','Mean-fold τ outer']):c.text=v
for r in data['runs']:
 vals=[str(r['lam'])]+[f'{r[k]:.4f}' for k in ['pooled_tau_frozen','pooled_tau_outer','mean_fold_tau_frozen','mean_fold_tau_outer']]
 for c,v in zip(tab.add_row().cells,vals):c.text=v
s.save(P/'Supplemental_Information_Patterns_v29.docx')
evidence={'doi':'10.5281/zenodo.23640979','zenodo_zip_md5':'d16a52ef2d86d837a5191dce6d89e33c','git_commit':'73ad0f1710953651c43055afc693f7a18ce93c6f','missing_from_frozen_public_archive':['exp_crossdomain_audit.py','refit_grid_audit.py','exp_regate_v28.py','make_figures_patterns.py'],'corrected_outer_refit':data}
(P/'AUDIT_v29_evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
print('Added corrected outer result, repaired AI disclosure, kept five embedded figures')
