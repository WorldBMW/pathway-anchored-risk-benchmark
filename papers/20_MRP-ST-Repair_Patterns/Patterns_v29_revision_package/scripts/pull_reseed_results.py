#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Pull the 8 reseed boundary JSONs from the AutoDL server into local results/.
Usage: python scripts/pull_reseed_results.py
"""
import os
import sys
import time
import paramiko

HOST = "connect.weste.seetacloud.com"
PORT = 47707
USER = "root"
PW = "ia+pvdX2udI7"

REMOTE_DIR = "/root/autodl-tmp/project/project4_cervix_multimodal/results"
LOCAL_DIR = r"g:\project4_cervix_multimodal\results"
TAGS = ["e2r_n16_s3", "e2r_n16_s4", "e2r_n32_s3", "e2r_n32_s4",
        "e2br_n16_s3", "e2br_n16_s4", "e2br_n32_s3", "e2br_n32_s4"]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(HOST, port=PORT, username=USER, password=PW, timeout=30)
    sftp = cli.open_sftp()
    got, missing = [], []
    for tag in TAGS:
        rpath = f"{REMOTE_DIR}/{tag}.json"
        lpath = os.path.join(LOCAL_DIR, f"{tag}.json")
        try:
            sftp.get(rpath, lpath)
            sz = os.path.getsize(lpath)
            got.append((tag, sz))
            log(f"pulled {tag}.json ({sz/1e3:.0f} KB)")
        except FileNotFoundError:
            missing.append(tag)
        except Exception as e:
            log(f"ERROR {tag}: {type(e).__name__}: {e}")
            missing.append(tag)
    sftp.close()
    cli.close()
    log(f"got={len(got)} missing={len(missing)} {missing if missing else ''}")
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
