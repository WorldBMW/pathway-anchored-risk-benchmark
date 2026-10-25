"""Download the GSE208654 cervical ST cohort (4 samples) from GEO FTP.

GSE208654 = Guo et al. 2023, Clin Transl Med — "Spatiotemporally deciphering
the unknown role of persistent HPV infection..." (Visium, GPL24676).

4 samples (normal -> HSIL -> cervical cancer progression):
  GSM6360689  N_HPV     normal cervix + HPV infection
  GSM6360690  HSIL_HPV  high-grade squamous intraepithelial lesion (pre-cancer)
  GSM6360691  CA_HPV    cervical cancer replicate 1 (SCC)
  GSM6360692  CA_HPV    cervical cancer replicate 2 (ADC)

Each GSM provides (10x Space Ranger output):
  - <prefix>.barcodes.tsv.gz   (spot barcodes)
  - <prefix>.features.tsv.gz   (gene features)
  - <prefix>.matrix.mtx.gz     (sparse expression matrix)
  - <prefix>.jpg.gz            (H&E tissue image, 47 MB)

NOTE: GEO does NOT include the Space Ranger `spatial/` folder
(tissue_positions_list.csv / scalefactors_json.json). Those are reconstructed
by `reconstruct_spatial.py` after download.

Usage:
  python scripts/download_cesc_st_geo.py --out data/st_visium/geo_cesc
"""
from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path

import urllib.request

SAMPLES = {
    "GSM6360689": "N_HPV",
    "GSM6360690": "HSIL_HPV",
    "GSM6360691": "CA_HPV_1",
    "GSM6360692": "CA_HPV_2",
}

# The tissue-prefix inside each GSM's suppl dir (seen in the FTP listing):
#   GSM6360691_SCC.{barcodes,features,matrix.mtx}.gz / GSM6360691_SCC.jpg.gz
#   GSM6360692_ADC.... etc. We list the known prefixes; if a prefix is unknown
#   we fall back to listing the GSM suppl dir and picking the unique prefix.
KNOWN_PREFIX = {
    "GSM6360689": None,   # N_HPV — prefix unknown, will auto-detect
    "GSM6360690": None,   # HSIL_HPV — auto-detect
    "GSM6360691": "SCC",
    "GSM6360692": "ADC",
}

EXT = ["barcodes.tsv.gz", "features.tsv.gz", "matrix.mtx.gz", "jpg.gz"]

FTP_BASE = "https://ftp.ncbi.nlm.nih.gov/geo/samples"

# ---- proxy auto-detect (added for users behind GFW — direct NCBI FTP is ~1KB/s) ----
PROXY_CANDIDATES = [
    "http://127.0.0.1:7890", "http://127.0.0.1:7891", "http://127.0.0.1:7897",
    "http://127.0.0.1:1080", "socks5://127.0.0.1:1080",
    "http://127.0.0.1:10808", "http://127.0.0.1:10809",
    "http://127.0.0.1:8080", "http://127.0.0.1:8888",
]


def _winreg_proxy() -> str | None:
    """Read Windows system proxy (WinINET) from the registry, e.g. 127.0.0.1:7890."""
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                           r"Software\Microsoft\Windows\CurrentVersion\Internet Settings")
        try:
            enabled, _ = winreg.QueryValueEx(k, "ProxyEnable")
        except Exception:
            enabled = 0
        server = None
        try:
            server, _ = winreg.QueryValueEx(k, "ProxyServer")
        except Exception:
            pass
        winreg.CloseKey(k)
        if enabled and server:
            s = str(server)
            if not s.startswith("http://") and not s.startswith("socks"):
                s = "http://" + s
            return s
    except Exception:
        pass
    return None


def _find_working_proxy() -> str | None:
    """Resolve proxy: (1) system env vars, (2) Windows registry, (3) common ports."""
    import os
    for env in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        v = os.environ.get(env)
        if v:
            return v
    reg = _winreg_proxy()
    if reg:
        return reg
    return None


_PROXY = _find_working_proxy()


def _opener():
    """Return a urllib opener that routes through _PROXY if set (using ProxyHandler)."""
    if _PROXY:
        return urllib.request.build_opener(urllib.request.ProxyHandler({"http": _PROXY, "https": _PROXY}))
    return urllib.request.build_opener()


def _open(url, timeout=90):
    return _opener().open(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=timeout)


def _list_dir(url: str, retries: int = 5) -> str:
    for i in range(retries):
        try:
            with _open(url, timeout=90) as r:
                return r.read().decode()
        except Exception as e:
            if i == retries - 1:
                raise
            print(f"  [retry {i+1}] {url}: {e}")
            time.sleep(3)


def _download(url: str, dst: Path, retries: int = 8, timeout: int = 300) -> bool:
    """Streaming download with chunked write, retry and resume. Returns True on success."""
    tmp = dst.with_suffix(dst.suffix + ".part")
    existing = tmp.stat().st_size if tmp.exists() else 0
    for i in range(retries):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            if existing > 0:
                headers["Range"] = f"bytes={existing}-"
            req = urllib.request.Request(url, headers=headers)
            with _opener().open(req, timeout=timeout) as r:
                # if server ignored Range, restart
                if existing > 0 and r.status != 206:
                    existing = 0
                    tmp.unlink(missing_ok=True)
                mode = "ab" if existing > 0 else "wb"
                with open(tmp, mode) as w:
                    while True:
                        chunk = r.read(1024 * 256)  # 256 KB
                        if not chunk:
                            break
                        w.write(chunk)
            tmp.replace(dst)
            return True
        except Exception as e:
            existing = tmp.stat().st_size if tmp.exists() else 0
            print(f"  [retry {i+1}/{retries}] {dst.name}: {e} (resume at {existing/1e6:.1f} MB)")
            time.sleep(5)
    return False


def _detect_prefix(gsm: str) -> str:
    """List the GSM suppl dir and extract the unique tissue prefix."""
    import re
    txt = _list_dir(f"{FTP_BASE}/GSM6360nnn/{gsm}/suppl/")
    files = re.findall(r'href="([^"]+\.(?:gz|tsv|csv|jpg|png|tif))"', txt)
    # e.g. GSM6360691_SCC.barcodes.tsv.gz -> prefix "GSM6360691_SCC"
    prefixes = set()
    for f in files:
        m = re.match(r"(GSM\d+_[A-Za-z0-9_]+)\.", f)
        if m:
            prefixes.add(m.group(1))
    # keep the longest prefix (tissue prefix usually has the extra suffix)
    if not prefixes:
        raise RuntimeError(f"no files detected for {gsm}: {files}")
    # strip the GSM id to get the tissue prefix, e.g. SCC / ADC / N_HPV
    pref = sorted(prefixes, key=len, reverse=True)[0]
    return pref


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/st_visium/geo_cesc")
    ap.add_argument("--gsm", nargs="*", help="subset of GSM ids to download")
    ap.add_argument("--proxy", default=None, help="force a specific proxy, e.g. http://127.0.0.1:7890")
    args = ap.parse_args()

    global _PROXY
    if args.proxy:
        _PROXY = args.proxy
    print(f"[proxy] using: {_PROXY or '(none, direct)'}")

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    gsms = args.gsm if args.gsm else list(SAMPLES)
    for gsm in gsms:
        tissue = SAMPLES[gsm]
        sample_dir = out_root / tissue
        sample_dir.mkdir(parents=True, exist_ok=True)

        prefix = KNOWN_PREFIX.get(gsm)
        if prefix is None:
            prefix = _detect_prefix(gsm)
        # full filename prefix = "<gsm>_<tissue>", e.g. "GSM6360691_SCC"
        full_prefix = prefix if prefix.startswith("GSM") else f"{gsm}_{prefix}"
        print(f"\n=== {gsm} ({tissue}) prefix={full_prefix} ===")

        for ext in EXT:
            fname = f"{full_prefix}.{ext}"
            url = f"{FTP_BASE}/GSM6360nnn/{gsm}/suppl/{fname}"
            dst = sample_dir / fname
            if dst.exists():
                print(f"  [skip] {fname} (exists)")
                continue
            print(f"  [get]  {fname} ...")
            ok = _download(url, dst)
            if ok:
                print(f"         -> {dst.stat().st_size/1e6:.1f} MB")
            else:
                print(f"  [FAIL] {fname}: giving up after retries")

    print("\nDone. Next: run reconstruct_spatial.py to build spatial/ for each sample.")


if __name__ == "__main__":
    main()
