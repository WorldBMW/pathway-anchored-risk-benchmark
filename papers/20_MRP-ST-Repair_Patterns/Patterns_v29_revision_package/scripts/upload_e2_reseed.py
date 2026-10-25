#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Robust resumable SFTP uploader for data/e2_reseed (8 cohorts, 784 files).

v2 fix: create ALL remote dirs (including the base dir) via one `mkdir -p`
shell command on the server, instead of SFTP mkdir loops that silently
skipped the never-created base directory.
"""
import os
import sys
import time
import paramiko

HOST = "connect.weste.seetacloud.com"
PORT = 47707
USER = "root"
PW = "ia+pvdX2udI7"

LOCAL_BASE = r"g:\project4_cervix_multimodal\data\e2_reseed"
REMOTE_BASE = "/root/autodl-tmp/project/project4_cervix_multimodal/data/e2_reseed"
LOG = r"C:\Users\jm\AppData\Local\Temp\reseed_upload.log"


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def connect():
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(HOST, port=PORT, username=USER, password=PW, timeout=30)
    return cli


def remote_size(sftp, path):
    try:
        return sftp.stat(path).st_size
    except Exception:
        return None


def main():
    files = []
    for root, dirs, fs in os.walk(LOCAL_BASE):
        for f in fs:
            p = os.path.join(root, f)
            rel = os.path.relpath(p, LOCAL_BASE).replace("\\", "/")
            files.append((p, rel, os.path.getsize(p)))
    total_bytes = sum(t[2] for t in files)
    log(f"local files={len(files)} total={total_bytes/1e6:.1f}MB")

    cli = connect()
    # create ALL remote dirs (base included) via a single mkdir -p
    dirset = sorted({os.path.dirname(rel) for _, rel, _ in files if os.path.dirname(rel)})
    dirset.append("")  # force base dir creation
    mklist = " ".join(f"'{REMOTE_BASE}/{d}'" if d else f"'{REMOTE_BASE}'" for d in dirset)
    _, out, err = cli.exec_command(f"mkdir -p {mklist} && echo MKDIR-OK", timeout=120)
    print(out.read().decode("utf-8", "replace"), flush=True)
    e = err.read().decode("utf-8", "replace")
    if e.strip():
        log(f"mkdir stderr: {e[:500]}")
    sftp = cli.open_sftp()

    uploaded, skipped, failed = 0, 0, []
    t0 = time.time()
    done_bytes = 0
    for i, (p, rel, sz) in enumerate(files):
        rpath = f"{REMOTE_BASE}/{rel}"
        if remote_size(sftp, rpath) == sz:
            skipped += 1
            done_bytes += sz
            continue
        ok = False
        for attempt in range(3):
            try:
                sftp.put(p, rpath)
                if remote_size(sftp, rpath) == sz:
                    ok = True
                break
            except Exception as ex:
                log(f"  retry {attempt+1} {rel}: {type(ex).__name__}: {ex}")
                time.sleep(2)
                try:
                    sftp.close()
                    cli.close()
                except Exception:
                    pass
                time.sleep(1)
                try:
                    cli = connect()
                    sftp = cli.open_sftp()
                except Exception as ex2:
                    log(f"  reconnect failed: {ex2}")
        if ok:
            uploaded += 1
        else:
            failed.append(rel)
        done_bytes += sz
        if (i + 1) % 40 == 0 or i == len(files) - 1:
            rate = done_bytes / max(1, time.time() - t0) / 1e6
            log(f"progress {i+1}/{len(files)} up={uploaded} skip={skipped} "
                f"fail={len(failed)} {done_bytes/1e6:.0f}MB rate={rate:.1f}MB/s")

    n_remote = 0
    for root, dirs, fs in sftp.walk(REMOTE_BASE):
        n_remote += len(fs)
    log(f"DONE uploaded={uploaded} skipped={skipped} failed={len(failed)} "
        f"remote_files={n_remote}")
    if failed:
        log("FAILED LIST: " + "; ".join(failed[:20]))
        sys.exit(1)
    if n_remote != len(files):
        log(f"MISMATCH remote={n_remote} local={len(files)}")
        sys.exit(1)
    log("UPLOAD-VERIFIED-OK")
    sftp.close()
    cli.close()


if __name__ == "__main__":
    main()
