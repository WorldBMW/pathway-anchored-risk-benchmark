# -*- coding: utf-8 -*-
"""分块续传下载 GEO supplementary tar 包（NCBI 限速环境下可用）
用法:
  python3 scripts/download_geo_tar.py --gse GSE280313
  python3 scripts/download_geo_tar.py --gse GSE280311 --outdir data/st_visium --chunk 2097152
支持断点续传：中断后重跑同一命令会自动接着下（.part 文件）。
"""
import argparse
import os
import sys
import time
import urllib.request

FTP = "https://ftp.ncbi.nlm.nih.gov/geo/series/{dir}/{gse}/suppl/{gse}_RAW.tar"


def gse_dir(gse):
    # GSE280313 -> GSE280nnn
    return gse[: len(gse) - 3] + "nnn"


def human(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}TB"


def get_total(url, retries=5, wait=3.0):
    """稳健获取远端总字节数：先 HEAD，失败再用 Range bytes=0-0 读 Content-Range。
    返回 int 或 None（都失败）。返回 None 时调用方必须拒绝无界下载，否则会反复
    把整个文件 append 进 .part 导致损坏。"""
    for _ in range(retries):
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=30) as r:
                cl = r.headers.get("Content-Length")
                if cl:
                    return int(cl)
                cr = r.headers.get("Content-Range")
                if cr and "/" in cr:
                    return int(cr.split("/")[-1])
        except Exception:
            time.sleep(wait)
    for _ in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Range": "bytes=0-0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                cr = r.headers.get("Content-Range")
                if cr and "/" in cr:
                    return int(cr.split("/")[-1])
        except Exception:
            time.sleep(wait)
    return None



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gse", default="GSE280313")
    ap.add_argument("--outdir", default="data/st_visium")
    ap.add_argument("--prefix", default="geo_crc")
    ap.add_argument("--chunk", type=int, default=1048576, help="分块字节数，默认 1MB")
    ap.add_argument("--unpack", action="store_true", help="下载完成后解 tar")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--file", default="",
                    help="suppl 下的具体文件名；留空则用 {GSE}_RAW.tar")
    ap.add_argument("--gunzip", action="store_true",
                    help="下载后若是 .gz 则解压（非 tar）")
    ap.add_argument("--retries", type=int, default=60,
                    help="单块失败后的最大重试次数（穿越 SSL EOF 等瞬时错误）")
    ap.add_argument("--retry-wait", type=float, default=3.0,
                    help="重试前等待秒数")
    args = ap.parse_args()

    gse = args.gse
    fname = args.file or f"{gse}_RAW.tar"
    url = "https://ftp.ncbi.nlm.nih.gov/geo/series/{d}/{g}/suppl/{f}".format(
        d=gse_dir(gse), g=gse, f=fname)
    out_dir = os.path.join(args.outdir, f"{args.prefix}_{gse}")
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, fname)
    part = dst + ".part"

    # 目标大小（稳健获取，HEAD 失败回退 Range 探测）
    total = get_total(url)
    if total:
        print(f"[INFO] 远端大小: {human(total)}")
    else:
        print(f"[WARN] 无法获取远端总大小，拒绝无界下载（避免损坏）")
        print(f"[HINT] 重跑同一命令通常可拿到大小（NCBI 偶发限频）")
        return 1

    if args.dry:
        print(f"[DRY] URL: {url}\n[DRY] 目标: {dst}\n[DRY] 大小: {human(total or 0)}")
        return 0

    done = os.path.getsize(part) if os.path.exists(part) else 0
    if os.path.exists(dst) and (total is None or os.path.getsize(dst) == total):
        print(f"[SKIP] 已存在且完整: {dst} ({human(os.path.getsize(dst))})")
    else:
        if done:
            print(f"[RESUME] 断点续传，已下 {human(done)} / {human(total or 0)}")
        t0 = time.time()
        attempt = 0
        with open(part, "ab") as f:
            while True:
                if total and done >= total:
                    break
                end = min(done + args.chunk - 1, total - 1) if total else done + args.chunk - 1
                req = urllib.request.Request(url, headers={"Range": f"bytes={done}-{end}"})
                # 自动重试：穿越 SSL EOF / 连接重置等瞬时错误，单块最多重试 --retries 次
                data = b""
                while True:
                    try:
                        with urllib.request.urlopen(req, timeout=120) as r:
                            data = r.read()
                        break
                    except Exception as e:
                        attempt += 1
                        if attempt > args.retries:
                            print(f"\n[ERR] 分块重试耗尽 @ {human(done)}: {e}")
                            print("[HINT] 重跑同一命令即可续传")
                            return 1
                        print(f"\r  重试 {attempt}/{args.retries} @ {human(done)}: {e}",
                              end="", flush=True)
                        time.sleep(args.retry_wait)
                        # 退避后刷新请求（Range 偏移已随 done 更新）
                        req = urllib.request.Request(
                            url, headers={"Range": f"bytes={done}-{end}"})
                if not data:
                    break
                f.write(data)
                f.flush()
                done += len(data)
                pct = f"{done/total*100:.1f}%" if total else ""
                spd = done / (time.time() - t0) / 1024
                print(f"\r  已下 {human(done)} / {human(total or 0)}  {pct}  {spd:.0f} KB/s",
                      end="", flush=True)
                if total and len(data) < args.chunk and done >= total:
                    break
        print()
        os.replace(part, dst)
        print(f"[OK] 下载完成: {dst} ({human(os.path.getsize(dst))}) 用时 {time.time()-t0:.0f}s")

    if args.gunzip and dst.endswith(".gz"):
        import gzip as _gz
        out = dst[:-3]
        if not os.path.exists(out):
            print("[INFO] gunzip 解压中（大文件请耐心）...")
            with _gz.open(dst, "rb") as f, open(out, "wb") as o:
                shutil.copyfileobj(f, o)
        os.remove(dst)
        print(f"[OK] 已解压: {out} ({human(os.path.getsize(out))})")

    if args.unpack:
        import tarfile
        print("[INFO] 解压中...")
        with tarfile.open(dst) as t:
            t.extractall(out_dir)
        print(f"[OK] 已解压到 {out_dir}")
        for f in sorted(os.listdir(out_dir)):
            p = os.path.join(out_dir, f)
            if os.path.isfile(p):
                print(f"   {f}  {human(os.path.getsize(p))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
