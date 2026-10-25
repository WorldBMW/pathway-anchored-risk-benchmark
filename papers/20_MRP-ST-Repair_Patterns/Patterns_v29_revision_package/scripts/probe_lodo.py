#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Leave-one-donor-out (LODO) linear-probe audit on the FROZEN fused embeddings.

Why this exists
---------------
The in-sample scalar `score` head has NO disease orientation once supervision is
removed (NOALL trains it only with neighbour-smoothness + a variance floor), so
its in-sample Kendall tau collapses to ~0 *regardless of whether a real disease
program exists in the embedding*. An unoriented latent cannot be read out by
inspecting an arbitrary head direction.

The correct "does the representation contain a transferable disease signal?"
test is representation probing: freeze the embedding, fit a simple linear
severity probe on a set of donors, and evaluate on donors the probe NEVER saw.

  - Real shared program (sim group_A) -> high LODO tau on NOSUP/NOALL embedding
  - Donor/batch-confounded artifact (group_C) -> high in-sample, LODO ~ 0
  - Weak shared program (group_B) -> borderline, seed-unstable LODO

Runs entirely offline on the dumped fused_embs_SIM_*.npz files — no retraining.

Usage:
    python scripts/probe_lodo.py [n_perm]
"""
import sys
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
GROUPS = ["group_A", "group_B", "group_C"]
VARIANTS = ["FULL", "NOIMAGE", "NOHPV", "NONEIGH", "NOPROG", "NOSUP", "NOALL"]


def severity_of(sample_name: str):
    n = str(sample_name).upper()
    # Prostate cohort (GSE278936): BPH -> 0 (benign), all others -> 1 (tumour).
    if n.startswith("BPH_"):
        return 0
    if n.startswith(("CRPC_", "MET_", "TRNA_", "PC_", "PRAD_")):
        return 1
    # E4 external HNSCC cohort (GSE268014): HPV status is the target label.
    # HPVp_Pxxxx -> 1 (HPV+), HPVn_Pxxxx -> 0 (HPV-). Binary 0/1 keeps the
    # same tau/LDI machinery (Kendall tau-b handles binary y).
    if n.startswith("HPVP_"):
        return 1
    if n.startswith("HPVN_"):
        return 0
    # normal ectocervix donors are named ecto_Pxxx in the Visium cohort;
    # N_HPV is the HPV+ normal donor. Both are severity 0.
    if n.startswith("N_") or n.startswith("ECTO_") or "NORMAL" in n:
        return 0
    if "HSIL" in n or "CIN" in n or "DYS" in n:
        return 1
    if (n.startswith("CA_") or "CANCER" in n or "TUMOR" in n
            or n.startswith("CERVICAL_CANCER")):
        return 2
    return None


def kendall_tau(a, b):
    """Kendall tau-b for possibly-tied vectors (dependency-free)."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    n = len(a)
    conc = disc = tx = ty = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            da, db = a[j] - a[i], b[j] - b[i]
            if da == 0 and db == 0:
                continue
            if da == 0:
                tx += 1
            elif db == 0:
                ty += 1
            elif da * db > 0:
                conc += 1
            else:
                disc += 1
    denom = np.sqrt((conc + disc + tx) * (conc + disc + ty))
    return 0.0 if denom == 0 else (conc - disc) / denom


def per_sample_embedding(npz):
    """Mean-pool spot embeddings to one vector per donor; attach severity."""
    fused = npz["fused"]
    sids = npz["sample_ids"].astype(str)
    names, inv = np.unique(sids, return_inverse=True)
    d = fused.shape[1]
    vecs, sevs, kept = [], [], []
    for k, nm in enumerate(names):
        sev = severity_of(nm)
        if sev is None:
            continue
        vecs.append(fused[inv == k].mean(axis=0))
        sevs.append(sev)
        kept.append(nm)
    X = np.vstack(vecs)
    y = np.array(sevs, float)
    return X, y, kept


def ridge_predict(Xtr, ytr, Xte, alpha=1.0):
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-8
    Ztr, Zte = (Xtr - mu) / sd, (Xte - mu) / sd
    p = Ztr.shape[1]
    A = Ztr.T @ Ztr + alpha * np.eye(p)
    w = np.linalg.solve(A, Ztr.T @ ytr)
    return Zte @ w


def lodo_probe(X, y, n_perm=2000):
    n = len(y)
    pred = np.zeros(n)
    for i in range(n):
        tr = np.arange(n) != i
        pred[i] = ridge_predict(X[tr], y[tr], X[i:i + 1])[0]
    tau_obs = kendall_tau(pred, y)
    rng = np.random.default_rng(0)
    n_ge = 0
    for _ in range(n_perm):
        if kendall_tau(pred, rng.permutation(y)) >= tau_obs:
            n_ge += 1
    p_perm = (n_ge + 1) / (n_perm + 1)
    # in-sample contrast (fit all, predict all): reveals the memorization gap
    pred_in = np.array([ridge_predict(X, y, X[i:i + 1])[0] for i in range(n)])
    tau_in = kendall_tau(pred_in, y)
    return tau_obs, p_perm, tau_in


def main():
    n_perm = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    print(f"LODO linear-probe audit on frozen fused embeddings (n_perm={n_perm})\n")
    for g in GROUPS:
        print(f"===== {g} =====")
        print(f"  {'variant':8s} {'seed':>4s}  {'tau_LODO':>9s}  {'p_perm':>8s}  "
              f"{'tau_in-sample':>13s}  {'gap':>6s}")
        for v in VARIANTS:
            for s in range(3):
                fp = RESULTS / f"fused_embs_SIM_{g}_{v}_seed{s}.npz"
                if not fp.exists():
                    continue
                try:
                    X, y, _ = per_sample_embedding(np.load(fp))
                except Exception as e:
                    print(f"  {v:8s} {s:4d}  [error] {e}")
                    continue
                if len(np.unique(y)) < 2:
                    print(f"  {v:8s} {s:4d}  only one severity level")
                    continue
                tau_l, p_l, tau_i = lodo_probe(X, y, n_perm)
                print(f"  {v:8s} {s:4d}  {tau_l:+9.3f}  {p_l:8.4f}  "
                      f"{tau_i:+13.3f}  {tau_i - tau_l:6.3f}")
        print()


if __name__ == "__main__":
    main()
