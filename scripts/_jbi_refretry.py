import json,re,urllib.request,urllib.parse
from pathlib import Path
p=Path('papers/08_JBI/_qa_20260924/reference_verification.json');data=json.loads(p.read_text(encoding='utf-8'))
for r in data:
 if r['status']=='resolved' or 'doi' not in r or 'arxiv' in r.get('doi','').lower():continue
 try:
  req=urllib.request.Request('https://api.crossref.org/works/'+urllib.parse.quote(r['doi'],safe=''),headers={'User-Agent':'ManuscriptReferenceAudit/1.0'})
  with urllib.request.urlopen(req,timeout=18) as resp:x=json.load(resp)['message']
  r.update(status='resolved',title=x.get('title'),published=x.get('published'),volume=x.get('volume'),page=x.get('page'),article_number=x.get('article-number'))
 except Exception as e:r['status']=str(e)
 print(r['doi'],r['status'],r.get('title'),flush=True)
p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
