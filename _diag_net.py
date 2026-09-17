import urllib.request, time

# 测试多个可能的加速镜像，找最快的下载路径
target = "GSM6360691_SCC.barcodes.tsv.gz"
candidates = [
    # AWS Open Data (ncbi GEO mirror)
    f"https://ncbi-geo.s3.amazonaws.com/geo/samples/GSM6360nnn/GSM6360691/suppl/{target}",
    f"https://s3.amazonaws.com/ncbi-geo/geo/samples/GSM6360nnn/GSM6360691/suppl/{target}",
    # 尝试带 CDN 前缀
    f"https://ftp.ncbi.nlm.nih.gov.geo.mirror.../{target}",  # placeholder, will fail fast
]

# 用真实可测的镜像
candidates = [
    ("AWS ncbi-geo", f"https://ncbi-geo.s3.amazonaws.com/geo/samples/GSM6360nnn/GSM6360691/suppl/{target}"),
    ("AWS ncbi-acc", f"https://ncbi-acc.s3.amazonaws.com/geo/samples/GSM6360nnn/GSM6360691/suppl/{target}"),
    ("original", f"https://ftp.ncbi.nlm.nih.gov/geo/samples/GSM6360nnn/GSM6360691/suppl/{target}"),
]

for name, u in candidates:
    t = time.time()
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        r = urllib.request.urlopen(req, timeout=20)
        d = r.read(300)
        print("OK  ", name, round(time.time()-t, 1), "s", len(d), "B")
    except Exception as e:
        print("FAIL", name, type(e).__name__, getattr(e, "code", ""), round(time.time()-t, 1), "s")
