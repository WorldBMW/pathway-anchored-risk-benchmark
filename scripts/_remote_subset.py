#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Same-subset probe: our NOALL embeddings restricted to the exact benchmark
sample subsets, so Table 5 compares identical samples across all methods."""
import sys, json
from pathlib import Path
import numpy as np
PROJ = Path("/root/autodl-tmp/project/project4_cervix_multimodal")
sys.path.insert(0, str(PROJ / "scripts"))
from probe_lodo import per_sample_embedding, lodo_probe

RES = PROJ / "results"
bm = json.loads((RES / "st_methods_benchmark_v2.json").read_text(encoding="utf-8"))
N_PERM = 10000
out = {}
print("=== our NOALL probe on benchmark subsets (same samples as baselines) ===")
for g, gd in bm["groups"].items():
    names = sorted(gd["methods"]["SpaGCN"]["sample_risks"].keys())
    nset = set(names)
    taus, ps = [], []
    for ts in [0, 1, 2]:
        fps = sorted(RES.glob(f"fused_embs_SIM_{g}_NOALL_seed{ts}.npz"))
        if not fps:
            continue
        X, y, sn = per_sample_embedding(np.load(fps[0]))
        keep = [i for i, s in enumerate(sn) if s in nset]
        Xs, ys = X[keep], np.asarray(y)[keep]
        tau_l, p_l, tau_in = lodo_probe(Xs, ys, N_PERM)
        taus.append(tau_l); ps.append(p_l)
    if taus:
        m = float(np.mean(taus))
        out[g] = {"mean_tau": m, "taus": taus, "ps": ps, "n_samples": len(names)}
        print(f"{g:28s} ours-subset tau={m:+.3f} per-seed={[round(t,3) for t in taus]} ps={[round(p,4) for p in ps]}")
(RES / "v2_ours_subset_probe.json").write_text(json.dumps(out, indent=2))
print("saved results/v2_ours_subset_probe.json")