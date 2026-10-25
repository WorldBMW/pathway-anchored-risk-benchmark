#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Size-verify all 784 e2_reseed files server-side against local.

Prints MISMATCH list (missing or size-diff). Exit 0 iff all match.
"""
import os
import sys
import paramiko

HOST = "connect.weste.seetacloud.com"
PORT = 47707
USER = "root"
PW = "ia+pvdX2udI7"

LOCAL_BASE = r"g:\project4_cervix_multimodal\data\e2_reseed"
REMOTE_BASE = "/root/autodl-tmp/project/project4_cervix_multimodal/data/e2_reseed"


def main():
    files = []
    for root, dirs, fs in os.walk(LOCAL_BASE):
        for f in fs:
            p = os.path.join(root, f)
            rel = os.path.relpath(p, LOCAL_BASE).replace("\\", "/")
            files.append((rel, os.path.getsize(p)))
    print(f"local files: {len(files)}")

    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(HOST, port=PORT, username=USER, password=PW, timeout=30)
    sftp = cli.open_sftp()

    bad = []
    for i, (rel, sz) in enumerate(files):
        try:
            rs = sftp.stat(f"{REMOTE_BASE}/{rel}").st_size
        except FileNotFoundError:
            bad.append((rel, "MISSING"))
            continue
        except Exception as e:
            bad.append((rel, f"ERR:{type(e).__name__}"))
            continue
        if rs != sz:
            bad.append((rel, f"SIZE {rs} != {sz}"))
        if (i + 1) % 200 == 0:
            print(f"  checked {i+1}/{len(files)} bad={len(bad)}", flush=True)

    print(f"RESULT: {len(files)-len(bad)}/{len(files)} ok, {len(bad)} bad")
    for rel, why in bad[:30]:
        print(f"  BAD {rel}: {why}")
    sftp.close()
    cli.close()
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
