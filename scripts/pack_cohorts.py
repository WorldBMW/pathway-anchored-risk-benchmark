#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Pack MULTIPLE cohorts into one tar.gz (Python tarfile)."""
import os
import tarfile
import time

LOCAL_BASE = r"g:\project4_cervix_multimodal\data\e2_reseed"
cohorts = os.environ["PACK_COHORTS"].split()
out = os.path.join(os.environ["TEMP"], "reseed_rest.tar.gz")

t0 = time.time()
n = 0
with tarfile.open(out, "w:gz", compresslevel=1) as tf:
    for cohort in cohorts:
        for root, dirs, fs in os.walk(os.path.join(LOCAL_BASE, cohort)):
            for f in fs:
                p = os.path.join(root, f)
                arc = os.path.relpath(p, LOCAL_BASE).replace("\\", "/")
                tf.add(p, arcname=arc)
                n += 1
sz = os.path.getsize(out) / 1e6
print(f"packed {cohorts}: {n} files -> {out} ({sz:.0f}MB, {time.time()-t0:.0f}s)")
