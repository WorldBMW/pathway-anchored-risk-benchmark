import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe_lodo import per_sample_embedding, lodo_probe

R = Path(__file__).resolve().parent.parent / "results"
N_PERM = int(sys.argv[1]) if len(sys.argv) > 1 else 1000

KEY = {
    "group_A": [("FULL", "10-08 09:35"), ("NOALL", "10-08 10:10")],
    "group_B": [("FULL", None), ("NOSUP", None), ("NOALL", None)],
    "group_C": [("FULL", None), ("NOSUP", None), ("NOALL", None)],
}
import json
for g, vs in KEY.items():
    print(f"===== {g} (seed 0, n_perm={N_PERM}) =====")
    for v, _ in vs:
        fp = R / f"fused_embs_SIM_{g}_{v}_seed0.npz"
        if not fp.exists():
            print(f"  {v:8s}  (npz missing)")
            continue
        X, y, _ = per_sample_embedding(np.load(fp))
        tau_l, p_l, tau_i = lodo_probe(X, y, N_PERM)
        # in-head JSON tau for reference
        jf = R / f"results_SIM_{g}_{v}_seed0.json"
        jtau = None
        if jf.exists():
            d = json.load(open(jf, encoding="utf-8"))
            pm = d.get("progression_monotonicity") or {}
            jtau = pm.get("kendall_tau")
        js = f"{jtau:+.3f}" if jtau is not None else "null"
        print(f"  {v:8s} LODO={tau_l:+.3f} (p={p_l:.4f})  in-probe={tau_i:+.3f}  "
              f"gap={tau_i-tau_l:+.3f}  head_tau={js}  n={len(y)}")
