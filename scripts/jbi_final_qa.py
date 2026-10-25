from pathlib import Path
import sys,json,re,zipfile
sys.path.insert(0,str(Path.cwd()))
from docx import Document
from PIL import Image
import pymupdf as fitz
from scripts.audit_jbi_package import manuscript_audit,docx_audit,highlights_audit,word_count,paragraphs_between
P=Path('papers/08_JBI');out={'manuscript':manuscript_audit(P/'Manuscript_JBI.docx'),'highlights':highlights_audit(P/'Highlights_JBI.docx')}
for f in P.glob('*.docx'):
 if f.name not in ['Manuscript_JBI.docx','Manuscript_JBI_中文.docx','CoverLetter_JBI.docx','Highlights_JBI.docx','Supplementary_Information_JBI.docx']:continue
 d=Document(f);x=docx_audit(f)
 with zipfile.ZipFile(f) as z:
  xml=z.read('word/document.xml').decode();x['tracked_changes_xml']=len(re.findall(r'<w:(?:ins|del)\b',xml));x['comments_xml']=len(re.findall(r'<w:commentRangeStart\b',xml))
 x['bad_tokens']=[t for t in ['吉美','标志物有效性','within-lineage score correlation','187–220','Commun. Biol. 9 (2025)','W. Yang, et al., ST-Align'] if t in '\n'.join(p.text for p in d.paragraphs)]
 assert not x['tracked_changes_xml'] and not x['comments_xml'] and not x['bad_tokens'],(f,x)
 out[f.name]=x
 if f.name=='Manuscript_JBI.docx':
  out['manuscript']['body_words_excluding_abstract_references_tables']=word_count(paragraphs_between(d,'1. Introduction','Declarations'))
  x['embedded_image_matches']=[]
  import hashlib
  with zipfile.ZipFile(f) as z:
   hs={hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('word/media/')}
  for name in ['Fig1_Framework','Fig2_risk_violin','Fig3_ablation_multiseed','Fig4_biology_correlation','Fig5_external_transfer']:
   same=hashlib.sha256((P/'Figures'/(name+'.png')).read_bytes()).hexdigest() in hs;x['embedded_image_matches'].append([name,same]);assert same
out['figures']={}
for f in (P/'Figures').glob('*.tiff'):
 im=Image.open(f);out['figures'][f.name]={'pixels':list(im.size),'dpi':[float(a) for a in im.info['dpi']]};assert min(im.info['dpi'])>=500
for f in (P/'Figures').glob('*.pdf'):
 if 'schematic' in f.name:continue
 d=fitz.open(f);out['figures'].setdefault(f.stem,{})['pdf_text_characters']=len(d[0].get_text());assert len(d[0].get_text())>50
im=Image.open(P/'GraphicalAbstract_JBI.tiff');out['graphical_abstract']={'pixels':list(im.size),'dpi':[float(a) for a in im.info['dpi']]};assert im.width>=1328 and im.height>=531
(P/'_qa_20260924/final_structure_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out['manuscript'],indent=2));print('All five manuscript images match the final PNG files. PDF text is vector; TIFFs >=500 dpi. No tracked edits/comments/stale known errors.')
