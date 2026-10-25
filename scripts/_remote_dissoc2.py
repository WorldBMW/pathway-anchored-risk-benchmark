#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Dissociation cell: LODO probe on CTRL FULL embeddings (label-trained encoder,
identity-confounded cohorts). Expect tau ~ 0 (no transfer) vs in-sample head tau ~ 0.5."""
import sys, json
from pathlib import Path
import numpy as np
PROJ = Path("/root/autodl-tmp/project/project4_cervix_multimodal")
sys.path.insert(0, str(PROJ / "scripts"))
from probe_lodo import per_sample_embedding, lodo_probe

RES = PROJ / "results"
N_PERM = 10000
out = {}
print("=== CTRL FULL-embedding LODO probe (dissociation) ===")
for g in ["20261006", "20261007", "20261008"]:
    for sz in ["", "_small"]:
        tag = f"group_C_g{g}_CTRL{sz}"
        taus, ps = [], []
        for ts in [0, 1, 2]:
            fps = sorted(RES.glob(f"fused_embs_SIM_{tag}_FULL_seed{ts}.npz"))
            if not fps:
                continue
            X, y, _ = per_sample_embedding(np.load(fps[0]))
            tau_l, p_l, tau_in = lodo_probe(X, y, N_PERM)
            taus.append(tau_l); ps.append(p_l)
        if taus:
            m = float(np.mean(taus))
            out[tag] = {"mean_tau_lodo": m, "taus": taus, "ps": ps}
            print(f"{tag:34s} FULL-emb LODO tau={m:+.3f} per-seed={[round(t,3) for t in taus]} min_p={min(ps):.4f}")
(RES / "v2_ctrl_full_probe.json").write_text(json.dumps(out, indent=2))
print("saved results/v2_ctrl_full_probe.json")