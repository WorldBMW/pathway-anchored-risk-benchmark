"""Inject histology stats (MW U + spot-level robustness) into a completed
result JSON, without re-running training. Mirrors what train_st.py v3 now
computes. Works on any result JSON that already has:
  histology_association.per_sample[*]
  histology_association.by_histology_subtype
  histology_association.by_cin_grade  (preserved as-is)
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import kruskal, mannwhitneyu, rankdata, norm


def _dunn_bonf(groups):
    out = {}
    if len(groups) < 2:
        return out
    all_vals = np.concatenate([np.asarray(g[1]).ravel() for g in groups])
    all_labels = np.concatenate(
        [np.full(len(np.asarray(g[1]).ravel()), i) for i, g in enumerate(groups)]
    )
    R = rankdata(all_vals, method="average")
    N = len(all_vals)
    n_per_group = np.array([len(np.asarray(g[1]).ravel()) for g in groups])
    _, counts = np.unique(R, return_counts=True)
    tie_groups = counts[counts > 1]
    tie_sum = float(np.sum(tie_groups**3 - tie_groups))
    C = 1.0 - tie_sum / (N**3 - N) if N >= 3 else 1.0
    mean_ranks = np.array([np.mean(R[all_labels == i]) for i in range(len(groups))])
    n_comparisons = len(groups) * (len(groups) - 1) // 2
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            ni, nj = int(n_per_group[i]), int(n_per_group[j])
            if ni == 0 or nj == 0:
                continue
            sigma2 = (N * (N + 1) / 12.0) * (1.0 / ni + 1.0 / nj)
            sigma2 *= max(C, 1e-12)
            z = (mean_ranks[i] - mean_ranks[j]) / np.sqrt(sigma2)
            try:
                raw_p = float(2.0 * (1.0 - norm.cdf(abs(z))))
            except Exception:
                raw_p = float(min(1.0, 1.0 / max(abs(z), 1e-6) ** 2))
            bonf = float(min(raw_p * n_comparisons, 1.0))
            out[f"{groups[i][0]}_vs_{groups[j][0]}"] = {
                "z": float(z),
                "p_raw": float(raw_p),
                "p_bonferroni": bonf,
            }
    return out


def compute_mw_focus(ha):
    subtype_agg = ha["by_histology_subtype"]
    focus_pairs = [
        ("Normal_Ecto", "SCC"),
        ("Normal_Ecto", "HSIL"),
        ("Normal_Ecto", "ADC"),
        ("Normal", "SCC"),
        ("HSIL", "SCC"),
    ]
    mw = {}
    subvecs = {s: np.array(subtype_agg[s]["per_sample_means"]) for s in subtype_agg}
    for a, b in focus_pairs:
        if a not in subvecs or b not in subvecs:
            continue
        va, vb = subvecs[a], subvecs[b]
        if len(va) == 0 or len(vb) == 0:
            continue
        try:
            u_stat, p_raw = mannwhitneyu(va, vb, alternative="two-sided")
        except Exception:
            u_stat, p_raw = float("nan"), 1.0
        p_bonf5 = float(min(p_raw * len(focus_pairs), 1.0))
        mw[f"{a}_vs_{b}"] = {
            "u": (
                None
                if (isinstance(u_stat, float) and np.isnan(u_stat))
                else float(u_stat)
            ),
            "p_raw": float(p_raw),
            "p_bonf5": p_bonf5,
            "n_a": int(len(va)),
            "n_b": int(len(vb)),
        }
    return mw


def compute_spot_robust(ha):
    rows = ha["per_sample"]
    spot_by_sub = {}
    for r in rows:
        s = r["histology_subtype"]
        if s is None:
            continue
        arr = np.full(int(r["n_spots"]), float(r["mean_risk"]))
        spot_by_sub.setdefault(s, []).append(arr)
    for s in list(spot_by_sub.keys()):
        spot_by_sub[s] = np.concatenate(spot_by_sub[s])
    sub_spot_order = sorted(spot_by_sub.keys())
    spot_kw = kruskal(*[spot_by_sub[s] for s in sub_spot_order])
    spot_groups = [(s, spot_by_sub[s]) for s in sub_spot_order]
    return {
        "subtype_kruskal_stat": float(spot_kw.statistic),
        "subtype_kruskal_p": float(spot_kw.pvalue),
        "dunn_by_subtype": _dunn_bonf(spot_groups),
        "note": (
            "per-sample mean repeated to n_spots per sample; "
            "used as Fig.2 sensitivity analysis only; "
            "primary = per-sample Mann-Whitney U."
        ),
    }


def _pythonify(obj):
    if isinstance(obj, dict):
        return {k: _pythonify(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_pythonify(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        if np.isnan(obj) or np.isinf(obj):
            return None  # allow_nan=False requires real finite number
        return float(obj)
    if isinstance(obj, np.ndarray):
        return [_pythonify(x) for x in obj.tolist()]
    return obj


def patch_file(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    ha = data.get("histology_association") or {}
    if "per_sample" not in ha or "by_histology_subtype" not in ha:
        print(f"[skip] {path} missing per_sample / by_histology_subtype")
        return False
    mw = compute_mw_focus(ha)
    try:
        sr = compute_spot_robust(ha)
    except Exception as e:
        sr = {"error": str(e)}
    ha["mannwhitney_by_subtype_bonf5"] = mw
    ha["spot_level_robustness"] = sr
    data["histology_association"] = ha
    data = _pythonify(data)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, allow_nan=False, default=str)
    print(f"[ok] patched {path}")
    print(f"  mannwhitney keys: {list(mw.keys())}")
    focus = "Normal_Ecto_vs_SCC"
    if focus in mw:
        print(f"  MW {focus}: p_bonf5={mw[focus]['p_bonf5']:.3e}")
    if "subtype_kruskal_p" in sr:
        print(f"  spot KW p={sr['subtype_kruskal_p']:.3e}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", help="result JSON files to patch in-place")
    args = ap.parse_args()
    ok = 0
    for f in args.files:
        p = Path(f)
        if not p.exists():
            print(f"[missing] {p}")
            continue
        if patch_file(p):
            ok += 1
    print(f"done: {ok}/{len(args.files)} patched")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
