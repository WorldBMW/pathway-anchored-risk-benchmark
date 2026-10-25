from pathlib import Path
import json, urllib.request, urllib.parse, concurrent.futures, re

ROOT=Path(__file__).resolve().parents[1]
O=ROOT/'papers/13_CSBJ_v2_20261014'
QA=O/'submission_review';QA.mkdir(exist_ok=True)

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'CSBJ-manuscript-metadata-check/1.0','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=35) as r:return json.load(r)

def verify_refs():
    refs=json.loads((O/'evidence/references_verified.json').read_text(encoding='utf-8-sig'))
    def one(k,r):
        if not r.get('doi'):return k,{'status':'no_doi','record':r}
        try:
            d=fetch('https://api.crossref.org/works/'+urllib.parse.quote(r['doi'],safe=''))['message']
            authors=[]
            for a in d.get('author',[]):
                authors.append((a.get('given','')+' '+a.get('family','')).strip() or a.get('name',''))
            out=dict(r)
            out.update(title=d['title'][0],authors=authors or r['authors'],journal=d.get('container-title',[r['journal']])[0],volume=d.get('volume',r.get('volume','')),page=d.get('page',d.get('article-number',r.get('page',''))),doi=d['DOI'],url='https://doi.org/'+d['DOI'])
            date=d.get('published-print',d.get('published',d.get('published-online',{})))
            if date.get('date-parts'):out['year']=date['date-parts'][0][0]
            return k,{'status':'verified_crossref','original':r,'record':out,'metadata':d}
        except Exception as e:return k,{'status':'unverified','error':str(e),'record':r}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        audit=dict(pool.map(lambda kv:one(*kv),refs.items()))
    (QA/'reference_metadata_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    corrected={k:v['record'] for k,v in audit.items()}
    (QA/'references_corrected.json').write_text(json.dumps(corrected,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Reference checks:', {s:sum(v['status']==s for v in audit.values()) for s in set(v['status'] for v in audit.values())})
    for endpoint in ['https://api.github.com/repos/WorldBMW/pathway-anchored-risk-benchmark','https://api.github.com/repos/WorldBMW/pathway-anchored-risk-benchmark/releases/tags/v1.0']:
        try:
            d=fetch(endpoint);(QA/('github_release.json' if '/tags/' in endpoint else 'github_repository.json')).write_text(json.dumps(d,indent=2),encoding='utf-8');print(endpoint,d.get('html_url'))
        except Exception as e:print(endpoint,str(e));(QA/'github_access_error.txt').write_text(str(e),encoding='utf-8')

def retry_refs():
    import time
    a=json.loads((QA/'reference_metadata_audit.json').read_text(encoding='utf-8'))
    for k,v in a.items():
        if v['status']!='unverified':continue
        time.sleep(1)
        try:
            d=fetch('https://api.crossref.org/works/'+urllib.parse.quote(v['record']['doi'],safe=''))['message']
            r=dict(v['record']);r.update(title=d['title'][0],authors=[(x.get('given','')+' '+x.get('family','')).strip() or x.get('name','') for x in d.get('author',[])],journal=d['container-title'][0],volume=d.get('volume',r.get('volume','')),page=d.get('page',d.get('article-number',r.get('page',''))))
            v.update(status='verified_crossref',record=r,metadata=d);print(k,'verified',flush=True)
        except Exception as e:print(k,str(e),flush=True)
    (QA/'reference_metadata_audit.json').write_text(json.dumps(a,ensure_ascii=False,indent=2),encoding='utf-8')
    (QA/'references_corrected.json').write_text(json.dumps({k:v['record'] for k,v in a.items()},ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':
    import sys
    if '--retry' in sys.argv:retry_refs()
    else:verify_refs()
