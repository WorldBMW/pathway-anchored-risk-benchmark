"""Freeze the real cervical n=5 label-free LODO probe result into a versioned
JSON artifact consumed by gen_cbm.py (every manuscript number from JSON)."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe_lodo import per_sample_embedding, lodo_probe  # noqa: E402

RES = Path(__file__).resolve().parent.parent / "results"
N_PERM = 10000

seeds = []
for s in (0, 1, 2):
    fp = RES / f"fused_embs_NOALL_seed{s}.npz"
    X, y, _ = per_sample_embedding(np.load(fp))
    tau_l, p_l, tau_i = lodo_probe(X, y, N_PERM)
    seeds.append({"seed": s, "tau_lodo": tau_l, "p": p_l,
                  "tau_insample_probe": tau_i, "n_donors": int(len(y))})

taus = np.array([r["tau_lodo"] for r in seeds])
ins = np.array([r["tau_insample_probe"] for r in seeds])
n_sig = int(sum(r["p"] < 0.05 for r in seeds))
_mean = float(taus.mean())
if _mean >= 0.35 and n_sig / len(seeds) >= 2 / 3:
    verdict = "supported"
elif abs(_mean) <= 0.15 and n_sig == 0:
    verdict = "unsupported"
else:
    verdict = "suggestive"
out = {
    "verdict": verdict,
    "metric": "LODO Kendall tau-b on real cervical NOALL (label-free) frozen embeddings",
    "n_donors": int(seeds[0]["n_donors"]),
    "n_perm": N_PERM,
    "lodo_mean": float(taus.mean()),
    "lodo_sd": float(taus.std(ddof=1)),
    "lodo_seeds": seeds,
    "insample_probe_mean": float(ins.mean()),
    "note": ("n=35 donors (31 normals: 30 ecto_Pxxx + N_HPV; 4 diseased: "
             "HSIL_HPV + CA_HPV_1/2 + cervical_cancer_1). Label-free NOALL "
             "encoder saw every donor's expression (never labels); the ridge "
             "severity probe is trained on 34 donors and tested on the held-out "
             "donor (standard linear-probe LODO, transductive in X only). "
             "Positive but weak and seed-unstable transfer (1/3 seeds p<0.05) "
             "grades as suggestive under the pre-registered rules — partial "
             "cross-donor disease-axis information survives complete label "
             "removal, in contrast to the identity-confounding simulation arm."),
}
json.dump(out, open(RES / "real_lodo_summary.json", "w", encoding="utf-8"), indent=2)
print(json.dumps(out, indent=2))
