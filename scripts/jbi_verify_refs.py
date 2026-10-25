from pathlib import Path
from docx import Document
import re,json,urllib.request,urllib.parse,concurrent.futures
P=Path('papers/08_JBI'); Q=P/'_qa_20260924'
d=Document(P/'Manuscript_JBI.docx')
refs=[p.text for p in d.paragraphs if re.match(r'^\[\d+\]',p.text)]
def check(s):
 m=re.search(r'https://doi.org/(\S+)',s)
 if not m:return {'reference':s,'status':'no_doi'}
 doi=m.group(1).rstrip('.')
 try:
  url='https://api.crossref.org/works/'+urllib.parse.quote(doi,safe='')
  data=json.load(urllib.request.urlopen(url,timeout=25))['message']
  return {'reference':s,'doi':doi,'status':'resolved','title':data.get('title'),'published':data.get('published'),'volume':data.get('volume'),'page':data.get('page'),'article_number':data.get('article-number'),'first_author':data.get('author',[{}])[0]}
 except Exception as e:return {'reference':s,'doi':doi,'status':str(e)}
out=list(concurrent.futures.ThreadPoolExecutor(6).map(check,refs))
(Q/'reference_verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
for x in out:print(x.get('doi'),x['status'],x.get('published'),x.get('volume'),x.get('page'),x.get('article_number'))
