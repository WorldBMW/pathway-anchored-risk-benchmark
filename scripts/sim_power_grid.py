#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""MRP-ST operating-characteristic aggregation (A3).

Turns the independent-replication grid produced by
``scripts/run_sim_power_grid.sh`` into the numbers that a methods journal
requires:

  * detection rate (statistical power) of the MRP-ST supported/suggestive/
    unsupported grading rule as a function of ground-truth signal strength
  * empirical type-I error of the same rule on the identity-confounding
    negative control (no disease signal)
  * threshold sensitivity of the rule, i.e. a ROC-style curve obtained by
    sweeping the "supported" tau threshold
  * the in-sample vs leave-one-donor-out dissociation on the control arm

Input : results/fused_embs_group_{A,C}_g<GEN>_<LEVEL|CTRL>[_small]_NOALL_seed<k>.npz
        results/results_SIM_group_C_g<GEN>_CTRL[_small]_FULL_seed<k>.json
Output: results/sim_power_raw.json         per-run tau / p (cached)
        results/sim_power_summary.json     aggregated power / error / ROC
        results/sim_power_operating_characteristics.png

Usage:  python scripts/sim_power_grid.py [--perm 10000] [--force] [--tag-filter STR]
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from probe_lodo import per_sample_embedding, lodo_probe  # noqa: E402

RES = ROOT / "results"

SUP_THR = 0.35        # mean tau needed for "supported"  (matches mrpst_lodo.py)
UNSUP_THR = 0.15      # |mean tau| below which "unsupported"
ALPHA = 0.05          # per-seed significance level

NAME_RE = re.compile(r"^group_([AC])_(g\d+?)_(L\d+|CTRL)(_small)?$")


def parse_group(name):
    m = NAME_RE.match(name)
    if not m:
        return None
    kind, gen, level, small = m.group(1), m.group(2), m.group(3), bool(m.group(4))
    return {"kind": kind, "gen": gen, "level": level,
            "size": "small" if small else "main"}


def discover():
    """Scan results/ for NOALL embeddings belonging to the power grid."""
    cells = {}
    # train_st.py dumps embeddings as fused_embs_<run_id>.npz where the grid
    # run_id is "SIM_group_X_g..._..._NOALL_seed<k>", so on disk the files
    # carry both a "SIM_" prefix and the "_NOALL" variant token. Accept both
    # the prefixed layout and the bare layout.
    for fp in sorted(RES.glob("fused_embs_*group_*_NOALL_seed*.npz")):
        base = fp.name[len("fused_embs_"):-len(".npz")]
        seed = int(base.rsplit("_seed", 1)[1])
        group = base.rsplit("_seed", 1)[0]
        if group.startswith("SIM_"):
            group = group[len("SIM_"):]
        if group.endswith("_NOALL"):
            group = group[: -len("_NOALL")]
        meta = parse_group(group)
        if meta is None:          # not a power-grid cohort (e.g. group_A)
            continue
        cells.setdefault(group, {"meta": meta, "runs": {}})["runs"][seed] = fp
    return cells


def full_head_tau(group, seed):
    fp = RES / f"results_SIM_{group}_FULL_seed{seed}.json"
    if not fp.exists():
        return None
    try:
        d = json.load(open(fp, encoding="utf-8"))
    except Exception:
        return None
    return (d.get("progression_monotonicity") or {}).get("kendall_tau")


def measure(cells, n_perm):
    out = {}
    for group, payload in sorted(cells.items()):
        meta = payload["meta"]
        runs = []
        for seed, fp in sorted(payload["runs"].items()):
            try:
                X, y, _ = per_sample_embedding(np.load(fp))
            except Exception as e:                       # noqa: BLE001
                print(f"  [skip] {group} seed{seed}: {e}")
                continue
            if len(np.unique(y)) < 2:
                print(f"  [skip] {group} seed{seed}: single severity level")
                continue
            tau_l, p_l, tau_in = lodo_probe(X, y, n_perm)
            runs.append({"seed": seed, "tau_lodo": float(tau_l),
                         "p": float(p_l), "tau_insample_probe": float(tau_in),
                         "n_donors": int(len(y)),
                         "full_head_insample_tau": full_head_tau(group, seed)})
            print(f"  {group:34s} seed{seed}  tau={tau_l:+.3f}  p={p_l:.4f}")
        if runs:
            out[group] = {"meta": meta, "runs": runs}
    return out


def grade_runs(runs, sup_thr=SUP_THR):
    """MRP-ST three-tier verdict for one (gen, size) cell = 3 training seeds."""
    taus = np.array([r["tau_lodo"] for r in runs])
    ps = np.array([r["p"] for r in runs])
    n_sig = int((ps < ALPHA).sum())
    frac_sig = n_sig / len(runs)
    mean_tau = float(taus.mean())
    if mean_tau >= sup_thr and frac_sig >= 2 / 3:
        verdict = "supported"
    elif abs(mean_tau) <= UNSUP_THR and n_sig == 0:
        verdict = "unsupported"
    else:
        verdict = "suggestive"
    return {"mean_tau": mean_tau, "sd_tau": float(taus.std(ddof=1)) if len(taus) > 1 else 0.0,
            "n_significant": n_sig, "n_runs": len(runs),
            "frac_significant": frac_sig, "verdict": verdict}


def aggregate(raw, levels):
    """Collapse per-run measurements into power / type-I error / ROC."""
    # (level, size) cells: pool the 3 generator seeds, 3 training seeds each
    by_level_size = {}
    ctrl = {}
    for group, payload in raw.items():
        m = payload["meta"]
        key = (m["level"], m["size"])
        tgt = ctrl if m["kind"] == "C" else by_level_size
        tgt.setdefault(key, []).extend(payload["runs"])

    detection, error = {}, {}
    for (level, size), runs in by_level_size.items():
        g = grade_runs(runs)
        detection.setdefault(size, {})[level] = g
    for (level, size), runs in ctrl.items():
        g = grade_runs(runs)
        g["frac_false_positive"] = g["frac_significant"]
        error.setdefault(size, {})[level] = g

    # ROC-style sensitivity/specificity sweep of the supported-tau threshold
    roc = {}
    for size in sorted(detection.keys()):
        taus_sig = np.concatenate([[r["tau_lodo"] for r in runs]
                                   for (lv, sz), runs in by_level_size.items()
                                   if sz == size and lv == levels[0]])
        taus_ctrl = np.concatenate([[r["tau_lodo"] for r in runs]
                                    for (lv, sz), runs in ctrl.items() if sz == size])
        grid = np.round(np.arange(0.05, 0.86, 0.025), 3)
        roc[size] = {"threshold": grid.tolist(),
                     "sensitivity": [float((taus_sig >= t).mean()) for t in grid],
                     "one_minus_specificity": [float((taus_ctrl >= t).mean()) for t in grid]}
    return detection, error, roc


def make_figure(detection, error, roc, levels, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "figure.dpi": 150,
                         "savefig.dpi": 300, "savefig.bbox": "tight"})
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))

    ax = axes[0]
    xs = np.arange(len(levels))
    for size, marker in [("main", "o"), ("small", "s")]:
        ys = [detection.get(size, {}).get(lv, {}).get("mean_tau", np.nan) for lv in levels]
        ss = [detection.get(size, {}).get(lv, {}).get("sd_tau", 0.0) for lv in levels]
        ax.errorbar(xs, ys, yerr=ss, marker=marker, capsize=4, lw=2,
                    label=f"{size} cohort")
    ax.axhline(SUP_THR, color="#38761d", ls="--", lw=1.2,
               label=f"supported tau = {SUP_THR}")
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xticks(xs); ax.set_xticklabels(levels)
    ax.set_xlabel("signal level (strong → weak)")
    ax.set_ylabel("mean LODO probe tau")
    ax.set_title("(a) Probe recovery vs signal strength")
    ax.legend(fontsize=8, frameon=False)

    ax = axes[1]
    w = 0.35
    for i, size in enumerate(["main", "small"]):
        ys = [detection.get(size, {}).get(lv, {}).get("frac_significant", np.nan)
              for lv in levels]
        ax.bar(xs + (i - 0.5) * w, ys, w, label=f"{size}: significant fraction")
    err = [error.get("main", {}).get("CTRL", {}).get("frac_false_positive", np.nan),
           error.get("small", {}).get("CTRL", {}).get("frac_false_positive", np.nan)]
    ax.axhline(ALPHA, color="#cc0000", ls="--", lw=1.2,
               label=f"nominal alpha = {ALPHA}")
    ax.set_xticks(xs); ax.set_xticklabels(levels)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("signal level (strong → weak)")
    ax.set_ylabel("fraction of runs with p < 0.05")
    ax.set_title(f"(b) Detection rate  [control: {err[0]:.2f}/{err[1]:.2f}]")
    ax.legend(fontsize=8, frameon=False)

    ax = axes[2]
    for size, marker in [("main", "o"), ("small", "s")]:
        if size not in roc:
            continue
        ax.plot(roc[size]["one_minus_specificity"], roc[size]["sensitivity"],
                marker=marker, lw=2, label=f"{size}")
    ax.plot([0, 1], [0, 1], color="gray", ls=":", lw=1)
    ax.set_xlabel("1 − specificity (control arm)")
    ax.set_ylabel("sensitivity (strongest signal)")
    ax.set_title("(c) Supported-tau threshold ROC")
    ax.legend(fontsize=8, frameon=False)

    fig.tight_layout()
    fig.savefig(path)
    print(f"figure -> {path}")
    return roc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--perm", type=int, default=10000)
    ap.add_argument("--force", action="store_true",
                    help="recompute even if results/sim_power_raw.json exists")
    ap.add_argument("--levels", nargs="+", default=["L1", "L2", "L3", "L4"])
    args = ap.parse_args()

    raw_fp = RES / "sim_power_raw.json"
    if raw_fp.exists() and not args.force:
        raw = json.load(open(raw_fp, encoding="utf-8"))
        print(f"[cache] reusing {raw_fp} ({len(raw)} cohorts)")
    else:
        cells = discover()
        if not cells:
            print("No power-grid cohorts found under results/.\n"
                  "Run:  bash scripts/run_sim_power_grid.sh")
            return
        print(f"found {len(cells)} grid cohorts; probing with n_perm={args.perm}")
        raw = measure(cells, args.perm)
        json.dump(raw, open(raw_fp, "w", encoding="utf-8"), indent=2)
        print(f"wrote {raw_fp}")

    detection, error, roc = aggregate(raw, args.levels)
    fig_fp = RES / "sim_power_operating_characteristics.png"
    make_figure(detection, error, roc, args.levels, fig_fp)

    summary = {
        "design": {
            "generator_seeds": sorted({p["meta"]["gen"] for p in raw.values()}),
            "signal_levels": args.levels,
            "sizes": sorted({p["meta"]["size"] for p in raw.values()}),
            "thresholds": {"supported_tau": SUP_THR,
                           "unsupported_abs_tau": UNSUP_THR, "alpha": ALPHA},
        },
        "detection_rate": {sz: {lv: detection[sz][lv] for lv in detection[sz]}
                           for sz in detection},
        "type_i_error_control": error,
        "threshold_roc": roc,
        "per_cohort": {g: {"meta": p["meta"], "runs": p["runs"]} for g, p in raw.items()},
    }
    out_fp = RES / "sim_power_summary.json"
    json.dump(summary, open(out_fp, "w", encoding="utf-8"), indent=2)
    print(f"summary -> {out_fp}")

    print("\n===== MRP-ST operating characteristics =====")
    for size in sorted(detection):
        print(f"[{size}] " + "  ".join(
            f"{lv}: tau={detection[size][lv]['mean_tau']:+.3f} "
            f"sig={detection[size][lv]['frac_significant']:.2f} "
            f"{detection[size][lv]['verdict']}" for lv in detection[size]))
    for size in sorted(error):
        for lv, g in error[size].items():
            print(f"[{size}] control {lv}: false-positive rate = "
                  f"{g['frac_false_positive']:.3f}")


if __name__ == "__main__":
    main()