import urllib.request

urls = {
    "HF_HOME": "https://huggingface.co",
    "HF_UNI": "https://huggingface.co/MahmoodLab/UNI/resolve/main/pytorch_model.bin",
    "HF_MIRROR": "https://hf-mirror.com",
}


def test(name, url):
    try:
        req = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            print(f"[OK ] {name}: status={r.status}")
    except Exception as e:
        print(f"[FAIL] {name}: {type(e).__name__}: {e}")


if __name__ == "__main__":
    for n, u in urls.items():
        test(n, u)
