import sys,json,urllib.request,urllib.parse,concurrent.futures,re
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
P=Path('papers/20_MRP-ST-Repair_Patterns')
t=(P/'MRP-ST-Repair_manuscript_Patterns_v27.md').read_text(encoding='utf-8')
refs=t.split('## REFERENCES')[1].strip().splitlines()
def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'AcademicManuscriptAudit/1.0'})
 with urllib.request.urlopen(req,timeout=25) as r:return r.status,r.read().decode('utf-8','replace')
def check(line):
 if not re.match(r'^\d+\.',line):return None
 n=int(line.split('.')[0]); doi=re.search(r'https://doi.org/(\S+)',line)
 try:
  url='https://api.crossref.org/works/'+doi[1].rstrip('.') if doi else 'https://api.crossref.org/works?rows=1&query.bibliographic='+urllib.parse.quote(line)
  status,raw=get(url); msg=json.loads(raw)['message']; a=msg if doi else msg['items'][0]
  return {'n':n,'input':line,'matched_title':a.get('title'),'DOI':a.get('DOI'),'author':a.get('author',[])[:2],'year':a.get('published',{}),'volume':a.get('volume'),'page':a.get('page'),'article_number':a.get('article-number'),'match_score':a.get('score'),'status':status}
 except Exception as e:return {'n':n,'input':line,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:out=list(filter(None,ex.map(check,refs)))
(P/'REFERENCE_LOOKUP_v27.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
for a in out:print(a['n'],a.get('matched_title',a.get('error')),a.get('DOI'),a.get('page'))
urls=['https://www.cell.com/patterns/information-for-authors','https://github.com/WorldBMW/cervix-st-multimodal','https://github.com/WorldBMW/cervix-st-multimodal/releases/tag/v1.0.0']
for i,u in enumerate(urls):
 try:
  status,txt=get(u);(P/f'official_source_{i}_v27.html').write_text(txt,encoding='utf-8');print('URL',u,status)
 except Exception as e:print('URL',u,str(e))
