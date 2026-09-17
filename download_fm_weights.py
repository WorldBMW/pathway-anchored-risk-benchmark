import requests, os, sys, time

PROXY = "http://127.0.0.1:7890"
TOKEN = os.environ.get("HF_TOKEN")
if not TOKEN:
    sys.exit("ERROR: set HF_TOKEN environment variable, see https://huggingface.co/settings/tokens")
proxies = {"http": PROXY, "https": PROXY}

URLS = {
    "UNI":  "https://huggingface.co/MahmoodLab/UNI/resolve/main/pytorch_model.bin",
    "UNI2": "https://huggingface.co/MahmoodLab/UNI2-h/resolve/main/pytorch_model.bin",
}

DEST = {
    "UNI":  "fm_cache/UNI/UNI-pytorch_model.bin",
    "UNI2": "fm_cache/UNI2/UNI2-pytorch_model.bin",
}

def download(name, url, dest):
    dest = os.path.abspath(dest)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0", "Authorization": f"Bearer {TOKEN}"}

    # probe
    r0 = requests.get(url, headers=headers, stream=True, proxies=proxies, timeout=30)
    total = int(r0.headers.get("content-length", 0) or 0)
    print(f"[{name}] status={r0.status_code} total_bytes={total}", flush=True)
    r0.close()
    if r0.status_code != 200:
        print(f"[{name}] FAILED {r0.status_code}", flush=True)
        return

    chunk = 1024 * 1024
    attempt = 0
    while True:
        start = os.path.getsize(dest) if os.path.exists(dest) else 0
        if total and start >= total:
            print(f"[{name}] already complete {start} bytes", flush=True)
            return
        h = dict(headers)
        if start > 0:
            h["Range"] = f"bytes={start}-"
        attempt += 1
        try:
            print(f"[{name}] attempt={attempt} resume_from={start}", flush=True)
            r = requests.get(url, headers=h, stream=True, proxies=proxies, timeout=60)
            if r.status_code in (200, 206):
                mode = "ab" if start > 0 and r.status_code == 206 else "wb"
                with open(dest, mode) as f:
                    n = start
                    for c in r.iter_content(chunk):
                        if not c:
                            continue
                        f.write(c)
                        n += len(c)
                        if n % (20 * 1024 * 1024) < chunk:
                            print(f"[{name}] MB {n // (1024*1024)} / {total//(1024*1024)}", flush=True)
                print(f"[{name}] DONE {n} bytes", flush=True)
                return
            else:
                print(f"[{name}] unexpected {r.status_code}", flush=True)
        except Exception as e:
            print(f"[{name}] error {e}, retry in 3s", flush=True)
            time.sleep(3)

if __name__ == "__main__":
    targets = sys.argv[1:] or ["UNI", "UNI2"]
    for t in targets:
        download(t, URLS[t], DEST[t])
