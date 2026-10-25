"""
===========================================================================
 hnscc_discriminative_eval.py
===========================================================================
Purpose
-------
Plan-B discriminative cross-organ validation for the HNSCC cohorts
(hard-injury 1 in the CSBJ v10 review): Moran's I alone cannot establish
pathway specificity. Here we test whether the FINAL-PROTOCOL cervical model's
expression score differs between biologically meaningful groups:

GSE268014 (8 Visium HNSCC sections; Simkin et al., Nat Genet 2026):
  1. CNV-confirmed Malignant vs Non_Malignant spots ("Mixed" excluded),
     using the authors' own per-spot annotation
     (merged_metadata_Extend.rds -> gse268014_spot_annotations_8patients.csv;
      binCNAstatus, sample-specific CNA thresholds from per_sample_parameters.csv).
  2. Tumor edge (Zone_1) vs tumor core (Zone_3) within the epithelial
     compartment (zones defined by distance to the tumor-stroma boundary in
     State_Proximity_and_Zonation.R: Zone_1 = leading edge, Zone_3 = core).
  3. HPV+ vs HPV- at the SAMPLE level (4 vs 4 sections; HPV status from the
     GEO SOFT record "hpv-related" field).

GSE281978 (6 Visium sections; Lee et al., J Med Virol 2024):
  4. HPV+ (n=2) vs HPV- (n=4) at the sample level.
  5. Primary tumor (PT, n=3) vs lymph-node metastasis (LNMT, n=3).

Statistics
----------
- spot level (secondary, spots are pseudoreplicates): two-sided Mann-Whitney
  U, rank-biserial effect size r = 2U/(n1 n2) - 1.
- sample level (primary evidence): per-section mean scores -> paired Wilcoxon
  signed-rank for within-section contrasts (1-2); Mann-Whitney for between-
  section contrasts (3-5). With n <= 8 these tests have limited power; all
  per-sample values are printed so the claim is auditable.

Inputs (FINAL-protocol inference outputs):
  results/infer_XCOHORT_HNSCC_FINAL_full.json
  results/infer_XCOHORT_HNSCC_GSE281978_FINAL_full.json
  data/st_visium/geo_hnscc_hpv_GSE268014/annotations/
      gse268014_spot_annotations_8patients.csv

Usage:
  python scripts/hnscc_discriminative_eval.py
  python scripts/hnscc_discriminative_eval.py \
      --g268014_full results/infer_XCOHORT_HNSCC_FINAL_full.json \
      --g281978_full results/infer_XCOHORT_HNSCC_GSE281978_FINAL_full.json \
      --out results/hnscc_discriminative_eval.json
===========================================================================
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, wilcoxon

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

# GSE268014: GSM accession -> (patient ID, HPV-related) from GEO SOFT record.
G268014_MAP = {
    "GSM8283897": ("P5909", False),
    "GSM8283898": ("P5903", True),
    "GSM8283899": ("P5767", True),
    "GSM8283900": ("P5766", True),
    "GSM8283901": ("P5764", True),
    "GSM8283902": ("P5756", False),
    "GSM8283903": ("P5751", False),
    "GSM8283904": ("P5736", False),
}

# GSE281978: LI_SING section -> (GSM, HPV-positive, is_primary_tumor)
# from the GEO sample titles (GSM8633891-896).
G281978_MAP = {
    "LI_SING_21_00757": ("GSM8633891", False, True),    # HPV- PT2
    "LI_SING_21_00758": ("GSM8633892", False, False),   # HPV- LMNT2
    "LI_SING_21_01569": ("GSM8633893", True, True),     # HPV+ PT3
    "LI_SING_21_01570": ("GSM8633894", True, False),    # HPV+ LNMT3
    "LI_SING_21_01586": ("GSM8633895", False, True),    # HPV- PT1
    "LI_SING_21_01587": ("GSM8633896", False, False),   # HPV- LNMT1
}


def mwu_stats(x: np.ndarray, y: np.ndarray) -> dict:
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    u = mannwhitneyu(x, y, alternative="two-sided")
    U1 = float(u.statistic)
    rb = 2.0 * U1 / (len(x) * len(y)) - 1.0   # rank-biserial: x>y => positive
    return {
        "n_x": int(len(x)), "n_y": int(len(y)),
        "mean_x": float(np.mean(x)), "mean_y": float(np.mean(y)),
        "median_x": float(np.median(x)), "median_y": float(np.median(y)),
        "mwu_U": U1, "mwu_p": float(u.pvalue),
        "rank_biserial_r": float(rb),
    }


def load_scores(full_json: Path) -> dict:
    d = json.load(open(full_json, encoding="utf-8"))
    out = {}
    for s in d["samples"]:
        out[s["name"]] = pd.DataFrame({
            "barcode": s["barcodes"],
            "score": np.asarray(s["scores"], float),
        })
    return out


def eval_gse268014(full_json: Path, annot_csv: Path) -> dict:
    scores = load_scores(full_json)
    annot = pd.read_csv(annot_csv)
    rows = []
    for gsm, (pat, hpv) in G268014_MAP.items():
        if gsm not in scores:
            print(f"  [warn] {gsm} ({pat}) missing from {full_json.name}")
            continue
        df = scores[gsm].merge(
            annot[annot.Sample == pat][["SpotID", "binCNAstatus", "Zone"]],
            left_on="barcode", right_on="SpotID", how="inner")
        if len(df) == 0:
            print(f"  [warn] {gsm} ({pat}): zero barcode overlap")
            continue
        r = {"gsm": gsm, "patient": pat, "hpv_positive": hpv, "n_joined": len(df)}
        mal = df.loc[df.binCNAstatus == "Malignant", "score"].to_numpy()
        nmal = df.loc[df.binCNAstatus == "Non_Malignant", "score"].to_numpy()
        r["n_malignant"] = int(len(mal))
        r["n_nonmalignant"] = int(len(nmal))
        r["mean_malignant"] = float(mal.mean()) if len(mal) else None
        r["mean_nonmalignant"] = float(nmal.mean()) if len(nmal) else None
        if len(mal) >= 5 and len(nmal) >= 5:
            r["malignant_vs_non"] = mwu_stats(mal, nmal)
        edge = df.loc[df.Zone == "Zone_1", "score"].to_numpy()
        core = df.loc[df.Zone == "Zone_3", "score"].to_numpy()
        r["n_zone1_edge"] = int(len(edge))
        r["n_zone3_core"] = int(len(core))
        r["mean_edge"] = float(edge.mean()) if len(edge) else None
        r["mean_core"] = float(core.mean()) if len(core) else None
        if len(edge) >= 5 and len(core) >= 5:
            r["edge_vs_core"] = mwu_stats(edge, core)
        rows.append(r)

    # ---- pooled spot-level contrasts (pseudoreplication caveat) ----
    pooled = {}
    for key, col, a, b in [("malignant_vs_nonmalignant", "binCNAstatus",
                            "Malignant", "Non_Malignant"),
                           ("edge_zone1_vs_core_zone3", "Zone",
                            "Zone_1", "Zone_3")]:
        xa, xb = [], []
        for gsm, (pat, _) in G268014_MAP.items():
            if gsm not in scores:
                continue
            df = scores[gsm].merge(
                annot[annot.Sample == pat][["SpotID", "binCNAstatus", "Zone"]],
                left_on="barcode", right_on="SpotID", how="inner")
            xa.append(df.loc[df[col] == a, "score"].to_numpy())
            xb.append(df.loc[df[col] == b, "score"].to_numpy())
        xa, xb = np.concatenate(xa), np.concatenate(xb)
        pooled[key] = mwu_stats(xa, xb)

    # ---- sample-level (primary): paired across sections ----
    paired = {}
    d_mal = [r["mean_malignant"] - r["mean_nonmalignant"] for r in rows
             if r.get("mean_malignant") is not None and r.get("mean_nonmalignant") is not None]
    if len(d_mal) >= 3:
        wp = wilcoxon(d_mal, alternative="two-sided")
        paired["malignant_minus_nonmalignant"] = {
            "n_sections": len(d_mal),
            "mean_delta": float(np.mean(d_mal)),
            "median_delta": float(np.median(d_mal)),
            "wilcoxon_p": float(wp.pvalue),
            "n_sections_positive": int(sum(d > 0 for d in d_mal)),
            "per_section_delta": [float(v) for v in d_mal],
        }
    d_zone = [r["mean_edge"] - r["mean_core"] for r in rows
              if r.get("mean_edge") is not None and r.get("mean_core") is not None]
    if len(d_zone) >= 3:
        wp = wilcoxon(d_zone, alternative="two-sided")
        paired["edge_zone1_minus_core_zone3"] = {
            "n_sections": len(d_zone),
            "mean_delta": float(np.mean(d_zone)),
            "median_delta": float(np.median(d_zone)),
            "wilcoxon_p": float(wp.pvalue),
            "n_sections_positive": int(sum(d > 0 for d in d_zone)),
            "per_section_delta": [float(v) for v in d_zone],
        }

    # ---- HPV+ vs HPV- at sample level (4 vs 4) ----
    hpv_means = [(r["hpv_positive"],
                  float(pd.merge(scores[r["gsm"]],
                                 annot[annot.Sample == r["patient"]][["SpotID"]],
                                 left_on="barcode", right_on="SpotID")["score"].mean()),
                  r["mean_malignant"])
                 for r in rows]
    pos_all = [v for h, v, _ in hpv_means if h]
    neg_all = [v for h, v, _ in hpv_means if not h]
    pos_mal = [m for h, _, m in hpv_means if h and m is not None]
    neg_mal = [m for h, _, m in hpv_means if not h and m is not None]
    hpv = {
        "n_hpv_pos": len(pos_all), "n_hpv_neg": len(neg_all),
        "per_section": [{"gsm": r["gsm"], "patient": r["patient"],
                         "hpv_positive": r["hpv_positive"],
                         "score_mean_all": float(pd.merge(
                             scores[r["gsm"]],
                             annot[annot.Sample == r["patient"]][["SpotID"]],
                             left_on="barcode", right_on="SpotID")["score"].mean()),
                         "score_mean_malignant": r["mean_malignant"]}
                        for r in rows],
    }
    if len(pos_all) >= 2 and len(neg_all) >= 2:
        hpv["all_spots_mean"] = mwu_stats(pos_all, neg_all)
    if len(pos_mal) >= 2 and len(neg_mal) >= 2:
        hpv["malignant_only_mean"] = mwu_stats(pos_mal, neg_mal)

    return {"n_sections": len(rows), "per_section": rows,
            "pooled_spot_level_PSEUDOREPLICATION": pooled,
            "sample_level_paired": paired, "sample_level_hpv": hpv,
            "annotation_source": "Simkin et al. merged_metadata_Extend.rds "
                                 "(binCNAstatus; Zone_1=edge ... Zone_3=core)"}


def eval_gse281978(full_json: Path) -> dict:
    scores = load_scores(full_json)
    per = []
    for name, (gsm, hpv, is_pt) in G281978_MAP.items():
        if name not in scores:
            print(f"  [warn] {name} missing from {full_json.name}")
            continue
        s = scores[name]["score"].to_numpy()
        per.append({"section": name, "gsm": gsm, "hpv_positive": hpv,
                    "site": "primary" if is_pt else "lymph_node_metastasis",
                    "n_spots": int(len(s)),
                    "score_mean": float(s.mean()),
                    "score_median": float(np.median(s))})
    pos = [r["score_mean"] for r in per if r["hpv_positive"]]
    neg = [r["score_mean"] for r in per if not r["hpv_positive"]]
    pt = [r["score_mean"] for r in per if r["site"] == "primary"]
    ln = [r["score_mean"] for r in per if r["site"] == "lymph_node_metastasis"]
    out = {"n_sections": len(per), "per_section": per,
           "sample_level": {
               "hpv_pos_vs_neg": {"n_pos": len(pos), "n_neg": len(neg),
                                  **(mwu_stats(pos, neg) if len(pos) >= 2 and len(neg) >= 2 else {})},
               "primary_vs_lnmt": {"n_pt": len(pt), "n_lnmt": len(ln),
                                   **(mwu_stats(pt, ln) if len(pt) >= 2 and len(ln) >= 2 else {})},
           },
           "note": "n=2 HPV+ vs n=4 HPV- sections: extremely limited power; "
                   "per-section values are the primary evidence."}
    # pooled spot level (pseudoreplication)
    xp = [scores[r["section"]]["score"].to_numpy() for r in per if r["hpv_positive"]]
    xn = [scores[r["section"]]["score"].to_numpy() for r in per if not r["hpv_positive"]]
    if xp and xn:
        out["pooled_spot_level_PSEUDOREPLICATION_hpv"] = mwu_stats(
            np.concatenate(xp), np.concatenate(xn))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--g268014_full", type=Path,
                    default=REPO / "results" / "infer_XCOHORT_HNSCC_FINAL_full.json")
    ap.add_argument("--g281978_full", type=Path,
                    default=REPO / "results" / "infer_XCOHORT_HNSCC_GSE281978_FINAL_full.json")
    ap.add_argument("--annot", type=Path,
                    default=REPO / "data" / "st_visium" / "geo_hnscc_hpv_GSE268014"
                            / "annotations" / "gse268014_spot_annotations_8patients.csv")
    ap.add_argument("--out", type=Path,
                    default=REPO / "results" / "hnscc_discriminative_eval.json")
    args = ap.parse_args()

    out = {}
    if args.g268014_full.exists() and args.annot.exists():
        print("[GSE268014] malignant/zone/HPV contrasts ...")
        out["GSE268014"] = eval_gse268014(args.g268014_full, args.annot)
        for r in out["GSE268014"]["per_section"]:
            mv = r.get("malignant_vs_non", {})
            zv = r.get("edge_vs_core", {})
            print(f"  {r['patient']} HPV{'+' if r['hpv_positive'] else '-'} "
                  f"joined={r['n_joined']} "
                  f"mal {r.get('mean_malignant'):.3f} vs non {r.get('mean_nonmalignant'):.3f} "
                  f"p={mv.get('mwu_p', float('nan')):.2e} r={mv.get('rank_biserial_r', float('nan')):.3f} | "
                  f"edge {r.get('mean_edge'):.3f} vs core {r.get('mean_core'):.3f} "
                  f"p={zv.get('mwu_p', float('nan')):.2e}")
        pr = out["GSE268014"]["sample_level_paired"]
        if "malignant_minus_nonmalignant" in pr:
            d = pr["malignant_minus_nonmalignant"]
            print(f"  SAMPLE-LEVEL mal-non: d={d['mean_delta']:.4f} "
                  f"{d['n_sections_positive']}/{d['n_sections']}>0 p={d['wilcoxon_p']:.4f}")
        if "edge_zone1_minus_core_zone3" in pr:
            d = pr["edge_zone1_minus_core_zone3"]
            print(f"  SAMPLE-LEVEL edge-core: d={d['mean_delta']:.4f} "
                  f"{d['n_sections_positive']}/{d['n_sections']}>0 p={d['wilcoxon_p']:.4f}")
        h = out["GSE268014"]["sample_level_hpv"]
        if "all_spots_mean" in h:
            q = h["all_spots_mean"]
            print(f"  SAMPLE-LEVEL HPV+({q['n_x']}) vs HPV-({q['n_y']}) "
                  f"means {q['mean_x']:.3f} vs {q['mean_y']:.3f} p={q['mwu_p']:.4f}")
    else:
        print(f"[skip] GSE268014: missing {args.g268014_full} or {args.annot}")

    if args.g281978_full.exists():
        print("[GSE281978] HPV / PT-vs-LNMT contrasts ...")
        out["GSE281978"] = eval_gse281978(args.g281978_full)
        for r in out["GSE281978"]["per_section"]:
            print(f"  {r['section']} HPV{'+' if r['hpv_positive'] else '-'} "
                  f"{r['site']:<22s} mean={r['score_mean']:.4f}")
        sl = out["GSE281978"]["sample_level"]
        q = sl["hpv_pos_vs_neg"]
        if "mwu_p" in q:
            print(f"  SAMPLE-LEVEL HPV+({q['n_x']}) vs HPV-({q['n_y']}) "
                  f"{q['mean_x']:.3f} vs {q['mean_y']:.3f} p={q['mwu_p']:.4f}")
        q = sl["primary_vs_lnmt"]
        if "mwu_p" in q:
            print(f"  SAMPLE-LEVEL PT({q['n_x']}) vs LNMT({q['n_y']}) "
                  f"{q['mean_x']:.3f} vs {q['mean_y']:.3f} p={q['mwu_p']:.4f}")
    else:
        print(f"[skip] GSE281978: missing {args.g281978_full}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
