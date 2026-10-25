#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Stream data/e2_reseed as tar.gz over native ssh to the AutoDL server.

Uses OpenSSH key auth; tar | ssh byte-safe pipe via subprocess.
"""
import subprocess
import sys
import time
import os

KEY = os.path.join(os.environ["USERPROFILE"], ".ssh", "id_ed25519_autodl")
SSH = ["ssh", "-p", "47707", "-i", KEY,
       "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=NUL",
       "root@connect.weste.seetacloud.com"]
LOCAL_PARENT = r"g:\project4_cervix_multimodal\data"
REMOTE_DATA = "/root/autodl-tmp/project/project4_cervix_multimodal/data"

t0 = time.time()
cohorts = (os.environ.get("UPLOAD_COHORTS") or "e2_reseed").split()
print(f"uploading cohorts: {cohorts}", flush=True)
p1 = subprocess.Popen(
    ["tar", "-czf", "-", "-C", LOCAL_PARENT] + cohorts,
    stdout=subprocess.PIPE)
p2 = subprocess.Popen(
    SSH + [f"tar -xzf - -C {REMOTE_DATA}/ && echo EXTRACT-OK"],
    stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
p1.stdout.close()
out = p2.communicate()[0].decode("utf-8", "replace")
rc1 = p1.wait()
print(out)
print(f"tar rc={rc1} ssh rc={p2.returncode} elapsed={time.time()-t0:.0f}s")
sys.exit(1 if (rc1 or p2.returncode) else 0)
