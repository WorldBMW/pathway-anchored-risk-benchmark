import urllib.request, json

url = "https://www.ebi.ac.uk/biostudies/api/v1/search?query=GSE208654&pageSize=20"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
r = urllib.request.urlopen(req, timeout=30)
d = json.load(r)

for hit in d.get("hits", []):
    acc = hit.get("accession")
    title = hit.get("title", "")[:100]
    print("ACC:", acc, "|", title)

    # try to get files via the biostudies files API
    try:
        furl = f"https://www.ebi.ac.uk/biostudies/api/v1/studies/{acc}/info"
        fr = urllib.request.urlopen(urllib.request.Request(furl, headers={"User-Agent": "Mozilla/5.0"}), timeout=30)
        finfo = json.load(fr)
        subs = finfo.get("submissions", [])
        print("  submissions:", len(subs))
    except Exception as e:
        print("  info err:", e)
