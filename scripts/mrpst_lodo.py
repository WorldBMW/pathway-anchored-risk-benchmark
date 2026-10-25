"""MRP-ST simulation validation: official three-tier grading.

VALID EVIDENCE AXIS
-------------------
The leave-one-donor-out (LODO) linear probe is only interpretable on a
LABEL-FREE encoder: the NOALL variant (lambda_prog = lambda_sup = lambda_hpv =
0) never sees disease labels, proxy labels, or pathway priors, so its frozen
embeddings cannot carry donor labels baked in during joint training. LODO
probes on FULL / NOPROG / NOSUP embeddings are contaminated (those encoders
were optimised with every donor's labels) and MUST NOT be reported as
generalisation evidence.

Evidence per arm (group):
  transfer  : LODO Kendall tau-b on NOALL frozen per-donor embeddings,
              averaged over seeds, with sample-label permutation p
  in_sample : in-sample head Kendall tau-b of the FULL supervised model
              (shows what supervision can fit, even for random labels)
  gap       : in_sample - transfer

Verdicts (operational, pre-registered):
  supported   : transfer mean >= 0.35 AND >=2/3 seeds with p < 0.05
  unsupported : |transfer| mean <= 0.15 AND 0 seeds with p < 0.05
  suggestive  : everything in between (weak / seed-unstable transfer)

Usage:  python scripts/mrpst_lodo.py [n_perm] [--seeds 0 1 2] [--groups ...]
Output: results/sim_lodo_summary.json  (override with --out)
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe_lodo import per_sample_embedding, lodo_probe  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"

SUP_THR = 0.35       # minimum mean LODO tau for "supported"
UNSUP_THR = 0.15     # maximum |mean LODO tau| for "unsupported"
P_ALPHA = 0.05


def head_tau(group: str, seed: int):
    fp = RES / f"results_SIM_{group}_FULL_seed{seed}.json"
    if not fp.exists():
        return None
    d = json.load(open(fp, encoding="utf-8"))
    return (d.get("progression_monotonicity") or {}).get("kendall_tau")


def transfer_tau(group: str, seed: int, n_perm: int):
    fp = RES / f"fused_embs_SIM_{group}_NOALL_seed{seed}.npz"
    if not fp.exists():
        return None
    X, y, _ = per_sample_embedding(np.load(fp))
    tau_l, p_l, tau_i = lodo_probe(X, y, n_perm)
    return {"tau_lodo": tau_l, "p": p_l, "tau_insample_probe": tau_i,
            "n_donors": int(len(y))}


def grade(rows: list[dict]):
    valid = [r for r in rows if r["transfer"] is not None]
    if not valid:
        return "missing", {}
    taus = np.array([r["transfer"]["tau_lodo"] for r in valid])
    ps = np.array([r["transfer"]["p"] for r in valid])
    n_sig = int((ps < P_ALPHA).sum())
    frac_sig = n_sig / len(valid)
    stats = {
        "transfer_mean": float(taus.mean()),
        "transfer_sd": float(taus.std(ddof=1)) if len(taus) > 1 else 0.0,
        "seeds_significant": n_sig,
        "seeds_total": len(valid),
        "fraction_significant": frac_sig,
    }
    if stats["transfer_mean"] >= SUP_THR and frac_sig >= 2 / 3:
        v = "supported"
    elif abs(stats["transfer_mean"]) <= UNSUP_THR and n_sig == 0:
        v = "unsupported"
    else:
        v = "suggestive"
    return v, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("n_perm", nargs="?", type=int, default=10000)
    ap.add_argument("--groups", nargs="+",
                    default=["group_A", "group_B", "group_C"])
    ap.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    ap.add_argument("--out", type=str, default="sim_lodo_summary.json",
                    help="output filename under results/ (default "
                         "sim_lodo_summary.json; use a new name for the "
                         "scale-matched arms so the main summary is kept)")
    args = ap.parse_args()

    summary = {
        "metric": "LODO Kendall tau-b on NOALL (label-free) frozen embeddings",
        "thresholds": {"supported_tau": SUP_THR, "unsupported_abs_tau": UNSUP_THR,
                       "alpha": P_ALPHA},
        "n_perm": args.n_perm,
        "arms": {},
    }

    for g in args.groups:
        rows = []
        for s in args.seeds:
            rows.append({
                "seed": s,
                "transfer": transfer_tau(g, s, args.n_perm),
                "full_head_insample_tau": head_tau(g, s),
            })
        verdict, stats = grade(rows)
        ins = [r["full_head_insample_tau"] for r in rows
               if r["full_head_insample_tau"] is not None]
        stats["full_head_insample_mean"] = float(np.mean(ins)) if ins else None
        stats["gap_insample_minus_transfer"] = (
            stats["full_head_insample_mean"] - stats["transfer_mean"]
            if ins and "transfer_mean" in stats else None)
        summary["arms"][g] = {"verdict": verdict, "stats": stats, "seeds": rows}
        print(f"[{g}] verdict={verdict.upper()}")
        if verdict == "missing":
            have = [r["seed"] for r in rows if r["transfer"] is not None]
            print(f"   NO NOALL embeddings found for seeds {args.seeds} "
                  f"(present: {have or 'none'}).")
            print("   Run the training first, e.g. "
                  f"bash scripts/run_sim_one.sh {g} NOALL 0 200")
            continue
        print(f"   NOALL LODO tau = {stats['transfer_mean']:.3f} "
              f"± {stats['transfer_sd']:.3f}  "
              f"(significant seeds {stats['seeds_significant']}/{stats['seeds_total']})")
        if ins:
            print(f"   FULL in-sample head tau = {stats['full_head_insample_mean']:+.3f}"
                  f"   gap = {stats['gap_insample_minus_transfer']:+.3f}")

    out = RES / args.out
    json.dump(summary, open(out, "w", encoding="utf-8"), indent=2)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
